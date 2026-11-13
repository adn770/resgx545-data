# SPDX-License-Identifier: MIT
# run/hooks.sh: r8-geo's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory.
# hook_reading NAME: a control's reading: pixels=N, the count of the tool's `row Y:` lines (every
# row of every stage prints its pixels with --pixels; the scorer reads the values themselves)
hook_reading() {
	local n
	n=$(grep -Ec 'row [0-9]+: ' "$JW/$1.out")
	[ "$n" -gt 0 ] && printf 'pixels=%s\n' "$n"
	return 0
}
# hook_check NAME: the plan's stop rule "two unparsed outputs in a stage": the SECOND row of the
# stage whose output has no `row 0:` line stops it (rc 24); the first is kept and scored cannot tell
UNPARSED=0
hook_check() {
	grep -Eq 'row 0: ' "$JW/$1.out" && return 0
	UNPARSED=$((UNPARSED + 1))
	[ "$UNPARSED" -ge 2 ] && echo "the second output without pixel rows ($1)"
	return 0
}
