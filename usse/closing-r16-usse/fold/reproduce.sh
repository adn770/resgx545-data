#!/bin/bash
# SPDX-License-Identifier: MIT
# fold/reproduce.sh: the frozen scorer re-run on the kept files of attempt 20261114-092913;
# each output must equal the kept out/ATT/score-STAGE.txt byte for byte.
cd "$(dirname "$0")/.." || exit 1
ATT=out/20261114-092913
rc=0
for s in uadd utest urpt; do
	python3 -B score/score.py "$s" "$ATT/$s" > "${TMPDIR:-/tmp}/r16u-score-$s.txt"
	if cmp -s "${TMPDIR:-/tmp}/r16u-score-$s.txt" "$ATT/score-$s.txt"; then echo "$s: identical"
	else echo "$s: DIFFERS"; rc=1; fi
done
exit $rc
