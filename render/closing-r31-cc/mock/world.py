# SPDX-License-Identifier: MIT
"""mock/world.py: r31-cc's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name; timeline() gives regtimeline's
samples of the wrapped job. EXPECT: {world: (the driver's status, {stage: the runner's status})}.

t10's two forms as the session runs them, nothing else: `tri --width 64 --height 64` (per render
`job: ok`, `target:`, `diff: 0 of 4096 pixels`, `outside:`, the count line and `tri 64x64 #1: T
us`, then `tri: 1 renders ok`, E547's kept tri64 text) and the bare `fill` (the kit's kept health
fill text: `job: ok`, `diff: 0 of 2048 pixels`, `fill: ok, 64x32 ...`), which is also the health
fill. regtimeline's samples (the kit's fake prints them 1 us apart with start 0 end 0): 0x012c the
idle word, then E547's tri64 order once (a fill: the idle word and SW_EVENT); 0x0804 0x0000ffff
then 0x1000ffff from the job (E1120); 0x0b14 bit 16 set and counting; 0x0c00 0; 0x0a74
0x00208200 then 0x50208200; every other register 0.

Worlds: model (every stage runs, 0); nodiff (a triangle without its diff line: c1's hook stops
it, 24, on_stop end: the session ends); notl (regtimeline prints no timeline for a row: c1 stops
at its first row, 24, end); tickstop (0x0b14 bit 16 clear in the last sample: c1 samples no
0x0b14 and runs, c2 stops, 24, end); nofillok (the fill row's text without `fill: ok`: c1 to c4
run, c5 stops, 24; the health fill reads only its diff line)."""
EXPECT = {"model": (0, {"c1": 0, "c2": 0, "c3": 0, "c4": 0, "c5": 0}),
          "nodiff": (24, {"c1": 24}),
          "notl": (24, {"c1": 24}),
          "tickstop": (24, {"c1": 0, "c2": 24}),
          "nofillok": (24, {"c1": 0, "c2": 0, "c3": 0, "c4": 0, "c5": 24})}
TRI = ["tri", "--width", "64", "--height", "64"]
FILL = ["fill"]
FORMS = (TRI, FILL)
IDLE = 0x20000000
JOB = {"tri": (0x24000000, IDLE, 0x20040001, IDLE, 0xa0004000, IDLE),
       "fill": (IDLE, 0xa0004000, IDLE)}


def tri_out(world):
    out = ("tri: render context for targets up to 64x64\n"
           "job: ok\ntarget: 64x64 hash 0x99385a04ee01c585\n")
    if "nodiff" not in world:
        out += "diff: 0 of 4096 pixels\n"
    return out + ("outside: 0 dwords\nlayout: fb 0x3e001000\n"
                  "tri 64x64 #1: 1062 triangle, 3034 background, 0 other; wrong 0 inside, "
                  "0 outside, 0 at edges; 612 if flipped; guard 0\ntri 64x64 #1: 5394 us\n"
                  "tri: 1 renders ok\n")


def fill_out(world, row):
    out = ("programs asm\njob: ok\njob time: 399 us\ntarget: 64x32 hash 0xb60c6095080bd325\n"
           "diff: 0 of 2048 pixels\noutside: 0 dwords\n")
    if not (row and "nofillok" in world):
        out += "fill: ok, 64x32 at (0, 0), stride 256, colour 0xff336699\n"
    return out


def answer(tool, argv, world):
    if tool == "rt":
        if "notl" in world and len(argv) > 5 and argv[5:] in FORMS:
            return dict(out=tri_out(world) if argv[5:] == TRI else fill_out(world, True))
        return None             # the kit's fake runs the wrapped tool, then timeline()
    if argv == FILL:
        # the health fill and the c5 rows alike (the world cannot tell them apart by the argv):
        # nofillok drops the `fill: ok` line, which only the rows' hook reads
        return dict(out=fill_out(world, True))
    if argv == ["tri"]:
        return None             # the kit's health triangle
    if argv != TRI:
        return None             # a refusal: usage, rc 2
    return dict(out=tri_out(world))


def timeline(tool, regs, argv, rc, world):
    if argv not in FORMS:
        return None
    words = [IDLE] + list(JOB[argv[0]]) + [IDLE]
    rows = []
    for i, w in enumerate(words):
        v = {0x012c: w, 0x0804: 0x1000ffff if i else 0x0000ffff, 0x0b14: 0x10000 | (0x0a00 + i),
             0x0c00: 0, 0x0a74: 0x50208200 if i > 2 else 0x00208200}
        if "tickstop" in world and i == len(words) - 1:
            v[0x0b14] = 0x0a00 + i - 1
        rows.append([v.get(r, 0) for r in regs])
    return rows
