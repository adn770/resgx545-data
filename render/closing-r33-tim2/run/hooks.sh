# SPDX-License-Identifier: MIT
# run/hooks.sh: r33-tim2's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs access, no write, no rm, no exit (session.py guard). $JW/NAME.out is the
# job's text, $JW/snap0.regs and snap9.regs the kit's snapshots before and after it.
#
# rd_words NAME: the `k=v` words of one job; score/score.py's analyse() is the twin
# (tests/test_session.py holds them equal):
#   diff    the wrong pixels of every `diff: N of` line, summed
#   ivl     ns a sample: regtimeline's TOTAL / samples, or the stored rows' mean step when TOTAL
#           is 0
#   ten     1 when every stored 0x0acc sample is a running count (the 8 hex digits begin 01 and
#           bits 23:0 are at most 0x061a80 = 400000, the reload word E1131 read once), else 0
#   ten0, ten9  the same for 0x0acc in snap0 and snap9 (scored, not a premise: the kit's mock
#           snapshots have no 0x0acc)
# and, for hook_check only: tl (sample lines), cut (1: a line with the wrong field count), tlrc
# (regtimeline's rc), rok (1: `tri: N renders ok`)
rd_words() {
	awk '
	/^diff: [0-9]+ of / { diff += $2; nd++; next }
	/^tri: [0-9]+ renders ok$/ { rok = 1; next }
	/^timeline: regs/ {
		if (nreg) { done = 1; next }
		for (i = 3; i <= NF && $i != "samples"; i++) { nreg++; if ($i == "0x0acc") kc = nreg + 2 }
		samples = $(i + 1); secs = $(i + 3); tlrc = $(i + 9); ten = 1
		next
	}
	/^tl / && nreg && !done {
		if (NF != nreg + 2) { cut = 1; done = 1; next }
		if (!ntl) t0 = $2
		t1 = $2; ntl++
		if (kc) { v = tolower($kc); if (substr(v, 1, 2) != "01" || substr(v, 3, 6) > "061a80") ten = 0 }
	}
	END {
		if (nd) print "diff=" diff
		print "rok=" rok + 0
		if (nreg) {
			if (secs + 0 > 0 && samples + 0 > 0) print "ivl=" int(secs * 1e9 / samples)
			else if (ntl > 1) print "ivl=" int((t1 - t0) / (ntl - 1))
			printf "tl=%d\ncut=%d\ntlrc=%s\n", ntl, cut, tlrc
			if (kc && ntl) print "ten=" ten
		}
	}' "$JW/$1.out"
	snapten ten0 "$JW/snap0.regs"
	snapten ten9 "$JW/snap9.regs"
	return 0
}
# snapten KEY FILE: KEY=1 when the snapshot's 0x0acc is a running count, KEY=0 when not, nothing
# without the file or the register
snapten() {
	[ -f "$2" ] && awk -v k="$1" '$1 == "reg" && $2 == "0x0acc" && !f {
		v = tolower($3); f = 1
		print k "=" (substr(v, 1, 4) == "0x01" && substr(v, 5, 6) <= "061a80" ? 1 : 0) }' "$2"
	return 0
}
# word KEY: one word of the last rd_words (in $RW)
word() { printf '%s\n' "$RW" | sed -n "s/^$1=//p" | head -n 1; }
# hook_reading NAME: a control's reading, `key=value` words (every key of its reads: knob)
hook_reading() {
	local RW
	RW=$(rd_words "$1")
	printf '%s\n' "$RW" | grep -E '^(diff|ivl|ten|ten0|ten9)='
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
# Every row draws exactly, says `tri: 1 renders ok` and has its whole timeline with rc 0 (every
# row of both stages runs under regtimeline). Both stages declare on_stop "end".
hook_check() {
	local RW d
	RW=$(rd_words "$1")
	[ "$(word rok)" = 1 ] || { echo "$1 has no \`tri: N renders ok\` line"; return 0; }
	d=$(word diff)
	[ "${d:-x}" = 0 ] || { echo "$1 drew ${d:-no diff line} wrong pixels"; return 0; }
	[ "$(word tl)" -gt 0 ] 2>/dev/null || { echo "$1 has no regtimeline sample"; return 0; }
	[ "$(word cut)" = 0 ] || { echo "$1's timeline is cut (a line with the wrong field count)"; return 0; }
	[ "$(word tlrc)" = 0 ] || { echo "$1's timeline says rc $(word tlrc)"; return 0; }
	return 0
}
# hook_fault NAME: no row expects a fault or hang (the runner stops on any first)
hook_fault() { return 0; }
