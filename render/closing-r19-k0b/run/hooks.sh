# SPDX-License-Identifier: MIT
# run/hooks.sh: r19-k0's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (kit/session.py guard).
#
# rd_words OUT [W]: the `k=v` reading of one job, score/read.py's `words` in awk: from regtimeline's
# block nparts (0x0658 stretches) and knob (0x0624 at the first sample from `start` whose 0x0724
# low half is not 0); from the tool's lines ovfK (render K overflowed: 1, completed: 0), thrK
# (0x0624 of the --regs block at snapshot K), drawn (the last render's triangle pixels) and dst
# (the depth store's changed dwords); dsha, pmask, tadata: the first 16 hex digits of the sha256 of
# W/depth-store.1.bin, of W/p1139-green.param.bin masked (pmask), of W/p1139-green.tadata.bin (the scorer reads them
# from readings.tsv: a control's only). tests/test_read.py holds the two equal on the kept twins and the mock's outputs.
# pmask FILE: the sha256 of FILE's dwords as hex lines (od -tx4, the host's little-endian order,
# "%08x\n" each) after the stream ends are masked: a dword 0xc0000000 (the terminate word) right
# after another is written 00000000, so each stream ends at its first terminate word and what
# follows it in the run (words its job did not write, r19-k0 20261114-223342: 4 stale ones) is not
# compared. score/read.py pmask is its twin.
pmask() {
	od -An -v -tx4 "$1" | tr -s ' ' '\n' | awk 'NF { if ($1 == "c0000000" && p) print "00000000"; else print $1; p = ($1 == "c0000000") }' | sha
}
rd_words() {
	local ds="" pa="" ta=""
	if [ -n "${2:-}" ] && [ -f "$2/depth-store.1.bin" ]; then ds=$(sha "$2/depth-store.1.bin" | cut -c1-16); fi
	if [ -n "${2:-}" ] && [ -f "$2/p1139-green.param.bin" ]; then pa=$(pmask "$2/p1139-green.param.bin" | cut -c1-16); fi
	if [ -n "${2:-}" ] && [ -f "$2/p1139-green.tadata.bin" ]; then ta=$(sha "$2/p1139-green.tadata.bin" | cut -c1-16); fi
	awk -v ds="$ds" -v pa="$pa" -v ta="$ta" '
	function hx(s,   i, c, v) { v = 0; s = tolower(s); for (i = 1; i <= length(s); i++) { c = index("0123456789abcdef", substr(s, i, 1)); v = v * 16 + c - 1 }; return v }
	/^timeline: regs/ {
		if (nreg) { done = 1; next }
		for (i = 3; i <= NF && $i != "samples"; i++) { nreg++; col[$i] = nreg }
		for (j = i; j <= NF; j++) if ($j == "start") start = $(j + 1) + 0
		next
	}
	/^tl / && nreg && !done {
		if (NF != nreg + 2) { cut = 1; done = 1; next }
		n++; t[n] = $2 + 0
		p7[n] = hx($(col["0x0724"] + 2)); pr[n] = hx($(col["0x0658"] + 2)) % 2
		kn[n] = hx($(col["0x0624"] + 2))
		next
	}
	/^tri: registers at snapshot [0-9]+$/ { snap = $5; next }
	/^reg 0x0624 0x[0-9a-f]+$/ && snap != "" && !(snap in thr) { thr[snap] = sprintf("0x%x", hx(substr($3, 3))); next }
	/^tri [0-9]+x[0-9]+ #[0-9]+: / {
		k = $3; sub(/^#/, "", k); sub(/:$/, "", k)
		if ($4 == "geometry") { ovf[k] = 0; next }
		if ($4 == "overflowed,") { ovf[k] = 1; drawn = $5 } else if ($5 == "triangle,") { ovf[k] = 0; drawn = $4 }
		next
	}
	/^depth store #1: [0-9]+ dwords, [0-9]+ changed/ { dst = $6 + 0; next }
	END {
		out = ""
		if (!cut && n && col["0x0724"] && col["0x0658"] && col["0x0624"]) {
			np = 0; knob = ""
			for (i = 1; i <= n; i++) {
				if (pr[i] && (i == 1 || !pr[i - 1])) np++
				if (knob == "" && t[i] >= start && p7[i] % 65536 != 0) knob = sprintf("0x%x", kn[i])
			}
			out = out " nparts=" np
			if (knob != "") out = out " knob=" knob
		}
		if (drawn != "") out = out " drawn=" drawn
		if (dst != "") out = out " dst=" dst
		for (k = 1; k <= 3; k++) {
			if (k in ovf) out = out " ovf" k "=" ovf[k]
			if (k in thr) out = out " thr" k "=" thr[k]
		}
		if (ds != "") out = out " dsha=" ds
		if (pa != "") out = out " pmask=" pa
		if (ta != "") out = out " tadata=" ta
		sub(/^ /, "", out)
		if (out != "") print out
	}' "$1"
}
# hook_reading NAME: a control's reading, the `k=v` words of its output and files
hook_reading() {
	rd_words "$JW/$1.out" "$W" | tr ' ' '\n'
	return 0
}
# hook_check NAME: a row's `ctl:KEY=VALUE` words are its control's frozen values: one its reading
# does not equal stops the stage (rc 24; a key the reading lacks is the premise's, rc 25). A row
# with `stop:jobfail` (f0-down) stops the stage when any render ended `job: failed:` other than
# an overflow (a hang or fault the kernel recovered, a cancelled job) though the job ended ok.
hook_check() {
	local w k v got rd
	case " $knobs " in
	*" stop:jobfail "*)
		got=$(grep '^job: failed:' "$JW/$1.out" | grep -v 'scene overflowed the parameter buffer' | head -n 1)
		[ -z "$got" ] || { echo "f0-down rule: $1 printed '$got'"; return 0; } ;;
	esac
	case " $knobs " in *" ctl:"*) ;; *) return 0 ;; esac
	rd=" $(rd_words "$JW/$1.out" "$W") "
	for w in $knobs; do
		case "$w" in ctl:*=*) ;; *) continue ;; esac
		k=${w#ctl:}; v=${k#*=}; k=${k%%=*}
		got=$(printf '%s\n' "$rd" | tr ' ' '\n' | sed -n "s/^$k=//p" | head -n 1)
		[ -n "$got" ] || continue
		[ "$got" = "$v" ] || { echo "control $1 reads $k=$got where the frozen value is $v"; return 0; }
	done
	return 0
}
# hook_fault NAME: after an expected fault or hang row; this session plans none
hook_fault() { return 0; }
