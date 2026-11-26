# SPDX-License-Identifier: MIT
# run/hooks.sh: the hooks of the round 46 addendum sessions r46-n3k-n9 ... -n16 (N3k rows W, LFK,
# LTK, LFK2, LFKP, R, P, R2, P2 with emitsb_sbc43s: command 6's after-read in dwords 224-255 with
# M6 and its run id in slot 6) into the kit's laptop runner (kit/run_stage.sh), sourced by it
# (round 46's hooks unchanged: the plants w9-w16 run job 1 alone, every other stage two jobs).
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $JW/snap0.regs the registers right before it, $W its work directory (the
# results page: $W/own_res.json, fwtask_run.py page's {"page": [1024 dwords]}); $tool and $STAGE
# are the runner's.
#
# own_dw FILE I: dword I of a results page, as 0x%08x (nothing when the page has no dword I)
own_dw() {
	local v
	v=$(tr -d '{}[]":a-z \n' < "$1" | tr ',' '\n' | sed -n "$(( $2 + 1 ))p")
	[ -n "$v" ] && printf '0x%08x\n' "$v"
}
# own_range FILE I N: dwords I to I+N-1 of a results page, one decimal a line
own_range() {
	tr -d '{}[]":a-z \n' < "$1" | tr ',' '\n' | sed -n "$(( $2 + 1 )),$(( $2 + $3 ))p"
}
# ta3d I: TA3DCtl dword I (0-3) in the row's snap0 (`ta3dctl 0xOO 0xV`, the kernel's regs file
# while the firmware is loaded); a snap0 without the line (the kit mock's fake regs) falls back to
# G1 m's kept snap0 (round 42, gen/constants.txt V0-V3; tests/test_gen.py checks they agree)
ta3d() {
	local v
	v=$(sed -n "s/^ta3dctl $(printf '0x%02x' $(( $1 * 4 ))) \(0x[0-9a-f]\{8\}\)$/\1/p" "$JW/snap0.regs" | head -n 1)
	[ -n "$v" ] || case "$1" in 0) v=0x32004000 ;; 1) v=0x32005000 ;; 2) v=0x32002000 ;; 3) v=0x00000000 ;; esac
	printf '%s\n' "$v"
}
# hook_reading NAME: no control row reads (every row is the stage's one owntask row)
hook_reading() {
	return 0
}
# sa_note NAME F: job 1's post sa0-sa3 (slot 3) against TA3DCtl dwords 0-3 and, in a stage with
# command 6 (the land stages and the B rows), the after-read (dwords 224-255) against the pre
# survey (128-159): printed to the runner log, never a stop (n3f design K4: the change is the
# reading)
sa_note() {
	local why=""
	[ "$(own_dw "$2" 76)" = "$(ta3d 0)" ] || why="$why sa0 $(own_dw "$2" 76) is not V0 $(ta3d 0);"
	[ "$(own_dw "$2" 77)" = "$(ta3d 1)" ] || why="$why sa1 $(own_dw "$2" 77) is not TA3DCtl dword 1 $(ta3d 1);"
	[ "$(own_dw "$2" 78)" = "$(ta3d 2)" ] || why="$why sa2 $(own_dw "$2" 78) is not V2 $(ta3d 2);"
	[ "$(own_dw "$2" 79)" = "$(ta3d 3)" ] || why="$why sa3 $(own_dw "$2" 79) is not TA3DCtl dword 3 $(ta3d 3);"
	case "$STAGE" in
	w*|z*) ;;
	*) [ "$(own_range "$2" 224 32)" = "$(own_range "$2" 128 32)" ] || why="$why the after-read (dwords 224-255) is not the pre survey (128-159);" ;;
	esac
	[ -n "$why" ] || return 0
	echo "  $1 (printed, not a stop):$why" >&2
}
# hook_check NAME: after a row that read ok (and passed its gate, where it has one), a reason to
# stop the stage (rc 24; on_stop "end" ends the session), or nothing: the page was dumped; cmd 0,
# state 2, echo = the last job's run id (dword 3); job 1's slot 1 = M1 and its run id, slot 1
# dword 2 = X0, slot 5 dword 0 = S1, slot 4 = M4 and job 1's run id (r36-n3's and N3b's checks,
# B11's); a row with command 6 (the land stages, b5, b6): slot 6 = M6 and the last run id; w* (job
# 1 alone, no gate) and zff2 (one quiet job, no pass after): a BIF_FAULT in snap9 is W-FAULT or B
# failing (design §4.2, §4.3: stop the session); then sa_note.
hook_check() {
	local f r r1 b
	case "$tool" in
	owntask)
		f=$W/own_res.json
		[ -s "$f" ] || { echo "$1: no results page"; return 0; }
		r=$(own_dw "$f" 3)
		r1=$(own_dw "$f" 69)
		[ "$(own_dw "$f" 1)" = 0x00000000 ] || echo "$1: cmd is $(own_dw "$f" 1), not cleared"
		[ "$(own_dw "$f" 2)" = 0x00000002 ] || echo "$1: state is $(own_dw "$f" 2), not 2"
		[ "$(own_dw "$f" 5)" = "$r" ] || echo "$1: echo $(own_dw "$f" 5) is not the run id $r"
		[ "$(own_dw "$f" 68)" = 0x5a5a3301 ] || echo "$1: slot 1 is $(own_dw "$f" 68), not entry 0's marker M1"
		[ "$(own_dw "$f" 70)" = 0x5a5a3303 ] || echo "$1: slot 1 dword 2 is $(own_dw "$f" 70), not X0 0x5a5a3303 (past the emit)"
		[ "$(own_dw "$f" 84)" = 0x5a5a3304 ] || echo "$1: slot 5 dword 0 is $(own_dw "$f" 84), not S1 0x5a5a3304 (entry 1's first store)"
		[ "$(own_dw "$f" 80)" = 0x5a5a3302 ] && [ "$(own_dw "$f" 81)" = "$r1" ] \
			|| echo "$1: slot 4 is $(own_dw "$f" 80) $(own_dw "$f" 81), not entry 1's marker and job 1's run id $r1"
		case "$STAGE" in
		w*|z*)
			b=$(sed -n 's/^reg 0x0c08 \(0x[0-9a-f]\{8\}\)$/\1/p' "$JW/snap9.regs" | head -n 1)
			[ "$b" = 0x00000000 ] || echo "$1: W-FAULT: BIF_FAULT ${b:-unread} in snap9 after job 1 (a pass ran that we did not expect: stop the session for the user)" ;;
		*)
			[ "$(own_dw "$f" 88)" = 0x5a5a3306 ] && [ "$(own_dw "$f" 89)" = "$r" ] \
				|| echo "$1: slot 6 is $(own_dw "$f" 88) $(own_dw "$f" 89), not command 6's marker M6 and the run id $r" ;;
		esac
		sa_note "$1" "$f" ;;
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
