#!/bin/bash
# SPDX-License-Identifier: MIT
# fold/reproduce.sh: added at the fold (2026-11-12), not by the run.  Re-runs the frozen scorer
# (score/score_r7.py, which verifies the freeze first) on every kept stage of the attempt and
# compares its output with the kept out/ATT/score-STAGE.txt byte for byte, prints the verdict lines,
# and checks every kept file against the raw sha256 the laptop logged (out/ATT/STAGE/raw.sha256:
# name, size, sha256 of the file before gzip).  Then Q139's held-out rows: the model files are
# checked against fold/q139_FROZEN.sha256 (committed before the held-out read), the fit is re-run
# (fold/q139_fit.py check, byte-identical to fold/q139_fit.out's first part) and score_dump.py
# q139-heldout's output is compared with fold/q139_heldout.out; last, the post hoc write-order
# check (fold/q139_order_posthoc.py, run after the held-out read).
#   PY=python S7=<t7 sha256> fold/reproduce.sh > fold/reproduce.out
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-python3}
S7=${S7:-$(cut -d' ' -f1 TOOL7.sha256)}
RUN=/Users/jtorra/src/scratch/resgx545/closing7/r7-rp     # where the session ran and scored
tmp=$(mktemp -d "${TMPDIR:-/tmp}/r7rp-fold.XXXXXX") || exit 1
trap 'rm -rf "$tmp"' EXIT
st=0
for att in out/2026*/; do
	a=$(basename "$att")
	for s in $(cat stages.txt); do
		[ -d "$att$s" ] || continue
		"$PY" score/score_r7.py "$s" "$att$s" "$S7" > "$tmp/$s.txt"
		if cmp -s "$tmp/$s.txt" "$att/score-$s.txt"; then echo "$a $s: score output byte-identical to the kept one"
		# p7-rd's first line names the kept p7-rdc directory by its absolute path, the run's
		elif sed "s#$(pwd)/#$RUN/#" "$tmp/$s.txt" | cmp -s - "$att/score-$s.txt"; then
			echo "$a $s: score output byte-identical to the kept one once this copy's path is the run's ($RUN)"
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
	"$PY" score/score_r7.py verdict "$att" "$S7" | sed "s/^/$a /"
done
echo "== Q139 held out (fold/q139_fit.py, committed before the read)"
(cd fold && shasum -a 256 -c q139_FROZEN.sha256) || st=1
"$PY" score/score_dump.py q139-fitdata out/20261112-205431/q139 > "$tmp/fitdata"
cmp -s "$tmp/fitdata" fold/q139_fitdata.out && echo "q139-fitdata: byte-identical to fold/q139_fitdata.out" \
	|| { echo "q139-fitdata: DIFFERS"; st=1; }
"$PY" fold/q139_fit.py check fold/q139_fitdata.out > "$tmp/fit"
cmp -s "$tmp/fit" <(head -n "$(wc -l < "$tmp/fit")" fold/q139_fit.out) \
	&& echo "q139_fit.py check: byte-identical to fold/q139_fit.out" || { echo "q139_fit.py check: DIFFERS"; st=1; }
"$PY" score/score_dump.py q139-heldout out/20261112-205431/q139 "$(cut -d' ' -f1 < <(grep q139-model.json fold/q139_FROZEN.sha256))" \
	fold/q139-model.json > "$tmp/heldout"
cmp -s "$tmp/heldout" fold/q139_heldout.out && echo "q139-heldout: byte-identical to fold/q139_heldout.out" \
	|| { echo "q139-heldout: DIFFERS"; st=1; }
grep '^SUMMARY' fold/q139_heldout.out
echo "== post hoc, after the held-out read: R7-BLK's slot rule under five write orders (fold/q139_order_posthoc.py)"
"$PY" fold/q139_order_posthoc.py > "$tmp/order"
cmp -s "$tmp/order" fold/q139_order_posthoc.out && echo "q139_order_posthoc.py: byte-identical to fold/q139_order_posthoc.out" \
	|| { echo "q139_order_posthoc.py: DIFFERS"; st=1; }
cat fold/q139_order_posthoc.out
rm -f .verify.out
exit $st
