#!/bin/bash
# 11.34 o23-tiles (Q023): the 8-register tagged shader at several target sizes and PDS_SIZE values, x run and
# y run of each table (the tag's low 16 bits: job marker * 16 + register number + 1; the high half is the float
# x or y of the pixel's own place), every pixel read, whole raw output kept. Safe.
SCRIPT_NAME=o23-tiles
. "$(dirname "$0")/lib1134.sh"
begin
while IFS='|' read -r name set w h args m ax; do
	[ -z "$name" ] && continue
	eval "set -- $args"
	run_job "$name" "$set" "$w" "$h" "$@"
done < "$(dirname "$0")/gen/table-o23-tiles.txt"
health </dev/null || true
echo "## end"
