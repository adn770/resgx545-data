#!/bin/bash
# SPDX-License-Identifier: MIT
# fold/reproduce.sh: the frozen scorer re-run on the kept stage; the output must be byte-identical
# to the kept out/ATTEMPT/score-pr3.txt (r14-dpm fold, 2026-11-14).
cd "$(dirname "$0")/.." || exit 1
PY=${PY:-$HOME/src/resgx545/.venv/bin/python}
ATT=out/20261114-052638
if PYTHONDONTWRITEBYTECODE=1 "$PY" score/score.py pr3 "$ATT/pr3" | cmp -s - "$ATT/score-pr3.txt"; then echo "pr3: identical"
else echo "pr3: DIFFERS"; exit 1; fi
