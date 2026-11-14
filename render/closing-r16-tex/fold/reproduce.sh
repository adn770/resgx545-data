#!/bin/bash
# SPDX-License-Identifier: MIT
# fold/reproduce.sh: the frozen scorer re-run on the kept stage; the output must be byte-identical
# to the kept out/ATTEMPT/score-ty.txt (r16-tex fold, 2026-11-14).
cd "$(dirname "$0")/.." || exit 1
PY=${PY:-$HOME/src/resgx545/.venv/bin/python}
ATT=out/20261114-090305
if PYTHONDONTWRITEBYTECODE=1 "$PY" score/score.py ty "$ATT/ty" | cmp -s - "$ATT/score-ty.txt"; then
	echo "ty: identical"
else
	echo "ty: DIFFERS"; exit 1
fi
