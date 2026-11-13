#!/bin/bash
# SPDX-License-Identifier: MIT
# fold/reproduce.sh: the frozen scorer re-run on the kept files of the one attempt, compared byte
# for byte with the scores the driver kept; then the post hoc guard scan (fold/posthoc_bounds.py).
#   bash fold/reproduce.sh > fold/reproduce.out
cd "$(dirname "$0")/.." || exit 1
PY=${PY:-python3}
A=out/20261113-215416
for s in q201 q261 far; do
	"$PY" -B score/score.py "$s" "$A/$s" "$A" > "fold/score-$s.reproduce.txt" || exit 1
	if cmp -s "fold/score-$s.reproduce.txt" "$A/score-$s.txt"; then echo "$s: byte-identical"; else echo "$s: DIFFERS"; fi
done
"$PY" -B fold/posthoc_bounds.py > fold/posthoc_bounds.out && grep -E '^(ALL|QUARTER:)' fold/posthoc_bounds.out | cut -c1-120
