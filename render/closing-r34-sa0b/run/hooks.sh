# SPDX-License-Identifier: MIT
# run/hooks.sh: r34-sa0b's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out is the job's output;
# $args is the runner's (the row's arguments).
# hook_reading NAME: a control's reading, `key=value` words (every control is a probe, reads:sa,top):
#   sa=V    the probe's scratch dword 0 (`probe X: scratch +0x000 0xV`)
#   top=V   the most frequent o0 value (`probe X: o0 0xV (...)` or `probe X: o0 mixed 0xV xN ...`)
hook_reading() {
	local f v
	f=$JW/$1.out
	v=$(sed -n 's/^probe [^ ]*: scratch +0x000 \(0x[0-9a-f]\{8\}\)$/\1/p' "$f" | head -n 1); [ -n "$v" ] && printf 'sa=%s\n' "$v"
	v=$(sed -n 's/^probe [^ ]*: o0 \(mixed \)\{0,1\}\(0x[0-9a-f]\{8\}\) .*/\2/p' "$f" | head -n 1); [ -n "$v" ] && printf 'top=%s\n' "$v"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing (E934):
#   probe  an o0 line and no `failed:` line; a writer (bins/w-) or a colour job (bins/k.) also its
#          scratch dword 0
#   tri    `job: ok`, its `target:` hash and `diff: 0 of 4096` (the t10 triangle drew exactly)
#   fill   `fill: ok` and `diff: 0 of 2048` (the t10 fill wrote every pixel)
hook_check() {
	local f
	f=$JW/$1.out
	case "$args" in
	probe*)
		grep -q '^probe [^ ]*: o0 ' "$f" || echo "$1 read ok without its o0 line"
		grep -q '^probe [^ ]*: failed' "$f" && echo "$1 read ok with a failed line"
		case "$args" in
		*/bins/w-*|*/bins/k.bin*)
			grep -q '^probe [^ ]*: scratch +0x000 0x' "$f" || echo "$1 read ok without its scratch dword 0" ;;
		esac ;;
	tri)
		grep -q '^job: ok' "$f" || echo "$1 read ok without job: ok ($(grep -m 1 '^job:' "$f"))"
		grep -q '^target: 64x64 hash 0x' "$f" || echo "$1 read ok without its target hash"
		grep -q '^diff: 0 of 4096' "$f" || echo "$1 did not draw exactly ($(grep -m 1 '^diff:' "$f"))" ;;
	fill)
		grep -q '^fill: ok' "$f" || echo "$1 read ok without fill: ok"
		grep -q '^diff: 0 of 2048' "$f" || echo "$1 did not fill exactly ($(grep -m 1 '^diff:' "$f"))" ;;
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
