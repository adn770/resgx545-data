# SPDX-License-Identifier: MIT
# run/hooks.sh: r23-dpm's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it
# (r21-zls's reader with t22b's keep, background and kept-copy lines added). Only reads: no debugfs
# write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are the job's files, $W its
# work directory.
#
# rd_words FILE: the `k=v` reading of one job's output (the tool's text, then regtimeline's
# block), score/score.py's `words` in awk (tests/test_plan.py holds the two equal):
#   ovf1, ovf2  1 when render 1 (2) overflowed (the tool's `tri WxH #N: overflowed`), 0 when it
#               ended otherwise (geometry only, checked, or `target kept`)
#   thr         0x0624 in the last --regs block (after the final render)
#   nparts      the partial renders: 0x0658 bit 0 rising edges in the timeline
#   peak        the last TA run's peak page status (0x0724 low half)
#   sidx        1 when the last depth store report has 32768+ distinct values (indices), else 0
#   diff        the last reference check's wrong pixels
#   refill      the tool's `refill: render` lines (zn's premise: the host wrote the load buffer)
#   tri1, oth1, win1   render 1's check line: triangle, other pixels, wrong inside (rl-c1)
#   chg, red2   render 2's keep line (`tri WxH #2: target kept, X pixels changed, colours ...`):
#               X, and the count of 0xffff0000 among its colours (0 when not listed)
#   kept        render_kept copies made with more than 0 bytes (og: 3, or 2 when the copy right
#               after the close reads empty); gsize, fsize the bytes of the copy after the second
#               context's geometry kick and after its render
rd_words() {
	awk '
	function hx(s,   i, c, v) { v = 0; s = tolower(s); sub(/^0x/, "", s); for (i = 1; i <= length(s); i++) { c = index("0123456789abcdef", substr(s, i, 1)); v = v * 16 + c - 1 }; return v }
	/^tri [0-9]+x[0-9]+ #[12]: / {
		k = substr($3, 2, 1) + 0
		if ($4 == "overflowed,") o[k] = 1
		else if (!(k in o) && ($4 == "geometry" || $4 == "target" || $5 == "triangle,")) o[k] = 0
	}
	/^tri [0-9]+x[0-9]+ #1: (overflowed, )?[0-9]+ triangle, [0-9]+ background, [0-9]+ other; wrong [0-9]+ inside/ {
		t = $0; sub(/^tri [0-9]+x[0-9]+ #1: (overflowed, )?/, "", t); split(t, f, " ")
		tri1 = f[1] + 0; oth1 = f[5] + 0; win1 = f[8] + 0
	}
	/^tri [0-9]+x[0-9]+ #2: (overflowed, )?target kept, [0-9]+ pixels changed, colours/ {
		t = $0; sub(/^.*target kept, /, "", t); chg = t + 0; red2 = 0
		if (match(t, /0xffff0000 [0-9]+/)) red2 = substr(t, RSTART + 11, RLENGTH - 11) + 0
	}
	/^tri: render_kept .*: \/.* \([0-9]+ bytes\)$/ {
		b = $NF; t = $(NF - 1); sub(/^\(/, "", t); b = t + 0
		anyk = 1; if (b > 0) nkept++
		if ($0 ~ /^tri: render_kept after the second context.s geometry kick/) gsize = b
		else if ($0 ~ /^tri: render_kept after the second context.s render/) fsize = b
	}
	/^reg 0x0624 / { thr = sprintf("0x%x", hx($3)); next }
	/^depth store #[0-9]+: / { sidx = ($0 ~ /32768\+ distinct/) ? 1 : 0; next }
	/^refill: render / { nref++; next }
	/^diff: [0-9]+ of / { diff = $2; next }
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
		if (nref != "") out = out " refill=" nref
		if (diff != "") out = out " diff=" diff
		if (tri1 != "") out = out " tri1=" tri1 " oth1=" oth1 " win1=" win1
		if (chg != "") out = out " chg=" chg " red2=" red2
		if (anyk) out = out " kept=" (nkept + 0)
		if (gsize != "") out = out " gsize=" gsize
		if (fsize != "") out = out " fsize=" fsize
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
# hook_check NAME: a row's `ctl:KEY=VALUE` words are its premise (every geometry row: the kick
# overflowed, the final did not, 0x0624 = N - 0x22 after it; zn: one refill; rl-c1: no overflow).
# One its reading does not equal, or a key a row that is not a control lacks, stops the stage (rc
# 24): a geometry row without its premise is no reading of the question (rank-round22 2.3, 2.5);
# a control's missing key is left to the kit's premise (rc 25). og (--ctx2-geometry): the second
# context's geometry kick and closing render were made and the copy after its render holds bytes,
# else the stage stops (no reading of the kick clause). An empty copy right after the close or
# after the kick is counted by the scorer (cannot tell, E1085), never a stop.
hook_check() {
	local w k v got rd
	case " $args " in
	*" --ctx2-geometry "*)
		grep -q '^tri2 [0-9]*x[0-9]* #1: geometry only, the scene left open$' "$JW/$1.out" ||
			{ echo "$1: no geometry kick of the second context (--ctx2-geometry not taken)"; return 0; }
		grep -q '^tri2 [0-9]*x[0-9]* #1: closing render$' "$JW/$1.out" ||
			{ echo "$1: no closing render of the second context"; return 0; }
		grep -q "^tri: render_kept after the second context's render 1: /.* ([1-9][0-9]* bytes)\$" "$JW/$1.out" ||
			echo "$1: no copy after the second context's render (render_keep not taken or render_kept unreadable)"
		return 0
		;;
	esac
	case " $knobs " in *" ctl:"*) ;; *) return 0 ;; esac
	rd=" $(rd_words "$JW/$1.out") "
	for w in $knobs; do
		case "$w" in ctl:*=*) ;; *) continue ;; esac
		k=${w#ctl:}; v=${k#*=}; k=${k%%=*}
		got=$(printf '%s\n' "$rd" | tr ' ' '\n' | sed -n "s/^$k=//p" | head -n 1)
		# a control's missing key is the kit's premise stop (rc 25), any other row's is this one
		[ -n "$got" ] || [ "$sset" != control ] || continue
		[ "$got" = "$v" ] || { echo "$1 reads $k=${got:--} where its premise is $v"; return 0; }
	done
	return 0
}
# hook_fault NAME: after an expected fault or hang row; this session plans none
hook_fault() { return 0; }
