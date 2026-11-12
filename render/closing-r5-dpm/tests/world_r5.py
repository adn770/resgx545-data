#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""world_r5.py: synthetic worlds of R5-dpm for the runner mock and the scorer tests.  A world answers a job BY ITS ARGV (the command
the runner actually ran: target size, scene, vertices, move) and the knob the runner wrote (render_pb_pages in the fake debugfs),
never by its case name (round 4's slip o2: a control run with the default triangle must look like the default triangle).

    world_r5.py job ARGS...      (the fake tool) print the tool's overflow line and the regtimeline block; write buf09 to the fake debugfs;
                                 with the own task armed (own_arm in the fake debugfs) also the results page (sgx-sim through
                                 tests/simring.py) to own_res.json
Environment: SGXFIVE_DEBUGFS (the fake debugfs directory), FAKE_WORLD (the spec, see World.from_spec).

The world (spec keys, comma separated key=value):
  hyp=pend|block|noise   the S cells: pend (grow, the guard on count - 1: S2/S3 raise, S4/S5 silent), block (grow, silent), noise (no grow
                         anywhere: the guard as off a step); default pend
  shift=N                every step of every target moved by N pages (the runner must read the steps from the calibration, not the table);
                         the flips (LAST_RAISE) stay the table's
  skip2=1                the 2048x2048 scene shows no step 2 (a calibration whose steps are not monotone)
  kskew=N                the job's 0x0624 reads thr0 + N (the knob proof fails)
  tail=0|1               H-TAIL (default 1): the last m - 1 pages before a step leave one global page fewer
  d=FRACTION             the count rule's d of the B scenes (default 7/4, H-CNT); uoff=SCENE:N adds N to that scene's page need
  x734=1                 0x0734 bit 0 set in every sample (H-GREQ's register clause fails)
  flip=PATTERN           a probe job whose args contain PATTERN at the knob of flipP=0xP reads the other class (a control off)
  bits=pend|block|bit9   the sa8/sa9 words of the A3 rungs (default: as hyp)
  stall=N[+M]            the Nth (and Mth) armed job leaves the EDM stalled (fake fwtask_run.py status reads it)
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import struct
import sys
from fractions import Fraction as F

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
KP = HERE.parent
sys.path[:0] = [str(KP / "gen"), str(KP / "run"), str(HERE)]
import hu1  # noqa: E402
import r5plan as P  # noqa: E402

RT_REGS = [0x012C, 0x0624, 0x0628, 0x0658, 0x0660, 0x0700, 0x070C, 0x0710, 0x0720, 0x0724, 0x0728, 0x072C, 0x0730, 0x0734, 0x0748, 0x0A74]
NEED1500 = {(2048, 2048): 0x213, (4096, 4096): 0x84C, (4096, 2048): 0x426, (2048, 4096): 0x426, (3072, 3072): 0x4AB}


def parse_args(args: str):
    g = lambda k, d=None: (re.search(rf"--{k} (\d+)", args) or [None, d])[1]
    mv = re.search(r"--move 1:(-?\d+),(-?\d+)", args)
    return dict(w=int(g("width", 64)), h=int(g("height", 64)), vertices=int(g("vertices", 0) or 0), probe=args.startswith("probe"),
                move=(int(mv.group(1)), int(mv.group(2))) if mv else (0, 0))


class World:
    def __init__(self, spec=""):
        kv = dict(p.split("=", 1) for p in spec.split(",") if p)
        self.hyp = kv.get("hyp", "pend")
        self.shift = int(kv.get("shift", "0"))
        self.tail = kv.get("tail", "1") == "1"
        self.d = F(kv["d"]) if "d" in kv else F(7, 4)
        self.uoff = {}
        if "uoff" in kv:
            sc, n = kv["uoff"].split(":")
            self.uoff[sc] = int(n)
        self.x734 = kv.get("x734") == "1"
        self.flip, self.flipP = kv.get("flip"), (int(kv["flipP"], 0) if "flipP" in kv else None)
        self.bits = kv.get("bits", self.hyp)
        self.stall = [int(x) for x in kv.get("stall", "0").split("+")]
        self.kskew = int(kv.get("kskew", "0"))
        self.skip2 = kv.get("skip2") == "1"

    def steps(self, wh):
        s = {k: v + self.shift for k, v in P.STEPS[wh].items()}
        if self.skip2 and wh == (2048, 2048):
            s.pop(2)
        return s

    def last_raise(self, wh):
        return P.LAST_RAISE[wh]

    # ---------------------------------------------------------------------------------------------- 1500-vertex jobs
    def dpm(self, wh, thr0, args=""):
        """(grow, raised, gps_abort, gps_left) of a 1500-vertex job at thr0."""
        s = self.steps(wh)
        on = thr0 in s.values() and self.hyp != "noise"
        g = 1 + sum(1 for v in s.values() if v < thr0)
        s3 = s.get(3, P.STEPS[wh][3])
        nxt = min((v for v in s.values() if v > thr0), default=None)
        m = P.M_TAIL[wh]
        left = 2 if g >= 2 else 1
        if self.tail and nxt is not None and nxt - thr0 <= m - 1:
            left -= 1
        if on:
            k = next(k for k, v in s.items() if v == thr0)
            raised = self.hyp == "pend" and k <= 3
        elif thr0 < s3:
            raised = True
        else:
            raised = thr0 <= self.last_raise(wh)
        if self.flip and self.flip in args and self.flipP is not None and thr0 + P.D_OFF == self.flipP:
            raised = not raised
        return on, raised, g, left

    def need_b(self, a):
        U = hu1.hu1(a["w"], a["h"], hu1.moved(a["w"], a["h"], *a["move"]))[0]
        sc = next((k for k, mv in P.B_MOVES.items() if mv == a["move"]), None)
        return U + self.uoff.get(sc, 0)


def row(vals):
    return [vals.get(r, 0) for r in RT_REGS]


def timeline(rows, rc=3):
    t = ["timeline: regs " + " ".join(f"0x{r:04x}" for r in RT_REGS) + f" samples {len(rows)} seconds 0 start 100 end {100 + 10 * len(rows)} rc {rc}"]
    t += [f"tl {100 + 10 * i} " + " ".join(f"{v:08x}" for v in r) for i, r in enumerate(rows)]
    return "\n".join(t) + "\n"


def job_1500(world: World, a, thr0):
    wh = (a["w"], a["h"])
    s = world.steps(wh)
    need = NEED1500[wh]
    grow, raised, g_ab, left = world.dpm(wh, thr0, a.get("args", ""))
    x734 = 1 if world.x734 else 0
    rows = [row({0x0624: 0x400, 0x0628: 0x100F0})]
    g = 1
    first = min(thr0, need)
    for p in range(1, first + 1):
        g = max([1] + [k for k, v in s.items() if v < p])     # the highest global page asked for (skip2: 1 to 3 at once)
        v628 = 0x10003 if (grow and p >= first - 1) else (0x10000 | thr0)
        rows.append(row({0x0624: thr0 + world.kskew, 0x0628: v628, 0x0720: 1, 0x0724: (p << 16) | p, 0x072C: (g << 16) | g, 0x0734: x734}))
    nparts = 0
    if thr0 < need:
        nparts = 1
        for _ in range(2):
            rows.append(row({0x0624: thr0, 0x0628: 0x10000 | thr0, 0x0658: 1, 0x0720: 1, 0x0724: (first << 16) | first, 0x072C: (left << 16) | left, 0x0734: x734}))
        t2 = thr0 + 0x20 if raised else thr0
        rest = need - thr0
        run2 = min(t2, rest + 1)
        for p in range(1, run2 + 1):
            rows.append(row({0x0624: t2, 0x0628: 0x10000 | t2, 0x0720: 1, 0x0724: (p << 16) | p, 0x072C: (2 << 16) | 2}))
        if rest + 1 > t2:
            nparts = 2
            for _ in range(2):
                rows.append(row({0x0624: t2, 0x0658: 1, 0x0720: 1, 0x0724: (run2 << 16) | run2, 0x072C: 0x10001}))
            for p in range(1, 9):
                rows.append(row({0x0624: t2, 0x0720: 1, 0x0724: (p << 16) | p, 0x072C: 0x10001}))
    rows.append(row({0x0624: thr0}))
    buf = [0] * 59
    buf[38] = 0x20 if (raised and nparts) else 0
    buf[36] = max(g_ab - 2, 0)
    over = thr0 < need
    return timeline(rows), buf, over, dict(grow=grow, raised=raised and bool(nparts), nparts=nparts)


def job_tri(world: World, a, thr0):
    U = world.need_b(a)
    rows = [row({0x0624: 0x400})]
    n = 0
    if thr0 < U:
        n = P.cnt(thr0, U, world.d)
        t = thr0
        for i in range(n):
            for p in range(1, t + 1):
                rows.append(row({0x0624: t, 0x0628: 0x10000 | t, 0x0720: 1, 0x0724: (p << 16) | p, 0x072C: 0x10001}))
            rows.append(row({0x0624: t, 0x0658: 1, 0x0720: 1, 0x0724: (t << 16) | t, 0x072C: 0x10001}))
            t = thr0 + 0x20
        for p in range(1, 6):
            rows.append(row({0x0624: t, 0x0720: 1, 0x0724: (p << 16) | p, 0x072C: 0x10001}))
    else:
        for p in range(1, U + 1):
            rows.append(row({0x0624: thr0, 0x0628: 0x10000 | thr0, 0x0720: 1, 0x0724: (p << 16) | p, 0x072C: 0x10001}))
    rows.append(row({0x0624: thr0}))
    buf = [0] * 59
    return timeline(rows), buf, thr0 < U, dict(nparts=n, U=U)


def a3_events(world: World, a, thr0, info):
    """The event passes of an armed job: (slot, pa0, pa1, sa8, sa9, timer).  First OOM entry (abort), TA terminated, end of render (sa9
    bit 8 by the bits world), the decision OOM entry (sa8 bits 7, 8, 9 by the world), the next OOM entry, TA finished, end of render."""
    wh = (a["w"], a["h"])
    raised = info.get("raised", False)
    grow = info.get("grow", False)
    mode = world.bits
    sa9_eor = 0x100 if (grow and mode == "block") else 0
    if mode == "bit9":
        dec = 0x380
    else:
        dec = 0x180 if raised else 0
    ev = [(1, 0, 0x02000100, 0, 0, 1000)]                         # a kick (not logged: no bit of the mask)
    if grow:
        ev.append((2, 3, 0x00200000, 0x0, 0x1, 1100))              # the grow entry (bit 21)
    ev += [(2, 3, 0x00100000, 0x80000, 0x1, 1200),                 # the first OOM entry (bit 20): abort
           (2, 4, 0x00000400, 0x20, 0x1, 1300),                    # TA terminated (bit 10)
           (3, 5, 0x00000010, 0x0, sa9_eor, 1400),                 # end of the partial render (bit 4)
           (2, 3, 0x00100000, 0x80000 | dec, 0x1, 1500)]           # the decision entry
    if raised:
        ev.append((2, 3, 0x00100000, 0x80000 | 0x380, 0x1, 1600))  # the entry after the raise
    ev += [(2, 6, 0x00000200, 0x0, 0x0, 1700), (3, 5, 0x00000010, 0x0, 0x0, 1800), (0, 2, 0x02000000, 0, 0, 1900)]
    return ev


def main(argv):
    mode, args = argv[1], " ".join(argv[2:])
    world = World(os.environ.get("FAKE_WORLD", ""))
    dbg = pathlib.Path(os.environ["SGXFIVE_DEBUGFS"])
    thr0 = int(open(dbg / "render_pb_pages").read().split()[0], 0) - P.D_OFF
    a = parse_args(args)
    a["args"] = args
    if a["probe"] and a["vertices"] == 1500:
        text, buf, over, info = job_1500(world, a, thr0)
    else:
        text, buf, over, info = job_tri(world, a, thr0)
    (dbg / "buf09").write_bytes(struct.pack("<59I", *buf))
    armed = (dbg / "own_arm").exists() and (dbg / "own_arm").read_text().startswith("armed")
    if armed and mode == "job":
        import simring
        page, _ = simring.run_events(a3_events(world, a, thr0, info))
        n = int((dbg / "armed_jobs").read_text()) + 1 if (dbg / "armed_jobs").exists() else 1
        (dbg / "armed_jobs").write_text(str(n))
        if n in world.stall:
            (dbg / "stalled").write_text("1")
        (dbg / "own_res.json").write_text(json.dumps(page))
    if mode == "timeline":
        sys.stdout.write(text)
        return 0
    if over and a["probe"]:
        print("probe p1139-green: failed: scene overflowed the parameter buffer, context kept (No space left on device)")
        return 3
    if over:     # g-qf's kept form: --keep-overflow, rc 0, the overflow in the job and render lines
        print("job: failed: scene overflowed the parameter buffer, context kept (No space left on device)\n"
              "diff: 1000 of 16777216 pixels\ntri 4096x4096 #1: overflowed\ntri: 0 of 1 renders ok, 1 overflowed")
        return 0
    print("job: ok" if a["probe"] else "tri: 1 of 1 renders ok\ndiff: 0 of 16777216 pixels")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
