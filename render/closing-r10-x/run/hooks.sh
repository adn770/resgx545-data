# SPDX-License-Identifier: MIT
# run/hooks.sh: r10-x's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory, $args the row's arguments.
# hook_reading NAME: a control's reading, `key=value` words:
#   job=W            tri: the tool's `job:` line (ok, rejected, failed)
#   pixels=N         the number of pixel values on the output's `row N:` lines (probe and tri)
#   drawn=N          tri: `tri WxH #1: N triangle, ...`
#   depth_changed=N  tri --depth: `depth #1: D dwords, N changed, ...`
hook_reading() {
	local f j p d z
	f=$JW/$1.out
	j=$(sed -n 's/^job: \([a-z]*\).*/\1/p' "$f" | head -n 1)
	p=$(grep -E '(^|: )row [0-9]+: ' "$f" | sed 's/^.*row [0-9]*: //' | wc -w | tr -d ' ')
	d=$(sed -n 's/^tri [0-9]*x[0-9]* #1: \([0-9]*\) triangle.*/\1/p' "$f" | head -n 1)
	z=$(sed -n 's/^depth #1: [0-9]* dwords, \([0-9]*\) changed.*/\1/p' "$f" | head -n 1)
	[ -n "$j" ] && printf 'job=%s\n' "$j"
	[ "${p:-0}" -gt 0 ] && printf 'pixels=%s\n' "$p"
	[ -n "$d" ] && printf 'drawn=%s\n' "$d"
	[ -n "$z" ] && printf 'depth_changed=%s\n' "$z"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
# Round 8's r8-geo lost rows to a kernel that rejected the job while the tool still printed a diff
# line: every tri row must say `job: ok`. A probe row must print one pixel row a target row (its
# --height, 64 by default): a probe that ran but printed no image is no reading of the question.
hook_check() {
	local f n h
	f=$JW/$1.out
	case " $args" in
	" tri"*)
		grep -q '^job: ok$' "$f" || echo "$1 read ok without job: ok ($(grep -m 1 '^job:' "$f"))" ;;
	" probe"*)
		h=$(printf '%s\n' "$args" | sed -n 's/.*--height \([0-9]*\).*/\1/p')
		n=$(grep -c ': row [0-9]*: ' "$f")
		[ "$n" = "${h:-64}" ] || echo "$1: $n pixel rows, not ${h:-64}" ;;
	esac
	return 0
}
