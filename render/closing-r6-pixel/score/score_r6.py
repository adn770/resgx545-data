#!/usr/bin/env python3
"""score_r6.py: score one R6-pixel stage from its kept files, the gate of a stage, and the verdict over an attempt.

  score_r6.py STAGE KEPTDIR     STAGE p6-rd p6-l3 g6-rwa g6-rw p6-s; KEPTDIR = out/ATT/STAGE (copied from the laptop's
                                ~/scratch/r6p/out).  g6-rw reads part a from KEPTDIR/../g6-rwa, else from the newest out/*/g6-rwa
  score_r6.py gate STAGE KEPT   exit 0 pass, 1 a gating control FAILED, 2 cannot tell: the driver (run/r6.sh) stops the session unless
                                0.  p6-rd: the bridge controls (c-e709 G-o4, c-u G-o1, c-ow, c-rd-0); p6-l3: never stops (its
                                controls void the set only); g6-rwa: every control word exact; g6-rw: the controls; p6-s: the restore
                                check (r-u G-o1)
  score_r6.py verdict ROOT      one line a stage of an attempt directory (out/ATT)
Refuses to run unless `run/freeze_r6.sh verify` passes.  Run with the scratch venv:
  PYTHONDONTWRITEBYTECODE=1 .../pixel-faults/.venv/bin/python score/score_r6.py p6-rd out/ATT/p6-rd
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
import score_rd  # noqa: E402
import score_rw6  # noqa: E402
import scorekit as SK  # noqa: E402

STAGES = ["p6-rd", "p6-l3", "g6-rwa", "g6-rw", "p6-s"]


def preds_rw():
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    for st in ("g6-rwa", "g6-rw"):
        for c, qs in L.load_preds(stage=st).items():
            for q, v in qs.items():
                out[c][q] += v
    return out


def part_a(d):
    d = pathlib.Path(d)
    a = d.parent / "g6-rwa"
    if (a / "cases.tsv").exists():
        return a, ""
    cands = sorted((p for p in (HERE.parent / "out").glob("*/g6-rwa") if (p / "cases.tsv").exists()), key=lambda p: p.parent.name)
    if cands:
        return cands[-1], f"part a from {cands[-1]} (not in this attempt)"
    return None, "no g6-rwa kept: the controls cannot tell"


def run_stage(stage, d):
    """(text, result) for one stage directory."""
    if stage == "p6-rd":
        return score_rd.score_rd(L.Kept(d), L.load_preds(stage=stage))
    if stage == "p6-l3":
        return score_rd.score_l3(L.Kept(d), L.load_preds(stage=stage))
    if stage == "p6-s":
        return score_rd.score_s(L.Kept(d), L.load_preds(stage=stage))
    p = preds_rw()
    if stage == "g6-rwa":
        return score_rw6.score_a(L.Kept(d), {n: v for n, v in p.items() if n.startswith(("rw-k", "d-"))})
    if stage == "g6-rw":
        a, note = part_a(d)
        text, res = score_rw6.score(L.Kept(a) if a else None, L.Kept(d), p)
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
    r = subprocess.run([str(HERE.parent / "run" / "freeze_r6.sh"), "verify"], capture_output=True, text=True)
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
