# SPDX-License-Identifier: MIT
"""Scorer of q4-f (Q082 pixel side, the load in a fill).  Written before the run; frozen with the predictions.

A job: the post-job STATUS2 bit 6 (clear / set), the loop proof o0 = MARK on 2048 of 2048 (a failed proof voids the job), the burst B and
the time of the latch t6 (recorded; d6 has no prediction).  Controls (the bridge to E804 / E805 on the rgn4 module; each gates every
held-out row): f-rel-b8-16 (clear), f-rel-b8-53 (clear), f-rel-b8-56 (set), f-rel-b8-136 (set, t6 120..340 us), f-ld8-70 (clear).
Where sgx-pipe's rule on a tile's time (r4tl.bit6_rule: clear below 118 us, set above 132 us, edge between, no load) speaks, a bridge row
that contradicts it FAILS; at the edge (53 and 56) the control is E804's measured bracket, as the table says.
Held-out rows against the three readings of a load, frozen in score/r4const.py F_HYP (c clear, S set, either not scored):
H-YIELD (a wait restarts the timer), H-LOADOFF (a waiting program never latches), H-SUM (the busy time of the tile is summed).
A hypothesis is REFUTED by one row it contradicts, consistent with every decided row it was not, cannot tell with no decided row; a void
job is `cannot tell`.  A shut gate makes every row cannot tell.  Several hypotheses surviving, or none, is stated as it is (the table
separates them on the rows run; a hypothesis that predicts `either` on every row it shares cannot be told from another by it).
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import re  # noqa: E402

import r4const as C  # noqa: E402
import r4lib as L  # noqa: E402
import r4loops as LP  # noqa: E402
import r4tl as T  # noqa: E402
import scorekit as SK  # noqa: E402
from r4job import job  # noqa: E402

FILL = 2048
CONTROLS = {"f-rel-b8-16": (16, False), "f-rel-b8-53": (53, False), "f-rel-b8-56": (56, True), "f-rel-b8-136": (136, True), "f-ld8-70": (70, False)}
LD0 = re.compile(r"f-ld0-k(\d+)$")
LDO = re.compile(r"f-ldo-k(\d+)-m(\d+)$")


def mark_of(name):
    if name in CONTROLS:
        return LP.mark(CONTROLS[name][0])
    m = LD0.match(name)
    if m:
        return LP.load_mark(int(m[1]))
    m = LDO.match(name)
    if m:
        return LP.load_mark(int(m[1]), int(m[2]))
    return None


def fjob(k, name):
    mk = mark_of(name)
    j = job(k, name, mk, FILL)
    if not j["void"] and j["proof"] is False:
        j["void"] = "loop proof failed (o0 is not the mark on 2048 of 2048)"
    return j


def control_states(k):
    out, why = {}, {}
    for name, (n, want) in CONTROLS.items():
        j = fjob(k, name)
        if j["void"]:
            out[name], why[name] = None, "void: " + j["void"]
            continue
        ok = j["bit6"] == want and not j["bit7"]
        note = ""
        if n in (16, 136) and j["tau"] is not None:                       # the rule speaks (no load, outside its edge): a contradiction fails
            rule = T.bit6_rule(j["tau"])
            if rule != T.EDGE and (rule == T.SET) != j["bit6"]:
                ok = False
            note = f"; tile time {j['tau']:.1f} us: rule {rule}"
        if n == 136 and j["t6"] is not None and not (C.T6_LO <= j["t6"] <= C.T6_HI):
            ok = False
            note += f"; t6 {j['t6']:.0f} us outside {C.T6_LO:g}..{C.T6_HI:g}"
        out[name] = ok
        why[name] = f"bit 6 {'set' if j['bit6'] else 'clear'} (want {'set' if want else 'clear'}), B {j['B'] if j['B'] is None else round(j['B'])} us" + note
    return out, why


def held_rows(k):
    """[(name, kind, index)] of the held-out jobs in table order."""
    rows = []
    for n in k.names():
        m = LD0.match(n)
        if m and int(m[1]) in C.F_LD0:
            rows.append((n, "ld0", C.F_LD0.index(int(m[1]))))
        m = LDO.match(n)
        if m and (int(m[1]), int(m[2])) in C.F_LDO:
            rows.append((n, "ldo", C.F_LDO.index((int(m[1]), int(m[2])))))
    return rows


def score_f(k, preds):
    cstate, cwhy = control_states(k)
    g = SK.gate(cstate)
    out = ["Q082 pixel side (q4-f): what a load does to bit 6 of a fill (H-YIELD, H-LOADOFF, H-SUM)", ""]
    for c in CONTROLS:
        out.append(f"control {c}: {SK._state(cstate.get(c))}: {cwhy.get(c, 'not run')}")
    rows, per = [], {h: [] for h in C.F_HYP}
    for name, kind, i in held_rows(k):
        j = fjob(k, name)
        if j["void"]:
            rows.append((name, "-", "-", "-", "VOID: " + j["void"][:50]))
            for h in per:
                per[h].append(None)
            continue
        rows.append((name, "S" if j["bit6"] else "c", f"{j['B']:.0f}" if j["B"] is not None else "-", "-" if j["t6"] is None else f"{j['t6']:.0f}",
                     "set" if j["bit6"] else "clear"))
        for h, tab in C.F_HYP.items():
            w = tab[kind][i]
            per[h].append(None if w == "either" else (w == "S") == j["bit6"])
    out += ["", L.table(rows, ["job", "bit6", "B us", "t6 us (d6 from the burst start)", "read"]), ""]
    verdicts = {}
    for h, rs in per.items():
        gated = [SK.gated(g, r) for r in rs]
        t = SK.tally(gated)
        verdicts[h] = ("cannot tell" if not g.ok else "REFUTED" if t.failed else "consistent" if t.decided else "cannot tell", t)
        out.append(f"{h}: {verdicts[h][0]} ({t})")
    live = [h for h, (v, t) in verdicts.items() if v == "consistent"]
    dead = [h for h, (v, t) in verdicts.items() if v == "REFUTED"]
    if not g.ok:
        what = "cannot tell (bridge controls: " + "; ".join(g.problems) + ")"
    elif len(live) == 1:
        what = f"{live[0]} alone is consistent ({', '.join(dead) or 'no other'} refuted)"
    elif not live and dead:
        what = "every reading refuted (" + ", ".join(dead) + "): a load does something none of the three says"
    else:
        what = f"consistent: {live or 'none'}; refuted: {dead or 'none'}"
    out.append("SUMMARY: q4-f " + what)
    return "\n".join(out), {"controls": cstate, "gate": g, "verdicts": {h: v for h, (v, t) in verdicts.items()}}


def gate_text(k, preds):
    cstate, cwhy = control_states(k)
    return SK.gate(cstate), [f"{c}: {SK._state(cstate.get(c))}: {cwhy.get(c, 'not run')}" for c in CONTROLS]
