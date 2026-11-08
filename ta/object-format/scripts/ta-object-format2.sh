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
SCRIPT_NAME=ta-object-format2
. "$(dirname "$0")/lib1131.sh"
for f in "$S"/p1131-green__0.bin "$S"/pix_pa0.bin; do
	[ -f "$f" ] || { echo "no $f: run stage-p1131.sh and copy"; exit 1; }
done
begin
TABLE=$(cat <<'TABLE'
f2-n4-s1|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 4 --blk 16=1 --blk 17=1 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
f2-n4-s2|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 4 --blk 16=2 --blk 17=1 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
f2-n4-s3|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 4 --blk 16=3 --blk 17=1 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
f2-n4-s4|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 4 --blk 16=4 --blk 17=1 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
f2-n4-s5|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 4 --blk 16=5 --blk 17=1 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
f2-n8-34|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 8 --blk 16=35 --blk 17=3 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
f2-n8-55|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 8 --blk 16=45 --blk 17=3 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
f2-n8-15|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 8 --blk 16=41 --blk 17=3 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
f2-n8-52u|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 8 --blk 16=21 --blk 17=2 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
f2-n11-235|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 11 --blk 16=346 --blk 17=7 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
f2-n11-111|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 11 --blk 16=73 --blk 17=7 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
f2-n11-2u2|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 11 --blk 16=146 --blk 17=5 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
TABLE
)
run_table "$TABLE"
health </dev/null || true
echo "## end"
