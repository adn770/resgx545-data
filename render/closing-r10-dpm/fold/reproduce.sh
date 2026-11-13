#!/bin/bash
# SPDX-License-Identifier: MIT
# fold/reproduce.sh: the frozen scorer re-run on the kept stage; the output must be byte-identical
# to the kept out/ATTEMPT/score-s6rep.txt (r10-dpm fold, 2026-11-13).
cd "$(dirname "$0")/.." || exit 1
PY=${PY:-$HOME/src/resgx545/.venv/bin/python}
ATT=out/20261113-102513
if PYTHONDONTWRITEBYTECODE=1 "$PY" score/score.py s6rep "$ATT/s6rep" | cmp -s - "$ATT/score-s6rep.txt"; then echo "s6rep: identical"
else echo "s6rep: DIFFERS"; exit 1; fi
