# SPDX-License-Identifier: MIT
"""Scorer of g6-rw (Q230, the 1/w word), parts g6-rwa (8 controls) and g6-rw (L, B, replicates, E).  Written before the run; frozen
with the predictions.  Plan: closing6/pixel/exp-pixel-r6.md section 4.  Decode: R4's score_rw.py and R5's score_rw5.py unchanged
(read_job: pbdump's first object, each predicted vertex matched at its frozen window within 1/32 pixel; word_records, word_table).
Controls (g6-rwa): rw-k0..k5 and d-01, d-02, every known word exact (R4.control_state); a control that is not a pass makes every
row cannot tell.  Gate of part a (the driver's, before part b): every control passes.
Rows: per word "RZ or RZ + 1"; per job shape (object, 3 vertices at the frozen window, depth 0x3f000000): a job without it is
FAILED shape, its words cannot tell; three FAILED shapes among L and B void L and B (the design is wrong).
H-FRAC (E872): held iff no L or B word with frac < 0.5 stores RZ + 1 and >= 20 such words are read; one such word refutes it.
H-SMOOTH(s): a window is separable iff min frac of its RZ + 1 words > max frac of its RZ words; scored only with >= 30 of 36 words
read, >= 4 RZ + 1 and >= 4 RZ words above frac 0.5; held iff both windows of the stride are separable, refuted iff both have an
inversion, mixed otherwise (no stride is predicted to hold).  The interval of e a separable window gives is printed.
H-MANT per exponent (E rows): held iff 12 of 12 words equal R4's delta; jobs without their shape: "no object at this exponent".
Replicates: the words of their L job.  B: the smallest frac that stores RZ + 1, reported.
  score(kept_a, kept_b, preds) -> (text, result); the last line starts with SUMMARY:"""
from __future__ import annotations

import collections
import sys
from fractions import Fraction as F

sys.dont_write_bytecode = True

import rwdesign6 as D  # noqa: E402
import score_rw as R4  # noqa: E402
import score_rw5 as W5  # noqa: E402
import scorekit as SK  # noqa: E402

SHAPE_STOP = 3
HFRAC_MIN = 20


def controls(k, preds):
    names = sorted(n for n in preds if n.startswith(("rw-k", "d-")))
    jobs = {n: R4.read_job(k, preds, n) for n in names}
    return {n: R4.control_state(jobs[n], preds) for n in names}, jobs


def gate_a(k, preds):
    ctl, _ = controls(k, preds)
    return SK.gate(ctl), []


def window_state(recs):
    """(state, text) of one window from its records [(frac, delta)]: separable True / False, or None (cannot tell)."""
    rz1 = [f for f, d in recs if d == 1]
    rz = [f for f, d in recs if d == 0]
    if len(recs) < 30 or len(rz1) < 4 or sum(1 for f in rz if f > F(1, 2)) < 4:
        return None, f"cannot tell ({len(recs)} read, {len(rz1)} RZ + 1, {sum(1 for f in rz if f > F(1, 2))} RZ above 0.5)"
    lo, hi = min(rz1), max(rz)
    if lo > hi:
        return True, f"separable: RZ + 1 from frac {float(lo):.4f}, RZ up to {float(hi):.4f}: e in [{float(1 - lo):.4f}, {float(1 - hi):.4f})"
    inv = sum(1 for a in rz1 for b in rz if a < b)
    return False, f"inversion: {inv} (RZ + 1, RZ) pairs out of order; RZ + 1 from {float(lo):.4f}, RZ up to {float(hi):.4f}"


def score(ka, kb, preds):
    k = W5.Both(ka, kb)
    out = []
    ctl, cj = controls(k, preds)
    g = SK.gate(ctl)
    out.append("Q230 (g6-rw): controls " + "; ".join(f"{n} {SK._state(v)}" for n, v in ctl.items()))
    names = [n for n in preds if not n.startswith(("rw-k", "d-", "@"))]
    order = {"l": 0, "b": 1, "r": 2, "e": 3}
    names.sort(key=lambda n: (order.get(n[0], 9), n))
    jobs, recs = W5.word_records(k, preds, names, {})
    out += ["", W5.word_table(recs), ""]
    shape = {n: (None if jobs[n]["void"] else bool(jobs[n]["shape"])) for n in names}
    for n in names:
        if jobs[n]["notes"]:
            out.append(f"{n}: {'FAILED shape' if shape[n] is False else 'shape'} ({', '.join(jobs[n]['notes'])})")
    for grp, pre in (("L", "l-"), ("B", "b-"), ("replicates", "rl-"), ("E", "e")):
        out.append(f"job shape, {grp}: {SK.tally([SK.gated(g, shape[n]) for n in names if n.startswith(pre)])}")
    out.append(f"'RZ or RZ+1', all: {SK.tally([SK.gated(g, r[6]) for r in recs])}")
    got = {(r[0], r[1]): r[4] for r in recs}
    rzw = {(r[0], r[1]): r[3] for r in recs}
    delta = {}
    for r in recs:
        if r[4] is not None and not jobs[r[0]]["void"] and shape[r[0]] and r[6]:
            delta[(r[0], r[1])] = r[4] - r[3]
    lbfail = [n for n in names if n.startswith(("l-", "b-")) and shape[n] is False]
    lb_void = len(lbfail) >= SHAPE_STOP
    if lb_void:
        out.append(f"L and B VOID: {len(lbfail)} jobs FAILED shape ({', '.join(lbfail[:6])}): the design is wrong")
    # ---- H-FRAC on L and B
    word = lambda n, i: R4._list(R4.pq(preds, n, "w_words"))[i]
    below, above, mins = [], collections.Counter(), []
    seen = {}
    for n in names:
        if not n.startswith(("l-", "b-")):
            continue
        for i in range(3):
            if (n, i) not in delta:
                continue
            M = D.mant(word(n, i))
            f = D.frac(M)
            seen[M] = (f, delta[(n, i)])
    for M, (f, d) in seen.items():
        if f < F(1, 2):
            below.append(d)
        else:
            above[d] += 1
            if d == 1:
                mins.append(f)
    nb, nb1 = len(below), sum(below)
    if not g.ok or lb_void:
        hfrac = None
    elif nb1:
        hfrac = False
    else:
        hfrac = True if nb >= HFRAC_MIN else None
    out.append(f"H-FRAC on L and B: {nb} mantissas with frac < 0.5, {nb1} of them RZ + 1; {sum(above.values())} above 0.5, "
               f"{above[1]} RZ + 1: {SK._state(hfrac)}")
    if mins:
        out.append(f"smallest frac storing RZ + 1 (L and B): {float(min(mins)):.4f}")
    bm = [D.frac(D.mant(word(n, i))) for n in names if n.startswith("b-") for i in range(3) if delta.get((n, i)) == 1]
    out.append(f"B: RZ + 1 at {len(bm)} words; smallest frac {float(min(bm)):.4f}" if bm else "B: no RZ + 1 word read")
    # ---- H-SMOOTH per window and stride
    wins = collections.defaultdict(dict)
    for n in names:
        if n.startswith("l-"):
            tag = R4.pq(preds, n, "window").split(":")[0]
            for i in range(3):
                if (n, i) in delta:
                    M = D.mant(word(n, i))
                    wins[tag][M] = (D.frac(M), delta[(n, i)])
    hs = {}
    for _, sn in D.STRIDES:
        sts = []
        for wn in "ab":
            st, txt = window_state(list(wins.get(sn + wn, {}).values())) if g.ok and not lb_void else (None, "cannot tell (controls or L void)")
            sts.append(st)
            out.append(f"window {sn}{wn}: {txt}")
        if None in sts:
            hs[sn] = "cannot tell"
        elif all(sts):
            hs[sn] = "held"
        elif not any(sts):
            hs[sn] = "refuted"
        else:
            hs[sn] = "mixed"
        out.append(f"H-SMOOTH(2^{sn}): {hs[sn]}")
    # ---- replicates
    rep = []
    for n in names:
        if n.startswith("rl-"):
            src = R4.pq(preds, n, "same_as")
            for i in range(3):
                a, b = got.get((n, i)), got.get((src, i))
                rep.append(None if a is None or b is None else a == b)
    out.append(f"replicates (their L job's words): {SK.tally(rep)}")
    # ---- H-MANT per exponent
    hm = {}
    for e in D.EXPS:
        es = [n for n in names if n.startswith("e") and R4.pq(preds, n, "exp") == str(e)]
        if not g.ok:
            hm[e] = "cannot tell (controls)"
        elif any(shape[n] is False for n in es):
            hm[e] = f"no object at this exponent ({sum(1 for n in es if shape[n] is False)} of {len(es)} jobs FAILED shape)"
        else:
            sts, miss = [], []
            for n in es:
                ds = R4.pq(preds, n, "hmant").split(",")
                for i in range(3):
                    gv = got.get((n, i))
                    st = None if gv is None or jobs[n]["void"] else (gv - rzw[(n, i)]) == int(ds[i])
                    sts.append(st)
                    if st is False:
                        miss.append(f"{n}.{i}")
            t = SK.tally(sts)
            hm[e] = ("held 12 of 12" if t.held == 12 else f"REFUTED ({t.failed} miss: {', '.join(miss[:4])})" if t.failed
                     else f"cannot tell ({t.cannot_tell} not read)")
        out.append(f"H-MANT at exponent {e}: {hm[e]}")
    if not g.ok:
        verdict = "cannot tell: controls " + "; ".join(g.problems)
    else:
        verdict = (f"H-FRAC {SK._state(hfrac)} ({nb1} RZ + 1 of {nb} below 0.5); H-SMOOTH " + ", ".join(f"2^{s} {v}" for s, v in hs.items())
                   + "; H-MANT " + ", ".join(f"{e}: {v.split(' (')[0]}" for e, v in hm.items())
                   + ("" if not rep or all(rep) else "; a replicate differs or is not read") + ("; L and B VOID" if lb_void else ""))
    res = dict(gate=g, controls=ctl, hfrac=hfrac, hsmooth=hs, hmant=hm, replicate=rep, lb_void=lb_void, recs=recs, shape=shape)
    out.append("SUMMARY: " + verdict + "; " + SK.headline("every word is RZ or RZ+1 of 1/w", ctl, [SK.gated(g, r[6]) for r in recs]))
    return "\n".join(out), res


def score_a(k, preds):
    ctl, _ = controls(k, preds)
    g = SK.gate(ctl)
    out = ["Q230 (g6-rwa): " + "; ".join(f"{n} {SK._state(v)}" for n, v in ctl.items())]
    out.append("SUMMARY: part a: " + ("PASS" if g.ok else ("FAILED: " if g.failed else "CANNOT TELL: ") + "; ".join(g.problems)))
    return "\n".join(out), {"gate": g, "controls": ctl}
