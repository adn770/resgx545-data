#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""sim_c3.py: C3's blob (bins/start.blob as frozen) run in sgx-sim (pysgx) with the landed simrun.py's bus and stand-in for the
closed task.  What this proves: encodings, control flow, patching, the command protocol of start.s (what the writer writes and
leaves alone, the predicates at its tail call, the reader's record, the sa registers it only reads, no other register changed).
What it does not: any hardware behaviour (the closed task is a stub that records that it was called).  Every command path of the
blob runs here.  Exit 0 when every check holds.

    ../../closing/pixel-faults/.venv/bin/python tests/sim_c3.py
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
import c3layout as L  # noqa: E402
import c3blobs as B  # noqa: E402

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




TICK = (2, 0x02000000, 0x01061A70)


def start_page(sa=None, pclink=0x98, preds=(1, 1, 0, 0), r=(0, 0x3000), i=(0xB5000020, 0xB5000021)):
    p = Page("start")
    for n, v in (sa or {63: 0, 64: 2, 65: 0x02000000, 100: 0xA5000064, 127: 0xA500007F, 20: 0, 24: 0}).items():
        p.m.set("sa", n, v)
    p.set_pclink(pclink)
    for n, v in enumerate(preds):
        p.m.set_pred(n, bool(v))
    p.m.set("r", 20, r[0])
    p.m.set("r", 21, r[1])
    p.m.set("i", 0, i[0])
    p.m.set("i", 1, i[1])
    return p


def command(p, cmd, marker=0, ri=(0, 0, 0, 0), flags=(0, 0, 0, 0), runid=7, pa=TICK):
    p.w(L.CMD, cmd)
    p.w(L.STATE, 0)
    p.w(L.RUNID, runid)
    p.w(L.A_M, marker)
    for n, v in enumerate(ri):
        p.w(L.A_RI + n, v)
    for n, v in enumerate(flags):
        p.w(L.PF + n, v)
    return p.pass_(0, pa)


def sa_now(p, ns=(63, 64, 65, 100, 127, 20, 24)):
    return [p.m.get("sa", n) for n in ns]


def rd_of(p):
    return dict(zip(L.RD_FIELDS, [p.r(L.RD + n) for n in range(len(L.RD_FIELDS))]))


def test_blob():
    info = json.loads((R3 / "bins" / "blobs.json").read_text())["start"]
    blob = (R3 / "bins" / "start.blob").read_bytes()
    regs = fwtask.load_regs()
    check(fwtask.build_blob_text((R3 / "asm" / "start.s").read_text(), regs) == blob,
          "asm/start.s assembles and passes the landed verifier to exactly bins/start.blob")
    check(info["str"] == 0 and info["ldr"] == [] and info["sa_writes"] == ["sa63"],
          "start: no str, no ldr, the only sa write is sa63")
    check({int(k): v for k, v in info["cmd_sa"].items()} == L.CMD_SA, "start: the sa write set of each command is c3layout.CMD_SA")
    check(fwtask.parse_blob(blob).entries == [0], "start: one entry (own_arm slots=0x1 entry=0)")


def test_commands():
    p = start_page()
    before = sa_now(p)
    steps, stub = command(p, 0)
    check(stub == 0 and sa_now(p) == before and p.r(L.A_PASS) == 1 and p.r(L.CMD) == 0 and p.r(L.STATE) == 0,
          "cmd 0: one pass counted, the closed task called at once, nothing written")
    check((p.m.get("r", 20), p.m.get("r", 21), p.m.get("i", 0), p.m.get("i", 1)) == (0, 0x3000, 0xB5000020, 0xB5000021),
          "cmd 0: r20, r21, i0, i1 untouched")
    # the reader: the entry values of the previous pass are what it stores; sa100 etc. are read as they are
    p = start_page(pclink=0x98, preds=(1, 1, 0, 0), r=(5, 0x3000), i=(0xAA, 0xBB),
                   sa={63: 0x11, 64: 2, 65: 0x02000000, 100: 0xC0FFEE01, 127: 0xC0FFEE7F, 20: 0x20, 24: 0x24})
    before = sa_now(p)
    steps, stub = command(p, L.CMD_READ)
    got = rd_of(p)
    want = {"pclink": 0x98, "p0": 1, "p1": 1, "p2": 0, "p3": 0, "r20": 5, "r21": 0x3000, "i0": 0xAA, "i1": 0xBB, "sa63": 0x11,
            "sa64": 2, "sa65": 0x02000000, "sa100": 0xC0FFEE01, "sa127": 0xC0FFEE7F, "sa20": 0x20, "sa24": 0x24, "pa0": 2,
            "pa1": 0x02000000, "pa2": 0x01061A70, "pass": 1}
    check(got == want, f"cmd 9 (reader): stores the entry values and the seven sa registers ({got})")
    check(sa_now(p) == before, "cmd 9: no sa register changes (sa100, sa127, sa20, sa24 are only read)")
    check(stub == 0 and p.r(L.CMD) == 0 and p.r(L.STATE) == 2 and p.r(L.ECHO) == 7,
          "cmd 9: cmd = 0, state done, run id echoed, closed task called")
    # the writer
    for flags in L.FLAGS:
        p = start_page(preds=(1, 1, 1, 1))
        ri = (0x11111111, 0x22222222, 0x33333333, 0x44444444)
        steps, stub = command(p, L.CMD_W, marker=0xB0C3A5E1, ri=ri, flags=flags)
        sa = dict(zip((63, 64, 65, 100, 127, 20, 24), sa_now(p)))
        check(sa == {63: 0xB0C3A5E1, 64: 2, 65: 0x02000000, 100: 0xA5000064, 127: 0xA500007F, 20: 0, 24: 0},
              f"writer: sa63 = the marker, no other sa register changes ({flags})")
        check((p.m.get("r", 20), p.m.get("r", 21), p.m.get("i", 0), p.m.get("i", 1)) == ri, f"writer: r20, r21, i0, i1 = the markers ({flags})")
        check(p.preds() == tuple(int(bool(f)) for f in flags), f"writer: p0..p3 = the host's flags at the tail call ({flags}, {p.preds()})")
        check(stub == 0 and p.r(L.CMD) == 9 and p.r(L.STATE) == 2 and p.r(L.ECHO) == 7 and p.r(L.WR_DONE) == 7,
              "writer: reader armed (cmd 9), state done, run id echoed and kept in WR_DONE, closed task called")
    wr = dict(zip(L.WR_FIELDS, [p.r(L.WR + n) for n in range(len(L.WR_FIELDS))]))
    check(wr == {"pa0": 2, "pa1": 0x02000000, "pa2": 0x01061A70, "sa63_before": 0, "sa63_written": 0xB0C3A5E1,
                 "sa63_readback": 0xB0C3A5E1}, f"writer: the record holds the entry words and the sa63 values ({wr})")
    # the reader armed by the writer reads what the writer left (the next pass, closed task in between is the stub)
    p = start_page()
    command(p, L.CMD_W, marker=0xB0C3A5E1, ri=(1, 2, 3, 4), flags=(0, 1, 0, 1))
    steps, stub = command(p, L.CMD_READ, runid=7)
    got = rd_of(p)
    check(got["sa63"] == 0xB0C3A5E1 and (got["r20"], got["r21"], got["i0"], got["i1"]) == (1, 2, 3, 4) and got["pass"] == 2,
          f"writer then reader: the reader sees sa63, r20, r21, i0, i1 as written, pass count 2 ({got})")
    p = start_page()
    steps, stub = command(p, 8)
    check(stub == 0 and sa_now(p) == [0, 2, 0x02000000, 0xA5000064, 0xA500007F, 0, 0] and p.r(L.CMD) == 8,
          "an unknown command is a plain tail call that changes nothing")


def main():
    if not simrun.available() or not SIM.exists():
        print("SKIPPED, NOT PASSED: pysgx or the sgx-sim binary is not available")
        return 2
    test_blob()
    test_commands()
    print(f"{len(FAIL)} failed" if FAIL else "all sim checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
