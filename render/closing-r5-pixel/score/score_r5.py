#!/usr/bin/env python3
"""score_r5.py: score one R5-pixel stage from its kept files, the gate of a stage, and the verdict over an attempt.

  score_r5.py STAGE KEPTDIR     STAGE p5-o4 g5-rwa g5-rw; KEPTDIR = out/ATT/STAGE (copied from the laptop's ~/r5p-out).  g5-rw reads
                                part a from KEPTDIR/../g5-rwa, else from the newest out/*/g5-rwa (printed)
  score_r5.py gate STAGE KEPT   exit 0 pass, 1 a gating control FAILED, 2 cannot tell: the driver (run/r5.sh) stops the session unless
                                0.  p5-o4: the bridge controls (c-e709 G-o4, c-u G-o1, c-v-a4 class A; c-all4 voids the stage only);
                                g5-rwa: every control word exact and fewer than 3 q jobs FAILED shape; g5-rw: the controls (always 0
                                when they passed: nothing runs after it)
  score_r5.py verdict ROOT      one line a stage of an attempt directory (out/ATT)
Refuses to run unless `run/freeze_r5.sh verify` passes.  Run with the scratch venv:
  PYTHONDONTWRITEBYTECODE=1 .../pixel-faults/.venv/bin/python score/score_r5.py p5-o4 out/ATT/p5-o4
Rules (HACKING.md, Closing-session scorers: score/scorekit.py): a job with no output, an rc that is not a result of the tool, a missing
dump or a class that is not ok is `cannot tell`, tested before any match, never a pass; a control that is not a pass shuts the gate of
the rows that depend on it; held-out rows are tallied apart; every scorer ends with one SUMMARY line."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import collections  # noqa: E402
import pathlib  # noqa: E402
import subprocess  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r4lib as L  # noqa: E402
import score_o5  # noqa: E402
import score_rw5  # noqa: E402
import scorekit as SK  # noqa: E402

STAGES = ["p5-o4", "g5-rwa", "g5-rw"]


def preds_rw():
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    for st in ("g5-rwa", "g5-rw"):
        for c, qs in L.load_preds(stage=st).items():
            for q, v in qs.items():
                out[c][q] += v
    return out


def part_a(d):
    d = pathlib.Path(d)
    a = d.parent / "g5-rwa"
    if (a / "cases.tsv").exists():
        return a, ""
    cands = sorted((p for p in (HERE.parent / "out").glob("*/g5-rwa") if (p / "cases.tsv").exists()), key=lambda p: p.parent.name)
    if cands:
        return cands[-1], f"part a from {cands[-1]} (not in this attempt)"
    return None, "no g5-rwa kept: the controls cannot tell"


def run_stage(stage, d):
    """(text, result) for one stage directory."""
    if stage == "p5-o4":
        return score_o5.score(L.Kept(d), L.load_preds(stage=stage))
    p = preds_rw()
    if stage == "g5-rwa":
        ka = L.Kept(d)
        g, lines = score_rw5.gate_a(ka, p)
        text, res = score_rw5.score(ka, None, {n: v for n, v in p.items() if n.startswith(("rw-k", "q-"))})
        body = [x for x in text.splitlines() if not x.startswith("SUMMARY:")]
        s = "part a: " + ("PASS" if g.ok else ("FAILED: " if g.failed else "CANNOT TELL: ") + "; ".join(g.problems))
        res["gate"] = g
        return "\n".join(body + lines + ["SUMMARY: " + s]), res
    if stage == "g5-rw":
        a, note = part_a(d)
        text, res = score_rw5.score(L.Kept(a) if a else None, L.Kept(d), p)
        return (note + "\n" if note else "") + text, res
    raise SystemExit(f"unknown stage {stage}")


def gate(stage, d):
    text, res = run_stage(stage, d)
    g = res.get("gate")
    if g is None:
        g = SK.Gate(ok=False, problems=["no control state in the result"])
    code = 0 if g.ok else (1 if g.failed else 2)
    return code, f"gate {stage}: " + ("PASS" if g.ok else ("FAILED: " if g.failed else "CANNOT TELL: ") + "; ".join(g.problems))


def verdict(root):
    lines = []
    root = pathlib.Path(root)
    for st in STAGES:
        d = root / st
        if not (d / "cases.tsv").exists():
            lines.append(f"{st}: did not run")
            continue
        text, _ = run_stage(st, d)
        s = [x for x in text.splitlines() if x.startswith("SUMMARY:")]
        lines.append(f"{st}: " + (s[-1][len('SUMMARY: '):] if s else "no SUMMARY"))
    print("\n".join(lines))
    return 0


def main(a):
    r = subprocess.run([str(HERE.parent / "run" / "freeze_r5.sh"), "verify"], capture_output=True, text=True)
    if r.returncode:
        print("REFUSING: the frozen files do not verify:\n" + r.stdout + r.stderr)
        return 3
    if a and a[0] == "gate" and len(a) == 3:
        code, text = gate(a[1], a[2])
        print(text)
        return code
    if a and a[0] == "verdict" and len(a) == 2:
        return verdict(a[1])
    if len(a) != 2 or a[0] not in STAGES:
        print(__doc__)
        return 2
    try:
        text, _ = run_stage(*a)
        print(text)
    except SystemExit as e:
        print(f"REFUSING: {e}")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
