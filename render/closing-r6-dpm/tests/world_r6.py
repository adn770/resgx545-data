#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""world_r6.py: synthetic worlds of R6-dpm for the runner mock.  A world answers a job BY ITS ARGV (the command the runner actually
ran: target size, scene, vertices, --vtx-coords, move) and the knob the runner wrote (render_pb_pages in the fake debugfs), never by
its case name (round 4's slip o2), and with no wall-clock dependence (the sample times it prints are its own numbers, not the clock's).

    world_r6.py job ARGS...        (the fake tool) print the tool's lines; write buf09 (and with --dump-render the param and tadata
                                   dumps; with the own task armed the results page through sgx-sim) to the fake debugfs / dump dir
    world_r6.py timeline ARGS...   (the fake regtimeline) print the regtimeline block of the same job
Environment: SGXFIVE_DEBUGFS (the fake debugfs directory), FAKE_WORLD (the spec, comma separated key=value):
  vmode=cap|page    the --vtx-coords scenes follow H-BURST-CAP (default) or H-BURST-PAGE (the frozen VMODEL at L0)
  vL=N              the object size the --vtx-coords dumps show (default L0 = 67 + 15 N)
  order=row|col     the walk order of one-triangle scenes (F7's replay; default row)
  shift=G:N         the steps of target G (c2x1, c1x2, c15, c2048) moved by N pages (a calibration off the model: r-n re-picks)
  skip2=1           the 2048x2048 scene shows no step 2 (a calibration whose steps are not monotone)
  kskew=N           the job's 0x0624 reads thr0 + N (the knob proof fails)
  flip=PATTERN,flipP=0xP   a probe job whose args contain PATTERN at P reads the other class (a control off)
  left=0xP:N        the job at P leaves N global pages (a ctlleft control off)
  cnt=0xP:N         the default-triangle job at P has N partial renders (a ctlcnt control off)
  uoff=SCENE:N      N more pages in that scene's need (its calibration is void)
  vvoid=1           the --vtx-coords scenes never reach a second global page (r-v's premise fails)
  isub=fwd|rev      the creep cell's decision bits: R-5's operand order (fwd: 0) or the other (rev: 0x180)
  stall=N[+M]       the Nth (and Mth) armed job leaves the EDM stalled
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import struct
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
KP = HERE.parent
sys.path[:0] = [str(KP / "gen"), str(KP / "run"), str(HERE)]
import r6plan as P  # noqa: E402

RT_REGS = [0x012C, 0x0624, 0x0628, 0x0658, 0x0660, 0x0700, 0x070C, 0x0710, 0x0720, 0x0724, 0x0728, 0x072C, 0x0730, 0x0734, 0x0748, 0x0A74]
GROUP = {(2048, 2048): "c2048", (2048, 1024): "c2x1", (1024, 2048): "c1x2", (1536, 1536): "c15", (2048, 4096): "c2x4"}


def parse_args(args: str):
    g = lambda k, d=None: (re.search(rf"--{k} (\d+)", args) or [None, d])[1]
    mv = re.search(r"--move 1:(-?\d+),(-?\d+)", args)
    return dict(w=int(g("width", 64)), h=int(g("height", 64)), vertices=int(g("vertices", 0) or 0), probe=args.startswith("probe"),
                coords=int(g("vtx-coords", 0) or 0), move=(int(mv.group(1)), int(mv.group(2))) if mv else (0, 0),
                dump=(re.search(r'--dump-render "?([^" ]+)', args) or [None, None])[1])


class World:
    def __init__(self, spec=""):
        kv = dict(p.split("=", 1) for p in spec.split(",") if p)
        self.vmode = kv.get("vmode", "cap")
        self.vL = int(kv["vL"]) if "vL" in kv else None
        self.order = kv.get("order", "row")
        self.shift = {}
        if "shift" in kv:
            g, n = kv["shift"].split(":")
            self.shift[g] = int(n)
        self.skip2 = kv.get("skip2") == "1"
        self.kskew = int(kv.get("kskew", "0"))
        self.flip, self.flipP = kv.get("flip"), (int(kv["flipP"], 0) if "flipP" in kv else None)
        self.left = tuple(int(x, 0) for x in kv["left"].split(":")) if "left" in kv else None
        self.cnt = tuple(int(x, 0) for x in kv["cnt"].split(":")) if "cnt" in kv else None
        self.uoff = {}
        if "uoff" in kv:
            sc, n = kv["uoff"].split(":")
            self.uoff[sc] = int(n)
        self.vvoid = kv.get("vvoid") == "1"
        self.isub = kv.get("isub", "fwd")
        self.stall = [int(x) for x in kv.get("stall", "0").split("+")]

    def scene(self, a):
        """(S, B, U) of a 1500-vertex job: the frozen model (MODEL, VMODEL), shifted as the world says."""
        wh = (a["w"], a["h"])
        if a["coords"]:
            S, B, U, _ = P.VMODEL[(a["coords"], self.vmode)]
            S, B = dict(S), {k: v for k, v in B.items() if v is not None}
        else:
            S, B, U = P.MODEL[wh]
            S, B = dict(S), dict(B)
            n = self.shift.get(GROUP.get(wh), 0)
            S = {k: v + n for k, v in S.items()}
            B = {k: v + n for k, v in B.items()}
            if self.skip2 and wh == (2048, 2048):
                S[2] = 0                              # the run starts on 2 global pages: no step 2 is seen (not monotone)
        return S, B, U


def row(vals):
    return [vals.get(r, 0) for r in RT_REGS]


def timeline(rows, rc=3):
    t = ["timeline: regs " + " ".join(f"0x{r:04x}" for r in RT_REGS) + f" samples {len(rows)} seconds 0 start 100 end {100 + 10 * len(rows)} rc {rc}"]
    t += [f"tl {tt} " + " ".join(f"{v:08x}" for v in r) for tt, r in rows]
    return "\n".join(t) + "\n"


def job_1500(world: World, a, thr0):
    """The first run takes pages 1..min(thr0, U) one sample a page, 1 us apart but for a 200 us wait after each burst end B_k (so the
    frozen timeline rule reads E_k = B_k); the global count steps at S_k; then the partial render(s)."""
    S, B, U = world.scene(a)
    args = a["args"]
    on = thr0 in S.values()
    gv = (lambda p: 1) if (a["coords"] and world.vvoid) else (lambda p: 1 + sum(1 for v in S.values() if v < p))
    left = P.M.F4.predict(thr0, S, B) if S else 1
    if left is None:                                  # a step cell: 1 in the render (the pending page, H-PENDREQ)
        left = 1
    if world.left and world.left[0] == thr0 + P.D_OFF:
        left = world.left[1]
    if S and 3 in S and 3 in B:
        raised = (thr0 < S[3] or thr0 < B[3]) if not on else (next(k for k, v in S.items() if v == thr0) <= 3)
    else:
        raised = False
    if world.flip and world.flip in args and world.flipP is not None and thr0 + P.D_OFF == world.flipP:
        raised = not raised
    tt, rows = 100, [(100, row({0x0624: 0x400, 0x0628: 0x100F0}))]
    first = min(thr0, U)
    ends = set(B.values())
    for p in range(1, first + 1):
        tt += 200000 if (p - 1) in ends else 1000
        g = gv(p)
        v628 = 0x10003 if (on and p >= first - 1) else (0x10000 | thr0)
        rows.append((tt, row({0x0624: thr0 + world.kskew, 0x0628: v628, 0x0720: 1, 0x0724: (p << 16) | p, 0x072C: (g << 16) | g})))
    nparts = 0
    if thr0 < U:
        nparts = 1
        for _ in range(2):
            tt += 1000
            rows.append((tt, row({0x0624: thr0, 0x0628: 0x10000 | thr0, 0x0658: 1, 0x0720: 1, 0x0724: (first << 16) | first, 0x072C: (left << 16) | left})))
        t2 = thr0 + 0x20 if raised else thr0
        rest = U - thr0 + 0x50
        run2 = min(t2, rest)
        for p in range(1, run2 + 1):
            tt += 1000
            rows.append((tt, row({0x0624: t2, 0x0628: 0x10000 | t2, 0x0720: 1, 0x0724: (p << 16) | p, 0x072C: (2 << 16) | 2})))
        if rest > t2:
            nparts = 2
            for _ in range(2):
                tt += 1000
                rows.append((tt, row({0x0624: t2, 0x0658: 1, 0x0720: 1, 0x0724: (run2 << 16) | run2, 0x072C: 0x10001})))
            for p in range(1, 9):
                tt += 1000
                rows.append((tt, row({0x0624: t2, 0x0720: 1, 0x0724: (p << 16) | p, 0x072C: 0x10001})))
    tt += 1000
    rows.append((tt, row({0x0624: thr0, 0x0628: 0x10000 | thr0})))      # after the job: no grow reading (0x0628 holds the threshold)
    buf = [0] * 59
    buf[38] = 0x20 if (raised and nparts >= 2) else 0
    buf[36] = max(gv(first) - 2, 0)
    return timeline(rows), buf, thr0 < U, dict(grow=on, raised=raised and nparts >= 2, nparts=nparts, creep=(a["w"], a["h"]) == (2048, 4096))


def job_tri(world: World, a, thr0):
    dx, dy = a["move"]
    _, U = P.M.scene(dx, dy)
    sc = next((k for k, mv in P.B_NAME.items() if mv == (dx, dy)), None)
    U += world.uoff.get(sc, 0)
    tt, rows = 100, [(100, row({0x0624: 0x400}))]
    if thr0 < U:
        rp = P.M.h_replay(dx, dy, thr0, world.order)
        n, peaks = rp
        if world.cnt and world.cnt[0] == thr0 + P.D_OFF:
            n = world.cnt[1]
            peaks = (peaks + [5] * n)[:n + 1]
        t = thr0
        for i, pk in enumerate(peaks):
            for p in range(1, pk + 1):
                tt += 1000
                rows.append((tt, row({0x0624: t, 0x0628: 0x10000 | t, 0x0720: 1, 0x0724: (p << 16) | p, 0x072C: 0x10001})))
            if i < n:
                tt += 1000
                rows.append((tt, row({0x0624: t, 0x0658: 1, 0x0720: 1, 0x0724: (pk << 16) | pk, 0x072C: 0x10001})))
                t = thr0 + 0x20
    else:
        n = 0
        for p in range(1, U + 1):
            tt += 1000
            rows.append((tt, row({0x0624: thr0, 0x0628: 0x10000 | thr0, 0x0720: 1, 0x0724: (p << 16) | p, 0x072C: 0x10001})))
    tt += 1000
    rows.append((tt, row({0x0624: thr0})))
    return timeline(rows), [0] * 59, thr0 < U, dict(nparts=n, U=U)


def a3_events(world: World, a, thr0, info):
    """The event passes of an armed job (R5-dpm's world): the decision entry's sa8 bits by R-5 (0x180 when the job raises), the
    creep cell by the world's operand order."""
    raised = info.get("raised", False)
    dec = 0x180 if raised else 0
    if info.get("creep") and world.isub == "rev":
        dec = 0x180
    ev = [(1, 0, 0x02000100, 0, 0, 1000)]
    if info.get("grow"):
        ev.append((2, 3, 0x00200000, 0x0, 0x1, 1100))
    ev += [(2, 3, 0x00100000, 0x80000, 0x1, 1200), (2, 4, 0x00000400, 0x20, 0x1, 1300), (3, 5, 0x00000010, 0x0, 0, 1400),
           (2, 3, 0x00100000, 0x80000 | dec, 0x1, 1500)]
    if raised:
        ev.append((2, 3, 0x00100000, 0x80000 | 0x380, 0x1, 1600))
    ev += [(2, 6, 0x00000200, 0x0, 0x0, 1700), (3, 5, 0x00000010, 0x0, 0x0, 1800), (0, 2, 0x02000000, 0, 0, 1900)]
    return ev


def write_dump(world: World, a, d: pathlib.Path):
    """A param dump whose PB page 1 holds object blocks of L dwords (the head pair recurs every L), and a tadata stand-in."""
    L = world.vL or (P.VTX.get(a["coords"]) if a["coords"] else 67)
    w = [0] * 2048
    for i in range(0, 1024 - 1, L):
        w[i], w[i + 1] = 0x04000004, 0x00030004 if a["coords"] else 0x00030001
    for i in range(1024):
        if w[i] == 0:
            w[i] = 0x1000 + i
    d.mkdir(parents=True, exist_ok=True)
    (d / "p1139-green.param.bin").write_bytes(struct.pack("<2048I", *w))
    (d / "p1139-green.tadata.bin").write_bytes(b"tadata" * 100)


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
    if mode == "timeline":
        sys.stdout.write(text)
        return 0
    (dbg / "buf09").write_bytes(struct.pack("<59I", *buf))
    if a["dump"]:
        write_dump(world, a, pathlib.Path(a["dump"]))
    armed = (dbg / "own_arm").exists() and (dbg / "own_arm").read_text().startswith("armed")
    if armed:
        import simring
        page, _ = simring.run_events(a3_events(world, a, thr0, info))
        n = int((dbg / "armed_jobs").read_text()) + 1 if (dbg / "armed_jobs").exists() else 1
        (dbg / "armed_jobs").write_text(str(n))
        if n in world.stall:
            (dbg / "stalled").write_text("1")
        (dbg / "own_res.json").write_text(json.dumps(page))
    if over and a["probe"]:
        print("probe p1139-green: failed: scene overflowed the parameter buffer, context kept (No space left on device)")
        return 3
    if over:
        print("job: failed: scene overflowed the parameter buffer, context kept (No space left on device)\n"
              "diff: 1000 of 16777216 pixels\ntri 4096x4096 #1: overflowed\ntri: 0 of 1 renders ok, 1 overflowed")
        return 0
    print("job: ok" if a["probe"] else "tri: 1 of 1 renders ok\ndiff: 0 of 16777216 pixels")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
