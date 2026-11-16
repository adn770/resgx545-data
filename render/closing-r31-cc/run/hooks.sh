# SPDX-License-Identifier: MIT
# run/hooks.sh: r31-cc's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory.
#
# rd_words FILE: the `k=v` words of one job's output (t10's text, then regtimeline's block);
# score/score.py's analyse() is the twin of the reading keys (tests/test_session.py holds them
# equal on kept records):
#   diff    the wrong pixels of every `diff: N of` line, summed
#   ivl     the mean sample interval in ns: max(TOTAL, end) / samples
#   cache   CR_CACHE_CTRL (0x0804) in the first sample (before the job: LEAD > 0)
#   idle    CR_EVENT_STATUS (0x012c), bif0 CR_BIF_CTRL (0x0c00), dms0 CR_DMS_CTRL (0x0a74) in the
#           first sample, where sampled
#   se16    CR_USE0_SERV_EVENT (0x0b14) bit 16 in the first sample
# and, for hook_check only: tl (sample lines), cut (1: a line with the wrong field count), tlrc
# (regtimeline's rc), selast (0x0b14 bit 16 in the last sample), seadv (0x0b14 bits 15:0 advance
# over the samples), ms (max(TOTAL, end) in ms)
rd_words() {
	awk '
	function hx(s,   i, c, v) { v = 0; s = tolower(s); sub(/^0x/, "", s); for (i = 1; i <= length(s); i++) { c = index("0123456789abcdef", substr(s, i, 1)); v = v * 16 + c - 1 }; return v }
	/^diff: [0-9]+ of / { diff += $2; nd++; next }
	/^timeline: regs/ {
		if (nreg) { done = 1; next }
		for (i = 3; i <= NF && $i != "samples"; i++) { nreg++; col[$i] = nreg }
		samples = $(i + 1); secs = $(i + 3); end = $(i + 7); tlrc = $(i + 9)
		next
	}
	/^tl / && nreg && !done {
		if (NF != nreg + 2) { cut = 1; done = 1; next }
		ntl++
		if (ntl == 1) {
			if ("0x012c" in col) idle = sprintf("0x%08x", hx($(col["0x012c"] + 2)))
			if ("0x0804" in col) cw = sprintf("0x%08x", hx($(col["0x0804"] + 2)))
			if ("0x0c00" in col) bw = sprintf("0x%08x", hx($(col["0x0c00"] + 2)))
			if ("0x0a74" in col) dw = sprintf("0x%08x", hx($(col["0x0a74"] + 2)))
		}
		if ("0x0b14" in col) {
			v = hx($(col["0x0b14"] + 2)); c = v % 65536
			if (ntl == 1) se16 = int(v / 65536) % 2
			else seadv += (c - pc + 65536) % 65536
			pc = c; selast = int(v / 65536) % 2
		}
	}
	END {
		if (nd) print "diff=" diff
		if (nreg) {
			d = secs * 1e9; if (end + 0 > d) d = end + 0
			if (samples + 0 > 0) print "ivl=" int(d / samples)
			printf "tl=%d\ncut=%d\ntlrc=%s\nms=%d\n", ntl, cut, tlrc, d / 1e6
		}
		if (idle != "") print "idle=" idle
		if (cw != "") print "cache=" cw
		if (bw != "") print "bif0=" bw
		if (dw != "") print "dms0=" dw
		if (se16 != "") { print "se16=" se16; print "selast=" selast; print "seadv=" seadv + 0 }
	}' "$1"
}
# word KEY: one word of the last rd_words (in $RW)
word() { printf '%s\n' "$RW" | sed -n "s/^$1=//p" | head -n 1; }
# hook_reading NAME: a control's reading, `key=value` words (every key of its reads: knob)
hook_reading() {
	local RW
	RW=$(rd_words "$JW/$1.out")
	printf '%s\n' "$RW" | grep -E '^(diff|ivl|idle|cache|se16|bif0|dms0)='
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
# Every row draws exactly and says `tri: N renders ok` (c5: `fill: ok`); its timeline is there,
# whole, with rc 0; and where 0x0b14 is sampled, the tick goes on: bit 16 set in the last sample
# and at least half a count a ms (E009: 0.997; a stop reads bit 16 clear and its count frozen),
# else the stage stops (every stage declares on_stop "end": the session ends).
hook_check() {
	local RW d n ms adv
	RW=$(rd_words "$JW/$1.out")
	grep -Eq '^(tri: [0-9]+ renders ok|fill: ok, .*)$' "$JW/$1.out" || { echo "$1 has no \`tri: N renders ok\` or \`fill: ok\` line"; return 0; }
	d=$(word diff)
	[ "${d:-x}" = 0 ] || { echo "$1 drew ${d:-no diff line} wrong pixels"; return 0; }
	n=$(word tl)
	[ "${n:-0}" -gt 0 ] || { echo "$1 has no regtimeline sample"; return 0; }
	[ "$(word cut)" = 0 ] || { echo "$1's timeline is cut (a line with the wrong field count)"; return 0; }
	[ "$(word tlrc)" = 0 ] || { echo "$1's timeline says rc $(word tlrc)"; return 0; }
	[ -n "$(word se16)" ] || return 0
	ms=$(word ms); adv=$(word seadv)
	[ "$(word selast)" = 1 ] || { echo "$1: CR_USE0_SERV_EVENT bit 16 clear in the last sample (the tick stopped?)"; return 0; }
	[ "${ms:-0}" -lt 50 ] || [ "${adv:-0}" -ge $(( ms / 2 - 5 )) ] || echo "$1: CR_USE0_SERV_EVENT advanced $adv in $ms ms (the tick stopped?)"
	return 0
}
# hook_fault NAME: no row expects a fault or hang (the runner stops on any first)
hook_fault() { return 0; }
