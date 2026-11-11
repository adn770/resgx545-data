# SPDX-License-Identifier: MIT
"""Scorer of q4-v (Q082 TA side, bit 7 held out against the TA-clock rule).  Written before the run; frozen with the predictions.

Reading of a job: the kept regtimeline (r4tl): L = the longest run of samples with CLKGATESTATUS (0x0008) == 0x000ccff8, bit 7 of STATUS2
after the job, the time of bit 7 from the start of that run.  The frozen rule (r4tl.bit7_rule): CLEAR below L = 122 us, SET above
136 us, the edge between not scored; a set job shows bit 7 118 to 138 us after its run began.  Loop proof: the stored depth word of EVERY
decoded vertex = 0x3f200000 + N (3 vertices at least), else the job is VOID (a loop that did not run N times must not be read).
Controls (the bridge to E807 on the rgn4 module, each of them gates every ladder row): v-ctl0 (clear, no TA run), v-n1 (clear), v-i880
(clear, L 95..112), v-i1760 (set, L 160..260).  The ladders' FIT points (set `control` in the table) are tallied apart as FIT rows and do
not gate.  The stock rows (1500 vertices, 2048x2048 twice and 4096x4096): H-STALL (bit 7 clear) against H-PHASE (set), only where the
job's L is at least 125 us (else void for that).  A void job is `cannot tell`, never a pass; a control that is not a pass shuts the gate:
every held-out row is then `cannot tell` (scorekit.gate).  The headline is printed only with every control passed and a row decided.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import re  # noqa: E402

import r4const as C  # noqa: E402
import r4lib as L  # noqa: E402
import r4tl as T  # noqa: E402
import scorekit as SK  # noqa: E402
from r4job import job  # noqa: E402

NAME = re.compile(r"v-(ctl0|n(\d+)|i(\d+)|(b12v|b2v|v24)-n(\d+)|stock-(2048-a|2048-b|4096))$")
STOCK_MIN_L = 125.0
CONTROLS = ("v-ctl0", "v-n1", "v-i880", "v-i1760")


def parse(n):
    """(group, N, V) with group ctl0 / ctl / b12v / b2v / v24 / stock."""
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
        return m[4], int(m[5]), 24 if m[4] == "v24" else 3
    return "stock", 0, 1500


def vjob(k, name, N, V, group):
    j = job(k, name)
    j.update(N=N, V=V, group=group, proof=None, nv=None, words=None)
    if j["void"] or group == "stock":
        return j
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
    if not j["proof"]:
        j["void"] = f"loop proof failed ({len(ws)} vertices decoded, depth words {sorted({f'{w:#x}' for w in ws})[:3]} not {want:#x})"
    elif j["L"] is None:
        j["void"] = "no timeline"
    return j


def collect(k):
    d = {}
    for n in k.names():
        p = parse(n)
        if p is None:
            continue
        g, N, V = p
        d[n] = vjob(k, n, N, V, g)
    return d


def control_states(d):
    """{control: True / False / None} and why, from the kept jobs: the bridge to E807."""
    out, why = {}, {}

    def rule(name, bit7, lrange):
        j = d.get(name)
        if j is None or j["void"]:
            out[name], why[name] = None, "not run or void" + (f" ({j['void']})" if j else "")
            return
        lo, hi = lrange
        ok = (j["bit7"] == bit7) and not j["bit6"] and lo <= j["L"] <= hi
        out[name] = ok
        why[name] = f"bit 7 {'set' if j['bit7'] else 'clear'}, bit 6 {'set' if j['bit6'] else 'clear'}, L {j['L']:.1f} us (want bit 7 {'set' if bit7 else 'clear'}, L {lo:g}..{hi:g})"
    rule("v-ctl0", False, (0.0, 30.0))
    rule("v-n1", False, (0.0, 30.0))
    rule("v-i880", False, (95.0, 112.0))
    rule("v-i1760", True, (160.0, 260.0))
    return out, why


def score_v(k, preds):
    d = collect(k)
    out = ["Q082 TA side (q4-v): bit 7 against the TA-clock rule; L = the longest run of CLKGATESTATUS 0x000ccff8 (us)", ""]
    rows = []
    for n in sorted(d, key=lambda n: (parse(n)[0], parse(n)[1])):
        j = d[n]
        if j["void"]:
            rows.append((n, "-", "-", "-", "-", "VOID: " + j["void"][:60]))
            continue
        rule = T.bit7_rule(j["L"])
        rows.append((n, j["N"] or "-", f"{j['L']:.1f}", "S" if j["bit7"] else "c", "-" if j["d7"] is None else f"{j['d7']:.1f}", rule))
    out.append(L.table(rows, ["job", "N", "L us", "bit7", "t7 - run start us", "rule says"]))
    out.append("")
    cstate, cwhy = control_states(d)
    for c in CONTROLS:
        out.append(f"control {c}: {SK._state(cstate.get(c))}: {cwhy.get(c, 'not run')}")
    g = SK.gate(cstate)
    # ------------------------------------------------------------------ ladders (FIT points apart)
    held, fit, latch = [], [], []
    ladder_lines = []
    for key in ("b12v", "b2v", "v24"):
        js = sorted((j for j in d.values() if j["group"] == key), key=lambda j: j["N"])
        n_by = {"clear": 0, "edge": 0, "set": 0}
        for j in js:
            is_fit = k.case(j["name"]).get("set") == "control"
            if j["void"]:
                (fit if is_fit else held).append(None)
                continue
            rule = T.bit7_rule(j["L"])
            n_by[rule] += 1
            v = T.verdict(rule, j["bit7"])
            (fit if is_fit else held).append(v)
            if j["bit7"] and not is_fit and j["d7"] is not None:
                latch.append(T.LATCH7[0] <= j["d7"] <= T.LATCH7[1])
            if j["bit7"] and is_fit and j["d7"] is not None:
                latch.append(T.LATCH7[0] <= j["d7"] <= T.LATCH7[1])
        ladder_lines.append(f"ladder {key}: {len(js)} jobs, by the rule on their own L: {n_by['clear']} clear, {n_by['edge']} edge, {n_by['set']} set"
                            + ("" if n_by["clear"] and n_by["set"] else "  (NOT INFORMATIVE: no point on one side of the edge)"))
    out += [""] + ladder_lines
    held_g = [SK.gated(g, r) for r in held]
    t = SK.tally(held_g)
    tf = SK.tally(fit)
    tl = SK.tally(latch)
    out.append(f"FIT points (clear by the model; not gating): {tf}")
    out.append(f"HELD OUT ladder rows, bit 7 follows L (the edge band 122..136 us is not scored): {t}" + ("" if g.ok else "  [gate shut: " + "; ".join(g.problems) + "]"))
    out.append(f"latch time (bit 7 shows {T.LATCH7[0]:g}..{T.LATCH7[1]:g} us after the run began) in the set jobs: {tl}")
    # ------------------------------------------------------------------ the stock rows: H-STALL against H-PHASE
    stock = [j for j in d.values() if j["group"] == "stock"]
    stall = phase = voidn = 0
    srows = []
    for j in sorted(stock, key=lambda j: j["name"]):
        if j["void"] or j["L"] is None:
            voidn += 1
            srows.append(f"{j['name']}: VOID ({j['void'] or 'no timeline'})")
        elif j["L"] < STOCK_MIN_L:
            voidn += 1
            srows.append(f"{j['name']}: L {j['L']:.1f} us < {STOCK_MIN_L:g}: void for H-STALL / H-PHASE; bit 7 {'set' if j['bit7'] else 'clear'}")
        else:
            if j["bit7"]:
                phase += 1
            else:
                stall += 1
            srows.append(f"{j['name']}: L {j['L']:.1f} us, bit 7 {'set' if j['bit7'] else 'clear'}: " + ("H-PHASE" if j["bit7"] else "H-STALL"))
    out += [""] + srows
    if not g.ok:
        sv = "cannot tell (a control did not pass)"
    elif stall + phase == 0:
        sv = "cannot tell (no stock row with L >= 125 us)"
    elif stall and phase:
        sv = f"mixed ({stall} H-STALL, {phase} H-PHASE)"
    else:
        sv = f"{'H-STALL' if stall else 'H-PHASE'} in {stall + phase} of {len(stock)} rows (the others void)" if voidn else f"{'H-STALL' if stall else 'H-PHASE'} in {stall + phase} of {len(stock)} rows"
    out.append(f"stock rows: {sv}")
    head = SK.headline("bit 7 follows the TA clock run L (set iff L >= 129.5 us, edge 122..136)", cstate, held_g)
    out.append("SUMMARY: " + head + f"; FIT {tf}; latch window {tl}; stock: {sv}")
    return "\n".join(out), {"controls": cstate, "gate": g, "held": t, "fit": tf, "latch": tl, "stock": sv, "jobs": d}


def gate_text(k, preds):
    d = collect(k)
    cstate, cwhy = control_states(d)
    g = SK.gate(cstate)
    return g, [f"{c}: {SK._state(cstate.get(c))}: {cwhy.get(c, 'not run')}" for c in CONTROLS]
