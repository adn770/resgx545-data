#!/bin/bash
# SPDX-License-Identifier: MIT
# fold/reproduce.sh: the frozen scorer re-run on the kept stages; each output must be byte-identical
# to the kept out/ATTEMPT/score-STAGE.txt (r9-ldpm fold, 2026-11-13).
cd "$(dirname "$0")/.." || exit 1
PY=${PY:-$HOME/src/resgx545/.venv/bin/python}
ATT=out/20261113-082650
rc=0
for s in a0 m6b w f9b; do
	if "$PY" score/score.py "$s" "$ATT/$s" | cmp -s - "$ATT/score-$s.txt"; then echo "$s: identical"
	else echo "$s: DIFFERS"; rc=1; fi
done
exit $rc
