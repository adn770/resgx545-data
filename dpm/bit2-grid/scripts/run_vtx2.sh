#!/bin/bash
# 11.34 q053-vtx2 (Q053): the vertex program moves g16-g31, g39-g43 into vertex outputs; 126 vertices. Safe.
SCRIPT_NAME=q053-vtx2
. "$(dirname "$0")/lib1134.sh"
begin
while IFS='|' read -r name set w h args m marker regs V; do
	[ -z "$name" ] && continue
	eval "set -- $args"
	run_job "$name" "$set" "$w" "$h" "$@"
done < "$(dirname "$0")/gen/table-q053-vtx2.txt"
health </dev/null || true
echo "## end"
