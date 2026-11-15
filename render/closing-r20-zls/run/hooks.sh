# SPDX-License-Identifier: MIT
# run/hooks.sh: r20-zls's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory.
#
# rd_words FILE: the `k=v` reading of one job's output (the tool's text, then regtimeline's
# block), score/score.py's `words` in awk (tests/test_hooks.py holds the two equal):
#   ovf1, ovf2  1 when render 1 (2) overflowed (the tool's `tri WxH #N: overflowed`), 0 when it
#               ended otherwise (geometry only, or checked)
#   thr         0x0624 in the last --regs block (after the final render)
#   nparts      the partial renders: 0x0658 bit 0 rising edges in the timeline
#   peak        the last TA run's peak page status (0x0724 low half, dpm_raise.py's runs())
#   sidx        1 when the last depth store report has 32768+ distinct values (indices), else 0
#   diff        the last reference check's wrong pixels;  inplace  the layer texels in place
#   ssame       1 when the depth store report after render 2 equals the one after render 1 (the
#               text after `depth store #N: `), 0 when it differs (zc-geo's control proxy; the
#               scorer compares the dumps inside the store window)
#   refill      the tool's `refill: render` lines (zr's premise: the host wrote the load buffer)
rd_words() {
	awk '
	function hx(s,   i, c, v) { v = 0; s = tolower(s); sub(/^0x/, "", s); for (i = 1; i <= length(s); i++) { c = index("0123456789abcdef", substr(s, i, 1)); v = v * 16 + c - 1 }; return v }
	/^tri [0-9]+x[0-9]+ #[12]: / {
		k = substr($3, 2, 1) + 0
		if ($4 == "overflowed,") o[k] = 1
		else if (!(k in o) && ($4 == "geometry" || $5 == "triangle,")) o[k] = 0
	}
	/^reg 0x0624 / { thr = sprintf("0x%x", hx($3)); next }
	/^depth store #[0-9]+: / {
		sidx = ($0 ~ /32768\+ distinct/) ? 1 : 0
		k = substr($3, 2) + 0; t = $0; sub(/^depth store #[0-9]+: /, "", t); srep[k] = t
		next
	}
	/^refill: render / { nref++; next }
	/^diff: [0-9]+ of / { diff = $2; next }
	/ layer texels in place/ { if (match($0, /[0-9]+ layer texels in place/)) inpl = substr($0, RSTART, RLENGTH) + 0; next }
	/^timeline: regs/ {
		if (nreg) { done = 1; next }
		for (i = 3; i <= NF && $i != "samples"; i++) { nreg++; col[$i] = nreg }
		next
	}
	/^tl / && nreg && !done {
		if (NF != nreg + 2) { cut = 1; done = 1; next }
		n++
		pr[n] = int(hx($(col["0x0658"] + 2)) % 2); st[n] = hx($(col["0x0724"] + 2)) % 65536
	}
	END {
		out = ""
		if (1 in o) out = out " ovf1=" o[1]
		if (2 in o) out = out " ovf2=" o[2]
		if (thr != "") out = out " thr=" thr
		if (sidx != "") out = out " sidx=" sidx
		if ((1 in srep) && (2 in srep)) out = out " ssame=" ((srep[1] == srep[2]) ? 1 : 0)
		if (nref != "") out = out " refill=" nref
		if (diff != "") out = out " diff=" diff
		if (inpl != "") out = out " inplace=" inpl
		if (!cut && n && col["0x0658"] && col["0x0724"]) {
			np = 0; cur = 0
			for (i = 1; i <= n; i++) {
				if (pr[i]) { if (i == 1 || !pr[i - 1]) { np++; cur = 0 }; continue }
				if (st[i] > cur) cur = st[i]
			}
			out = out " nparts=" np " peak=" sprintf("0x%x", cur)
		}
		sub(/^ /, "", out)
		if (out != "") print out
	}' "$1"
}
# hook_reading NAME: a control's reading, the `k=v` words of its output
hook_reading() {
	rd_words "$JW/$1.out" | tr ' ' '\n'
	return 0
}
# hook_check NAME: a row's `ctl:KEY=VALUE` words are its premise or control values (every geometry
# row: the kick overflowed, the final did not, 0x0624 = N - 0x22 after it; zr: one refill; the
# controls: their frozen readings). One its reading does not equal, or a key a row that is not a control
# lacks, stops the stage (rc 24): a geometry row without its premise is no reading of the
# question (plan section 3); a control's missing key is left to the kit's premise (rc 25).
hook_check() {
	local w k v got rd
	case " $knobs " in *" ctl:"*) ;; *) return 0 ;; esac
	rd=" $(rd_words "$JW/$1.out") "
	for w in $knobs; do
		case "$w" in ctl:*=*) ;; *) continue ;; esac
		k=${w#ctl:}; v=${k#*=}; k=${k%%=*}
		got=$(printf '%s\n' "$rd" | tr ' ' '\n' | sed -n "s/^$k=//p" | head -n 1)
		# a control's missing key is the kit's premise stop (rc 25), any other row's is this one
		[ -n "$got" ] || [ "$sset" != control ] || continue
		[ "$got" = "$v" ] || { echo "$1 reads $k=${got:--} where its premise or control is $v"; return 0; }
	done
	return 0
}
# hook_fault NAME: after an expected fault or hang row; this session plans none
hook_fault() { return 0; }
