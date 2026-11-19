# SPDX-License-Identifier: MIT
# run/hooks.sh: r38-n3c-s1's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $JW/snap0.regs the registers right before it, $W its work directory (an owntask
# row's results page: $W/own_res.json, fwtask_run.py page's {"page": [1024 dwords]}); $tool and
# $args are the runner's (the row's).
#
# own_dw FILE I: dword I of a results page, as 0x%08x (nothing when the page has no dword I)
own_dw() {
	local v
	v=$(tr -d '{}[]":a-z \n' < "$1" | tr ',' '\n' | sed -n "$(( $2 + 1 ))p")
	[ -n "$v" ] && printf '0x%08x\n' "$v"
}
# hook_reading NAME: a control's reading (stage post): diff=N of the job's `diff: N of` line
hook_reading() {
	local d
	d=$(sed -n 's/^diff: \([0-9][0-9]*\) of .*/\1/p' "$JW/$1.out" | head -n 1)
	[ -n "$d" ] && printf 'diff=%s\n' "$d"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing:
#   owntask  (r37's page checks for emitsn) the page was dumped; cmd 0 (entry 0 cleared it), state
#            2, echo = run id (dword 3); slot 1 = M1 and the run id, slot 1 dword 2 = X0; slot 4 =
#            M4 and the run id; every other dword of the host's fill (72-79, 82-87) still the
#            fill 0xdeadc0de (emitsn stores nowhere else). Only after an ok end: a job not done is
#            the runner's stop (rc 4). own's on_stop "end" ends the session.
#   rt       (stage tim, th) nothing: the scorer reads the row; a hook stop would run the health
#            pair before the stage's last reset, with the EDM tick stopped by design
#   tri      `job: ok` and `diff: 0 of 4096` (the stock firmware drew exactly)
#   fill     `fill: ok` and `diff: 0 of 2048`
hook_check() {
	local f r i
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
		[ "$(own_dw "$f" 70)" = 0x5a5a3303 ] || echo "$1: slot 1 dword 2 is $(own_dw "$f" 70), not X0 0x5a5a3303"
		[ "$(own_dw "$f" 80)" = 0x5a5a3302 ] && [ "$(own_dw "$f" 81)" = "$r" ] \
			|| echo "$1: slot 4 is $(own_dw "$f" 80) $(own_dw "$f" 81), not done's marker and run id $r"
		i=$(tr -d '{}[]":a-z \n' < "$f" | tr ',' '\n' \
			| awk 'NR >= 73 && NR <= 88 && NR != 81 && NR != 82 && $1 != 3735929054 { printf " %d", NR - 1 }')
		[ -z "$i" ] || echo "$1: dwords$i are not the host's fill 0xdeadc0de (emitsn stores nowhere there)" ;;
	rt) ;;
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
