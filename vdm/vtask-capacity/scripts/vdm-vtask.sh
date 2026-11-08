#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.31 vdm-vtask (draft phase): Q094 (vertices per vertex task against output rows).
# 126 vertices (42 triangles) with N = 2, 4, 8 and 11 coordinate outputs (2, 2, 3 and 4 output
# rows of four dwords) and the vertex task's MAX_VERTICES (vdm:6 bits 31:28) at 15 (the control and
# most GLES2 draws), 13, 9, 7, 2 (the closed driver's values), 3 and 1. The vertex program writes
# the vertex's clip x and y to o4 and o5, so the TA's object holds each vertex's identity: the
# recompute counts the 126 distinct vertices that reach the objects (H94-none: all of them).
# Raw outputs are KEPT: every tool output, whole, gzip (mtime 0) in $KEEP/NAME.txt.gz, the render's
# dumps beside it (NAME.param.bin.gz, NAME.tadata.bin.gz), the raw size and sha256 printed ("kept
# ..."), the case table in $KEEP/cases.tsv (with the exact tool arguments of every job) and the
# kernel log of the run (journalctl -k, as the short ring buffer loses it) in $KEEP/kernel.log.
# Recompute with recompute/recompute_p1131.py. After a failed job the GPU is reset (3 s), a plain
# 64x64 triangle must draw exactly (retry after 5 s waits); three failed recoveries stop the script.
# No clock-gate register is written (see lib1131.sh). Root through sudo -n.
SCRIPT_NAME=vdm-vtask
. "$(dirname "$0")/lib1131.sh"
for f in "$S"/p1131-green__0.bin "$S"/pix_pa0.bin; do
	[ -f "$f" ] || { echo "no $f: run stage-p1131.sh and copy"; exit 1; }
done
begin
TABLE=$(cat <<'TABLE'
vt-n2-f15|fit|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 2 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c2.bin" "$S/p1131-fmt-2__0.bin"
vt-n2-f13|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 2 --vdm 6^=0x20000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c2.bin" "$S/p1131-fmt-2__0.bin"
vt-n2-f9|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 2 --vdm 6^=0x60000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c2.bin" "$S/p1131-fmt-2__0.bin"
vt-n2-f7|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 2 --vdm 6^=0x80000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c2.bin" "$S/p1131-fmt-2__0.bin"
vt-n2-f2|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 2 --vdm 6^=0xd0000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c2.bin" "$S/p1131-fmt-2__0.bin"
vt-n2-f3|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 2 --vdm 6^=0xc0000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c2.bin" "$S/p1131-fmt-2__0.bin"
vt-n2-f1|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 2 --vdm 6^=0xe0000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c2.bin" "$S/p1131-fmt-2__0.bin"
vt-n4-f15|fit|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 4 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
vt-n4-f13|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 4 --vdm 6^=0x20000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
vt-n4-f9|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 4 --vdm 6^=0x60000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
vt-n4-f7|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 4 --vdm 6^=0x80000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
vt-n4-f2|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 4 --vdm 6^=0xd0000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
vt-n4-f3|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 4 --vdm 6^=0xc0000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
vt-n4-f1|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 4 --vdm 6^=0xe0000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
vt-n8-f15|fit|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 8 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
vt-n8-f13|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 8 --vdm 6^=0x20000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
vt-n8-f9|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 8 --vdm 6^=0x60000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
vt-n8-f7|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 8 --vdm 6^=0x80000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
vt-n8-f2|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 8 --vdm 6^=0xd0000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
vt-n8-f3|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 8 --vdm 6^=0xc0000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
vt-n8-f1|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 8 --vdm 6^=0xe0000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
vt-n11-f15|fit|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 11 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
vt-n11-f13|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 11 --vdm 6^=0x20000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
vt-n11-f9|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 11 --vdm 6^=0x60000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
vt-n11-f7|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 11 --vdm 6^=0x80000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
vt-n11-f2|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 11 --vdm 6^=0xd0000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
vt-n11-f3|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 11 --vdm 6^=0xc0000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
vt-n11-f1|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 11 --vdm 6^=0xe0000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
TABLE
)
run_table "$TABLE"
health </dev/null || true
echo "## end"
