# SPDX-License-Identifier: MIT
# run/hooks.sh: r14-isp's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out is the job's
# output; $args and $knobs are the row's args and knob words (the runner's).
# hook_reading NAME: a control's reading, `key=value` words:
#   job=W            the `job:` line's word (ok, rejected, failed)
#   drawn=N          `tri WxH #1: N triangle`
#   pixels=N         the values of the `row N:` lines (--pixels)
#   hash=H           `target: WxH hash H`
#   diff=N           `diff: N of ...`
#   depth_changed=N  `depth #1: D dwords, N changed` (--depth)
hook_reading() {
	local f j n p h d z
	f=$JW/$1.out
	j=$(sed -n 's/^job: \([a-z]*\).*/\1/p' "$f" | head -n 1)
	n=$(sed -n 's/^tri [0-9]*x[0-9]* #1: \([0-9][0-9]*\) triangle.*/\1/p' "$f" | head -n 1)
	p=$(grep -E '^row [0-9]+: ' "$f" | sed 's/^row [0-9]*: //' | wc -w | tr -d ' ')
	h=$(sed -n 's/^target: [0-9]*x[0-9]* hash \(0x[0-9a-f]*\).*/\1/p' "$f" | head -n 1)
	d=$(sed -n 's/^diff: \([0-9][0-9]*\) of .*/\1/p' "$f" | head -n 1)
	z=$(sed -n 's/^depth #1: [0-9]* dwords, \([0-9][0-9]*\) changed.*/\1/p' "$f" | head -n 1)
	[ -n "$j" ] && printf 'job=%s\n' "$j"
	[ -n "$n" ] && printf 'drawn=%s\n' "$n"
	[ "${p:-0}" -gt 0 ] && printf 'pixels=%s\n' "$p"
	[ -n "$h" ] && printf 'hash=%s\n' "$h"
	[ -n "$d" ] && printf 'diff=%s\n' "$d"
	[ -n "$z" ] && printf 'depth_changed=%s\n' "$z"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
#  - every row must say `job: ok` (r8-geo's E934: a rejected job still printed a diff line); in
#    g14 this is the stop at the first poked-viewport row that is not ok (R14-2 a), in clipr at
#    the first int32 row that is not ok (R14-3 a; clipr's on_stop = "end");
#  - every row must print its whole image (--pixels: H rows of W values).
hook_check() {
	local f w h n
	f=$JW/$1.out
	grep -q '^job: ok$' "$f" || echo "$1 read ok without job: ok ($(grep -m 1 '^job:' "$f" || echo 'no job line'))"
	w=$(echo "$args" | sed -n 's/.*--width \([0-9][0-9]*\).*/\1/p')
	h=$(echo "$args" | sed -n 's/.*--height \([0-9][0-9]*\).*/\1/p')
	n=$(grep -E '^row [0-9]+: ' "$f" | sed 's/^row [0-9]*: //' | wc -w | tr -d ' ')
	[ "${n:-0}" = "$((w * h))" ] || echo "$1: ${n:-0} pixel values, not $h rows of $w"
	return 0
}
# hook_fault NAME: no row expects a fault (#limit 0 everywhere): nothing to add
hook_fault() { return 0; }
