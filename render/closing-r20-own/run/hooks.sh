# SPDX-License-Identifier: MIT
# run/hooks.sh: r20-own's hooks (r19-own1b's, every row under regtimeline, whose lines follow t18b's) into the kit's laptop runner (kit/run_stage.sh), sourced by it.
# Only reads: no debugfs write, no rm, no exit (session.py guard). $JW/NAME.out, .err, .dmesg are
# the job's files, $W its work directory.
# t18b's lines read here (sgxfive-test.c at ec50498: kept_copy(), cmd_tri()):
#   tri 1024x768 #1: overflowed, ...                       the first context's render overflowed
#   tri: render_kept after closing the first context, before the second context's render 1: PATH (N bytes)
#   tri: render_kept after the second context's render 1: PATH (N bytes)
# (a failed copy prints its error and 0 bytes)
# kept_n NAME: how many kept copies were made (N > 0)
kept_n() { grep -c '^tri: render_kept .*: /.* ([1-9][0-9]* bytes)$' "$JW/$1.out"; }
# hook_reading NAME: a control's reading: ovf (the first context's render overflowed, 0 or 1),
# kept (copies made, 0 to 2), size (bytes of the copy made after the close)
hook_reading() {
	local o k s
	o=$(grep -c '^tri [0-9]*x[0-9]* #1: overflowed, ' "$JW/$1.out")
	k=$(kept_n "$1")
	s=$(sed -n 's/^tri: render_kept after closing the first context.*: \/.* (\([0-9][0-9]*\) bytes)$/\1/p' "$JW/$1.out" | head -n 1)
	printf 'ovf=%s kept=%s size=%s\n' "${o:-0}" "${k:-0}" "${s:--}"
	return 0
}
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing.
# The copy after the second context's render must be made (N > 0 bytes); the copy right after the
# close may read empty (0 bytes: [infer] the context parked after the tool read it, E1085), which
# makes the row cannot tell (score.py); two such rows in a row stop the stage. EMPTY_RUN is kept
# in the runner's shell from row to row.
EMPTY_RUN=0
hook_check() {
	local a c
	a=$(grep -c '^tri: render_kept after the second context.*: /.* ([1-9][0-9]* bytes)$' "$JW/$1.out")
	c=$(grep -c '^tri: render_kept after closing the first context.*: /.* ([1-9][0-9]* bytes)$' "$JW/$1.out")
	[ "${a:-0}" = 1 ] || echo "$1: no copy after the second context's render (render_keep not taken or render_kept unreadable)"
	if [ "${c:-0}" = 1 ]; then EMPTY_RUN=0; else EMPTY_RUN=$((EMPTY_RUN + 1)); fi
	[ "$EMPTY_RUN" -ge 2 ] && echo "$1: the copy right after the close read empty in 2 rows in a row"
	return 0
}
# hook_fault NAME: no row of this session expects a fault or a hang
hook_fault() { return 0; }
