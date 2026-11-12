#!/bin/bash
# SPDX-License-Identifier: MIT
# fold/reproduce.sh: added at the fold (2026-11-12), not by the run.  Re-runs the frozen scorer
# (score/score_g.py) on every kept stage of the attempt that ran (out/20261112-211113; the first
# attempt, out/20261112-211042, kept no stage directory) and compares its output with the kept
# out/ATT/score-STAGE.txt byte for byte, prints the verdict lines, and checks every kept file
# against the raw sha256 the laptop logged (out/ATT/STAGE/raw.sha256: name, size, sha256 of the
# file before gzip).  Then the post hoc readings: tx row by row (fold/tx_read.py), the depth error
# of zd and zf (fold/depth_read.py), the iterated pa0 of zi (fold/iter_read.py) and zs row by row
# (fold/zs_read.py).  The scorer refuses to run unless run/freeze_g.sh verify passes; that check
# needs bin/t6/sgxfive-test (round 6's t6 binary, left out of the published copy; session_tests.sh
# puts it back from resgx545-data-private's cited/closing7/r7-geo/) and the resgx545 files at the
# freeze's commit.  Without the binary the script checks every session file the freeze names by
# a relative path but bin/t6 against FROZEN.sha256 and PREDICTIONS.sha256 itself, says so, and
# scores with R7G_NO_FREEZE_CHECK=1 (the scorer's switch for that check alone).
#   PY=<python with numpy> fold/reproduce.sh > fold/reproduce.out
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-python3}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/r7g-fold.XXXXXX") || exit 1
trap 'rm -rf "$tmp"' EXIT
st=0
if [ ! -f bin/t6/sgxfive-test ]; then
	n=0; bad=0
	for f in FROZEN.sha256 PREDICTIONS.sha256; do
		while read -r h p; do
			case "$p" in /*|bin/t6/sgxfive-test) continue ;; esac
			n=$((n + 1))
			[ "$(shasum -a 256 < "$p" | cut -c1-64)" = "$h" ] || { bad=$((bad + 1)); echo "frozen file changed: $p"; }
		done < "$f"
	done
	echo "bin/t6/sgxfive-test absent: $n session files of the freeze checked, $bad changed; scored with R7G_NO_FREEZE_CHECK=1"
	[ "$bad" = 0 ] || st=1
	export R7G_NO_FREEZE_CHECK=1
fi
for att in out/2026*/; do
	a=$(basename "$att")
	ls -d "$att"*/ > /dev/null 2>&1 || { echo "$a: no kept stage directory"; continue; }
	for s in xf tx zd zi zf zs; do
		[ -d "$att$s" ] || continue
		"$PY" score/score_g.py "$s" "$att$s" > "$tmp/$s.txt"
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
	"$PY" score/score_g.py verdict "$att" | sed "s/^/$a /"
done
A=out/20261112-211113
echo "== post hoc: tx row by row (fold/tx_read.py)"
"$PY" fold/tx_read.py "$A"
echo "== post hoc: the depth error of zd and zf (fold/depth_read.py)"
"$PY" fold/depth_read.py "$A"
echo "== post hoc: the iterated pa0 of zi (fold/iter_read.py)"
"$PY" fold/iter_read.py "$A"
echo "== post hoc: zs row by row (fold/zs_read.py)"
"$PY" fold/zs_read.py "$A"
rm -f .verify.out
exit $st
