# SPDX-License-Identifier: MIT
# run/hooks.sh: r29-flag's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out and $JW/NAME.dmesg
# are the job's output and kernel-log slice, $W its work directory (the files the tool wrote,
# still there when the hooks run); $STAGE, $args and $class are the runner's; sha is lib_kit.sh's.
# hook_reading NAME: a control's reading, `key=value` words (tables/s0.txt, h1's and h2's controls):
#   job=W       tri, copy: the first `job:` line's word (ok, failed, rejected)
#   hash=H      tri, copy: the first `target: WxH hash H`
#   depthat=A   tri --depth: `depth: A N pages` (the depth buffer's address: f1's knob address)
#   zstore=S    tri --depth-store: sha256 of the first render's store ($W/depth-store.1.bin)
#   tadata=T    --dump-render: the TA data bytes of `render memory to ... (P, T bytes)`
#   pixels=N    probe --pixels: the count of `row Y:` lines
#   scratchat=A probe: `scratch at A` (f1's knob address)
#   o0=present  probe --tri: an `o0` line (the job drew and was read)
hook_reading() {
	local f v
	f=$JW/$1.out
	v=$(sed -n 's/^job: \([a-z]*\).*/\1/p' "$f" | head -n 1); [ -n "$v" ] && printf 'job=%s\n' "$v"
	v=$(sed -n 's/^target: [0-9]*x[0-9]* hash \(0x[0-9a-f]*\).*/\1/p' "$f" | head -n 1); [ -n "$v" ] && printf 'hash=%s\n' "$v"
	v=$(sed -n 's/^depth: \(0x[0-9a-f]*\) [0-9]* pages.*/\1/p' "$f" | head -n 1); [ -n "$v" ] && printf 'depthat=%s\n' "$v"
	[ -f "$W/depth-store.1.bin" ] && printf 'zstore=%s\n' "$(sha "$W/depth-store.1.bin" | cut -d' ' -f1)"
	v=$(sed -n 's/.*render memory to .* ([0-9]*, \([0-9]*\) bytes).*/\1/p' "$f" | head -n 1); [ -n "$v" ] && printf 'tadata=%s\n' "$v"
	v=$(grep -Ec 'row [0-9]+: ' "$f"); [ "$v" -gt 0 ] && printf 'pixels=%s\n' "$v"
	v=$(sed -n 's/.*scratch at \(0x[0-9a-f]*\) .*/\1/p' "$f" | head -n 1); [ -n "$v" ] && printf 'scratchat=%s\n' "$v"
	grep -q ': o0 ' "$f" && printf 'o0=present\n'
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing:
#   a tri or copy row must say `job: ok` and print its `target:` hash (expectdiff's rc 1 is a
#   reading only with them; E934); a probe row must print its pixels (an `o0` or a `row Y:` line).
hook_check() {
	local f
	f=$JW/$1.out
	case "$args" in
	tri* | copy*)
		grep -q '^job: ok' "$f" || echo "$1 read ok without job: ok ($(grep -m 1 '^job:' "$f"))"
		grep -q '^target: [0-9]*x[0-9]* hash 0x' "$f" || echo "$1 read ok without its target hash" ;;
	*)
		grep -q ': o0 ' "$f" || grep -Eq 'row [0-9]+: ' "$f" || echo "$1 read ok without its pixels (no o0 or row line)" ;;
	esac
	return 0
}
# hook_fault NAME: after an expectfault row's fault or hang (its reset and strict health done), a
# reason to stop the stage (rc 24; session.toml's on_stop = end ends the session), or nothing:
#   - any `SGX recovery failed` line in the row's kernel slice (a failed recovery stops the session;
#     no reboot, the user decides);
#   - f1 and f2 plan faults only: the end must be a fault with its kernel `BIF fault S at A` line;
#   - h1 and h2 plan hangs only: the end must be a hang with its kernel `job N hung, recovering`.
hook_fault() {
	local k
	k=$JW/$1.dmesg
	grep -q 'SGX recovery failed' "$k" && { echo "$1: SGX recovery failed ($(grep -m 1 'SGX recovery failed' "$k" | sed 's/.*SGX recovery failed/SGX recovery failed/'))"; return 0; }
	case "$STAGE" in
	f1 | f2)
		[ "$class" = fault ] || { echo "$1 ended $class, not a fault (stage $STAGE plans faults only)"; return 0; }
		grep -Eq 'BIF fault 0x[0-9a-f]+ at 0x[0-9a-f]+' "$k" || echo "$1 faulted without a kernel BIF fault line" ;;
	h1 | h2)
		[ "$class" = hang ] || { echo "$1 ended $class, not a hang (stage $STAGE plans hangs only)"; return 0; }
		grep -Eq 'job [0-9]+ hung, recovering' "$k" || echo "$1 hung without the kernel's hung line" ;;
	*)
		echo "$1 ended $class in stage $STAGE, which plans none" ;;
	esac
	return 0
}
