#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.31 ta-object-format (draft phase): Q070 (the object's format word and set masks over coordinate outputs).
# One triangle with N coordinate outputs (N = 2 to 11 in sets of four and the rest), the coordinate
# size word (blk:16, 3 bits a set) and format word (blk:17, one bit a set) set, the TA's object read
# from the dump: the dwords a vertex takes, the format word's two bytes, the four set masks. Fit:
# five of E308's settings (N = 4). Held out: seven values of N with six size/format patterns each.
# Models (plan.md section 3): H70-F stored = 1 + sum of the sets' dwords (half precision halves a
# set, rounded up), iterated = 1 + N; H70-M mask i bit j for set j: format bit, size 1, size 3 or 5,
# size 4 or 5. Needs the pixel PDS program of E437 (stage-p1131.sh), as E308's csize probes did.
# Raw outputs are KEPT: every tool output, whole, gzip (mtime 0) in $KEEP/NAME.txt.gz, the render's
# dumps beside it (NAME.param.bin.gz, NAME.tadata.bin.gz), the raw size and sha256 printed ("kept
# ..."), the case table in $KEEP/cases.tsv (with the exact tool arguments of every job) and the
# kernel log of the run (journalctl -k, as the short ring buffer loses it) in $KEEP/kernel.log.
# Recompute with recompute/recompute_p1131.py. After a failed job the GPU is reset (3 s), a plain
# 64x64 triangle must draw exactly (retry after 5 s waits); three failed recoveries stop the script.
# No clock-gate register is written (see lib1131.sh). Root through sudo -n.
SCRIPT_NAME=vdm-vtask4
. "$(dirname "$0")/lib1131.sh"
for f in "$S"/p1131-green__0.bin "$S"/pix_pa0.bin; do
	[ -f "$f" ] || { echo "no $f: run stage-p1131.sh and copy"; exit 1; }
done
begin
TABLE=$(cat <<'TABLE'
v4-n6-f10-r1|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 6 --vdm 6^=0x50000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c6.bin" "$S/p1131-fmt-6__0.bin"
v4-n6-f10-r2|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 6 --vdm 6^=0x50000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c6.bin" "$S/p1131-fmt-6__0.bin"
v4-n6-f10-r3|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 6 --vdm 6^=0x50000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c6.bin" "$S/p1131-fmt-6__0.bin"
v4-n8-f10-r1|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 8 --vdm 6^=0x50000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
v4-n8-f10-r2|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 8 --vdm 6^=0x50000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
v4-n5-f11-r1|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 5 --vdm 6^=0x40000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c5.bin" "$S/p1131-fmt-5__0.bin"
v4-n5-f11-r2|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 5 --vdm 6^=0x40000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c5.bin" "$S/p1131-fmt-5__0.bin"
v4-n9-f8-r1|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 9 --vdm 6^=0x70000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c9.bin" "$S/p1131-fmt-9__0.bin"
v4-n9-f8-r2|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 9 --vdm 6^=0x70000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c9.bin" "$S/p1131-fmt-9__0.bin"
v4-n6-f9-r1|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 6 --vdm 6^=0x60000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c6.bin" "$S/p1131-fmt-6__0.bin"
v4-n6-f9-r2|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 6 --vdm 6^=0x60000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c6.bin" "$S/p1131-fmt-6__0.bin"
v4-n11-f8-r1|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 11 --vdm 6^=0x70000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
v4-n11-f8-r2|heldout|64|64|probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 11 --vdm 6^=0x70000000 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
TABLE
)
run_table "$TABLE"
health </dev/null || true
echo "## end"
