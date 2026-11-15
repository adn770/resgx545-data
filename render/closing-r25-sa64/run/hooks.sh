# SPDX-License-Identifier: MIT
# run/hooks.sh: r25-sa64's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory; $args and $knobs are the row's (the runner's loop).
# hook_reading NAME: a control's reading, `key=value` words (every key of its reads: knob)
#   echo=K/N     K `probe NAME: poked ...` lines for the row's N --poke options (t24's echo)
#   shown=L/M    L `probe NAME: scratch +0x...` lines, M the `scratch M more changed` count (or 0)
hook_reading() {
	local n k l m
	n=$(printf '%s\n' "$args" | grep -o -- '--poke ' | wc -l | tr -d ' ')
	k=$(grep -c "^probe [^ ]*: poked " "$JW/$1.out")
	l=$(grep -c "^probe [^ ]*: scratch +0x" "$JW/$1.out")
	m=$(sed -n 's/^probe [^ ]*: scratch \([0-9]*\) more changed$/\1/p' "$JW/$1.out" | head -n 1)
	case "$args" in probe*) printf 'echo=%s/%s\nshown=%s/%s\n' "$k" "$n" "$l" "${m:-0}" ;; esac
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing:
#   a probe row whose echo count is not its poke count (rank-round24.md 5: every poke row reads
#   its echo as a premise); a print that stopped below 64 scratch lines with a `more changed`
#   line (the tool did not take --scratch-show 64: the row's premise)
hook_check() {
	local n k l m
	case "$args" in
	probe*)
		n=$(printf '%s\n' "$args" | grep -o -- '--poke ' | wc -l | tr -d ' ')
		k=$(grep -c "^probe [^ ]*: poked " "$JW/$1.out")
		[ "$k" = "$n" ] || { printf '%s echoed %s of its %s pokes\n' "$1" "$k" "$n"; return 0; }
		l=$(grep -c "^probe [^ ]*: scratch +0x" "$JW/$1.out")
		m=$(sed -n 's/^probe [^ ]*: scratch \([0-9]*\) more changed$/\1/p' "$JW/$1.out" | head -n 1)
		[ -z "$m" ] || [ "$l" = 64 ] || printf '%s printed %s scratch lines and %s more changed: not --scratch-show 64\n' "$1" "$l" "$m" ;;
	esac
	return 0
}
# hook_fault NAME: no fault or hang is planned (every stage #limit 0)
hook_fault() { return 0; }
