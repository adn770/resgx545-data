#!/usr/bin/env python3
"""score_s1.py STAGE KEPTDIR: score one S1b stage from its kept files (file name kept from S1).

  STAGE    p-f g-e4w g-e5 p-d p-b2 g-e8b g-e1 g-e3 p-c
  KEPTDIR  out/STAGE (copied from the laptop's ~/s1b-out/STAGE): cases.tsv (with rc, class and hypothesis group),
           NAME.txt.gz, dumps
Refuses to run unless `run/freeze_s1.sh verify` passes (scorers, predictions, tables, programs, and the read-only
imports from the landed tree and the data repo, as frozen): the frozen predictions are verified at scoring.  Prints
the per-job table and one `SUMMARY:` line.
Run with the scratch venv (numpy):  ~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python score/score_s1.py p-f out/p-f
Tests call `run_stage(...)` directly (no CLI, no verification).
"""
import sys
sys.dont_write_bytecode = True     # the scorers import the data repo's modules: no __pycache__ there

import pathlib  # noqa: E402
import subprocess  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "gen"))
from s1lib import Kept, load_preds  # noqa: E402
import score_geo as G  # noqa: E402
import score_pix as P  # noqa: E402

TABLE = {"p-f": P.score_f, "g-e4w": G.score_e4w, "g-e5": G.score_e5, "p-d": P.score_d_s1b, "p-b2": P.score_b2_s1b,
         "g-e8b": G.score_e8b, "g-e1": G.score_e1_ladder, "g-e3": G.score_e3, "p-c": P.score_c}


def run_stage(stage, kept_dir, preds_path=None):
    k = Kept(kept_dir)
    preds = load_preds(preds_path, stage)
    text, _ = TABLE[stage](k, preds)
    return text


def main(a):
    if len(a) != 2 or a[0] not in TABLE:
        print(__doc__)
        return 2
    stage, d = a
    r = subprocess.run([str(HERE.parent / "run" / "freeze_s1.sh"), "verify", stage], capture_output=True, text=True)
    if r.returncode:
        print("REFUSING: the frozen files do not verify:\n" + r.stdout + r.stderr)
        return 3
    try:
        print(run_stage(stage, d))
    except SystemExit as e:
        print(f"REFUSING: {e}")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
