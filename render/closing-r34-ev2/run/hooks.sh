# SPDX-License-Identifier: MIT
# run/hooks.sh: r34-ev2's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs access, no write, no rm, no exit (session.py guard). $JW/NAME.out is the
# job's text.
#
# rd_words NAME: the `k=v` words of one job; score/score.py's analyse() is the twin
# (tests/test_session.py holds them equal):
#   diff    the wrong pixels of every `diff: N of` line, summed (the copies)
#   cok     1 with the copy's `copy: ok,` line
#   img     the green count of the probe's `o0 mixed 0xff203040 xA 0xff00ff00 xG` line
#   ovl     1 with the probe's "scene overflowed the parameter buffer" line, else 0 (probe only)
#   ivl     ns a sample: regtimeline's end / samples, or seconds / samples when end is 0
#   rOFF    the first sample of each sampled register (0x%08x), e.g. r012c
#   bKn     the runs of samples with 0x0748 bit K clear, K = 0..4
# and, for hook_check only: tl (sample lines), cut (1: a line with the wrong field count), tlrc
# (regtimeline's rc), probe (1: a probe job)
rd_words() {
	awk '
	/^diff: [0-9]+ of / { diff += $2; nd++; next }
	/^copy: ok,/ { cok = 1; next }
	/^probe p1139-green: / { probe = 1 }
	/scene overflowed the parameter buffer/ { ovl = 1 }
	/o0 mixed 0xff203040 x[0-9]+ 0xff00ff00 x[0-9]+/ {
		for (i = 1; i <= NF; i++) if ($i == "0xff00ff00") { img = substr($(i + 1), 2) }
		next
	}
	/^timeline: regs/ {
		if (nreg) { done = 1; next }
		for (i = 3; i <= NF && $i != "samples"; i++) {
			nreg++; reg[nreg] = $i; if ($i == "0x0748") k748 = nreg + 2
		}
		samples = $(i + 1); secs = $(i + 3); tend = $(i + 7); tlrc = $(i + 9)
		next
	}
	/^tl / && nreg && !done {
		if (NF != nreg + 2) { cut = 1; done = 1; next }
		if (!ntl) for (j = 1; j <= nreg; j++) first[j] = $(j + 2)
		ntl++
		if (k748) {
			v = tolower($k748); x = 0
			for (c = 1; c <= 8; c++) x = x * 16 + index("0123456789abcdef", substr(v, c, 1)) - 1
			for (b = 0; b < 5; b++) {
				clr = int(x / 2 ^ b) % 2 == 0
				if (clr && !inclr[b]) bn[b]++
				inclr[b] = clr
			}
		}
	}
	END {
		if (nd) print "diff=" diff
		if (cok) print "cok=1"
		if (img != "") print "img=" img
		if (probe) print "ovl=" ovl + 0
		if (nreg) {
			if (tend + 0 > 0 && samples + 0 > 0) print "ivl=" int(tend / samples)
			else if (secs + 0 > 0 && samples + 0 > 0) print "ivl=" int(secs * 1e9 / samples)
			if (ntl) for (j = 1; j <= nreg; j++) print "r" substr(reg[j], 3) "=0x" tolower(first[j])
			if (k748 && ntl) for (b = 0; b < 5; b++) print "b" b "n=" bn[b] + 0
			printf "tl=%d\ncut=%d\ntlrc=%s\n", ntl, cut, tlrc
		}
		print "probe=" probe + 0
	}' "$JW/$1.out"
	return 0
}
# word KEY: one word of the last rd_words (in $RW)
word() { printf '%s\n' "$RW" | sed -n "s/^$1=//p" | head -n 1; }
# hook_reading NAME: a control's reading, `key=value` words (every key of its reads: knob)
hook_reading() {
	local RW
	RW=$(rd_words "$1")
	printf '%s\n' "$RW" | grep -E '^(diff|img|ivl|r[0-9a-f]{4}|b[0-4]n)='
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
# Every row runs under regtimeline and must have its whole timeline with the job's rc; a probe
# row must print its image line, a copy its own check (`copy: ok`, diff 0).
hook_check() {
	local RW d
	RW=$(rd_words "$1")
	[ "$(word tl)" -gt 0 ] 2>/dev/null || { echo "$1 has no regtimeline sample"; return 0; }
	[ "$(word cut)" = 0 ] || { echo "$1's timeline is cut (a line with the wrong field count)"; return 0; }
	if [ "$(word probe)" = 1 ]; then
		[ -n "$(word img)" ] || { echo "$1 printed no o0 image line"; return 0; }
		return 0
	fi
	[ "$(word cok)" = 1 ] || { echo "$1 has no \`copy: ok\` line"; return 0; }
	d=$(word diff)
	[ "${d:-x}" = 0 ] || { echo "$1 copied ${d:-no diff line} wrong pixels"; return 0; }
	[ "$(word tlrc)" = 0 ] || { echo "$1's timeline says rc $(word tlrc)"; return 0; }
	return 0
}
# hook_fault NAME: no row expects a fault or hang (#limit 0: the runner stops on any)
hook_fault() { return 0; }
