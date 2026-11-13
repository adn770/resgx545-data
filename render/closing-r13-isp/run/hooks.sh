# SPDX-License-Identifier: MIT
# run/hooks.sh: r13-isp's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out is the job's
# output; $args and $knobs are the row's args and knob words (the runner's).
# hook_reading NAME: a control's reading, `key=value` words:
#   job=W      tri: the `job:` line's word (ok, rejected, failed)
#   pixels=N   tri --pixels (`row N:`) or probe --pixels (`probe P: row N:`): the pixel values
#   hash=H     tri: `target: WxH hash H`
#   diff=N     tri: `diff: N of ...`
hook_reading() {
	local f j p h d
	f=$JW/$1.out
	j=$(sed -n 's/^job: \([a-z]*\).*/\1/p' "$f" | head -n 1)
	p=$(grep -E '(^|: )row [0-9]+: ' "$f" | sed 's/^.*row [0-9]*: //' | wc -w | tr -d ' ')
	h=$(sed -n 's/^target: [0-9]*x[0-9]* hash \(0x[0-9a-f]*\).*/\1/p' "$f" | head -n 1)
	d=$(sed -n 's/^diff: \([0-9][0-9]*\) of .*/\1/p' "$f" | head -n 1)
	[ -n "$j" ] && printf 'job=%s\n' "$j"
	[ "${p:-0}" -gt 0 ] && printf 'pixels=%s\n' "$p"
	[ -n "$h" ] && printf 'hash=%s\n' "$h"
	[ -n "$d" ] && printf 'diff=%s\n' "$d"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
#  - a tri row (q261, far) must say `job: ok` (r8-geo's E934: a rejected job still printed a diff
#    line); in far this is the "first job that is not ok" stop of the untested range;
#  - a probe row (q201, all 64 x 64) must print its 64 pixel rows of 64 values.
hook_check() {
	local f n
	f=$JW/$1.out
	case "$args" in
	tri\ *)
		grep -q '^job: ok$' "$f" || echo "$1 read ok without job: ok ($(grep -m 1 '^job:' "$f" || echo 'no job line'))" ;;
	probe\ *)
		n=$(grep -E '^probe [^ ]*: row [0-9]+: ' "$f" | sed 's/^.*row [0-9]*: //' | wc -w | tr -d ' ')
		[ "${n:-0}" = 4096 ] || echo "$1: ${n:-0} pixel values, not 64 rows of 64" ;;
	esac
	return 0
}
# hook_fault NAME: no row expects a fault (#limit 0 everywhere): nothing to add
hook_fault() { return 0; }
