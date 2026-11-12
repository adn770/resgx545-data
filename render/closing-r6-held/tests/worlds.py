#!/usr/bin/env python3
"""worlds.py: the fake laptop's tool for tests/run_mock.sh and the replay fixtures built from E848's kept files.

  worlds.py tool ARGS...        the fake ~/sgxfive-test-rgn4.  It answers FROM ITS ARGV and the fake debugfs state only (never from a
                                case name or a marker's name): a held 4x job faults only with `--tri-full`, `cmd:1=0xe0000000`, a
                                maximum equal to its size and render_rgn_arrays 1 (E828's forced fault); its page is the size's (640 x
                                480: 0x2000a, 288 x 144: 0x20006, any other: 0x2000f).  After it answers it writes the latest case
                                marker of the kernel log to $FAKE_DIR/answered (the sudo shim's regs read during a hold waits for that
                                line: no timing window on the fake's start-up).  FAKE_SLOW_START=S answers S seconds late.
  worlds.py e848 DST MAP...     copy E848's kept stage-h files into DST under this session's names (MAP: E848CELL=OURCELL), the steps
                                h1, h2, h3 renamed t1, t2, t3, with a cases.tsv of our columns (the replays of tests/test_replay.py).

The fake GPU state lives in $FAKE_DIR: state ("idle" or "STAT WORD STATUS2 STATUS"), hold (Y/N), list (the directory list the next
job takes: 1 after a reset, one more per job, as E848's h4 read [infer]), pending ("WORD COUNT": the replay a held TA write fault left).
Worlds ($FAKE_WORLD): model (one replay a fault through the list current at the next TA run, the flush changes nothing: H-LIST and
H-PEND), flushclears (the flush drops the pending write: H-FLUSH), word (the replay keeps the job's list 1: H-WORD), replay2 (two
replays a fault), replay3 (three: a cell's third triangle fails), m110 (every reset of a held fault logs the -110 boot timeout),
noreplay (nothing pending after a fault: a0's control fails), othershape (the replay at page 0x20006 whatever the job's),
nofault (the held job completes), gatebad (bif_flush is taken with nothing held), flushrefused (bif_flush refused even while held),
fillfault (a fill faults with the pending word).
"""
import glob
import gzip
import os
import re
import shutil
import sys
import time

DATA = "/Users/jtorra/src/resgx545-data"
E848 = DATA + "/render/closing-r4-render4x/out/20261111-211649/h"
FAULT_LINE = "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90004 at 0x%08x (PD 0x5dbf000) stalls job %d, recovering"
HELD_LINE = "gma500 0000:00:02.0: [drm] sgxfive: job %d hung, recovery held (debugfs hold_recovery)"
RESET_LINES = ["gma500 0000:00:02.0: [drm] SGX stopped, 0 events seen",
               "gma500 0000:00:02.0: [drm] SGX reset: BIF_FAULT 0x0 BIF_INT_STAT 0x80000 EVENT_STATUS 0x20000000/0x480",
               "gma500 0000:00:02.0: [drm] SGX reset: after the fault clear BIF_FAULT 0x0 BIF_INT_STAT 0x80000",
               "gma500 0000:00:02.0: [drm] SGX boot: kicking the EDM",
               "gma500 0000:00:02.0: [drm] SGX boot: EDM up after 155 us"]
PAGES = {(640, 480): 0x2000a, (288, 144): 0x20006}


def rd(F, n, default=""):
    try:
        return open(os.path.join(F, n)).read().strip()
    except OSError:
        return default


def wr(F, n, v):
    open(os.path.join(F, n), "w").write("%s\n" % v)


def klog(lines):
    with open(os.environ["KMSG"], "a") as f:
        for ln in lines:
            f.write(ln + "\n")


def latest_marker():
    t = open(os.environ["KMSG"]).read()
    m = re.findall(r"resgx545 case (\S+) ", t)
    return m[-1] if m else ""


def take_list(F):
    lst = int(rd(F, "list", "1") or 1)
    wr(F, "list", lst + 1)
    return lst


def opt(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        return argv[i + 1] if i + 1 < len(argv) else default
    return default


def replay(F, world, lst, jobno):
    """A TA run after a pending write: (word or None).  Consumes one replay."""
    p = rd(F, "pending")
    if not p:
        return None
    word, n = (int(x, 0) for x in p.split())
    if n <= 0:
        return None
    wr(F, "pending", "0x%08x %d" % (word, n - 1)) if n > 1 else os.remove(os.path.join(F, "pending"))
    if world == "othershape":
        return (0x20006 << 12) | 0x060 | lst
    if world == "word":
        return word
    return (word & ~0xf) | lst


def tool(argv):
    F, world = os.environ["FAKE_DIR"], os.environ.get("FAKE_WORLD", "model")
    R = os.environ["FAKE_DBGREAL"]
    with open(os.environ.get("FAKE_LOG", os.devnull), "a") as f:
        f.write(" ".join(argv) + "\n")
    time.sleep(float(os.environ.get("FAKE_SLOW_START", "0") or 0))
    marker = latest_marker()
    jobno = 100 + len(open(os.environ["KMSG"]).read().splitlines())
    lst = take_list(F)
    rgn = int(open(os.path.join(R, "render_rgn_arrays")).read().strip() or "0", 0)
    rc = 0
    if argv[:1] == ["fill"]:
        w = replay(F, world, lst, jobno) if world == "fillfault" else None
        if w is not None:
            klog([FAULT_LINE % (w, jobno)] + RESET_LINES)
            print("fill: job failed: Connection timed out")
            rc = 1
        else:
            print("fill: 64x32 0xff203040\ndiff: 0 of 2048 pixels")
    elif argv[:1] == ["tri"] and "--tri-full" not in argv:
        w = replay(F, world, lst, jobno)
        if w is not None:
            klog([FAULT_LINE % (w, jobno)] + RESET_LINES)
            print("tri: render context for targets up to 64x64\njob: failed: job faulted (Connection timed out)")
            rc = 1
        else:
            print("tri: render context for targets up to 64x64\njob: ok\ndiff: 0 of 4096 pixels\ntri: 1 renders ok")
    elif argv[:1] == ["tri"]:
        w, h = int(opt(argv, "--width", "0")), int(opt(argv, "--height", "0"))
        mw, mh = int(opt(argv, "--max-width", "0")), int(opt(argv, "--max-height", "0"))
        forced = "cmd:1=0xe0000000" in argv and rgn == 1 and (mw, mh) == (w, h) and "--aa4" not in argv
        if forced and world != "nofault":
            word = (PAGES.get((w, h), 0x2000f) << 12) | 0x060 | lst
            wr(F, "state", "0x90004 0x%08x 0x480 0x20000000" % word)
            n = {"replay2": 2, "replay3": 3, "noreplay": 0}.get(world, 1)
            if n:
                wr(F, "pending", "0x%08x %d" % (word, n))
            held = rd(F, "hold") == "Y"
            klog([FAULT_LINE % (word, jobno)] + ([HELD_LINE % jobno] if held else []))
            wr(F, "answered", marker)
            if held:
                for _ in range(600):                   # the job waits for the kernel's recovery (the reset), bounded
                    if rd(F, "state") == "idle":
                        break
                    time.sleep(0.1)
            else:
                wr(F, "state", "idle")
            print("tri: render context for targets up to %dx%d\njob: failed: job hung, context lost (Connection timed out)" % (mw, mh))
            return 1
        n = w * h
        print("tri: render context for targets up to %dx%d\njob: ok\ndiff: 0 of %d pixels\ntri: 1 renders ok" % (mw, mh, n))
    else:
        print("sgxfive-test: unknown command %s" % " ".join(argv))
        rc = 2
    wr(F, "answered", marker)
    return rc


# ---- E848 fixtures --------------------------------------------------------------------------------------------------------------
COLS = "name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tmode\tfault_req\treset_rc\theld_msg"


def e848(dst, maps):
    """Copy E848's stage-h cells as this session's cells: maps {e848cell: ourcell}; steps h1..h3 -> t1..t3."""
    os.makedirs(dst, exist_ok=True)
    rows = [COLS]
    head = open(os.path.join(E848, "cases.tsv")).read().splitlines()
    cols = head[0].split("\t")
    for src, ours in maps.items():
        for ln in head[1:]:
            f = dict(zip(cols, ln.split("\t")))
            nm = f["name"]
            if nm != src and not nm.startswith(src + "."):
                continue
            stp = nm[len(src) + 1:] if nm != src else ""
            stp = {"h1": "t1", "h2": "t2", "h3": "t3", "h4": "t4"}.get(stp, stp)
            f["name"] = ours + ("." + stp if stp else "")
            f["stage"] = "q"
            rows.append("\t".join(f[c] for c in cols))
        for p in glob.glob(os.path.join(E848, src + ".*")):
            rest = os.path.basename(p)[len(src):]
            for a, b in (("h1", "t1"), ("h2", "t2"), ("h3", "t3"), ("h4", "t4")):
                rest = rest.replace(".%s." % a, ".%s." % b).replace(".snap%s." % a, ".snap%s." % b)
            shutil.copy(p, os.path.join(dst, ours + rest))
    open(os.path.join(dst, "cases.tsv"), "w").write("\n".join(rows) + "\n")
    return dst


def s0_world(dst, refused=True, ctrl_same=True, peek="reg 0x0694 0x00000000", tri_ok=True):
    """A synthesized s0 (the new kernel's gate row has no earlier record): n0 from the fork's text, c1 from E848's health output."""
    os.makedirs(dst, exist_ok=True)
    gz = lambda n, t: gzip.open(os.path.join(dst, n), "wt").write(t)  # noqa: E731
    gz("n0-gate.txt.gz", "rc 1\ntee: /sys/kernel/debug/dri/0/sgx/bif_flush: Device or resource busy\n" if refused else "rc 0\n\n")
    regs = "sgxfive regs 1\nreg 0x0c00 0x00000000\nreg 0x0c04 0x00080000\nreg 0x0c08 0x00000000\n"
    gz("n0-gate.snap0.regs.gz", regs)
    gz("n0-gate.snap1.regs.gz", regs if ctrl_same else regs.replace("0x0c00 0x00000000", "0x0c00 0x00000008"))
    gz("n0-gate.dmesg.gz", "")
    gz("n0-gate.peek0.txt.gz", peek + "\n")
    shutil.copy(os.path.join(E848, "begin.health1.txt.gz"), os.path.join(dst, "c1-tri.txt.gz"))
    open(os.path.join(dst, "cases.tsv"), "w").write("\n".join([
        COLS,
        "n0-gate\ts0\tcontrol\tsafe\tgate\t-\t-\t1\t%s\tgate\t-\t-\tno" % ("ok" if refused and ctrl_same else "fail"),
        "c1-tri\ts0\tcontrol\tsafe\texpectdiff\t-\ttri --keep-going\t0\t%s\tplain\t-\t-\tno" % ("ok" if tri_ok else "fail"),
    ]) + "\n")
    return dst


if __name__ == "__main__":
    if sys.argv[1] == "tool":
        sys.exit(tool(sys.argv[2:]))
    if sys.argv[1] == "e848":
        e848(sys.argv[2], dict(a.split("=") for a in sys.argv[3:]))
        sys.exit(0)
    print(__doc__)
    sys.exit(2)
