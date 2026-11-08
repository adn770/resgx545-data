#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.31 ta-line-point (draft phase): Q070 (the region test for lines and points) and Q117 (what a point covers).
# Lines (index list type 1, ISP word 0 + 0x8000) and points (type 2, + 0x18000) placed by the viewport
# words (blk:6-9: x offset, x scale, y offset, y scale; the vertex k of the first triangle is the
# offset + scale * its NDC position, the copies of --vertices moved c/16 pixel when the scale is
# W/2): 128x128 for the region lists (32x16 regions, 16x16 tiles), 64x64 for the pixel footprints.
# Lines: the landed geometry (fit), a near-horizontal segment round y = 16 and a near-vertical one
# round x = 16 and 32, each at ISP word 1 widths 0x10 and 0x40, then two and three lines in one
# object. Points: the landed geometry, 6-point boundary jobs, widths, and the footprints (pixel
# centres and corners, widths 0x00 to 0xf0 as ISP word 1 bits 15:8) with the vertex-output size.
# Raw outputs are KEPT: every tool output, whole, gzip (mtime 0) in $KEEP/NAME.txt.gz, the render's
# dumps beside it (NAME.param.bin.gz, NAME.tadata.bin.gz), the raw size and sha256 printed ("kept
# ..."), the case table in $KEEP/cases.tsv (with the exact tool arguments of every job) and the
# kernel log of the run (journalctl -k, as the short ring buffer loses it) in $KEEP/kernel.log.
# Recompute with recompute/recompute_p1131.py. After a failed job the GPU is reset (3 s), a plain
# 64x64 triangle must draw exactly (retry after 5 s waits); three failed recoveries stop the script.
# No clock-gate register is written (see lib1131.sh). Root through sudo -n.
SCRIPT_NAME=ta-line-point
. "$(dirname "$0")/lib1131.sh"
for f in "$S"/p1131-green__0.bin "$S"/pix_pa0.bin; do
	[ -f "$f" ] || { echo "no $f: run stage-p1131.sh and copy"; exit 1; }
done
begin
TABLE=$(cat <<'TABLE'
ln-ctl64-r1|fit|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d08200 --blk 6=0x42000000 --blk 7=0x42000000 --blk 8=0x42000000 --blk 9=0x42000000 --vdm 2=0x84c00002 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-ctl64-r2|fit|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d08200 --blk 6=0x42000000 --blk 7=0x42000000 --blk 8=0x42000000 --blk 9=0x42000000 --vdm 2=0x84c00002 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-ctl64-two|fit|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 6 --blk 1=0x01d08200 --blk 6=0x42000000 --blk 7=0x42000000 --blk 8=0x42000000 --blk 9=0x42000000 --vdm 2=0x84c00004 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-row-a-w10|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x42800000 --blk 7=0x42000000 --blk 8=0x41810000 --blk 9=0x3f000000 --blk 2=0x000010f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-row-a-w40|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x42800000 --blk 7=0x42000000 --blk 8=0x41810000 --blk 9=0x3f000000 --blk 2=0x000040f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-row-b-w10|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x42800000 --blk 7=0x42000000 --blk 8=0x41818000 --blk 9=0x3f000000 --blk 2=0x000010f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-row-b-w40|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x42800000 --blk 7=0x42000000 --blk 8=0x41818000 --blk 9=0x3f000000 --blk 2=0x000040f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-row-c-w10|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x42800000 --blk 7=0x42000000 --blk 8=0x41828000 --blk 9=0x3f000000 --blk 2=0x000010f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-row-c-w40|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x42800000 --blk 7=0x42000000 --blk 8=0x41828000 --blk 9=0x3f000000 --blk 2=0x000040f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-row-d-w10|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x42800000 --blk 7=0x42000000 --blk 8=0x41830000 --blk 9=0x3f000000 --blk 2=0x000010f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-row-d-w40|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x42800000 --blk 7=0x42000000 --blk 8=0x41830000 --blk 9=0x3f000000 --blk 2=0x000040f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-row-e-w10|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x42800000 --blk 7=0x42000000 --blk 8=0x41848000 --blk 9=0x3f000000 --blk 2=0x000010f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-row-e-w40|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x42800000 --blk 7=0x42000000 --blk 8=0x41848000 --blk 9=0x3f000000 --blk 2=0x000040f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-col-a-w10|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x41060000 --blk 7=0x3f000000 --blk 8=0x42400000 --blk 9=0x42000000 --blk 2=0x000010f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-col-a-w40|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x41060000 --blk 7=0x3f000000 --blk 8=0x42400000 --blk 9=0x42000000 --blk 2=0x000040f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-col-b-w10|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x41c30000 --blk 7=0x3f000000 --blk 8=0x42400000 --blk 9=0x42000000 --blk 2=0x000010f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-col-b-w40|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x41c30000 --blk 7=0x3f000000 --blk 8=0x42400000 --blk 9=0x42000000 --blk 2=0x000040f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-col-c-w10|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x42018000 --blk 7=0x3f000000 --blk 8=0x42400000 --blk 9=0x42000000 --blk 2=0x000010f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-col-c-w40|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x42018000 --blk 7=0x3f000000 --blk 8=0x42400000 --blk 9=0x42000000 --blk 2=0x000040f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-col-d-w10|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x41fe8000 --blk 7=0x3f000000 --blk 8=0x42400000 --blk 9=0x42000000 --blk 2=0x000010f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-col-d-w40|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d08200 --blk 6=0x41fe8000 --blk 7=0x3f000000 --blk 8=0x42400000 --blk 9=0x42000000 --blk 2=0x000040f0 --vdm 2=0x84c00002 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-two128|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 1=0x01d08200 --blk 6=0x42800000 --blk 7=0x42800000 --blk 8=0x42800000 --blk 9=0x42800000 --vdm 2=0x84c00004 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-three128|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 1=0x01d08200 --blk 6=0x42800000 --blk 7=0x42800000 --blk 8=0x42800000 --blk 9=0x42800000 --vdm 2=0x84c00006 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-two128-shift|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 1=0x01d08200 --blk 6=0x42a00000 --blk 7=0x42800000 --blk 8=0x42800000 --blk 9=0x42800000 --vdm 2=0x84c00004 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-three64|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 6 --blk 1=0x01d08200 --blk 6=0x42000000 --blk 7=0x42000000 --blk 8=0x42000000 --blk 9=0x42000000 --vdm 2=0x84c00006 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ln-two128-w40|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 1=0x01d08200 --blk 6=0x42800000 --blk 7=0x42800000 --blk 8=0x42800000 --blk 9=0x42800000 --blk 2=0x000040f0 --vdm 2=0x84c00004 --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-ctl64|fit|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x42000000 --blk 7=0x42000000 --blk 8=0x42000000 --blk 9=0x42000000 --vdm 2=0x88c00003 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-ctl128|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 1=0x01d18200 --blk 6=0x42800000 --blk 7=0x42800000 --blk 8=0x42800000 --blk 9=0x42800000 --vdm 2=0x88c00003 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-b-16m|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 1=0x01d18200 --blk 6=0x427fc000 --blk 7=0x42800000 --blk 8=0x427fc000 --blk 9=0x42800000 --vdm 2=0x88c00006 --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-b-16|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 1=0x01d18200 --blk 6=0x42800000 --blk 7=0x42800000 --blk 8=0x42800000 --blk 9=0x42800000 --vdm 2=0x88c00006 --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-b-c32m|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 1=0x01d18200 --blk 6=0x429fe000 --blk 7=0x42800000 --blk 8=0x427fc000 --blk 9=0x42800000 --vdm 2=0x88c00006 --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-b-c32|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 1=0x01d18200 --blk 6=0x42a00000 --blk 7=0x42800000 --blk 8=0x42800000 --blk 9=0x42800000 --vdm 2=0x88c00006 --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-b-d32m|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 1=0x01d18200 --blk 6=0x429fe000 --blk 7=0x42800000 --blk 8=0x429fe000 --blk 9=0x42800000 --vdm 2=0x88c00006 --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-b-d32|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 1=0x01d18200 --blk 6=0x42a00000 --blk 7=0x42800000 --blk 8=0x42a00000 --blk 9=0x42800000 --vdm 2=0x88c00006 --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-b-e48m|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 1=0x01d18200 --blk 6=0x42bfe000 --blk 7=0x42800000 --blk 8=0x429fe000 --blk 9=0x42800000 --vdm 2=0x88c00006 --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-b-e48|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 1=0x01d18200 --blk 6=0x42c00000 --blk 7=0x42800000 --blk 8=0x42a00000 --blk 9=0x42800000 --vdm 2=0x88c00006 --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-w20-64|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x42000000 --blk 7=0x42000000 --blk 8=0x42000000 --blk 9=0x42000000 --blk 2=0x000020f0 --vdm 2=0x88c00003 --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-w40-64|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x42000000 --blk 7=0x42000000 --blk 8=0x42000000 --blk 9=0x42000000 --blk 2=0x000040f0 --vdm 2=0x88c00003 --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-w80-64|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x42000000 --blk 7=0x42000000 --blk 8=0x42000000 --blk 9=0x42000000 --blk 2=0x000080f0 --vdm 2=0x88c00003 --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-wf0-64|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x42000000 --blk 7=0x42000000 --blk 8=0x42000000 --blk 9=0x42000000 --blk 2=0x0000f0f0 --vdm 2=0x88c00003 --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-f-c-w10|fit|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --blk 2=0x000010f0 --vdm 2=0x88c00003 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-f-c-w20|fit|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --blk 2=0x000020f0 --vdm 2=0x88c00003 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-f-c-w40|fit|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --blk 2=0x000040f0 --vdm 2=0x88c00003 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-f-c-w00|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --blk 2=0x000000f0 --vdm 2=0x88c00003 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-f-c-w08|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --blk 2=0x000008f0 --vdm 2=0x88c00003 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-f-c-w80|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --blk 2=0x000080f0 --vdm 2=0x88c00003 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-f-c-wf0|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --blk 2=0x0000f0f0 --vdm 2=0x88c00003 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-f-k-w10|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x41b00000 --blk 7=0x41800000 --blk 8=0x41b00000 --blk 9=0x41800000 --blk 2=0x000010f0 --vdm 2=0x88c00003 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-f-k-w20|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x41b00000 --blk 7=0x41800000 --blk 8=0x41b00000 --blk 9=0x41800000 --blk 2=0x000020f0 --vdm 2=0x88c00003 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-f-k-w40|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x41b00000 --blk 7=0x41800000 --blk 8=0x41b00000 --blk 9=0x41800000 --blk 2=0x000040f0 --vdm 2=0x88c00003 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-f-k-w80|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x41b00000 --blk 7=0x41800000 --blk 8=0x41b00000 --blk 9=0x41800000 --blk 2=0x000080f0 --vdm 2=0x88c00003 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-f-k-wf0|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x41b00000 --blk 7=0x41800000 --blk 8=0x41b00000 --blk 9=0x41800000 --blk 2=0x0000f0f0 --vdm 2=0x88c00003 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
pt-o-c-s1|heldout|64|64|probe --tri vtxuse --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --blk 2=0x000010f0 --vdm 2=0x88c00003 --vtx-coords 1 --slot "pixel=$S/p1131-green__0.bin" --pixels --dump-render "$W/dump" "$S/p1131-psize__0.bin"
pt-o-c-s8|heldout|64|64|probe --tri vtxuse --temps 32 --width 64 --height 64 --blk 1=0x01d18200 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --blk 2=0x000010f0 --vdm 2=0x88c00003 --vtx-coords 1 --slot "pixel=$S/p1131-green__0.bin" --pixels --dump-render "$W/dump" "$S/p1131-psize__1.bin"
TABLE
)
run_table "$TABLE"
health </dev/null || true
echo "## end"
