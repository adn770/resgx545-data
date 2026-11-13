# SPDX-License-Identifier: MIT
# run/hooks.sh: r13-flag's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out and $JW/NAME.dmesg
# are the job's output and kernel-log slice; $STAGE and $class are the runner's (the stage, and
# the class of the row that just ended: ok, fault or hang).
# hook_reading NAME: a control's reading, `key=value` words:
#   pixels=N  the count of the probe's `row Y:` lines (f1: 32, the 64 x 32 fill; f2: 64)
#   job=W     the tool's first `job:` line: ok, hung, faulted or failed (f3's tri control)
hook_reading() {
	local f n j
	f=$JW/$1.out
	n=$(grep -Ec 'row [0-9]+: ' "$f")
	j=$(sed -n 's/^job: \([a-z]*\).*/\1/p' "$f" | head -n 1)
	[ "$j" = failed ] && grep -m 1 '^job:' "$f" | grep -q 'job hung' && j=hung
	[ "$j" = failed ] && grep -m 1 '^job:' "$f" | grep -q 'job faulted' && j=faulted
	[ "$n" -gt 0 ] && printf 'pixels=%s\n' "$n"
	[ -n "$j" ] && printf 'job=%s\n' "$j"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
#   f1, f2: an ok row must print its pixel rows (32 or 64): a row that cannot be read stops the
#           flagged stage at once.
#   f3:     the control (E413's second v = 7 job) must hang: if it completes, the counter is not
#           there to read and every later row's prediction is void; any row that read ok with a
#           `failed:` line (a probe's `no pixel written`) breaks the sequence's state.
hook_check() {
	local f n want
	f=$JW/$1.out
	case "$STAGE" in
	f1 | f2)
		want=32
		[ "$STAGE" = f2 ] && want=64
		n=$(grep -Ec 'row [0-9]+: ' "$f")
		[ "$n" = "$want" ] || echo "$1 read ok without its $want pixel rows ($n)" ;;
	f3)
		[ "$1" = f3-c-b ] && echo "the control f3-c-b completed: E413's v = 7 pair did not hang on its second job (the counter's premise)"
		grep -q 'failed:' "$f" && echo "$1 read ok with a failed: line ($(grep -m 1 'failed:' "$f" | cut -c1-80))" ;;
	esac
	return 0
}
# hook_fault NAME: after an expected fault or hang row (its reset and strict health done), a
# reason to stop the stage (rc 24), or nothing:
#   - any `SGX recovery failed` line in the row's kernel slice: the first failed recovery stops
#     the stage (handover 2026-11-11: a -110 reset happened once; no reboot, the user decides);
#   - f1, f2: the end must be a fault with its kernel `BIF fault S at A` line (the status and
#     address the scorer reads); a hang there is no planned end;
#   - f3: the end must be a hang with its kernel `job N hung, recovering` line; a fault there is
#     no planned end.
hook_fault() {
	local k
	k=$JW/$1.dmesg
	grep -q 'SGX recovery failed' "$k" && { echo "$1: SGX recovery failed ($(grep -m 1 'SGX recovery failed' "$k" | sed 's/.*SGX recovery failed/SGX recovery failed/'))"; return 0; }
	case "$STAGE" in
	f1 | f2)
		[ "$class" = fault ] || { echo "$1 ended $class, not a fault"; return 0; }
		grep -Eq 'BIF fault 0x[0-9a-f]+ at 0x[0-9a-f]+' "$k" || echo "$1 faulted without a kernel BIF fault line (no status or address to read)" ;;
	f3)
		[ "$class" = hang ] || { echo "$1 ended $class, not a hang"; return 0; }
		grep -Eq 'job [0-9]+ hung, recovering' "$k" || echo "$1 hung without the kernel's hung line" ;;
	esac
	return 0
}
