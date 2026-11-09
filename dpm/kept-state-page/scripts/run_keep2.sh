#!/bin/bash
# 11.35 keep-partial (Q045, follow-up): the kept context's state page after a partial render. The first context
# renders 1024x768 on a 0x28-page parameter buffer (the scene overflows and is finished by partial renders: its state
# page, page 6 of the TA data, then holds the DPM lists, E464); render flags of the first flipped by FLAG; keep=1
# arms debugfs render_keep; ctx2=1 adds a second context (--ctx2 --close-first-early) that renders after the first is
# closed. The kept TA data is read through debugfs render_kept after the tool exits. Table
# gen/table-keep-partial.txt: name|set|keep|flag|ctx2. Writes: render_keep, render_pb_pages (put back), kpoke, reset.
SCRIPT_NAME=keep-partial
. "$(dirname "$0")/lib1135.sh"
PB_RESTORE=0x00000422
begin
while IFS='|' read -r name set keep flag ctx2; do
	[ -z "$name" ] && continue
	[ -n "${ONLY:-}" ] && [ "${name#*"$ONLY"}" = "$name" ] && continue
	printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$SCRIPT_NAME" "$set" 1024 768 "keep=$keep flag=$flag ctx2=$ctx2" >> "$KEEP/cases.tsv"
	echo "== $name set=$set keep=$keep flag=$flag ctx2=$ctx2"
	reset_gpu
	rm -rf "${W:?}/dump" "${W:?}/words"; mkdir -p "$W/dump" "$W/words"
	set_knob render_pb_pages 0x28
	[ "$keep" = 1 ] && set_knob render_keep 1
	args=(tri --width 1024 --height 768 --keep-overflow --wait-ms 20000 -n 1 --words "$W/words" --dump-render "$W/dump")
	[ "$ctx2" = 1 ] && args+=(--ctx2 --close-first-early --close-trace)
	[ "$flag" != 0x0 ] && args+=(--kpoke-render "1:ta:7^=$flag")
	mark "$name"
	sudo -n timeout 300 "$T" "${args[@]}" > "$W/$name.out" 2>&1 </dev/null
	rc=$?
	echo "  rc $rc $(grep -E '^(job|diff|tri:)' "$W/$name.out" | head -3 | tr '\n' ' ' | cut -c1-200)"
	sudo -n cat "$D/render_kept" > "$W/kept.bin" 2>/dev/null
	echo "  kept TA data: $(wc -c < "$W/kept.bin" | tr -d ' ') bytes"
	keep "$name" "$W/$name.out"
	keep "$name" "$W/kept.bin" .kept.bin
	for f in "$W/dump"/*.tadata.bin; do [ -f "$f" ] && keep "$name" "$f" "-$(basename "$f" | cut -d. -f1).tadata.bin"; done
	sudo -n dmesg | grep -E "kept|BIF fault" | tail -n 4 | cut -c1-200
	kp_clear; set_knob render_keep 0; set_knob render_pb_pages 0x422
	reset_gpu; health </dev/null || true
done < "$(dirname "$0")/gen/table-keep-partial.txt"
echo "## end"
