# SPDX-License-Identifier: MIT
# run/hooks.sh: r14-dpm's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (kit/session.py guard).
#
# rd_words FILE: the `k=v` reading of one job's output (the tool's text and regtimeline's block over
# 0x0748 alone), score/read.py's `words`, in awk: clr, pulses, period (ns), short (tests/test_read.py
# holds the two equal on kept jobs and on the mock's).
rd_words() {
	awk '
	function hx(s,   i, c, v) { v = 0; s = tolower(s); for (i = 1; i <= length(s); i++) { c = index("0123456789abcdef", substr(s, i, 1)); v = v * 16 + c - 1 }; return v }
	function bit(v, k) { return int(v / (2 ^ k)) % 2 }
	/^timeline: regs/ {
		if (nreg) { done = 1; next }
		for (i = 3; i <= NF && $i != "samples"; i++) { nreg++; col[$i] = nreg }
		for (j = i; j <= NF; j++) {
			if ($j == "samples") samples = $(j + 1) + 0
			if ($j == "start") start = $(j + 1) + 0
			if ($j == "end") fin = $(j + 1) + 0
		}
		next
	}
	/^tl / && nreg && !done {
		if (NF != nreg + 2) { cut = 1; done = 1; next }
		n++; t[n] = $2 + 0
		cl[n] = (t[n] >= start) && (1 - bit(hx($(col["0x0748"] + 2)), 2))
	}
	END {
		if (cut || !n || !col["0x0748"] || samples <= 0 || fin <= 0) n = 0
		if (!n) exit
		clr = 0; pul = 0
		for (i = 1; i <= n; i++) if (cl[i]) { clr++; if (i == 1 || !cl[i - 1]) pul++ }
		period = int(fin / samples)
		print "clr=" clr " pulses=" pul " period=" period " short=" (period <= 1000 ? 1 : 0)
	}' "$1"
}
# hook_reading NAME: a control's reading, the `k=v` words of its output
hook_reading() {
	rd_words "$JW/$1.out" | tr ' ' '\n'
	return 0
}
# hook_check NAME: a row's `ctl:KEY=VALUE` words are its control values: one its reading does not
# equal stops the stage (rc 24; plan: the sampler on one register has a period of at most 1000 ns,
# or R-PULSE is not tested). A key the reading lacks is left to the premise (the kit's rc 25: a
# control without its reading).
hook_check() {
	local w k v got rd
	case " $knobs " in *" ctl:"*) ;; *) return 0 ;; esac
	rd=" $(rd_words "$JW/$1.out") "
	for w in $knobs; do
		case "$w" in ctl:*=*) ;; *) continue ;; esac
		k=${w#ctl:}; v=${k#*=}; k=${k%%=*}
		got=$(printf '%s\n' "$rd" | tr ' ' '\n' | sed -n "s/^$k=//p" | head -n 1)
		[ -n "$got" ] || continue
		[ "$got" = "$v" ] || { echo "control $1 reads $k=${got:--} where the frozen value is $v"; return 0; }
	done
	return 0
}
# hook_fault NAME: after an expected fault or hang row; this session plans none
hook_fault() { return 0; }
