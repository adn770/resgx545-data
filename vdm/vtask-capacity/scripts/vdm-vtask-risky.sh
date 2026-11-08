#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.31 vdm-vtask-risky (draft phase): Q092 (the first trailing word's top nibble against the task's attribute rows).
# RISKY: five copies (15 vertices), vdm:4 at 0xf0000000, 0xd0000000, 0x70000000 against the vertex
# task's attribute rows (vdm:7 bits 14:7) at 1, 2 and 4, the object compared with the control's
# (0xf, 1). The attribute rows beyond the vertex program's may fault or hang the job.
# Raw outputs are KEPT: every tool output, whole, gzip (mtime 0) in $KEEP/NAME.txt.gz, the render's
# dumps beside it (NAME.param.bin.gz, NAME.tadata.bin.gz), the raw size and sha256 printed ("kept
# ..."), the case table in $KEEP/cases.tsv (with the exact tool arguments of every job) and the
# kernel log of the run (journalctl -k, as the short ring buffer loses it) in $KEEP/kernel.log.
# Recompute with recompute/recompute_p1131.py. After a failed job the GPU is reset (3 s), a plain
# 64x64 triangle must draw exactly (retry after 5 s waits); three failed recoveries stop the script.
# No clock-gate register is written (see lib1131.sh). Root through sudo -n.
SCRIPT_NAME=vdm-vtask-risky
. "$(dirname "$0")/lib1131.sh"
for f in "$S"/p1131-green__0.bin "$S"/pix_pa0.bin; do
	[ -f "$f" ] || { echo "no $f: run stage-p1131.sh and copy"; exit 1; }
done
begin
TABLE=$(cat <<'TABLE'
q92-nibf-rows1|control|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --vdm 4=0xf0000000 --vdm 7^=0x00000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
q92-nibf-rows2|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --vdm 4=0xf0000000 --vdm 7^=0x00000180 --dump-render "$W/dump" "$S/p1131-green__0.bin"
q92-nibf-rows4|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --vdm 4=0xf0000000 --vdm 7^=0x00000280 --dump-render "$W/dump" "$S/p1131-green__0.bin"
q92-nibd-rows1|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --vdm 4=0xd0000000 --vdm 7^=0x00000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
q92-nibd-rows2|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --vdm 4=0xd0000000 --vdm 7^=0x00000180 --dump-render "$W/dump" "$S/p1131-green__0.bin"
q92-nibd-rows4|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --vdm 4=0xd0000000 --vdm 7^=0x00000280 --dump-render "$W/dump" "$S/p1131-green__0.bin"
q92-nib7-rows1|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --vdm 4=0x70000000 --vdm 7^=0x00000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
q92-nib7-rows2|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --vdm 4=0x70000000 --vdm 7^=0x00000180 --dump-render "$W/dump" "$S/p1131-green__0.bin"
q92-nib7-rows4|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --vdm 4=0x70000000 --vdm 7^=0x00000280 --dump-render "$W/dump" "$S/p1131-green__0.bin"
TABLE
)
run_table "$TABLE"
health </dev/null || true
echo "## end"
