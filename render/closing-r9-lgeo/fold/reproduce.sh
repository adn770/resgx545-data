#!/bin/bash
# SPDX-License-Identifier: MIT
# fold/reproduce.sh: added at the fold (2026-11-13), not by the run (fold/ is outside the freeze).
# Checks the freeze (kit/session.py verify), re-runs the frozen scorer (score/score.py) on every
# kept stage of the attempt (out/20261113-080029) and compares its output with the kept
# out/ATT/score-STAGE.txt byte for byte, checks every kept file against the raw sha256 the laptop
# logged (out/ATT/STAGE/raw.sha256: name, size, sha256 before gzip), then prints the post hoc
# readings (q139b_residue.py, q139b_lastflag.py, q139b_images.py).
#   PY=<python3 >= 3.11> bash fold/reproduce.sh > fold/reproduce.out
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-python3}
st=0
"$PY" kit/session.py verify . || st=1
A=out/20261113-080029
tmp=$(mktemp -d "${TMPDIR:-/tmp}/r9m-fold.XXXXXX") || exit 1
trap 'rm -rf "$tmp"' EXIT
for s in tx6 q139b; do
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
echo "== post hoc: the 1280 x 720 residue's headers (fold/q139b_residue.py)"
"$PY" fold/q139b_residue.py "$A"
echo "== post hoc: H-LAST, the last-region flag, on every kept dump (fold/q139b_lastflag.py)"
"$PY" fold/q139b_lastflag.py
echo "== post hoc: H-EVEN with H-LAST on the datasets' kept images (fold/q139b_images.py)"
"$PY" -I fold/q139b_images.py
exit $st
