#!/bin/bash
# 11.34 q053-eotcap (Q053): the end-of-tile program stores g16-g31, g39-g43 to the scratch; the EOT area capacity: 0 to 3 extra nops after the 7-instruction plain EOT; risky, one at a time.
SCRIPT_NAME=q053-eotcap
. "$(dirname "$0")/lib1134.sh"
begin
while IFS='|' read -r name set w h args m ax; do
	[ -z "$name" ] && continue
	eval "set -- $args"
	run_job "$name" "$set" "$w" "$h" "$@"
done < "$(dirname "$0")/gen/table-q053-eotcap.txt"
health </dev/null || true
echo "## end"
