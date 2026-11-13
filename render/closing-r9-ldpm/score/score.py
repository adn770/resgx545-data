#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r9-ldpm's frozen scorer (r8-ldpm's, its post-run fix included, cut to this session's
stages). Every verdict rule comes from kit/scorekit.py, the kept files are read through
kit/kitscore.py (byte copies of resgx545 f32dfac, pinned in FROZEN.commits) and one job's output
through score/read.py (r8-ldpm's reader with gps_next).

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL and ROW lines, MODEL tallies, SUMMARY lines
  score.py gate STAGE ROOTS...         exit 0 when every control of a0 passed (m6b, w, f9b)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

A row is scored only when its job completed (kitscore.completed: rc 0, the rc 3 overflow of an
`expect:rc3-overflow` row, the rc 1 with its diff line of an `expectdiff` row) and its knob proof
holds (0x0624 read = the row's thr0); otherwise it is cannot tell. A control passes when every
value it is frozen with (CTL, and H-STEPMODEL's steps inside the bracket its job read) holds.

  a0   E935's six controls (r8-ldpm a0 on module B60AB0B4); the gate of every later stage
  m6b  the six E936 replicates are the controls (gps_next as E936 read it; no stop: one off gates
       every verdict of the stage); per held-out cell gps_next against H-NEXT1 (OD-2's frozen end
       after[b_6 + 1]), H-SPAN (A_6), H-NEXT2 (after[b_6 + 2]) and, at the A_6 cell, E936's class
       rivals; H-SPAN-AL (R7's calibration alignment, E936) tallied; the calibrations' steps and
       need (H-STEPMODEL); the dumped A_6 replicate is explore
  w    each calibration is a control of its own target only: its need is OD-1's held-out
       reading (H-REPLAY against HU1, tallied over the four calibrations whatever their state),
       and its steps (H-STEPMODEL) and need gate its cell; the cell's F9 count and run peaks,
       d = 7/4, d = 1, E625 and the abort's global page count (H-ABORT, E935's rule on the
       replay's steps)
  f9b  the calibrations are controls (need, steps; a need off stopped the stage on the laptop);
       F9 against H-NORAISE at the band 4 cells, E854's d = 7/4, d = 1, E625, H-ABORT

REQUIRED: the files each stage reads; read_files(STAGE, DIR) reads exactly those; producible(row)
is the set of reading keys the row's job can produce (score/read.py's words: the freeze refuses a
control that reads anything else)."""
import collections
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "gen"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402
import read as R  # noqa: E402
import plan as PL  # noqa: E402

STAGES = PL.STAGES
BASE = (".txt", "cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {s: BASE for s in STAGES}
GATES = {s: "a0" for s in STAGES if s != "a0"}
MAIN = {"m6b": ("H-NEXT1", "H-SPAN", "H-NEXT2", "H-BIG6", "H-ANY6", "H-6LATE", "H-STEPMODEL"),
        "w": ("H-REPLAY", "HU1", "F9", "d=7/4", "d=1", "E625", "H-ABORT"),
        "f9b": ("F9", "H-NORAISE", "d=7/4", "d=1", "E625", "H-ABORT")}
PASS_MODELS = ("CTL", "H-STEPMODEL")


def producible(row):
    """The reading keys of the row's job: every job reads knob, nparts, gmax and runpeaks; a probe
    job its steps below min(thr0, U) and mono; a completed job (thr0 >= U) its need; one with a
    partial render gps_abort, gps_left and gps_next."""
    keys = {"knob", "nparts", "gmax", "runpeaks"}
    args = row["args"]
    thr0 = PL.thr0_of(row)
    w, h = PL.target(dict(args=args))
    if " probe " in f" {args} ":
        S, A, U, _ = PL.model(w, h)
        keys |= {f"s{k}" for k, v in S.items() if v < min(thr0, U)} | {"mono"}
    else:
        U = 287                                  # a0's g-qf: the 4096x4096 default triangle (E832)
    keys |= {"need"} if thr0 >= U else {"gps_abort", "gps_left", "gps_next"}
    return keys


# ---- reading ------------------------------------------------------------------------------------
def thr0_of(r):
    return PL.thr0_of(r)


def readings(stage, d):
    cases = K.rows(d, "cases.tsv")
    out = {}
    for r in K.table(KP, stage):
        n = r["name"]
        c = cases.get(n)
        if c is None or not K.completed(c):
            out[n] = None
            continue
        rd = R.reading(K.text(d, n + ".txt"))
        if rd.get("void") or rd.get("knob") != thr0_of(r):
            out[n] = None
            continue
        out[n] = rd
    return out


def value(rd, q):
    if rd is None:
        return None
    if q.startswith("s") and q[1:].isdigit():
        return rd["iv"].get(int(q[1:]))
    if q == "runpeaks":
        return ",".join(f"0x{x:x}" for x in rd["runpeaks"]) if rd["runpeaks"] else None
    if q == "overflow":
        return str(int(rd["nparts"] >= 1))
    v = rd.get(q)
    if v is None:
        return None
    if isinstance(v, bool):
        return str(int(v))
    return v


def holds(got, want):
    if got is None:
        return None
    if isinstance(got, tuple):                      # a step bracket (a, max(a, b - 1))
        return got[0] <= int(want, 16) <= got[1]
    if isinstance(got, int):
        return got == int(want, 0)
    return str(got) == want


def shown(got):
    return ("[0x%x, 0x%x]" % got if isinstance(got, tuple) else
            f"0x{got:x}" if isinstance(got, int) else got)


# ---- controls -----------------------------------------------------------------------------------
def control_states(rds, preds, rows):
    out, lines = {}, []
    for r in rows:
        if r["set"] != "control":
            continue
        n, rd = r["name"], rds[r["name"]]
        st, why = True, []
        for q, by in preds.get(n, {}).items():
            for mdl, v in by.items():
                if mdl not in PASS_MODELS:
                    continue
                h = holds(value(rd, q), v)
                if h is not True:
                    why.append(f"{q} {shown(value(rd, q))} (frozen {v})")
                    st = None if h is None and st is not False else False if h is False else st
        if rd is None:
            st = None
        out[n] = st
        lines.append(f"CONTROL {n}: {'PASS' if st else 'FAILED' if st is False else 'cannot tell'}"
                     + (": " + "; ".join(why) if why else ""))
    return out, lines


def model_rows(rds, preds, rows, sets=("heldout", "explore"), only=None):
    """{model: [(row, state, detail)]} over the predicted quantities of the rows in `sets`."""
    res = collections.defaultdict(list)
    for r in rows:
        n = r["name"]
        if r["set"] not in sets:
            continue
        for q, by in preds.get(n, {}).items():
            for mdl, v in by.items():
                if mdl == "CTL" or (only and mdl not in only):
                    continue
                got = value(rds[n], q)
                st = holds(got, v)
                if q == "runpeaks" and got and got.split(",")[0] == "0x0":
                    st = None                        # E916: a first run no sample fell in
                res[mdl].append((r, st, f"{q} {shown(got)} (frozen {v})"))
    return res


def m6b_aligned(rds, rows):
    """H-SPAN-AL (tally): E936's alignment, the run's cell thr0 - (S_6 read - S_6 model) when the
    calibration's S_6 bracket does not hold the model's; no S_6 read voids the target."""
    res = collections.defaultdict(list)
    for m in PL.T["m6b"]:
        w, h = m["w"], m["h"]
        S, A, U, _ = PL.model(w, h)
        cal = rds.get(f"m6b-cal-{PL.tag(w, h)}")
        iv = cal["iv"].get(6) if cal else None
        shift = None if iv is None else 0 if iv[0] <= S[6] <= iv[1] else iv[1] - S[6]
        for r in rows:
            if r["set"] != "heldout" or not r["name"].startswith(f"m6b-{PL.tag(w, h)}-"):
                continue
            rd = rds.get(r["name"])
            got = rd["gps_next"] if rd else None
            if shift is None:
                res["H-SPAN-AL"].append((r, None, f"gps_next {got}: no calibration S_6"))
                continue
            v = PL.left_by(thr0_of(r) - shift, S, A[6])
            st = None if v is None or got is None else got == v
            res["H-SPAN-AL"].append((r, st, f"gps_next {got} (model cell 0x{thr0_of(r) - shift:x}, frozen {v})"))
    return res


def verdicts(stage, d):
    rows = K.table(KP, stage)
    preds = K.predictions(KP, stage)
    rds = readings(stage, d)
    controls, lines = control_states(rds, preds, rows)
    tallies = {}
    gated = {}                                         # row -> the gate that decides it
    if stage == "w":
        res = model_rows(rds, preds, rows)
        need = model_rows(rds, preds, rows, sets=("control",), only=("H-REPLAY", "HU1"))
        for r in rows:
            if r["set"] == "heldout":
                cal = f"w-cal-{r['name'].split('-')[1]}"
                gated[r["name"]] = SK.gate({cal: controls.get(cal)})
        res.update(need)
    else:
        res = model_rows(rds, preds, rows)
        if stage == "m6b":
            res.update(m6b_aligned(rds, rows))
            res.update(model_rows(rds, preds, rows, sets=("heldout",), only=("H-STEPMODEL",)))
    g_all = SK.gate(controls) if controls else None
    for mdl, items in sorted(res.items()):
        states, expl = [], []
        for r, st, det in items:
            if r["set"] == "control":
                g = None                                # w's needs: the reading is the verdict
            elif stage == "w":
                g = gated.get(r["name"])
            else:
                g = g_all
            if g is not None and not g.ok:
                st = None
            lines.append(f"ROW {r['name']} [{mdl}, {r.get('set')}]: "
                         f"{'held' if st else 'FAILED' if st is False else 'cannot tell'}: {det}")
            (expl if r.get("set") == "explore" else states).append(st)
        tallies[mdl] = (states, expl)
    return controls, lines, tallies


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        dep = GATES.get(argv[2])
        if dep is None:
            return 0
        for root in argv[3:]:
            d = os.path.join(root, dep)
            if os.path.isdir(d):
                g = SK.gate(verdicts(dep, d)[0])
                print(f"gate {argv[2]} on {dep}: {'open' if g.ok else '; '.join(g.problems)}")
                return 0 if g.ok else 1
        print(f"gate {argv[2]}: {dep} has not run")
        return 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        st = argv[1]
        controls, lines, tallies = verdicts(st, argv[2])
        print("\n".join(lines))
        for mdl, (held, expl) in tallies.items():
            print(f"MODEL {mdl}: {SK.tally(held)}" + (f"; explore {SK.tally(expl)}" if expl else ""))
        if st == "a0":
            print("SUMMARY: a0: " + SK.headline("the premise held (E935's a0 controls repeat on B60AB0B4)",
                                                controls, [True] if controls else []))
        for mdl in MAIN.get(st, ()):
            held = tallies.get(mdl, ([], []))[0]
            ctls = controls
            if st == "w":
                ctls = {"a0 (the gate score.py gate opened)": True} if mdl in ("H-REPLAY", "HU1") else controls
            print(f"SUMMARY: {st}: {mdl}: " + SK.headline(
                f"{mdl} holds", ctls or {"a0 (the gate score.py gate opened)": True}, held))
        return 0
    print(__doc__)
    return 2


def read_files(stage, d):
    """Exactly the files score() reads in the kept directory."""
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.text(d, "readings.tsv")
    for n in cases:
        K.text(d, n + ".txt")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
