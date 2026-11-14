#!/bin/bash
# SPDX-License-Identifier: MIT
# fold/reproduce.sh: the frozen scorer re-run on the kept stage; the output must be byte-identical
# to the kept out/ATTEMPT/score-refill.txt (r14-bif fold, 2026-11-14).
cd "$(dirname "$0")/.." || exit 1
PY=${PY:-$HOME/src/resgx545/.venv/bin/python}
ATT=out/20261114-055414
if PYTHONDONTWRITEBYTECODE=1 "$PY" score/score.py refill "$ATT/refill" | cmp -s - "$ATT/score-refill.txt"; then echo "refill: identical"
else echo "refill: DIFFERS"; exit 1; fi
