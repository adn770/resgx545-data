#!/bin/bash
# 11.34 q053-eotst (Q053): the end-of-tile program stores g16-g31, g39-g43 to the scratch; which instruction of the stores faults in the EOT: mov r1 alone, a store of r2, of g43 with and without the fence.
SCRIPT_NAME=q053-eotst
. "$(dirname "$0")/lib1134.sh"
begin
while IFS='|' read -r name set w h args m ax; do
	[ -z "$name" ] && continue
	eval "set -- $args"
	run_job "$name" "$set" "$w" "$h" "$@"
done < "$(dirname "$0")/gen/table-q053-eotst.txt"
health </dev/null || true
echo "## end"
