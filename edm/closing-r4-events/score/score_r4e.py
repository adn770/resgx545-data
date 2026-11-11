#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score_r4e.py STAGE OUTDIR | gate STAGE ROOT | sig FILE...: score one stage of R4-events (kb2, kp, e3p) from what the runner kept
(OUT/ATTEMPT/STAGE/: NAME.json, cases.tsv, stage.json, env.json, stop-*.txt).  Written before the run and frozen (run/freeze_r4e.sh); refuses
unless `run/freeze_r4e.sh verify` passes (skipped under R3_NO_FREEZE_CHECK=1, set by the tests only).  Prints a line a job and one `SUMMARY:`
line.  Standard library only.  The shared readers are score/scorelib.py (the ring, the stop signature, the marks, P3: R3k-events' file), the
verdict words come from score/scorekit.py (resgx545 5a13042 tools/closing/scorekit.py, byte for byte), the engine is score/r4common.py, the
stage scorers are sc_kb2.py, sc_kp.py and sc_e3p.py.  The frozen values are read from predictions/STAGE.tsv, never written here.

`gate STAGE ROOT` exits 0 when the previous stage's own kept stage.json (ROOT/PREV/stage.json) says it finished (exit 0, or 8: a stop rule ended
it, reset and gate exact): derived from kept output only, so restaging never closes it.
"""
import json
import os
import pathlib
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
R4 = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(R4 / "gen"))
import r4layout as L  # noqa: E402
import scorelib as C  # noqa: E402
import sc_kb2  # noqa: E402
import sc_kp  # noqa: E402
import sc_e3p  # noqa: E402

SCORERS = {"kb2": sc_kb2.score_kb2, "kp": sc_kp.score_kp, "e3p": sc_e3p.score_e3p}
GATE_EXITS = (0, 8)


def gate(stage, root):
    """0 when the previous stage finished according to its own kept stage.json."""
    prev = L.GATE_OF.get(stage)
    if not prev:
        print(f"GATE {stage} OPEN (no previous stage)")
        return 0
    try:
        st = json.loads((pathlib.Path(root) / prev / "stage.json").read_text())
    except (OSError, ValueError):
        print(f"GATE {stage} CLOSED: no kept stage.json of {prev} under {root}")
        return 1
    if st.get("exit") in GATE_EXITS:
        print(f"GATE {stage} OPEN: {prev} finished (exit {st.get('exit')}, run {st.get('run')})")
        return 0
    print(f"GATE {stage} CLOSED: {prev} exit {st.get('exit')} ({st.get('why', '')[:80]})")
    return 1


def freeze_problem():
    if os.environ.get("R3_NO_FREEZE_CHECK") == "1":
        return None
    r = subprocess.run([str(R4 / "run" / "freeze_r4e.sh"), "verify"], capture_output=True, text=True)
    return None if r.returncode == 0 else (r.stdout + r.stderr).strip().splitlines()[-1:]


def score(stage, d, base=None):
    S = C.Stage(stage, d, base)
    return S, SCORERS[stage](S)


def main(argv):
    if len(argv) >= 4 and argv[1] == "gate":
        return gate(argv[2], argv[3])
    if len(argv) >= 3 and argv[1] == "sig":
        for f in argv[2:]:
            text = pathlib.Path(f).read_text()
            sm = []
            for part in text.split("\n===\n"):
                r, hc = C.parse_regs_text(part)
                sm.append({"regs": {hex(k): v for k, v in r.items()}, "hc12": hc.get(12)})
            print(f, C.sig_line(C.score_sig(sm)))
        return 0
    if len(argv) < 3 or argv[1] not in SCORERS:
        print("usage: score_r4e.py STAGE OUTDIR | gate STAGE ROOT | sig FILE...")
        return 2
    prob = freeze_problem()
    if prob:
        print(f"REFUSING: the frozen files changed ({prob})")
        return 3
    S, summary = score(argv[1], argv[2])
    for ln in S.lines:
        print(ln)
    print("SUMMARY: " + summary)
    return 0


if __name__ == "__main__":
    sys.exit(main(argv=sys.argv))
