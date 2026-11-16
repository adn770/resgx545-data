# SPDX-License-Identifier: MIT
"""mock/world.py: r32-misc's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name; timeline() gives regtimeline's
samples of the wrapped job. EXPECT: {world: (the driver's status, {stage: the runner's status})}.

t10's one form as the session runs it, `tri --width 64 --height 64` (`job: ok`, `target:`,
`diff: 0 of 4096 pixels`, `outside:`, the count line, `tri 64x64 #1: T us`, `tri: 1 renders
ok`, E547's kept tri64 text), and the kit's health pair (bare `fill` and `tri`, the kit's own
answers). The kit's fake sudo answers debugfs miscinfo as the kernel does (and the reset logs
the boot's own GETMISCINFO answer); its regs file has no 0x0804, so the mock's controls read no
cache word (the scorer is tested on r31-cc's kept snapshots and on synthetic ones).
regtimeline's samples (1 us apart, start 0 end 0): 0x0804 0x0000ffff then 0x1000ffff from the
job (E1122), 0x0b14 bit 16 set and counting.

Worlds: model (both stages run, 0); nodiff (a triangle without its diff line: m1 stops at its
first row, 24, on_stop end: the session ends); miscinfobad (the kit's world token: the miscinfo
read prints a MISMATCH, m1 stops before its first row with the word, 19); notl (regtimeline
prints no timeline: m1 runs, m2 stops at its first row, 24, end)."""
EXPECT = {"model": (0, {"m1": 0, "m2": 0}),
          "nodiff": (24, {"m1": 24}),
          "miscinfobad": (19, {"m1": 19}),
          "notl": (24, {"m1": 0, "m2": 24})}
TRI = ["tri", "--width", "64", "--height", "64"]


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
    for i in range(6):
        v = {0x0804: 0x1000ffff if i else 0x0000ffff, 0x0b14: 0x10000 | (0x0a00 + i)}
        rows.append([v.get(r, 0) for r in regs])
    return rows
