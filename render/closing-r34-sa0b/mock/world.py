# SPDX-License-Identifier: MIT
"""mock/world.py: r34-sa0b's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv, the world's tokens and the fake laptop's state (its reset count and this
world's own state files in FAKE_DIR), never a case name; it returns dict(rc, out, err, kmsg, latch)
or a refusal (usage, rc 2). As strict as the tools on this session's rows: t30 `probe [--temps N]
[--pixels] [--scratch-show N] FILE` with FILE one of bins/ (a plain fill: no --coords), and t10's
bare `fill` and `tri` (the health pair and the X rows alike, so they count as jobs here too).

The program is known from FILE's base name only: `w-MMMMMMMM` writes marker M to sa0 and outputs
K1, `r` reads sa0 (o0 = sa0, E496's form), `p` reads pa0 (o0 = pa0), `k` outputs K3. The state kept in
FAKE_DIR: the last job's output (r34s_last: a multiset, or `tri`), the sa0 value last written and
the jobs since (r34s_sa0), and the reset count at that write. The t10 texts are r34-q010's kept
health pair (mock/kept, written by gen/make.py from the pinned data).

Worlds (EXPECT: the driver's status and the stage's runner status):
  onejob    H-ONEJOB: sa0 is read by the next job only (across a reset); pa0, and sa0 after any
            job between, read the colour the job before output                        0
  persist   H-PERSIST: sa0 keeps the marker whatever runs                              0
  colour    H-COLOUR: sa0 never persists (reads the colour the job before output)      0
  resetclr  H-RESET with H-ONEJOB: a reset after the write gives 0 in sa0              0
  fixed     H-FIXED: pa0 reads the tri mixture whatever ran before                     0
  odd       H-ONEJOB, and every writer's o0 shows 4 pixels of its marker (E484's odd pixels): 0
  wbad      the writer's in-job readback reads 0 (every W control FAILED)              0
  noread    the third reader prints no o0 line: hook_check stops s (24), the session ends
  nofill    the X fills print `fill: FAIL` (the health fill before them passes): 24
  fault     the first writer faults (no expectfault): s 4, the session stops
  hang      the first reader hangs (no expectfault): s 4
  model     = onejob (the kit's default world name)
"""
import os
import re

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECT = {
    "onejob": (0, {"s": 0}),
    "persist": (0, {"s": 0}),
    "colour": (0, {"s": 0}),
    "resetclr": (0, {"s": 0}),
    "fixed": (0, {"s": 0}),
    "odd": (0, {"s": 0}),
    "wbad": (0, {"s": 0}),
    "noread": (24, {"s": 24}),
    "nofill": (24, {"s": 24}),
    "fault": (4, {"s": 4}),
    "hang": (4, {"s": 4}),
    "model": (0, {"s": 0}),
}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
NPIX = 2048


def constants():
    out = {}
    for ln in open(os.path.join(KP, "gen", "constants.txt")).read().splitlines():
        k, _, v = ln.partition("=")
        out[k] = v
    return out


C = constants()
K1, K2, K3, K4 = (int(C[k], 16) for k in ("K1", "K2", "K3", "K4"))
TRI = [int(v, 16) for v in C["TRI"].split(",")]
TRI_MIX = {TRI[0]: 1536, TRI[1]: 512}               # E496's first job (the counts are the mock's)


def kept(name):
    return open(os.path.join(KP, "mock", "kept", name)).read()


def get(name, default=""):
    d = os.environ.get("FAKE_DIR")
    p = os.path.join(d, name) if d else None
    return open(p).read().strip() if p and os.path.exists(p) else default


def put(name, value):
    d = os.environ.get("FAKE_DIR")
    if d:
        with open(os.path.join(d, name), "w") as f:
            f.write(str(value))


def resets():
    d = os.environ.get("FAKE_DIR")
    p = os.path.join(d, "writes") if d else None
    return sum(1 for ln in open(p) if ln.startswith("reset")) if p and os.path.exists(p) else 0


def enc(ms):
    return "tri" if ms == "tri" else " ".join("%08x:%d" % kv for kv in ms.items())


def dec(s):
    if s == "tri":
        return dict(TRI_MIX)
    return {int(v, 16): int(n) for v, n in (w.split(":") for w in s.split())} if s else {0: NPIX}


def count(name):
    n = int(get(name, "0")) + 1
    put(name, n)
    return n


def o0_line(name, ms):
    items = sorted(ms.items(), key=lambda kv: -kv[1])
    if len(items) == 1:
        return "probe %s: o0 0x%08x (%d of %d)" % (name, items[0][0], items[0][1], NPIX)
    return "probe %s: o0 mixed " % name + " ".join("0x%08x x%d" % kv for kv in items[:4])


def sa0_read(world, last):
    """What a reader's sa0 holds now (a multiset)."""
    m, since, at = (get("r34s_sa0", "-1 99 -1").split() + ["-1"])[:3]
    m, since, at = int(m, 16) if m != "-1" else None, int(since), int(at)
    if m is None or "colour" in world:
        return dec(last)
    if "resetclr" in world and resets() != at:
        return {0: NPIX}
    if "persist" in world or since == 0:
        return {m: NPIX}
    return dec(last)


def probe(argv, world):
    i, path = 1, None
    while i < len(argv):
        a = argv[i]
        if a in ("--temps", "--scratch-show") and i + 1 < len(argv) and argv[i + 1].isdigit():
            lim = (1, 128) if a == "--temps" else (1, 64)
            if not lim[0] <= int(argv[i + 1]) <= lim[1]:
                return USAGE
            i += 2
        elif a == "--pixels":
            i += 1
        elif a.startswith("--") or path is not None:
            return USAGE
        else:
            path = a
            i += 1
    if path is None:
        return USAGE
    if not os.path.isfile(path):
        return dict(rc=2, err="sgxfive-test: %s: No such file or directory\n" % path)
    size = os.path.getsize(path)
    if not size or size % 8 or size > 256 * 8:
        return dict(rc=2, err="sgxfive-test: %s: not 1 to 256 USSE words\n" % path)
    name = os.path.basename(path).split(".")[0]
    w = re.fullmatch(r"w-([0-9a-f]{8})", name)
    if not w and name not in ("r", "p", "k"):
        return USAGE
    last = get("r34s_last", "")
    head = ["programs asm", "probe %s: scratch at 0x3e003000 (64 KiB)" % name,
            "probe %s: job time: 640 us" % name]
    if w:
        m = int(w.group(1), 16)
        if "fault" in world and count("r34s_w") == 1:
            return dict(rc=3, out="\n".join(head + ["probe %s: failed: job faulted, context lost "
                                                    "(Input/output error)" % name]) + "\n",
                        kmsg=["sgxfive: BIF fault 0x80020 at 0x3e003001 (PD 0x5736000) stalls "
                              "job 7, recovering"], latch=(0x1000, 0x3E003001))
        out_ms = {K1: NPIX - 4, m: 4} if "odd" in world else {K1: NPIX}
        put("r34s_sa0", "%08x 0 %d" % (m, resets()))
        put("r34s_last", enc(out_ms))
        dw0 = 0 if "wbad" in world else m
        return dict(out="\n".join(head + [o0_line(name, out_ms),
                                          "probe %s: scratch +0x000 0x%08x" % (name, dw0)]) + "\n")
    if name == "k":
        bump()
        put("r34s_last", enc({K3: NPIX}))
        return dict(out="\n".join(head + [o0_line(name, {K3: NPIX}),
                                          "probe %s: scratch +0x000 0x%08x" % (name, K3)]) + "\n")
    if name == "r":
        n = count("r34s_r")
        if "hang" in world and n == 1:
            return dict(rc=3, out="\n".join(head + ["probe r: failed: job hung, context lost "
                                                    "(Connection timed out)"]) + "\n",
                        kmsg=["sgxfive: job 12 hung, recovering"])
        sa = sa0_read(world, last)
        bump()
        ms = {v ^ K2: c for v, c in sa.items()}
        put("r34s_last", enc(ms))
        lines = [o0_line(name, ms)] if not ("noread" in world and n == 3) else []
        return dict(out="\n".join(head + lines + ["probe r: scratch +0x000 0x%08x"
                                                  % max(sa, key=sa.get)]) + "\n")
    pa = dict(TRI_MIX) if "fixed" in world else dec(last)
    bump()
    ms = {v ^ K4: c for v, c in pa.items()}
    put("r34s_last", enc(ms))
    return dict(out="\n".join(head + [o0_line(name, ms), "probe p: scratch +0x000 0x%08x"
                                      % max(pa, key=pa.get)]) + "\n")


def bump():
    """A job that writes no sa0: the jobs since the write grow by one."""
    s = get("r34s_sa0", "")
    if s:
        m, since, at = s.split()
        put("r34s_sa0", f"{m} {int(since) + 1} {at}")


def health(argv, world):
    job = argv[0]
    bump()
    if job == "tri":
        put("r34s_last", "tri")
        return dict(out=kept("tri.txt"))
    put("r34s_last", enc({int(C["FILL"], 16): NPIX}))
    text = kept("fill.txt")
    if "nofill" in world and count("r34s_fill") > 1:          # the stage-begin health's passes
        text = text.replace("fill: ok", "fill: FAIL")
    return dict(out=text)


def answer(tool, argv, world):
    if tool == "t10" and argv in (["fill"], ["tri"]):
        return health(argv, world)
    if tool == "t30" and argv and argv[0] == "probe":
        return probe(argv, world)
    return USAGE
