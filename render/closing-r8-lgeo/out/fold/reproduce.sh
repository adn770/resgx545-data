#!/bin/bash
# SPDX-License-Identifier: MIT
# out/fold/reproduce.sh: added at the fold (2026-11-13), not by the run, under out/ because the kit's
# verify takes every other new file of a frozen session for a change. Checks the freeze
# (kit/session.py verify), re-runs the frozen scorer (score/score.py) on every kept stage of the
# attempt (out/20261113-024441) and compares its output with the kept out/ATT/score-STAGE.txt byte
# for byte, checks every kept file against the raw sha256 the laptop logged (out/ATT/STAGE/
# raw.sha256: name, size, sha256 before gzip), then prints the post hoc readings (zs2_read.py,
# zs2_far.py, tx5_read.py).
#   PY=<python3 >= 3.11> bash out/fold/reproduce.sh > out/fold/reproduce.out
cd "$(dirname "$0")/../.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-python3}
st=0
"$PY" kit/session.py verify . || st=1
A=out/20261113-024441
tmp=$(mktemp -d "${TMPDIR:-/tmp}/r8m-fold.XXXXXX") || exit 1
trap 'rm -rf "$tmp"' EXIT
for s in tx3 tx4 tx5 zs2 q139; do
	"$PY" score/score.py "$s" "$A/$s" > "$tmp/$s.txt"
	if cmp -s "$tmp/$s.txt" "$A/score-$s.txt"; then echo "$s: score output byte-identical to the kept one"
	else echo "$s: score output DIFFERS"; st=1; fi
	n=0; bad=0
	while read -r f _ h; do
		n=$((n + 1))
		if [ -f "$A/$s/$f.gz" ]; then got=$(gunzip -c "$A/$s/$f.gz" | shasum -a 256 | cut -c1-64)
		elif [ -f "$A/$s/$f" ]; then got=$(shasum -a 256 < "$A/$s/$f" | cut -c1-64)
		else got=absent; fi
		[ "$got" = "$h" ] || bad=$((bad + 1))
	done < "$A/$s/raw.sha256"
	echo "$s: $n kept files logged, $bad differ from the laptop's sha256"
	[ "$bad" = 0 ] || st=1
	grep '^SUMMARY' "$A/score-$s.txt"
done
echo "== post hoc: zs2 pixel by pixel (out/fold/zs2_read.py)"
"$PY" out/fold/zs2_read.py "$A"
echo "== post hoc: zs2 far vertices (out/fold/zs2_far.py)"
"$PY" out/fold/zs2_far.py "$A"
echo "== post hoc: tx5's explore rows (out/fold/tx5_read.py)"
"$PY" out/fold/tx5_read.py "$A"
exit $st
