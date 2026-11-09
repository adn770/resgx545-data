#!/bin/bash
# 11.34 o23-size (Q023 follow-up): the o23-tiles jobs with --dump-render at several target sizes and PDS_SIZE values, x run and
# y run of each table (the tag's low 16 bits: job marker * 16 + register number + 1; the high half is the float
# x or y of the pixel's own place), every pixel read, whole raw output kept. Safe.
SCRIPT_NAME=o23-size
. "$(dirname "$0")/lib1134.sh"
begin
while IFS='|' read -r name set w h args m ax; do
	[ -z "$name" ] && continue
	eval "set -- $args"
	run_job "$name" "$set" "$w" "$h" "$@"
done < "$(dirname "$0")/gen/table-o23-size.txt"
health </dev/null || true
echo "## end"
