#!/usr/bin/env python3
"""run_p1140.py: the laptop side of the p1140 coverage-envelope sweep (python3, standard library only).

    run_p1140.py --cases cases-1140.tsv --out DIR [--groups S1,S2,..] [--sets fit,heldout,pilot,repeat] [--first ID --last ID]
                 [--tool PATH] [--check-each] [--resume] [--mock]

One process of the tool per job: `tri --tri-unit U --tri-v ... --pixels-rle` (colour image only; no depth, no probe), the
tool printing the vertices and the clip words it sends.  Per job: a marker line to /dev/kmsg, the whole raw output gzipped
(DIR/raw/ID.txt.gz), one line in DIR/jobs.tsv: id, rc, seconds, raw size, raw sha256, flags, the command.  After a flagged
job the GPU is reset through the debugfs `reset` file and a plain 64 x 64 triangle must draw exactly; three failed
recoveries in a row stop the script (exit 3).  --check-each runs that plain triangle before every job (the far cases).
Nothing is written to any register; no directory is deleted."""
import argparse
import gzip
import hashlib
import os
import subprocess
import sys
import time

FAIL = ("failed", "faulted", "hung", "FAIL", "Traceback")
COLS = ("id", "set", "group", "cls", "w", "h", "unit", "v0x", "v0y", "v1x", "v1y", "v2x", "v2y", "pair", "jobs")


def load_cases(path):
    out = []
    for line in open(path):
        f = line.rstrip("\n").split("\t")
        if len(f) != len(COLS):
            continue
        c = dict(zip(COLS, f))
        for k in ("id", "w", "h", "unit"):
            c[k] = int(c[k])
        c["v"] = [int(c[k]) for k in COLS[7:13]]
        out.append(c)
    return out


def build_cmd(c, tool, mock=False):
    pre = [] if mock else ["sudo", "-n", "timeout", "120"]
    pre = pre + [tool] + (["--mock"] if mock else [])
    return pre + ["tri", "--keep-overflow", "--wait-ms", "20000", "--width", str(c["w"]), "--height", str(c["h"]),
                  "--tri-unit", str(c["unit"]), "--tri-v", ",".join(str(x) for x in c["v"]), "--pixels-rle"]


def gz_write(path, data):
    with open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=6, mtime=0) as g:
            g.write(data)


class Runner:
    def __init__(self, a):
        self.a = a
        self.dbg = None
        if not a.mock:
            ls = subprocess.run(["sudo", "-n", "sh", "-c", "ls -d /sys/kernel/debug/dri/*/sgx"], capture_output=True,
                                text=True).stdout.split()
            self.dbg = ls[0] if ls else None
            if not self.dbg:
                sys.exit("no sgx debugfs directory")
        self.run_id = "%d-%d" % (time.time(), os.getpid())
        self.bad = 0
        self.resets = 0

    def mark(self, text):
        if not self.a.mock:
            subprocess.run(["sudo", "-n", "tee", "/dev/kmsg"], input=("resgx545 p1140 %s run %s\n" % (text, self.run_id)).encode(),
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

    def job(self, c):
        self.mark("job %d" % c["id"])
        cmd = build_cmd(c, self.a.tool, self.a.mock)
        t0 = time.time()
        flags = []
        try:
            r = subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL, timeout=200)
            rc, raw = r.returncode, r.stdout + (b"## stderr\n" + r.stderr if r.stderr else b"")
        except subprocess.TimeoutExpired as e:
            rc, raw = 124, (e.stdout or b"") + b"## timeout\n"
            flags.append("timeout")
        dt = time.time() - t0
        text = raw.decode("utf-8", "replace")
        if rc:
            flags.append("rc%d" % rc)
        if any(k in text for k in FAIL):
            flags.append("failtext")
        gz_write(os.path.join(self.a.out, "raw", "%d.txt.gz" % c["id"]), raw)
        with open(os.path.join(self.a.out, "jobs.tsv"), "a") as jf:
            jf.write("%d\t%d\t%.3f\t%d\t%s\t%s\t%s\n" % (c["id"], rc, dt, len(raw), hashlib.sha256(raw).hexdigest(),
                                                       ",".join(flags) or "-", " ".join(cmd[4 if not self.a.mock else 0:])))
        return flags


def select(cases, a):
    groups = set(a.groups.split(",")) if a.groups else None
    sets = set(a.sets.split(","))
    return [c for c in cases if c["set"] in sets and (groups is None or c["group"] in groups) and a.first <= c["id"] <= a.last]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--groups", default="")
    ap.add_argument("--sets", default="fit,heldout,repeat")
    ap.add_argument("--first", type=int, default=0)
    ap.add_argument("--last", type=int, default=10 ** 9)
    ap.add_argument("--tool", default=os.path.expanduser("~/sgxfive-test-1140"))
    ap.add_argument("--check-each", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--mock", action="store_true")
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "raw"), exist_ok=True)
    done = set()
    jf = os.path.join(a.out, "jobs.tsv")
    if a.resume and os.path.exists(jf):
        for line in open(jf):
            f = line.split("\t")
            if f[1] == "0" and f[5].strip() == "-":
                done.add(int(f[0]))
    r = Runner(a)
    cases = select(load_cases(a.cases), a)
    r.mark("script start %d cases" % len(cases))
    n = nbad = 0
    r.healthy()
    for c in cases:
        if c["id"] in done:
            continue
        if a.check_each and not r.healthy():
            continue
        flags = r.job(c)
        n += 1
        if flags:
            nbad += 1
            print("  case %d %s %s: %s" % (c["id"], c["group"], c["cls"], ",".join(flags)), flush=True)
            r.reset_gpu()
            r.healthy()
        if n % 100 == 0:
            print("## %d jobs, %d flagged, %d resets, case %d" % (n, nbad, r.resets, c["id"]), flush=True)
    print("## done: %d jobs, %d flagged, %d resets" % (n, nbad, r.resets), flush=True)
    r.mark("script end %d jobs %d flagged" % (n, nbad))
    r.healthy()


if __name__ == "__main__":
    main()
