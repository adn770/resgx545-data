# SPDX-License-Identifier: MIT
# run/hooks.sh: r29-kreg's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory.
# A job's readings: diff, the wrong pixels of all its renders summed (every `diff: N of` line);
# us, the mean of renders 2 to N's `tri WxH #i: T us` times (E141, E396), only with two or more.
job_diff() { awk '/^diff: [0-9]+ of / { s += $2; n++ } END { if (n) print s }' "$JW/$1.out"; }
job_us() { awk '/^tri [0-9]+x[0-9]+ #[0-9]+: [0-9]+ us$/ { k++; if (k > 1) { s += $(NF-1); n++ } } END { if (n) printf "%d\n", s / n }' "$JW/$1.out"; }
# hook_reading NAME: a control's reading, `key=value` words (every key of its reads: knob)
hook_reading() {
	local d u
	d=$(job_diff "$1"); u=$(job_us "$1")
	[ -n "$d" ] && printf 'diff=%s\n' "$d"
	[ -n "$u" ] && printf 'us=%s\n' "$u"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
# Every row draws exactly (E045: every value drew its triangle), says `tri: N renders ok`, and its
# mean is at most twice the stage's first timed row's (REF_US, kept in the runner's shell): a
# slower render is a wedge's symptom, not timing noise (E396's slowest render was 10 percent up).
REF_US=""
hook_check() {
	local d u
	d=$(job_diff "$1"); u=$(job_us "$1")
	grep -Eq '^tri: [0-9]+ renders ok$' "$JW/$1.out" || { echo "$1 has no \`tri: N renders ok\` line"; return 0; }
	[ "${d:-x}" = 0 ] || { echo "$1 drew ${d:-no diff line} wrong pixels"; return 0; }
	[ -n "$u" ] || return 0
	[ -n "$REF_US" ] || REF_US=$u
	[ "$u" -le $(( 2 * REF_US )) ] || echo "$1's render mean $u us is above twice $REF_US us"
	return 0
}
# hook_fault NAME: no row expects a fault or hang (the runner stops on any first)
hook_fault() { return 0; }
