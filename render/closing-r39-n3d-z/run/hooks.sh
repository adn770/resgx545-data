# SPDX-License-Identifier: MIT
# run/hooks.sh: the hooks of r39-n3d-k and -z (r38-n3c-s3's: emitsk and emitsk14 store what emitsb stores, where it stores it) into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $JW/snap0.regs the registers right before it, $W its work directory (an owntask
# row's results page: $W/own_res.json, fwtask_run.py page's {"page": [1024 dwords]}); $tool is the
# runner's (the row's tool).
#
# own_dw FILE I: dword I of a results page, as 0x%08x (nothing when the page has no dword I)
own_dw() {
	local v
	v=$(tr -d '{}[]":a-z \n' < "$1" | tr ',' '\n' | sed -n "$(( $2 + 1 ))p")
	[ -n "$v" ] && printf '0x%08x\n' "$v"
}
# ta3d I: TA3DCtl dword I (0-3) in the row's snap0 (`ta3dctl 0xOO 0xV`, the kernel's regs file
# while the firmware is loaded); a snap0 without the line (the kit mock's fake regs) falls back to
# r35-sa's kept snap0 (E1144, gen/constants.txt V0-V3; tests/test_gen.py checks they agree)
ta3d() {
	local v
	v=$(sed -n "s/^ta3dctl $(printf '0x%02x' $(( $1 * 4 ))) \(0x[0-9a-f]\{8\}\)$/\1/p" "$JW/snap0.regs" | head -n 1)
	[ -n "$v" ] || case "$1" in 0) v=0x32004000 ;; 1) v=0x32005000 ;; 2) v=0x32002000 ;; 3) v=0x00000000 ;; esac
	printf '%s\n' "$v"
}
# hook_reading NAME: a control's reading (stage post): diff=N of the job's `diff: N of` line
hook_reading() {
	local d
	d=$(sed -n 's/^diff: \([0-9][0-9]*\) of .*/\1/p' "$JW/$1.out" | head -n 1)
	[ -n "$d" ] && printf 'diff=%s\n' "$d"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24; own's on_stop =
# "end" ends the session), or nothing:
#   owntask  (r36-n3's page checks, emitsb's two breadcrumbs added; emitsk's alike) the page was dumped; cmd 0
#            (entry 0 cleared it: one emit), state 2, echo = run id (dword 3); slot 1 = M1 and the
#            run id (entry 0 ran this command), slot 1 dword 2 = X0 (the issuer went on past the
#            emit); slot 5 dword 0 = S1 (entry 1's first store); slot 4 = M4 and the run id (entry 1
#            ran to its end); sa0-sa3 (slot 3) = TA3DCtl dwords 0-3 (else the firmware's
#            attributes changed: r36-n3's stop). Only after an ok end: a job not done is the
#            runner's stop (rc 4), which ends the session. The stage has one row by design.
#   tri      `job: ok` and `diff: 0 of 4096` (the stock firmware drew exactly)
#   fill     `fill: ok` and `diff: 0 of 2048`
hook_check() {
	local f r
	case "$tool" in
	owntask)
		f=$W/own_res.json
		[ -s "$f" ] || { echo "$1: no results page"; return 0; }
		r=$(own_dw "$f" 3)
		[ "$(own_dw "$f" 1)" = 0x00000000 ] || echo "$1: cmd is $(own_dw "$f" 1), not cleared by entry 0"
		[ "$(own_dw "$f" 2)" = 0x00000002 ] || echo "$1: state is $(own_dw "$f" 2), not 2"
		[ "$(own_dw "$f" 5)" = "$r" ] || echo "$1: echo $(own_dw "$f" 5) is not the run id $r"
		[ "$(own_dw "$f" 68)" = 0x5a5a3301 ] && [ "$(own_dw "$f" 69)" = "$r" ] \
			|| echo "$1: slot 1 is $(own_dw "$f" 68) $(own_dw "$f" 69), not entry 0's marker and run id $r"
		[ "$(own_dw "$f" 70)" = 0x5a5a3303 ] || echo "$1: slot 1 dword 2 is $(own_dw "$f" 70), not X0 0x5a5a3303 (past the emit)"
		[ "$(own_dw "$f" 84)" = 0x5a5a3304 ] || echo "$1: slot 5 dword 0 is $(own_dw "$f" 84), not S1 0x5a5a3304 (entry 1's first store)"
		[ "$(own_dw "$f" 80)" = 0x5a5a3302 ] && [ "$(own_dw "$f" 81)" = "$r" ] \
			|| echo "$1: slot 4 is $(own_dw "$f" 80) $(own_dw "$f" 81), not entry 1's marker and run id $r"
		[ "$(own_dw "$f" 76)" = "$(ta3d 0)" ] || echo "$1: sa0 $(own_dw "$f" 76) is not V0 $(ta3d 0): the firmware's attributes changed"
		[ "$(own_dw "$f" 77)" = "$(ta3d 1)" ] || echo "$1: sa1 $(own_dw "$f" 77) is not TA3DCtl dword 1 $(ta3d 1): the firmware's attributes changed"
		[ "$(own_dw "$f" 78)" = "$(ta3d 2)" ] || echo "$1: sa2 $(own_dw "$f" 78) is not V2 $(ta3d 2): the firmware's attributes changed"
		[ "$(own_dw "$f" 79)" = "$(ta3d 3)" ] || echo "$1: sa3 $(own_dw "$f" 79) is not TA3DCtl dword 3 $(ta3d 3): the firmware's attributes changed" ;;
	t30)
		f=$JW/$1.out
		case "$args" in
		tri)
			grep -q '^job: ok' "$f" || echo "$1 read ok without job: ok"
			grep -q '^diff: 0 of 4096' "$f" || echo "$1 did not draw exactly ($(grep -m 1 '^diff:' "$f"))" ;;
		fill)
			grep -q '^fill: ok' "$f" || echo "$1 read ok without fill: ok"
			grep -q '^diff: 0 of 2048' "$f" || echo "$1 did not fill exactly ($(grep -m 1 '^diff:' "$f"))" ;;
		*)
			echo "$1: a row this session does not plan ($args)" ;;
		esac ;;
	*)
		echo "$1: a tool this session does not plan ($tool)" ;;
	esac
	return 0
}
# hook_fault NAME: never reached (#limit 0, no expectfault row: any fault or hang stops, rc 4)
hook_fault() {
	echo "$1 ended $class: no fault or hang is planned"
	return 0
}
