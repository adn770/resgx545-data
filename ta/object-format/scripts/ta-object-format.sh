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
SCRIPT_NAME=ta-object-format
. "$(dirname "$0")/lib1131.sh"
for f in "$S"/p1131-green__0.bin "$S"/pix_pa0.bin; do
	[ -f "$f" ] || { echo "no $f: run stage-p1131.sh and copy"; exit 1; }
done
begin
TABLE=$(cat <<'TABLE'
fmt-fit-n4-cs1-cf0|fit|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 4 --blk 16=1 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
fmt-fit-n4-cs3-cf0|fit|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 4 --blk 16=3 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
fmt-fit-n4-cs5-cf0|fit|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 4 --blk 16=5 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
fmt-fit-n4-cs5-cf1|fit|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 4 --blk 16=5 --blk 17=1 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
fmt-fit-n4-cs18-cf3|fit|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 4 --blk 16=18 --blk 17=3 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c4.bin" "$S/p1131-fmt-4__0.bin"
fmt-n2-s1|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 2 --blk 16=1 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c2.bin" "$S/p1131-fmt-2__0.bin"
fmt-n2-s3|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 2 --blk 16=3 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c2.bin" "$S/p1131-fmt-2__0.bin"
fmt-n2-s5|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 2 --blk 16=5 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c2.bin" "$S/p1131-fmt-2__0.bin"
fmt-n2-mix|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 2 --blk 16=1 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c2.bin" "$S/p1131-fmt-2__0.bin"
fmt-n2-f1|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 2 --blk 16=2 --blk 17=1 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c2.bin" "$S/p1131-fmt-2__0.bin"
fmt-n2-alt|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 2 --blk 16=5 --blk 17=1 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c2.bin" "$S/p1131-fmt-2__0.bin"
fmt-n3-s1|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 3 --blk 16=1 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c3.bin" "$S/p1131-fmt-3__0.bin"
fmt-n3-s3|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 3 --blk 16=3 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c3.bin" "$S/p1131-fmt-3__0.bin"
fmt-n3-s5|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 3 --blk 16=5 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c3.bin" "$S/p1131-fmt-3__0.bin"
fmt-n3-mix|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 3 --blk 16=1 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c3.bin" "$S/p1131-fmt-3__0.bin"
fmt-n3-f1|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 3 --blk 16=2 --blk 17=1 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c3.bin" "$S/p1131-fmt-3__0.bin"
fmt-n3-alt|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 3 --blk 16=5 --blk 17=1 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c3.bin" "$S/p1131-fmt-3__0.bin"
fmt-n5-s1|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 5 --blk 16=9 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c5.bin" "$S/p1131-fmt-5__0.bin"
fmt-n5-s3|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 5 --blk 16=27 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c5.bin" "$S/p1131-fmt-5__0.bin"
fmt-n5-s5|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 5 --blk 16=45 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c5.bin" "$S/p1131-fmt-5__0.bin"
fmt-n5-mix|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 5 --blk 16=25 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c5.bin" "$S/p1131-fmt-5__0.bin"
fmt-n5-f1|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 5 --blk 16=18 --blk 17=3 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c5.bin" "$S/p1131-fmt-5__0.bin"
fmt-n5-alt|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 5 --blk 16=29 --blk 17=5 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c5.bin" "$S/p1131-fmt-5__0.bin"
fmt-n6-s1|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 6 --blk 16=9 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c6.bin" "$S/p1131-fmt-6__0.bin"
fmt-n6-s3|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 6 --blk 16=27 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c6.bin" "$S/p1131-fmt-6__0.bin"
fmt-n6-s5|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 6 --blk 16=45 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c6.bin" "$S/p1131-fmt-6__0.bin"
fmt-n6-mix|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 6 --blk 16=25 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c6.bin" "$S/p1131-fmt-6__0.bin"
fmt-n6-f1|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 6 --blk 16=18 --blk 17=3 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c6.bin" "$S/p1131-fmt-6__0.bin"
fmt-n6-alt|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 6 --blk 16=29 --blk 17=5 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c6.bin" "$S/p1131-fmt-6__0.bin"
fmt-n8-s1|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 8 --blk 16=9 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
fmt-n8-s3|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 8 --blk 16=27 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
fmt-n8-s5|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 8 --blk 16=45 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
fmt-n8-mix|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 8 --blk 16=25 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
fmt-n8-f1|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 8 --blk 16=18 --blk 17=3 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
fmt-n8-alt|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 8 --blk 16=29 --blk 17=5 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c8.bin" "$S/p1131-fmt-8__0.bin"
fmt-n9-s1|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 9 --blk 16=73 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c9.bin" "$S/p1131-fmt-9__0.bin"
fmt-n9-s3|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 9 --blk 16=219 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c9.bin" "$S/p1131-fmt-9__0.bin"
fmt-n9-s5|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 9 --blk 16=365 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c9.bin" "$S/p1131-fmt-9__0.bin"
fmt-n9-mix|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 9 --blk 16=281 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c9.bin" "$S/p1131-fmt-9__0.bin"
fmt-n9-f1|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 9 --blk 16=146 --blk 17=7 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c9.bin" "$S/p1131-fmt-9__0.bin"
fmt-n9-alt|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 9 --blk 16=93 --blk 17=5 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c9.bin" "$S/p1131-fmt-9__0.bin"
fmt-n11-s1|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 11 --blk 16=73 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
fmt-n11-s3|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 11 --blk 16=219 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
fmt-n11-s5|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 11 --blk 16=365 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
fmt-n11-mix|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 11 --blk 16=281 --blk 17=0 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
fmt-n11-f1|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 11 --blk 16=146 --blk 17=7 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
fmt-n11-alt|heldout|64|64|probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --vtx-coords 11 --blk 16=93 --blk 17=5 --dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c11.bin" "$S/p1131-fmt-11__0.bin"
TABLE
)
run_table "$TABLE"
health </dev/null || true
echo "## end"
