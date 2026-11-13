# SPDX-License-Identifier: MIT
# run/hooks.sh: r10-tex's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory. Every row is a probe (r9-geo's hooks, cut to probes).
# hook_reading NAME: a control's reading: pixels=N, the count of the probe's `row Y:` lines (32
# with --pixels on the 64 x 32 fill)
hook_reading() {
	local n
	n=$(grep -Ec 'row [0-9]+: ' "$JW/$1.out")
	[ "$n" -gt 0 ] && printf 'pixels=%s\n' "$n"
	return 0
}
# hook_check NAME: the plan's stop rule "the second row without pixel rows": the SECOND row of the
# stage whose output has not its 32 `row Y:` lines stops it (rc 24); the first is kept and scored
# cannot tell
UNPARSED=0
hook_check() {
	local n
	n=$(grep -Ec 'row [0-9]+: ' "$JW/$1.out")
	[ "$n" = 32 ] && return 0
	UNPARSED=$((UNPARSED + 1))
	[ "$UNPARSED" -ge 2 ] && echo "the second output without its 32 pixel rows ($1: $n)"
	return 0
}
# hook_fault NAME: no row of this session expects a fault (safe class, #limit 0)
hook_fault() { return 0; }
