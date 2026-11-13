# SPDX-License-Identifier: MIT
# run/hooks.sh: r13-tex's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory. Every row is a probe (r10-tex's hooks): a fill probe
# prints 32 `row Y:` lines (64 x 32), sb12's `probe --tri` 64 (64 x 64).
# hook_reading NAME: a control's reading: pixels=N, the count of the probe's `row Y:` lines
hook_reading() {
	local n
	n=$(grep -Ec 'row [0-9]+: ' "$JW/$1.out")
	[ "$n" -gt 0 ] && printf 'pixels=%s\n' "$n"
	return 0
}
# hook_check NAME: the plan's stop rule "the second row without pixel rows": the SECOND row of the
# stage whose output has not its `row Y:` lines (64 for sb12's rows, else 32) stops it (rc 24); the
# first is kept and scored cannot tell
UNPARSED=0
hook_check() {
	local n want=32
	case "$1" in sb12-*) want=64 ;; esac
	n=$(grep -Ec 'row [0-9]+: ' "$JW/$1.out")
	[ "$n" = "$want" ] && return 0
	UNPARSED=$((UNPARSED + 1))
	[ "$UNPARSED" -ge 2 ] && echo "the second output without its $want pixel rows ($1: $n)"
	return 0
}
# hook_fault NAME: no row of this session expects a fault (safe class, #limit 0)
hook_fault() { return 0; }
