#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""r6read.py: the ONE reader of R6-dpm (R5-dpm's run/r5read.py with round 6's additions).  The laptop runner (run/run_stage.sh,
python3 stdlib, no root) and the Mac scorer (score/score_r6.py) both import it, so the picks the runner makes and the readings the scorer makes are the same code (round 4's
slip t, a scorer looking for another file name than the runner wrote, cannot happen: `kept_name` below is the only place a kept
file name is made).

A job's reading, from the tool output with the regtimeline block (`timeline: regs ...`, `tl T v v ...`) and the control block
(buf09, 59 dwords) the runner keeps:
  nparts, thr0, peaks, reach, valid, knob, need   R1's rules, unchanged (score/dpm3.py and run/dpm_read.awk of R3-geo; the twin
                                                  test tests/test_read.py compares them on every kept job)
  raised        dword 38 of the control block is 0x20 (R3-geo's class rule); `raise_tl` adds the plan's second clause: 0x0624
                above thr0 in a sample after the first partial render
  cls           R raise, N none, V void (valid is R1's: the second run reaches thr0 and there are 2 or more partial renders)
  iv            round 6 (H-IV, E873): {k: (a, max(a, b - 1))}, the bracket a sampled step allows; a jump of the global count by
                more than one between two samples gives every page it passes the same bracket (CAP's close steps at --vtx-coords)
  ends          round 6: {k: E_k}, F4's frozen timeline burst-end rule (f4_phase.ends, X = 75 us, E874): in the first TA run the
                smallest T >= S_k + 2 (below S_k+1 and S_k + 0x200) whose wait from the first sample with T pages to the first
                with T + 1 is above 75 us
  runpeaks      round 6: each TA run's peak of the 0x0724 high half, F7's reading (f7_replay.kept, E875)
  steps         {k: (a, b)}: in the first TA run (the samples before the first partial render, all samples if there is none),
                the high half of 0x072c (global pages) steps to k >= 2 between a sample whose 0x0724 high half (pages) is a and the
                next, whose is b.  S[k] = max(a, b - 1): "the page count read just before global page k appears" (plan section
                1); max(a, b - 1) gives the count before the step when the sample after it read one page more (the usual
                case), and a when the step is seen with the count unchanged (f-1350-0x36e: (0x125, 0x125]).  amb[k]: b - a > 1
  grow          the low half of 0x0628 below 0x10 in a sample from the first one where 0x0720 is non-zero to the first one
                with 0x0658 bit 0 set (plan section 2); None (no reading) when the job's threshold is itself below 0x10
                (0x0628's low half holds the threshold: g-qf's low cells read below 0x10 with no grow)
  gps_abort     0x072c high half in the last sample before the first partial render; gps_left the same in the LAST sample of
                the first partial render (the "pages left by the first partial render" of H-TAIL and of R-5)
  x734_clear    0x0734 bit 0 clear in every sample from 0x0720 non-zero to the first grow sample (None without 0x0734 or a grow)
  x734_zero     0x0734 read 0 in every sample (the clause "cannot tell" of the plan's stop list)
  gmax          the highest global page count of the whole job (a default-triangle job stays at 1: the scene check)
CLI (the laptop runner):  r6read.py line OUT [BUF09]   one `key=value` line;   r6read.py steps OUT   `k S a b` lines;
                          r6read.py ends OUT            `k E` lines (F4's timeline rule);
                          r6read.py model OUT 0xS2,0xS3,...  status 0 when the frozen model's steps lie in the job's brackets;
                          r6read.py kept NAME KIND      the kept file name;
                          r6read.py check OUT           status 0 when the capture is whole, else why.
"""
from __future__ import annotations

import struct
import sys

KEPT = {"out": ".txt", "dmesg": ".dmesg", "buf09": ".after.buf09.bin", "regs": ".after.regs.txt", "page": ".page.json",
        "status": ".status.json", "param": ".p1139-green.param.bin", "tadata": ".p1139-green.tadata.bin"}
X_US = 75          # F4's frozen gap (f4_phase.out: "X = 75 us")


def kept_name(name: str, kind: str) -> str:
    """The kept (gzipped) file name of a job's file of this kind: the runner writes it, the scorer reads it."""
    return name + KEPT[kind] + ".gz"


def hx(s: str) -> int:
    return int(s, 16)


def parse(text: str):
    """(regs, rows, start): regs as ints, rows [(t, {reg: value})] of the first timeline block, start the header's start."""
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
                return regs, rows, None          # a cut line: the capture is not whole
            rows.append((int(p[1]), dict(zip(regs, (hx(x) for x in p[2:2 + len(regs)])))))
    return regs, rows, start


def check(text: str) -> str | None:
    """None when the capture is whole: a timeline block, every tl line complete, the text ending with a newline; else why."""
    if "timeline: regs" not in text:
        return "no timeline block"
    if not text.endswith("\n"):
        return "the text does not end with a newline (cut)"
    regs, rows, start = parse(text)
    if start is None:
        return f"a cut timeline line after {len(rows)} lines"
    if not rows:
        return "a timeline block with no sample"
    return None


def lo(v):
    return v & 0xFFFF


def hi(v):
    return (v >> 16) & 0xFFFF


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


def gap(seq, T):
    """f4_phase.gap: microseconds from the first sample with page count >= T to the first with >= T + 1 (times in ns)."""
    a = next((t for t, p in seq if p >= T), None)
    b = next((t for t, p in seq if p >= T + 1), None)
    return None if a is None or b is None else (b - a) / 1000.0


def ends(seq, S, X=X_US):
    """f4_phase.ends, unchanged: E_k = the smallest T in [S_k + 2, min(S_k+1, S_k + 0x200)) with gap(T) > X, or None."""
    out = {}
    for k, s in S.items():
        nxt = S.get(k + 1, 1 << 30)
        e = None
        for T in range(s + 2, min(nxt, s + 0x200)):
            g = gap(seq, T)
            if g is not None and g > X:
                e = T
                break
        out[k] = e
    return out


def model_check(r: dict, model: list) -> str | None:
    """None when every model step S_k (k = 2, 3, ... in order) that the first run passed lies in the job's bracket for k; else why.
    The runner's test of a calibration against the frozen model (stage r-n: a calibration off the model re-picks its B cells)."""
    if not r.get("S"):
        return "no step read"
    for i, s in enumerate(model):
        k = i + 2
        if s >= r.get("peak1", 0):
            continue
        if k not in r["iv"]:
            return f"step {k} (model 0x{s:x}) not seen"
        lo_, hi_ = r["iv"][k]
        if not lo_ <= s <= hi_:
            return f"step {k} bracket [0x{lo_:x}, 0x{hi_:x}], model 0x{s:x}"
    return None


def buf_words(b: bytes | None):
    if not b or len(b) < 4 * 39:
        return None
    return list(struct.unpack_from(f"<{len(b) // 4}I", b))


def reading(text: str, buf09: bytes | None = None) -> dict:
    regs, rows, start = parse(text)
    if start is None:
        return dict(void="capture cut")
    if not regs or not rows or 0x658 not in regs or 0x724 not in regs:
        return dict(void="no timeline")
    # R1's partial renders and runs (dpm3.runs_of)
    prs, peaks, cur, inpr = [], [], 0, False
    for _, v in rows:
        if v[0x658] & 1:
            if not inpr:
                prs.append(lo(v[0x724]))
                peaks.append(cur)
                cur, inpr = 0, True
            continue
        inpr = False
        cur = max(cur, lo(v[0x724]))
    peaks.append(cur)
    knob = next((v.get(0x624) for t, v in rows if t >= start and lo(v[0x724]) != 0), None)
    thr0 = prs[0] if prs else None
    reach = bool(thr0 is not None and len(peaks) > 1 and peaks[1] >= thr0)
    st = stretches(rows)
    a = st[0][0] if st else len(rows)
    r = dict(void=None, nparts=len(prs), thr0=thr0, peaks=peaks, reach=reach, valid=bool(reach and len(prs) > 1), knob=knob,
             need=max(peaks) if peaks else None, nsamples=len(rows))
    # the global page steps of the first TA run
    steps, S, amb = {}, {}, {}
    if 0x72c in regs:
        pg = pp = None
        for i in range(0, a):
            v = rows[i][1]
            g, p = hi(v[0x72c]), hi(v[0x724])
            if pg is not None and g > pg and pg >= 1:
                for k in range(pg + 1, g + 1):     # a jump by more than one page: each page passed has the same bracket
                    steps[k] = (pp, p)
                    S[k] = max(pp, p - 1)
                    amb[k] = p - pp > 1
            pg, pp = g, p
        r["gps_abort"] = hi(rows[a - 1][1][0x72c]) if st and a > 0 else None
        r["gps_left"] = hi(rows[st[0][1]][1][0x72c]) if st else None
        r["gmax"] = max(hi(v[0x72c]) for _, v in rows)
    else:
        r["gps_abort"] = r["gps_left"] = r["gmax"] = None
    r["steps"], r["S"], r["amb"] = steps, S, amb
    r["iv"] = {k: (a_, max(a_, b_ - 1)) for k, (a_, b_) in steps.items()}
    # monotone: every page from 2 up seen, the steps never going down (two pages passed between two samples share a value)
    r["mono"] = bool(S) and all(S[k] <= S[k2] for k, k2 in zip(sorted(S), sorted(S)[1:])) and sorted(S) == list(range(2, 2 + len(S)))
    # F4's timeline rule (f4_phase.rows_and_refs and ends): the first run's rising page counts with their times
    seq, mx = [], 0
    for i in range(0, a):
        t_, p_ = rows[i][0], hi(rows[i][1][0x724])
        if p_ < mx:
            break
        if p_ > mx:
            seq.append((t_, p_))
            mx = p_
    r["peak1"] = mx
    r["ends"] = ends(seq, S)
    # F7's run peaks (f7_replay.kept): the high half of 0x0724 in each run, row 0 left out as there
    bounds = [(1, st[0][0] if st else len(rows))] + [(st[k][1] + 1, st[k + 1][0] if k + 1 < len(st) else len(rows)) for k in range(len(st))]
    r["runpeaks"] = [max(hi(rows[i][1][0x724]) for i in range(a_, e_)) for a_, e_ in bounds if e_ > a_]
    # the grow (0x0628 low half below 0x10 between 0x0720 leaving 0 and the first partial render)
    g0 = next((i for i, (_, v) in enumerate(rows) if v.get(0x720, 0)), None) if 0x720 in regs else None
    gi = None
    if g0 is not None and 0x628 in regs:
        last = min(a, len(rows) - 1)
        gi = next((i for i in range(g0, last + 1) if lo(rows[i][1][0x628]) < 0x10), None)
    # a threshold below 0x10 reads below 0x10 by itself (the default triangle's low cells): no grow reading there
    r["grow"] = gi is not None if (g0 is not None and 0x628 in regs and (knob or 0) >= 0x10) else None
    if 0x734 in regs:
        r["x734_zero"] = all(v[0x734] == 0 for _, v in rows)
        r["x734_clear"] = all(not rows[i][1][0x734] & 1 for i in range(g0, gi + 1)) if gi is not None else None
    else:
        r["x734_zero"] = r["x734_clear"] = None
    # the raise: dword 38 (R3-geo) and 0x0624 above thr0 after the first partial render (the plan's second clause)
    w = buf_words(buf09)
    r["dw36"], r["dw38"] = (w[36], w[38]) if w else (None, None)
    r["raised"] = (w[38] == 0x20) if w else None
    r["raise_tl"] = bool(st and thr0 is not None and 0x624 in regs and any(v[0x624] > thr0 for _, v in rows[st[0][1] + 1:]))
    if not r["valid"]:
        r["cls"] = "V"
    elif r["raised"] is None:
        r["cls"] = "V"
    else:
        r["cls"] = "R" if r["raised"] else "N"
    return r


def line(r: dict) -> str:
    """The runner's one-line view (bash reads it with `field`)."""
    if r.get("void"):
        return "void=1 cls=V"
    f = lambda v: "-" if v is None else (f"0x{v:x}" if isinstance(v, int) and not isinstance(v, bool) else str(int(v)) if isinstance(v, bool) else str(v))
    s = " ".join(f"S{k}=0x{v:x}" for k, v in sorted(r["S"].items()))
    return (f"void=0 cls={r['cls']} nparts={r['nparts']} thr0={f(r['thr0'])} knob={f(r['knob'])} need={r['need']} "
            f"valid={int(r['valid'])} grow={f(r['grow'])} gps_abort={f(r['gps_abort'])} gps_left={f(r['gps_left'])} "
            f"gmax={f(r['gmax'])} mono={int(r['mono'])} {s}").strip()


def main(argv):
    if len(argv) >= 3 and argv[1] == "line":
        text = open(argv[2], errors="replace").read()
        buf = open(argv[3], "rb").read() if len(argv) > 3 else None
        print(line(reading(text, buf)))
        return 0
    if len(argv) >= 3 and argv[1] == "check":
        why = check(open(argv[2], errors="replace").read())
        if why:
            print(why)
            return 1
        return 0
    if len(argv) >= 4 and argv[1] == "kept":
        print(kept_name(argv[2], argv[3]))
        return 0
    if len(argv) >= 3 and argv[1] == "ends":
        r = reading(open(argv[2], errors="replace").read())
        for k in sorted(r.get("ends", {})):
            if r["ends"][k] is not None:
                print(k, r["ends"][k])
        return 0
    if len(argv) >= 4 and argv[1] == "model":
        why = model_check(reading(open(argv[2], errors="replace").read()), [int(x, 16) for x in argv[3].split(",")])
        if why:
            print(why)
            return 1
        return 0
    if len(argv) >= 3 and argv[1] == "steps":
        r = reading(open(argv[2], errors="replace").read())
        for k in sorted(r.get("S", {})):
            a, b = r["steps"][k]
            print(k, r["S"][k], a, b)
        return 0
    print("usage: r6read.py line OUT [BUF09] | steps OUT | ends OUT | model OUT LIST | kept NAME KIND | check OUT", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
