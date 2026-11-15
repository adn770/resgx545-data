# SPDX-License-Identifier: MIT
# run/hooks.sh: r25-csc's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory; $args and $knobs are the row's (the runner's loop).
# hook_reading NAME: a control's reading, `key=value` words (every key of its reads: knob)
#   echo=K/N     K `probe NAME: poked ...` lines for the row's N --poke options (t22's echo)
#   o0=0xV       a uniform o0 (2048 of 2048), else o0=mixed
#   hash=0xH     a copy's `target: WxH hash 0xH`
hook_reading() {
	local o h n k
	n=$(printf '%s\n' "$args" | grep -o -- '--poke ' | wc -l | tr -d ' ')
	k=$(grep -c "^probe [^ ]*: poked " "$JW/$1.out")
	case "$args" in probe*) printf 'echo=%s/%s\n' "$k" "$n" ;; esac
	o=$(sed -n 's/^probe [^ ]*: o0 \(0x[0-9a-f]*\) (2048 of 2048)$/\1/p' "$JW/$1.out" | head -n 1)
	[ -z "$o" ] && grep -q "^probe [^ ]*: o0 mixed" "$JW/$1.out" && o=mixed
	[ -n "$o" ] && printf 'o0=%s\n' "$o"
	h=$(sed -n 's/^target: [0-9]*x[0-9]* hash \(0x[0-9a-f]*\)$/\1/p' "$JW/$1.out" | head -n 1)
	[ -n "$h" ] && printf 'hash=%s\n' "$h"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing:
#   a probe row whose echo count is not its poke count (rank-round24.md 2.2: every poke row reads
#   its echo as a premise; a row with no poke must print none)
hook_check() {
	local n k
	case "$args" in
	probe*)
		n=$(printf '%s\n' "$args" | grep -o -- '--poke ' | wc -l | tr -d ' ')
		k=$(grep -c "^probe [^ ]*: poked " "$JW/$1.out")
		[ "$k" = "$n" ] || printf '%s echoed %s of its %s pokes\n' "$1" "$k" "$n" ;;
	esac
	return 0
}
# hook_fault NAME: no fault or hang is planned (#limit 0)
hook_fault() { return 0; }
