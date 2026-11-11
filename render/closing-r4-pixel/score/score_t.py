# SPDX-License-Identifier: MIT
"""Scorer of q4-t (Q082 pixel side, triangles: H-SEG, H-N, E806-DISC and the first-piece reading of the latch time).  Written before the
run; frozen with the predictions.

A job: bit 6 after the job, the loop proof o0 = MARK on W x H of W x H (full-target triangle; a failed proof voids the job), the burst and
t6 (us from the burst start).  Gate (every held-out row depends on it): the fill bridge t4-fill-n53 (clear) and t4-fill-n56 (set) (E804) and
the five stock green triangles (bit 6 clear, o0 green on W x H of W x H).  Per size, the loop at N = 1 (t4-ctl-n1-WxH) must carry the MARK
on W x H of W x H and leave bit 6 clear: a size that fails it is void for its rows (the others stand), as round 3's q-t.
Held-out bit rows against the frozen tables of H-SEG, H-N and E806-DISC (score/r4const.py t_pred; either = not scored): a hypothesis is
REFUTED by one row it contradicts.  The t6 rows (64x32 and 8x8 at 150, 180, 250, 330): set, and t6 = 250 + 0.43 N us (N <= 290), 250 us
beyond, +- 15 us; a row that did not set is void for t6.  The first-piece reading is tallied apart: if it fails the bit rule can still hold.
The default (partial) 64x64 triangle rows are exploratory and print their reading with no verdict.  A void job is `cannot tell`.
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

GREEN = 0xff00ff00
HYPS = ("H-SEG", "H-N", "E806-DISC")
SIZED = re.compile(r"t4-(\d+)x(\d+)-n(\w+)$")
GREENR = re.compile(r"t4-ctl-green-(\d+)x(\d+)$")
N1R = re.compile(r"t4-ctl-n1-(\d+)x(\d+)$")
PAR = re.compile(r"t4-par-64x64-n(\d+)$")


def tjob(k, name, w, h, n):
    """n None: the green control (o0 green); n 0: a fill; n > 0: MARK on W x H."""
    j = job(k, name, None if n is None else LP.mark(n), w * h)
    if not j["void"] and n is None:
        o = j["o0"]
        j["proof"] = bool(o and o[0] == "same" and o[1] == GREEN and o[2] == w * h == o[3])
    if not j["void"] and j["proof"] is False:
        j["void"] = f"proof failed (o0 is not {'green' if n is None else 'the mark'} on {w * h} of {w * h})"
    return j


def control_states(k):
    out, why = {}, {}
    for n, want in (("t4-fill-n53", False), ("t4-fill-n56", True)):
        j = job(k, n, LP.mark(int(n[-2:])), 2048)
        if not j["void"] and j["proof"] is False:
            j["void"] = "loop proof failed"
        if j["void"]:
            out[n], why[n] = None, "void: " + j["void"]
        else:
            out[n] = j["bit6"] == want
            why[n] = f"bit 6 {'set' if j['bit6'] else 'clear'} (want {'set' if want else 'clear'})"
    for w, h in C.T_CTL_SIZES:
        n = f"t4-ctl-green-{w}x{h}"
        j = tjob(k, n, w, h, None)
        if j["void"]:
            out[n], why[n] = None, "void: " + j["void"]
        else:
            out[n] = not j["bit6"] and not j["bit7"]
            why[n] = f"bit 6 {'set' if j['bit6'] else 'clear'}, green on {w * h}"
    return out, why


def usable_sizes(k):
    """{(w, h): None or the reason} from the N = 1 control of each size."""
    r = {}
    for w, h in C.T_CTL_SIZES:
        j = tjob(k, f"t4-ctl-n1-{w}x{h}", w, h, 1)
        r[(w, h)] = ("void: " + j["void"]) if j["void"] else ("bit 6 set at N = 1" if j["bit6"] else None)
    return r


def score_t(k, preds):
    cstate, cwhy = control_states(k)
    g = SK.gate(cstate)
    ok_size = usable_sizes(k)
    out = ["Q082 pixel side (q4-t): bit 6 in fully covered triangles, H-SEG / H-N / E806-DISC, and the time of the latch", ""]
    for c in cstate:
        out.append(f"control {c}: {SK._state(cstate[c])}: {cwhy[c]}")
    for s, why in ok_size.items():
        out.append(f"size {s[0]}x{s[1]} (N = 1 control): " + ("usable" if why is None else "VOID for its rows: " + why))
    per = {h: [] for h in HYPS}
    t6rows, rows, par = [], [], []
    for n in k.names():
        m = SIZED.match(n)
        if m:
            w, h, tag = int(m[1]), int(m[2]), m[3]
            nn = int(tag.rstrip("b"))
            j = tjob(k, n, w, h, nn)
            if ok_size.get((w, h)) is not None:
                j["void"] = j["void"] or "size void: " + str(ok_size[(w, h)])
            if j["void"]:
                rows.append((n, nn, "-", "-", "-", "VOID: " + j["void"][:48]))
                for hyp in HYPS:
                    per[hyp].append(None)
                if (w, h) in C.T_T6_SIZES and nn in C.T_T6_N:
                    t6rows.append((n, None))
                continue
            rows.append((n, nn, "S" if j["bit6"] else "c", "-" if j["B"] is None else f"{j['B']:.0f}", "-" if j["t6"] is None else f"{j['t6']:.0f}", ""))
            if (w, h) in C.T_T6_SIZES and nn in C.T_T6_N:
                for hyp in ("H-SEG", "H-N"):
                    per[hyp].append(j["bit6"])                # frozen: set at every size at these N
                per["E806-DISC"].append(j["bit6"])
                if j["bit6"] and j["t6"] is not None:
                    t6rows.append((n, abs(j["t6"] - C.t6_pred(nn)) <= C.T6_TOL))
                else:
                    t6rows.append((n, None))
            else:
                for hyp in HYPS:
                    want = C.t_pred(hyp, (w, h), nn)
                    per[hyp].append(None if want == "either" else (want == "set") == j["bit6"])
            continue
        m = PAR.match(n)
        if m:
            j = job(k, n)
            par.append(f"{n}: " + ("VOID: " + j["void"] if j["void"] else f"bit 6 {'set' if j['bit6'] else 'clear'}, B {j['B'] if j['B'] is None else round(j['B'])} us, t6 {j['t6']}"))
    out += ["", L.table(rows, ["job", "N", "bit6", "B us", "t6 us", "note"]), ""]
    verdicts = {}
    for hyp, rs in per.items():
        t = SK.tally([SK.gated(g, r) for r in rs])
        verdicts[hyp] = ("cannot tell" if not g.ok else "REFUTED" if t.failed else "consistent" if t.decided else "cannot tell", t)
        out.append(f"{hyp}: {verdicts[hyp][0]} ({t})")
    t6t = SK.tally([SK.gated(g, v) for n, v in t6rows])
    out.append(f"first-piece reading of the latch time (t6 = 250 + 0.43 N to N = 290, then 250 us, +- {C.T6_TOL:g}): {t6t}")
    out += par
    live = [h for h, (v, t) in verdicts.items() if v == "consistent"]
    dead = [h for h, (v, t) in verdicts.items() if v == "REFUTED"]
    if not g.ok:
        what = "cannot tell (gate: " + "; ".join(g.problems) + ")"
    else:
        what = f"consistent {live or 'none'}, refuted {dead or 'none'}"
    out.append("SUMMARY: q4-t " + what + f"; latch time {t6t}")
    return "\n".join(out), {"controls": cstate, "gate": g, "verdicts": {h: v for h, (v, t) in verdicts.items()}, "t6": t6t, "sizes": ok_size}


def gate_text(k, preds):
    cstate, cwhy = control_states(k)
    return SK.gate(cstate), [f"{c}: {SK._state(cstate[c])}: {cwhy[c]}" for c in cstate]
