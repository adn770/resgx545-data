# SPDX-License-Identifier: MIT
# run/hooks.sh: r15-tw's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out is the job's
# output; $STAGE is the runner's stage.
# hook_reading NAME: a control's reading, `key=value` words:
#   pixels=N  tw14 (probe): the count of the probe's `row Y:` lines (32, the 64 x 32 fill)
hook_reading() {
	local p
	case "$STAGE" in
	tw14)
		p=$(grep -Ec 'row [0-9]+: ' "$JW/$1.out")
		[ "$p" -gt 0 ] && printf 'pixels=%s\n' "$p" ;;
	esac
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
#   tw14: an ok row must print its 32 pixel rows and the probe's `scratch at A (1024 KiB)` line
#   (256 pages: every frozen model's farthest read lies inside it; a smaller scratch would put
#   the bit-14 rows' reads past it). session.toml's on_stop = end ends the session there.
hook_check() {
	local f n
	f=$JW/$1.out
	case "$STAGE" in
	tw14)
		n=$(grep -Ec 'row [0-9]+: ' "$f")
		[ "$n" = 32 ] || { echo "$1 read ok without its 32 pixel rows ($n)"; return 0; }
		grep -Eq 'scratch at 0x[0-9a-f]+ \(1024 KiB\)' "$f" || echo "$1 read ok without its 1024 KiB scratch line" ;;
	esac
	return 0
}
# hook_fault: never called (tw14 has no expectfault row; any fault or hang stops it, rc 4).
hook_fault() {
	echo "$1: a fault or hang in tw14, which plans none"
	return 0
}
