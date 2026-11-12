# SPDX-License-Identifier: MIT
"""Scorer of p5-o4 (Q276: what the tag-5 word is).  Written before the run; frozen with the predictions.  Standard library only.
Plan: closing5/pixel/exp-pixel-r5.md section 2.  Reading (R4's decode, score/score_o4.py byte for byte: read_grid, decode_pairs,
source_of, read_class, g_o4_control): a configuration is its x job and y job; words of the same tag and variant bits at the same pixel
are a pair, decoded to their source pixel (x from the x job's high half, y from the y job's).
Per configuration: the labels "T:B" (tag T in 4, 5, 13; bits 5:4 = B) counted per job; the displaced tag-1 pairs d1 (tag-1 pairs
whose source is not their own pixel; 0 in R4's 17 configurations).  Reading (R4's class rule): a label with >= 10 words in both jobs
and no other label above 2; `none` when no label is above 2; with d1 >= 10 (and <= 100) and no tag-4/5 class: `d1`; d1 or a label
count in 3..9: cannot tell.  A job without the frozen marker on >= 95% of its pairs is void (the program is not the frozen one).
Controls (scorekit.gate): G-o4 on c-e709 (R4's structural criteria), G-o1 on c-u (tag-2 fraction >= 0.98 of >= 300 o1 sources),
c-all4 reads 5:1 (every model; anything else and the layout cannot be read: the stage is void), c-v-a4 reads 5:0 (E838's class A).
The BRIDGE controls (the driver's gate: a failure stops the session) are c-e709, c-u and c-v-a4.  Positive control of the walk: in
w-0 >= 95% of the own-pixel tag-1 words carry bit 4, in w-1 >= 95% of the tag-2 words (it gates the walk).
Verdict: "the tag-5 word is MODEL" iff the controls pass, the 8 walk entries are decided and equal one frozen vector, z-o3, l-o4 and
l-o6 read that model's cells and the replicate of w-3 agrees; a decided walk that is no frozen vector: "family refuted, vector
recorded"; else cannot tell by entry.  Predicate sets: P4 scored only if the model reads o4, P3 only if it reads o3; (gating)
survivors among gated / ignored; the other set is cannot tell by design.  n-o4 is read and reported against its frozen cells."""
from __future__ import annotations

import collections
import sys

sys.dont_write_bytecode = True

import rd_r4lib as L  # noqa: E402
import rd_score_o4 as R4  # noqa: E402  (R4's reader, unchanged)
import scorekit as SK  # noqa: E402

BG = L.BG
WALK = [f"w-{j}" for j in range(8)]
INDEP = ["z-o3", "l-o4", "l-o6", "n-o4"]
PSET = {ps: [f"{ps}-{o}-k{k}" for o in ("pa", "ps") for k in (0, 3, 7)] for ps in ("p4", "p3")}
CONTROLS = ["c-e709", "c-u", "c-all4", "c-v-a4"]
ALL = CONTROLS + WALK + INDEP + PSET["p4"] + PSET["p3"]
D1_MIN, D1_MAX = 10, 100


def labels(g, variants):
    c = collections.Counter()
    for r in g:
        for v in r:
            if v != BG and (v & 15) in (4, 5, 13):
                c[f"{v & 15}:{(v >> 4) & 3 if variants else 0}"] += 1
    return c


def pairs(gx, gy, marker):
    """(d1, own tag-1 pairs [(x job word)], all pairs by tag {tag: [x job words]}, marker_ok) over the pixels of a configuration."""
    d1, own1, bytag = 0, [], collections.defaultdict(list)
    good = bad = 0
    for y in range(len(gx)):
        for x in range(len(gx[0])):
            vx, vy = gx[y][x], gy[y][x]
            if BG in (vx, vy) or (vx & 15) != (vy & 15) or (vx >> 4 & 3) != (vy >> 4 & 3):
                continue
            s = R4.source_of(vx, vy, len(gx[0]), len(gx))
            if s is None:
                continue
            t = vx & 15
            bytag[t].append(vx)
            if t == 1:
                if s == (x, y):
                    own1.append(vx)
                else:
                    d1 += 1
            if marker is not None:
                if ((vx & 0xffff) >> 6) == marker and ((vy & 0xffff) >> 6) == marker + 1:
                    good += 1
                else:
                    bad += 1
    mok = None if marker is None else (good + bad > 0 and good / (good + bad) >= 0.95)
    return d1, own1, bytag, mok


def reading(cx, cy, d1):
    cls = R4.read_class(cx, cy)
    if cls is None:
        return None
    if D1_MIN <= d1 <= D1_MAX:
        return "d1" if cls == "none" else "mixed:" + cls + "+d1"
    if d1 > 2:
        return None
    return cls


def read_cfg(k, preds, cfg, xname=None, yname=None):
    nx, ny = xname or f"{cfg}-x", yname or f"{cfg}-y"
    vv = k.void(nx) or k.void(ny)
    if vv:
        return dict(void=vv)
    for n in (nx, ny):
        if k.case(n).get("class") not in ("ok", None, ""):
            return dict(void=f"class {k.case(n).get('class')}")
    gx, gy = R4.read_grid(k, nx), R4.read_grid(k, ny)
    if gx is None or gy is None:
        return dict(void="no 64x64 pixel rows")
    mk = preds.get(f"{cfg}-x", {}).get("marker", [])
    marker = int(mk[0][0], 16) if mk else None
    variants = marker is not None
    d1, own1, bytag, mok = pairs(gx, gy, marker)
    if mok is False:
        return dict(void="marker proof failed: the program that ran is not the frozen one")
    cx, cy = labels(gx, variants), labels(gy, variants)
    src, _ = R4.decode_pairs(gx, gy, marker, variants)
    return dict(void=None, cx=cx, cy=cy, d1=d1, own1=own1, bytag=bytag, src=src, cls=reading(cx, cy, d1),
                x13=sum(n for lab, n in cx.items() if lab.startswith("13:")), gx=gx, gy=gy)


def frozen(preds, cfg, q="o4_word", name=None):
    return {m: v for v, m, st in preds.get(name or f"{cfg}-x", {}).get(q, [])}


def frac_bit4(words):
    return (sum(1 for w in words if (w >> 4) & 1) / len(words)) if words else 0.0


def score(k, preds):
    out = []
    cf = {c: read_cfg(k, preds, c) for c in ALL}
    for c, r in cf.items():
        if r["void"]:
            out.append(f"{c}: NODATA ({r['void']})")
        else:
            out.append(f"{c}: reads {r['cls']}  d1 {r['d1']}  x {dict(r['cx'])}  y {dict(r['cy'])}")
    # ---- controls
    ctl = {}
    r = cf["c-e709"]
    if r["void"]:
        ctl["G-o4 c-e709"] = None
    else:
        p5 = r["src"][5]
        cx5 = collections.Counter({("A" if lab.startswith("5:") else lab): n for lab, n in r["cx"].items()})
        cy5 = collections.Counter({("A" if lab.startswith("5:") else lab): n for lab, n in r["cy"].items()})
        okc, why = R4.g_o4_control(cx5, cy5, len(p5), sum(1 for s in p5 if s[0] & 1 or s[1] & 1), r["x13"])
        ctl["G-o4 c-e709"] = okc
        if not okc:
            out.append(f"G-o4 control c-e709: FAIL {why}")
        b = collections.Counter((w >> 4) & 3 for row in r["gx"] for w in row if w != BG and (w & 15) == 5)
        out.append(f"c-e709-x bits 5:4 of the tag-5 words (reported; frozen 3): {dict(b)}")
    ru = cf["c-u"]
    crit = float(preds.get("c-u-x", {}).get("ctl_min_frac", [("0.98",)])[0][0])
    if ru["void"]:
        ctl["G-o1 c-u"] = None
    else:
        n2, n12 = len(ru["src"][2]), len(ru["src"][12])
        frac = n2 / (n2 + n12) if n2 + n12 else 0.0
        ctl["G-o1 c-u"] = n2 + n12 >= R4.MIN_SOURCES and frac >= crit
        out.append(f"G-o1 control c-u: tag-2 fraction {frac:.3f} of {n2 + n12} sources (frozen >= {crit})")
    for c in ("c-all4", "c-v-a4"):
        want = set(frozen(preds, c).values())
        ctl[f"{c} reads {'/'.join(sorted(want))}"] = None if cf[c]["void"] or cf[c]["cls"] is None else cf[c]["cls"] in want
    bridge = {n: v for n, v in ctl.items() if not n.startswith("c-all4")}
    gate = SK.gate(ctl)
    pos = {}
    for j, tag in ((0, 1), (1, 2)):
        r = cf[f"w-{j}"]
        if r["void"]:
            pos[f"positive w-{j}"] = None
            continue
        ws = r["own1"] if j == 0 else r["bytag"].get(2, [])
        f = frac_bit4(ws)
        pos[f"positive w-{j}"] = len(ws) >= 30 and f >= 0.95
        out.append(f"positive control w-{j}: {f:.3f} of {len(ws)} {'own-pixel tag-1' if j == 0 else 'tag-2'} words carry bit 4")
    wgate = SK.gate({**ctl, **pos})
    out.append("controls: " + ("PASS" if gate.ok else "; ".join(gate.problems)))
    out.append("walk gate (controls + positive controls): " + ("PASS" if wgate.ok else "; ".join(wgate.problems)))
    # ---- per-tag map of the walk (reported, not scored)
    for j in range(8):
        r = cf[f"w-{j}"]
        if not r["void"]:
            m = {t: dict(collections.Counter((w >> 4) & 3 for w in ws)) for t, ws in sorted(r["bytag"].items())}
            out.append(f"w-{j} pairs by tag: bits 5:4 counts {m}")
    # ---- replicate
    rep = None
    if "w-3-x-rep" in k.names():
        rr = read_cfg(k, preds, "w-3", "w-3-x-rep", "w-3-y-rep")
        rep_cls = None if rr["void"] else rr["cls"]
        if rep_cls is not None and cf["w-3"]["cls"] is not None and not cf["w-3"]["void"]:
            rep = rep_cls == cf["w-3"]["cls"]
        out.append(f"replicate w-3: {rep_cls if not rr['void'] else 'NODATA ' + rr['void']} vs {cf['w-3'].get('cls')}")
    # ---- the walk
    fam = list(frozen(preds, "w-0").keys())
    vecs = {m: tuple(frozen(preds, c)[m] for c in WALK) for m in fam}
    obs = tuple(None if cf[c]["void"] else cf[c]["cls"] for c in WALK)
    out.append("walk read: " + " ".join(str(o) for o in obs))
    model, verdict, answered, rows = None, None, False, []
    ind = {c: (None if cf[c]["void"] else cf[c]["cls"]) for c in INDEP}
    psurv = {}
    if not gate.ok:
        verdict = "cannot tell: controls " + "; ".join(gate.problems)
    elif not wgate.ok:
        verdict = "cannot tell: walk positive control " + "; ".join(wgate.problems)
    elif None in obs:
        verdict = "cannot tell: walk entries " + ", ".join(c for c, o in zip(WALK, obs) if o is None) + " not decided"
    else:
        match = [m for m, v in vecs.items() if v == obs]
        if not match:
            verdict = f"family refuted, vector recorded: walk {' '.join(obs)}"
        else:
            model = match[0]
            cells = {c: frozen(preds, c)[model] for c in INDEP}
            for c in INDEP:
                if cells[c] == "nofrozen":
                    out.append(f"{c}: {ind[c]} (no frozen cell for {model}: cannot tell by design)")
                    continue
                rows.append(None if ind[c] is None else ind[c] == cells[c])
                out.append(f"{c}: read {ind[c]}, {model} frozen {cells[c]}: {SK._state(rows[-1])}")
            core = [ind[c] == cells[c] if ind[c] is not None else None for c in ("z-o3", "l-o4", "l-o6")]
            if False in core:
                verdict = f"family refuted, vector recorded: the walk reads {model} but an independent row differs ({ind})"
            elif None in core:
                verdict = f"cannot tell: the walk reads {model}; an independent row is not decided"
            elif rep is not True:
                verdict = f"cannot tell: the walk reads {model}; the replicate of w-3 {'differs' if rep is False else 'is not decided'}"
            else:
                answered = True
                verdict = f"the tag-5 word is {model} (walk, z-o3, l-o4, l-o6 and the replicate)"
            # predicate sets, gated by the model
            for ps, cfgs in PSET.items():
                gate_list = [v for v, m_, st in preds.get("@p5-o4", {}).get(f"{ps}_gate", [])][0].split()
                if model not in gate_list:
                    out.append(f"{ps.upper()}: cannot tell by design ({model} does not read o{ps[1]})")
                    continue
                pobs = {c: (None if cf[c]["void"] else cf[c]["cls"]) for c in cfgs}
                if None in pobs.values():
                    out.append(f"{ps.upper()}: cannot tell (a row not decided: {pobs})")
                    continue
                s = [g for g in ("gated", "ignored") if all(frozen(preds, c)[f"{model}+{g}"] == pobs[c] for c in cfgs)]
                psurv[ps] = s
                out.append(f"{ps.upper()} read {pobs}; gating survivors {s or 'none'}")
            if answered and psurv:
                verdict += "; predicate " + ", ".join(f"{ps.upper()} {v[0] if len(v) == 1 else (v or 'none')}" for ps, v in psurv.items())
    out.append("rows: " + SK.headline("the walk's model holds on the independent rows", ctl, rows))
    out.append("SUMMARY: " + verdict)
    return "\n".join(out), {"answered": answered, "model": model, "obs": obs, "controls": ctl, "bridge": bridge, "gate": SK.gate(bridge),
                            "replicate": rep, "pred": psurv, "independent": ind}
