#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""sim_r1.py: the R1-events blob (bins/ring_e1.blob, as frozen: 12 rungs in slot 3) and the Q082 loop programs
(bins/loop-*.bin, bins/vtx-stock.bin) run in sgx-sim (pysgx and the sgx-sim binary) with the landed simrun.py's bus and
stand-in for the closed task.  What this proves: encodings, control flow, patching, the window protocol, the ring ladders
(slot 3's 12 rungs, then the drop counter), the filter, the loops' lengths in executed instructions (prologue + iterations x
body + 1) and their end value o0 = 0.  What it does not: any hardware behaviour (CR_TIMER is a value we hand the bus; pa and
sa are values we set; the sim has no resident-instance model and no memory latency).  Exit 0 when every check holds.

    ../../closing/pixel-faults/.venv/bin/python tests/sim_r1.py
"""
import json
import os
import pathlib
import re
import subprocess
import sys

sys.dont_write_bytecode = True
R1 = pathlib.Path(__file__).resolve().parent.parent
R = pathlib.Path.home() / "src/resgx545"
os.environ.setdefault("FWTASK_USSE_ASM", str(R / "tools/usse-asm/usse-asm"))
sys.path.insert(0, str(R / "tools/fwtask"))
sys.path.insert(0, str(R1 / "gen"))
import fwtask  # noqa: E402
import simrun  # noqa: E402
import r1layout as L  # noqa: E402

RES = simrun.RES
FAIL = []
SIM = R / "target/release/sgx-sim"


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


class Page:
    """The results page and the machine across passes (the closed task between passes is the sim's stand-in)."""

    def __init__(self, blob_name="ring_e1"):
        self.blob = fwtask.parse_blob((R1 / "bins" / f"{blob_name}.blob").read_bytes())
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

    def pass_(self, slot, pa, timer, max_steps=400000):
        bus = simrun.Bus({81: timer})
        bus.mem = self.mem
        bus.m = self.m
        bus.seal()
        self.w(simrun.STUB_MARK, 0)
        for i, v in enumerate(pa):
            self.m.set("pa", i, v)
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
        return [(self.r(b + L.RUNG * j + 1), self.r(b + L.RUNG * j + 2), self.r(b + L.RUNG * j + 3),
                 self.r(b + L.RUNG * j + 4)) for j in range(L.RUNGS[slot]) if self.r(b + L.RUNG * j)]


TICK = (2, 0x02000000, 0x01061A70)
KICK = (0, 0x02000100, 0x0100700C)        # S2 run 1's first kick
FILL_H1 = (0, 0x10, 0x01061A70)           # status bit 18 under the reversed reading: pa1 bit 4 -> slot 3
BIT19 = (0, 1 << 19, 0x01061A70)          # Q033: pa1 bit 19, general slot by E146's dispatch


def test_ring():
    p = Page()
    check(L.RUNGS == {0: 16, 1: 8, 2: 8, 3: 12} and L.RING_END == L.RING_BASE[3] + 12 * L.RUNG,
          "layout: 16, 8, 8 and 12 rungs; the ring ends at the last rung of slot 3")
    _, stub = p.pass_(0, TICK, 1000)
    check(p.ring(0) == [] and stub == 0, "window 0 logs nothing and tail-calls slot 0")
    p.w(L.WINDOW, 1)
    p.pass_(0, TICK, 2000)
    check(p.ring(0) == [], "window 1 filters a plain tick")
    p.pass_(0, KICK, 3000)
    check(p.ring(0) == [KICK + (3000,)], "window 1 logs the kick with its CR_TIMER")
    for k in (3, 4, 5, 0xFF, 0):             # the count byte pa1[31:24] never makes a tick non-plain (S2 run 1; Q290 K5 wraps)
        p.pass_(0, (2, k << 24, 0x01061A70), 4000 + k)
    check(len(p.ring(0)) == 1, "window 1 filters ticks whatever the count byte (0, 3, 4, 5, 255)")
    _, stub = p.pass_(3, FILL_H1, 5000)
    check(p.ring(3) == [(0, 0x10, 0x01061A70, 5000)] and stub == 3, "slot 3 logs into its own ring, tail-calls 3")
    p.pass_(0, BIT19, 6000)
    check(p.ring(0)[-1] == BIT19 + (6000,), "pa1 bit 19 (Q033) is logged in slot 0 in window 1")
    p.w(L.WINDOW, 2)
    before = len(p.ring(0))                  # the kick and the bit-19 entry are already in the ladder
    for t in range(40):
        p.pass_(0, TICK, 10000 + 25000 * t)
    check(len(p.ring(0)) == L.RUNGS[0] and p.r(L.DROP) == 40 - (L.RUNGS[0] - before),
          f"window 2: slot 0 ring full at {L.RUNGS[0]} rungs, {p.r(L.DROP)} passes counted as dropped")
    for k in (1, 2, 3):
        p2 = Page()
        p2.w(L.WINDOW, 2)
        for t in range(L.RUNGS[k] + 3):
            _, stub = p2.pass_(k, (0, 0x200, 0x01061A70), t)
        check(len(p2.ring(k)) == L.RUNGS[k] and p2.r(L.DROP + k) == 3 and stub == k,
              f"slot {k}: ring of {L.RUNGS[k]} then 3 drops, tail-call {k}")
    # slot 3's twelfth rung is the last that writes inside the ring, a thirteenth entry is a drop and writes nothing outside
    p3 = Page()
    p3.w(L.WINDOW, 2)
    for t in range(13):
        p3.pass_(3, (0, 0x10, 0x01061A70), 100 + t)
    check(p3.r(L.RING_END - 8) == 1 and p3.r(L.RING_END - 4) == 111 and p3.r(L.DROP + 3) == 1
          and all(p3.r(d) == 0 for d in range(L.RING_END, L.RING_END + 16)),
          "slot 3: the 12th rung holds entry 12, the 13th is one drop, nothing written past the ring")


def run_sim(path, max_steps=100000):
    r = subprocess.run([str(SIM), "--task", "pixel", "--max", str(max_steps), str(path)], capture_output=True, text=True)
    m = re.search(r"ended after (\d+) steps", r.stdout)
    o0 = re.search(r"^o0 = (0x[0-9a-f]+)", r.stdout, re.M)
    return (int(m[1]) if m else None), (int(o0[1], 16) if o0 else None), r.stdout + r.stderr


def test_loops():
    info = json.loads((R1 / "bins" / "blobs.json").read_text())["loops"]
    bad = []
    n = 0
    for name, meta in sorted(info.items()):
        if "kind" not in meta:
            continue
        steps, o0, txt = run_sim(R1 / "bins" / f"{name}.bin")
        n += 1
        want = meta["prologue"] + meta["iters"] * meta["body"] + 1       # prologue, the loop, then mov.end
        if steps != want or o0 != 0:
            bad.append((name, steps, want, o0))
    check(not bad, f"{n} loop programs: executed instructions = prologue + iterations x body + 1, o0 = 0 ({bad[:3]})")
    steps8, _, _ = run_sim(R1 / "bins" / "loop-b8-i56.bin")
    steps53, _, _ = run_sim(R1 / "bins" / "loop-b8-i53.bin")
    check(steps8 - steps53 == 3 * 8, "body 8: three more iterations are 24 more instructions")
    s16, _, _ = run_sim(R1 / "bins" / "loop-b16-i28.bin")
    s4, _, _ = run_sim(R1 / "bins" / "loop-b4-i110.bin")
    check(s16 - 5 == 28 * 16 and s4 - 5 == 110 * 4 and abs(s16 - s4) <= 8,
          f"body 16 at 28 and body 4 at 110 run about 440 instructions ({s16 - 5} and {s4 - 5}), H-INSTR's equal-instruction pair")
    sl, _, _ = run_sim(R1 / "bins" / "loop-ld8-i53.bin")
    check(sl == 5 + 53 * 8 + 1, "ld8: the load and its wait are two of the eight instructions of the body")


def test_blob():
    info = json.loads((R1 / "bins" / "blobs.json").read_text())["ring_e1"]
    blob = (R1 / "bins" / "ring_e1.blob").read_bytes()
    regs = fwtask.load_regs()
    check(fwtask.build_blob_text((R1 / "asm" / "ring_e1.s").read_text(), regs) == blob,
          "asm/ring_e1.s assembles and passes the landed verifier to exactly bins/ring_e1.blob")
    check(info["str"] == 0 and info["sa_writes"] == [], "ring_e1: no str, no sa write")


def main():
    if not simrun.available() or not SIM.exists():
        print("SKIPPED, NOT PASSED: pysgx or the sgx-sim binary is not available")
        return 2
    test_blob()
    test_ring()
    test_loops()
    print(f"{len(FAIL)} failed" if FAIL else "all sim checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
