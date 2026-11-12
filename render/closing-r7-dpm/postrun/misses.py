#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""misses.py: post hoc reads of R7-dpm's frozen misses (written at the fold, 2026-11-12, after the run and
its scores were read; no re-scoring). Run from the session directory: python3 postrun/misses.py > postrun/misses.out

1. s-b b-s17-0x9 (H-REPLAY64's one FAILED row): the timeline rows around the first TA run.
2. s-m: the cells where H-SPAN or the step model FAILED, with the job's own steps.
3. s-v: the head pair offsets of the two calibration dumps.
4. s-k: every job's rungs of oomring2 (pa1 flags, sa8 bits 7 to 9, the high and low halves of 0x0724 and
   0x072c) and the host's samples of the first partial render, to show what the task read at the abort and
   at the decision entry against what H-PASS took them to be.
Standard library plus the session's own run/r7read.py (the frozen reader)."""
import gzip
import json
import pathlib
import struct
import sys

sys.dont_write_bytecode = True
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KP / "run"))
import r7read as R  # noqa: E402

A1, B1 = KP / "out/a1", KP / "out/b1"


def text(p):
    return gzip.open(p, "rt", errors="replace").read()


def s17():
    print("== 1. s-b b-s17-0x9: the first rows of the timeline (0x0624, 0x0658 bit 0, hi 0x0724, hi 0x072c)")
    t = text(A1 / "s-b/b-s17-0x9.txt.gz")
    regs, rows, _ = R.parse(t)
    for i, (ts, v) in enumerate(rows[:6]):
        print(f"  row {i} t {ts} ns: 0x0624 0x{v[0x624]:x} pr {v[0x658] & 1} pages 0x{R.hi(v[0x724]):x} global {R.hi(v[0x72c])}")
    st = R.stretches(rows)
    print(f"  partial-render stretches {st}; rows before the first: {st[0][0]} (row 0 is left out of a run's peak)")
    r = R.reading(t)
    print(f"  runpeaks as read {[hex(x) for x in r['runpeaks']]}; nparts {r['nparts']}")
    for name in ("b-s17-0x2", "b-s17-0xe", "b-s17-0x15"):
        regs, rows, _ = R.parse(text(A1 / f"s-b/{name}.txt.gz"))
        st = R.stretches(rows)
        print(f"  {name}: rows before the first partial render {st[0][0] if st else len(rows)}")


def s_m():
    print("== 2. s-m: the FAILED cells, read")
    for name in ("m-c33-0x3cf", "m-c25-0x2b1"):
        r = R.reading(text(A1 / f"s-m/{name}.txt.gz"))
        print(f"  {name}: thr0 {r['thr0']:#x} gps_left {r['gps_left']} nparts {r['nparts']} grow {r['grow']} "
              f"steps {dict((k, hex(v)) for k, v in sorted(r['S'].items()))}")
    for name in ("m-cal-c23", "m-cal-c33", "m-cal-c25"):
        r = R.reading(text(A1 / f"s-m/{name}.txt.gz"))
        print(f"  {name}: bracket of each step {dict((k, (hex(a), hex(b))) for k, (a, b) in sorted(r['iv'].items()))}")


def s_v():
    print("== 3. s-v: PB page 1 head pair offsets of the two calibration dumps (R6-dpm's postrun/ungated.py reading)")
    for n in ("v-cal-c4", "v-cal-c8"):
        p = gzip.open(A1 / "s-v" / f"{n}.p1139-green.param.bin.gz").read()
        w = struct.unpack_from("<1024I", p, 0)
        pos = [i for i in range(1023) if (w[i], w[i + 1]) == (w[0], w[1])]
        r = R.reading(text(A1 / f"s-v/{n}.txt.gz"))
        print(f"  {n}: offsets {pos}, periods {[b - a for a, b in zip(pos, pos[1:])]}; "
              f"steps {[hex(v) for _, v in sorted(r['S'].items())]}")


def s_k():
    print("== 4. s-k: oomring2's rungs (slot, pa1, sa8 & 0x380, 0x0724 hi:lo, 0x072c hi:lo); host samples")
    rows_tsv = [ln.split("\t") for ln in (B1 / "s-k/cases.tsv").read_text().splitlines()[1:]]
    for row in rows_tsv:
        name = row[0]
        page = json.loads(text(B1 / f"s-k/{name}.page.json.gz"))["page"]
        t = text(B1 / f"s-k/{name}.txt.gz")
        ring = R.decode_ring(page)
        o = R.ring_reading(page, t)
        rd = R.reading(t)
        print(f"-- {name}: thr0 {rd['thr0']:#x} nparts {rd['nparts']} gps_abort {rd['gps_abort']} gps_left {rd['gps_left']} "
              f"passes {ring['passes']} lost {ring['lost']}")
        for j, g in enumerate(ring["rungs"]):
            tag = "OOM" if g["pa1"] & R.OOM else ("EOR" if g["pa1"] & R.EOR else "")
            print(f"   rung {j:2} slot {g['slot']:2} pa1 0x{g['pa1']:08x} {tag:3} sa8&0x380 0x{g['sa8'] & 0x380:03x} "
                  f"0x0724 {R.hi(g['x724']):#x}:{R.lo(g['x724']):#x} 0x072c {R.hi(g['x72c'])}:{R.lo(g['x72c'])}")
        print(f"   reader: {R.ring_line(o)} abort_pages {o.get('abort_pages')} dec_pages {o.get('dec_pages')}")
        regs, rows, _ = R.parse(t)
        st = R.stretches(rows)
        for k, (a, b) in enumerate(st):
            pre = rows[a - 1][1] if a > 0 else None
            post = rows[b + 1][1] if b + 1 < len(rows) else None
            def f(v):
                return "-" if v is None else f"{R.hi(v[0x724]):#x}/{R.hi(v[0x72c])}"
            print(f"   host partial render {k + 1}: before {f(pre)} first-in {f(rows[a][1])} last-in {f(rows[b][1])} "
                  f"after {f(post)} (pages/global)")


if __name__ == "__main__":
    s17()
    s_m()
    s_v()
    s_k()
