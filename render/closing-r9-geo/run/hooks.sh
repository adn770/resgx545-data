# SPDX-License-Identifier: MIT
# run/hooks.sh: r9-geo's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory.
# hook_reading NAME: a control's reading: pixels=N (the count of the tool's `row Y:` lines; every
# row prints its pixels with --pixels), jobok=1 when a tri job printed `job: ok` (E934's rejected
# jobs printed pixel rows of 0xdeadbeef too), hash=0x... the target's hash of a tri job
hook_reading() {
	local n h
	n=$(grep -Ec 'row [0-9]+: ' "$JW/$1.out")
	[ "$n" -gt 0 ] && printf 'pixels=%s\n' "$n"
	grep -q '^job: ok' "$JW/$1.out" && printf 'jobok=1\n'
	h=$(sed -n 's/^target: [0-9]*x[0-9]* hash \(0x[0-9a-f]*\)$/\1/p' "$JW/$1.out" | head -n 1)
	[ -n "$h" ] && printf 'hash=%s\n' "$h"
	return 0
}
# hook_check NAME: the plan's stop rule "the second row without pixel rows": the SECOND row of the
# stage whose output has no `row 0:` line, or (a tri job) no `job: ok` line, stops it (rc 24); the
# first is kept and scored cannot tell
UNPARSED=0
hook_check() {
	local bad=0
	grep -Eq 'row 0: ' "$JW/$1.out" || bad=1
	case "$(head -c 4 "$JW/$1.out")" in
	tri:) grep -q '^job: ok' "$JW/$1.out" || bad=1 ;;
	esac
	[ "$bad" = 0 ] && return 0
	UNPARSED=$((UNPARSED + 1))
	[ "$UNPARSED" -ge 2 ] && echo "the second output without pixel rows or job: ok ($1)"
	return 0
}
