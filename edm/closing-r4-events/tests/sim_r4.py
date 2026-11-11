#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""sim_r4.py: the R4-events blobs (S2b's bins/ring_hold.blob, and the new ring_exit2 and ring_skip3p) run in sgx-sim (pysgx) with the landed
simrun.py's bus and stand-in for the closed task (resgx545 5a13042).  What this proves: encodings, control flow, patching, the acted pass of
ring_exit2.s (KIND 1 a plain tick pass, KIND 2 a kick pass, ACT 4: logged first with flag 3, COUNT - 1, ACTED + 1, ACT_SEEN, then the phase end
and nop.end with the closed task NOT called; only the wanted pass, only window 2, only COUNT times), the skip-once of ring_skip3p.s (the slot 3
end-of-render pass ends with the phase end, once, the other passes tail-call; no `str` anywhere), the S2 ring behaviour of the other slots, the
hold of ring_hold.blob.  What it does not: any hardware behaviour (the closed task is a stub that records which slot tail-called it).
Exit 0 when every check holds, 2 when the simulator is not available (SKIPPED, NOT PASSED).

    .../pixel-faults/.venv/bin/python tests/sim_r4.py
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys

sys.dont_write_bytecode = True
R4 = pathlib.Path(__file__).resolve().parent.parent
R = pathlib.Path(os.environ.get("RESGX545", "/Users/jtorra/src/scratch/resgx545/closing4/lead/wt"))
os.environ.setdefault("FWTASK_USSE_ASM", str(R / "tools/usse-asm/usse-asm"))
sys.path.insert(0, str(R / "tools/fwtask"))
sys.path.insert(0, str(R4 / "gen"))
import fwtask  # noqa: E402
import simrun  # noqa: E402
import r4layout as L  # noqa: E402
import r3blobs as B  # noqa: E402

RES = simrun.RES
FAIL = []
SIM = R / "target/release/sgx-sim"


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


class Page:
    """The results page and the machine across passes (the closed task between passes is the sim's stand-in)."""

    def __init__(self, blob_name):
        self.blob = fwtask.parse_blob((R4 / "bins" / f"{blob_name}.blob").read_bytes())
        cont = {k: len(self.blob.words) + 8 + 8 * k for k in range(5)}
        words = fwtask.apply_patches(self.blob.words, self.blob.patches, RES, cont)
        img = words + [simrun.NOP] * 8
        for k in range(5):
            st = simrun.stub_words(k)
            img += st + [simrun.NOP] * (8 - len(st))
        self.prog = simrun.pysgx.Program(img)
        self.mem = {RES + 4 * i: 0 for i in range(L.PAGE_DWORDS)}
        self.m = simrun.pysgx.Machine()
        simrun.prime(self.m)
        self.steps = 0

    def w(self, d, v):
        self.mem[RES + 4 * d] = v & 0xFFFFFFFF

    def r(self, d):
        return self.mem[RES + 4 * d]

    def set_pclink(self, v):
        p = simrun.pysgx.Program(fwtask.assemble_text(f"mov r12, #0x{v:08x}\nmov pclink, r12\nnop.end"))
        self.m.pc = 0
        self.m.run(p, simrun.Bus({}))

    def get_pclink(self):
        q = simrun.pysgx.Program(fwtask.assemble_text("mov r31, pclink\nnop.end"))
        pc = self.m.pc
        self.m.pc = 0
        self.m.run(q, simrun.Bus({}))
        v = self.m.get("r", 31)
        self.m.pc = pc
        return v

    def pass_(self, slot, pa, timer=1000, max_steps=400000):
        """One pass at the slot's entry.  Returns (steps, slot of the closed-task stub that ended it or None)."""
        bus = simrun.Bus({81: timer})
        bus.mem = self.mem
        bus.m = self.m
        bus.seal()
        self.bus = bus
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
        self.steps = n
        stub = self.r(simrun.STUB_MARK)
        return n, ((stub - 0x57AB0001) if stub else None)

    def preds(self):
        return tuple(int(self.m.pred(n)) for n in range(4))

    def ring(self, slot):
        b = L.RING_BASE[slot]
        return [(self.r(b + L.RUNG * j), self.r(b + L.RUNG * j + 1), self.r(b + L.RUNG * j + 2),
                 self.r(b + L.RUNG * j + 3), self.r(b + L.RUNG * j + 4)) for j in range(L.RUNGS[slot])
                if self.r(b + L.RUNG * j)]


TICK = (2, 0x02000000, 0x01061A70)
KICK = (0, 0x02000100, 0x0100700C)


# ---- the new tasks -----------------------------------------------------------------------------------------------------------
INFO = json.loads((R4 / "bins" / "blobs.json").read_text())
EXIT_CFI, EXIT_PHAS = 0xF843B300A0000180, 0xFA44070000000000


def verify_blob(name):
    blob = (R4 / "bins" / f"{name}.blob").read_bytes()
    regs = fwtask.load_regs()
    check(fwtask.build_blob_text((R4 / "asm" / f"{name}.s").read_text(), regs) == blob, f"asm/{name}.s assembles to exactly bins/{name}.blob")
    check(fwtask.verify_blob(blob, regs) == [], f"{name}.blob passes the landed verifier (fwtask.verify_blob)")
    pb = fwtask.parse_blob(blob)
    check(len(pb.words) <= 1024, f"{name}: {len(pb.words)} words (limit 1024)")
    check(fwtask.lint((R4 / "asm" / f"{name}.s").read_text()) == [], f"{name}: the landed lint has no warning (every .end follows the exit phas)")
    check(INFO[name]["str"] == [] and not INFO[name]["cont4"], f"{name}: no firmware str, no cont4 (blobs.json)")
    conts = sorted(p.kind for p in pb.patches if p.kind.startswith("cont"))
    check(conts == ["cont0", "cont1", "cont2", "cont3"], f"{name}: one continue patch an entry ({conts})")
    return pb


def exit_page(act=L.ACT_PHAS, count=1, kind=1, window=2):
    p = Page("ring_exit2")
    p.w(L.WINDOW, window)
    p.w(L.KIND, kind)
    p.w(L.ACT, act)
    p.w(L.COUNT, count)
    return p


def test_exit2():
    pb = verify_blob("ring_exit2")
    ws = pb.words
    check(sum(1 for w in ws if w == EXIT_PHAS) == 1 and sum(1 for w in ws if w == EXIT_CFI) == 0,
          "ring_exit2.blob holds the exit's phase end once and no cache flush (cfi.global)")
    p = Page("ring_exit2")
    _, stub = p.pass_(0, TICK, 1000)
    check(stub == 0 and p.ring(0) == [] and p.r(L.A_PASS) == 1, "window 0: counted, not logged, the closed task called")
    for kind, pa, what in ((1, TICK, "a plain tick pass"), (2, KICK, "a kick pass")):
        p = exit_page(kind=kind)
        _, stub = p.pass_(0, pa, 2000)
        check(stub is None and p.ring(0) == [(L.SKIP_FLAG,) + pa + (2000,)] and p.r(L.COUNT) == 0 and p.r(L.ACTED) == 1
              and p.r(L.ACT_SEEN) == L.ACT_PHAS, f"KIND {kind}: {what} is acted on, logged first with flag 3, ACT_SEEN 4, ends in the phase end and nop.end (no closed task)")
        _, stub = p.pass_(0, pa, 3000)
        check(stub == 0 and p.ring(0)[-1] == (1,) + pa + (3000,) and p.r(L.ACTED) == 1, f"KIND {kind}: COUNT is spent: the next pass is logged with flag 1 and tail-calls slot 0")
    # only the wanted kind
    for kind, pa, what in ((1, KICK, "a kick pass under KIND 1"), (2, TICK, "a tick pass under KIND 2"), (1, (2, 0x02000200, 0x01061A70), "a tick with a bit"),
                           (2, (0, 0x02000300, 0), "a kick word with another bit"), (2, (1, 0x02000100, 0), "pa0 = 1 with the kick bit"),
                           (0, TICK, "KIND 0")):
        p = exit_page(kind=kind)
        _, stub = p.pass_(0, pa, 100)
        check(stub == 0 and p.r(L.ACTED) == 0, f"{what}: not acted on")
    p = exit_page(window=1)
    _, stub = p.pass_(0, TICK, 100)
    check(stub == 0 and p.r(L.ACTED) == 0 and p.ring(0) == [], "window 1: a plain tick is not logged and not acted on")
    p = exit_page(count=0)
    _, stub = p.pass_(0, TICK, 100)
    check(stub == 0 and p.r(L.ACTED) == 0, "COUNT 0: nothing is acted on")
    p = exit_page(act=3)
    _, stub = p.pass_(0, TICK, 100)
    check(stub == 0 and p.r(L.ACTED) == 1 and p.ring(0)[0][0] == L.SKIP_FLAG, "an ACT other than 4 has no end of its own here: the pass tail-calls (no own end is ever taken)")
    p = exit_page(count=2)
    p.pass_(0, TICK, 100)
    _, stub = p.pass_(0, TICK, 200)
    check(stub is None and p.r(L.ACTED) == 2 and p.r(L.COUNT) == 0, "COUNT 2: two passes acted on")
    for k in (1, 2, 3):
        p = exit_page()
        _, stub = p.pass_(k, (0, 1 << 24 | 0x10, 0x01061A70), 100 + k)
        check(stub == k and p.r(L.ACTED) == 0 and len(p.ring(k)) == 1, f"slot {k}: logged and tail-called as S2's ring, never acted on")


ENDRENDER = (0, 0x02000010, 0x01061A70)


def test_skip3p():
    pb = verify_blob("ring_skip3p")
    check(sum(1 for w in pb.words if w == EXIT_PHAS) == 1 and sum(1 for w in pb.words if w == EXIT_CFI) == 0,
          "ring_skip3p.blob holds the exit's phase end once and no cache flush")
    p = Page("ring_skip3p")
    p.w(L.WINDOW, 2)
    _, stub = p.pass_(3, ENDRENDER, 500)
    check(stub == 3 and p.ring(3) == [(1,) + ENDRENDER + (500,)] and p.r(L.SKIPPED) == 0, "flag 0: the end-of-render pass is logged with flag 1 and tail-calls slot 3")
    p = Page("ring_skip3p")
    p.w(L.WINDOW, 2)
    p.w(L.SKIP3, 1)
    for pa, what in (((0, 0x02000040, 0), "another bit (pa1 = 0x40)"), ((0, 0x02000011, 0), "pa1[23:0] = 0x11"), ((1, 0x02000010, 0), "pa0 = 1")):
        _, stub = p.pass_(3, pa, 400)
        check(stub == 3 and p.r(L.SKIP3) == 1, f"flag 1: {what} is not the end of render: not skipped")
    _, stub = p.pass_(3, ENDRENDER, 500)
    check(stub is None and p.ring(3)[-1] == (L.SKIP_FLAG,) + ENDRENDER + (500,) and p.r(L.SKIP3) == 0 and p.r(L.SKIPPED) == 1,
          "flag 1: the end-of-render pass is logged with flag 3, the flag taken, SKIPPED 1, ends in the phase end and nop.end (no closed task)")
    _, stub = p.pass_(3, ENDRENDER, 600)
    check(stub == 3 and p.r(L.SKIPPED) == 1, "once: the next end-of-render pass tail-calls")
    p = Page("ring_skip3p")
    p.w(L.SKIP3, 1)
    _, stub = p.pass_(1, ENDRENDER, 100)
    check(stub == 1 and p.r(L.SKIP3) == 1, "slots 0-2 never skip")
    p = Page("ring_skip3p")
    p.w(L.SKIP3, 1)
    _, stub = p.pass_(3, ENDRENDER, 100)
    check(stub is None and p.r(L.SKIPPED) == 1 and p.ring(3) == [], "window 0: the skip still happens, nothing is logged")
    p = Page("ring_skip3p")
    p.w(L.WINDOW, 2)
    p.w(L.CMD, 2)
    p.w(L.SC_VAL, 0x40000)
    _, stub = p.pass_(0, TICK, 300)
    check(stub == 0 and p.r(L.CMD) == 2 and p.bus.writes == [], "slot 0 takes no command: a CMD 2 is ignored, no register is written (no str in the blob)")


# ---- ring_hold.blob (S2b's, unchanged) ------------------------------------------------------------------------------------
def test_hold():
    blob = (R4 / "bins" / "ring_hold.blob").read_bytes()
    check(hashlib.sha256(blob).hexdigest() == L.HOLD_SHA, "bins/ring_hold.blob is S2b's, byte for byte (sha256 fa0f79db...)")
    regs = fwtask.load_regs()
    check(fwtask.verify_blob(blob, regs) == [], "ring_hold.blob passes the landed verifier")
    p = Page("ring_hold")
    p.w(L.WINDOW, 2)
    _, stub = p.pass_(0, TICK, 5000)
    check(stub == 0 and p.ring(0) == [(1,) + TICK + (5000,)], "ring_hold: a tick in window 2 is logged with flag 1 and tail-calls (the ring kb2 reads)")
    p = Page("ring_hold")
    p.w(L.WINDOW, 2)
    _, stub = p.pass_(0, KICK, 5100)
    check(stub == 0 and p.ring(0) == [(1,) + KICK + (5100,)], "ring_hold: a kick pass is logged (pa0 0, pa1[23:0] 0x100) and tail-calls")
    p = Page("ring_hold")
    p.w(L.WINDOW, 2)
    p.w(L.N_ITER, 7)
    p.w(L.CMD, 1)
    p.w(L.RUNID, 0x77)
    _, stub = p.pass_(0, TICK, 5000)
    check(p.r(L.CMD) == 0 and p.r(L.STATE) == 2 and p.r(L.ECHO) == 0x77 and stub == 0, "ring_hold: cmd 1 with n = 7 holds, ends done and tail-calls (kb2 never sends it)")


def main():
    if not simrun.available() or not SIM.exists():
        print("SKIPPED, NOT PASSED: pysgx or the sgx-sim binary is not available")
        return 2
    test_exit2()
    test_skip3p()
    test_hold()
    print(f"{len(FAIL)} failed" if FAIL else "all sim checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
