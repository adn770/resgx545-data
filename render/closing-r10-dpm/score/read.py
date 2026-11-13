#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""read.py: r9-ldpm's reader of one job's output (r8-ldpm's score/read.py, byte for byte but for
this docstring's first lines and the key gps_next, added for stage m6b: offline/OD2-FIX.md, OD-2
(a)). r8-ldpm's reader of one job's output: the tool's text with regtimeline's block after
it (`timeline: regs ...`, `tl T v v ...`). R7-dpm's run/r7read.py `reading`, unchanged in what it
reads (it is the reading E915 to E918 were scored with), less the control block (buf09: the kit
keeps no buf09, so R-5's class is not read here) and the own task's rungs. run/hooks.sh reads the
same keys in awk for the runner's premise; tests/test_read.py holds the two equal on every kept
R7-dpm job and on the mock's outputs.

  nparts      the partial renders (stretches of 0x0658 bit 0)
  knob        0x0624 at the first sample at or after the header's start whose 0x0724 low half is
              not 0 (the job's threshold P - 0x22: the knob proof)
  need        the highest 0x0724 low half of a job with no partial render (else None)
  steps, S    the first TA run's global page steps: 0x072c's high half going from g to g' between
              two samples gives every page k in (g, g'] the bracket (a, max(a, b - 1)) of the two
              samples' 0x0724 high halves; S_k = max(a, b - 1)
  gps_abort   0x072c's high half in the last sample before the first partial render
  gps_left    0x072c's high half in the last sample of the first partial render
  gps_next    0x072c's high half in the first sample after the first partial render (OD-2 (a):
              equal to gps_left at 94 of 98 kept r8-ldpm rows; at two band 6 cells every sample of
              the render still read the abort's 6 and the next one 2, the list trimmed between two
              samples; the other two are step cells, where a page is pending after the grow)
  gmax        the highest 0x072c high half of the job
  runpeaks    each TA run's highest 0x0724 high half (row 0 left out; f7_replay.kept)
  mono        the steps are pages 2, 3, ... with no gap and never going down
"""
from __future__ import annotations


def hx(s: str) -> int:
    return int(s, 16)


def lo(v):
    return v & 0xFFFF


def hi(v):
    return (v >> 16) & 0xFFFF


def parse(text: str):
    """(regs, rows, start) of the first timeline block; start None for a cut line."""
    regs, rows, start = None, [], 0
    for ln in text.splitlines():
        if ln.startswith("timeline: regs"):
            if regs is not None:
                break
            p = ln.split()
            i = p.index("samples")
            regs = [hx(x) for x in p[2:i]]
            if "start" in p:
                start = int(p[p.index("start") + 1])
            continue
        if regs is not None and ln.startswith("tl "):
            p = ln.split()
            if len(p) != 2 + len(regs):
                return regs, rows, None
            rows.append((int(p[1]), dict(zip(regs, (hx(x) for x in p[2:])))))
    return regs, rows, start


def stretches(rows):
    out, a = [], None
    for i, (_, v) in enumerate(rows):
        on = v.get(0x658, 0) & 1
        if on and a is None:
            a = i
        if not on and a is not None:
            out.append((a, i - 1))
            a = None
    if a is not None:
        out.append((a, len(rows) - 1))
    return out


def reading(text: str) -> dict:
    regs, rows, start = parse(text)
    if start is None:
        return dict(void="capture cut")
    if not regs or not rows or 0x658 not in regs or 0x724 not in regs or 0x72C not in regs:
        return dict(void="no timeline")
    st = stretches(rows)
    a = st[0][0] if st else len(rows)
    knob = next((v.get(0x624) for t, v in rows if t >= start and lo(v[0x724]) != 0), None)
    lows = [lo(v[0x724]) for _, v in rows if not v[0x658] & 1]
    r = dict(void=None, nparts=len(st), knob=knob,
             need=(max(lows) if lows else None) if not st else None)
    steps, S = {}, {}
    pg = pp = None
    for i in range(0, a):
        v = rows[i][1]
        g, p = hi(v[0x72C]), hi(v[0x724])
        if pg is not None and g > pg and pg >= 1:
            for k in range(pg + 1, g + 1):
                steps[k] = (pp, p)
                S[k] = max(pp, p - 1)
        pg, pp = g, p
    r["steps"], r["S"] = steps, S
    r["iv"] = {k: (a_, max(a_, b_ - 1)) for k, (a_, b_) in steps.items()}
    r["gps_abort"] = hi(rows[a - 1][1][0x72C]) if st and a > 0 else None
    r["gps_left"] = hi(rows[st[0][1]][1][0x72C]) if st else None
    r["gps_next"] = hi(rows[st[0][1] + 1][1][0x72C]) if st and st[0][1] + 1 < len(rows) else None
    r["gmax"] = max(hi(v[0x72C]) for _, v in rows)
    r["mono"] = bool(S) and all(S[k] <= S[k2] for k, k2 in zip(sorted(S), sorted(S)[1:])) \
        and sorted(S) == list(range(2, 2 + len(S)))
    bounds = [(1, st[0][0] if st else len(rows))] + [
        (st[k][1] + 1, st[k + 1][0] if k + 1 < len(st) else len(rows)) for k in range(len(st))]
    r["runpeaks"] = [max(hi(rows[i][1][0x724]) for i in range(a_, e_)) for a_, e_ in bounds if e_ > a_]
    return r


def words(r: dict) -> dict:
    """The `k=v` reading of the runner's hooks (run/hooks.sh), from a reading."""
    if r.get("void"):
        return {}
    f = lambda v: "-" if v is None else f"0x{v:x}"  # noqa: E731
    out = {"nparts": str(r["nparts"]), "knob": f(r["knob"]), "need": f(r["need"]),
           "gps_abort": f(r["gps_abort"]), "gps_left": f(r["gps_left"]),
           "gps_next": f(r["gps_next"]), "gmax": f(r["gmax"]),
           "mono": str(int(r["mono"])), "runpeaks": ",".join(f"0x{x:x}" for x in r["runpeaks"]) or "-"}
    for k, v in sorted(r["S"].items()):
        out[f"s{k}"] = f"0x{v:x}"
    return {k: v for k, v in out.items() if v != "-"}
