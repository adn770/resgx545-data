#!/bin/bash
# 11.34 bif-alias (Q076): debugfs alias_skip masks (ids E457 did not run: 0-5, 12-15, pairs and five of 6,7,8,10,11), a render pair
# (tri -n 2 --keep-going) under regtimeline on the BIF registers 0x0c00-0x0c8c, the debugfs layout (pd_phys of the newest VM) read
# 2.5 s into the run, the kernel log of the case. Usage: run_bif.sh safe|risky (risky = ids 0-5, last, each case alone).
RISK=${1:-safe}
SCRIPT_NAME=bif-alias-$RISK
. "$(dirname "$0")/lib1134.sh"
[ -x "$RT" ] || { echo "no $RT"; exit 1; }
trap 'set_knob alias_skip 0; kp_clear; reset_gpu; rm -rf "${W:?}"; finish_log' EXIT
begin
while IFS='|' read -r name set risk mask; do
	[ -z "$name" ] && continue
	[ "$risk" = "$RISK" ] || continue
	echo "== $name set=$set alias_skip $mask"
	printf '%s\t%s\t%s\t%s\n' "$name" "$SCRIPT_NAME" "$set" "$mask" >> "$KEEP/cases.tsv"
	reset_gpu; health </dev/null || true
	set_knob alias_skip "$mask"
	echo "  alias_skip=$(sudo -n cat "$D/alias_skip")"
	mark "$name"
	( sleep 2.5; sudo -n cat "$D/layout" > "$W/layout.txt" 2>&1 ) &
	sudo -n timeout 120 "$RT" 0 0.3 0x0c00-0x0c8c -- "$T" tri -n 2 --keep-going --wait-ms 6000 > "$W/$name.out" 2>&1 </dev/null
	rc=$?
	wait
	echo "  rc $rc $(grep -E '^(tri|job|diff)' "$W/$name.out" | head -2 | tr '\n' ' ' | cut -c1-200)"
	grep -E "renders ok|FAILED|failed|faulted" "$W/$name.out" | head -3 | cut -c1-200
	keep "$name" "$W/$name.out"
	keep "$name" "$W/layout.txt" .layout.txt
	set_knob alias_skip 0
	sudo -n dmesg | grep -iE "BIF fault|stalls|recover" | tail -n 3 | cut -c1-200
	if grep -qE "failed|faulted|hung|FAILED" "$W/$name.out" || [ "$rc" -ne 0 ]; then
		reset_gpu; health </dev/null || true
	fi
done < "$(dirname "$0")/gen/table-bif-alias.txt"
health </dev/null || true
echo "## end"
