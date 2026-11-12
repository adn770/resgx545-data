#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""simring.py: bins/oomring.blob run in sgx-sim (pysgx) through the landed tools/fwtask/simrun.py bus and stand-in for the closed task,
one pass a time, with chosen pa0, pa1, sa8, sa9 and CR_TIMER: what the results page holds after a sequence of event passes.  Used by
tests/test_oomring.py (rung by rung) and by the A3 mock world (tests/world_r5.py writes the page the fake fwtask_run.py serves).
What this proves: encodings, control flow, patching, the rung layout the scorer decodes.  What it does not: any hardware behaviour.
"""
from __future__ import annotations

import pathlib
import sys

sys.dont_write_bytecode = True
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, "/Users/jtorra/src/resgx545/tools/fwtask")
import fwtask  # noqa: E402
import simrun  # noqa: E402

RES = simrun.RES


class Ring:
    def __init__(self, blob_path=KP / "bins" / "oomring.blob"):
        self.blob = fwtask.parse_blob(pathlib.Path(blob_path).read_bytes())
        cont = {k: len(self.blob.words) + 8 + 8 * k for k in range(5)}
        words = fwtask.apply_patches(self.blob.words, self.blob.patches, RES, cont)
        img = words + [simrun.NOP] * 8
        for k in range(5):
            st = simrun.stub_words(k)
            img += st + [simrun.NOP] * (8 - len(st))
        self.prog = simrun.pysgx.Program(img)
        self.mem = {RES + 4 * i: 0 for i in range(1024)}
        self.mem[RES] = 0x4E574F53      # the kernel's magic at dword 0
        self.m = simrun.pysgx.Machine()
        simrun.prime(self.m)

    def page(self):
        return [self.mem[RES + 4 * i] for i in range(1024)]

    def pass_(self, slot, pa0, pa1, sa8=0, sa9=0, timer=1000, max_steps=200000):
        """One event pass at the slot's entry; returns (steps, the slot whose closed-task stand-in it reached, or None)."""
        bus = simrun.Bus({81: timer})
        bus.mem = self.mem
        bus.m = self.m
        bus.seal()
        self.mem[RES + 4 * simrun.STUB_MARK] = 0
        self.m.set("pa", 0, pa0)
        self.m.set("pa", 1, pa1)
        self.m.set("pa", 2, 0)
        self.m.set("sa", 8, sa8)
        self.m.set("sa", 9, sa9)
        self.m.pc = self.blob.entries[slot]
        n = 0
        while True:
            bus.now = n
            n += 1
            if self.m.step(self.prog, bus) or n > max_steps:
                break
        stub = self.mem[RES + 4 * simrun.STUB_MARK]
        self.mem[RES + 4 * simrun.STUB_MARK] = 0
        return n, ((stub - 0x57AB0001) if stub else None)


def run_events(events, blob_path=KP / "bins" / "oomring.blob"):
    """events: [(slot, pa0, pa1, sa8, sa9, timer)] -> (page, [(steps, stub slot)])."""
    r = Ring(blob_path)
    res = [r.pass_(*e) for e in events]
    return r.page(), res
