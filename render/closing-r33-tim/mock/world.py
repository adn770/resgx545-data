# SPDX-License-Identifier: MIT
"""mock/world.py: r33-tim's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name; timeline() gives regtimeline's
samples of the wrapped job. EXPECT: {world: (the driver's status, {stage: the runner's status})}.

t10's one form as the session runs it, `tri --width 64 --height 64` (E547's kept tri64 text),
and the kit's health pair (bare `fill` and `tri`, the kit's own answers). regtimeline's samples
(the kit's fake: 1 us apart, TOTAL printed 0): 0x0acc counting down 399 a sample from 0x0104_0000
and reloading to 400000 (hw_spec 12.2), 0x0804 0x0000ffff then 0x1000ffff at sample 2200
(E1122), 0x012c 0x20000000 with bit 26 (0x24000000) for samples 2230 to 2235 (E1115, E1130).
The kit's fake snapshots have no 0x0acc, so ten0 and ten9 are absent in the mock (scored, not
read by the controls' premise).

Worlds: model (both stages run, 0); nodiff (a triangle without its diff line: t1 stops at its
first row, 24, on_stop end: the session ends); notl (regtimeline prints no timeline: t1 stops at
its first row, 24, end); timerstop (0x0acc reads 0, as after POWER IDLE: no stop, the controls'
ten reads 0 and the scorer fails them)."""
EXPECT = {"model": (0, {"t1": 0, "t1d": 0}),
          "nodiff": (24, {"t1": 24}),
          "notl": (24, {"t1": 24}),
          "timerstop": (0, {"t1": 0, "t1d": 0})}
TRI = ["tri", "--width", "64", "--height", "64"]
N = 3000


def tri_out(world):
    out = ("tri: render context for targets up to 64x64\n"
           "job: ok\ntarget: 64x64 hash 0x99385a04ee01c585\n")
    if "nodiff" not in world:
        out += "diff: 0 of 4096 pixels\n"
    return out + ("outside: 0 dwords\nlayout: fb 0x3e001000\n"
                  "tri 64x64 #1: 1062 triangle, 3034 background, 0 other; wrong 0 inside, "
                  "0 outside, 0 at edges; 612 if flipped; guard 0\ntri 64x64 #1: 5394 us\n"
                  "tri: 1 renders ok\n")


def answer(tool, argv, world):
    if tool == "rt":
        if "notl" in world and len(argv) > 5 and argv[5:] == TRI:
            return dict(out=tri_out(world))
        return None             # the kit's fake runs the wrapped tool, then timeline()
    if argv in (["fill"], ["tri"]):
        return None             # the kit's health pair
    if argv != TRI:
        return None             # a refusal: usage, rc 2
    return dict(out=tri_out(world))


def timeline(tool, regs, argv, rc, world):
    if argv != TRI:
        return None
    rows = []
    for i in range(N):
        tim = 0 if "timerstop" in world else 0x01000000 | ((0x40000 - 399 * i) % 400000)
        v = {0x0acc: tim, 0x0804: 0x1000ffff if i >= 2200 else 0x0000ffff,
             0x012c: 0x24000000 if 2230 <= i <= 2235 else 0x20000000}
        rows.append([v.get(r, 0) for r in regs])
    return rows
