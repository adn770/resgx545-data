#!/usr/bin/env python3
"""score_r1.py STAGE KEPTDIR: score one R1 stage from its kept files.

  STAGE    p-c2 g-u1 g-c1 g-c1f g-t1 g-t2 g-t7 g-u2 g-t5 g-t6
  KEPTDIR  out/STAGE (copied from the laptop's ~/r1-out/STAGE): cases.tsv (rc, class), NAME.txt.gz, dumps
Refuses to run unless `run/freeze_r1.sh verify` passes (scorers, predictions, tables, programs, templates and the
read-only imports as frozen).  Prints the per-job table and one `SUMMARY:` line; g-u1 also re-evaluates the 0x072c gate
from the kept files.
Run with the scratch venv (numpy):  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python score/score_r1.py g-u1 out/g-u1
Tests call `run_stage(...)` directly (no CLI, no verification).
"""
import sys
sys.dont_write_bytecode = True     # the scorers import modules of the data repo: no __pycache__ there

import pathlib  # noqa: E402
import subprocess  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "gen"))
import gate072c  # noqa: E402
import score_geo2 as G  # noqa: E402
import score_q276 as Q  # noqa: E402
from r1lib import Kept, load_preds  # noqa: E402

TABLE = {"p-c2": Q.score_p_c2, "g-u1": G.score_u1, "g-c1": G.score_c1, "g-c1f": G.score_c1f, "g-t1": G.score_t1,
         "g-t2": G.score_t2, "g-t7": G.score_t7, "g-u2": G.score_u2, "g-t5": G.score_t5, "g-t6": G.score_t6}
TRIALS = {"u-ctl-1": 19, "u-ctl-2a": 29}


def gate_report(k: Kept):
    """The gate re-evaluated from the kept files of the two trial jobs (G6 is the runner's: taken as recorded)."""
    lines, state = [], "pass"
    rec = k.d / "gate072c.txt"
    recorded = rec.read_text().strip() if rec.exists() else "(no gate072c.txt kept)"
    for n, u in TRIALS.items():
        c = k.case(n)
        if not c:
            lines.append(f"gate trial {n}: not run")
            state = "untested"
            continue
        ok, why = gate072c.gate_check(k.out(n), k.dmesg(n), c.get("class", ""), u, True)
        lines.append(f"gate trial {n}: {'CLEAN' if ok else 'NOT clean: ' + '; '.join(why)}")
        if not ok:
            state = "fail" if state != "untested" else state
    lines.append(f"gate (offline, G1-G5; G6 is the runner's): {state}; the runner recorded: {recorded}")
    return lines


def run_stage(stage, kept_dir, preds_path=None):
    k = Kept(kept_dir)
    preds = load_preds(preds_path, stage)
    text, _ = TABLE[stage](k, preds)
    if stage == "g-u1":
        text = text + "\n" + "\n".join(gate_report(k))
    return text


def main(a):
    if len(a) != 2 or a[0] not in TABLE:
        print(__doc__)
        return 2
    stage, d = a
    r = subprocess.run([str(HERE.parent / "run" / "freeze_r1.sh"), "verify"], capture_output=True, text=True)
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
