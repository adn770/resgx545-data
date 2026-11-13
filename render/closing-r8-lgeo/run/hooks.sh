# SPDX-License-Identifier: MIT
# run/hooks.sh: r8-lgeo's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out is the job's output.
# hook_reading NAME: a control's reading, `key=value` words:
#   rows=N   the probe's pixel rows (`probe NAME: row Y:` lines; tx3, tx4, tx5)
#   hash=H   the tool's `target: WxH hash H` line (zs2, q139)
#   dump=T   the TA data bytes of `probe tri: render memory to DIR/tri.{param,tadata}.bin (P, T bytes)` (q139)
hook_reading() {
	local f h r d
	f=$JW/$1.out
	h=$(sed -n 's/^target: [0-9]*x[0-9]* hash \(0x[0-9a-f]*\).*/\1/p' "$f" | head -n 1)
	r=$(grep -c '^probe [^ ]*: row [0-9]*:' "$f")
	d=$(sed -n 's/^probe tri: render memory to .* ([0-9]*, \([0-9]*\) bytes).*/\1/p' "$f" | head -n 1)
	[ -n "$h" ] && printf 'hash=%s\n' "$h"
	[ "${r:-0}" -gt 0 ] && printf 'rows=%s\n' "$r"
	[ -n "$d" ] && [ "$d" -gt 0 ] && printf 'dump=%s\n' "$d"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
# needhash: the SECOND row of the stage without a hash line stops it (r7-geo's rule);
# needrows: the SECOND probe of the stage without pixel rows stops it.
NOHASH=0
NOROWS=0
hook_check() {
	case " $knobs " in
	*" needhash "*)
		grep -Eq '^target: [0-9]+x[0-9]+ hash 0x[0-9a-f]+' "$JW/$1.out" || NOHASH=$((NOHASH + 1))
		[ "$NOHASH" -ge 2 ] && echo "the second row without a hash ($1)" ;;
	esac
	case " $knobs " in
	*" needrows "*)
		grep -Eq '^probe [^ ]+: row [0-9]+:' "$JW/$1.out" || NOROWS=$((NOROWS + 1))
		[ "$NOROWS" -ge 2 ] && echo "the second probe without pixel rows ($1)" ;;
	esac
	return 0
}
