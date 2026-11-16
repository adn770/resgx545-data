# SPDX-License-Identifier: MIT
"""mock/world.py: r34-q010's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv, the world's tokens and the fake laptop's state (its reset count and this
world's own state file in FAKE_DIR), never a case name; it returns dict(rc, out, err, kmsg, latch)
or a refusal (usage, rc 2). As strict as the tools for this session's rows: t30 `copy
--every-value --pixels [--poke tex:N[^]=V | xfer:N[^]=V]...` and t10's bare `fill` and `tri` (the
health pair and the X rows alike, so a world's clearing job also runs in the kit's health).

The colour-space set is kept in FAKE_DIR (r34q_csc: bt601, zeros or other; zeros after boot): a
copy whose xfer:17 bit 0 is set loads its five words, a copy without it reads the set (the kept
r29-flag2 texts: q010-pre's for BT.601, q010-af's for zeros). The world decides which job clears
it (to zeros); the idle words are not visible to the mock (IDLE_WAIT 0), so H-IDLE has no world.

Worlds (EXPECT: the driver's status and the stage's runner status):
  fill      H-FILL: the t10 fill clears (the health fill too)                         0
  tri       H-TRI: the t10 triangle clears                                             0
  both      H-BOTH: either clears                                                      0
  none      H-NONE: nothing clears                                                     0
  copyclr   H-COPYNL with H-FILL: the plain copy clears too                            0
  resetclr  a debugfs reset clears the set (T0's controls fail: every row cannot tell) 0
  noread    a copy without its target line: hook_check stops c (24), the session ends
  nojob     an X fill that does not print `fill: ok`: hook_check stops c (24)
  fault     a load copy faults (no expectfault): c 4, the session stops
  hang      the t10 triangle row hangs (no expectfault): c 4
  model     = fill (the kit's default world name)
"""
import gzip
import os
import re

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECT = {
    "fill": (0, {"c": 0}),
    "tri": (0, {"c": 0}),
    "both": (0, {"c": 0}),
    "none": (0, {"c": 0}),
    "copyclr": (0, {"c": 0}),
    "resetclr": (0, {"c": 0}),
    "noread": (24, {"c": 24}),
    "nojob": (24, {"c": 24}),
    "fault": (4, {"c": 4}),
    "hang": (4, {"c": 4}),
    "model": (0, {"c": 0}),
}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
BT601 = (0x00950095, 0x00000095, 0x010203CE, 0x039800CC, 0)
SPEC = re.compile(r"^(xfer|tex):(\d+)(\^?)=(0x[0-9a-fA-F]+|\d+)$")


def kept(name):
    with open(os.path.join(KP, "mock", "kept", name), "rb") as f:
        return gzip.decompress(f.read()).decode()


def state(name, default):
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


def csc():
    """The set now: a reset since the last load clears it in the resetclr world."""
    cur, at = (state("r34q_csc", "zeros -1").split() + ["-1"])[:2]
    return cur, int(at)


def clears(world, job):
    """Whether JOB (fill, tri, copy: the plain copy) clears the set in this world."""
    kind = "tri" if "tri" in world else "both" if "both" in world else \
        "none" if world & {"none", "resetclr"} else "fill"
    if job == "copy":
        return "copyclr" in world
    return kind == "both" and job in ("fill", "tri") or kind == job


def fault(head):
    return dict(rc=3, out=head + "job: failed: job faulted, context lost (Input/output error)\n",
                kmsg=["sgxfive: BIF fault 0x80020 at 0x3e002001 (PD 0x5736000) stalls job 7, recovering"],
                latch=(0x1000, 0x3E002001))


def copy(argv, world):
    o, i = {}, 1
    while i < len(argv):
        a = argv[i]
        if a in ("--every-value", "--pixels"):
            o.setdefault(a, True)
            i += 1
        elif a == "--poke" and i + 1 < len(argv) and SPEC.match(argv[i + 1]):
            o.setdefault("--poke", []).append(argv[i + 1])
            i += 2
        else:
            return USAGE
    if "--every-value" not in o:
        return USAGE
    w = {}
    for s in o.get("--poke", []):
        m = SPEC.match(s)
        w[(m[1], int(m[2]))] = int(m[4], 0)
    if not w:                                               # the plain copy (T3's X): exact
        if clears(world, "copy"):
            put("r34q_csc", f"zeros {resets()}")
        return dict(out="programs asm\njob: ok\njob time: 410 us\ntarget: 64x32 hash 0x5f0c2b1d9e8a7c31\n"
                    "diff: 0 of 2048 pixels\noutside: 0 dwords\ncopy: ok\n")
    if w.get(("tex", 1)) != 0x7D03F01F or w.get(("tex", 0)) != 0x90:
        return USAGE
    cur, at = csc()
    if "resetclr" in world and resets() != at:
        cur = "zeros"
    if w.get(("xfer", 17), 0) & 1:
        words = tuple(w.get(("xfer", k), 0) for k in range(18, 23))
        if "fault" in world:
            return fault("")
        cur = "bt601" if words == BT601 else "zeros" if not any(words) else "other"
        put("r34q_csc", f"{cur} {resets()}")
        return dict(rc=1, out=kept("load.txt.gz") if cur == "bt601" else kept("zeros.txt.gz"))
    text = kept("bt601.txt.gz") if cur == "bt601" else kept("zeros.txt.gz")
    if "noread" in world:
        text = "\n".join(ln for ln in text.splitlines() if not ln.startswith("target:")) + "\n"
    return dict(rc=1, out=text)


def health(argv, world):
    job = argv[0]
    if clears(world, job):
        put("r34q_csc", f"zeros {resets()}")
    if job == "tri" and "hang" in world and state("r34q_tri", "0") == "1":
        put("r34q_tri", "hung")                             # once: the recovery's health draws
        return dict(rc=3, out="tri: render context for targets up to 64x64\n"
                    "job: failed: job hung, context lost (Connection timed out)\n",
                    kmsg=["sgxfive: job 12 hung, recovering"])
    if job == "tri" and state("r34q_tri", "0") == "0":
        put("r34q_tri", "1")                                # the first is the stage-begin health's
    text = kept("fill.txt.gz" if job == "fill" else "tri.txt.gz")
    if job == "fill" and "nojob" in world and state("r34q_fill", "0") != "0":
        text = text.replace("fill: ok", "fill: FAIL")
    if job == "fill":
        put("r34q_fill", int(state("r34q_fill", "0")) + 1)
    return dict(out=text)


def answer(tool, argv, world):
    if tool == "t10" and argv in (["fill"], ["tri"]):
        return health(argv, world)
    if tool == "t30" and argv and argv[0] == "copy":
        return copy(argv, world)
    return USAGE
