#!/usr/bin/env python3
"""score_s1.py STAGE KEPTDIR [--emit-u FILE]: score one S1 stage from its kept files.

  STAGE    g-e1 g-e2a g-e2b g-e3 g-e4 g-e8 g-e8b g-e5 p-b1 p-c p-g p-b2 p-d p-f
  KEPTDIR  out/STAGE (copied from the laptop's ~/s1-out/STAGE): cases.tsv (with rc and class), NAME.txt.gz, dumps
Refuses to run unless `run/freeze_s1.sh verify STAGE` passes (scorers, predictions, tables, programs, pbdump and probe
as frozen); the predictions are always the frozen predictions/STAGE.tsv.  Prints the per-job table and one `SUMMARY:` line.
Run with the scratch venv (numpy):  ../pixel-faults/.venv/bin/python score/score_s1.py g-e1 out/g-e1
Tests call `run_stage(...)` directly (no CLI, no verification) on landed data.
"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "gen"))
from s1lib import Kept, load_preds  # noqa: E402
import score_geo as G  # noqa: E402
import score_pix as P  # noqa: E402

TABLE = {"g-e1": G.score_e1, "g-e2a": G.score_e2a, "g-e2b": G.score_e2b, "g-e3": G.score_e3, "g-e4": G.score_e4,
         "g-e8": G.score_e8, "g-e8b": G.score_e8b, "g-e5": G.score_e5, "p-b1": P.score_b1, "p-c": P.score_c,
         "p-g": P.score_g, "p-b2": P.score_b2, "p-d": P.score_d, "p-f": P.score_f}


def run_stage(stage, kept_dir, preds_path=None, emit_u=None):
    k = Kept(kept_dir)
    preds = load_preds(preds_path, stage)
    fn = TABLE[stage]
    text, _ = fn(k, preds, emit_u) if stage == "g-e2a" else fn(k, preds)
    return text


def main(a):
    if len(a) < 2 or a[0] not in TABLE or "--preds" in a:
        print(__doc__)
        return 2
    stage, d = a[0], a[1]
    r = subprocess.run([str(HERE.parent / "run" / "freeze_s1.sh"), "verify", stage], capture_output=True, text=True)
    if r.returncode:
        print("REFUSING: the frozen files do not verify:\n" + r.stdout + r.stderr)
        return 3
    emit = a[a.index("--emit-u") + 1] if "--emit-u" in a else None
    try:
        print(run_stage(stage, d, None, emit))
    except SystemExit as e:
        print(f"REFUSING: {e}")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
