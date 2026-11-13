# SPDX-License-Identifier: MIT
# run/hooks.sh: r10-geo's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out is the job's
# output; $args, $knobs and $dbgs are the row's args, knob words and dbg: words (the runner's).
# hook_reading NAME: a control's reading, `key=value` words:
#   job=W      tri: the `job:` line's word (ok, rejected, failed)
#   pixels=N   tri --pixels: the number of pixel values on the `row N:` lines
#   hash=H     tri: `target: WxH hash H`
#   diff=N     tri: `diff: N of ...`
#   dump=T     --dump-render: the TA data bytes of `probe tri: render memory to DIR/tri.{param,tadata}.bin (P, T bytes)`
#   inplace=N  tri --bg-layer: the summary's `N layer texels in place`
#   layer=Y    --bg-layer: the tool's `bg-layer: source 0x3e800000 64x64 RGBA8888, knob Y` line
hook_reading() {
	local f j p h d t i l
	f=$JW/$1.out
	j=$(sed -n 's/^job: \([a-z]*\).*/\1/p' "$f" | head -n 1)
	p=$(grep -E '^row [0-9]+: ' "$f" | sed 's/^row [0-9]*: //' | wc -w | tr -d ' ')
	h=$(sed -n 's/^target: [0-9]*x[0-9]* hash \(0x[0-9a-f]*\).*/\1/p' "$f" | head -n 1)
	d=$(sed -n 's/^diff: \([0-9][0-9]*\) of .*/\1/p' "$f" | head -n 1)
	t=$(sed -n 's/^probe tri: render memory to .* ([0-9]*, \([0-9]*\) bytes).*/\1/p' "$f" | head -n 1)
	i=$(sed -n 's/.*; \([0-9][0-9]*\) layer texels in place, .*/\1/p' "$f" | head -n 1)
	l=$(grep -c '^bg-layer: source 0x3e800000 64x64 RGBA8888, knob Y$' "$f")
	[ -n "$j" ] && printf 'job=%s\n' "$j"
	[ "${p:-0}" -gt 0 ] && printf 'pixels=%s\n' "$p"
	[ -n "$h" ] && printf 'hash=%s\n' "$h"
	[ -n "$d" ] && printf 'diff=%s\n' "$d"
	[ -n "$t" ] && [ "$t" -gt 0 ] && printf 'dump=%s\n' "$t"
	[ -n "$i" ] && printf 'inplace=%s\n' "$i"
	[ "$l" = 1 ] && printf 'layer=Y\n'
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
#  - every row is a tri row and must say `job: ok` (r8-geo's E934: a rejected job still printed a
#    diff line);
#  - a row with the layer's knob words has the tool's bg-layer line (the tool read the knob);
#  - needhash: the SECOND row of the stage without a hash line stops it (r7-geo's rule, q139c).
NOHASH=0
hook_check() {
	local f
	f=$JW/$1.out
	grep -q '^job: ok$' "$f" || { echo "$1 read ok without job: ok ($(grep -m 1 '^job:' "$f"))"; return 0; }
	case " $dbgs " in
	*" render_bg_layer=Y "*)
		grep -q '^bg-layer: source 0x3e800000 64x64 RGBA8888, knob Y$' "$f" || { echo "$1: no bg-layer source line (the tool did not take the layer)"; return 0; } ;;
	esac
	case " $knobs " in
	*" needhash "*)
		grep -Eq '^target: [0-9]+x[0-9]+ hash 0x[0-9a-f]+' "$f" || NOHASH=$((NOHASH + 1))
		[ "$NOHASH" -ge 2 ] && echo "the second row without a hash ($1)" ;;
	esac
	return 0
}
# hook_fault NAME: no row expects a fault (#limit 0 everywhere): nothing to add
hook_fault() { return 0; }
