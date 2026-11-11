# SPDX-License-Identifier: MIT
"""Scorer of q-v (Q082 TA side: bit 7 of CR_EVENT_STATUS2 with a looping vertex program).  Written before the run; frozen with the
predictions.  Readers: R2-geo's g-t5v (the stored depth words), the burst of the regtimeline.

Loop proof of every row: the stored depth word of EVERY decoded vertex = 0x3f200000 + N (z = 0.25 + 4N ulp); a vertex that did
not run N iterations, or a branch that fell through, shows (E770's failure mode) and voids the row.  Rows with V > 3 vertices
use the same decode; the decoded vertex count is reported (`nv`) and a count other than V is a note, not a void (the object may
list fewer vertices than the tool copied; never run on hardware).  Controls: ctl0 / n1 / n3 (bit 7 clear, loop proof), i880 clear and
i1760 set (E784).  Narrowing: the b8v ladder up and down gives a bracket (last clear, first set] of N8*, both orders within one
step of 55.  Ladders: b16v, b4v, v12, v48 against the frozen formulas of N8* (HV-INSTR, HV-MA, HV-JOB), tolerance one ladder step;
HV-TIME: the burst's length B at a job >= B at N8* (-10%); t7 the same within 25% in every set job (an end-of-work latch has t7
growing with N)."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import re  # noqa: E402
import statistics  # noqa: E402

import r3const as C  # noqa: E402
import r3lib as L  # noqa: E402
from r3job import job  # noqa: E402

NAME = re.compile(r"v-(ctl0|n(\d+)|i(\d+)|(up|dn)-n(\d+)|(b16v|b4v|v12|v48)-n(\d+))$")
BITMASK = C.BIT7


def parse(n):
    """(group, N, V): group ctl0 / ctl / up / dn / b16v / b4v / v12 / v48."""
    m = NAME.match(n)
    if not m:
        return None
    if m[1] == "ctl0":
        return "ctl0", 0, 3
    if m[2]:
        return "ctl", int(m[2]), 3
    if m[3]:
        return "ctl", int(m[3]), 3
    if m[4]:
        return m[4], int(m[5]), 3
    return m[6], int(m[7]), {"v12": 12, "v48": 48}.get(m[6], 3)


def vjob(k, name, N, V):
    j = job(k, name)
    j["N"], j["V"] = N, V
    j["proof"], j["nv"], j["words"] = None, None, None
    if j["void"]:
        return j
    c = k.case(name)
    param, tad = k.dump(name, "param.bin"), k.dump(name, "tadata.bin")
    if param is None or tad is None:
        j["void"] = "dump missing"
        return j
    ws = L.depth_words(param, tad)
    if ws is None:
        j["void"] = "dump unreadable"
        return j
    want = C.BASE_DEPTH + N
    j["words"], j["nv"] = ws, len(ws)
    j["proof"] = len(ws) >= 3 and all(w == want for w in ws)
    return j


def collect(k):
    d = {}
    for n in k.names():
        p = parse(n)
        if p is None:
            continue
        g, N, V = p
        if k.case(n).get("class") == "skipped":
            d.setdefault(g, {})[N] = dict(name=n, skipped=True, void="skipped", N=N, V=V, proof=None, bit7=None, B=None, t7=None)
            continue
        j = vjob(k, n, N, V)
        j["name"] = n
        d.setdefault(g, {})[N] = j
    return d


def ok(j):
    return j is not None and not j.get("void") and j.get("proof") is True and j.get("bit7") is not None


def bracket(pairs, lo_bound=None, hi_bound=None):
    """(last clear, first set] from [(N, bit)] of usable rows, with the controls as bounds (880 clear, 1760 set);
    (lo, hi, monotone)."""
    ps = sorted(pairs)
    mono = all(not (a[1] and not b[1]) for a, b in zip(ps, ps[1:]))
    sets = [N for N, b in ps if b]
    clears = [N for N, b in ps if not b]
    hi = min(sets) if sets else hi_bound
    lo = max([c for c in clears if hi is None or c < hi], default=lo_bound)
    return lo, hi, mono


def br(b):
    """(lo, hi] as text."""
    return f"({b[0]}, {b[1]}]"


def ladder_bracket(g):
    return bracket([(N, j["bit7"]) for N, j in g.items() if ok(j)])


def consistent(pred, br, ns):
    """The frozen prediction pred (a point N* from the narrowing bracket: (flo, fhi) interval) against a ladder's observed bracket
    (lo, hi]: strict overlap (post-run fix A1, POSTRUN-FIX.md): a first set point in (lo, hi] can lie in [flo, fhi].  An open end is
    None; there is no slack of a step.  ns (the ladder's points) is kept for the callers and no longer used."""
    flo, fhi = pred
    lo, hi = br
    return (hi is None or flo <= hi) and (lo is None or fhi > lo)


def evaluate(d):
    lines = []
    ctl = d.get("ctl", {})
    c0 = d.get("ctl0", {}).get(0)
    bad = []
    for name, j, want in (("ctl0", c0, False), ("n1", ctl.get(1), False), ("n3", ctl.get(3), False), ("i880", ctl.get(880), False),
                          ("i1760", ctl.get(1760), True)):
        if not ok(j) or j["bit7"] != want or j["pre"] != 0x400:
            bad.append(f"{name}: " + ("not run" if j is None else (j["void"] or ("loop proof FAILED" if j["proof"] is not True else f"bit 7 {'set' if j['bit7'] else 'clear'}, frozen {'set' if want else 'clear'}"))))
    n3_alone = bool(bad) and all(b.startswith("n3") for b in bad)
    info = dict(bad=bad, n3_alone=n3_alone)
    if bad:
        return lines, None, info
    up, dn = d.get("up", {}), d.get("dn", {})
    bu = bracket([(N, j["bit7"]) for N, j in up.items() if ok(j)], 880, 1760)
    bd = bracket([(N, j["bit7"]) for N, j in dn.items() if ok(j)], 880, 1760)
    lines.append(f"b8v narrowing: up (last clear, first set] = {br(bu)} monotone {bu[2]}; down {br(bd)} monotone {bd[2]}")
    agree = bu[1] is not None and bd[1] is not None and abs(bu[1] - bd[1]) <= 55 and abs((bu[0] or 0) - (bd[0] or 0)) <= 55
    width = (bu[1] - bu[0]) if bu[1] is not None and bu[0] is not None else None
    lines.append(f"  bracket width {width} (frozen: 55); the two orders {'agree within one step' if agree else 'DIFFER by more than one step'}")
    both = (min(bu[0], bd[0]) if bu[0] is not None and bd[0] is not None else bu[0], max(bu[1], bd[1]) if bu[1] is not None and bd[1] is not None else bu[1])
    n8 = both
    info.update(bu=bu, bd=bd, agree=agree, n8=n8, width=width)
    res = {}
    for key in ("b16v", "b4v", "v12", "v48"):
        g = d.get(key, {})
        if not g:
            continue
        pts = [(N, j["bit7"]) for N, j in g.items() if ok(j)]
        lo, hi, mono = bracket(pts)
        ns = sorted(g)
        row = {"bracket": (lo, hi), "mono": mono, "n": len(pts), "skipped": sum(1 for j in g.values() if j.get("skipped"))}
        for hyp in ("HV-INSTR", "HV-MA", "HV-JOB"):
            f_lo, f_hi = C.v_formula(hyp, key, n8[0]) if n8[0] else None, C.v_formula(hyp, key, n8[1]) if n8[1] else None
            if f_lo is None and f_hi is None:
                if hyp == "HV-JOB" and key in ("b16v", "b4v"):
                    row[hyp] = "by INSTR or MA"
                continue
            pred = (min(f_lo, f_hi), max(f_lo, f_hi))
            row[hyp] = (pred, consistent(pred, (lo, hi), ns))
        # HV-TIME: B >= B(N8*) - 10%: the b8v narrowing ladder gives B at the bracket
        bl = next((j["B"] for N, j in sorted(up.items()) if ok(j) and not j["bit7"] and j["B"] is not None and N == n8[0]), None)
        bh = next((j["B"] for N, j in sorted(up.items()) if ok(j) and j["bit7"] and j["B"] is not None and N == n8[1]), None)
        if bh is None:
            bh = next((j["B"] for N, j in sorted(dn.items()) if ok(j) and j["bit7"] and j["B"] is not None and N == n8[1]), None)
        hit = tot = 0
        for N, j in g.items():
            if not ok(j) or j["B"] is None or bh is None:
                continue
            p = "set" if j["B"] >= 0.9 * bh else ("clear" if bl is not None and j["B"] <= 1.1 * bl else None)
            if p is None:
                continue
            tot += 1
            hit += (p == "set") == bool(j["bit7"])
        row["HV-TIME"] = (tot, hit)
        t7s = [(N, j["t7"], j["B"]) for N, j in sorted(g.items()) if ok(j) and j["bit7"] and j["t7"] is not None]
        if len(t7s) >= 2:
            med = statistics.median(t for _, t, _ in t7s)
            row["t7"] = dict(n=len(t7s), within25=sum(1 for _, t, _ in t7s if abs(t - med) <= 0.25 * med), median=med)
        res[key] = row
    info["ladders"] = res
    for key, row in res.items():
        lines.append(f"{key}: observed (last clear, first set] = {br(row['bracket'])} (monotone {row['mono']}, {row['n']} usable, {row['skipped']} skipped by the sweep): "
                     + "; ".join(f"{h} {v[0][0]:.0f}..{v[0][1]:.0f} {'ok' if v[1] else 'MISS'}" if isinstance(v, tuple) and isinstance(v[0], tuple) else f"{h} {v}"
                                 for h, v in row.items() if h.startswith("HV-") and h != "HV-TIME")
                     + (f"; HV-TIME {row['HV-TIME'][1]} of {row['HV-TIME'][0]} rows as the burst predicts" if row.get("HV-TIME") and row["HV-TIME"][0] else "")
                     + (f"; t7 within 25% of the median in {row['t7']['within25']} of {row['t7']['n']} set jobs" if "t7" in row else ""))
    return lines, res, info


def score_v(k, preds):
    d = collect(k)
    lines, res, info = evaluate(d)
    rows = []
    for g in ("ctl0", "ctl", "up", "dn", "b16v", "b4v", "v12", "v48"):
        for N, j in sorted(d.get(g, {}).items()):
            rows.append((j["name"], "skipped (sweep)" if j.get("skipped") else j["void"] or ("loop proof FAILED" if j["proof"] is not True else "ok"),
                         "-" if j.get("post") is None else f"{j['post']:#x}", j.get("nv", "-"), "-" if j.get("B") is None else f"{j['B']:.0f}",
                         "-" if j.get("t7") is None else f"{j['t7']:.0f}"))
    out = ["q-v: per job (loop proof = every vertex's depth word 0x3f200000 + N, STATUS2 after, decoded vertices, burst B, t7)",
           L.table(rows, ["job", "state", "STATUS2", "nv", "B us", "t7 us"]), ""] + lines + [""]
    if res is None:
        why = ("the first backward branch did not loop as E784 saw it (n3): no ladder row is a reading" if info["n3_alone"]
               else "control(s) failed")
        out.append(f"SUMMARY: cannot tell: {why}: {info['bad']}")
        return "\n".join(out), info
    parts = []
    for key, row in res.items():
        for h in ("HV-INSTR", "HV-MA", "HV-JOB"):
            v = row.get(h)
            if isinstance(v, tuple) and isinstance(v[0], tuple):
                parts.append(f"{key} {h} {'consistent' if v[1] else 'REFUTED'}")
    out.append(f"SUMMARY: controls pass; b8v bracket (last clear, first set] up {br(info['bu'])} down {br(info['bd'])} "
               f"({'orders agree' if info['agree'] else 'ORDERS DIFFER'}, width {info['width']}); " + "; ".join(parts))
    return "\n".join(out), info
