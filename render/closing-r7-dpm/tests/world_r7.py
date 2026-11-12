#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""world_r7.py: synthetic worlds of R7-dpm for the runner mock (R6-dpm's world_r6.py with round 7's rules).  A world answers a job BY ITS
ARGV (the command the runner actually ran: target size, scene, vertices, --vtx-coords, move, dump) and the knob the runner wrote
(render_pb_pages in the fake debugfs), never by its case name, and with no wall-clock dependence (the sample times it prints are its
own numbers, not the clock's; nothing waits for a process to start).

    world_r7.py job ARGS...        (the fake tool) print the tool's lines; write buf09 (and with --dump-render the dumps; with the own
                                   task armed the results page through sgx-sim running bins/oomring2.blob) to the fake debugfs
    world_r7.py timeline ARGS...   (the fake regtimeline) print the regtimeline block of the same job
Environment: SGXFIVE_DEBUGFS (the fake debugfs directory), FAKE_WORLD (the spec, comma separated key=value):
  span=a|b          the first partial render leaves 2 pages below A_k (H-SPAN, default) or below B_k (E874's rival)
  order=walk64|row  the walk order of one-triangle scenes (E875's replay; default walk64 = H-REPLAY64) and of their dumps
  shift=G:N         the steps of target G (c33, c32, c23, c25, c11, c2048) moved by N pages (a calibration off the model: s-m re-picks)
  skip2=1           the 2048x2048 scene shows no step 2 (a calibration whose steps are not monotone)
  kskew=N           the job's 0x0624 reads thr0 + N (the knob proof fails)
  flip=PATTERN,flipP=0xP   a probe job whose args contain PATTERN at P reads the other class (a control off)
  left=0xP:N        the job at P leaves N global pages (a ctlleft control off)
  cnt=0xP:N         the one-triangle job at P has N partial renders (a ctlcnt control off)
  peaks=0xP         the one-triangle job at P reads its last run's peak one page higher (a ctlpeaks control off)
  nogrow0628=1      no sample of 0x0628 (every key needing it reads `-`: a control WITHOUT A READING)
  noleft=0xP        the job at P takes its first partial render with no sample inside it (gps_left reads `-`: NO READING)
  uoff=SCENE:N      N more pages in that scene's need (its calibration is void)
  vvoid=1           the --vtx-coords scenes never reach a second global page
  isub=fwd|rev      the creep cell's decision bits: R-5's operand order (fwd: 0) or the other (rev: 0x180)
  ringoff=1         oomring2's rungs read page counts of 0 (s-k's premise fails)
  pass=host|off     the abort rung's page count is the host's (default) or 5 pages below it, inside the samples (H-PASS fails, the premise holds)
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
import r7plan as P  # noqa: E402

RT_REGS = [0x012C, 0x0624, 0x0628, 0x0658, 0x0660, 0x0700, 0x070C, 0x0710, 0x0720, 0x0724, 0x0728, 0x072C, 0x0730, 0x0734, 0x0748, 0x0A74]
GROUP = {wh: g for g, wh in P.TARGETS.items() if g not in ("c2048f",)}


def parse_args(args: str):
    g = lambda k, d=None: (re.search(rf"--{k} (\d+)", args) or [None, d])[1]
    mv = re.search(r"--move 1:(-?\d+),(-?\d+)", args)
    return dict(w=int(g("width", 64)), h=int(g("height", 64)), vertices=int(g("vertices", 0) or 0), probe=args.startswith("probe"),
                coords=int(g("vtx-coords", 0) or 0), move=(int(mv.group(1)), int(mv.group(2))) if mv else (0, 0),
                dump=(re.search(r'--dump-render "?([^" ]+)', args) or [None, None])[1])


class World:
    def __init__(self, spec=""):
        kv = dict(p.split("=", 1) for p in spec.split(",") if p)
        self.span = kv.get("span", "a")
        self.order = kv.get("order", "walk64")
        self.shift = {}
        if "shift" in kv:
            g, n = kv["shift"].split(":")
            self.shift[g] = int(n)
        self.skip2 = kv.get("skip2") == "1"
        self.kskew = int(kv.get("kskew", "0"))
        self.flip, self.flipP = kv.get("flip"), (int(kv["flipP"], 0) if "flipP" in kv else None)
        self.left = tuple(int(x, 0) for x in kv["left"].split(":")) if "left" in kv else None
        self.cnt = tuple(int(x, 0) for x in kv["cnt"].split(":")) if "cnt" in kv else None
        self.peaks = int(kv["peaks"], 0) if "peaks" in kv else None
        self.noleft = int(kv["noleft"], 0) if "noleft" in kv else None
        self.uoff = {}
        if "uoff" in kv:
            sc, n = kv["uoff"].split(":")
            self.uoff[sc] = int(n)
        self.vvoid = kv.get("vvoid") == "1"
        self.isub = kv.get("isub", "fwd")
        self.ringoff = kv.get("ringoff") == "1"
        self.pass_ = kv.get("pass", "host")
        self.stall = [int(x) for x in kv.get("stall", "0").split("+")]

    def scene(self, a):
        """(S, E, U) of a 1500-vertex job: the frozen model, E = A (H-SPAN) or B (the rival) as the world says, shifted as it says."""
        wh = (a["w"], a["h"])
        if a["coords"]:
            S, U = P.VCAL[a["coords"]]
            return dict(S), {}, U
        S, A, B, U = P.MODEL[wh]
        E = A if self.span == "a" else B
        if wh == (2048, 4096):
            S = {**S, **P.KEPT_2X4}          # the hardware's S3 at 2048x4096 (the kept calibrations)
        n = self.shift.get(GROUP.get(wh), 0)
        S = {k: v + n for k, v in S.items()}
        E = {k: v + n for k, v in E.items()}
        if self.skip2 and wh == (2048, 2048):
            S = dict(S)
            S[2] = 0
        return S, E, U


def row(vals):
    return [vals.get(r, 0) for r in RT_REGS]


def timeline(rows, rc=3):
    t = ["timeline: regs " + " ".join(f"0x{r:04x}" for r in RT_REGS) + f" samples {len(rows)} seconds 0 start 100 end {100 + 10 * len(rows)} rc {rc}"]
    t += [f"tl {tt} " + " ".join(f"{v:08x}" for v in r) for tt, r in rows]
    return "\n".join(t) + "\n"


def span_pred(thr0, S, E):
    ks = [k for k in sorted(S) if S[k] <= thr0]
    if not ks:
        return 1
    k = ks[-1]
    if thr0 == S[k]:
        return None
    if k not in E:
        return 1
    return 2 if thr0 < E[k] else 1


def job_1500(world: World, a, thr0):
    """The first run takes pages 1..min(thr0, U) one sample a page; the global count steps at S_k; then the partial render(s): the
    second run at thr0 (+ 0x20 when it raises), a second partial render if the rest does not fit."""
    S, E, U = world.scene(a)
    args = a["args"]
    on = thr0 in S.values()
    gv = (lambda p: 1) if (a["coords"] and world.vvoid) else (lambda p: 1 + sum(1 for v in S.values() if 0 < v < p))
    left = span_pred(thr0, S, E) if S else 1
    if left is None:                                  # a step cell: 1 in the render (the pending page, H-PENDREQ)
        left = 1
    if world.left and world.left[0] == thr0 + P.D_OFF:
        left = world.left[1]
    if S and 3 in S and 3 in E:
        raised = (thr0 < S[3] or left == 2) if not on else (next(k for k, v in S.items() if v == thr0) <= 3)
    else:
        raised = False
    if world.flip and world.flip in args and world.flipP is not None and thr0 + P.D_OFF == world.flipP:
        raised = not raised
    no628 = os.environ.get("FAKE_NO0628") == "1"
    tt, rows = 100, [(100, row({0x0624: 0x400, 0x0628: 0 if no628 else 0x100F0}))]
    first = min(thr0, U)
    for p in range(1, first + 1):
        tt += 1000
        g = gv(p)
        v628 = 0x10003 if (on and p >= first - 1) else (0x10000 | thr0)
        rows.append((tt, row({0x0624: thr0 + world.kskew, 0x0628: v628, 0x0720: 1 if thr0 < U else 0, 0x0724: (p << 16) | p,
                              0x072C: (g << 16) | g})))
    nparts = 0
    if thr0 < U:
        nparts = 1
        ins = 0 if world.noleft == thr0 + P.D_OFF else 2
        for _ in range(ins):
            tt += 1000
            rows.append((tt, row({0x0624: thr0, 0x0628: 0x10000 | thr0, 0x0658: 1, 0x0720: 1, 0x0724: (first << 16) | first, 0x072C: (left << 16) | left})))
        t2 = thr0 + 0x20 if raised else thr0
        rest = U - thr0 + 0x50
        if (a["w"], a["h"]) == (2048, 4096):
            rest = t2 + 1                              # the creep cell takes a second partial render (F9, R6-dpm's kept k-creep: 2)
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
    rows.append((tt, row({0x0624: thr0, 0x0628: 0x10000 | thr0})))
    if no628:
        rows = [(t_, [0 if r == 0x0628 else v for r, v in zip(RT_REGS, vals)]) for t_, vals in rows]
    buf = [0] * 59
    buf[38] = 0x20 if (raised and nparts >= 2) else 0
    buf[36] = max(gv(first) - 2, 0)
    info = dict(grow=on, raised=raised and nparts >= 2, nparts=nparts, creep=(a["w"], a["h"]) == (2048, 4096),
                abort=(first, gv(first)), left=left, after=(1, 1))
    return timeline(rows), buf, thr0 < U, info


def scene_U(a):
    dx, dy = a["move"]
    wh = (a["w"], a["h"])
    if wh == (4096, 4096) and (dx, dy) == (0, 0):
        return 287, None
    sc = next((s for s in P.B_SCENES if (s[1], s[2]) == wh and (s[3], s[4]) == (dx, dy)), None)
    return (sc[5] if sc else P.M().scene_u(*wh, dx, dy)), (sc[0] if sc else None)


def job_tri(world: World, a, thr0):
    dx, dy = a["move"]
    U, sc = scene_U(a)
    U += world.uoff.get(sc, 0)
    tt, rows = 100, [(100, row({0x0624: 0x400}))]
    if thr0 < U:
        n, peaks = P.M().replay(a["w"], a["h"], dx, dy, thr0, world.order)
        peaks = list(peaks)
        if world.cnt and world.cnt[0] == thr0 + P.D_OFF:
            n = world.cnt[1]
            peaks = (peaks + [5] * n)[:n + 1]
        if world.peaks == thr0 + P.D_OFF:
            peaks[-1] += 1
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
            rows.append((tt, row({0x0624: thr0, 0x0628: 0x10000 | thr0, 0x0724: (p << 16) | p, 0x072C: 0x10001})))
    tt += 1000
    rows.append((tt, row({0x0624: thr0})))
    return timeline(rows), [0] * 59, thr0 < U, dict(nparts=n, U=U)


def a3_events(world: World, a, thr0, info):
    """The event passes of an armed job, shaped as R6-dpm's kept r-k rings (abort pa1 0x3200000, the grow's 0x3100000 after it, 0x3000400,
    the end of render 0x3000010, 0x3400000, the decision entry 0x3200000), with the page counts the task reads: the host's at the abort
    (the last sample before the partial render) and the pages left at the decision entry (H-PASS).  sa8 at the decision by R-5 (0x180
    when the job raises); the creep cell by the world's operand order."""
    raised = info.get("raised", False)
    dec = 0x180 if raised else 0
    if info.get("creep") and world.isub == "rev":
        dec = 0x180
    pages, gp = info.get("abort", (1, 1))
    if world.pass_ == "off":
        pages -= 5                                    # inside the host samples (the premise holds), off the abort bracket
    x724, x72c = (pages << 16) | pages, (gp << 16) | gp
    lf = info.get("left", 1)
    xl = (lf << 16) | lf
    if world.ringoff:
        x724 = x72c = xl = 0
    ev = [(2, 3, 0x03200000, 0, 0x1, 1000, x724, x72c)]
    if info.get("grow"):
        ev.append((2, 3, 0x03100000, 0, 0x1, 1100, x724, x72c))
    ev += [(2, 4, 0x03000400, 0, 0x1, 1300, x724, x72c), (3, 5, 0x03000010, 0, 0, 1400, 0x10001, xl),
           (3, 5, 0x03400000, 0, 0, 1450, 0x10001, xl)]
    if info.get("nparts", 0) >= 2:
        ev.append((2, 3, 0x03200000, dec, 0x1, 1500, (8 << 16) | 8, xl))
        if raised:
            ev.append((2, 3, 0x03200000, 0x380, 0x1, 1600, (9 << 16) | 9, xl))
    ev += [(1, 6, 0x03000200, 0, 0, 1700, 0, 0), (3, 5, 0x03000010, 0, 0, 1800, 0, 0)]
    return ev


def write_dump(world: World, a, d: pathlib.Path):
    """--dump-render: a probe job's p1139-green.param/tadata stand-ins, or a tri job's tri.param.bin and tri.tadata.bin with one region
    header a region of the scene (dpm_words.tadata_layout), its stream block's address placed by the world's walk order."""
    if not d.is_dir():
        return                                         # the fake tool refused the job before (a missing directory)
    if a["probe"]:
        (d / "p1139-green.param.bin").write_bytes(b"\x01" * 8192)
        (d / "p1139-green.tadata.bin").write_bytes(b"tadata" * 100)
        return
    M = P.M()
    w, h = a["w"], a["h"]
    regs = M.walk(w, h, a["move"][0], a["move"][1], world.order)
    lay = M.O.D.tadata_layout(w, h)
    buf = bytearray(lay["size"])
    cur, npg = {}, 0
    for i, (c, r, m) in enumerate(regs):
        if m not in cur or cur[m][1] == 32:
            cur[m] = [npg, 0]
            npg += 1
        pg, slot = cur[m]
        cur[m][1] += 1
        # the header's coordinates are in G1's units (its walk64 key (r // 8, c // 4) is 64 pixels: 16-pixel columns, 8-pixel rows)
        struct.pack_into("<3I", buf, lay["rgn"] + 12 * i, ((2 * c) << 16) | (m << 12) | (2 * r), 0x100000 + pg * 0x1000 + slot * 128, 0)
    (d / "tri.tadata.bin").write_bytes(bytes(buf))
    (d / "tri.param.bin").write_bytes(b"\x02" * 4096)


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
    if a["dump"] and os.environ.get("FAKE_DUMPFAIL_ALL") != "1":
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
              f"diff: 1000 of {a['w'] * a['h']} pixels\ntri {a['w']}x{a['h']} #1: overflowed\ntri: 0 of 1 renders ok, 1 overflowed")
        return 0
    print("job: ok" if a["probe"] else f"tri: 1 of 1 renders ok\ndiff: 0 of {a['w'] * a['h']} pixels")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
