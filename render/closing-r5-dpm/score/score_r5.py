#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score_r5.py: the frozen scorer of R5-dpm.

    score_r5.py STAGE DIR [--ctl DIR_A0] [--out OUTDIR]     score one stage's kept directory (refuses unless the freeze verifies)
    score_r5.py replay DIR [--scene probe|tri]              the per-job readings of ANY kept DPM directory (round 3's g-c4, g-c5, g-qf
                                                            and this session's), its controls (cases.tsv ctl:R/N) and flips: the
                                                            dry run of plan section 5

Every job is read by run/r5read.py (the runner's own reader, one file-name function) and checked for its SCENE from the data, not from
its arguments: a 1500-vertex job must reach a second global page and show every first-run step within 1 page of its target's
calibration (this session's, else the section 1 table); a job of the default triangle (stage d-b) must stay at 1 global page.  A job
that fails the scene check, or whose own 0x0624 is not P - 0x22 (the knob proof), is FAILED if it is a control and cannot tell
otherwise (round 4's slip o2).  A skipped job, a missing file: cannot tell (never a pass); a missing file of a job the runner says it ran is reported as
NODATA.  Verdict rules: tools/closing/scorekit.py (copied byte for byte as score/scorekit.py).
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
import r5read as R  # noqa: E402
import r5plan as P  # noqa: E402
import scorekit as SK  # noqa: E402

OOM, EOR = P.OOM, P.EOR
RING_AT, RUNGS, RUNG_WORDS = 0x400, 48, 8


# ------------------------------------------------------------------------------------------------ kept files
def cases(d: pathlib.Path):
    p = d / "cases.tsv"
    if not p.exists():
        return {}
    return {r["name"]: r for r in csv.DictReader(open(p), delimiter="\t")}


def kept(d: pathlib.Path, name: str, kind: str):
    p = d / R.kept_name(name, kind)
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
    """The rungs the plan names (section 2, H-BITS): the first OOM entry (pa1 bit 20 or 21), the first end of render after it (bit 4),
    the DECISION entry = the first OOM entry after that end of render, and the next OOM entry after the decision."""
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


def ref_steps(wh, dirs):
    """The steps a scene check compares with: this session's calibration of the target (a cal: row of a kept directory), else the
    section 1 table."""
    for d in dirs:
        for n, c in cases(d).items():
            if "cal:" in c.get("knobs", "") and target_of(c.get("args")) == wh and c.get("class") == "ok":
                out = kept(d, n, "out")
                if out:
                    r = R.reading(out.decode(errors="replace"))
                    if r.get("mono"):
                        return r["S"], f"calibration {n}"
    return P.STEPS.get(wh, {}), "section 1 table"


def scene_check(r, args, dirs):
    """None when the job's data show the scene its arguments name; else the reason."""
    if r.get("void"):
        return r["void"]
    if (args or "").startswith("probe") and "--vertices 1500" in args:
        if (r.get("gmax") or 0) < 2:
            return f"a 1500-vertex job that never reached a second global page (gmax {r.get('gmax')}): not the 1500-vertex scene"
        ref, src = ref_steps(target_of(args), dirs)
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
    return r, ""


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
        return f"0x{r['S'][k]:x}" if k in r.get("S", {}) else None
    if q in ("dec_sa8_380", "next_sa8_380"):
        return None if q not in r else f"0x{r[q]:x}"
    v = r.get(q)
    return None if v is None else str(v)


def same(pred, obs):
    if obs is None:
        return None
    if pred.startswith("<="):
        return int(obs) <= int(pred[2:])
    if pred.startswith("0x") or obs.startswith("0x"):
        return int(pred, 0) == int(obs, 0)
    return pred == obs


# ------------------------------------------------------------------------------------------------ one stage
def load_preds(stage):
    return list(csv.DictReader(open(KP / "predictions" / f"{stage}.tsv"), delimiter="\t"))


def freeze_ok():
    if os.environ.get("R5_SCORE_NOFREEZE") == "1":
        return True
    r = subprocess.run(["bash", str(KP / "run" / "freeze_r5.sh"), "verify"], capture_output=True, text=True)
    return r.returncode == 0


def premise_gate(ctl_dir):
    """A0's controls (every `control` prediction of d-a0) as a scorekit gate."""
    if ctl_dir is None or not pathlib.Path(ctl_dir).exists():
        return {"d-a0 premise": None}
    res = score_rows("d-a0", pathlib.Path(ctl_dir), [pathlib.Path(ctl_dir)])
    return {f"d-a0 {x['case']} {x['quantity']}": x["state"] for x in res if x["set"] == "control"}


def _score(stage, d, dirs):
    """(rows, readings): one row a prediction, with its state; the reading of each job."""
    cs = cases(d)
    out = []
    readings = {}
    for p in load_preds(stage):
        c = p["case"]
        if c.startswith("@"):
            continue
        if c not in readings:
            if c not in cs:
                readings[c] = (None, "NODATA: not in cases.tsv")
            else:
                readings[c] = read_job(d, c, cs[c], dirs)
        r, why = readings[c]
        o = observed(r, p["quantity"])
        st = same(p["value"], o) if r is not None else None
        if r is not None and r.get("scene_fail"):
            why, o = ("" if r["scene_fail"].startswith("knob") else "scene: ") + r["scene_fail"], None
            st = False if p["set"] == "control" else None
        out.append(dict(case=c, quantity=p["quantity"], pred=p["value"], obs=o, model=p["model"], set=p["set"], state=st,
                        why=why or ("" if o is not None else "no reading")))
    return out, readings


def score_rows(stage, d, dirs):
    return _score(stage, d, dirs)[0]


def by_model(rows, model, sets=None):
    return [x["state"] for x in rows if x["model"] == model and (sets is None or x["set"] in sets)]


def stage_verdict(stage, rows, readings, gate_ctl):
    ctl = dict(gate_ctl)
    for x in rows:
        if x["set"] == "control":
            ctl[f"{x['case']} {x['quantity']}"] = x["state"]
    lines = []
    if stage == "d-a0":
        lines.append(SK.headline("the premise holds on rgn4 (steps of section 1, the four flips, no grow, knob proof)", ctl,
                                 [x["state"] for x in rows]))
        return lines
    g = SK.gate(ctl)
    tag = "" if g.ok else " [GATED: " + "; ".join(g.problems[:3]) + "]"
    if stage == "d-a1":
        reps = [readings[c][0] for c in sorted(readings) if c.startswith("a1-rep")]
        grows = [None if r is None or r.get("grow") is None else bool(r["grow"]) for r in reps]
        n = sum(1 for x in grows if x)
        nb = [x["state"] for x in rows if x["quantity"] == "grow" and not x["case"].startswith("a1-rep")]
        if None in grows or not g.ok:
            v = "cannot tell"
        elif any(s is False for s in nb):
            v = "refuted (a grow at a neighbour)"
        elif n == 5:
            v = "held (5 of 5)"
        elif n == 4:
            v = "mostly, with a race (4 of 5)"
        else:
            v = f"refuted ({n} of 5)"
        noise = "cannot tell" if None in grows else ("consistent" if n <= 1 else f"refuted ({n} of 5)")
        lines.append(f"H-GREQ {v}; H-NOISE {noise}; grows in the replicates {grows}; neighbours {SK.tally(nb)}{tag}")
        lines.append("silent (all 9): " + str(SK.tally([x["state"] for x in rows if x["quantity"] == "cls"])) + tag)
        return lines
    if stage == "d-a2":
        lines.append("H-GREQ: " + str(SK.tally(by_model(rows, "H-GREQ"))) + tag)
        dec = []
        for c in sorted({x["case"] for x in rows}):
            pe = next((x for x in rows if x["case"] == c and x["model"] == "H-PEND" and x["quantity"] == "cls"), None)
            bl = next((x for x in rows if x["case"] == c and x["model"] == "H-BLOCK" and x["quantity"] == "cls"), None)
            if not pe or not bl or pe["pred"] == bl["pred"]:
                continue
            r = readings[c][0]
            if r is None or r.get("grow") is None or r["cls"] == "V" or r.get("scene_fail"):
                dec.append((c, "cannot tell"))
            elif not r["grow"]:
                dec.append((c, "no grow (void for this question)"))
            else:
                dec.append((c, "H-PEND" if r["cls"] == pe["pred"] else "H-BLOCK"))
        kinds = {k for _, k in dec}
        if not dec or "cannot tell" in kinds or not g.ok:
            v = "cannot tell"
        elif kinds == {"H-PEND"}:
            v = "H-PEND (guard intact; c4-b3 a sampling artefact of the count estimate)"
        elif kinds == {"H-BLOCK"}:
            v = "H-BLOCK (the guard lacks a condition: A3 names the bit)"
        elif kinds == {"no grow (void for this question)"}:
            v = "H-GREQ refuted at the S cells: void for PEND/BLOCK"
        else:
            v = "mixed, by cell"
        lines.append(f"raising-side S cells: {v}: {dec}{tag}")
        off = {x["case"] for x in rows if x["model"] == "H-GREQ" and x["pred"] == "0"}
        lines.append("R-5's guard off the steps (the neighbours): " +
                     str(SK.tally([x["state"] for x in rows if x["case"] in off and x["quantity"] == "cls" and x["model"] == "H-PEND"])) + tag)
        return lines
    if stage in ("d-a2b", "d-t"):
        for m in sorted({x["model"] for x in rows}):
            lines.append(f"{m}: {SK.tally(by_model(rows, m))}{tag}")
        return lines
    if stage == "d-b":
        qf = {f"{x['case']} {x['quantity']}": x["state"] for x in rows if x["case"].startswith("b-qf-")}
        lines.append(SK.headline("the five g-qf controls repeat on rgn4", dict(gate_ctl, **qf), [s for s in qf.values()]))
        for sc in P.B_MOVES:
            cal = {f"{x['case']} {x['quantity']}": x["state"] for x in rows if x["case"] == f"b-cal-{sc}"}
            cells = [x for x in rows if x["case"].startswith(f"b-{sc}-")]
            gate = dict(gate_ctl, **qf, **cal)
            h = SK.headline(f"H-CNT on scene {sc} (HU1 U = {P.B_U[sc]})", gate, [x["state"] for x in cells if x["model"] == "H-CNT"])
            alts = ", ".join(f"{a} {SK.tally([x['state'] for x in cells if x['model'] == a]).failed} misses" for a in P.ALTS)
            lines.append(f"{h}; alternatives: {alts}")
        return lines
    if stage == "d-a3":
        a3 = {f"{x['case']} {x['quantity']}": x["state"] for x in rows if x["model"] == "CTL-A3"}
        bits = [x["state"] for x in rows if x["model"] == "H-BITS"]
        lines.append(SK.headline("H-BITS (R-5's sa8 semantics, first direct read)", dict(gate_ctl, **a3), bits))
        for m in ("H-PEND", "H-BLOCK"):
            lines.append(f"{m} on the rungs: {SK.tally([x['state'] for x in rows if x['model'] == m and x['quantity'] != 'cls'])}" +
                         ("" if SK.gate(dict(gate_ctl, **a3)).ok else " [GATED: the controls with the task armed]"))
        return lines
    return lines


def run_stage(stage, d, ctl_dir=None, out=None):
    d = pathlib.Path(d)
    if not freeze_ok():
        return "SUMMARY: refused: the frozen files do not verify (run/freeze_r5.sh verify)"
    dirs = [d] + [pathlib.Path(x) for x in (ctl_dir,) if x] + [d.parent / "d-a0", d.parent / "d-a2b"]
    rows, readings = _score(stage, d, dirs)
    gate_ctl = {} if stage == "d-a0" else premise_gate(ctl_dir or (d.parent / "d-a0"))
    text = [f"# score_r5.py {stage} {d}"]
    for x in rows:
        st = {True: "held", False: "FAILED", None: "cannot tell"}[x["state"]]
        text.append(f"{x['case']:18} {x['quantity']:12} pred {x['pred']:6} obs {str(x['obs']):6} [{x['model']}] {x['set']:8} {st}"
                    + (f"  ({x['why']})" if x["why"] else ""))
    v = stage_verdict(stage, rows, readings, gate_ctl)
    text += [f"verdict: {ln}" for ln in v]
    summary = f"SUMMARY: {stage}: " + " | ".join(v)
    text.append(summary)
    if out:
        pathlib.Path(out).mkdir(parents=True, exist_ok=True)
        (pathlib.Path(out) / f"score-{stage}.txt").write_text("\n".join(text) + "\n")
    return "\n".join(text)


# ------------------------------------------------------------------------------------------------ replay (plan section 5)
def replay(d, scene=None):
    """Every kept job of a directory read as the session reads its own: thr0, class, grow, partial renders, global pages left, steps;
    the controls of its cases.tsv (ctl:R/N) as a gate (a scene-check failure FAILS a control); the last raise / first silent cell by
    target (scorekit.bracket over the class ladder); the count by thr0 of default-triangle jobs."""
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
    grows = sorted(n for n, (r, _) in jobs.items() if r is not None and r.get("grow"))
    flips = {}
    for n, (r, _) in jobs.items():
        if r is None or r["cls"] == "V" or r.get("scene_fail") or "--vertices 1500" not in cs[n].get("args", ""):
            continue
        flips.setdefault(target_of(cs[n]["args"]), []).append((r["thr0"], r["cls"]))
    fl = {}
    for wh, pts in flips.items():
        R_ = [t for t, c in pts if c == "R"]
        N_ = [t for t, c in pts if c == "N"]
        if R_ and N_:
            lo = max(R_)
            hi = min((t for t in N_ if t > lo), default=None)
            fl[wh] = (lo, hi)
    counts = {r["thr0"]: r["nparts"] for n, (r, _) in jobs.items() if r is not None and cs[n].get("args", "").startswith("tri")
              and r["thr0"] is not None}
    g = SK.gate(ctl) if ctl else None
    head = ("controls: none in cases.tsv" if g is None else ("controls PASS" if g.ok else "controls FAILED: " + "; ".join(g.problems)))
    return dict(lines=lines, grows=grows, flips=fl, counts=counts, controls=head, jobs=jobs)


def main(argv):
    if len(argv) >= 3 and argv[1] == "replay":
        sc = argv[argv.index("--scene") + 1] if "--scene" in argv else None
        rp = replay(argv[2], sc)
        print("\n".join(rp["lines"]))
        print("grows:", rp["grows"])
        print("flips (last raise, first silent above):", {f"{w}x{h}": (hex(a), hex(b) if b else None) for (w, h), (a, b) in rp["flips"].items()})
        if rp["counts"]:
            print("counts by thr0:", {hex(k): v for k, v in sorted(rp["counts"].items())})
        print("SUMMARY: replay:", rp["controls"])
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
