# SPDX-License-Identifier: MIT
# run/hooks.sh: r34-q010's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out is the job's output;
# $args is the runner's (the row's arguments).
# hook_reading NAME: a control's reading, `key=value` words (every control is a copy, reads:job,hash):
#   job=W       the first `job:` line's word (ok, failed, rejected)
#   hash=H      the first `target: WxH hash H`
hook_reading() {
	local f v
	f=$JW/$1.out
	v=$(sed -n 's/^job: \([a-z]*\).*/\1/p' "$f" | head -n 1); [ -n "$v" ] && printf 'job=%s\n' "$v"
	v=$(sed -n 's/^target: [0-9]*x[0-9]* hash \(0x[0-9a-f]*\).*/\1/p' "$f" | head -n 1); [ -n "$v" ] && printf 'hash=%s\n' "$v"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing (E934):
#   copy  `job: ok` and its `target:` hash (expectdiff's rc 1 is a reading only with them)
#   tri   `job: ok`, its `target:` hash and `diff: 0 of 4096` (the health triangle drew exactly)
#   fill  `fill: ok` (the health fill wrote every dword)
hook_check() {
	local f
	f=$JW/$1.out
	case "$args" in
	copy*)
		grep -q '^job: ok' "$f" || echo "$1 read ok without job: ok ($(grep -m 1 '^job:' "$f"))"
		grep -q '^target: [0-9]*x[0-9]* hash 0x' "$f" || echo "$1 read ok without its target hash" ;;
	tri)
		grep -q '^job: ok' "$f" || echo "$1 read ok without job: ok ($(grep -m 1 '^job:' "$f"))"
		grep -q '^target: 64x64 hash 0x' "$f" || echo "$1 read ok without its target hash"
		grep -q '^diff: 0 of 4096' "$f" || echo "$1 did not draw exactly ($(grep -m 1 '^diff:' "$f"))" ;;
	fill)
		grep -q '^fill: ok' "$f" || echo "$1 read ok without fill: ok" ;;
	*)
		echo "$1: a row this session does not plan ($args)" ;;
	esac
	return 0
}
# hook_fault NAME: never reached (no expectfault row; any fault or hang stops the stage, rc 4)
hook_fault() {
	echo "$1 ended $class in a safe stage"
	return 0
}
