#!/bin/bash
# run-all-1141ta.sh: on the laptop, the order of plan.md section 5: safe tables first, risky last, one table at a time,
# each table's own log; a table that stops itself (three failed recoveries) stops the whole run. Writes nothing to any
# register (no kreg, no kregnow), so no clock-gate register and no trc_hazard; debugfs reset/kpoke/hold_recovery/
# render_pb_pages as the 11.39 scripts. Usage: run-all-1141ta.sh [FROM_TABLE]
cd "$(dirname "$0")" || exit 1
OUT=${OUT:-$HOME/p1141ta-out}; mkdir -p "$OUT"
ORDER="vdm-series-a capacity dpm-oom dpm-stack eot-globals vdm-series-b o4-g25 dpm-hang eot-store capacity-rows"
go=0; [ -z "${1:-}" ] && go=1
for t in $ORDER; do
	[ "$t" = "${1:-}" ] && go=1
	[ $go = 1 ] || continue
	echo "#### $t $(date +%T)"
	bash run/run_table_ta.sh "$t" all > "$OUT/$t.out" 2>&1; rc=$?
	echo "rc $rc, $(grep -c '^== ' "$OUT/$t.out") cases"; grep -E "^## abort|health: the plain" "$OUT/$t.out" | head -3
	[ $rc -ne 0 ] && { echo "stopped after $t: read dmesg first"; exit $rc; }
done
