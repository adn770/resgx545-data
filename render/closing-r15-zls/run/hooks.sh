# SPDX-License-Identifier: MIT
# run/hooks.sh: r15-zls's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
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
# Every row must say `job: ok` (r8-geo's E934: a rejected job still prints a diff line). A row
# poking rd:12 (zp-c-id, E1029's zb-c-id) must have its depth buffer at 0x3e001000 (20 pages,
# base 0x3e000000), its store at 0x3e015000 and print its rd:12 poke line; a row poking rd:13
# (zovl's E411 arrangement: page 12 of the depth buffer) its depth buffer at 0x3e001000 with
# base 0x3e000000 and its rd:13=0xd000 line: gen/z15.py's poked values assume these, so else the
# moves are not the frozen ones and the stage stops (zovl: the session ends, on_stop "end").
hook_check() {
	local f
	f=$JW/$1.out
	grep -q '^job: ok$' "$f" || echo "$1 read ok without job: ok ($(grep -m 1 '^job:' "$f"))"
	case " $args " in
	*" 1:rd:12="*)
		grep -q '^depth: 0x3e001000 20 pages, .*base 0x3e000000,' "$f" ||
			echo "$1: the depth buffer is not at 0x3e001000 (20 pages, base 0x3e000000)"
		grep -q '^depth store: 0x3e015000 20 pages' "$f" ||
			echo "$1: the depth store is not at 0x3e015000"
		grep -q ' before render 1: rd:12=0x' "$f" ||
			echo "$1: no line of the rd:12 poke before render 1" ;;
	*" 1:rd:13="*)
		grep -q '^depth: 0x3e001000 [0-9]* pages, .*base 0x3e000000,' "$f" ||
			echo "$1: the depth buffer is not at 0x3e001000 (base 0x3e000000)"
		grep -q ' before render 1: rd:13=0xd000' "$f" ||
			echo "$1: no line of the rd:13 poke before render 1" ;;
	esac
	return 0
}
# hook_fault NAME: after an expected fault or hang row; no row of this session expects one
hook_fault() { return 0; }
