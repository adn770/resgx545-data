#!/bin/bash
# 11.34 dpm-bit2 (Q036, Q045): the DPM registers 0x0600-0x0750 (regtimeline, read-only, a line at every change) through a 4096x4096
# triangle of N vertices in PB pages P (render_pb_pages), three runs a case: whether 0x0748 bit 2 clears, whether STATUS2's high
# halves (0x0710, 0x071c) and 0x0740 ever hold anything. Usage: run_dpm.sh safe|risky (risky: the cells beside the E443 hangs).
RISK=${1:-safe}
SCRIPT_NAME=dpm-bit2-$RISK
. "$(dirname "$0")/lib1134.sh"
[ -x "$RT" ] || { echo "no $RT"; exit 1; }
PB_RESTORE=$(sudo -n cat "$D/render_pb_pages"); echo "## render_pb_pages at start: $PB_RESTORE"
B=$S/p1131-green__0.bin
[ -f "$B" ] || { echo "no $B"; exit 1; }
begin
while IFS='|' read -r name set risk n pages; do
	[ -z "$name" ] && continue
	[ "$risk" = "$RISK" ] || continue
	echo "== $name set=$set vertices $n pb $pages"
	printf '%s\t%s\t%s\t%s\t%s\n' "$name" "$SCRIPT_NAME" "$set" "$n" "$pages" >> "$KEEP/cases.tsv"
	set_knob render_pb_pages "$pages"
	mark "$name"
	sudo -n timeout 90 "$RT" 10.0 0.2 0x0600-0x0750 -- "$T" probe --tri pixel --width 4096 --height 4096 --vertices "$n" "$B" > "$W/$name.out" 2>&1 </dev/null
	rc=$?
	echo "  rc $rc $(grep -E 'failed|hung|faulted|overflow' "$W/$name.out" | head -1 | cut -c1-120)"
	keep "$name" "$W/$name.out"
	if grep -qE "failed|hung|faulted" "$W/$name.out" || [ "$rc" -ne 0 ]; then
		set_knob render_pb_pages "$PB_RESTORE"; reset_gpu; health </dev/null || true
	fi
done < "$(dirname "$0")/gen/table-dpm-bit2.txt"
set_knob render_pb_pages "$PB_RESTORE"
health </dev/null || true
echo "## end"
