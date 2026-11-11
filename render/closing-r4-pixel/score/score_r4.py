#!/usr/bin/env python3
"""score_r4.py: score one R4-pixel stage from its kept files, the bridge gate of a stage, and the verdict over a session.

  score_r4.py STAGE KEPTDIR     STAGE p4-o4 q4-v q4-f q4-t g4-rw; KEPTDIR = out/ATT/STAGE (copied from the laptop's ~/r4p-out)
  score_r4.py gate STAGE KEPT   exit 0 every bridge control of the stage passed, 1 a control FAILED, 2 a control cannot tell (void or
                                not run): the driver (run/r4.sh) stops the session unless it is 0 (the lead decides)
  score_r4.py verdict ROOT      the stage summaries of an attempt directory (out/ATT)
Refuses to run unless `run/freeze_r4.sh verify` passes.  Prints the per-job table and one `SUMMARY:` line.  Run with the scratch venv:
  PYTHONDONTWRITEBYTECODE=1 .../pixel-faults/.venv/bin/python score/score_r4.py q4-v out/ATT/q4-v
Rules (HACKING.md, Closing-session scorers: score/scorekit.py): a job with no output, an rc that is not a result of the tool, a failed
pre-read, a missing dump or a skipped class is `cannot tell`, tested before any match, never a pass; a control that is not a pass shuts
the gate of the rows that depend on it; held-out rows are tallied apart from FIT and control rows; every scorer ends with one SUMMARY.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import pathlib  # noqa: E402
import subprocess  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "gen"))          # r4loops (the marks of the loop programs)
import r4lib as L  # noqa: E402
import score_f  # noqa: E402
import score_o4  # noqa: E402
import score_rw  # noqa: E402
import score_t  # noqa: E402
import score_v  # noqa: E402

STAGES = ["p4-o4", "q4-v", "q4-f", "q4-t", "g4-rw"]
MODS = {"q4-v": (score_v, "score_v"), "q4-f": (score_f, "score_f"), "q4-t": (score_t, "score_t")}


def run_stage(stage, d):
    """(text, result) for one stage directory."""
    k = L.Kept(d)
    p = L.load_preds(stage=stage)
    if stage == "p4-o4":
        return score_o4.score(k, p)
    if stage == "g4-rw":
        return score_rw.score(k, p)
    if stage == "q4-v":
        return score_v.score_v(k, p)
    if stage == "q4-f":
        return score_f.score_f(k, p)
    if stage == "q4-t":
        return score_t.score_t(k, p)
    raise SystemExit(f"unknown stage {stage}")


def gate(stage, d):
    """(exit, text): the bridge controls of a stage from its kept files."""
    k = L.Kept(d)
    p = L.load_preds(stage=stage)
    if stage in ("q4-v", "q4-f", "q4-t"):
        mod = MODS[stage][0]
        g, lines = mod.gate_text(k, p)
        code = 0 if g.ok else (1 if g.failed else 2)
        return code, f"gate {stage}: " + ("PASS" if g.ok else ("FAILED: " if g.failed else "CANNOT TELL: ") + "; ".join(g.problems)) + "\n" + "\n".join(lines)
    text, res = run_stage(stage, d)
    g = res.get("gate")
    if g is None:
        # p4-o4 and g4-rw: the stage scorers expose the controls in their result
        ctl = res.get("controls")
        import scorekit as SK
        g = SK.gate(ctl) if ctl else SK.Gate(ok=False, problems=["no control state in the result"])
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
    if a and a[0] == "gate" and len(a) == 3:
        code, text = gate(a[1], a[2])
        print(text)
        return code
    if a and a[0] == "verdict" and len(a) == 2:
        return verdict(a[1])
    if len(a) != 2 or a[0] not in STAGES:
        print(__doc__)
        return 2
    stage, d = a
    r = subprocess.run([str(HERE.parent / "run" / "freeze_r4.sh"), "verify"], capture_output=True, text=True)
    if r.returncode:
        print("REFUSING: the frozen files do not verify:\n" + r.stdout + r.stderr)
        return 3
    try:
        text, _ = run_stage(stage, d)
        print(text)
    except SystemExit as e:
        print(f"REFUSING: {e}")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
