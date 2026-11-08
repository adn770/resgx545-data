#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.31 event-irq-matrix (draft phase): Q111, which bit of the event registers each kind of job
# sets, seen as a host interrupt.
# Raw outputs are KEPT: every tool output, whole, gzip (mtime 0) in $KEEP/NAME.txt.gz, the render's
# dumps beside it (NAME.param.bin.gz, NAME.tadata.bin.gz), the raw size and sha256 printed ("kept
# ..."), the case table in $KEEP/cases.tsv (with the exact tool arguments of every job) and the
# kernel log of the run (journalctl -k, as the short ring buffer loses it) in $KEEP/kernel.log.
# Recompute with recompute/recompute_p1131.py. After a failed job the GPU is reset (3 s), a plain
# 64x64 triangle must draw exactly (retry after 5 s waits); three failed recoveries stop the script.
# No clock-gate register is written (see lib1131.sh). Root through sudo -n.

SCRIPT_NAME=event-irq-matrix
. "$(dirname "$0")/lib1131.sh"
PB_RESTORE=$(sudo -n cat "$D/render_pb_pages")
begin
# E444's method over ordinary jobs: after a reset one host event enable bit is written through
# debugfs kregnow (CR_EVENT_HOST_ENABLE 0x0130 = 0x4000 | bit for CR_EVENT_STATUS, CR_EVENT_HOST_ENABLE2
# 0x0110 = bit for CR_EVENT_STATUS2; kregnow_enable refuses every other offset, CR_CLKGATECTL2 among
# them), a job runs, one second later kregnow's counters ("host_irqs N extra M last S1 S2 ...": an
# interrupt with no SW_EVENT counts as extra, and puts the enables back, so one detection a run) and
# the two status registers are read. KINDS and the BITS variables restrict the matrix.
# Limits (plan.md 6): an event that coincides with the EDM's SW_EVENT (bit 14) in one interrupt is
# not counted as extra, the status word `last` shows it; bits 29 and 31 of status and bit 10 of
# status2 are set with no job (E444) and are not armed; CR_EVENT_HOST_CLEAR cannot be written.
KINDS=${KINDS:-"tri64 fill"}
STAT_BITS=${STAT_BITS:-"0 1 2 3 4 5 6 7 8 9 10 11 12 13 15 16 18 19 20 21 22 23 24 25 26 28"}
STAT2_BITS=${STAT2_BITS:-"0 1 2 3 4 5 6 7 8 9 11 12 13 14 15"}
irq_job() { # NAME KIND REG VALUE ("" "" for the unarmed control)
	name=$1 kind=$2 reg=$3 val=$4
	case $kind in
	fill) cmd="fill" ;; copy) cmd="copy" ;;
	tri64) cmd="tri --width 64 --height 64" ;;
	tri256n3) cmd="tri --width 256 --height 256 -n 3" ;;
	zstore) cmd="tri --width 64 --height 64 --depth --depth-store" ;;
	partial) cmd="tri --width 1024 --height 768 -n 2 --keep-overflow --wait-ms 20000" ;;
	esac
	reset_gpu
	if [ "$kind" = partial ]; then set_knob render_pb_pages 0x30; else set_knob render_pb_pages "$PB_RESTORE"; fi
	printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$SCRIPT_NAME" "$kind" "0" "0" "enable ${reg:-none}=${val:-none}; $T $cmd" >> "$KEEP/cases.tsv"
	mark "$name"
	{
		echo "case $name kind $kind enable ${reg:-none}=${val:-none}"
		echo "before: status $(rd 0x012c) $(rd 0x0118) enable $(rd 0x0130) $(rd 0x0110)"
		echo "kregnow before: $(kregnow_counts)"
		[ -n "$reg" ] && kregnow_enable "$reg" "$val"
		sudo -n timeout 120 "$T" $cmd 2>&1 </dev/null | grep -E "^(job|diff|tri|fill|copy)|failed|overflow" | head -n 4 | sed 's/^/job: /'
		sleep 1
		echo "after: status $(rd 0x012c) $(rd 0x0118) enable $(rd 0x0130) $(rd 0x0110)"
		echo "kregnow after: $(kregnow_counts)"
		echo "kernel: $(sudo -n dmesg | tail -n 12 | grep -E 'kregnow|host interrupt' | sed 's/^\[[ 0-9.]*\] //' | tr '\n' ';')"
	} > "$W/$name.out" 2>&1
	sed 's/^/  /' "$W/$name.out"
	keep "$name" "$W/$name.out"
	rm -f "${W:?}/${name:?}.out"
}
for kind in $KINDS; do
	for i in 1 2 3; do irq_job "irq-$kind-none-$i" "$kind" "" ""; done
	for b in $STAT_BITS; do irq_job "irq-$kind-st$b" "$kind" 0x0130 "$(printf '0x%x' $(( 0x4000 | (1 << b) )))"; done
	case $kind in tri64|fill)
		for b in $STAT2_BITS; do irq_job "irq-$kind-st2b$b" "$kind" 0x0110 "$(printf '0x%x' $(( 1 << b )))"; done ;;
	esac
	health </dev/null || true
done
echo "## end"
