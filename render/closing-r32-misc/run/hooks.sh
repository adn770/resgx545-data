# SPDX-License-Identifier: MIT
# run/hooks.sh: r32-misc's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs access, no write, no rm, no exit (session.py guard). $JW/NAME.out is the
# job's text, $JW/snap0.regs and snap9.regs the kit's snapshots before and after it,
# $JW/miscinfo.out the kit's pre:miscinfo read (a row with the word only) and $JW/dmesg.all the
# kernel log the runner read for the job's slice (the whole log up to the job's end).
#
# rd_words NAME: the `k=v` words of one job; score/score.py's analyse() and kicks() are the twins
# (tests/test_session.py holds them equal):
#   diff    the wrong pixels of every `diff: N of` line, summed
#   ivl     the mean sample interval in ns of regtimeline's block: max(TOTAL, end) / samples
#   cache   CR_CACHE_CTRL (0x0804) in snap0 (after the reset, the knobs and pre:miscinfo)
#   cache9  CR_CACHE_CTRL in snap9 (after the job)
#   kicks   the served GETMISCINFO answers the kernel logged (`SGX firmware: core ... answered
#           after N us`) after the last `SGX boot: kicking the EDM` before this row's snap0 mark:
#           the boot's own (sgxfive_ident_ask), and pre:miscinfo's
#   mi      1 when the kit's miscinfo read was served (`GETMISCINFO answered after N us`, `all
#           values match`, no MISMATCH), else 0; absent without the word
# and, for hook_check only: tl (sample lines), cut (1: a line with the wrong field count), tlrc
# (regtimeline's rc), rok (1: `tri: N renders ok`)
rd_words() {
	awk '
	/^diff: [0-9]+ of / { diff += $2; nd++; next }
	/^tri: [0-9]+ renders ok$/ { rok = 1; next }
	/^timeline: regs/ {
		if (nreg) { done = 1; next }
		for (i = 3; i <= NF && $i != "samples"; i++) nreg++
		samples = $(i + 1); secs = $(i + 3); end = $(i + 7); tlrc = $(i + 9)
		next
	}
	/^tl / && nreg && !done { if (NF != nreg + 2) { cut = 1; done = 1; next }; ntl++ }
	END {
		if (nd) print "diff=" diff
		print "rok=" rok + 0
		if (nreg) {
			d = secs * 1e9; if (end + 0 > d) d = end + 0
			if (samples + 0 > 0) print "ivl=" int(d / samples)
			printf "tl=%d\ncut=%d\ntlrc=%s\n", ntl, cut, tlrc
		}
	}' "$JW/$1.out"
	[ -f "$JW/snap0.regs" ] && awk '$1 == "reg" && $2 == "0x0804" && !f { print "cache=" $3; f = 1 }' "$JW/snap0.regs"
	[ -f "$JW/snap9.regs" ] && awk '$1 == "reg" && $2 == "0x0804" && !f { print "cache9=" $3; f = 1 }' "$JW/snap9.regs"
	[ -f "$JW/dmesg.all" ] && awk -v m="resgx545 $PREFIX snap $1 0 " -v r=" $RUN" '
		/SGX boot: kicking the EDM/ { k = 0 }
		/SGX firmware: core .* answered after [0-9]+ us/ { k++ }
		index($0, m) && index($0, r) && !f { print "kicks=" k + 0; f = 1 }' "$JW/dmesg.all"
	[ -f "$JW/miscinfo.out" ] && awk '
		/^GETMISCINFO answered after [0-9]+ us$/ { a = 1 }
		/^all values match$/ { m = 1 }
		/MISMATCH/ { bad = 1 }
		END { print "mi=" (a && m && !bad ? 1 : 0) }' "$JW/miscinfo.out"
	return 0
}
# word KEY: one word of the last rd_words (in $RW)
word() { printf '%s\n' "$RW" | sed -n "s/^$1=//p" | head -n 1; }
# hook_reading NAME: a control's reading, `key=value` words (every key of its reads: knob)
hook_reading() {
	local RW
	RW=$(rd_words "$1")
	printf '%s\n' "$RW" | grep -E '^(diff|ivl|cache|cache9|kicks|mi)='
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
# Every row draws exactly and says `tri: 1 renders ok`; a row under regtimeline has its whole
# timeline with rc 0. Both stages declare on_stop "end": a stop ends the session.
hook_check() {
	local RW d
	RW=$(rd_words "$1")
	[ "$(word rok)" = 1 ] || { echo "$1 has no \`tri: N renders ok\` line"; return 0; }
	d=$(word diff)
	[ "${d:-x}" = 0 ] || { echo "$1 drew ${d:-no diff line} wrong pixels"; return 0; }
	# m2's rows run under regtimeline (gen/make.py): the stage, not the text, says a timeline is due
	if [ "$STAGE" = m2 ]; then
		[ "$(word tl)" -gt 0 ] 2>/dev/null || { echo "$1 has no regtimeline sample"; return 0; }
		[ "$(word cut)" = 0 ] || { echo "$1's timeline is cut (a line with the wrong field count)"; return 0; }
		[ "$(word tlrc)" = 0 ] || { echo "$1's timeline says rc $(word tlrc)"; return 0; }
	fi
	return 0
}
# hook_fault NAME: no row expects a fault or hang (the runner stops on any first)
hook_fault() { return 0; }
