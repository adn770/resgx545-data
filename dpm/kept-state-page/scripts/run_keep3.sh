#!/bin/bash
# 11.35 keep-pages (Q045, follow-up 3: the ramp in page 1 or page 2 of the first context's TA data, ramp = the page): tri -n 1 --ctx2 --close-first-early: the first context renders (render flags
# flipped by --kpoke-render 1:ta:7^=FLAG), is closed, the second renders in the same VM. keep=1: debugfs
# render_keep armed before (the first context's close keeps its mappings, slot and memory); ramp=1:
# debugfs tadata_fill "3 0xa5000000 ramp" armed before (the first context's state page, page 3 of a 64x64
# context's TA data, holds word i = 0xa5000000 + i at its first render's kick). After the tool exits the
# kept context's TA data is read through debugfs render_kept (before the reset that releases it).
# Table gen/table-keep-pages.txt: name|set|keep|flag|ramp, the cases that fault last. Writes: render_keep,
# tadata_fill, kpoke, reset. No register is written.
SCRIPT_NAME=keep-pages
. "$(dirname "$0")/lib1135.sh"
begin
while IFS='|' read -r name set keep flag ramp; do
	[ -z "$name" ] && continue
	printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$SCRIPT_NAME" "$set" 64 64 "keep=$keep flag=$flag ramp=$ramp" >> "$KEEP/cases.tsv"
	echo "== $name set=$set keep=$keep flag=$flag ramp=$ramp"
	reset_gpu
	rm -rf "${W:?}/dump" "${W:?}/words"; mkdir -p "$W/dump" "$W/words"
	[ "$keep" = 1 ] && set_knob render_keep 1
	[ "$ramp" != 0 ] && printf "%s 0xa5000000 ramp\n" "$ramp" | sudo -n tee "$D/tadata_fill" >/dev/null
	echo "  render_keep=$(sudo -n cat "$D/render_keep") before"
	args=(tri --wait-ms 5000 -n 1 --ctx2 --close-first-early --close-trace --words "$W/words" --dump-render "$W/dump")
	[ "$flag" != 0x0 ] && args+=(--kpoke-render "1:ta:7^=$flag")
	mark "$name"
	sudo -n timeout 120 "$T" "${args[@]}" > "$W/$name.out" 2>&1 </dev/null
	rc=$?
	echo "  rc $rc $(grep -E '^(job|diff|tri:)' "$W/$name.out" | head -3 | tr '\n' ' ' | cut -c1-200)"
	echo "  render_keep=$(sudo -n cat "$D/render_keep") after"
	sudo -n cat "$D/render_kept" > "$W/kept.bin" 2>/dev/null
	echo "  kept TA data: $(wc -c < "$W/kept.bin" | tr -d ' ') bytes"
	keep "$name" "$W/$name.out"
	keep "$name" "$W/kept.bin" .kept.bin
	for f in "$W/dump"/*.tadata.bin; do [ -f "$f" ] && keep "$name" "$f" "-$(basename "$f" | cut -d. -f1).tadata.bin"; done
	for f in "$W/words"/ta3d.*.bin; do [ -f "$f" ] && keep "$name" "$f" "-$(basename "$f" .bin).ta3d.bin"; done
	sudo -n dmesg | grep -E "kept|BIF fault" | tail -n 4 | cut -c1-200
	kp_clear; printf 'clear\n' | sudo -n tee "$D/tadata_fill" >/dev/null 2>&1; set_knob render_keep 0
	reset_gpu; health </dev/null || true
done < "$(dirname "$0")/gen/table-keep-pages.txt"
echo "## end"
