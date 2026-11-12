#!/bin/bash
# SPDX-License-Identifier: MIT
# fold/reproduce.sh: added at the fold (2026-11-12), not by the run.  Re-runs the frozen scorer
# (score/score_m.py, freeze 2) on every kept stage of both attempts and compares its output with
# the kept out/ATT/score-STAGE.txt byte for byte, prints the verdict lines, and checks every kept
# file against the raw sha256 the laptop logged (out/ATT/STAGE/raw.sha256: name, size, sha256 of
# the file before gzip).  Then the post hoc readings: E126's pictures against the place rule
# (fold/q289_e126.py) and the q086 images inside and outside the words' grid (fold/q086_extent.py).
#   PY=python S6=<t6 sha256> DATA=<resgx545-data> fold/reproduce.sh > fold/reproduce.out
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-python3}
S6=${S6:-$(cut -d' ' -f1 TOOL6.sha256)}
DATA=${DATA:-$(cd ../.. && pwd)}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/r6m-fold.XXXXXX") || exit 1
trap 'rm -rf "$tmp"' EXIT
st=0
for att in out/2026*/; do
	a=$(basename "$att")
	for s in q289 q287 q086; do
		[ -d "$att$s" ] || continue
		"$PY" score/score_m.py "$s" "$att$s" "$S6" > "$tmp/$s.txt"
		if cmp -s "$tmp/$s.txt" "$att/score-$s.txt"; then echo "$a $s: score output byte-identical to the kept one"
		else echo "$a $s: score output DIFFERS"; st=1; fi
		n=0; bad=0
		while read -r f _ h; do
			n=$((n + 1))
			if [ -f "$att$s/$f.gz" ]; then got=$(gunzip -c "$att$s/$f.gz" | shasum -a 256 | cut -c1-64)
			elif [ -f "$att$s/$f" ]; then got=$(shasum -a 256 < "$att$s/$f" | cut -c1-64)
			else got=absent; fi
			[ "$got" = "$h" ] || bad=$((bad + 1))
		done < "$att$s/raw.sha256"
		echo "$a $s: $n kept files logged, $bad differ from the laptop's sha256"
		[ "$bad" = 0 ] || st=1
	done
	"$PY" score/score_m.py verdict "$att" "$S6" | sed "s/^/$a /"
done
echo "== post hoc: E126's pictures against the place rule (fold/q289_e126.py)"
"$PY" fold/q289_e126.py "$DATA"
echo "== post hoc: the q086 images inside and outside the rectangle the words' grid covers (fold/q086_extent.py)"
"$PY" -B fold/q086_extent.py out/20261112-144153
rm -f .verify.out
exit $st
