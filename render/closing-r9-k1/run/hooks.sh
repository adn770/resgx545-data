# SPDX-License-Identifier: MIT
# run/hooks.sh: r9-k1's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out is the job's
# output; $args and $dbgs are the row's args and dbg: words (the runner's variables).
# hook_reading NAME: a control's reading, `key=value` words:
#   job=W      tri: the `job:` line's word (ok, rejected, failed)
#   hash=H     tri: `target: WxH hash H`
#   diff=N     tri: `diff: N of ...`
#   inplace=N  tri --bg-layer: the summary's `N layer texels in place`
#   layer=Y    --bg-layer: the tool's `bg-layer: source 0x3e800000 64x64 RGBA8888, knob Y` line
#   rows=N     probe --tri --pixels: the number of `probe NAME: row Y:` lines
hook_reading() {
	local f j h d p l r
	f=$JW/$1.out
	j=$(sed -n 's/^job: \([a-z]*\).*/\1/p' "$f" | head -n 1)
	h=$(sed -n 's/^target: [0-9]*x[0-9]* hash \(0x[0-9a-f]*\).*/\1/p' "$f" | head -n 1)
	d=$(sed -n 's/^diff: \([0-9][0-9]*\) of .*/\1/p' "$f" | head -n 1)
	p=$(sed -n 's/.*; \([0-9][0-9]*\) layer texels in place, .*/\1/p' "$f" | head -n 1)
	l=$(grep -c '^bg-layer: source 0x3e800000 64x64 RGBA8888, knob Y$' "$f")
	r=$(grep -c '^probe [A-Za-z0-9_.-]*: row [0-9]*:' "$f")
	[ -n "$j" ] && printf 'job=%s\n' "$j"
	[ -n "$h" ] && printf 'hash=%s\n' "$h"
	[ -n "$d" ] && printf 'diff=%s\n' "$d"
	[ -n "$p" ] && printf 'inplace=%s\n' "$p"
	[ "$l" = 1 ] && printf 'layer=Y\n'
	[ "$r" -gt 0 ] && printf 'rows=%s\n' "$r"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
#  - every tri row says `job: ok` (r8-geo's E934: a rejected job still printed a diff line);
#  - every probe row printed its 64 pixel rows;
#  - a row with the layer's knob words has the tool's bg-layer line (the tool read the knob);
#  - c-rawv, the premise check of the second component (DOUTI0 0x40400801 on the layered
#    background is unmeasured): pa1 must be a function of y alone, at most 4 distinct values in
#    any row of background pixels (the triangle's 0xff00ff00 aside); more stops the stage, and
#    the gates of s1 and s1n stay shut (c-rawv's reading is then missing or wrong).
hook_check() {
	local f n m
	f=$JW/$1.out
	case " $args" in
	" tri"*)
		grep -q '^job: ok$' "$f" || { echo "$1 read ok without job: ok ($(grep -m 1 '^job:' "$f"))"; return 0; } ;;
	" probe"*)
		n=$(grep -c '^probe [A-Za-z0-9_.-]*: row [0-9]*:' "$f")
		[ "$n" = 64 ] || { echo "$1: $n pixel rows, not 64"; return 0; } ;;
	esac
	case " $dbgs " in
	*" render_bg_layer=Y "*)
		grep -q '^bg-layer: source 0x3e800000 64x64 RGBA8888, knob Y$' "$f" || { echo "$1: no bg-layer source line (the tool did not take the layer)"; return 0; } ;;
	esac
	if [ "$1" = c-rawv ]; then
		m=$(awk '/^probe [A-Za-z0-9_.-]*: row [0-9]*:/ { split("", s); k = 0; for (i = 5; i <= NF; i++) if ($i != "ff00ff00" && !($i in s)) { s[$i] = 1; k++ } if (k > w) w = k } END { print w + 0 }' "$f")
		[ "$m" -le 4 ] || echo "c-rawv: pa1 is not a function of y ($m distinct background values in one row): the second component of DOUTI0 0x40400801 is not v"
	fi
	return 0
}
