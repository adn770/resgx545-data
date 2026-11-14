# SPDX-License-Identifier: MIT
# run/hooks.sh: r14-flag's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out and $JW/NAME.dmesg
# are the job's output and kernel-log slice; $STAGE and $class are the runner's (the stage, and
# the class of the row that just ended: ok, fault or hang).
# hook_reading NAME: a control's reading, `key=value` words:
#   pixels=N  f1 (probe): the count of the probe's `row Y:` lines (32, the 64 x 32 fill);
#             f2 (tri --pixels): the count of pixel values on the `row Y:` lines
#   job=W     tri: the `job:` line's word (ok, rejected, failed)
#   hash=H    tri: `target: WxH hash H`
#   diff=N    tri: `diff: N of ...`
#   dump=T    tri --dump-render: the TA data bytes of `probe tri: render memory to DIR/tri.{param,
#             tadata}.bin (P, T bytes)`
hook_reading() {
	local f j p h d t
	f=$JW/$1.out
	case "$STAGE" in
	f1)
		p=$(grep -Ec 'row [0-9]+: ' "$f")
		[ "$p" -gt 0 ] && printf 'pixels=%s\n' "$p" ;;
	f2)
		j=$(sed -n 's/^job: \([a-z]*\).*/\1/p' "$f" | head -n 1)
		p=$(grep -E '^row [0-9]+: ' "$f" | sed 's/^row [0-9]*: //' | wc -w | tr -d ' ')
		h=$(sed -n 's/^target: [0-9]*x[0-9]* hash \(0x[0-9a-f]*\).*/\1/p' "$f" | head -n 1)
		d=$(sed -n 's/^diff: \([0-9][0-9]*\) of .*/\1/p' "$f" | head -n 1)
		t=$(sed -n 's/^probe tri: render memory to .* ([0-9]*, \([0-9]*\) bytes).*/\1/p' "$f" | head -n 1)
		[ -n "$j" ] && printf 'job=%s\n' "$j"
		[ "${p:-0}" -gt 0 ] && printf 'pixels=%s\n' "$p"
		[ -n "$h" ] && printf 'hash=%s\n' "$h"
		[ -n "$d" ] && printf 'diff=%s\n' "$d"
		[ -n "$t" ] && [ "$t" -gt 0 ] && printf 'dump=%s\n' "$t" ;;
	esac
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
#   f1: an ok row must print its 32 pixel rows (a row that cannot be read stops the flagged stage,
#       and session.toml's on_stop = end the session);
#   f2: every row is a tri row and must say `job: ok` (r8-geo's E934: a rejected job still printed
#       a diff line), its target hash and its dump line (the scorer reads the image and the dump).
hook_check() {
	local f n
	f=$JW/$1.out
	case "$STAGE" in
	f1)
		n=$(grep -Ec 'row [0-9]+: ' "$f")
		[ "$n" = 32 ] || echo "$1 read ok without its 32 pixel rows ($n)" ;;
	f2)
		grep -q '^job: ok$' "$f" || { echo "$1 read ok without job: ok ($(grep -m 1 '^job:' "$f"))"; return 0; }
		grep -Eq '^target: [0-9]+x[0-9]+ hash 0x[0-9a-f]+' "$f" || { echo "$1 read ok without its target hash"; return 0; }
		grep -q '^probe tri: render memory to ' "$f" || echo "$1 read ok without its dump line" ;;
	esac
	return 0
}
# hook_fault NAME: after an expected fault or hang row (its reset and strict health done), a
# reason to stop the stage (rc 24), or nothing:
#   - any `SGX recovery failed` line in the row's kernel slice: the first failed recovery stops
#     the stage (handover 2026-11-11: a -110 reset happened once; no reboot, the user decides);
#   - the end must be a fault (no hang is planned: the user's OK is for faults only) with its
#     kernel `BIF fault S at A` line (f1's scorer reads the page; in f2 a fault of another kind is
#     not the planned one).
hook_fault() {
	local k
	k=$JW/$1.dmesg
	grep -q 'SGX recovery failed' "$k" && { echo "$1: SGX recovery failed ($(grep -m 1 'SGX recovery failed' "$k" | sed 's/.*SGX recovery failed/SGX recovery failed/'))"; return 0; }
	[ "$class" = fault ] || { echo "$1 ended $class, not a fault (no hang is planned)"; return 0; }
	grep -Eq 'BIF fault 0x[0-9a-f]+ at 0x[0-9a-f]+' "$k" || echo "$1 faulted without a kernel BIF fault line"
	return 0
}
