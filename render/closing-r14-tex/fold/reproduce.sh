#!/bin/bash
# SPDX-License-Identifier: MIT
# fold/reproduce.sh: the frozen scorer re-run on each kept stage; the output must be byte-identical
# to the kept out/ATTEMPT/score-STAGE.txt (r14-tex fold, 2026-11-14).
cd "$(dirname "$0")/.." || exit 1
PY=${PY:-$HOME/src/resgx545/.venv/bin/python}
ATT=out/20261114-054258
rc=0
for st in srgb4 addr5; do
	if PYTHONDONTWRITEBYTECODE=1 "$PY" score/score.py "$st" "$ATT/$st" | cmp -s - "$ATT/score-$st.txt"; then
		echo "$st: identical"
	else
		echo "$st: DIFFERS"; rc=1
	fi
done
exit $rc
