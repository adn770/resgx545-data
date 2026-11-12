#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score_r6.py: the frozen scorer of R6-dpm.

    score_r6.py STAGE DIR [--ctl DIR_A0] [--out OUTDIR]    score one stage's kept directory (refuses unless the freeze verifies)
    score_r6.py replay DIR [--scene probe|tri]             the per-job readings of ANY kept DPM directory (R5-dpm's replay)
    score_r6.py replay-r5 R5OUT                            R5-dpm's kept attempt (closing5/r5-dpm/out/a2) scored by THIS scorer with
                                                           R5-dpm's frozen predictions: the dry run of the plan (section 4): it must
                                                           give E860 to E864's tables, with a2b-cal-4x2's S2 held under H-IV (E873)

Every job is read by run/r6read.py (the runner's own reader, one file-name function: kept_name) and checked for its SCENE from the data,
not from its arguments: a 1500-vertex job must reach a second global page and show every first-run step within 1 page of its target's
reference (this session's calibration of the target, else the frozen model's steps; a --vtx-coords job: its own calibration only); a
job of the default triangle (stages r-a0, r-b) must stay at 1 global page.  A job that fails the scene check, or whose own 0x0624 is
not P - 0x22 (the knob proof), is FAILED if it is a control and cannot tell otherwise.  A skipped job, a missing file: cannot tell
(never a pass); a missing file of a job the runner says it ran is NODATA.

Round 6's rules (plan section 4): a step S_k is scored by its bracket (H-IV, E873): a frozen S holds when it lies in [a, max(a, b-1)];
an r-v row whose value is `rule` is the frozen rule evaluated at the job's own thr0 and the object size L read from its calibration's
dump (H-OBJPAGE, E874), CAP and PAGE apart; r-v calibration rows are re-evaluated at the measured L when it is not L0; an r-n cell
the runner re-picked (calibration off the model) is scored for H-PHASE only, on the calibration's own steps and timeline burst ends.
Verdict rules: tools/closing/scorekit.py (copied byte for byte as score/scorekit.py).
"""
from __future__ import annotations

import collections
import csv
import gzip
import json
import os
import pathlib
import re
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "run"), str(KP / "gen"), str(KP / "score")]
import r6read as R  # noqa: E402
import r6plan as P  # noqa: E402
import scorekit as SK  # noqa: E402

M = P.M
OOM = (1 << 20) | (1 << 21)
EOR = 1 << 4
RING_AT, RUNGS, RUNG_WORDS = 0x400, 48, 8


# ------------------------------------------------------------------------------------------------ kept files
def cases(d: pathlib.Path):
    p = pathlib.Path(d) / "cases.tsv"
    if not p.exists():
        return {}
    return {r["name"]: r for r in csv.DictReader(open(p), delimiter="\t")}


def kept(d: pathlib.Path, name: str, kind: str):
    p = pathlib.Path(d) / R.kept_name(name, kind)
    return gzip.open(p).read() if p.exists() else None


def decode_ring(page):
    """gen_oomring.decode_ring's layout: passes (dwords 16..19), lost (20), rungs at res + 0x400, 8 dwords each."""
    base = RING_AT // 4
    rungs = []
    for j in range(RUNGS):
        w = page[base + RUNG_WORDS * j: base + RUNG_WORDS * j + 6]
        if len(w) < 6 or w[0] == 0:
            break
        rungs.append(dict(slot=w[0] - 1, pa0=w[1], pa1=w[2], sa8=w[3], sa9=w[4], timer=w[5]))
    return dict(passes=page[16:20], lost=page[20], rungs=rungs)


def a3_reading(ring):
    """R5-dpm's rung reading (E864): the first OOM entry, the first end of render after it, the DECISION entry = the first OOM entry
    after that end of render, and the next OOM entry after the decision."""
    rg = ring["rungs"]
    oom = [i for i, r in enumerate(rg) if r["pa1"] & OOM]
    if not oom:
        return {}
    eor = next((i for i, r in enumerate(rg) if i > oom[0] and r["pa1"] & EOR), None)
    if eor is None:
        return dict(n_rungs=len(rg))
    dec = next((i for i in oom if i > eor), None)
    out = dict(n_rungs=len(rg), eor_sa9_b8=(rg[eor]["sa9"] >> 8) & 1)
    if dec is not None:
        out["dec_sa8_380"] = rg[dec]["sa8"] & 0x380
        nxt = next((i for i in oom if i > dec), None)
        if nxt is not None:
            out["next_sa8_380"] = rg[nxt]["sa8"] & 0x380
    return out


def target_of(args):
    m = re.search(r"--width (\d+) --height (\d+)", args or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def coords_of(args):
    m = re.search(r"--vtx-coords (\d+)", args or "")
    return int(m.group(1)) if m else None


# ------------------------------------------------------------------------------------------------ the object size L (r-v)
def obj_L(param: bytes | None):
    """L of a completed job's dump: the period of the first two dwords of PB page 1 (the global list's head, F2's reading of a job
    whose lists read empty) over that page.  None when the pair does not recur at one period."""
    if not param or len(param) < 4096:
        return None
    w = struct.unpack_from("<1024I", param, 0)
    pos = [i for i in range(1023) if (w[i], w[i + 1]) == (w[0], w[1])]
    diffs = collections.Counter(b - a for a, b in zip(pos, pos[1:]))
    if not diffs or pos[0] != 0:
        return None
    L, n = diffs.most_common(1)[0]
    # a block holds at least its header, 1/w and packed vertices of 15 vertices (3d.md 10.1): a shorter period is not a block
    return L if L >= 32 and n >= 2 and all(d % L == 0 for d in diffs) else None


# ------------------------------------------------------------------------------------------------ scene check and one job
def ref_steps(wh, dirs, coords=None):
    """The steps a scene check compares with: this session's calibration of the same target and scene (a cal: row of a kept
    directory), else the frozen model's (none for a --vtx-coords scene)."""
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
    return (P.MODEL[wh][0] if wh in P.MODEL else {}), "the frozen model"


def scene_check(r, args, dirs):
    """None when the job's data show the scene its arguments name; else the reason."""
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
            return f"a default-triangle job with {r['gmax']} global pages: not the default triangle"
    return None


def read_job(d, name, c, dirs):
    """(reading or None, why) of one kept job: skipped, NODATA, void, knob proof, scene check."""
    if c.get("class") == "skipped":
        return None, "skipped: " + c.get("note", "")
    if c.get("class") not in ("ok",):
        return None, f"class {c.get('class')}"
    out = kept(d, name, "out")
    if out is None:
        return None, "NODATA: no kept output"
    r = R.reading(out.decode(errors="replace"), kept(d, name, "buf09"))
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
            ring = decode_ring(json.loads(pg)["page"])
            r["ring"] = ring
            r.update(a3_reading(ring))
        except (ValueError, KeyError):
            r["ring"] = None
    if coords_of(c.get("args")) and "cal:" in c.get("knobs", ""):
        r["L"] = obj_L(kept(d, name, "param"))
    return r, ""


# ------------------------------------------------------------------------------------------------ predictions against readings
def observed(r, q):
    if r is None:
        return None
    if q == "cls":
        return None if r["cls"] == "V" else r["cls"]
    if q in ("grow", "x734_clear"):
        return None if r.get(q) is None else str(int(r[q]))
    if q == "knob":
        return None if r.get("knob") is None else f"0x{r['knob']:x}"
    if q.startswith("S") and q[1:].isdigit():
        k = int(q[1:])
        return r["iv"].get(k)                       # the bracket (a, max(a, b - 1)) or None
    if q in ("dec_sa8_380", "next_sa8_380"):
        return None if q not in r else f"0x{r[q]:x}"
    if q == "peaks":
        return " ".join(f"0x{x:x}" for x in r.get("runpeaks", [])) or None
    if q == "gmax":
        return None if r.get("gmax") is None else str(r["gmax"])
    v = r.get(q)
    return None if v is None else str(v)


def same(pred, obs):
    if obs is None:
        return None
    if isinstance(obs, tuple):                     # H-IV: a frozen step holds when it lies in the job's bracket
        return obs[0] <= int(pred, 0) <= obs[1]
    if pred.startswith(">="):
        return int(obs, 0) >= int(pred[2:], 0)
    if pred.startswith("<="):
        return int(obs, 0) <= int(pred[2:], 0)
    if pred.startswith(">"):
        return int(obs, 0) > int(pred[1:], 0)
    if " " in pred or " " in obs:
        return pred.split() == obs.split()
    if pred.startswith("0x") or obs.startswith("0x"):
        return int(pred, 0) == int(obs, 0)
    return pred == obs


def show(o):
    if isinstance(o, tuple):
        return f"[0x{o[0]:x},0x{o[1]:x}]"
    return str(o)


def load_preds(stage, pdir=None):
    return list(csv.DictReader(open((pdir or (KP / "predictions")) / f"{stage}.tsv"), delimiter="\t"))


def freeze_ok():
    if os.environ.get("R6_SCORE_NOFREEZE") == "1":
        return True
    r = subprocess.run(["bash", str(KP / "run" / "freeze_r6.sh"), "verify"], capture_output=True, text=True)
    return r.returncode == 0


def v_rule(p, r, cal):
    """An r-v row's `rule`: the frozen rule at the job's own thr0 and the calibration's measured L (CAP or PAGE, by the model column)."""
    mode = "cap" if p["model"].endswith("CAP") else "page"
    L = cal.get("L") if cal else None
    if r is None or L is None or r.get("thr0") is None:
        return None, "no L from the calibration's dump" if r is not None else ""
    S, B, U, _ = M.model_L(2048, 2048, L, mode)
    v = M.F4.predict(r["thr0"], S, B)
    return (str(v) if v in (1, 2) else None), f"L {L}"


def _score(stage, d, dirs, pdir=None):
    """(rows, readings): one row a prediction, with its state; the reading of each job."""
    cs = cases(d)
    out, readings = [], {}
    for p in load_preds(stage, pdir):
        c = p["case"]
        if c.startswith("@"):
            continue
        if c not in readings:
            readings[c] = read_job(d, c, cs[c], dirs) if c in cs else (None, "NODATA: not in cases.tsv")
        r, why = readings[c]
        pred = p["value"]
        note = ""
        if pred == "rule":                         # r-v: the frozen rule at the measured L
            cal = readings.get(f"v-cal-c{c.split('-')[1][1:]}", (None, ""))[0]
            pred, note = v_rule(p, r, cal)
            if pred is None:
                out.append(dict(case=c, quantity=p["quantity"], pred="rule", obs=observed(r, p["quantity"]), model=p["model"],
                                set=p["set"], state=None, why=note or why or "no reading"))
                continue
        if stage == "r-v" and c.startswith("v-cal-") and "@L" in p["model"] and r is not None and r.get("L") not in (None, int(p["model"].split("@L")[1])):
            mode = "cap" if "CAP" in p["model"] else "page"
            S, B, U, _ = M.model_L(2048, 2048, r["L"], mode)
            k = int(p["quantity"][1:]) if p["quantity"][1:].isdigit() else None
            pred = (f"0x{S[k]:x}" if k in S else "none") if k else (f"0x{U:x}" if U < 0x400 else ">0x400")
            note = f"at the measured L {r['L']}"
        o = observed(r, p["quantity"])
        if p["quantity"] == "need" and pred == ">0x400" and r is not None:
            st = r.get("nparts", 0) >= 1
        elif pred == "none":
            st = None
        else:
            st = same(pred, o) if r is not None else None
        if r is not None and r.get("repicked") and p["model"] in ("H-PHASE", "R-5"):
            st, note = None, "re-picked cell: scored as H-PHASE(repick)"
        if r is not None and r.get("scene_fail"):
            why, o = ("" if r["scene_fail"].startswith("knob") else "scene: ") + r["scene_fail"], None
            st = False if p["set"] == "control" else None
        out.append(dict(case=c, quantity=p["quantity"], pred=pred, obs=o, model=p["model"], set=p["set"], state=st,
                        why=(note + ("; " if note and why else "") + why) if (note or why) else ("" if o is not None else "no reading")))
    # r-n: a re-picked cell, scored for H-PHASE on its calibration's own steps and timeline burst ends
    for c, (r, _) in readings.items():
        if r is None or not r.get("repicked") or r.get("scene_fail"):
            continue
        g = c.split("-")[1]
        cr = readings.get(f"n-cal-{g}", (None, ""))[0]
        if cr is None:
            continue
        v = M.F4.predict(r["thr0"], cr["S"], cr["ends"])
        if v in (1, 2):
            out.append(dict(case=c, quantity="gps_left", pred=str(v), obs=observed(r, "gps_left"), model="H-PHASE(repick)", set="heldout",
                            state=same(str(v), observed(r, "gps_left")), why="calibration's own S and E"))
    return out, readings


def score_rows(stage, d, dirs, pdir=None):
    return _score(stage, d, dirs, pdir)[0]


def by_model(rows, model, sets=None):
    return [x["state"] for x in rows if x["model"] == model and (sets is None or x["set"] in sets)]


def premise_gate(ctl_dir, first="r-a0", pdir=None):
    """r-a0's controls (every `control` prediction of r-a0) as a scorekit gate."""
    if ctl_dir is None or not pathlib.Path(ctl_dir).exists():
        return {f"{first} premise": None}
    res = score_rows(first, pathlib.Path(ctl_dir), [pathlib.Path(ctl_dir)], pdir)
    return {f"{first} {x['case']} {x['quantity']}": x["state"] for x in res if x["set"] == "control"}


def stage_verdict(stage, rows, readings, gate_ctl):
    ctl = dict(gate_ctl)
    for x in rows:
        if x["set"] == "control":
            ctl[f"{x['case']} {x['quantity']}"] = x["state"]
    lines = []
    if stage == "r-a0":
        lines.append(SK.headline("the premise holds on rgn4 (steps in their brackets incl. S6 0x181 and S7 0x1ca, c4-b5 R, c4-b6 N, left "
                                 "2 and 1, g-qf 2 partial renders, knob proof)", ctl, [x["state"] for x in rows]))
        return lines
    g = SK.gate(ctl)
    tag = "" if g.ok else " [GATED: " + "; ".join(g.problems[:3]) + "]"
    tal = lambda m, q=None: SK.tally([x["state"] for x in rows if x["model"] == m and (q is None or x["quantity"] == q)])
    if stage == "r-m":
        lines.append(SK.headline("H-PHASE at the new bands 5, 6, 7 (the model's burst ends B5 0x176, B6 0x1c1, B7 0x20c)", ctl,
                                 by_model(rows, "H-PHASE")))
        lines.append(f"rival E-TL (F4's timeline burst ends): {tal('E-TL')}{tag}")
        lines.append(f"R-5 silent: {tal('R-5')}; H-GREQ no grow: {tal('H-GREQ')}; F9 count (explore): {tal('F9')}{tag}")
        return lines
    if stage == "r-n":
        for gname in P.NEW:
            cal = [x["state"] for x in rows if x["case"] == f"n-cal-{gname}" and x["model"] == "H-STEPMODEL"]
            cells = [x for x in rows if x["case"].startswith(f"n-{gname}-")]
            lines.append(SK.headline(f"H-STEPMODEL at {P.TARGETS[gname][0]}x{P.TARGETS[gname][1]} (steps in their brackets, U)", gate_ctl, cal))
            lines.append(SK.headline(f"H-PHASE at {gname} (B - 1, B, S - 1 of bands 3 and 4)", gate_ctl,
                                     [x["state"] for x in cells if x["model"] == "H-PHASE"]) +
                         f"; re-picked {SK.tally([x['state'] for x in cells if x['model'] == 'H-PHASE(repick)'])}"
                         f"; R-5 {SK.tally([x['state'] for x in cells if x['model'] == 'R-5'])}")
        return lines
    if stage == "r-v":
        for N in (4, 8):
            cal = readings.get(f"v-cal-c{N}", (None, ""))[0]
            L = cal.get("L") if cal else None
            res = {}
            for mode in ("CAP", "PAGE"):
                res[mode] = SK.tally([x["state"] for x in rows if x["case"] == f"v-cal-c{N}" and x["model"].startswith(f"BURST-{mode}")])
            prem = cal is not None and not cal.get("scene_fail")
            hc, hp = res["CAP"], res["PAGE"]
            if not prem:
                v = "cannot tell (the premise: the calibration is not a 1500-vertex scene or was not kept)"
            elif hc.failed == 0 and hc.held and hp.failed:
                v = "H-BURST-CAP (the bursts stay at the stream blocks' capacity)"
            elif hp.failed == 0 and hp.held and hc.failed:
                v = "H-BURST-PAGE (one burst per global step)"
            elif hc.failed and hp.failed:
                v = "both refuted"
            else:
                v = "cannot tell"
            cells = [x for x in rows if x["case"].startswith(f"v-c{N}-")]
            lines.append(f"--vtx-coords {N}: L {L} (L0 {P.VTX[N]}); steps CAP {hc}, PAGE {hp}: {v}; cells H-PHASE|CAP "
                         f"{SK.tally([x['state'] for x in cells if x['model'] == 'H-PHASE|BURST-CAP'])}, |PAGE "
                         f"{SK.tally([x['state'] for x in cells if x['model'] == 'H-PHASE|BURST-PAGE'])}, E-TL "
                         f"{SK.tally([x['state'] for x in cells if x['model'] == 'E-TL'])}{tag}")
        return lines
    if stage == "r-b":
        qf = {f"{x['case']} {x['quantity']}": x["state"] for x in rows if x["case"].startswith("b-qf-") and x["set"] == "control"}
        lines.append(SK.headline("the four g-qf controls repeat on rgn4", dict(gate_ctl, **qf), list(qf.values())))
        for sc in P.B_NAME:
            calc = {f"{x['case']} {x['quantity']}": x["state"] for x in rows if x["case"] == f"b-cal-{sc}"}
            cells = [x for x in rows if x["case"].startswith(f"b-{sc}-")]
            gate = dict(gate_ctl, **qf, **calc)
            h = SK.headline(f"H-REPLAY (row order) counts on {sc} (HU1 U = {P.B_U[sc]})", gate,
                            [x["state"] for x in cells if x["model"] == "H-REPLAY-ROW" and x["quantity"] == "nparts"])
            within = 0
            for x in cells:
                if x["model"] == "H-REPLAY-ROW" and x["quantity"] == "peaks" and x["obs"]:
                    a, b = x["pred"].split(), x["obs"].split()
                    within += len(a) == len(b) and all(abs(int(u, 16) - int(v, 16)) <= 3 for u, v in zip(a, b))
            alt = ", ".join(f"{m} {SK.tally([x['state'] for x in cells if x['model'] == m and x['quantity'] == 'nparts'])}"
                            for m in ("H-REPLAY-COL", "d=7/4", "d=1"))
            lines.append(f"{h}; row peaks exact {SK.tally([x['state'] for x in cells if x['model'] == 'H-REPLAY-ROW' and x['quantity'] == 'peaks'])}, "
                         f"within 3 pages {within}; rivals: {alt}")
        return lines
    if stage == "r-k":
        a3 = {f"{x['case']} {x['quantity']}": x["state"] for x in rows if x["model"] in ("CTL-A3", "H-BITS")}
        lines.append(SK.headline("R-5's sa8 bits at the decision entry with the task armed (k-b5 0x180, k-b6 0)", dict(gate_ctl, **a3),
                                 [x["state"] for x in rows if x["model"] == "R-5" and x["quantity"] == "dec_sa8_380"]))
        cr = [x for x in rows if x["case"].startswith("k-creep") and x["quantity"] == "dec_sa8_380"]
        r5 = [x["state"] for x in cr if x["model"] == "R-5"]
        rv = [x["state"] for x in cr if x["model"] == "ISUB-REV"]
        if not SK.gate(dict(gate_ctl, **a3)).ok or None in r5 or not r5:
            v = "cannot tell"
        elif all(r5) and not any(rv):
            v = "isub16 is source 1 minus source 2 (the count read minus dword 36): E864's [infer] pinned"
        elif all(rv) and not any(r5):
            v = "the operands are the other way round (dword 36 minus the count)"
        else:
            v = "mixed"
        lines.append(f"the creep cell (dword 36 = 2 above 1 page left): {v}")
        lines.append("counts at the passes: cannot tell (oomring2 refused by both verifiers; r5's oomring ran, bits only)")
        return lines
    return lines


def run_stage(stage, d, ctl_dir=None, out=None):
    d = pathlib.Path(d)
    if not freeze_ok():
        return "SUMMARY: refused: the frozen files do not verify (run/freeze_r6.sh verify)"
    dirs = [d] + [pathlib.Path(x) for x in (ctl_dir,) if x] + [d.parent / "r-a0", d.parent / "r-n", d.parent / "r-v"]
    rows, readings = _score(stage, d, dirs)
    gate_ctl = {} if stage == "r-a0" else premise_gate(ctl_dir or (d.parent / "r-a0"))
    text = [f"# score_r6.py {stage} {d}"]
    for x in rows:
        st = {True: "held", False: "FAILED", None: "cannot tell"}[x["state"]]
        text.append(f"{x['case']:18} {x['quantity']:12} pred {str(x['pred'])[:24]:8} obs {show(x['obs'])[:24]:8} [{x['model']}] {x['set']:8} {st}"
                    + (f"  ({x['why']})" if x["why"] else ""))
    v = stage_verdict(stage, rows, readings, gate_ctl)
    text += [f"verdict: {ln}" for ln in v]
    summary = f"SUMMARY: {stage}: " + " | ".join(v)
    text.append(summary)
    if out:
        pathlib.Path(out).mkdir(parents=True, exist_ok=True)
        (pathlib.Path(out) / f"score-{stage}.txt").write_text("\n".join(text) + "\n")
    return "\n".join(text)


# ------------------------------------------------------------------------------------------------ the dry run on R5-dpm's kept attempt
def replay_r5(r5out):
    """R5-dpm's seven stages, scored by this file's reader and rules (H-IV for the steps) against R5-dpm's own frozen predictions
    (closing5/r5-dpm/predictions, or the published copy beside the out directory): {stage: {model: tally}} and the gate problems."""
    r5out = pathlib.Path(r5out)
    pdir = r5out.parent.parent / "predictions"
    res = {}
    for st in ("d-a0", "d-a1", "d-a2", "d-a2b", "d-t", "d-b", "d-a3"):
        d = r5out / st
        rows, _ = _score(st, d, [d, r5out / "d-a0", r5out / "d-a2b"], pdir)
        res[st] = {m: SK.tally([x["state"] for x in rows if x["model"] == m]) for m in sorted({x["model"] for x in rows})}
        res[st]["_controls_failed"] = [f"{x['case']} {x['quantity']}" for x in rows if x["set"] == "control" and x["state"] is not True]
    return res


# ------------------------------------------------------------------------------------------------ replay of any directory
def replay(d, scene=None):
    d = pathlib.Path(d)
    cs = cases(d)
    jobs, ctl = {}, {}
    for n, c in cs.items():
        r, why = read_job(d, n, c, [d])
        if r is not None and scene and not r.get("scene_fail"):
            if scene == "tri" and (r.get("gmax") or 1) != 1:
                r["scene_fail"] = "not the default triangle"
            if scene == "probe" and (r.get("gmax") or 0) < 2:
                r["scene_fail"] = "not the 1500-vertex scene"
        jobs[n] = (r, why)
        m = re.search(r"ctl:([RN])", c.get("knobs", ""))
        if m:
            ctl[n] = None if r is None else (False if r.get("scene_fail") else r["cls"] == m.group(1))
    lines = []
    for n, (r, why) in jobs.items():
        if r is None:
            lines.append(f"{n:18} {why}")
            continue
        s = " ".join(f"S{k}=0x{v:x}" for k, v in sorted(r["S"].items()))
        lines.append(f"{n:18} thr0={r['thr0'] and hex(r['thr0'])} cls={r['cls']} grow={r['grow']} nparts={r['nparts']} "
                     f"gps_left={r['gps_left']} gmax={r['gmax']} {s}" + (f" SCENE: {r['scene_fail']}" if r.get("scene_fail") else ""))
    g = SK.gate(ctl) if ctl else None
    head = ("controls: none in cases.tsv" if g is None else ("controls PASS" if g.ok else "controls FAILED: " + "; ".join(g.problems)))
    return dict(lines=lines, controls=head, jobs=jobs)


def main(argv):
    if len(argv) >= 3 and argv[1] == "replay":
        sc = argv[argv.index("--scene") + 1] if "--scene" in argv else None
        rp = replay(argv[2], sc)
        print("\n".join(rp["lines"]))
        print("SUMMARY: replay:", rp["controls"])
        return 0
    if len(argv) >= 3 and argv[1] == "replay-r5":
        for st, t in replay_r5(argv[2]).items():
            print(st, "; ".join(f"{m}: {v}" for m, v in t.items() if not m.startswith("_")), "| controls not held:", t["_controls_failed"])
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
