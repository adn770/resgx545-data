# SPDX-License-Identifier: MIT
# run/hooks.sh: r35-o0's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out is the job's
# output; $args is the runner's (the row's arguments). Every probe row is a t10 `probe --tri pixel
# --pixels` of H `row Y:` lines of W dwords (W = H = --height, 64 or 128); the X row is t10 `fill`.
# hook_reading NAME: a control's reading: pixels=N, the count of the probe's `row Y:` lines
hook_reading() {
	local n
	n=$(grep -Ec '^probe [^ ]*: row [0-9]+: ' "$JW/$1.out")
	[ "$n" -gt 0 ] && printf 'pixels=%s\n' "$n"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing:
#   probe  exactly --height `row Y:` lines and no `failed` line (a P row reads its A' row's
#          leftovers: a group without its image cannot be scored, and the next group's A'
#          would start from an unread state)
#   fill   `fill: ok` and `diff: 0 of 2048` (the t10 fill wrote every pixel)
hook_check() {
	local f n h
	f=$JW/$1.out
	case "$args" in
	probe*)
		h=$(printf '%s\n' "$args" | sed -n 's/.*--height \([0-9][0-9]*\) .*/\1/p')
		n=$(grep -Ec '^probe [^ ]*: row [0-9]+: ' "$f")
		[ "$n" = "$h" ] || echo "$1 printed $n pixel rows, not $h"
		grep -q '^probe [^ ]*: failed' "$f" && echo "$1 read ok with a failed line" ;;
	fill)
		grep -q '^fill: ok' "$f" || echo "$1 read ok without fill: ok"
		grep -q '^diff: 0 of 2048' "$f" || echo "$1 did not fill exactly ($(grep -m 1 '^diff:' "$f"))" ;;
	*)
		echo "$1: a row this session does not plan ($args)" ;;
	esac
	return 0
}
# hook_fault NAME: never reached (no expectfault row; any fault or hang stops the stage)
hook_fault() {
	echo "$1 ended $class in a safe stage"
	return 0
}
