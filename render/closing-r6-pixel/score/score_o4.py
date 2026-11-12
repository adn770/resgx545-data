# SPDX-License-Identifier: MIT
"""Scorer of p4-o4 (Q276, the o4 clause).  Written before the run; frozen with the predictions.  Standard library only.

Word layout (gen/r4_o4.py): low 16 bits = marker << 6 | variant bits (5:4) << 4 | tag (3:0).  o4 words are the words with tag 5 or
13; class labels A (tag 5), A4 (bit 4), A5 (bit 5), A3 (tag 13), other:TT.  A job without a marker prediction (c-e709: E709's own
program) is read by tag only (layout 'tag'), and so are the real R3 / R1 records the tests use.
Per job: the o4 word count per class.  A class counts with >= 10 words in the job; another class with <= 2 words is noise.
A configuration (x job and y job) reads: its class; `none` (<= 2 o4 words in both jobs); `mixed:...` (two classes with >= 10 words);
cannot tell (a count in 3..9, or the jobs disagree).  Void jobs (Kept.void: no output, bad rc, skipped, class not ok) are cannot tell.
Controls (scorekit.gate): G-o4 = c-e709 and c-o4-u pass the structural criteria (tag-5 words 10..100 in each job, pairs 5..60, every pair
source (even, even), tag-13 words <= 2 in the x job) and c-o4-u reads A; c-o4s-u reads A (E808); both gate the 7 value rows; c-u (the
tag-2 fraction of the o1 sources >= 0.98) gates the 6 predicate rows besides.  The marker proof of a job (>= 95% of the paired words
carry its marker) failing voids that configuration.
Verdict: survivors = models of the frozen family whose prediction equals the observed class in every value row; (model, gating) survivors
over the predicate rows (cannot tell if the bit-4 pairs c-v-a-a4 and c-v-a4-a read one class in both orders); answered iff every control
passes, the 7 value and 6 predicate rows are decided, the survivors share one gating and one prediction vector, and the replicate of
c-o4-u reads the class of c-o4-u."""
from __future__ import annotations

import collections
import math
import re
import sys
sys.dont_write_bytecode = True

import r4lib as L  # noqa: E402
import scorekit as SK  # noqa: E402

BG = L.BG
MIN_WORDS = 10
OTHER_MAX = 2
MIN_SOURCES = 300
O4_TAGS = (5, 13)
PAIR_TAGS = (2, 12, 5, 13)
VALUE_CFGS = ["v-a3", "v-a4", "v-a-a4", "v-a4-a", "v-a-a5", "v-a5-a", "v-a3-a4"]
PRED_CFGS = [f"{o}-k{k}" for o in ("pa", "ps") for k in (0, 3, 7)]
LABEL = {(5, 0): "A", (5, 1): "A4", (5, 2): "A5", (13, 0): "A3"}


def f32_hi(v):
    return L.f32v(v & 0xffff0000)


def source_of(vx, vy, w=64, h=64):
    sx = round(f32_hi(vx) * w / 2 + w / 2 - .5)
    sy = round(f32_hi(vy) * h / 2 + h / 2 - .5)
    return (sx, sy) if 0 <= sx < w and 0 <= sy < h else None


def read_grid(k, name, w=64, h=64):
    g = L.rows_of(k.out(name) or "")
    return g if len(g) == h and all(len(r) == w for r in g) else None


def klass(word, variants):
    tag, v = word & 15, (word >> 4) & 3 if variants else 0
    return LABEL.get((tag, v), f"other:{tag}.{v}")


def class_counts(g, variants):
    c = collections.Counter()
    for r in g:
        for v in r:
            if v != BG and (v & 15) in O4_TAGS:
                c[klass(v, variants)] += 1
    return c


def decode_pairs(gx, gy, marker, variants):
    """({tag: {(sx, sy)}}, marker_ok): words at the same pixel of the x and y image with the same tag (and variant bits),
    decoded to their source pixel; marker_ok: >= 95% of those words carry the job's marker (x) and marker + 1 (y), or None."""
    src = {t: set() for t in PAIR_TAGS}
    good = bad = 0
    for y in range(len(gx)):
        for x in range(len(gx[0])):
            vx, vy = gx[y][x], gy[y][x]
            if BG in (vx, vy) or (vx & 15) != (vy & 15) or (vx & 15) not in PAIR_TAGS:
                continue
            if variants and (vx >> 4 & 3) != (vy >> 4 & 3):
                continue
            s = source_of(vx, vy, len(gx[0]), len(gx))
            if s is None:
                continue
            src[vx & 15].add(s)
            if marker is not None:
                if ((vx & 0xffff) >> 6) == marker and ((vy & 0xffff) >> 6) == marker + 1:
                    good += 1
                else:
                    bad += 1
    ok = None if marker is None else (good + bad > 0 and good / (good + bad) >= 0.95)
    return src, ok


def read_class(cx, cy):
    """The class of a configuration from the per-class counts of its x and y job: label, 'none', 'mixed:..' or None."""
    labels = set(cx) | set(cy)
    big, amb = set(), False
    for lab in labels:
        for c in (cx, cy):
            n = c.get(lab, 0)
            if n >= MIN_WORDS:
                big.add(lab)
            elif n > OTHER_MAX:
                amb = True
    if not big:
        return None if amb else "none"
    for lab in big:                                     # a big class must be big in both jobs
        if cx.get(lab, 0) < MIN_WORDS or cy.get(lab, 0) < MIN_WORDS:
            return None
    if amb:
        return None
    return next(iter(big)) if len(big) == 1 else "mixed:" + "+".join(sorted(big))


def g_o4_control(cx, cy, pairs5, parity_bad, x13):
    why = []
    for k, c in (("x", cx), ("y", cy)):
        v = sum(n for lab, n in c.items() if lab.startswith(("A", "other:5")))
        if not 10 <= v <= 100:
            why.append(f"tag-5 words in the {k} job {v} (10..100)")
    if not 5 <= pairs5 <= 60:
        why.append(f"tag-5 pairs {pairs5} (5..60)")
    if parity_bad:
        why.append(f"{parity_bad} of {pairs5} pair sources are not (even, even)")
    if x13 > 2:
        why.append(f"tag-13 words in the x job {x13} (<= 2)")
    return not why, why


def read_cfg(k, preds, cfg):
    """dict(void, cx, cy, cls, marker_ok, src, variants) of one configuration (names c-CFG-x / -y)."""
    nx, ny = f"c-{cfg}-x", f"c-{cfg}-y"
    vv = k.void(nx) or k.void(ny)
    if vv:
        return dict(void=vv)
    gx, gy = read_grid(k, nx), read_grid(k, ny)
    if gx is None or gy is None:
        return dict(void="no 64x64 pixel rows")
    mk = preds.get(nx, {}).get("marker", [])
    marker = int(mk[0][0], 16) if mk else None
    variants = marker is not None
    src, mok = decode_pairs(gx, gy, marker, variants)
    if mok is False:
        return dict(void="marker proof failed: the program that ran is not the frozen one")
    cx, cy = class_counts(gx, variants), class_counts(gy, variants)
    return dict(void=None, cx=cx, cy=cy, cls=read_class(cx, cy), src=src, variants=variants,
                x13=sum(n for lab, n in cx.items() if lab == "A3" or lab.startswith("other:13")))


def frozen_models(preds, cfg):
    """{model token: label} of a configuration's frozen o4_class rows (set heldout); a model token is the first word of the
    model text ('V1/last', or 'V1/last+gated' for a predicate row)."""
    return {m.split(" ")[0]: v for v, m, st in preds.get(f"c-{cfg}-x", {}).get("o4_class", []) if st == "heldout"}


def score(k, preds):
    out = []
    cf = {c: read_cfg(k, preds, c) for c in ["e709", "o4-u", "o4s-u", "u"] + VALUE_CFGS + PRED_CFGS}
    for c, r in cf.items():
        if r["void"]:
            out.append(f"{c}: NODATA ({r['void']})")
        else:
            out.append(f"{c}: class {r['cls']}  x {dict(r['cx'])}  y {dict(r['cy'])}")
    # ---- controls
    ctl = {}

    def g4(c):
        r = cf[c]
        if r["void"]:
            return None
        p5 = r["src"][5]
        bad = sum(1 for s in p5 if s[0] & 1 or s[1] & 1)
        ok, why = g_o4_control(r["cx"], r["cy"], len(p5), bad, r["x13"])
        if not ok:
            out.append(f"G-o4 control {c}: FAIL {why}")
        return ok
    ctl["G-o4 c-e709"] = g4("e709")
    ctl["G-o4 c-o4-u"] = g4("o4-u")
    ctl["c-o4-u reads A"] = None if cf["o4-u"]["void"] else cf["o4-u"]["cls"] == "A"
    ctl["c-o4s-u reads A (E808)"] = None if cf["o4s-u"]["void"] else cf["o4s-u"]["cls"] == "A"
    gate_v = SK.gate(ctl)
    ru = cf["u"]
    crit = float(preds.get("c-u-x", {}).get("ctl_min_frac", [("0.98",)])[0][0])
    if ru["void"]:
        g1 = None
    else:
        n2, n12 = len(ru["src"][2]), len(ru["src"][12])
        frac = n2 / (n2 + n12) if n2 + n12 else 0.0
        g1 = n2 + n12 >= MIN_SOURCES and frac >= crit
        out.append(f"G-o1 control c-u: tag-2 fraction {frac:.3f} of {n2 + n12} sources (frozen >= {crit}): {'PASS' if g1 else 'FAIL'}")
    gate_p = SK.gate({**ctl, "G-o1 c-u": g1})
    out.append("controls (value rows): " + ("PASS" if gate_v.ok else "; ".join(gate_v.problems)))
    out.append("controls (predicate rows, adds G-o1): " + ("PASS" if gate_p.ok else "; ".join(gate_p.problems)))
    # ---- replicate
    rep = None
    nx = "c-o4-u-x-rep"
    if nx in k.names() and not cf["o4-u"]["void"]:
        vv = k.void(nx) or k.void("c-o4-u-y-rep")
        if vv:
            out.append(f"replicate c-o4-u: NODATA ({vv})")
        else:
            gx, gy = read_grid(k, nx), read_grid(k, "c-o4-u-y-rep")
            if gx is not None and gy is not None:
                rep = read_class(class_counts(gx, True), class_counts(gy, True)) == cf["o4-u"]["cls"]
                out.append(f"replicate c-o4-u: class {read_class(class_counts(gx, True), class_counts(gy, True))} vs {cf['o4-u']['cls']}: "
                           f"{'same' if rep else 'DIFFERENT'}")
    # ---- value rows
    fam = sorted({m for cfg in VALUE_CFGS for m in frozen_models(preds, cfg)})
    FM = {c: frozen_models(preds, c) for c in VALUE_CFGS + PRED_CFGS}
    obs = {c: (None if cf[c]["void"] else cf[c]["cls"]) for c in VALUE_CFGS}
    rows, surv = [], set(fam)
    for c in VALUE_CFGS:
        fm = FM[c]
        if obs[c] is None:
            rows.append(None)
            continue
        rows.append(obs[c] in set(fm.values()))                  # the family can produce what was read
        surv &= {m for m, v in fm.items() if v == obs[c]}
    decided_v = all(o is not None for o in obs.values())
    gv = gate_v.ok
    out.append("value rows read: " + ", ".join(f"{c}={obs[c]}" for c in VALUE_CFGS))
    if gv and decided_v:
        out.append(f"value survivors ({len(surv)} of {len(fam)}): {sorted(surv) or 'none: no model of the family fits'}")
    # ---- predicate rows
    pobs = {c: (None if cf[c]["void"] else cf[c]["cls"]) for c in PRED_CFGS}
    same4 = obs["v-a-a4"] is not None and obs["v-a-a4"] == obs["v-a4-a"]
    psurv = set()
    if gv and decided_v and gate_p.ok and not same4 and all(o is not None for o in pobs.values()):
        for m in surv:
            for g in ("gated", "ignored"):
                tag = f"{m}+{g}"
                if all(FM[c].get(tag) == pobs[c] for c in PRED_CFGS):
                    psurv.add(tag)
        out.append("predicate rows read: " + ", ".join(f"{c}={pobs[c]}" for c in PRED_CFGS))
        out.append(f"(model, gating) survivors: {sorted(psurv) or 'none'}")
    elif same4:
        out.append("predicate rows: cannot tell (the bit-4 pairs read one class in both orders)")
    # ---- verdict
    vec = lambda tag: tuple(FM[c].get(tag.split("+")[0] if c in VALUE_CFGS else tag) for c in VALUE_CFGS + PRED_CFGS)
    answered = False
    if not gv:
        verdict = "cannot tell: " + "; ".join(gate_v.problems)
    elif not decided_v:
        verdict = "cannot tell: a value row is void or unreadable"
    elif not surv:
        verdict = "family REFUTED: no (single-write path, combine rule) model fits the value rows; a new reading is needed"
    elif same4:
        verdict = f"value rows: {len(surv)} model(s) survive {sorted(surv)}; predicate rows cannot tell (the bit-4 pairs read one class in both orders)"
    elif not gate_p.ok:
        verdict = f"value rows: survivors {sorted(surv)}; predicate rows cannot tell: " + "; ".join(gate_p.problems)
    elif not all(o is not None for o in pobs.values()):
        verdict = f"value rows: survivors {sorted(surv)}; a predicate row is void or unreadable"
    elif not psurv:
        verdict = f"value rows: survivors {sorted(surv)}; no (model, gating) fits the predicate rows"
    else:
        gat = {s.split("+")[1] for s in psurv}
        vecs = {vec(s) for s in psurv}
        answered = len(gat) == 1 and len(vecs) == 1 and rep is not False
        verdict = (f"Q276 o4 clause {'ANSWERED' if answered else 'narrowed, not answered'}: gating {sorted(gat)}, "
                   f"{len(vecs)} prediction class(es) among {sorted(psurv)}" + ("" if rep is not False else "; the replicate of c-o4-u read another class"))
    head = SK.headline("the o4 family reads", {**ctl}, rows)
    out.append("rows: " + head)
    out.append("SUMMARY: " + verdict)
    return "\n".join(out), {"answered": answered, "value_survivors": sorted(surv), "pred_survivors": sorted(psurv), "obs": obs,
                            "pobs": pobs, "controls": ctl, "replicate": rep}
