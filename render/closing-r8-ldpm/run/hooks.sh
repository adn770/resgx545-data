# SPDX-License-Identifier: MIT
# run/hooks.sh: r8-ldpm's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (kit/session.py guard).
#
# rd_words FILE: the `k=v` reading of one job's output (the tool's text and regtimeline's block),
# score/read.py's `words`, in awk: nparts, knob, need, gps_abort, gps_left, gmax, mono, runpeaks,
# s2, s3, ... (tests/test_read.py holds the two equal on every kept R7-dpm job and the mock's).
rd_words() {
	awk '
	function hx(s,   i, c, v) { v = 0; s = tolower(s); for (i = 1; i <= length(s); i++) { c = index("0123456789abcdef", substr(s, i, 1)); v = v * 16 + c - 1 }; return v }
	function lo(v) { return v % 65536 }
	function hi(v) { return int(v / 65536) % 65536 }
	function h(v) { return sprintf("0x%x", v) }
	/^timeline: regs/ {
		if (nreg) { done = 1; next }
		for (i = 3; i <= NF && $i != "samples"; i++) { nreg++; col[$i] = nreg }
		for (j = i; j <= NF; j++) if ($j == "start") start = $(j + 1) + 0
		next
	}
	/^tl / && nreg && !done {
		if (NF != nreg + 2) { cut = 1; done = 1; next }
		n++; t[n] = $2 + 0
		p7[n] = hx($(col["0x0724"] + 2)); g7[n] = hx($(col["0x072c"] + 2))
		pr[n] = hx($(col["0x0658"] + 2)) % 2; kn[n] = hx($(col["0x0624"] + 2))
	}
	END {
		if (cut || !n || !col["0x0724"] || !col["0x072c"] || !col["0x0658"] || !col["0x0624"]) n = 0
		if (n) report()
	}
	function report(   i, ns, a, knob, need, gmax, out, pg, ks, mono, last, nk, k, g, p, s, pp, rp, r, b0, b1, m, sa, se, S) {
		ns = 0
		for (i = 1; i <= n; i++) {
			if (pr[i] && (i == 1 || !pr[i - 1])) { ns++; sa[ns] = i }
			if (pr[i] && (i == n || !pr[i + 1])) se[ns] = i
		}
		a = ns ? sa[1] : n + 1
		knob = ""
		for (i = 1; i <= n; i++) if (t[i] >= start && lo(p7[i]) != 0) { knob = h(kn[i]); break }
		need = -1
		if (!ns) for (i = 1; i <= n; i++) if (lo(p7[i]) > need) need = lo(p7[i])
		gmax = 0
		for (i = 1; i <= n; i++) if (hi(g7[i]) > gmax) gmax = hi(g7[i])
		out = "nparts=" ns
		if (knob != "") out = out " knob=" knob
		if (need >= 0) out = out " need=" h(need)
		if (ns && a > 1) out = out " gps_abort=" h(hi(g7[a - 1]))
		if (ns) out = out " gps_left=" h(hi(g7[se[1]]))
		out = out " gmax=" h(gmax)
		pg = -1; ks = ""; mono = 1; last = -1; nk = 0
		for (i = 1; i < a; i++) {
			g = hi(g7[i]); p = hi(p7[i])
			if (pg >= 1 && g > pg) for (k = pg + 1; k <= g; k++) { s = (pp > p - 1) ? pp : p - 1; S[k] = s; nk++; ks = ks " s" k "=" h(s) }
			pg = g; pp = p
		}
		for (k = 2; k < 2 + nk; k++) { if (!(k in S)) mono = 0; else { if (S[k] < last) mono = 0; last = S[k] } }
		out = out " mono=" (nk ? mono : 0)
		rp = ""
		for (r = 0; r <= ns; r++) {
			b0 = (r == 0) ? 2 : se[r] + 1; b1 = (r < ns) ? sa[r + 1] - 1 : n
			if (b1 < b0) continue
			m = 0; for (i = b0; i <= b1; i++) if (hi(p7[i]) > m) m = hi(p7[i])
			rp = rp (rp == "" ? "" : ",") h(m)
		}
		if (rp != "") out = out " runpeaks=" rp
		print out ks
	}' "$1"
}
# hook_reading NAME: a control's reading, the `k=v` words of its output
hook_reading() {
	rd_words "$JW/$1.out" | tr ' ' '\n'
	return 0
}
# hook_check NAME: a row's `ctl:KEY=VALUE` words are its control values: one its reading does not
# equal stops the stage (rc 24; plan: "a control off stops the stage"). The scorer gates the same.
# A key the reading lacks is left to the premise (the kit's rc 25: a control without its reading).
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
