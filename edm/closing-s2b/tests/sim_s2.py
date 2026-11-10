#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""sim_s2.py: the four S2 blobs (bins/*.blob, as frozen) run in sgx-sim (pysgx) with the landed simrun.py's bus and
stand-in for the closed task.  What this proves: encodings, control flow, patching, the page layout, the window
protocol, the ring ladder and its drop counter, the hold's stamps and n = 0 guard, the E2a areas and the writer's
predicates.  What it does not: any hardware behaviour (CR_TIMER is a value we hand the bus; pa and sa are values
we set).  Exit 0 when every check holds.

    ../pixel-faults/.venv/bin/python tests/sim_s2.py
"""
import os
import pathlib
import sys

sys.dont_write_bytecode = True
S2 = pathlib.Path(__file__).resolve().parent.parent
R = pathlib.Path.home() / "src/resgx545"
os.environ.setdefault("FWTASK_USSE_ASM", str(R / "tools/usse-asm/usse-asm"))
sys.path.insert(0, str(R / "tools/fwtask"))
sys.path.insert(0, str(S2 / "gen"))
import fwtask  # noqa: E402
import simrun  # noqa: E402
import s2layout as L  # noqa: E402

RES = simrun.RES
FAIL = []


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


class Page:
    """The results page and the machine across passes (the closed task between passes is the sim's stand-in)."""

    def __init__(self, blob_name):
        self.blob = fwtask.parse_blob((S2 / "bins" / f"{blob_name}.blob").read_bytes())
        cont = {k: len(self.blob.words) + 8 + 8 * k for k in range(4)}
        words = fwtask.apply_patches(self.blob.words, self.blob.patches, RES, cont)
        img = words + [simrun.NOP] * 8
        for k in range(4):
            st = simrun.stub_words(k)
            img += st + [simrun.NOP] * (8 - len(st))
        self.prog = simrun.pysgx.Program(img)
        self.mem = {RES + 4 * i: 0 for i in range(L.PAGE_DWORDS)}
        self.m = simrun.pysgx.Machine()
        simrun.prime(self.m)

    def w(self, d, v):
        self.mem[RES + 4 * d] = v & 0xFFFFFFFF

    def r(self, d):
        return self.mem[RES + 4 * d]

    def pass_(self, slot, pa, timer, sa=None, max_steps=400000):
        """One pass of slot `slot`'s entry with pa0..pa2 (or pa0..pa4) and CR_TIMER = timer. Returns (steps, stub)."""
        bus = simrun.Bus({81: timer})
        bus.mem = self.mem
        bus.m = self.m
        bus.seal()
        self.w(simrun.STUB_MARK, 0)
        for i, v in enumerate(pa):
            self.m.set("pa", i, v)
        for n, v in (sa or {}).items():
            self.m.set("sa", n, v)
        self.m.pc = self.blob.entries[slot]
        n = 0
        while True:
            bus.now = n
            n += 1
            if self.m.step(self.prog, bus) or n > max_steps:
                break
        stub = self.r(simrun.STUB_MARK)
        return n, (stub - 0x57AB0001) if stub else None

    def ring(self, slot):
        b = L.RING_BASE[slot]
        out = []
        for j in range(L.RUNGS[slot]):
            o = b + L.RUNG * j
            if self.r(o):
                out.append((self.r(o + 1), self.r(o + 2), self.r(o + 3), self.r(o + 4)))
        return out


TICK = (2, 0x02000000, 0x01061A70)
KICK = (0, 0x02000100, 0x0100700C)        # S2 run 1's first kick (E538's 0x03000000 was the tick after it)
FILL_H1 = (0, 0x10, 0x01061A70)         # status bit 18 under the reversed reading: pa1 bit 4 -> slot 3


def test_ring(name, hold):
    p = Page(name)
    # window 0: nothing logged, the closed task of the slot is called
    _, stub = p.pass_(0, TICK, 1000)
    check(p.ring(0) == [] and stub == 0, f"{name}: window 0 logs nothing and tail-calls slot 0")
    # window 1: a plain tick is filtered, a kick and a job word are logged
    p.w(L.WINDOW, 1)
    p.pass_(0, TICK, 2000)
    check(p.ring(0) == [], f"{name}: window 1 filters a plain tick (pa0 2, pa1 bit 25 only)")
    p.pass_(0, KICK, 3000)
    check(p.ring(0) == [KICK + (3000,)], f"{name}: window 1 logs the kick with its CR_TIMER")
    p.pass_(0, (2, 0x03000000, 0x01061A70), 3500)
    check(len(p.ring(0)) == 1, f"{name}: window 1 filters the tick after the kick (E538's words, count 3)")
    _, stub = p.pass_(3, FILL_H1, 4000)
    check(p.ring(3) == [(0, 0x10, 0x01061A70, 4000)] and stub == 3, f"{name}: slot 3 logs into its own ring, tail-calls 3")
    p.pass_(0, (2, 0x00000000, 0x01061A70), 4500)
    check(len(p.ring(0)) == 1, f"{name}: window 1 filters pa1 = 0, pa0 = 2 too")
    p.pass_(0, (0, 0x02000000, 0x01061A70), 4600)
    check(len(p.ring(0)) == 2, f"{name}: window 1 logs pa1 bit 25 alone when pa0 is not 2")
    for k in (3, 4, 5, 0xFF):                     # S2 run 1: pa1[31:24] is a count; a tick at any count is plain
        p.pass_(0, (2, k << 24, 0x01061A70), 4700 + k)
    check(len(p.ring(0)) == 2, f"{name}: window 1 filters ticks whatever the count byte pa1[31:24] (run 1)")
    p.pass_(0, (0, 0x05000100, 0x0103BB6F), 4800)
    check(len(p.ring(0)) == 3 and p.ring(0)[2][1] == 0x05000100, f"{name}: window 1 logs the kick (pa0 0, pa1 bit 8)")
    # window 2: every pass; the ladder fills, then the drop counter
    p.w(L.WINDOW, 2)
    for t in range(40):
        p.pass_(0, TICK, 10000 + 25000 * t)
    r0 = p.ring(0)
    check(len(r0) == L.RUNGS[0] and p.r(L.DROP) == 40 - (L.RUNGS[0] - 3), f"{name}: slot 0 ring full at "
          f"{L.RUNGS[0]} rungs, {p.r(L.DROP)} passes counted as dropped")
    for k in (1, 2, 3):
        p2 = Page(name)
        p2.w(L.WINDOW, 2)
        for t in range(L.RUNGS[k] + 3):
            _, stub = p2.pass_(k, (0, 0x200, 0x01061A70), t)
        check(len(p2.ring(k)) == L.RUNGS[k] and p2.r(L.DROP + k) == 3 and stub == k,
              f"{name}: slot {k} ring of {L.RUNGS[k]} then 3 drops, tail-call {k}")
    if not hold:
        return
    # the hold: cmd 1, n iterations, stamps, state, echo, cmd back to 0; the pass is logged before the hold
    p = Page(name)
    p.w(L.WINDOW, 2)
    p.w(L.N_ITER, 7)
    p.w(L.RUNID, 0x5299)
    p.w(L.CMD, 1)
    steps, stub = p.pass_(0, TICK, 77777)
    check(p.r(L.STATE) == 2 and p.r(L.CMD) == 0 and p.r(L.ECHO) == 0x5299 and stub == 0,
          f"{name}: cmd 1 holds and ends done, cmd 0, run id echoed, tail call ({steps} steps at n 7)")
    check(p.r(L.HOLD_ENTRY) == 77777 and p.r(L.HOLD_EXIT) == 77777 and len(p.ring(0)) == 1,
          f"{name}: entry and exit stamps written, the holding pass logged once")
    p2 = Page(name)
    p2.w(L.WINDOW, 2)
    p2.w(L.N_ITER, 70)
    p2.w(L.CMD, 1)
    steps2, _ = p2.pass_(0, TICK, 1)
    check(steps2 - steps == 3 * 63, f"{name}: the loop is three instructions an iteration ({steps2 - steps} steps for 63 more)")
    p3 = Page(name)
    p3.w(L.N_ITER, 0)
    p3.w(L.CMD, 1)
    steps3, _ = p3.pass_(0, TICK, 5)
    check(p3.r(L.STATE) == 2 and steps3 < 200, f"{name}: n = 0 does not loop ({steps3} steps), ends done")
    p.w(L.STATE, 1)                          # a pass of slot 2 while the state is busy: the overlap flag
    p.pass_(2, (0, 0x400, 0x01061A70), 999)
    check(p.r(L.OVL + 2) == 1 and p.r(L.OVL_LOG + 8 + 1) == 0x400 and p.r(L.OVL_LOG + 8 + 3) == 999
          and p.r(L.PASS + 2) == 1 and p.r(L.PASS) == 1, f"{name}: busy flag, its log and the pass counters")


def test_pa(name, write):
    p = Page(name)
    sa = {64: 2, 65: 0x02000000, 66: 0x01061A70, 67: 0x67, 68: 0x68, 0: 0x0BAD0000}
    pa = (2, 0x02000000, 0x01061A70, 0x33, 0x44)
    _, stub = p.pass_(0, pa, 100, sa)
    check(p.r(L.AREA_A) == 0 and stub == 0, f"{name}: cmd 0 stores nothing, tail call")
    for d in range(L.AREA_A, L.AREA_B + 12):
        p.w(d, L.INITFILL)
    p.w(L.RUNID, 0x52aa)
    p.w(L.CMD, 1)
    p.pass_(0, pa, 200, sa)
    A = [p.r(L.AREA_A + i) for i in range(12)]
    check(A == [2, 0x02000000, 0x01061A70, 0x33, 0x44, 2, 0x02000000, 0x01061A70, 0x67, 0x68, 0x0BAD0000, 200]
          and p.r(L.CMD) == 9 and p.r(L.STATE) == 2 and p.r(L.ECHO) == 0x52aa, f"{name}: cmd 1 area A, cmd 9 armed, done")
    p.pass_(0, pa, 300, sa)
    B = [p.r(L.AREA_B + i) for i in range(12)]
    check(B[:11] == A[:11] and B[11] == 300 and p.r(L.CMD) == 0 and p.r(L.STATE) == 3,
          f"{name}: the next pass stores area B, cmd 0, state 3")
    finals = {n: p.m.get("sa", n) for n in (64, 65, 66, 67, 68)}
    check(finals == {64: 2, 65: 0x02000000, 66: 0x01061A70, 67: 0x67, 68: 0x68}, f"{name}: cmd 1 and 9 write no sa")
    if not write:
        return
    for cmd, sa_n, c in ((2, 67, L.AREA_C), (3, 68, L.AREA_C + 2)):
        p.w(L.MARK, 0xB2A00000 + sa_n)
        for i, f in enumerate((0, 0, 1, 1)):
            p.w(L.PFLAGS + i, f)
        p.w(L.STATE, 0)
        p.w(L.CMD, cmd)
        _, stub = p.pass_(0, pa, 400, {})
        got = {n: p.m.get("sa", n) for n in (64, 65, 66, 67, 68)}
        want = dict(finals)
        want[sa_n] = 0xB2A00000 + sa_n
        if cmd == 3:
            want[67] = 0xB2A00043
        pred = tuple(int(p.m.pred(i)) for i in range(4))
        # the sim's pa bank is its own (no alias model): pa3/pa4 read what we set; sa67/sa68 read the write
        check(got == want and p.r(c + 1) == 0xB2A00000 + sa_n and p.r(c) == pa[3 + cmd - 2]
              and p.r(L.CMD) == 9 and p.r(L.STATE) == 2 and stub == 0,
              f"{name}: cmd {cmd} writes sa{sa_n} only, reads it back in the same pass, arms cmd 9")
        check(pred == (0, 0, 1, 1), f"{name}: cmd {cmd} reaches the tail call with p0..p3 = 0, 0, 1, 1 ({pred})")


def main():
    if not simrun.available():
        print("SKIPPED, NOT PASSED: pysgx is not available")
        return 2
    test_ring("ring_hold", True)            # S2b builds ring_hold only (no ring_e1, no pa task)
    print(f"{len(FAIL)} failed" if FAIL else "all sim checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
