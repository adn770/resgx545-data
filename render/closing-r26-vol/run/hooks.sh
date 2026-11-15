# SPDX-License-Identifier: MIT
# run/hooks.sh: r26-vol's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory; $args and $knobs are the row's (the runner's loop).
# hook_reading NAME: a control's reading, `key=value` words (every key of its reads: knob)
#   o0=0xV     a uniform o0 (2048 of 2048), else o0=mixed
#   rows=N     the `probe NAME: row Y: ...` lines (--pixels: 32)
hook_reading() {
	local o n
	o=$(sed -n 's/^probe [^ ]*: o0 \(0x[0-9a-f]*\) (2048 of 2048)$/\1/p' "$JW/$1.out" | head -n 1)
	[ -z "$o" ] && grep -q "^probe [^ ]*: o0 mixed" "$JW/$1.out" && o=mixed
	[ -n "$o" ] && printf 'o0=%s\n' "$o"
	n=$(grep -c "^probe [^ ]*: row [0-9]*: " "$JW/$1.out")
	case "$args" in probe*) printf 'rows=%s\n' "$n" ;; esac
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing:
#   a probe row without its 32 pixel rows (every row's premise: --pixels over the 64 x 32 fill)
hook_check() {
	local n
	case "$args" in
	probe*)
		n=$(grep -c "^probe [^ ]*: row [0-9]*: " "$JW/$1.out")
		[ "$n" = 32 ] || printf '%s printed %s pixel rows, not 32\n' "$1" "$n" ;;
	esac
	return 0
}
# hook_fault NAME: no fault or hang is planned (every stage #limit 0)
hook_fault() { return 0; }
