#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""sim_r3.py: the R3-events blobs (bins/alias.blob, bins/ring_skip.blob, S2b's bins/ring_hold.blob as frozen) run in sgx-sim
(pysgx) with the landed simrun.py's bus and stand-in for the closed task.  What this proves: encodings, control flow,
patching, the command protocol of alias.s (what each command writes, what it leaves alone, the predicates at its tail call,
the reader's record), the skip of ring_skip.s (flag 3, the counters, nop.end without the closed task, only plain ticks, only
window 2), the S2 ring behaviour of the other slots, the hold of ring_hold.blob at a small n.  What it does not: any hardware
behaviour (the closed task is a stub that records which slot tail-called it; sa, pa and CR_TIMER are values we set).
Exit 0 when every check holds.

    ../../closing/pixel-faults/.venv/bin/python tests/sim_r3.py
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys

sys.dont_write_bytecode = True
R3 = pathlib.Path(__file__).resolve().parent.parent
R = pathlib.Path.home() / "src/resgx545"
os.environ.setdefault("FWTASK_USSE_ASM", str(R / "tools/usse-asm/usse-asm"))
sys.path.insert(0, str(R / "tools/fwtask"))
sys.path.insert(0, str(R3 / "gen"))
import fwtask  # noqa: E402
import simrun  # noqa: E402
import r3layout as L  # noqa: E402
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
        self.blob = fwtask.parse_blob((R3 / "bins" / f"{blob_name}.blob").read_bytes())
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


# ---- alias.s -------------------------------------------------------------------------------------------------------------
def alias_page(sa=(0, 2, 0x02000000), pclink=0x98, preds=(1, 1, 0, 0), r=(0, 0x3000), i=(0xB5000020, 0xB5000021)):
    p = Page("alias")
    p.m.set("sa", 63, sa[0])
    p.m.set("sa", 64, sa[1])
    p.m.set("sa", 65, sa[2])
    p.set_pclink(pclink)
    for n, v in enumerate(preds):
        p.m.set_pred(n, bool(v))
    p.m.set("r", 20, r[0])
    p.m.set("r", 21, r[1])
    p.m.set("i", 0, i[0])
    p.m.set("i", 1, i[1])
    return p


def command(p, cmd, marker=0, ri=(0, 0, 0, 0), runid=7, pa=TICK):
    p.w(L.CMD, cmd)
    p.w(L.STATE, 0)
    p.w(L.RUNID, runid)
    p.w(L.A_M, marker)
    for n, v in enumerate(ri):
        p.w(L.A_RI + n, v)
    return p.pass_(0, pa)


def sa_now(p):
    return [p.m.get("sa", n) for n in (63, 64, 65)]


def test_alias_blob():
    info = json.loads((R3 / "bins" / "blobs.json").read_text())["alias"]
    blob = (R3 / "bins" / "alias.blob").read_bytes()
    regs = fwtask.load_regs()
    check(fwtask.build_blob_text((R3 / "asm" / "alias.s").read_text(), regs) == blob,
          "asm/alias.s assembles and passes the landed verifier to exactly bins/alias.blob")
    check(info["str"] == 0 and info["ldr"] == [] and info["sa_writes"] == ["sa63", "sa64", "sa65"],
          "alias: no str, no ldr, sa writes within sa63, sa64, sa65")
    check({int(k): v for k, v in info["cmd_sa"].items()} == L.CMD_SA, "alias: the sa write set of each command is r3layout.CMD_SA")


def test_alias_commands():
    p = alias_page()
    steps, stub = command(p, 0)
    check(stub == 0 and sa_now(p) == [0, 2, 0x02000000] and p.r(L.A_PASS) == 1 and p.r(L.CMD) == 0 and p.r(L.STATE) == 0,
          "cmd 0: one pass counted, the closed task called at once (slot 0), nothing written")
    # the reader: the entry values of the previous pass are what it stores
    p = alias_page(pclink=0x98, preds=(1, 1, 0, 0), r=(5, 0x3000), i=(0xAA, 0xBB))
    steps, stub = command(p, L.CMD_READ, pa=TICK)
    rd = [p.r(L.RD + n) for n in range(16)]
    want = {"pclink": 0x98, "p0": 1, "p1": 1, "p2": 0, "p3": 0, "r20": 5, "r21": 0x3000, "i0": 0xAA, "i1": 0xBB, "sa64": 2,
            "sa65": 0x02000000, "sa63": 0, "pa0": 2, "pa1": 0x02000000, "pa2": 0x01061A70, "pass": 1}
    got = dict(zip(L.RD_FIELDS, rd))
    check(got == want, f"cmd 9 (reader): stores pclink, p0-p3, r20, r21, i0, i1, sa64, sa65, sa63, pa0-pa2, pass ({got})")
    check(stub == 0 and p.r(L.CMD) == 0 and p.r(L.STATE) == 2 and p.r(L.ECHO) == 7,
          "cmd 9: cmd = 0, state done, run id echoed, closed task called")
    # A1
    p = alias_page()
    steps, stub = command(p, L.CMD_A1, marker=0xB0C3A5E1)
    check(sa_now(p) == [0xB0C3A5E1, 2, 0x02000000], "A1: sa63 = the marker, sa64 and sa65 untouched")
    check(p.preds() == (0, 0, 1, 1) and stub == 0 and p.r(L.CMD) == 9 and p.r(L.STATE) == 2 and p.r(L.ECHO) == 7,
          "A1: p0..p3 = 0, 0, 1, 1 at the tail call, reader armed (cmd 9), state done, closed task called")
    check(p.r(L.WR_DONE) == 7, "A1: the writer's flag that stays (WR_DONE) holds the run id")
    wr = dict(zip(L.WR_FIELDS, [p.r(L.WR + n) for n in range(9)]))
    check(wr["written"] == 0xB0C3A5E1 and wr["readback"] == 0xB0C3A5E1 and wr["sa63_before"] == 0 and wr["sa65_before"] == 0x02000000
          and wr["pa0"] == 2, f"A1: the record holds the entry values, the value written and the read-back ({wr})")
    # A2
    p = alias_page(sa=(0, 2, 0x03000000))
    command(p, L.CMD_A2)
    wr = dict(zip(L.WR_FIELDS, [p.r(L.WR + n) for n in range(9)]))
    check(sa_now(p) == [0, 2, 0x03000000] and wr["written"] == 0x03000000 and wr["readback"] == 0x03000000,
          "A2: sa65 written with its own entry value, nothing else changes")
    # A3
    p = alias_page(sa=(0, 2, 0x03000000))
    steps, stub = command(p, L.CMD_A3, marker=0xB009C5DC)
    wr = dict(zip(L.WR_FIELDS, [p.r(L.WR + n) for n in range(9)]))
    check(sa_now(p) == [0, 2, 0x03000000] and wr["written"] == 0xB009C5DC and wr["readback"] == 0xB009C5DC
          and wr["readback2"] == 0x03000000, "A3: sa65 = marker, read back, restored to its entry value before the tail call")
    # A4: pa0 & ~2
    for pa0, want in ((2, 0), (3, 1), (0, 0), (6, 4)):
        p = alias_page()
        command(p, L.CMD_A4, pa=(pa0, 0x02000000, 0x01061A70))
        check(sa_now(p) == [0, want, 0x02000000] and p.r(L.WR + 6) == want,
              f"A4: sa64 = pa0 & ~2 ({pa0:#x} -> {want:#x})")
    # A5
    p = alias_page()
    command(p, L.CMD_A5, pa=(3, 0x02000000, 0x01061A70))
    check(sa_now(p) == [0, 3, 0x02000000], "A5: sa64 = pa0")
    # A6
    p = alias_page(preds=(0, 0, 1, 0))
    steps, stub = command(p, L.CMD_A6, ri=(0x11111111, 0x22222222, 0x33333333, 0x44444444))
    check(sa_now(p) == [0, 2, 0x02000000], "A6: no sa register is written")
    check((p.m.get("r", 20), p.m.get("r", 21), p.m.get("i", 0), p.m.get("i", 1)) == (0x11111111, 0x22222222, 0x33333333, 0x44444444),
          "A6: r20, r21, i0, i1 = the markers")
    check(p.preds()[:2] == (1, 1) and p.preds()[2:] == (1, 0) and stub == 0 and p.r(L.CMD) == 9,
          f"A6: p0 = p1 = 1 at the tail call, p2 and p3 as at entry ({p.preds()}), reader armed")
    # restore
    p = alias_page(sa=(0xB0C3A5E1, 2, 0x02000000))
    command(p, L.CMD_RESTORE63, marker=0)
    check(sa_now(p) == [0, 2, 0x02000000], "cmd 7: sa63 restored to the host's value")
    # unknown command is a plain tail call
    p = alias_page()
    _, stub = command(p, 8)
    check(stub == 0 and sa_now(p) == [0, 2, 0x02000000] and p.r(L.CMD) == 8, "an unknown command (8) tail-calls and writes nothing")
    # every command touches only its own sa set
    for cmd, want in L.CMD_SA.items():
        p = alias_page(sa=(0x1111, 2, 0x02000000))
        before = sa_now(p)
        command(p, cmd, marker=0xABCD0001, ri=(1, 2, 3, 4), pa=(2, 0x02000000, 0x01061A70))
        changed = [f"sa{n}" for n, b, a in zip((63, 64, 65), before, sa_now(p)) if a != b]
        check(set(changed) <= set(want), f"command {cmd}: the sa registers it changed ({changed}) are within {want}")
    # the pass counter counts every pass of every command
    p = alias_page()
    for _ in range(5):
        command(p, 0)
    check(p.r(L.A_PASS) == 5, "the pass counter counts 5 passes")


# ---- ring_skip.s ---------------------------------------------------------------------------------------------------------
def test_skip_blob():
    info = json.loads((R3 / "bins" / "blobs.json").read_text())["ring_skip"]
    blob = (R3 / "bins" / "ring_skip.blob").read_bytes()
    regs = fwtask.load_regs()
    check(fwtask.build_blob_text((R3 / "asm" / "ring_skip.s").read_text(), regs) == blob,
          "asm/ring_skip.s assembles and passes the landed verifier to exactly bins/ring_skip.blob")
    check(info["str"] == 0 and info["sa_writes"] == [] and info["ldr"] == ["#81"], "ring_skip: no str, no sa write, ldr of #81 only")


def test_skip():
    p = Page("ring_skip")
    _, stub = p.pass_(0, TICK, 1000)
    check(stub == 0 and p.ring(0) == [] and p.r(L.A_PASS) == 1, "window 0: counted, not logged, the closed task called")
    p.w(L.SKIP, 3)
    p.pass_(0, TICK, 1100)
    check(p.r(L.SKIP) == 3 and p.r(L.SKIPPED) == 0, "window 0 never skips")
    p.w(L.WINDOW, 1)
    _, stub = p.pass_(0, TICK, 1200)
    check(stub == 0 and p.r(L.SKIP) == 3 and p.ring(0) == [], "window 1 never skips (and filters a plain tick)")
    p.w(L.WINDOW, 2)
    _, stub = p.pass_(0, TICK, 2000)
    check(stub is None and p.r(L.SKIP) == 2 and p.r(L.SKIPPED) == 1 and p.ring(0) == [(3,) + TICK + (2000,)],
          "window 2, SKIP 3: a plain tick is skipped: no closed-task call (nop.end), SKIP 2, SKIPPED 1, rung flag 3")
    _, stub = p.pass_(0, KICK, 2500)
    check(stub == 0 and p.r(L.SKIP) == 2 and p.ring(0)[-1] == (1,) + KICK + (2500,),
          "a kick pass is never skipped: logged with flag 1, closed task called")
    _, stub = p.pass_(0, (2, 0x00000200, 0x01061A70), 2600)
    check(stub == 0 and p.r(L.SKIP) == 2 and p.ring(0)[-1][0] == 1, "a tick with a bit in pa1[23:0] is not a plain tick: not skipped")
    for t in (3000, 4000):
        _, stub = p.pass_(0, TICK, t)
        check(stub is None, f"tick at {t}: skipped")
    check(p.r(L.SKIP) == 0 and p.r(L.SKIPPED) == 3, "SKIP ran down to 0, SKIPPED 3")
    _, stub = p.pass_(0, TICK, 5000)
    check(stub == 0 and p.ring(0)[-1] == (1,) + TICK + (5000,) and p.r(L.SKIPPED) == 3, "SKIP 0: the next tick is logged with flag 1 and the closed task called")
    check(p.r(L.A_PASS) == 9, f"every pass counted (9, got {p.r(L.A_PASS)})")
    # skip with a full ring: counted, still ends without the closed task
    q = Page("ring_skip")
    q.w(L.WINDOW, 2)
    for t in range(L.RUNGS[0]):
        q.pass_(0, KICK, 100 + t)
    q.w(L.SKIP, 1)
    _, stub = q.pass_(0, TICK, 9000)
    check(stub is None and q.r(L.SKIPPED) == 1 and q.r(L.DROP) == 1 and len(q.ring(0)) == L.RUNGS[0],
          "a skipped pass with the ring full: counted as a drop, SKIPPED 1, no closed-task call")
    for k in (1, 2, 3):
        q = Page("ring_skip")
        q.w(L.WINDOW, 2)
        q.w(L.SKIP, 4)
        for t in range(L.RUNGS[k] + 2):
            _, stub = q.pass_(k, (0, 0x200, 0x01061A70), t)
        check(len(q.ring(k)) == L.RUNGS[k] and q.r(L.DROP + k) == 2 and stub == k and q.r(L.SKIP) == 4,
              f"slot {k}: ring of {L.RUNGS[k]} then 2 drops, tail-call {k}, never skips")


# ---- ring_hold.blob (S2b's, unchanged) ------------------------------------------------------------------------------------
def test_hold():
    blob = (R3 / "bins" / "ring_hold.blob").read_bytes()
    check(hashlib.sha256(blob).hexdigest() == "fa0f79dbb5864187516febf9c96f6ceea944e5abf6ae69b5acbeb9ac8a0ac168",
          "bins/ring_hold.blob is S2b's, byte for byte (sha256 fa0f79db...)")
    regs = fwtask.load_regs()
    check(fwtask.verify_blob(blob, regs) == [], "ring_hold.blob passes the landed verifier")
    p = Page("ring_hold")
    p.w(L.WINDOW, 2)
    p.w(L.N_ITER, 7)
    p.w(L.CMD, 1)
    p.w(L.RUNID, 0x77)
    steps, stub = p.pass_(0, TICK, 5000)
    check(p.r(L.CMD) == 0 and p.r(L.STATE) == 2 and p.r(L.ECHO) == 0x77 and stub == 0 and p.r(L.HOLD_ENTRY) == 5000
          and p.r(L.HOLD_EXIT) == 5000, "ring_hold: cmd 1 with n = 7 holds, stamps, ends done and tail-calls")
    p2 = Page("ring_hold")
    p2.w(L.WINDOW, 2)
    p2.w(L.N_ITER, 7)
    p2.w(L.CMD, 1)
    s7, _ = p2.pass_(0, TICK, 5000)
    p3 = Page("ring_hold")
    p3.w(L.WINDOW, 2)
    p3.w(L.N_ITER, 107)
    p3.w(L.CMD, 1)
    s107, _ = p3.pass_(0, TICK, 5000)
    check(s107 - s7 == 100 * 3, f"ring_hold: a loop pass is 3 instructions ({s107 - s7} more for 100 more iterations)")
    check(L.n_for_ticks(L.K7_HOLD_TICKS) == 1508279, "K7's n for a 90-tick mid-period hold is 1508279 (S2b's e4l)")


def main():
    if not simrun.available() or not SIM.exists():
        print("SKIPPED, NOT PASSED: pysgx or the sgx-sim binary is not available")
        return 2
    test_alias_blob()
    test_alias_commands()
    test_skip_blob()
    test_skip()
    test_hold()
    print(f"{len(FAIL)} failed" if FAIL else "all sim checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
