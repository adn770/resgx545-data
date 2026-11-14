# SPDX-License-Identifier: MIT
# run/hooks.sh: r17-tw's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out is the job's
# output; $STAGE is the runner's stage.
# hook_reading NAME: a control's reading, `key=value` words:
#   pixels=N  tw17 (probe): the count of the probe's `row Y:` lines (32, the 64 x 32 fill)
hook_reading() {
	local p
	case "$STAGE" in
	tw17)
		p=$(grep -Ec 'row [0-9]+: ' "$JW/$1.out")
		[ "$p" -gt 0 ] && printf 'pixels=%s\n' "$p" ;;
	esac
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
#   tw17: an ok row must print its 32 pixel rows and the probe's `scratch at A (1024 KiB)` line
#   (256 pages: every frozen form's farthest read lies inside it). The bit-clear references of the
#   new widths must also print their sentinel, the farthest dword E561's law names on them
#   (texel (W - 1, H - 1); gen/tw17.py sentinel(), tests/test_gen.py): without it the texture at
#   that width is not read as the law says, and its width's bit-14 rows (after it) do not run.
#   session.toml's on_stop = end ends the session.
hook_check() {
	local f n s
	f=$JW/$1.out
	case "$STAGE" in
	tw17)
		n=$(grep -Ec 'row [0-9]+: ' "$f")
		[ "$n" = 32 ] || { echo "$1 read ok without its 32 pixel rows ($n)"; return 0; }
		grep -Eq 'scratch at 0x[0-9a-f]+ \(1024 KiB\)' "$f" || { echo "$1 read ok without its 1024 KiB scratch line"; return 0; }
		case "$1" in
		ref256) s=d0001fff ;;
		ref512h16) s=d0001fff ;;
		ref2048h16) s=d0007fff ;;
		*) s= ;;
		esac
		[ -z "$s" ] || grep -qw -- "$s" "$f" || echo "$1 read ok without its sentinel $s (E561's farthest dword at its width)" ;;
	esac
	return 0
}
# hook_fault: never called (tw17 has no expectfault row; any fault or hang stops it, rc 4).
hook_fault() {
	echo "$1: a fault or hang in tw17, which plans none"
	return 0
}
