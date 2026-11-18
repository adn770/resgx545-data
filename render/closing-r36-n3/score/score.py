#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r36-n3's scorer (closing29/kernel33/design.md §3, N3). Every verdict rule comes from
kit/scorekit.py, the kept files are read through kit/kitscore.py (byte copies of resgx545
b9098a41fc8d, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Stage own, per row (its results page NAME.own_res.json, its registers NAME.snap0.regs): V0-V3 are
TA3DCtl dwords 0-3 in the row's own snap0 (`ta3dctl 0xOO 0xV`, the kernel's regs file; a snap0
without them: cannot tell, never the frozen fallback the laptop hook uses). A prediction value is
a constant 0xV, `@runid` (dword 3, the run id the host wrote), `@Vi`, or `!X[,Y]` (none of them).

Controls per row (NAME:ctl): entry 0 ran this command (slot 1 = M1 and the run id, cmd 0, the
page kept) -- E0; entry 1 ran (slot 4 = M4 and the run id, state 2, echo = run id) -- E1;
the firmware's attributes unchanged (sa0-sa3 = V0-V3) -- SA; no douta landed off its attribute
(pa1, pa3 not V0 or V2) -- PA13.
  H-NONE  held when E0 passed and entry 1 left no trace (slot 4 dword 0 not M4, state not 2);
          FAILED when E1 passed; cannot tell otherwise. Gated on E0 alone (its reading is E1's absence).
  H-PA    held when pa0 = V0 and pa2 = V2, FAILED otherwise; gated on E0, E1, SA, PA13.
  H-SA    held when pa0 != V0 and pa2 != V2 (sa0, sa2 = V0, V2 is SA's), FAILED otherwise; same
          gate. A row with exactly one of pa0 = V0, pa2 = V2 fails both (a split landing).
Each headline is over the held-out rows (h1-h8), its gate over every kept row's controls; the fit
rows (e1, e2) are printed and scored apart. H-NONE can only be seen on the first row the stage
ran (a task that never reaches entry 1 never reports done: the runner stops the stage, rc 4, and
the driver ends the session before the scorer; score the kept directory by hand then), so its
rule reads every kept row, fit included.

RULE (N3 / Q128), frozen:
  N3 DECIDED-PA   H-PA held on at least 6 held-out rows, none FAILED, every control passed:
                  an emitted program's douta (the firmware's emitpds form, from an EDM task)
                  lands in the started task's primary attributes; fwsim/sgx-sim must model
                  emitted douta to pa (E1133's sa landing is refuted). Q128 NARROW.
  N3 NOT-PA       H-SA held likewise: the writes did not land in pa, and sa0/sa2 kept their
                  values; a positive sa landing is NOT shown (same values: design §4), the
                  distinct-value follow-up is a separate decision. Q128 NARROW.
  N3 NONE         H-NONE held on the first kept row (E0 passed): the image did not start entry 1
                  (U1 = U2 = 0, TRC 8 [infer]); the landing stays open. Q128 NARROW.
  N3 OPEN         anything else (a FAILED control, a split landing, too few rows): no claim.
Q128 is never retired here: its clauses are a client emitpds's fault page, the started program's
s0-s2 and the addend window, none of which this session measures."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

REQUIRED = {"own": (".txt", ".own_res.json", ".gate.json", ".snap0.regs", "cases.tsv",
                    "void.tsv", "readings.tsv"),
            "post": (".txt", "cases.tsv", "void.tsv", "readings.tsv")}
GATES = {}          # {stage: the earlier stage whose controls gate it}: none (own's stop ends)
M1, M4 = 0x5A5A3301, 0x5A5A3302
SLOT1, SLOT_PA, SLOT_SA, SLOT4 = 0x44, 0x48, 0x4C, 0x50
HYPS = ("H-PA", "H-SA", "H-NONE")
MIN_HELDOUT = 6


def state_word(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def producible(row):
    if row["tool"] == "owntask":
        return set()
    return {"diff"} if row["args"].split()[:1] in (["tri"], ["fill"]) else set()


def reading(text):
    for ln in text.splitlines():
        if ln.startswith("diff: "):
            return {"diff": ln.split()[1]}
    return {}


def snap_v(d, n):
    """{i: TA3DCtl dword i} of the row's snap0 (i = 0..3 present), or {}."""
    out = {}
    for m in re.finditer(r"^ta3dctl (0x[0-9a-f]{2}) (0x[0-9a-f]{8})$",
                         K.text(d, n + ".snap0.regs"), re.M):
        i = int(m.group(1), 16) // 4
        if i < 4:
            out[i] = int(m.group(2), 16)
    return out


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n, r in cases.items():
        K.text(d, n + ".txt")
        if stage == "own":
            K.own_res(d, n)
            K.text(d, n + ".snap0.regs")
            if r["class"] == "ok":
                K.text(d, n + ".gate.json")


def value_ok(spec, got, runid, v):
    """got (an int) against a frozen value: 0xV, @runid, @Vi or !A[,B]; None when a token's
    value is unknown."""
    neg = spec.startswith("!")
    toks = spec[1:].split(",") if neg else [spec]
    vals = []
    for t in toks:
        if t == "@runid":
            vals.append(runid)
        elif t.startswith("@V"):
            vals.append(v.get(int(t[2:])))
        else:
            vals.append(int(t, 16))
    if got is None or any(x is None for x in vals):
        return None
    return (got not in vals) if neg else (got == vals[0])


def own_row(d, n, preds, cases):
    """(controls {E0, E1, SA, PA13: state}, {hyp: state}, line) of one own row."""
    page = K.own_res(d, n)
    v = snap_v(d, n)
    q = preds.get(n, {})
    ran = n in cases
    if page is None or not ran:
        ctl = {"E0": None, "E1": None, "SA": None, "PA13": None}
        return ctl, {h: None for h in HYPS}, f"ROW {n}: no results page kept: cannot tell"
    runid = page[3]

    def chk(idx, model="CTL"):
        spec = q.get(f"res:0x{idx:x}", {}).get(model)
        return None if spec is None else value_ok(spec, page[idx], runid, v)

    def all_of(states):
        states = list(states)
        if any(s is False for s in states):
            return False
        return None if any(s is None for s in states) else True

    e0 = all_of([chk(SLOT1), chk(SLOT1 + 1), chk(1)])
    e1 = all_of([chk(SLOT4), chk(SLOT4 + 1), chk(2), chk(5)])
    sa = all_of(chk(SLOT_SA + i) for i in range(4))
    pa13 = all_of([chk(SLOT_PA + 1), chk(SLOT_PA + 3)])
    if e1 is False:          # entry 1 did not run: its slots carry no reading
        sa = pa13 = None
    ctl = {"E0": e0, "E1": e1, "SA": sa, "PA13": pa13}
    pa0, pa2 = page[SLOT_PA] == v.get(0), page[SLOT_PA + 2] == v.get(2)
    hyp = {"H-NONE": None, "H-PA": None, "H-SA": None}
    if e0 is True:
        # entry 1 alone writes slot 4 and state 2: neither written is H-NONE's reading
        hyp["H-NONE"] = (False if e1 is True else
                         True if page[SLOT4] != M4 and page[2] != 2 else None)
    if e1 is True and 0 in v and 2 in v:
        hyp["H-PA"] = pa0 and pa2
        hyp["H-SA"] = (not pa0) and (not pa2)
    sl = page[SLOT_PA:SLOT_PA + 4] + page[SLOT_SA:SLOT_SA + 4]
    line = (f"ROW {n}: run id {runid}; pa0-pa3 {' '.join('0x%08x' % x for x in sl[:4])}; "
            f"sa0-sa3 {' '.join('0x%08x' % x for x in sl[4:])}; V0-V3 "
            f"{' '.join('0x%08x' % v[i] if i in v else '?' for i in range(4))}; "
            + "; ".join(f"{k} {state_word(s)}" for k, s in ctl.items()) + "; "
            + "; ".join(f"{h} {'held' if s else 'FAILED' if s is False else 'cannot tell'}"
                        for h, s in hyp.items()))
    return ctl, hyp, line


def score_own(d):
    """(lines, per {hyp: {row: state}}, ctl {row:key: state}, sets {row: set})."""
    preds = K.predictions(KP, "own")
    cases = K.rows(d, "cases.tsv")
    tab = K.table(KP, "own")
    sets = {r["name"]: r["set"] for r in tab}
    lines, per, ctl = [], {h: {} for h in HYPS}, {}
    for r in tab:
        n = r["name"]
        if n not in cases and K.own_res(d, n) is None:
            continue                       # not run (the stage ended before it)
        c, h, ln = own_row(d, n, preds, cases)
        lines.append(ln)
        for k, s in c.items():
            ctl[f"{n}:{k}"] = s
        for k, s in h.items():
            per[k][n] = s
    for k, s in ctl.items():
        lines.append(f"CONTROL {k}: {state_word(s)}")
    return lines, per, ctl, sets


def headlines(per, ctl, sets):
    out = []
    for h in HYPS:
        if h == "H-NONE":
            c = {k: s for k, s in ctl.items() if k.endswith(":E0")}
            rows = list(per[h].values())
        else:
            c = dict(ctl)
            rows = [s for n, s in per[h].items() if sets.get(n) == "heldout"]
        out.append(f"SUMMARY: own: {h}: " + SK.headline(f"{h} on the held-out rows"
                                                       if h != "H-NONE" else
                                                       f"{h} on the kept rows", c, rows))
    return out


def rule_n3(per, ctl, sets):
    allc = SK.gate(ctl)
    h = {k: [s for n, s in per[k].items() if sets.get(n) == "heldout"] for k in ("H-PA", "H-SA")}
    out = []

    def decided(k):
        t = SK.tally(h[k])
        return allc.ok and t.failed == 0 and t.held >= MIN_HELDOUT

    first = next(iter(per["H-NONE"]), None)
    e0 = SK.gate({k: s for k, s in ctl.items() if k == f"{first}:E0"}) if first else None
    if decided("H-PA"):
        out.append("N3 RULE: DECIDED-PA: an emitted douta lands in the started task's pa "
                   f"({SK.tally(h['H-PA'])}); fwsim/sgx-sim: model emitted douta to pa")
    elif decided("H-SA"):
        out.append("N3 RULE: NOT-PA: the emitted douta did not land in pa, sa0/sa2 unchanged "
                   f"({SK.tally(h['H-SA'])}); a positive sa landing is not shown (same values)")
    elif first and e0.ok and per["H-NONE"][first] is True:
        out.append(f"N3 RULE: NONE: entry 1 never ran after the emit ({first}): the landing "
                   "stays open")
    else:
        why = "; ".join(allc.problems[:3]) + (f" (+{len(allc.problems) - 3})"
                                              if len(allc.problems) > 3 else "")
        why = why or "too few held-out rows decided, or a split landing"
        out.append(f"N3 RULE: OPEN: no claim ({why})")
    out.append("Q128 RULE: NARROW" + ("" if out[0].startswith("N3 RULE: OPEN") else
                                      " (the firmware's emitpds form from an EDM task, our "
                                      "image: " + out[0].split(": ")[1] + ")")
               + "; never RETIRE from this session")
    return out


def score_post(d):
    preds = K.predictions(KP, "post")
    cases = K.rows(d, "cases.tsv")
    controls, lines = {}, []
    for r in K.table(KP, "post"):
        n = r["name"]
        got = reading(K.text(d, n + ".txt")).get("diff") if n in cases and \
            cases[n]["class"] == "ok" else None
        want = preds.get(n, {}).get("diff", {})
        state = None if got is None or not want else got in want.values()
        controls[n] = state
        lines.append(f"CONTROL {n}: diff {got} (frozen {sorted(want.values())}): "
                     f"{state_word(state)}")
    g = SK.gate(controls)
    lines.append("SUMMARY: post: " + ("the stock firmware drew the triangle and the fill exactly "
                                      "after the disarm" if g.ok else
                                      "controls FAILED or cannot tell: " + "; ".join(g.problems)))
    return lines, controls


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        dep = GATES.get(argv[2])
        if dep is None:
            return 0
        print(f"gate {argv[2]}: {dep} has not run")
        return 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] == "own":
        lines, per, ctl, sets = score_own(argv[2])
        print("\n".join(lines + headlines(per, ctl, sets) + rule_n3(per, ctl, sets)))
        return 0
    if len(argv) >= 3 and argv[1] == "post":
        print("\n".join(score_post(argv[2])[0]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
