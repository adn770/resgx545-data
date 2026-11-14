# SPDX-License-Identifier: MIT
# run/hooks.sh: r19-flag's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err and .dmesg
# are the job's files, $W its work directory (the files the tool wrote, still there when the hooks
# run); $STAGE and $class are the runner's.
# fl_reading NAME: the reading words of a tri row of this stage (fl-ctl's `reads:` keys):
#   job=W    the last `job:` line's word (the closing render's: ok, failed, rejected)
#   ovf=N    the renders whose `tri WxH #K:` line says `overflowed` (the geometry kick: 1)
#   thr=V    the last `reg 0x0624 V` (the TA threshold after the closing render; 0xde = N - 0x22)
#   lists=W  yes when page 6 of $W/tri.1.tadata.bin (the state page of a 1024x768 context,
#            copied after the kick, before the fill) has a non-zero dword, else no
fl_reading() {
	local f v
	f=$JW/$1.out
	v=$(sed -n 's/^job: \([a-z]*\).*/\1/p' "$f" | sed -n '$p')
	[ -n "$v" ] && printf 'job=%s\n' "$v"
	printf 'ovf=%s\n' "$(grep -c '^tri [0-9]*x[0-9]* #[0-9]*: overflowed, ' "$f")"
	v=$(sed -n 's/^reg 0x0624 \(0x[0-9a-f]*\).*/\1/p' "$f" | sed -n '$p')
	[ -n "$v" ] && printf 'thr=%s\n' "$(printf '0x%x' "$v")"
	if [ -f "$W/tri.1.tadata.bin" ]; then
		v=$(dd if="$W/tri.1.tadata.bin" bs=4096 skip=6 count=1 2>/dev/null | od -An -v -tx4 | tr -s ' ' '\n' | grep -vc '^0*$')
		if [ "$v" -gt 0 ]; then printf 'lists=yes\n'; else printf 'lists=no\n'; fi
	fi
	return 0
}
hook_reading() { fl_reading "$1"; }
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24; on_stop = "end"
# ends the session), or nothing. fl-ctl is the stage's control: it must show the whole premise
# (the kick overflowed once, the closing render's threshold is N - 0x22, page 6 held lists before
# any fill) with `job: ok`, else no planned row runs (E934). A junk row that completed must show
# the premise that makes its fill the only difference (job ok, the kick overflowed once, lists
# in page 6 before the fill); its own threshold is a reading, not a stop, so the held-out row
# still runs after a legitimate "ok but different" first row.
hook_check() {
	local r
	r=$(fl_reading "$1" | tr '\n' ' ')
	case "$1" in
	fl-ctl)
		case "$r" in
		*"job=ok "*"ovf=1 "*"thr=0xde "*"lists=yes "*) ;;
		*) echo "$1 read ok without the premise: [$r] (want job=ok ovf=1 thr=0xde lists=yes)" ;;
		esac ;;
	*)
		case "$r" in
		*"job=ok "*"ovf=1 "*"lists=yes "*) ;;
		*) echo "$1 read ok without the premise: [$r] (want job=ok ovf=1 lists=yes)" ;;
		esac ;;
	esac
	return 0
}
# hook_fault NAME: after an expectfault row's fault or hang (its reset and strict health done), a
# reason to stop the stage (rc 24, the session ends), or nothing: any `SGX recovery failed` line in
# its kernel slice; a first render that did not overflow or a fault before the fill was armed (the
# junk is not its cause); an end that is not a BIF fault with its kernel line or a hang the kernel
# recovered (`job N hung, recovering`).
hook_fault() {
	local k o
	k=$JW/$1.dmesg
	o=$JW/$1.out
	grep -q 'SGX recovery failed' "$k" && { echo "$1: SGX recovery failed ($(grep -m 1 'SGX recovery failed' "$k" | sed 's/.*SGX recovery failed/SGX recovery failed/'))"; return 0; }
	grep -q '^tri [0-9]*x[0-9]* #1: overflowed, ' "$o" || { echo "$1 ended $class before the geometry kick's overflow was read (the junk is not its cause)"; return 0; }
	grep -q '^tri: tadata_fill before render 2: ' "$o" || { echo "$1 ended $class before the fill was armed (the junk is not its cause)"; return 0; }
	case "$class" in
	fault) grep -Eq 'BIF fault 0x[0-9a-f]+ at 0x[0-9a-f]+' "$k" || echo "$1 faulted without a kernel BIF fault line" ;;
	hang) grep -Eq 'job [0-9]+ hung, recovering' "$k" || echo "$1 hung without the kernel's hung line" ;;
	*) echo "$1 ended $class, neither a fault nor a hang" ;;
	esac
	return 0
}
