# SPDX-License-Identifier: MIT
# run/hooks.sh: r17-zls's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory, $args the row's arguments.
# hook_reading NAME: a control's reading, `key=value` words:
#   job=W            tri: the tool's `job:` line (ok, rejected, failed)
#   pixels=N         the number of pixel values on the output's `row N:` lines
#   drawn=N          tri: `tri WxH #1: N triangle, ...`
#   depth_changed=N  tri --depth: `depth #1: D dwords, N changed, ...`
#   dst_changed=N    tri --depth-store: `depth store #1: D dwords, N changed, ...`
#   sst_changed=N    tri --stencil-store: `stencil store #1: D dwords, N changed, ...`
hook_reading() {
	local f j p d z t s
	f=$JW/$1.out
	j=$(sed -n 's/^job: \([a-z]*\).*/\1/p' "$f" | head -n 1)
	p=$(grep -E '^row [0-9]+: ' "$f" | sed 's/^row [0-9]*: //' | wc -w | tr -d ' ')
	d=$(sed -n 's/^tri [0-9]*x[0-9]* #1: \([0-9]*\) triangle.*/\1/p' "$f" | head -n 1)
	z=$(sed -n 's/^depth #1: [0-9]* dwords, \([0-9]*\) changed.*/\1/p' "$f" | head -n 1)
	t=$(sed -n 's/^depth store #1: [0-9]* dwords, \([0-9]*\) changed.*/\1/p' "$f" | head -n 1)
	s=$(sed -n 's/^stencil store #1: [0-9]* dwords, \([0-9]*\) changed.*/\1/p' "$f" | head -n 1)
	[ -n "$j" ] && printf 'job=%s\n' "$j"
	[ "${p:-0}" -gt 0 ] && printf 'pixels=%s\n' "$p"
	[ -n "$d" ] && printf 'drawn=%s\n' "$d"
	[ -n "$z" ] && printf 'depth_changed=%s\n' "$z"
	[ -n "$t" ] && printf 'dst_changed=%s\n' "$t"
	[ -n "$s" ] && printf 'sst_changed=%s\n' "$s"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
# Every row must say `job: ok` (r8-geo's E934: a rejected job still prints a diff line), and a row
# naming --depth-pages N must have the tool map its buffers at N pages (the odd-size targets of
# zovp2 and zovs2 and every zb20 row rest on the explicit size: HACKING "Known tool weaknesses").
hook_check() {
	local f n
	f=$JW/$1.out
	grep -q '^job: ok$' "$f" || echo "$1 read ok without job: ok ($(grep -m 1 '^job:' "$f"))"
	n=$(printf '%s' "$args" | sed -n 's/.*--depth-pages \([0-9][0-9]*\).*/\1/p')
	if [ -n "$n" ]; then
		grep -q "^depth: 0x[0-9a-f]* $n pages, " "$f" ||
			echo "$1: the tool did not map the depth buffer at $n pages"
	fi
	return 0
}
# hook_fault NAME: after an expected fault or hang row; no row of this session expects one
hook_fault() { return 0; }
