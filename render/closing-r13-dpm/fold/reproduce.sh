#!/bin/bash
# SPDX-License-Identifier: MIT
# fold/reproduce.sh: the frozen scorer re-run on the kept stage; the output must be byte-identical
# to the kept out/ATTEMPT/score-pr2.txt (r13-dpm fold, 2026-11-13).
cd "$(dirname "$0")/.." || exit 1
PY=${PY:-$HOME/src/resgx545/.venv/bin/python}
ATT=out/20261113-212348
if PYTHONDONTWRITEBYTECODE=1 "$PY" score/score.py pr2 "$ATT/pr2" | cmp -s - "$ATT/score-pr2.txt"; then echo "pr2: identical"
else echo "pr2: DIFFERS"; exit 1; fi
