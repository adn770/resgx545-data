# SPDX-License-Identifier: MIT
# run/hooks.sh: r31-kreg2's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory. score/score.py's reading() is the twin of these.
# A job's readings (frozen, gen/gen.py):
#   diff  the wrong pixels of all its renders summed (every `diff: N of` line; t10's tri form)
#   us    the MEDIAN of renders 2 to N's `tri WxH #i: T us` times, in output order (t10's tri
#         prints #1..#6; t30's probe --tri --vertices prints #1 once a render), only with two or
#         more; an even count takes the mean of the middle two, rounded down
#   img   (probe form) how many renders' `probe NAME: o0 ...` lines differ from the first's
job_diff() { awk '/^diff: [0-9]+ of / { s += $2; n++ } END { if (n) print s }' "$JW/$1.out"; }
job_us() {
	awk '/^tri [0-9]+x[0-9]+ #[0-9]+: [0-9]+ us$/ { k++; if (k > 1) t[++n] = $(NF-1) + 0 }
	END {
		if (!n) exit
		for (i = 2; i <= n; i++) { v = t[i]; for (j = i - 1; j >= 1 && t[j] > v; j--) t[j+1] = t[j]; t[j+1] = v }
		if (n % 2) printf "%d\n", t[(n + 1) / 2]; else printf "%d\n", int((t[n/2] + t[n/2+1]) / 2)
	}' "$JW/$1.out"
}
job_img() {
	awk '/^probe [^ ]+: o0 / { sub(/^probe [^ ]+: /, ""); n++; if (n == 1) f = $0; else if ($0 != f) d++ }
	END { if (n) print d + 0 }' "$JW/$1.out"
}
job_probe() { grep -Eq '^probe [^ ]+: tri [0-9]+x[0-9]+ ' "$JW/$1.out"; }
# hook_reading NAME: a control's reading, `key=value` words (every key of its reads: knob)
hook_reading() {
	local d u i
	d=$(job_diff "$1"); u=$(job_us "$1"); i=$(job_img "$1")
	[ -n "$d" ] && printf 'diff=%s\n' "$d"
	[ -n "$u" ] && printf 'us=%s\n' "$u"
	[ -n "$i" ] && printf 'img=%s\n' "$i"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
# A wedge's symptoms only, never timing noise: tri form, no `tri: N renders ok` line or a wrong
# pixel (E045: every value drew its triangle); probe form, a `failed:` line or not six timing
# lines; either form, a median above twice the stage's first timed row of the same form (REF_TRI,
# REF_PROBE, kept in the runner's shell; E1114's slowest render was 24 percent up).
REF_TRI=""
REF_PROBE=""
hook_check() {
	local d u n
	u=$(job_us "$1")
	if job_probe "$1"; then
		if grep -q 'failed:' "$JW/$1.out"; then echo "$1 has a failed render"; return 0; fi
		n=$(grep -Ec '^tri [0-9]+x[0-9]+ #1: [0-9]+ us$' "$JW/$1.out")
		[ "$n" = 6 ] || { echo "$1 timed $n renders, not 6"; return 0; }
		[ -n "$REF_PROBE" ] || REF_PROBE=$u
		[ "$u" -le $(( 2 * REF_PROBE )) ] || echo "$1's render median $u us is above twice $REF_PROBE us"
		return 0
	fi
	d=$(job_diff "$1")
	grep -Eq '^tri: [0-9]+ renders ok$' "$JW/$1.out" || { echo "$1 has no \`tri: N renders ok\` line"; return 0; }
	[ "${d:-x}" = 0 ] || { echo "$1 drew ${d:-no diff line} wrong pixels"; return 0; }
	[ -n "$u" ] || return 0
	[ -n "$REF_TRI" ] || REF_TRI=$u
	[ "$u" -le $(( 2 * REF_TRI )) ] || echo "$1's render median $u us is above twice $REF_TRI us"
	return 0
}
# hook_fault NAME: no row expects a fault or hang (the runner stops on any first)
hook_fault() { return 0; }
