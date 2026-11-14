#!/bin/bash
# SPDX-License-Identifier: MIT
# fold/reproduce.sh: the frozen scorer re-run on the kept stage; the output must be byte-identical
# to the kept out/ATTEMPT/score-rclip.txt (r16-mte fold, 2026-11-14).
cd "$(dirname "$0")/.." || exit 1
PY=${PY:-$HOME/src/resgx545/.venv/bin/python}
ATT=out/20261114-093233
if PYTHONDONTWRITEBYTECODE=1 "$PY" score/score.py rclip "$ATT/rclip" | cmp -s - "$ATT/score-rclip.txt"; then
	echo "rclip: identical"
else
	echo "rclip: DIFFERS"; exit 1
fi
