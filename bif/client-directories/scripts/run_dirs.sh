#!/bin/bash
# 11.35 dirs (Q076): the client directory (debugfs render_words ctx:2, the page directory word of the
# newest render context's HW context, saved by the tool's --words after each render while the context
# lives) against CR_BIF_DIR_LIST_BASE0..15 (0x0c34..0x0c70, the tool's --regs after the renders), with
# regtimeline on the bus interface (0x0c00-0x0c8c) as the other record.
# Table gen/table-dirs.txt: name|set|reset|tool args|alias_skip mask. A `reset` case resets the GPU first
# and runs no tool between (the first kick of a VM after a reset takes list 1, E360); `noreset` follows
# the previous case at once. Cases with the partial render (render_pb_pages 0x28) are last.
# Writes: alias_skip (put back), render_pb_pages (put back), reset. No register is written.
SCRIPT_NAME=dirs
. "$(dirname "$0")/lib1135.sh"
PB_RESTORE=0x00000422
[ -x "$RT" ] || { echo "no $RT"; exit 1; }
begin
while IFS='|' read -r name set rst args mask; do
	[ -z "$name" ] && continue
	printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$SCRIPT_NAME" "$set" 64 64 "$rst $mask $args" >> "$KEEP/cases.tsv"
	echo "== $name set=$set $rst alias_skip=$mask: $args"
	[ "$rst" = reset ] && reset_gpu
	set_knob alias_skip "$mask"
	case "$args" in *1024*) set_knob render_pb_pages 0x28 ;; *) set_knob render_pb_pages 0x422 ;; esac
	mark "$name"
	rm -rf "${W:?}/words"; mkdir -p "$W/words"
	sudo -n timeout 120 "$RT" 0 0.3 0x0c00-0x0c8c -- "$T" ${args} --words "$W/words" --regs 0x0c34-0x0c74 > "$W/$name.out" 2>&1 </dev/null
	rc=$?
	echo "  rc $rc $(grep -E '^(tri|job|diff)' "$W/$name.out" | head -3 | tr '\n' ' ' | cut -c1-200)"
	last=$(ls "$W/words"/words.*.txt 2>/dev/null | sort -t. -k2 -n | tail -n 1)
	echo "  $(grep -E '^ctx:2=' "$last" 2>/dev/null) from $(basename "${last:-none}") ; $(grep -E '^reg 0x0c(38|3c|40|44|70) ' "$W/$name.out" | awk '{printf "%s=%s ", $2, $3}')"
	keep "$name" "$W/$name.out"
	for f in "$W/words"/words.*.txt; do [ -f "$f" ] && keep "$name" "$f" ".$(basename "$f")"; done
	set_knob alias_skip 0; set_knob render_pb_pages 0x422
	sudo -n dmesg | grep -iE "BIF fault|stalls|recover" | tail -n 2 | cut -c1-200
	if grep -qE "failed|faulted|hung|FAILED" "$W/$name.out" || [ "$rc" -ne 0 ]; then
		reset_gpu; health </dev/null || true
	fi
done < "$(dirname "$0")/gen/table-dirs.txt"
reset_gpu; health </dev/null || true
echo "## end"
