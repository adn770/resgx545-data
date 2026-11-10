#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""sim_r3.py: the R3x-events blobs (bins/alias2.blob, bins/ring_end.blob, S2b's bins/ring_hold.blob as frozen) run in sgx-sim
(pysgx) with the landed simrun.py's bus and stand-in for the closed task.  What this proves: encodings, control flow,
patching, the command protocol of alias2.s (what each command writes, what it leaves alone, the predicates at its tail call,
the reader's record; the three new commands 10, 11, 12), the acted pass of ring_end.s (KIND, ACT, COUNT: flag 3 and nop.end without
the closed task, flag 4 and the tail call to slot 2, only the wanted pass, only window 2), the S2 ring behaviour of the other slots, the hold of ring_hold.blob at a small n.  What it does not: any hardware
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


# ---- alias2.s ------------------------------------------------------------------------------------------------------------
def alias_page(sa=(0, 2, 0x02000000), pclink=0x98, preds=(1, 1, 0, 0), r=(0, 0x3000), i=(0xB5000020, 0xB5000021)):
    p = Page("alias2")
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


def command(p, cmd, marker=0, ri=(0, 0, 0, 0), runid=7, pa=TICK, w65=0, w64=0, npass=0):
    p.w(L.CMD, cmd)
    p.w(L.STATE, 0)
    p.w(L.RUNID, runid)
    p.w(L.A_M, marker)
    p.w(L.W65, w65)
    p.w(L.W64, w64)
    p.w(L.NPASS, npass)
    for n, v in enumerate(ri):
        p.w(L.A_RI + n, v)
    return p.pass_(0, pa)


def sa_now(p):
    return [p.m.get("sa", n) for n in (63, 64, 65)]


def wr_of(p):
    return dict(zip(L.WR_FIELDS, [p.r(L.WR + n) for n in range(9)]))


def test_alias2_blob():
    info = json.loads((R3 / "bins" / "blobs.json").read_text())["alias2"]
    blob = (R3 / "bins" / "alias2.blob").read_bytes()
    regs = fwtask.load_regs()
    check(fwtask.build_blob_text((R3 / "asm" / "alias2.s").read_text(), regs) == blob,
          "asm/alias2.s assembles and passes the landed verifier to exactly bins/alias2.blob")
    check(fwtask.verify_blob(blob, regs) == [], "alias2.blob passes the landed verifier (fwtask.verify_blob)")
    check(info["str"] == 0 and info["ldr"] == [] and info["sa_writes"] == ["sa63", "sa64", "sa65"],
          "alias2: no str, no ldr, sa writes within sa63, sa64, sa65")
    check({int(k): v for k, v in info["cmd_sa"].items()} == L.CMD_SA2, "alias2: the sa write set of each command is r3layout.CMD_SA2")


def test_alias2_old_commands():
    """alias.s's commands (A rows) are unchanged in alias2.s: the same protocol."""
    p = alias_page()
    steps, stub = command(p, 0)
    check(stub == 0 and sa_now(p) == [0, 2, 0x02000000] and p.r(L.A_PASS) == 1 and p.r(L.CMD) == 0 and p.r(L.STATE) == 0,
          "cmd 0: one pass counted, the closed task called at once (slot 0), nothing written")
    p = alias_page(pclink=0x98, preds=(1, 1, 0, 0), r=(5, 0x3000), i=(0xAA, 0xBB))
    steps, stub = command(p, L.CMD_READ, pa=TICK)
    got = dict(zip(L.RD_FIELDS, [p.r(L.RD + n) for n in range(16)]))
    want = {"pclink": 0x98, "p0": 1, "p1": 1, "p2": 0, "p3": 0, "r20": 5, "r21": 0x3000, "i0": 0xAA, "i1": 0xBB, "sa64": 2,
            "sa65": 0x02000000, "sa63": 0, "pa0": 2, "pa1": 0x02000000, "pa2": 0x01061A70, "pass": 1}
    check(got == want, f"cmd 9 (reader): stores pclink, p0-p3, r20, r21, i0, i1, sa64, sa65, sa63, pa0-pa2, pass ({got})")
    check(stub == 0 and p.r(L.CMD) == 0 and p.r(L.STATE) == 2 and p.r(L.ECHO) == 7, "cmd 9: cmd = 0, state done, run id echoed, closed task called")
    p = alias_page()
    steps, stub = command(p, L.CMD_A1, marker=0xB0C3A5E1)
    check(sa_now(p) == [0xB0C3A5E1, 2, 0x02000000] and p.preds() == (0, 0, 1, 1) and stub == 0 and p.r(L.CMD) == 9,
          "A1 (cmd 1): sa63 = the marker, p0..p3 = 0, 0, 1, 1, reader armed")
    p = alias_page(sa=(0, 2, 0x03000000))
    steps, stub = command(p, L.CMD_A3, marker=0xB009C5DC)
    check(sa_now(p) == [0, 2, 0x03000000] and wr_of(p)["written"] == 0xB009C5DC and wr_of(p)["readback2"] == 0x03000000,
          "A3 (cmd 3): sa65 = marker, read back, restored before the tail call (D3 does NOT restore: cmd 10)")
    for pa0, want_ in ((2, 0), (3, 1), (0, 0), (6, 4)):
        p = alias_page()
        command(p, L.CMD_A4, pa=(pa0, 0x02000000, 0x01061A70))
        check(sa_now(p) == [0, want_, 0x02000000], f"A4 (cmd 4): sa64 = pa0 & ~2 ({pa0:#x} -> {want_:#x})")
    p = alias_page(preds=(0, 0, 1, 0))
    steps, stub = command(p, L.CMD_A6, ri=(0x11111111, 0x22222222, 0x33333333, 0x44444444))
    check(sa_now(p) == [0, 2, 0x02000000] and (p.m.get("r", 20), p.m.get("r", 21), p.m.get("i", 0), p.m.get("i", 1))
          == (0x11111111, 0x22222222, 0x33333333, 0x44444444) and p.preds() == (1, 1, 1, 0), "A6 (cmd 6): r20, r21, i0, i1, p0 = p1 = 1, no sa write")
    p = alias_page(sa=(0xB0C3A5E1, 2, 0x02000000))
    command(p, L.CMD_RESTORE63, marker=0)
    check(sa_now(p) == [0, 2, 0x02000000], "cmd 7: sa63 restored to the host's value (the baseline after a stop)")
    p = alias_page()
    _, stub = command(p, 8)
    check(stub == 0 and sa_now(p) == [0, 2, 0x02000000] and p.r(L.CMD) == 8, "an unknown command (8) tail-calls and writes nothing")


def test_alias2_cmd10():
    """C1-C4, D1-D3: sa65 = the host's word, LEFT in place."""
    for word in (0x02800000, 0xB0000000, 0x0201C04C, 0x02080000, 0xB009C4DC, 0x02000100, 0xB009C5DC):
        p = alias_page(sa=(0, 2, 0x02000000))
        steps, stub = command(p, L.CMD_WORD65, w65=word)
        w = wr_of(p)
        check(sa_now(p) == [0, 2, word] and w["written"] == word and w["readback"] == word and w["sa65_before"] == 0x02000000,
              f"cmd 10: sa65 = {word:#010x}, left in place (not restored), the record holds the entry value, the word and the read-back")
        check(p.preds() == (0, 0, 1, 1) and stub == 0 and p.r(L.CMD) == 9 and p.r(L.STATE) == 2 and p.r(L.ECHO) == 7 and p.r(L.WR_DONE) == 7,
              f"cmd 10 ({word:#x}): p0..p3 = 0, 0, 1, 1 at the tail call, reader armed, state done, flag WR_DONE, closed task called")
    p = alias_page()
    command(p, L.CMD_WORD65, w65=0xB009C5DC)
    steps, stub = command(p, L.CMD_READ)
    rd = dict(zip(L.RD_FIELDS, [p.r(L.RD + n) for n in range(16)]))
    check(rd["sa65"] == 0xB009C5DC and rd["sa64"] == 2 and p.r(L.CMD) == 0 and p.r(L.RD + 15) == 2,
          "cmd 10 then the reader: sa65 still holds the word the writer left (nothing restored it), the reader ran (cmd 0, pass 2)")
    check(L.word65({"k": 1, "or": 0x800000}, 2) == 0x02800000 and L.word65({"lit": 0xB0000000}, 2) == 0xB0000000
          and L.word65({"k": 1, "or": 0x100}, 0xB0) == 0xB0000100 and L.word65(None, 2) is None, "L.word65: K << 24 | the row's bits, or the literal")


def test_alias2_cmd11():
    """D4: E537's combination."""
    e = L.E537
    p = alias_page(preds=(0, 0, 1, 0), sa=(0, 2, 0x02000000))
    steps, stub = command(p, L.CMD_E537, marker=e["sa63"], w64=e["sa64"], w65=e["sa65"], ri=(e["r20"], e["r21"], e["i0"], e["i1"]))
    check(sa_now(p) == [e["sa63"], e["sa64"], e["sa65"]], f"cmd 11: sa63, sa64, sa65 = E537's words ({sa_now(p)})")
    check((p.m.get("r", 20), p.m.get("r", 21), p.m.get("i", 0), p.m.get("i", 1)) == (e["r20"], e["r21"], e["i0"], e["i1"]),
          "cmd 11: r20, r21, i0, i1 = E537's words")
    check(p.preds()[:2] == (1, 1) and p.preds()[2:] == (1, 0) and stub == 0 and p.r(L.CMD) == 9,
          f"cmd 11: p0 = p1 = 1 at the tail call, p2 and p3 as at entry ({p.preds()}), reader armed, closed task called")
    w = wr_of(p)
    x = [p.r(L.WR_X + n) for n in range(4)]
    check(w["written"] == e["sa65"] and w["readback"] == e["sa65"] and x == [e["sa63"], e["sa63"], e["sa64"], e["sa64"]],
          f"cmd 11: the record holds sa65 written and read back, sa63 and sa64 written and read back ({x})")
    check(w["sa63_before"] == 0 and w["sa64_before"] == 2 and w["sa65_before"] == 0x02000000, "cmd 11: the entry values of the three sa registers")


def test_alias2_cmd12():
    """C5: sa64 = pa0 & ~2 on N consecutive passes, the reader armed on the last."""
    p = alias_page()
    seq = []
    for k in range(3):
        steps, stub = command(p, L.CMD_RUN64, npass=3, pa=TICK) if k == 0 else p.pass_(0, TICK)
        seq.append((p.r(L.NPASS), p.r(L.CMD), stub, sa_now(p)[1], p.preds(), p.r(L.WR_DONE)))
    check([s[0] for s in seq] == [2, 1, 0], f"cmd 12: NPASS counts 3 -> 2 -> 1 -> 0 over three passes ({[s[0] for s in seq]})")
    check([s[1] for s in seq] == [12, 12, 9], f"cmd 12: the command stays 12 until the last pass, which arms the reader (cmd 9): {[s[1] for s in seq]}")
    check(all(s[2] == 0 for s in seq) and all(s[3] == 0 for s in seq), "cmd 12: sa64 = pa0 & ~2 = 0 on every pass, the closed task called every pass")
    check(all(s[4] == (0, 0, 1, 1) for s in seq), f"cmd 12: p0..p3 = 0, 0, 1, 1 at every tail call, as A4's ({[s[4] for s in seq]})")
    check([s[5] for s in seq] == [0, 0, 7] and p.r(L.A_PASS) == 3, "cmd 12: the writer's flag (WR_DONE) is set only on the last pass; the pass counter counted all 3")
    steps, stub = p.pass_(0, TICK)
    check(p.r(L.CMD) == 0 and p.r(L.RD + 15) == 4, "cmd 12: the next pass is the reader (cmd 9 -> 0), pass count 4 in its record")
    p = alias_page()
    _, stub = command(p, L.CMD_RUN64, npass=0)
    check(stub == 0 and p.r(L.CMD) == 12 and sa_now(p) == [0, 2, 0x02000000] and p.r(L.NPASS) == 0,
          "cmd 12 with NPASS 0: a plain tail call, nothing written")
    p = alias_page()
    command(p, L.CMD_RUN64, npass=1, pa=(3, 0x02000000, 0x01061A70))
    check(sa_now(p)[1] == 1 and wr_of(p)["written"] == 1, "cmd 12: pa0 = 3 -> sa64 = 1 (pa0 & ~2)")


def test_alias2_sa_sets():
    for cmd, want in L.CMD_SA2.items():
        p = alias_page(sa=(0x1111, 2, 0x02000000))
        before = sa_now(p)
        command(p, cmd, marker=0xABCD0001, ri=(1, 2, 3, 4), w65=0xABCD0002, w64=0xABCD0003, npass=2, pa=(2, 0x02000000, 0x01061A70))
        changed = [f"sa{n}" for n, b, a in zip((63, 64, 65), before, sa_now(p)) if a != b]
        check(set(changed) <= set(want), f"command {cmd}: the sa registers it changed ({changed}) are within {want}")
    p = alias_page()
    for _ in range(5):
        command(p, 0)
    check(p.r(L.A_PASS) == 5, "the pass counter counts 5 passes")


# ---- ring_end.s ----------------------------------------------------------------------------------------------------------
def test_end_blob():
    info = json.loads((R3 / "bins" / "blobs.json").read_text())["ring_end"]
    blob = (R3 / "bins" / "ring_end.blob").read_bytes()
    regs = fwtask.load_regs()
    check(fwtask.build_blob_text((R3 / "asm" / "ring_end.s").read_text(), regs) == blob,
          "asm/ring_end.s assembles and passes the landed verifier to exactly bins/ring_end.blob")
    check(fwtask.verify_blob(blob, regs) == [], "ring_end.blob passes the landed verifier (fwtask.verify_blob)")
    check(info["str"] == 0 and info["sa_writes"] == [] and info["ldr"] == ["#81"], "ring_end: no str, no sa write, ldr of #81 only")
    pb = fwtask.parse_blob(blob)
    conts = sorted(p.kind for p in pb.patches if p.kind.startswith("cont"))
    check(conts == ["cont0", "cont1", "cont2", "cont2", "cont3"] and len(pb.words) <= 1024,
          f"ring_end: a continue patch an entry plus one cont2 in entry 0 (the ACT 2 triple), {len(pb.words)} words ({conts})")
    check(fwtask.apply_patches(pb.words, pb.patches, RES, {k: 5000 + 8 * k for k in range(4)}) != pb.words,
          "the landed overlay model patches every continue slot of the blob (the kernel's own overlay is not provable offline)")


def end_page(kind, act, count, window=2):
    p = Page("ring_end")
    p.w(L.WINDOW, window)
    p.w(L.KIND, kind)
    p.w(L.ACT, act)
    p.w(L.COUNT, count)
    return p


def test_end():
    p = Page("ring_end")
    _, stub = p.pass_(0, TICK, 1000)
    check(stub == 0 and p.ring(0) == [] and p.r(L.A_PASS) == 1, "window 0: counted, not logged, the closed task called")
    # X1: KIND 1, ACT 2 (tail to slot 2), COUNT 1
    p = end_page(1, 2, 1)
    _, stub = p.pass_(0, TICK, 2000)
    check(stub == 2 and p.ring(0) == [(4,) + TICK + (2000,)] and p.r(L.COUNT) == 0 and p.r(L.ACTED) == 1,
          "X1: a plain tick is acted on: logged first with flag 4, COUNT 0, ACTED 1, the closed task of SLOT 2 tail-called (cont2)")
    _, stub = p.pass_(0, TICK, 3000)
    check(stub == 0 and p.ring(0)[-1] == (1,) + TICK + (3000,) and p.r(L.ACTED) == 1, "X1: the next tick is logged with flag 1 and tail-calls slot 0 as ever")
    # B3-like: KIND 2, ACT 1: a kick pass ends with nop.end
    p = end_page(2, 1, 1)
    _, stub = p.pass_(0, TICK, 2000)
    check(stub == 0 and p.r(L.COUNT) == 1 and p.ring(0)[-1][0] == 1, "KIND 2: a tick pass is not acted on")
    _, stub = p.pass_(0, KICK, 2500)
    check(stub is None and p.ring(0)[-1] == (3,) + KICK + (2500,) and p.r(L.COUNT) == 0 and p.r(L.ACTED) == 1,
          "B3: a kick pass (pa0 = 0, pa1[23:0] = 0x100) is acted on: logged with flag 3, own end (nop.end), no closed-task call")
    _, stub = p.pass_(0, TICK, 3000)
    check(stub == 0, "after COUNT ran down the next tick tail-calls the closed task")
    for pa in ((0, 0x02000300, 0), (0, 0x02000101, 0), (2, 0x02000100, 0), (1, 0x02000100, 0), (0, 0x02000000, 0)):
        p = end_page(2, 1, 1)
        _, stub = p.pass_(0, pa, 100)
        check(stub == 0 and p.r(L.COUNT) == 1 and p.r(L.ACTED) == 0, f"KIND 2: pa {tuple(hex(x) for x in pa)} is not a kick pass: not acted on")
    # KIND 1 does not act on a kick or a tick with a bit
    for pa in (KICK, (2, 0x02000200, 0x01061A70), (0, 0x02000000, 0), (3, 0x02000000, 0)):
        p = end_page(1, 1, 1)
        _, stub = p.pass_(0, pa, 100)
        check(stub == 0 and p.r(L.ACTED) == 0, f"KIND 1: pa {tuple(hex(x) for x in pa)} is not a plain tick: not acted on")
    p = end_page(3, 1, 1)
    _, stub = p.pass_(0, TICK, 100)
    check(stub == 0 and p.r(L.ACTED) == 0, "KIND 3 (not a kind): never acts")
    p = end_page(1, 1, 0)
    _, stub = p.pass_(0, TICK, 100)
    check(stub == 0 and p.r(L.ACTED) == 0, "COUNT 0: never acts")
    # window 1 never acts; window 0 never
    for w in (0, 1):
        p = end_page(1, 1, 3, window=w)
        _, stub = p.pass_(0, TICK, 100)
        check(stub == 0 and p.r(L.COUNT) == 3, f"window {w}: never acts")
    # X20: twenty consecutive acted passes, the ring fills (16 rungs) and the rest are drops, every one still acted
    p = end_page(1, 2, 20)
    stubs = [p.pass_(0, TICK, 1000 + 25 * t)[1] for t in range(21)]
    check(stubs[:20] == [2] * 20 and stubs[20] == 0 and p.r(L.ACTED) == 20 and p.r(L.COUNT) == 0 and p.r(L.DROP) == 5
          and len(p.ring(0)) == 16 and all(r[0] == 4 for r in p.ring(0)),
          "X20: 20 consecutive acted passes all tail-call slot 2, 16 are logged (flag 4), 4 counted as drops (5 with the plain 21st)")
    # a skipped (own-end) pass with the ring full
    q = end_page(1, 1, 1)
    for t in range(L.RUNGS[0]):
        q.pass_(0, KICK, 100 + t)
    _, stub = q.pass_(0, TICK, 9000)
    check(stub is None and q.r(L.ACTED) == 1 and q.r(L.DROP) == 1, "an own-end pass with the ring full: counted as a drop, ACTED 1, no closed-task call")
    # the other slots never act
    for k in (1, 2, 3):
        q = end_page(1, 1, 4)
        for t in range(L.RUNGS[k] + 2):
            _, stub = q.pass_(k, (0, 0x200, 0x01061A70), t)
        check(len(q.ring(k)) == L.RUNGS[k] and q.r(L.DROP + k) == 2 and stub == k and q.r(L.COUNT) == 4, f"slot {k}: ring then 2 drops, tail-call {k}, never acts")


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
    test_alias2_blob()
    test_alias2_old_commands()
    test_alias2_cmd10()
    test_alias2_cmd11()
    test_alias2_cmd12()
    test_alias2_sa_sets()
    test_end_blob()
    test_end()
    test_hold()
    print(f"{len(FAIL)} failed" if FAIL else "all sim checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
