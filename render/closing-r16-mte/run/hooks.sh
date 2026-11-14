# SPDX-License-Identifier: MIT
# run/hooks.sh: r16-mte's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out is the job's
# output; $args is the row's args (the runner's).
# hook_reading NAME: a control's reading, `key=value` words:
#   pixels=N   probe --pixels: the values of the `probe P: row N:` lines
#   o0=V       the `probe P: o0 V (N of N)` value of a one-valued image, `mixed` otherwise
hook_reading() {
	local f p o
	f=$JW/$1.out
	p=$(grep -E '^probe [^ ]*: row [0-9]+: ' "$f" | sed 's/^.*row [0-9]*: //' | wc -w | tr -d ' ')
	o=$(sed -n 's/^probe [^ ]*: o0 \(0x[0-9a-f]*\) (.*/\1/p; s/^probe [^ ]*: o0 mixed.*/mixed/p' "$f" | head -n 1)
	[ "${p:-0}" -gt 0 ] && printf 'pixels=%s\n' "$p"
	[ -n "$o" ] && printf 'o0=%s\n' "$o"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24; on_stop = "end"
# ends the session), or nothing:
#  - every row must print its W x H pixel values (the args' --width and --height);
#  - every value must be the program's 0xff00ff00, the background 0xff203040 or the target's
#    sentinel 0xdeadbeef (any other: the clip words did something no model has; stop);
#  - a gate row (g-*) must read one value, 0xff00ff00, over the whole target.
hook_check() {
	local f w h n x o
	f=$JW/$1.out
	w=$(echo "$args" | sed -n 's/.*--width \([0-9][0-9]*\).*/\1/p')
	h=$(echo "$args" | sed -n 's/.*--height \([0-9][0-9]*\).*/\1/p')
	n=$(grep -E '^probe [^ ]*: row [0-9]+: ' "$f" | sed 's/^.*row [0-9]*: //' | wc -w | tr -d ' ')
	[ "${n:-0}" = "$((w * h))" ] || echo "$1: ${n:-0} pixel values, not ${w} x ${h}"
	x=$(grep -E '^probe [^ ]*: row [0-9]+: ' "$f" | sed 's/^.*row [0-9]*: //' | tr ' ' '\n' | grep -v -E '^(ff00ff00|ff203040|deadbeef)?$' | head -n 1)
	[ -z "$x" ] || echo "$1: pixel value 0x$x is none of 0xff00ff00, 0xff203040, 0xdeadbeef"
	case "$1" in
	g-*)
		o=$(sed -n 's/^probe [^ ]*: o0 \(0x[0-9a-f]*\) (\([0-9]*\) of \([0-9]*\))$/\1 \2 \3/p' "$f" | head -n 1)
		[ "$o" = "0xff00ff00 $((w * h)) $((w * h))" ] || echo "$1: the gate image is not 0xff00ff00 over the whole target (${o:-mixed})" ;;
	esac
	return 0
}
# hook_fault NAME: no row expects a fault (#limit 0): nothing to add
hook_fault() { return 0; }
