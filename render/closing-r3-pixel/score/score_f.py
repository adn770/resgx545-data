# SPDX-License-Identifier: MIT
"""Scorers of q-f0 (the loop controls) and q-f1a / q-f1b (what the latch counts), Q082 pixel side, fills.  Written before the run
and frozen with the predictions.  numpy is not needed.

Every row: STATUS2 read after the reset (must be 0x400) and after the job; the loop proof (relative loops: o0 = MARK on 2048 of
2048, else the job is VOID for every hypothesis: E770's failure); the burst B and the time t6 of bit 6 from the regtimeline.
Hypotheses (constants and per-N predictions in r3const.py): H-MA, H-WD, H-WD-busy, H-BURST (H-ITER and H-INSTR, E769's refuted
rows, are printed without weight).  Verdict rule: a hypothesis is refuted by ONE ladder whose two orders agree and contradict it;
`holds` needs every ladder; the two orders disagreeing at one N marks that N `edge` (E431's 54 was 2 of 3), never a refutation; a
contradiction seen in one order only is `unreplicated` (neither holds nor refuted)."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import re  # noqa: E402

import r3const as C  # noqa: E402
import r3lib as L  # noqa: E402
from r3job import job  # noqa: E402

FILL = 2048


def mark(n):
    return 0xC0DE0000 | n


def _band(v):
    """'204+-125' -> (204.0, 125.0); '120..340' -> (120.0, 340.0) as (lo, hi) via _range."""
    m = re.fullmatch(r"([\d.]+)\+-([\d.]+)", v)
    return (float(m[1]), float(m[2])) if m else None


# ------------------------------------------------------------------------------------------------------------------ q-f0
F0_NAME = re.compile(r"f0-(rel|abs)-b8-(\d+)(b?)$")


def f0_jobs(k):
    out = []
    for n in k.names():
        m = F0_NAME.match(n)
        if not m:
            continue
        form, N = m[1], int(m[2])
        j = job(k, n, mark=mark(N) if form == "rel" else 0, count=FILL)
        j.update(form=form, N=N)
        out.append(j)
    return out


def f0_state(k):
    """('open' | 'closed' | 'disagree' | 'edge', message, jobs).  Open: every relative row that ran proved its loop (o0 = MARK
    on 2048 of 2048) and at least the first one ran.  Closed: a relative row failed its proof (or the stage did not run).
    Disagree: abs and rel rows are each consistent on the bit at N = 53 and 56 and differ."""
    js = f0_jobs(k)
    rel = [j for j in js if j["form"] == "rel"]
    if not rel:
        return "closed", "q-f0 did not run: no relative loop row", js
    bad = [j["name"] + (f" ({j['void']})" if j["void"] else " (no MARK on 2048 of 2048)") for j in rel
           if j["void"] or j["proof"] is not True]
    ran = [j for j in rel if not j["void"] and j["proof"] is True]
    if bad or not ran:
        return "closed", f"the relative loop did not prove itself: {bad or 'no relative row ran'}", js
    dis, edge = [], []
    for N in (53, 56):
        sides = {}
        for f in ("rel", "abs"):
            bits = {j["bit6"] for j in js if j["form"] == f and j["N"] == N and not j["void"] and j["bit6"] is not None
                    and (j["proof"] is True or f == "abs")}
            sides[f] = bits
        if len(sides["rel"]) == 1 and len(sides["abs"]) == 1 and sides["rel"] != sides["abs"]:
            dis.append(N)
        elif len(sides["rel"]) > 1 or len(sides["abs"]) > 1:
            edge.append(N)
    if dis:
        return "disagree", f"abs and rel loops differ on the bit at N = {dis}", js
    return ("edge" if edge else "open"), (f"rel loop proved on {len(ran)} rows" + (f"; the bit is not repeatable at N = {edge}" if edge else "")), js


def score_f0(k, preds):
    js = f0_jobs(k)
    state, msg, _ = f0_state(k)
    out = ["q-f0: per job (proof = o0 MARK on 2048 of 2048, abs: o0 0 on 2048 of 2048; bit 6; burst B; t6 from the burst's start)",
           L.table([(j["name"], j["void"] or ("proof " + ("ok" if j["proof"] else "FAILED")), f"{j['post']:#x}" if j["post"] is not None else "-",
                     "-" if j["B"] is None else f"{j['B']:.0f}", "-" if j["t6"] is None else f"{j['t6']:.0f}") for j in js],
                   ["job", "state", "STATUS2 after", "B us", "t6 us"]), ""]
    notes = []
    for j in js:
        if j["void"]:
            continue
        pn = preds.get(j["name"], {})
        for v, m, s in pn.get("bit6", []):
            ok = (j["bit6"] == (v == "set"))
            notes.append(f"{j['name']}: bit 6 {'set' if j['bit6'] else 'clear'}, frozen {v}: {'ok' if ok else 'MISS'}")
        for v, m, s in pn.get("B_us", []):
            c, t = _band(v)
            if j["B"] is not None:
                notes.append(f"{j['name']}: B {j['B']:.0f} us vs {c:.0f} +- {t:.0f}: {'ok' if abs(j['B'] - c) <= t else 'MISS'}")
        for v, m, s in pn.get("t6_us", []):
            lo, hi = (float(x) for x in v.split(".."))
            if j["bit6"] and j["t6"] is not None:
                notes.append(f"{j['name']}: t6 {j['t6']:.0f} us vs {lo:.0f}..{hi:.0f}: {'ok' if lo <= j['t6'] <= hi else 'MISS'}")
    out += notes + [""]
    bitmiss = [n for n in notes if "bit 6" in n and "MISS" in n]
    out.append(f"SUMMARY: q-f0 loop gate {state.upper()}: {msg}; frozen bits {'all as E431 (53 clear, 56 set)' if not bitmiss else 'MISSED: ' + str(bitmiss)}; "
               f"{sum(1 for n in notes if 'MISS' in n)} misses of {len(notes)} frozen quantities")
    return "\n".join(out), {"state": state}


# ------------------------------------------------------------------------------------------------------------------ q-f1
F1_NAME = re.compile(r"f([ab])-(b16|b12|b4|b2|b8n|ld8)-n(\d+)$")


def f1_collect(k):
    """{(kind, N): job record} of one order."""
    out = {}
    for n in k.names():
        m = F1_NAME.match(n)
        if not m:
            continue
        kind, N = m[2], int(m[3])
        out[(kind, N)] = job(k, n, mark=mark(N), count=FILL)
    return out


def usable(j):
    return j is not None and not j["void"] and j["proof"] is True and j["bit6"] is not None


def _fit_points(kind, a, b):
    """The ladder's two short points [(N, B)] from the usable runs of both orders (mean B); None if a point has no B."""
    pts = []
    for N in C.F_LADDERS[kind][:2]:
        bs = [j["B"] for j in (a.get((kind, N)), b.get((kind, N))) if usable(j) and j["B"] is not None]
        if not bs:
            return None
        pts.append((N, sum(bs) / len(bs)))
    return pts


HYP = ["H-MA", "H-WD", "H-WD-busy", "H-BURST"]


def ladder_eval(kind, a, b):
    """Per N of one ladder: the agreed bit (or None: edge / not usable), and each hypothesis' verdict at it.  Returns
    (rows, info): rows [(N, bit_a, bit_b, agreed, state, {hyp: pred})], info {nstar, band, fit}."""
    pts = _fit_points(kind, a, b)
    nstar, band = C.wd_nstar(pts) if pts else (None, None)
    rows = []
    wd_first_set = None
    for N in C.F_LADDERS[kind]:
        ja, jb = a.get((kind, N)), b.get((kind, N))
        ua, ub = usable(ja), usable(jb)
        ba = ja["bit6"] if ua else None
        bb = jb["bit6"] if ub else None
        if ua and ub:
            agreed, state = (ba, "agree") if ba == bb else (None, "edge")
        elif ua or ub:
            agreed, state = (ba if ua else bb), "one order"
        else:
            agreed, state = None, "void"
        bs = [j["B"] for j in (ja, jb) if usable(j) and j["B"] is not None]
        own_b = sum(bs) / len(bs) if bs else None
        pred = {"H-MA": C.pred_ma(kind, N),
                "H-WD": C.pred_wd(kind, N, nstar, band, own_b),
                "H-BURST": C.pred_burst(own_b) if own_b is not None else C.EITHER}
        if kind == "ld8":
            w = pred["H-WD"]
            if w == "set" and wd_first_set is None:
                wd_first_set = N
                pred["H-WD-busy"] = "clear"
            else:
                pred["H-WD-busy"] = "clear" if w in ("clear", C.EITHER) else C.EITHER
        else:
            pred["H-WD-busy"] = pred["H-WD"]
        rows.append((N, ba, bb, agreed, state, pred))
    return rows, {"nstar": nstar, "band": band, "fit": pts}


def ladder_result(kind, a, b):
    """{hyp: ('refuted' | 'holds' | 'unreplicated' | 'no decided point', [details])} for one ladder (FIT rows excluded)."""
    rows, info = ladder_eval(kind, a, b)
    fit = set(C.F_LADDERS[kind][:2])
    res = {}
    for h in HYP:
        refuted, unrep, decided = [], [], 0
        for N, ba, bb, agreed, state, pred in rows:
            if N in fit or state in ("edge", "void"):
                continue
            p = pred[h]
            if p == C.EITHER:
                continue
            decided += 1
            if (p == "set") != bool(agreed):
                (refuted if state == "agree" else unrep).append(f"N {N}: predicted {p}, got {'set' if agreed else 'clear'}"
                                                                 + ("" if state == "agree" else " (one order)"))
        if refuted:
            res[h] = ("refuted", refuted)
        elif unrep:
            res[h] = ("unreplicated", unrep)
        elif decided == 0:
            res[h] = ("no decided point", [])
        else:
            res[h] = ("holds", [f"{decided} decided points"])
    return res, rows, info


def latch_times(a, b, infos):
    """Jobs with the bit set and N >= 1.3 N*(H-WD): t6 in [120, 340] us (H-EARLY: H-WD, H-MA-early) or within 15% of B (H-END)."""
    early = end = n = 0
    ts = []
    for kind in C.F_LADDERS:
        ns = infos[kind]["nstar"]
        for order in (a, b):
            for N in C.F_LADDERS[kind]:
                j = order.get((kind, N))
                if not usable(j) or not j["bit6"] or j["t6"] is None or j["B"] is None:
                    continue
                if ns is None or N < C.LONG_FACTOR * ns:
                    continue
                n += 1
                ts.append((kind, N, j["t6"], j["B"]))
                early += C.T6_LO <= j["t6"] <= C.T6_HI
                end += abs(j["t6"] - j["B"]) <= C.T6_END_FRAC * j["B"]
    return n, early, end, ts


def cluster_check(a, b, infos):
    """Near the threshold (N* <= N < 1.3 N*) H-WD alone predicts t6 in clusters one tile time apart: 25 + k (B - 60.2) / 4 + T*,
    k = 0..3, +- 30 us.  Returns (jobs, hits)."""
    n = hit = 0
    for kind in C.F_LADDERS:
        ns = infos[kind]["nstar"]
        if ns is None:
            continue
        for order in (a, b):
            for N in C.F_LADDERS[kind]:
                j = order.get((kind, N))
                if not usable(j) or not j["bit6"] or j["t6"] is None or j["B"] is None or not (ns <= N < C.LONG_FACTOR * ns):
                    continue
                n += 1
                tile = (j["B"] - C.B0) / C.TILES
                hit += any(abs(j["t6"] - (C.CLUSTER_START + kk * tile + C.T_STAR)) <= C.CLUSTER_TOL for kk in range(C.TILES))
    return n, hit


def f1_verdict(a, b):
    """Both orders: per hypothesis the ladders that refute / leave unreplicated / hold; the verdict text."""
    lines, per = [], {h: {} for h in HYP}
    infos = {}
    for kind in C.F_LADDERS:
        res, rows, info = ladder_result(kind, a, b)
        infos[kind] = info
        lines.append(f"ladder {kind}: N* (H-WD) = " + ("-" if info["nstar"] is None else f"{info['nstar']:.1f} +- {100 * info['band']:.0f}%")
                     + "; " + " ".join(f"{N}:{'.' if st == 'void' else ('E' if st == 'edge' else ('S' if g else 'c'))}"
                                       + ("" if st in ("agree", "void", "edge") else "*") for N, ba, bb, g, st, p in rows)
                     + "  (S set, c clear, E edge = the orders differ, . void, * one order only)")
        for h in HYP:
            per[h][kind] = res[h]
    verdict = {}
    for h in HYP:
        ref = [k_ for k_, (s, d) in per[h].items() if s == "refuted"]
        unr = [k_ for k_, (s, d) in per[h].items() if s == "unreplicated"]
        nod = [k_ for k_, (s, d) in per[h].items() if s == "no decided point"]
        if ref:
            verdict[h] = f"REFUTED by {ref}"
        elif unr or nod:
            verdict[h] = f"open (unreplicated {unr}, no decided point {nod})"
        else:
            verdict[h] = "HOLDS on every ladder"
    lines += [f"{h}: {verdict[h]}" for h in HYP]
    # E769's two refuted rows, without weight
    n, early, end, ts = latch_times(a, b, infos)
    lines.append(f"time of the latch (jobs set at N >= 1.3 N*): {n} jobs; t6 in [120, 340] us (H-EARLY): {early}; within 15% of B (H-END): {end}")
    cn, ch = cluster_check(a, b, infos)
    lines.append(f"near the threshold: {ch} of {cn} set jobs have t6 on an H-WD tile cluster (25 + k (B - 60.2)/4 + 121.8 +- 30 us)")
    # the unexplained case
    def last_set(kind):
        N = C.F_LADDERS[kind][-1]
        ja, jb = a.get((kind, N)), b.get((kind, N))
        return any(usable(j) and j["bit6"] for j in (ja, jb))
    b4_never = not any(usable(j) and j["bit6"] for kk, j in list(a.items()) + list(b.items()) if kk[0] == "b4")
    unexpl = (not last_set("b2")) and (not last_set("b8n")) and b4_never and any(usable(j) for j in list(a.values()) + list(b.values()))
    if unexpl:
        lines.append("NEITHER b2 nor b8n sets by its last point and b4 never sets: H-MA and H-WD are both refuted; E769's fit stays unexplained")
    ld = [r for r in ladder_eval("ld8", a, b)[0]]
    first_ld = next((N for N, ba, bb, g, st, p in ld if g and st in ("agree", "one order")), None)
    lines.append(f"ld8: first N with the bit set = {first_ld} (H-WD-busy: later than H-WD's first set point)")
    return lines, verdict, unexpl, infos


def score_f1(k, preds, order):
    me = f1_collect(k)
    other = {}
    rows = [(f"f{order}-{kind}-n{N}", "void: " + j["void"] if j["void"] else ("proof FAILED" if j["proof"] is not True else "ok"),
             "-" if j["post"] is None else f"{j['post']:#x}", "-" if j["B"] is None else f"{j['B']:.0f}",
             "-" if j["t6"] is None else f"{j['t6']:.0f}") for (kind, N), j in sorted(me.items(), key=lambda kv: (list(C.F_LADDERS).index(kv[0][0]), kv[0][1]))]
    out = [f"q-f1{order}: per job (loop proof, STATUS2 after, burst B, t6)",
           L.table(rows, ["job", "state", "STATUS2", "B us", "t6 us"]), ""]
    a, b = (me, other) if order == "a" else (other, me)
    lines, verdict, unexpl, infos = f1_verdict(a, b)
    out += ["single-order view (the verdict needs both orders; `unreplicated` here is expected):"] + lines + [""]
    nv = sum(1 for j in me.values() if j["void"] or j["proof"] is not True)
    sets = sum(1 for j in me.values() if usable(j) and j["bit6"])
    out.append(f"SUMMARY: q-f1{order}: {len(me)} jobs read, {nv} void (loop proof or STATUS2 pre failed), {sets} with bit 6 set; "
               + "; ".join(f"{h} {verdict[h].split(' ')[0].lower()}" for h in HYP) + " (single order: the two-order verdict is `verdict`)")
    return "\n".join(out), {"collect": me}
