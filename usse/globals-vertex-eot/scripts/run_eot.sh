#!/bin/bash
# 11.34 q053-eot (Q053): the end-of-tile program stores g16-g31, g39-g43 to the scratch; risky (an EOT program may hang): last, one at a time.
SCRIPT_NAME=q053-eot
. "$(dirname "$0")/lib1134.sh"
begin
while IFS='|' read -r name set w h args m marker regs; do
	[ -z "$name" ] && continue
	eval "set -- $args"
	run_job "$name" "$set" "$w" "$h" "$@"
done < "$(dirname "$0")/gen/table-q053-eot.txt"
health </dev/null || true
echo "## end"
