#!/bin/bash
# 11.34 q053-eot2 (Q053): one global register a job, stored by the end-of-tile program (the job faults after the store, a recovery each); risky.
SCRIPT_NAME=q053-eot2
. "$(dirname "$0")/lib1134.sh"
begin
while IFS='|' read -r name set w h args m g off; do
	[ -z "$name" ] && continue
	eval "set -- $args"
	run_job "$name" "$set" "$w" "$h" "$@"
done < "$(dirname "$0")/gen/table-q053-eot2.txt"
health </dev/null || true
echo "## end"
