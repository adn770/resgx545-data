#!/usr/bin/env python3
"""run_p1138.py: the laptop side of the 11.38 arithmetic sweep.  Runs on the laptop (python3, no numpy),
one process of the tool per job, the whole raw output of every job kept gzipped, nothing written to any
register (the options are render options only), the GPU reset through the debugfs `reset` after a failed
job.  Never deletes a directory.

    run_p1138.py --cases cases.tsv --out DIR [--kinds D,I,C] [--sets fit,heldout,repeat] [--first N --last M]
                 [--tool PATH] [--bins DIR] [--mock]

Job kinds of a case (the `jobs` column of cases.tsv):
  D  tri with the depth store (E465's layout, pitch G = 1): the colour image and the depth buffer
  I  two probes: pa0 (the vertices' clip z iterated) and pa1 (their clip x iterated) as the colour
  C  the plain green probe (the coverage under another pixel program)
Files: DIR/jobs.tsv (id, kind, rc, seconds, raw size, raw sha256, flags), DIR/D/ID.txt.gz and ID.depth.gz,
DIR/I0/ID.txt.gz, DIR/I1/ID.txt.gz, DIR/C/ID.txt.gz.  A marker line goes to /dev/kmsg before each job."""
import argparse
import gzip
import hashlib
import os
import subprocess
import sys
import time

BG = 0xff203040
DEPTH_CTL = 0x0017100c           # E465's control word; bits 11:3 are the pitch G, here tiles across - 1 (no overlap)
FAIL = ("failed", "faulted", "hung", "FAIL", "Traceback")


def pitch_g(w):
    """G = tiles across - 1, at least 1: the tiles of a row do not overlap (E465: the window is (th-1)(G+1)+tw tiles)"""
    return max(1, (w + 31) // 32 - 1)


def depth_ctl(w):
    return (DEPTH_CTL & ~(0x1ff << 3)) | (pitch_g(w) << 3)


def depth_pages(w, h):
    tw, th = (w + 31) // 32, (h + 15) // 16
    tiles = (th - 1) * (pitch_g(w) + 1) + tw
    return max((w * h * 4 + 4095) // 4096, tiles // 2) + 16


def vtx_args(c):
    v = ",".join(str(x) for x in c["v"])
    z = ",".join(c["z"])
    return ["--tri-v", v, "--tri-z", z]


def build_cmd(kind, c, tool, bins, depth_dir, mock=False):
    pre = [] if mock else ["sudo", "-n", "timeout", "120"]
    pre = pre + [tool] + (["--mock"] if mock else [])
    w, h = str(c["w"]), str(c["h"])
    if kind == "D":
        return pre + ["tri", "--keep-overflow", "--wait-ms", "20000", "--width", w, "--height", h] + vtx_args(c) + [
            "--depth", "--depth-ctl", hex(depth_ctl(c["w"])), "--depth-fill", "0xdeadbeef", "--depth-dump", depth_dir,
            "--depth-pages", str(depth_pages(c["w"], c["h"])), "--poke", "blk:1=0x00400200", "--pixels"]
    base = ["probe", "--tri", "pixpds:12", "--temps", "32", "--pixels", "--width", w, "--height", h] + vtx_args(c)
    if kind in ("I0", "I1"):
        k = kind[1]
        return pre + base + ["--vtx-coords", "2", "--slot", "pixel=%s/pix_pa%s.bin" % (bins, k),
                             "--slot", "vtxuse=%s/vtx_attr_zx.bin" % bins, "%s/p1138-it-a%s__0.bin" % (bins, k)]
    if kind == "C":
        return pre + base + ["--slot", "pixel=%s/pix_green.bin" % bins, "%s/p1138-green__0.bin" % bins]
    raise ValueError(kind)


def load_cases(path):
    out = []
    for line in open(path):
        f = line.rstrip("\n").split("\t")
        if len(f) < 16:
            continue
        out.append(dict(id=int(f[0]), set=f[1], cls=f[2], w=int(f[3]), h=int(f[4]), v=f[5:11], z=f[11:14],
                        pair=f[14], jobs=f[15]))
    return out


def kinds_of(c, wanted):
    ks = []
    for k in c["jobs"]:
        for kind in (("D",) if k == "D" else ("I0", "I1") if k == "I" else ("C",)):
            if kind in wanted or kind[0] in wanted:
                ks.append(kind)
    return ks


def gz_write(path, data):
    with open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=6, mtime=0) as g:
            g.write(data)


class Runner:
    def __init__(self, a):
        self.a = a
        self.out = a.out
        self.dbg = None
        if not a.mock:
            ls = subprocess.run(["sudo", "-n", "sh", "-c", "ls -d /sys/kernel/debug/dri/*/sgx"], capture_output=True,
                                text=True).stdout.split()
            self.dbg = ls[0] if ls else None
            if not self.dbg:
                sys.exit("no sgx debugfs directory (debug option off?)")
        self.run_id = "%d-%d" % (time.time(), os.getpid())
        self.bad = 0
        self.resets = 0

    def mark(self, text):
        if self.a.mock:
            return
        subprocess.run(["sudo", "-n", "tee", "/dev/kmsg"], input=("resgx545 p1138 %s run %s\n" % (text, self.run_id)).encode(),
                       capture_output=True)

    def reset_gpu(self):
        self.resets += 1
        if self.a.mock:
            return
        subprocess.run(["sudo", "-n", "tee", self.dbg + "/reset"], input=b"1\n", capture_output=True)
        time.sleep(1)

    def healthy(self):
        for attempt in range(2):
            r = subprocess.run((["sudo", "-n", "timeout", "60"] if not self.a.mock else []) + [self.a.tool] +
                               (["--mock"] if self.a.mock else []) + ["tri"], capture_output=True, text=True,
                               stdin=subprocess.DEVNULL)
            if "diff: 0 of 4096" in r.stdout:
                self.bad = 0
                return True
            if attempt == 0:
                self.reset_gpu()
                time.sleep(2)
        self.bad += 1
        print("  health: the plain triangle does not draw (%d)" % self.bad, flush=True)
        if self.bad >= 3:
            print("## abort: the GPU did not recover three times", flush=True)
            sys.exit(3)
        return False

    def job(self, kind, c):
        d = os.path.join(self.out, kind)
        depth_file = os.path.join(self.a.work, "depth.1.bin")
        if kind == "D" and os.path.exists(depth_file):
            os.remove(depth_file)                      # a single file: a stale dump must not be read
        self.mark("job %d %s" % (c["id"], kind))
        cmd = build_cmd(kind, c, self.a.tool, self.a.bins, self.a.work, self.a.mock)
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL, timeout=200)
        dt = time.time() - t0
        raw = r.stdout + (b"## stderr\n" + r.stderr if r.stderr else b"")
        flags = []
        text = raw.decode("utf-8", "replace")
        if r.returncode:
            flags.append("rc%d" % r.returncode)
        if any(k in text for k in FAIL):
            flags.append("failtext")
        gz_write(os.path.join(d, "%d.txt.gz" % c["id"]), raw)
        if kind == "D":
            if os.path.exists(depth_file):
                gz_write(os.path.join(d, "%d.depth.gz" % c["id"]), open(depth_file, "rb").read())
            else:
                flags.append("nodepth")
        with open(os.path.join(self.out, "jobs.tsv"), "a") as jf:
            jf.write("%d\t%s\t%d\t%.3f\t%d\t%s\t%s\n" % (c["id"], kind, r.returncode, dt, len(raw),
                                                         hashlib.sha256(raw).hexdigest(), ",".join(flags) or "-"))
        return flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--kinds", default="D,I,C")
    ap.add_argument("--sets", default="fit,heldout,repeat")
    ap.add_argument("--first", type=int, default=0)
    ap.add_argument("--last", type=int, default=10 ** 9)
    ap.add_argument("--tool", default=os.path.expanduser("~/sgxfive-test-1138"))
    ap.add_argument("--bins", default=os.path.expanduser("~/p1138-bins"))
    ap.add_argument("--work", default=os.path.expanduser("~/p1138-work"))
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    wanted = set(a.kinds.split(","))
    sets = set(a.sets.split(","))
    for sub in ("D", "I0", "I1", "C", a.work):
        os.makedirs(os.path.join(a.out, sub) if sub != a.work else sub, exist_ok=True)
    done = set()
    jf = os.path.join(a.out, "jobs.tsv")
    if a.resume and os.path.exists(jf):
        for line in open(jf):
            f = line.split("\t")
            if f[2] == "0" and f[6].strip() == "-":
                done.add((int(f[0]), f[1]))
    r = Runner(a)
    cases = [c for c in load_cases(a.cases) if c["set"] in sets and a.first <= c["id"] <= a.last]
    n = nbad = 0
    r.healthy()
    for c in cases:
        for kind in kinds_of(c, wanted):
            if (c["id"], kind) in done:
                continue
            flags = r.job(kind, c)
            n += 1
            if flags:
                nbad += 1
                print("  case %d %s %s: %s" % (c["id"], c["cls"], kind, ",".join(flags)), flush=True)
                r.reset_gpu()
                r.healthy()
            if n % 100 == 0:
                print("## %d jobs, %d flagged, %d resets, case %d" % (n, nbad, r.resets, c["id"]), flush=True)
    print("## done: %d jobs, %d flagged, %d resets" % (n, nbad, r.resets), flush=True)
    r.healthy()


if __name__ == "__main__":
    main()
