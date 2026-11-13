#!/bin/bash
# SPDX-License-Identifier: MIT
# out/fold/reproduce.sh: added at the fold (2026-11-13), not by the run (out/ is outside the
# freeze, so the session still verifies). Re-runs the frozen scorer (score/score.py) on every kept
# stage of the attempt that ran (out/20261113-102730, the only one), compares its output with the
# kept out/ATT/score-STAGE.txt byte for byte, checks every kept file against the raw sha256 the
# laptop logged (STAGE/raw.sha256), then prints the post hoc readings of out/fold/post_*.py.
#   bash out/fold/reproduce.sh > out/fold/reproduce.out
cd "$(dirname "$0")/../.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-python3}
A=out/20261113-102730
tmp=$(mktemp -d "${TMPDIR:-/tmp}/r10t-fold.XXXXXX") || exit 1
trap 'rm -rf "$tmp"' EXIT
st=0
for s in addr3 cube3 t3b srgb2; do
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
done
for p in post_addr post_ties post_edge post_srgb post_srgb_ftz; do
	echo "== out/fold/$p.py"
	"$PY" "out/fold/$p.py" || st=1
done
exit $st
