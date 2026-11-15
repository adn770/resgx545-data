# SPDX-License-Identifier: MIT
# run/hooks.sh: r26-sa0's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory. Every row is a `probe --coords` fill: it prints `probe
# NAME: o0 ...` and a `probe NAME: scratch +0xOFF 0xVALUE` line a dword it changed.
# hook_reading NAME: a control's reading: scratch=N, the count of the probe's scratch dword lines
hook_reading() {
	local n
	n=$(grep -Ec '^probe [^ ]+: scratch \+0x[0-9a-f]+ 0x[0-9a-f]{8}$' "$JW/$1.out")
	[ "$n" -gt 0 ] && printf 'scratch=%s\n' "$n"
	return 0
}
# hook_check NAME: the stage's stop rule "the second row without its scratch readout" (a writer
# quad that stored nothing prints none): the SECOND row of the stage whose output has no o0 line
# or no scratch dword line stops it (rc 24); the first is kept and scored cannot tell
UNREAD=0
hook_check() {
	local o s
	o=$(grep -Ec '^probe [^ ]+: o0 ' "$JW/$1.out")
	s=$(grep -Ec '^probe [^ ]+: scratch \+0x' "$JW/$1.out")
	[ "$o" -gt 0 ] && [ "$s" -gt 0 ] && return 0
	UNREAD=$((UNREAD + 1))
	[ "$UNREAD" -ge 2 ] && echo "the second output without its scratch readout ($1: o0 $o, dwords $s)"
	return 0
}
# hook_fault NAME: no fault or hang is planned (every stage #limit 0)
hook_fault() { return 0; }
