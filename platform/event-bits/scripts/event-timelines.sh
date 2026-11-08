#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.31 event-timelines (draft phase): Q111, which job sets which bit of CR_EVENT_STATUS and
# CR_EVENT_STATUS2, as a timeline.
# Raw outputs are KEPT: every tool output, whole, gzip (mtime 0) in $KEEP/NAME.txt.gz, the render's
# dumps beside it (NAME.param.bin.gz, NAME.tadata.bin.gz), the raw size and sha256 printed ("kept
# ..."), the case table in $KEEP/cases.tsv (with the exact tool arguments of every job) and the
# kernel log of the run (journalctl -k, as the short ring buffer loses it) in $KEEP/kernel.log.
# Recompute with recompute/recompute_p1131.py. After a failed job the GPU is reset (3 s), a plain
# 64x64 triangle must draw exactly (retry after 5 s waits); three failed recoveries stop the script.
# No clock-gate register is written (see lib1131.sh). Root through sudo -n.

SCRIPT_NAME=event-timelines
. "$(dirname "$0")/lib1131.sh"
[ -x "$RT" ] || { echo "no $RT: build tools/sweep/regtimeline.c on the laptop first"; exit 1; }
PB_RESTORE=$(sudo -n cat "$D/render_pb_pages")
begin
# The two event registers alone (CR_EVENT_STATUS2 0x0118, CR_EVENT_STATUS 0x012c) at the finest
# sampling regtimeline gives, and the same with five registers of the units (0x0218 the TA's dip,
# 0x0700, 0x0710, 0x0724, 0x0748 the DPM's), through each kind of job after a reset, in turn; the
# idle control is `sleep`. Read-only (/dev/mem), nothing is written but the reset, render_pb_pages
# (0x30 for the partial render, put back at exit) and kpoke clears.
R2="0x0118,0x012c"
R7="0x0118,0x012c,0x0218,0x0700,0x0710,0x0724,0x0748"
TLPY=$(cat <<'PYEOF'
import re, sys
regs, rows, hdr = [], [], ""
for line in sys.stdin:
    if line.startswith("timeline:"):
        hdr = line.split()
        regs = [t for t in hdr if t.startswith("0x")]
    elif line.startswith("tl "):
        rows.append(line.split()[1:])
if not rows:
    print("  no timeline"); sys.exit(0)
smp = int(hdr[hdr.index("samples") + 1]) if "samples" in hdr else 0
try:
    span = (int(hdr[hdr.index("end") + 1]) - int(hdr[hdr.index("start") + 1])) / 1000.0
    print("  %d changes, %s samples in %.0f us (%.2f us a sample)" % (len(rows), smp, span, span / max(smp, 1)))
except ValueError:
    print("  %d changes" % len(rows))
for i, r in enumerate(regs):
    vals = sorted({row[1 + i] for row in rows if len(row) > 1 + i})
    orv = 0
    for v in vals:
        orv |= int(v, 16)
    print("  %s: %d values %s ... or %#x" % (r, len(vals), " ".join(vals[:6]), orv))
PYEOF
)
rt_job() { # NAME KIND REGS: reset, then regtimeline 0 0.05 REGS -- the job
	name=$1 kind=$2 regs=$3
	case $kind in
	fill) cmd="fill" ;; copy) cmd="copy" ;;
	tri64) cmd="tri --width 64 --height 64" ;;
	tri256n3) cmd="tri --width 256 --height 256 -n 3" ;;
	zstore) cmd="tri --width 64 --height 64 --depth --depth-store" ;;
	partial) cmd="tri --width 1024 --height 768 -n 2 --keep-overflow --wait-ms 20000" ;;
	idle) cmd="sleep 0.3" ;;
	esac
	reset_gpu
	if [ "$kind" = partial ]; then set_knob render_pb_pages 0x30; else set_knob render_pb_pages "$PB_RESTORE"; fi
	[ "$kind" = idle ] && prog="" || prog="$T"
	printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$SCRIPT_NAME" "$kind" "0" "0" "regtimeline 0 0.05 $regs -- $prog $cmd" >> "$KEEP/cases.tsv"
	echo "== $name kind=$kind regs=$regs"
	mark "$name"
	sudo -n timeout 120 "$RT" 0 0.05 "$regs" -- $prog $cmd > "$W/$name.out" 2>&1 </dev/null
	echo "  rc $?"
	python3 -c "$TLPY" < "$W/$name.out"
	keep "$name" "$W/$name.out"
	if grep -qE "failed|faulted|hung" "$W/$name.out"; then reset_gpu; health </dev/null || true; fi
	rm -f "${W:?}/${name:?}.out"
}
for i in 1 2 3; do rt_job "tl-idle-r2-$i" idle "$R2"; rt_job "tl-idle-r7-$i" idle "$R7"; done
for run in 1 2 3 4 5; do
	for kind in tri64 fill tri256n3 copy zstore partial; do rt_job "tl-$kind-r2-$run" "$kind" "$R2"; done
done
for run in 1 2 3 4 5; do
	for kind in tri64 fill tri256n3 copy zstore partial; do rt_job "tl-$kind-r7-$run" "$kind" "$R7"; done
done
health </dev/null || true
echo "## end"
