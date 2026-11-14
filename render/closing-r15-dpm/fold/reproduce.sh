#!/bin/bash
# SPDX-License-Identifier: MIT
# fold/reproduce.sh: the frozen scorer re-run on the kept stage; the output must be byte-identical
# to the kept out/ATTEMPT/score-pr4.txt (r15-dpm fold, 2026-11-14).
cd "$(dirname "$0")/.." || exit 1
PY=${PY:-$HOME/src/resgx545/.venv/bin/python}
ATT=out/20261114-071243
if PYTHONDONTWRITEBYTECODE=1 "$PY" score/score.py pr4 "$ATT/pr4" | cmp -s - "$ATT/score-pr4.txt"; then echo "pr4: identical"
else echo "pr4: DIFFERS"; exit 1; fi
