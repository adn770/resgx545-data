# SPDX-License-Identifier: MIT
"""mock/world.py: r30-evst's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name; timeline() gives regtimeline's
samples of the wrapped job. EXPECT: {world: (the driver's status, {stage: the runner's status})}.

t10's `tri` as the session runs it (`--width 64 --height 64 [-n 3]`, nothing else): per render
`job: ok`, `target:`, `diff: 0 of 4096 pixels`, `outside:`, the count line and `tri 64x64 #i: T
us`, then `tri: N renders ok` (E547's kept tri64 text, r29-kreg's world). regtimeline's samples (the
kit's fake prints them with start 0 end 0): the idle word, then E547's tri64 order (0x24000000,
idle, 0x20040001, idle, 0xa0004000, idle) once a render; 0x0118 0x400, 0x0804 0x1000ffff, 0x0b14
bit 16 set and counting, every other register 0.

Worlds: model (every stage runs, 0); nodiff (no diff line: e1's and e5's hooks stop them, 24, the
driver goes on; e2's stops it and ends the session, 24); latch (0x0118 bit 7 in the job:
e2's hook stops it, 24, on_stop end: the session ends there); tickstop (0x0b14 bit 16 clear in the last sample: e2
stops, 24, end); notl (regtimeline prints no timeline: each
stage's hook stops it at its first row, 24, as nodiff)."""
EXPECT = {"model": (0, {"e1": 0, "e5": 0, "e2": 0, "e3": 0, "e4": 0}),
          "nodiff": (24, {"e1": 24, "e5": 24, "e2": 24}),
          "latch": (24, {"e1": 0, "e5": 0, "e2": 24}),
          "tickstop": (24, {"e1": 0, "e5": 0, "e2": 24}),
          "notl": (24, {"e1": 24, "e5": 24, "e2": 24})}
FORMS = (["tri", "--width", "64", "--height", "64"],
         ["tri", "--width", "64", "--height", "64", "-n", "3"])
IDLE = 0x20000000
JOB = (0x24000000, IDLE, 0x20040001, IDLE, 0xa0004000, IDLE)


def tri_out(n, world):
    out = "tri: render context for targets up to 64x64\n"
    for i in range(1, n + 1):
        out += "job: ok\ntarget: 64x64 hash 0x99385a04ee01c585\n"
        if "nodiff" not in world:
            out += "diff: 0 of 4096 pixels\n"
        out += ("outside: 0 dwords\nlayout: fb 0x3e001000\n"
                f"tri 64x64 #{i}: 1062 triangle, 3034 background, 0 other; wrong 0 inside, "
                f"0 outside, 0 at edges; 612 if flipped; guard 0\ntri 64x64 #{i}: 5394 us\n")
    return out + f"tri: {n} renders ok\n"


def answer(tool, argv, world):
    if tool == "rt":
        if "notl" in world and len(argv) > 5 and argv[5:] in FORMS:
            return dict(out=tri_out(3 if "-n" in argv else 1, world))
        return None             # the kit's fake runs the wrapped tool, then timeline()
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if argv not in FORMS:
        return None             # a refusal: usage, rc 2
    return dict(out=tri_out(3 if "-n" in argv else 1, world))


def timeline(tool, regs, argv, rc, world):
    if argv not in FORMS:
        return None
    n = 3 if "-n" in argv else 1
    words = [IDLE] + list(JOB) * n + [IDLE]
    rows = []
    for i, w in enumerate(words):
        v = {0x012c: w, 0x0118: 0x400, 0x0804: 0x1000ffff, 0x0b14: 0x10000 | (0x0a00 + i)}
        if "latch" in world and w == 0x24000000:
            v[0x0118] = 0x480
        if "tickstop" in world and i == len(words) - 1:
            v[0x0b14] = 0x0a00 + i - 1
        rows.append([v.get(r, 0) for r in regs])
    return rows
