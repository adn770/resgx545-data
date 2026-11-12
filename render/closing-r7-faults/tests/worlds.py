#!/usr/bin/env python3
"""worlds.py: the fake laptop of tests/run_mock.sh (its tool and its kernel's reset) and the replay fixtures built from kept files.

  worlds.py tool ARGS...      the fake ~/sgxfive-test-rgn4.  It answers FROM ITS ARGV, the program file its argv names and the fake
                              debugfs state only (never from a case name or a marker's name):
                              - a held 4x job faults only with `--tri-full`, `cmd:1=0xe0000000`, a maximum equal to its size, no --aa4
                                and render_rgn_arrays 1 (E828's forced fault); its page from the size, typed here by hand from the
                                kept faults (E507, E729, E789, E848; 128 x 528 the layout's 0x20009) and 0x2000f for any other size;
                              - a plain `tri` after such a fault replays it (once; `replay3`: three times) through the kernel's own
                                recovery, whose boot times out as the world says;
                              - `probe --temps 32 --pixels FILE` runs FILE's lock and release words (found by assembling them with
                                usse-asm here, not from any table of the session) over 512 quads as FAKE_LOCK says: self (a second lock
                                of a held mutex blocks its holder), reflag (it passes; one release frees), recount (it passes; counted);
                                a mutex still held at a quad's end blocks the next quad; a block is the job hung, recovered.
                              After it answers it writes the latest case marker to $FAKE_DIR/answered (the sudo shim's regs read
                              during a hold waits for it: no timing window on the fake's start-up); FAKE_SLOW_START=S answers S s late.
  worlds.py reset             the fake kernel's debugfs reset: the reset lines and a boot, two when the first times out (a held
                              fault whose page the world times out); exit 1 when a boot timed out (as the real write's status)
  worlds.py kregnow VALUE     the fake kernel's kregnow write (CR_BIF_CTRL bit 4 only): the kernel's line; refused in world kregrefuse
  worlds.py r6held DST MAP... copy r6-held's kept stage-q cells into DST under this session's names (MAP: R6CELL=OURCELL)
  worlds.py e826 DST MAP...   the same from E826's k-bif (n0-idle as the gate row, f2-ta-write as a clr cell)
  worlds.py e088 DST MAP...   the same from E088's raw.txt (usse-quad-lock-counter__N=OURROW)

Worlds ($FAKE_WORLD): model (E901's R-PAGE: a boot after a held reset or a replay of pages 0x20006 to 0x20008 times out, the
second boot comes up), size (only 288 x 144 times out), clr (as model, but a held fault whose CLEAR_FAULT was flipped twice boots
up), time (as model, but a held fault reset FAKE_LONG_S or more after it boots up), dead (the second boot fails too: rc 26),
ctl640 (page 0x2000a times out too: d stops on its control), word (a replay faults with 0x90008: the word stop), nofault (the held
job completes), replay3 (three replays: a cell's third triangle fails), kregrefuse (kregnow refused).
"""
import glob
import gzip
import os
import re
import shutil
import struct
import subprocess
import sys
import time

DATA = "/Users/jtorra/src/resgx545-data"
MAIN = "/Users/jtorra/src/resgx545"
R6H = DATA + "/render/closing-r6-held/out/20261112-154536/q"
E826 = DATA + "/render/closing-r3k-pixel/out/20261110-193547/k-bif"
E088 = DATA + "/usse/quad-lock/usse-quad-lock-counter"
P = "gma500 0000:00:02.0: [drm] "
FAULT_LINE = P + "*ERROR* sgxfive: BIF fault 0x%x at 0x%08x (PD 0x5dbf000) stalls job %d, recovering"
HELD_LINE = P + "sgxfive: job %d hung, recovery held (debugfs hold_recovery)"
HUNG_LINE = P + "*ERROR* sgxfive: job %d hung, recovering"
RESET = [P + "SGX stopped, 0 events seen", P + "SGX reset: BIF_FAULT 0x0 BIF_INT_STAT 0x80000 EVENT_STATUS 0x20000000/0x480",
         P + "SGX reset: after the fault clear BIF_FAULT 0x0 BIF_INT_STAT 0x80000", P + "SGX boot: kicking the EDM"]
UP = [P + "SGX boot: EDM up after 155 us", P + "reg 0x008 = 0x00000078", P + "reg 0xc04 = 0x00080000", P + "reg 0xc08 = 0x00000000"]


def timed_out(word):
    return [P + "*ERROR* SGX boot: no INIT_COMPLETE after 500 ms", P + "reg 0x008 = 0x000ccff8", P + "reg 0xc04 = 0x000d0004",
            P + "reg 0xc08 = 0x%08x" % ((word & ~0xf) & 0xffffffff), P + "*ERROR* SGX recovery failed: -110",
            P + "sgxfive: render context cleanup failed, resetting"]


# the pages of the kept faults by size (E507, E729, E789, E848), typed by hand; 128 x 528 is the fork's layout (side 64)
PAGES = {(640, 480): 0x2000a, (288, 144): 0x20006, (256, 288): 0x20006, (320, 400): 0x20008, (384, 384): 0x20008,
         (128, 528): 0x20009, (512, 256): 0x20006}


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
    m = re.findall(r"resgx545 case (\S+) ", open(os.environ["KMSG"]).read())
    return m[-1] if m else ""


def opt(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        return argv[i + 1] if i + 1 < len(argv) else default
    return default


def times_out(world, page, size, clr=0, held_s=0.0):
    """Whether the first boot after a fault of this page and size times out, in this world."""
    if world == "size":
        return size == (288, 144)
    t = 0x20006 <= page <= 0x20008 or (world == "ctl640" and page == 0x2000a)
    if world == "clr" and clr >= 2:
        return False
    if world == "time" and held_s >= float(os.environ.get("FAKE_LONG_S", "6")):
        return False
    return t


def boot(world, timeout, word):
    """The kernel's lines of one recovery: the reset, a boot; if it times out, the dump, -110, the cleanup reset and a second boot."""
    if not timeout:
        return RESET + UP
    second = timed_out(word) if world == "dead" else UP
    return RESET + timed_out(word) + RESET + second


# ---- the fake kernel's debugfs writes (called by the sudo shim) ---------------------------------------------------------------
def reset():
    F, world = os.environ["FAKE_DIR"], os.environ.get("FAKE_WORLD", "model")
    st = rd(F, "state", "idle")
    to = False
    if st != "idle" and rd(F, "job"):
        w, h, page, t0 = rd(F, "job").split()
        to = times_out(world, int(page, 0), (int(w), int(h)), int(rd(F, "clr", "0") or 0), time.time() - float(t0))
        word = int(st.split()[1], 0)
    else:
        word = 0
    klog(boot(world, to, word))
    wr(F, "state", "idle")
    wr(F, "list", 1)
    wr(F, "bifctrl", 0)
    return 1 if to else 0


def kregnow(value):
    F, world = os.environ["FAKE_DIR"], os.environ.get("FAKE_WORLD", "model")
    if value != "0x0c00^=0x10" or world == "kregrefuse":
        sys.stderr.write("tee: kregnow: Device or resource busy\n")
        return 1
    old = int(rd(F, "bifctrl", "0") or 0, 0)
    new = old ^ 0x10
    wr(F, "bifctrl", "0x%x" % new)
    st = rd(F, "state", "idle")
    if st == "idle":
        i, f = 0x80000, 0
    else:
        s = st.split()
        i, f = (0, 0) if new & 0x10 else (int(s[0], 0), int(s[1], 0))
        wr(F, "clr", int(rd(F, "clr", "0") or 0) + 1)
    klog([P + "sgxfive: kregnow 0x0c00: 0x%08x -> 0x%08x, reads 0x%08x, BIF_INT_STAT 0x%08x BIF_FAULT 0x%08x" % (old, new, new, i, f)])
    return 0


# ---- the fake tool --------------------------------------------------------------------------------------------------------------
def lock_words():
    """{word: (op, mutex)} of lock and release #0 to #3, assembled by usse-asm (the mock's plumbing)."""
    src = "".join("lock #%d\nrelease #%d\n" % (k, k) for k in range(4))
    r = subprocess.run([MAIN + "/tools/usse-asm/usse-asm", "-l", "-o", "/dev/null", "-"], input=src, capture_output=True, text=True)
    out = {}
    for m in re.finditer(r"0x([0-9A-F]{16})\s+(lock|release) #(\d)", r.stdout):
        out[int(m.group(1), 16)] = (m.group(2), int(m.group(3)))
    if len(out) != 8:
        raise SystemExit("usse-asm did not give the lock words: %s" % r.stderr)
    return out


def run_program(path, mode):
    """(hung, count) of E088's counter program at path over 512 quads, serial, as `mode` says a re-lock behaves."""
    b = open(path, "rb").read()
    lw = lock_words()
    ops = [lw[w] for w in struct.unpack("<%dQ" % (len(b) // 8), b) if w in lw]
    nadd = 0
    held = {}                      # mutex: count held by the quad running now (or left by an earlier one: -1)
    for _q in range(512):
        added = False
        mine = {}
        # the ops before the add are the locks, the rest the releases (E088's template: OP is lock... add ... release...)
        for op, k in ops:
            if op == "lock":
                if held.get(k, 0) and not mine.get(k):
                    return True, nadd           # held by an earlier quad that never released it
                if mine.get(k):
                    if mode == "self":
                        return True, nadd
                    mine[k] = mine[k] + 1 if mode == "recount" else 1
                else:
                    mine[k] = 1
                held[k] = 1
            else:
                if not added:
                    nadd += 1
                    added = True
                if mine.get(k):
                    mine[k] -= 1 if mode == "recount" else mine[k]
                    if mine[k] == 0:
                        held[k] = 0
        if not added:
            nadd += 1
        for k, n in mine.items():
            if n:
                held[k] = 1                     # left held: the next quad's lock of k blocks
    return False, nadd


def tool(argv):
    F, world = os.environ["FAKE_DIR"], os.environ.get("FAKE_WORLD", "model")
    R = os.environ["FAKE_DBGREAL"]
    with open(os.environ.get("FAKE_LOG", os.devnull), "a") as f:
        f.write(" ".join(argv) + "\n")
    time.sleep(float(os.environ.get("FAKE_SLOW_START", "0") or 0))
    marker = latest_marker()
    jobno = 100 + len(open(os.environ["KMSG"]).read().splitlines())
    lst = int(rd(F, "list", "1") or 1)
    wr(F, "list", lst + 1)
    rgn = int(open(os.path.join(R, "render_rgn_arrays")).read().strip() or "0", 0)
    rc = 0
    if argv[:1] == ["fill"]:
        print("fill: 64x32 0xff203040\ndiff: 0 of 2048 pixels")
    elif argv[:1] == ["tri"] and "--tri-full" not in argv:
        p = rd(F, "pending")
        if p:
            word, n, w, h = (int(x, 0) for x in p.split())
            wr(F, "pending", "0x%08x %d %d %d" % (word, n - 1, w, h)) if n > 1 else os.remove(os.path.join(F, "pending"))
            rw = (word & ~0xf) | lst
            stat = 0x90008 if world == "word" else 0x90004
            klog([FAULT_LINE % (stat, rw, jobno)] + boot(world, times_out(world, word >> 12, (w, h)), rw))
            print("tri: render context for targets up to 64x64\njob: failed: job faulted, context lost (Input/output error)")
            rc = 1
        else:
            print("tri: render context for targets up to 64x64\njob: ok\ndiff: 0 of 4096 pixels\ntri: 1 renders ok")
    elif argv[:1] == ["tri"]:
        w, h = int(opt(argv, "--width", "0")), int(opt(argv, "--height", "0"))
        mw, mh = int(opt(argv, "--max-width", "0")), int(opt(argv, "--max-height", "0"))
        forced = "cmd:1=0xe0000000" in argv and rgn == 1 and (mw, mh) == (w, h) and "--aa4" not in argv
        if forced and world != "nofault":
            page = PAGES.get((w, h), 0x2000f)
            word = (page << 12) | 0x060 | lst
            wr(F, "state", "0x90004 0x%08x 0x480 0x20000000" % word)
            wr(F, "job", "%d %d 0x%05x %f" % (w, h, page, time.time()))
            wr(F, "clr", 0)
            wr(F, "pending", "0x%08x %d %d %d" % (word, 3 if world == "replay3" else 1, w, h))
            held = rd(F, "hold") == "Y"
            klog([FAULT_LINE % (0x90004, word, jobno)] + ([HELD_LINE % jobno] if held else []))
            wr(F, "answered", marker)
            if held:
                for _ in range(900):                   # the job waits for the kernel's recovery (the reset), bounded
                    if rd(F, "state") == "idle":
                        break
                    time.sleep(0.05)
            else:
                klog(boot(world, times_out(world, page, (w, h)), word))
                wr(F, "state", "idle")
            print("tri: render context for targets up to %dx%d\njob: failed: job faulted, context lost (Input/output error)" % (mw, mh))
            return 1
        print("tri: render context for targets up to %dx%d\njob: ok\ndiff: 0 of %d pixels\ntri: 1 renders ok" % (mw, mh, w * h))
    elif argv[:1] == ["probe"] and argv[1:4] == ["--temps", "32", "--pixels"] and len(argv) == 5:
        path = argv[4]
        name = os.path.basename(path)[:-4]
        if not os.path.exists(path):
            print("probe %s: failed: %s: No such file or directory" % (name, path))
            rc = 1
        else:
            hung, n = run_program(path, os.environ.get("FAKE_LOCK", "self"))
            print("probe %s: scratch at 0x3e003000 (64 KiB)" % name)
            if hung:
                klog([HUNG_LINE % jobno] + RESET + UP)
                print("probe %s: failed: job hung, context lost (Connection timed out)" % name)
                print("probe %s: scratch +0x000 0x%08x" % (name, 0xd0000000 + n) if n else "probe %s: scratch unchanged" % name)
                rc = 3
            else:
                print("probe %s: o0 mixed 0xd0000001 x4 0xd0000002 x4 0xd0000003 x4 0xd0000004 x4 other x2032" % name)
                print("probe %s: scratch +0x000 0x%08x" % (name, 0xd0000000 + n))
    else:
        print("sgxfive-test: unknown command %s" % " ".join(argv))
        rc = 2
    wr(F, "answered", marker)
    return rc


# ---- fixtures from kept files ---------------------------------------------------------------------------------------------------
COLS = "name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tmode\tfault_req\treset_rc\theld_msg"


def _cp(src, dst):
    if os.path.exists(src):
        shutil.copy(src, dst)


def r6held(dst, maps, stage="d"):
    """r6-held's kept q cells as this session's held cells: NAME.snap1.regs -> NAME.regs, step snaps snapK -> NAME.K.regs; steps kept
    as they are (t1..t3); the fill follow-up dropped (this session has none)."""
    os.makedirs(dst, exist_ok=True)
    rows = [COLS]
    lines = open(os.path.join(R6H, "cases.tsv")).read().splitlines()
    cols = lines[0].split("\t")
    for src, ours in maps.items():
        for ln in lines[1:]:
            f = dict(zip(cols, ln.split("\t")))
            nm = f["name"]
            if nm != src and not nm.startswith(src + "."):
                continue
            stp = nm[len(src) + 1:]
            if stp == "fill":
                continue
            f["name"] = ours + ("." + stp if stp else "")
            f["stage"] = stage
            rows.append("\t".join(f[c] for c in cols))
            base = os.path.join(R6H, nm)
            o = os.path.join(dst, f["name"])
            _cp(base + ".txt.gz", o + ".txt.gz")
            _cp(base + ".dmesg.gz", o + ".dmesg.gz")
            if stp:
                _cp(os.path.join(R6H, "%s.snap%s.regs.gz" % (src, stp)), o + ".regs.gz")
            else:
                _cp(base + ".snap1.regs.gz", o + ".regs.gz")
    open(os.path.join(dst, "cases.tsv"), "w").write("\n".join(rows) + "\n")
    return dst


def e826(dst, maps, stage="m"):
    """E826's k-bif rows: n0-idle as the gate row (its two 0x0c00 lines; set/clear statuses from its kw.txt), f2-ta-write as a clr
    cell (its four kregnow lines, of which the scorer reads the two 0x0c00 ones; snap 1 as NAME.regs)."""
    os.makedirs(dst, exist_ok=True)
    rows = [COLS]
    for src, ours in maps.items():
        o = os.path.join(dst, ours)
        _cp(os.path.join(E826, src + ".dmesg.gz"), o + ".dmesg.gz")
        _cp(os.path.join(E826, src + ".snap1.regs.gz" if src != "n0-idle" else src + ".snapb5.regs.gz"), o + ".regs.gz")
        if src == "n0-idle":
            kw = gzip.open(os.path.join(E826, src + ".kw.txt.gz"), "rt").read()
            st = re.findall(r"^\d 0x0c00\^=0x10 rc (\d+)$", kw, re.M)
            gzip.open(o + ".txt.gz", "wt").write("set rc %s\nclear rc %s\n" % tuple(st[:2]))
            rows.append("%s\t%s\tcontrol\tsafe\tgate\t-\t-\t0\tok\tgate\t-\t-\tno" % (ours, stage))
        else:
            _cp(os.path.join(E826, src + ".txt.gz"), o + ".txt.gz")
            rows.append("%s\t%s\theldout\trisky\theld rgn:1 clr\t-\t-\t1\tfault\theld\t4\t0\tyes" % (ours, stage))
    if any(s == "n0-idle" for s in maps):
        _cp(os.path.join(E826, "begin.health1.txt.gz"), os.path.join(dst, "c1-tri.txt.gz"))
        gzip.open(os.path.join(dst, "c1-tri.dmesg.gz"), "wt").write("")
        _cp(os.path.join(E826, "n0-idle.snap0.regs.gz"), os.path.join(dst, "c1-tri.regs.gz"))
        rows.append("c1-tri\t%s\tcontrol\tsafe\texpectdiff\t-\ttri --keep-going\t0\tok\tplain\t-\t-\tno" % stage)
    open(os.path.join(dst, "cases.tsv"), "w").write("\n".join(rows) + "\n")
    return dst


def e088(dst, maps, stage="l"):
    """E088's raw.txt split by its probe-case lines: usse-quad-lock-counter__N's output as our row (its probe lines renamed);
    the class as the runner gives it (ok with a scratch line, hang with 'failed: job hung')."""
    os.makedirs(dst, exist_ok=True)
    raw = open(os.path.join(E088, "raw.txt")).read()
    parts = re.split(r"^probe-case (\S+)\n", raw, flags=re.M)
    out = dict(zip(parts[1::2], parts[2::2]))
    rows = [COLS]
    for src, ours in maps.items():
        text = out[src].replace("probe %s:" % src, "probe %s:" % ours)
        o = os.path.join(dst, ours)
        gzip.open(o + ".txt.gz", "wt").write(text)
        hung = "failed: job hung" in text
        gzip.open(o + ".dmesg.gz", "wt").write(HUNG_LINE % 101 + "\n" if hung else "")
        gzip.open(o + ".regs.gz", "wt").write("sgxfive regs 1\nreg 0x0c04 0x00080000\n")
        rows.append("%s\t%s\tcontrol\trisky\tprobe\t-\t-\t%d\t%s\tprobe\t-\t-\tno" % (ours, stage, 3 if hung else 0,
                                                                                  "hang" if hung else "ok"))
    open(os.path.join(dst, "cases.tsv"), "w").write("\n".join(rows) + "\n")
    return dst


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "tool":
        sys.exit(tool(sys.argv[2:]))
    if cmd == "reset":
        sys.exit(reset())
    if cmd == "kregnow":
        sys.exit(kregnow(sys.argv[2]))
    if cmd in ("r6held", "e826", "e088"):
        globals()[cmd](sys.argv[2], dict(a.split("=") for a in sys.argv[3:]))
        sys.exit(0)
    print(__doc__)
    sys.exit(2)
