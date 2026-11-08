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
SCRIPT_NAME=ta-tri-corner
. "$(dirname "$0")/lib1131.sh"
for f in "$S"/p1131-green__0.bin "$S"/pix_pa0.bin; do
	[ -f "$f" ] || { echo "no $f: run stage-p1131.sh and copy"; exit 1; }
done
begin
TABLE=$(cat <<'TABLE'
tc-16-16|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 6=0x41800000 --blk 7=0x42800000 --blk 8=0x42500000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tc-16-32|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 6=0x41800000 --blk 7=0x42800000 --blk 8=0x42880000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tc-32-16|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 6=0x42000000 --blk 7=0x42800000 --blk 8=0x42500000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tc-32-32|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 6=0x42000000 --blk 7=0x42800000 --blk 8=0x42880000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tc-48-16|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 6=0x42400000 --blk 7=0x42800000 --blk 8=0x42500000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tc-48-32|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 6=0x42400000 --blk 7=0x42800000 --blk 8=0x42880000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tc-64-16|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 6=0x42800000 --blk 7=0x42800000 --blk 8=0x42500000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tc-64-32|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 6 --blk 6=0x42800000 --blk 7=0x42800000 --blk 8=0x42880000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
TABLE
)
run_table "$TABLE"
health </dev/null || true
echo "## end"
