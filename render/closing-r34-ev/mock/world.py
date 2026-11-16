# SPDX-License-Identifier: MIT
"""mock/world.py: r34-ev's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name (nor the row's knob: every probe
answers as the 0x422 row, rc 0, which an expect:rc3-overflow row also takes as completed);
timeline() gives regtimeline's samples of the wrapped job, interval_ns() its spacing.
EXPECT: {world: (the driver's status, {stage: the runner's status})}.

t10's one form, the overflow probe (`probe --tri pixel --width 3072 --height 2048 --vertices 1500
BIN`, r13-dpm's kept text), t30's two copies (plain `copy` and the 256 x 256 one, E547's kept copy
text), and the kit's health pair. Timelines: 0x012c 0x20000000 with bit 1 (0x20000002) and bit 18
pulses in a probe and bit 14 with 31 in a copy (E547); 0x0118 0x400 (a probe: one bit 12 pulse);
0x0748 0x1f with bit 4 clear for a long run and bits 0-3 for short ones; 0x0660 0x2 then 0x70305
(r13-dpm). The kit's fake snapshots have no 0x012c, 0x0118 or 0x0660, so the @snap0 controls
cannot tell in the mock; a gate opens on the calibration (no control FAILED, a window per form).

Worlds: model (every stage runs, 0); slow748 (0x0660 + 0x0748 sampled every 5000 ns: d1's gate
stays shut, D1_MAX_NS); noimg (the probe prints no image line: e0, e2c and d0 stop at their first
row, 24, and e1, e2, d1 are skipped: their calibrations have one probe row); nocopy (a copy
without its `copy: ok` line: e0 and e2c stop at their first copy, 24, e1 and e2 are skipped, d0
and d1 run)."""
EXPECT = {"model": (0, {"e0": 0, "e1": 0, "e2c": 0, "e2": 0, "d0": 0, "d1": 0}),
          "slow748": (0, {"e0": 0, "e1": 0, "e2c": 0, "e2": 0, "d0": 0}),
          "noimg": (0, {"e0": 24, "e2c": 24, "d0": 24}),
          "nocopy": (0, {"e0": 24, "e2c": 24, "d0": 0, "d1": 0})}
PROBE = ["probe", "--tri", "pixel", "--width", "3072", "--height", "2048", "--vertices", "1500"]
COPY = ["copy"]
LCOPY = ["copy", "--width", "256", "--height", "256", "--src-stride", "1024", "--dst-stride",
         "1024"]
N = 4000


def kind(argv):
    if argv[:9] == PROBE and len(argv) == 10 and argv[9].endswith("/bins/p1139-green.bin"):
        return "ovf"
    if argv == COPY:
        return "copy"
    if argv == LCOPY:
        return "lcopy"
    return None


def answer(tool, argv, world):
    if tool == "rt" or argv in (["fill"], ["tri"]):
        return None             # the wrapped job (then timeline()), or the kit's health pair
    k = kind(argv)
    if k == "ovf" and tool == "t10":
        out = ("programs asm\nprobe p1139-green: scratch at 0x3f80a000 (64 KiB)\n"
               "probe p1139-green: tri 3072x2048 (1500 vertices), pixel replaced\n"
               "probe p1139-green: scratch unchanged\n")
        if "noimg" not in world:
            out += "probe p1139-green: o0 mixed 0xff203040 x4542751 0xff00ff00 x1748705\n"
        return dict(out=out)
    if k in ("copy", "lcopy") and tool == "t30":
        w, h = (64, 32) if k == "copy" else (256, 256)
        out = ("programs asm\njob: ok\njob time: 374 us\ntarget: %dx%d hash 0x9b1c0be484ac0d25\n"
               "diff: 0 of %d pixels\noutside: 0 dwords\n" % (w, h, w * h))
        if "nocopy" not in world:
            out += "copy: ok, %dx%d from (0, 0) to (0, 0)\n" % (w, h)
        return dict(out=out)
    return None                 # a refusal: usage, rc 2


def interval_ns(tool, regs, argv, rc, world):
    if 0x0748 in regs:
        return 5000 if "slow748" in world else 2300
    return 1100 if 0x0118 in regs else 600


def timeline(tool, regs, argv, rc, world):
    k = kind(argv)
    if k is None:
        return None
    rows = []
    for i in range(N):
        v = {0x012c: 0x20000000, 0x0118: 0x400, 0x0748: 0x1f,
             0x0660: 0x2 if i < 100 else 0x70305}
        if k == "ovf":
            if 1000 <= i < 1010:
                v[0x012c] |= 0x2
            if i in (1500, 2500):
                v[0x012c] |= 1 << 18
            if 1200 <= i < 1203:
                v[0x0118] |= 1 << 12
            if 50 <= i < 3000:
                v[0x0748] &= ~0x10
            if i % 200 == 7:
                v[0x0748] &= ~0x1
            if i % 500 == 9:
                v[0x0748] &= ~0x2
            if i % 700 == 11:
                v[0x0748] &= ~0x8
        elif 2000 <= i < 2040:
            v[0x012c] |= 0x80004000
        rows.append([v.get(r, 0) for r in regs])
    return rows
