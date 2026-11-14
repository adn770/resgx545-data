# SPDX-License-Identifier: MIT
# run/hooks.sh: r19-own's hooks into the kit's laptop runner (kit/run_stage.sh), sourced by it.
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
# hook_check NAME: after a job that read ok, a reason to stop the stage (rc 24), or nothing:
# both kept copies must have been made (render_keep taken by the first context's close and
# render_kept readable both times; a missing copy file stops the runner first, rc 23), and every
# own2 row is a partial-render owner: its first render must have overflowed (Q192's premise)
hook_check() {
	local k o
	k=$(kept_n "$1")
	[ "${k:-0}" = 2 ] || echo "$1: $k of 2 kept copies made (render_keep not taken or render_kept unreadable)"
	o=$(grep -c '^tri [0-9]*x[0-9]* #1: overflowed, ' "$JW/$1.out")
	[ "$STAGE" = own2 ] && [ "${o:-0}" != 1 ] && echo "$1: the first render did not overflow (no partial-render owner)"
	return 0
}
# hook_fault NAME: no row of this session expects a fault or a hang
hook_fault() { return 0; }
