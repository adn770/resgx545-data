#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score_r7.py: the frozen scorer of R7-dpm.

    score_r7.py STAGE DIR [--ctl DIR_A0] [--out OUTDIR]    score one stage's kept directory (refuses unless its set's freeze verifies)
    score_r7.py replay-r6 R6OUT                            R6-dpm's kept attempt (closing6/r6-dpm/out/a2) read through THIS scorer's
                                                           gate with R6's tables (the plan's G8): the gate stops at a0-cal-2048f's grow
                                                           (NO READING), and without that one control every ungated table of
                                                           postrun/ungated.out comes back as a verdict

Every job is read by run/r7read.py (the runner's own reader, one file-name function: kept_name) and checked for its SCENE from the data,
not from its arguments: a 1500-vertex job must reach a second global page and show every first-run step within 1 page of its target's
reference (this session's calibration of the target, else the frozen model's steps; at 2048x4096 the KEPT calibrations' steps, which the
model misses at S3; a --vtx-coords job: its own calibration only); a one-triangle job must stay at 1 global page.  A job that fails the
scene check, or whose own 0x0624 is not P - 0x22 (the knob proof), is FAILED if it is a control and cannot tell otherwise.  A skipped
job: cannot tell (never a pass); a missing file of a job the runner says it ran: NODATA.

Round 7's gate (plan section 6; R7-6): a control's state is held, FAILED or NO READING (scorekit's NODATA): a control whose reading is
absent is never "cannot tell" and the premise stage prints it as a STOP (scorekit.premise_stops) instead of a headline; a headline is gated
only by its own stage's controls and by s-a0's rows of the same scene class (the 1500-vertex rows gate s-m, g-qf gates s-b).
Verdict rules: tools/closing/scorekit.py (copied byte for byte as score/scorekit.py).  REQUIRED names every kept file a stage's scoring
reads (sessioncheck.py kept).
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import pathlib
import re
import subprocess
import sys

sys.dont_write_bytecode = True
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "run"), str(KP / "gen"), str(KP / "score")]
import r7read as R  # noqa: E402
import r7plan as P  # noqa: E402
import scorekit as SK  # noqa: E402

# the kept files each stage's scoring reads: ".suffix" for every row that ran, a name once (sessioncheck.py kept, the runner's check)
REQUIRED = {
    "s-a0": ("cases.tsv", ".txt", ".after.buf09.bin"),
    "s-m": ("cases.tsv", ".txt", ".after.buf09.bin"),
    "s-b": ("cases.tsv", ".txt", ".after.buf09.bin", "b-cal-s22.tri.tadata.bin"),
    "s-v": ("cases.tsv", ".txt", ".after.buf09.bin"),
    "s-k": ("cases.tsv", ".txt", ".after.buf09.bin", ".page.json"),
}
NO_READING = "NODATA"           # scorekit's word for a control with no reading (printed NO READING)


# ------------------------------------------------------------------------------------------------ kept files
def cases(d):
    p = pathlib.Path(d) / "cases.tsv"
    if not p.exists():
        return {}
    return {r["name"]: r for r in csv.DictReader(open(p), delimiter="\t")}


def kept(d, name, kind):
    p = pathlib.Path(d) / R.kept_name(name, kind)
    return gzip.open(p).read() if p.exists() else None


def target_of(args):
    m = re.search(r"--width (\d+) --height (\d+)", args or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def coords_of(args):
    m = re.search(r"--vtx-coords (\d+)", args or "")
    return int(m.group(1)) if m else None


# ------------------------------------------------------------------------------------------------ scene check and one job
def ref_steps(wh, dirs, coords=None):
    """The steps a scene check compares with: this session's calibration of the same target and scene (a cal: row of a kept directory,
    whole and monotone), else the kept calibrations' at 2048x4096, else the frozen model's (none for a --vtx-coords scene)."""
    for d in dirs:
        for n, c in cases(d).items():
            if "cal:" in c.get("knobs", "") and target_of(c.get("args")) == wh and coords_of(c.get("args")) == coords and c.get("class") == "ok":
                out = kept(d, n, "out")
                if out:
                    r = R.reading(out.decode(errors="replace"))
                    if r.get("mono"):
                        return r["S"], f"calibration {n}"
    if coords:
        return {}, "no calibration of the scene"
    if wh == (2048, 4096):
        return P.KEPT_2X4, "the kept 2048x4096 calibrations"
    return (P.MODEL[wh][0] if wh in P.MODEL else {}), "the frozen model"


def scene_check(r, args, dirs):
    if r.get("void"):
        return r["void"]
    if (args or "").startswith("probe") and "--vertices 1500" in args:
        if (r.get("gmax") or 0) < 2:
            return f"a 1500-vertex job that never reached a second global page (gmax {r.get('gmax')}): not the 1500-vertex scene"
        ref, src = ref_steps(target_of(args), dirs, coords_of(args))
        for k, s in r["S"].items():
            if k in ref and abs(s - ref[k]) > 1:
                return f"step {k} at 0x{s:x}, {src} 0x{ref[k]:x}: not this target's scene"
        return None
    if (args or "").startswith("tri"):
        if r.get("gmax") not in (None, 1):
            return f"a one-triangle job with {r['gmax']} global pages: not the one-triangle scene"
    return None


def walk_reading(d, name, args):
    """H-WALK64 (and row order) on the kept tri dump: 'exact' or 'placed/total'; None without the dump."""
    p = pathlib.Path(d) / R.kept_name(name, "ttadata")
    if not p.exists():
        return None, None
    import r7model as M
    w, h = target_of(args)
    pre = str(p)[: -len("tadata.bin.gz")]
    regs = M.O.regions_of(pre, w, h)
    out = []
    for key in (M.WALK64_DUMP, M.G1.ORDERS["row"]):
        ok, tot, _, _ = M.O.place(regs, key)
        out.append("exact" if ok == tot and tot else f"{ok}/{tot}")
    return out[0], out[1]


def read_job(d, name, c, dirs):
    """(reading or None, why) of one kept job: skipped, NODATA, void, knob proof, scene check."""
    if c.get("class") == "skipped":
        return None, "skipped: " + c.get("note", "")
    if c.get("class") not in ("ok",):
        return None, f"class {c.get('class')}"
    out = kept(d, name, "out")
    if out is None:
        return None, "NODATA: no kept output"
    text = out.decode(errors="replace")
    r = R.reading(text, kept(d, name, "buf09"))
    if r.get("void"):
        return None, "NODATA: " + r["void"]
    try:
        Pv = int(c["P"], 16)
    except (KeyError, ValueError):
        Pv = None
    r["P"] = Pv
    r["repicked"] = (c.get("note") or "").startswith("repicked")
    sc = scene_check(r, c.get("args"), dirs)
    if sc:
        r["scene_fail"] = sc
    elif Pv is not None and r.get("knob") is not None and r["knob"] != Pv - P.D_OFF:
        r["scene_fail"] = f"knob did not land: 0x0624 0x{r['knob']:x}, P - 0x22 0x{Pv - P.D_OFF:x}"
    pg = kept(d, name, "page")
    if pg is not None:
        try:
            r.update({k: v for k, v in R.ring_reading(json.loads(pg)["page"], text).items()})
        except (ValueError, KeyError):
            pass
    if "tdump" in c.get("knobs", ""):
        r["walk64"], r["walkrow"] = walk_reading(d, name, c.get("args"))
    return r, ""


# ------------------------------------------------------------------------------------------------ predictions against readings
def observed(r, q):
    if r is None:
        return None
    if q == "cls":
        return None if r["cls"] == "V" else r["cls"]
    if q in ("grow", "mono", "ring_counts", "pass_tl"):
        return None if r.get(q) is None else str(int(r[q]))
    if q == "knob":
        return None if r.get("knob") is None else f"0x{r['knob']:x}"
    if q.startswith("S") and q[1:].isdigit():
        return r["iv"].get(int(q[1:]))             # the bracket (a, max(a, b - 1)) or None
    if q in ("dec_sa8_380", "next_sa8_380"):
        return None if r.get(q) is None else f"0x{r[q]:x}"
    if q == "runpeaks":
        return " ".join(f"0x{x:x}" for x in r.get("runpeaks", [])) or None
    if q == "need":
        return None if r.get("nparts") != 0 or r.get("need") is None else str(r["need"])
    v = r.get(q)
    return None if v is None else str(v)


def same(pred, obs):
    if obs is None:
        return None
    if isinstance(obs, tuple):                     # H-IV: a frozen step holds when it lies in the job's bracket
        return obs[0] <= int(pred, 0) <= obs[1]
    if pred.startswith(">="):
        return int(obs, 0) >= int(pred[2:], 0)
    if " " in pred or " " in obs:
        return pred.split() == obs.split()
    if pred.startswith("0x") or obs.startswith("0x"):
        try:
            return int(pred, 0) == int(obs, 0)
        except ValueError:
            return pred == obs
    return pred == obs


def show(o):
    if isinstance(o, tuple):
        return f"[0x{o[0]:x},0x{o[1]:x}]"
    return str(o)


def load_preds(stage, pdir=None):
    return list(csv.DictReader(open((pdir or (KP / "predictions")) / f"{stage}.tsv"), delimiter="\t"))


def freeze_ok(stage):
    if os.environ.get("R7_SCORE_NOFREEZE") == "1":
        return True
    r = subprocess.run(["bash", str(KP / "run" / "freeze_r7.sh"), "verify", P.SET_OF[stage]], capture_output=True, text=True)
    return r.returncode == 0


def _score(stage, d, dirs, pdir=None):
    """(rows, readings): one row a prediction with its state; the reading of each job.  A control's row with no reading is NODATA."""
    cs = cases(d)
    out, readings = [], {}
    for p in load_preds(stage, pdir):
        c = p["case"]
        if c not in readings:
            readings[c] = read_job(d, c, cs[c], dirs) if c in cs else (None, "NODATA: not in cases.tsv")
        r, why = readings[c]
        pred, note = p["value"], ""
        o = observed(r, p["quantity"])
        st = same(pred, o) if r is not None else None
        if r is not None and r.get("repicked") and p["model"] in ("H-SPAN", "E874-B", "R-5"):
            S = cal_steps(c, dirs)
            v = repick_left(r, S, c)
            if p["model"] == "H-SPAN" and v is not None:
                pred, note = str(v), "re-picked cell: H-SPAN on the calibration's own S_k + (model A_k - model S_k)"
                st = same(pred, o)
            else:
                st, note = None, "re-picked cell: scored for H-SPAN only"
        if r is not None and r.get("scene_fail"):
            why, o = ("" if r["scene_fail"].startswith("knob") else "scene: ") + r["scene_fail"], None
            st = False if p["set"] == "control" else None
        if p["set"] == "control" and st is None and not (r is not None and r.get("scene_fail")):
            st = NO_READING
        out.append(dict(case=c, quantity=p["quantity"], pred=pred, obs=o, model=p["model"], set=p["set"], state=st,
                        why=(note + ("; " if note and why else "") + why) if (note or why) else ("" if o is not None else "no reading")))
    return out, readings


def cal_steps(case, dirs):
    g = case.split("-")[1]
    for d in dirs:
        cs = cases(d)
        n = f"m-cal-{g}"
        if n in cs and cs[n].get("class") == "ok":
            out = kept(d, n, "out")
            if out:
                return R.reading(out.decode(errors="replace"))["S"]
    return None


def repick_left(r, S, case):
    """H-SPAN at a re-picked cell: the calibration's own S_k and A_k = S_k + (model A_k - model S_k) (plan section 4)."""
    if not S or r.get("thr0") is None:
        return None
    g = case.split("-")[1]
    mS, mA, mB, mU = P.MODEL[P.TARGETS[g]]
    A = {k: S[k] + (mA[k] - mS[k]) for k in S if k in mA}
    t = r["thr0"]
    ks = [k for k in sorted(S) if S[k] <= t]
    if not ks or t == S[ks[-1]] or ks[-1] not in A:
        return None
    return 2 if t < A[ks[-1]] else 1


def tri_state(x):
    return {True: "held", False: "FAILED", None: "cannot tell", NO_READING: "NO READING"}[x["state"]]


def ctl_states(rows, pred=lambda x: True):
    return {f"{x['case']} {x['quantity']}": x["state"] for x in rows if x["set"] == "control" and pred(x)}


def premise(stage, rows, readings):
    """scorekit.premise_stops over the stage's controls that declare readings (reads: in the table): the STOP lines."""
    T = {r["name"]: r for r in P.tables()[stage]}
    decl = {n: tuple(P.knob_reads(r)) for n, r in T.items() if P.knob_reads(r)}
    rd = {}
    for n in decl:
        r = readings.get(n, (None, ""))[0]
        if r is None:
            continue
        line = R.line(r) if not r.get("void") else ""
        x = dict(w.split("=", 1) for w in line.split() if "=" in w)
        for k in ("ring_counts", "dec_sa8_380"):
            if k in decl[n]:
                v = observed(r, k)
                x[k] = "-" if v is None else v
        rd[n] = x
    return SK.premise_stops(decl, rd)


def a0_gate(ctl_dir, scene):
    """s-a0's control rows of one scene class ('probe': the five 1500-vertex rows; 'tri': g-qf) as a gate."""
    if ctl_dir is None or not pathlib.Path(ctl_dir).exists():
        return {"s-a0 premise": None}
    rows, _ = _score("s-a0", pathlib.Path(ctl_dir), [pathlib.Path(ctl_dir)])
    keep = (lambda x: x["case"].startswith("a0-qf-")) if scene == "tri" else (lambda x: not x["case"].startswith("a0-qf-"))
    return {f"s-a0 {k}": v for k, v in ctl_states(rows, keep).items()}


def rs(states):
    """Row states for scorekit.tally: a NO READING row of a control counts as cannot tell there (the gate already shuts on it)."""
    return [x if x in (True, False, None) else None for x in states]


def headline(claim, controls, rows):
    return SK.headline(claim, controls, rs(rows))


def tal(rows, m, q=None, pref=None, sets=None):
    return SK.tally([x["state"] if x["state"] in (True, False, None) else None for x in rows if x["model"] == m
                     and (q is None or x["quantity"] == q) and (pref is None or x["case"].startswith(pref)) and (sets is None or x["set"] in sets)])


def stage_verdict(stage, rows, readings, ctl_dir):
    lines = []
    if stage in ("s-a0", "s-k"):
        stops = premise(stage, rows, readings)
        if stops:
            return stops
    if stage == "s-a0":
        lines.append(headline("the premise holds on the test module (S2..S7 and the need in their brackets, 2 then 1 pages left at "
                                 "c4-b5 / c4-b6, R and N, t-s3m6 1 left, g-qf 2 partial renders with H-REPLAY64's peaks, knob proof)",
                                 ctl_states(rows), [x["state"] for x in rows if x["set"] == "control"]))
        return lines
    if stage == "s-m":
        g0 = a0_gate(ctl_dir, "probe")
        for g in P.NEW:
            gate = dict(g0, **ctl_states(rows, lambda x: x["case"] == f"m-cal-{g}"))
            cal = [x["state"] for x in rows if x["case"] == f"m-cal-{g}" and x["model"] == "H-STEPMODEL"]
            cells = [x for x in rows if x["case"].startswith(f"m-{g}-")]
            wh = P.TARGETS[g]
            lines.append(headline(f"H-STEPMODEL at {wh[0]}x{wh[1]} (steps in their brackets, U)", gate, rs(cal)))
            lines.append(headline(f"H-SPAN at {wh[0]}x{wh[1]}", gate, [x["state"] for x in cells if x["model"] == "H-SPAN"])
                         + f"; rival E874-B {tal(cells, 'E874-B')}; R-5 {tal(cells, 'R-5')}")
        reps = [x for x in rows if x["case"].startswith("m-r")]
        lines.append(headline("H-SPAN at 2048x2048 bands 5 to 7 (A - 1, A: replicates of R6-dpm's r-m)", g0,
                                 [x["state"] for x in reps if x["model"] == "H-SPAN"]) + f"; rival E874-B {tal(reps, 'E874-B')}")
        disc = [x for x in rows if x["case"].startswith(("m-c",)) and x["quantity"] == "gps_left" and x["set"] == "heldout"]
        pairs = {}
        for x in disc:
            pairs.setdefault(x["case"], {})[x["model"]] = x
        dd = [v["H-SPAN"]["state"] for v in pairs.values() if "H-SPAN" in v and "E874-B" in v and v["H-SPAN"]["pred"] != v["E874-B"]["pred"]]
        lines.append(f"the discriminating cells (H-SPAN 2, E874-B 1): {SK.tally([s if s in (True, False, None) else None for s in dd])}")
        return lines
    if stage == "s-b":
        g0 = a0_gate(ctl_dir, "tri")
        for name, w, h, dx, dy, U in P.B_SCENES:
            gate = dict(g0, **ctl_states(rows, lambda x: x["case"] == f"b-cal-{name}"))
            cells = [x for x in rows if x["case"].startswith(f"b-{name}-")]
            h1 = headline(f"H-REPLAY64 counts and run peaks on {name} ({w}x{h} move {dx},{dy}, HU1 U {U})", gate,
                             [x["state"] for x in cells if x["model"] == "H-REPLAY64"])
            lines.append(f"{h1}; rivals: row order {tal(cells, 'ROW')}, d=7/4 {tal(cells, 'd=7/4')}, d=1 {tal(cells, 'd=1')}")
        wk = [x for x in rows if x["quantity"] == "walk64"]
        lines.append(headline("H-WALK64 on the dump of b-cal-s22 (every block at its page and slot)", g0, rs([x["state"] for x in wk]))
                     + f"; row order {tal(rows, 'ROW', 'walkrow')}")
        return lines
    if stage == "s-v":
        for N in (4, 8):
            cal = [x for x in rows if x["case"] == f"v-cal-c{N}"]
            lines.append(f"--vtx-coords {N} (exploration, R6-dpm's readings repeated): {tal(cal, 'R6-REPEAT')}")
        return lines
    if stage == "s-k":
        gate = ctl_states(rows)
        lines.append(headline("R-5's sa8 bits at the decision entry under oomring2 (k-b5 0x180, k-b6 0)", gate,
                                 [x["state"] for x in rows if x["model"] == "R-5" and x["quantity"] == "dec_sa8_380"]))
        lines.append(headline("H-PASS: the page counts oomring2 reads at the abort and the decision entries", gate,
                                 [x["state"] for x in rows if x["model"] == "H-PASS"]))
        b5 = [x for x in rows if x["case"].startswith("k-b5-")]
        lines.append(f"band 5 A - 1, A with R-5 under H-SPAN: {tal(b5, 'R-5', 'dec_sa8_380')}; under E874-B: {tal(b5, 'R-5|E874-B')}")
        cr = [x for x in rows if x["case"].startswith("k-creep") and x["quantity"] == "dec_sa8_380"]
        r5 = [x["state"] for x in cr if x["model"] == "R-5"]
        rv = [x["state"] for x in cr if x["model"] == "ISUB-REV"]
        if not SK.gate(gate).ok or None in r5 or not r5:
            v = "cannot tell"
        elif all(r5) and not any(rv):
            v = "isub16 is source 1 minus source 2 (the count read minus dword 36): E864's [infer] read directly"
        elif all(rv) and not any(r5):
            v = "the operands are the other way round (dword 36 minus the count)"
        else:
            v = "mixed"
        lines.append(f"the creep cell (dword 36 = 2 above 1 page left): {v}")
        return lines
    return lines


def run_stage(stage, d, ctl_dir=None, out=None):
    d = pathlib.Path(d)
    if not freeze_ok(stage):
        return f"SUMMARY: refused: the frozen files of set {P.SET_OF[stage]} do not verify (run/freeze_r7.sh verify {P.SET_OF[stage]})"
    dirs = [d] + [pathlib.Path(x) for x in (ctl_dir,) if x] + [d.parent / "s-a0", d.parent / "s-m"]
    rows, readings = _score(stage, d, dirs)
    ctl_dir = ctl_dir or (d.parent / "s-a0")
    text = [f"# score_r7.py {stage} {d}"]
    for x in rows:
        text.append(f"{x['case']:18} {x['quantity']:12} pred {str(x['pred'])[:24]:8} obs {show(x['obs'])[:24]:8} [{x['model']}] {x['set']:8} "
                    f"{tri_state(x)}" + (f"  ({x['why']})" if x["why"] else ""))
    v = stage_verdict(stage, rows, readings, ctl_dir)
    text += [f"verdict: {ln}" for ln in v]
    summary = f"SUMMARY: {stage}: " + " | ".join(v)
    text.append(summary)
    if out:
        pathlib.Path(out).mkdir(parents=True, exist_ok=True)
        (pathlib.Path(out) / f"score-{stage}.txt").write_text("\n".join(text) + "\n")
    return "\n".join(text)


def score_files(stage, d):
    """What sessioncheck.py kept --call runs: the stage's scoring of one kept directory alone (the files it reads there)."""
    d = pathlib.Path(d)
    rows, readings = _score(stage, d, [d])
    stage_verdict(stage, rows, readings, None)
    return rows


# ------------------------------------------------------------------------------------------------ G8: the gate on R6-dpm's kept files
def replay_r6(r6out, drop=()):
    """R6-dpm's attempt a2 through this file's gate rule: its own frozen predictions (r6out/../../predictions), the control rows of r-a0
    as the premise.  Returns (STOP lines of the premise, {stage: {model: tally}}).  `drop`: control (case, quantity) pairs left out."""
    r6out = pathlib.Path(r6out)
    pdir = r6out.parent.parent / "predictions"
    a0 = list(csv.DictReader(open(pdir / "r-a0.tsv"), delimiter="\t"))
    ctl = {}
    for p in a0:
        if p["set"] == "control" and (p["case"], p["quantity"]) not in drop:
            ctl.setdefault(p["case"], []).append(p["quantity"])
    d0 = r6out / "r-a0"
    rd = {}
    for n in ctl:
        c = cases(d0).get(n)
        r, _ = read_job(d0, n, c, [d0]) if c else (None, "")
        if r is None:
            continue
        x = {q: (lambda v: "-" if v is None else v)(observed(r, q)) for q in ctl[n]}
        rd[n] = x
    stops = SK.premise_stops({n: tuple(q) for n, q in ctl.items()}, rd)
    res = {}
    for st in ("r-a0", "r-m", "r-n", "r-v", "r-b", "r-k"):
        d = r6out / st
        out = []
        for p in csv.DictReader(open(pdir / f"{st}.tsv"), delimiter="\t"):
            if p["value"] == "rule" or "@L" in p["model"]:
                continue
            c = cases(d).get(p["case"])
            r, _ = read_job(d, p["case"], c, [d, d0, r6out / "r-n"]) if c else (None, "")
            o = observed(r, p["quantity"]) if r is not None else None
            if p["quantity"] == "peaks":
                o = observed(r, "runpeaks") if r is not None else None
            s = same(p["value"], o) if r is not None and not r.get("scene_fail") else None
            if r is not None and r.get("repicked"):
                s = None
            out.append((p["model"], p["quantity"], s))
        res[st] = {}
        for m, q, s in out:
            res[st].setdefault((m, q), []).append(s)
        res[st] = {k: SK.tally(v) for k, v in res[st].items()}
    return stops, res


def main(argv):
    if len(argv) >= 3 and argv[1] == "replay-r6":
        stops, res = replay_r6(argv[2])
        print("\n".join(stops) or "premise: every control has its reading")
        for st, t in res.items():
            for k, v in sorted(t.items()):
                print(st, k[0], k[1], v)
        return 0
    if len(argv) >= 3:
        ctl = argv[argv.index("--ctl") + 1] if "--ctl" in argv else None
        out = argv[argv.index("--out") + 1] if "--out" in argv else None
        print(run_stage(argv[1], argv[2], ctl, out))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
