#!/bin/bash
# SPDX-License-Identifier: MIT
# fold/reproduce.sh: added at the fold (2026-11-13), not by the run (fold/ is outside the freeze).
# Checks the freeze (kit/session.py verify), re-runs the frozen scorer (score/score.py) on every
# kept stage of the attempt (out/20261113-084720) and compares its output with the kept
# out/ATT/score-STAGE.txt byte for byte, checks every kept file against the raw sha256 the laptop
# logged (out/ATT/STAGE/raw.sha256: name, size, sha256 before gzip), then prints the kernel's BIF
# fault lines and any recovery failure of each stage's kept kernel log.
#   PY=<python3 >= 3.11> bash fold/reproduce.sh > fold/reproduce.out
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-python3}
st=0
"$PY" kit/session.py verify . || st=1
A=out/20261113-084720
tmp=$(mktemp -d "${TMPDIR:-/tmp}/r9f-fold.XXXXXX") || exit 1
trap 'rm -rf "$tmp"' EXIT
for s in xf2 tri2 bif; do
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
	echo "$s: kernel lines (BIF fault, recovery failed, banned):"
	grep -E 'BIF fault|recovery failed|banned' "$A/$s/kernel.log" | sed 's/^\[[^]]*\] //'
	grep '^SUMMARY' "$A/score-$s.txt"
done
exit $st
