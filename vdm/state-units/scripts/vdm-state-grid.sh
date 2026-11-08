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
SCRIPT_NAME=vdm-state-grid
. "$(dirname "$0")/lib1131.sh"
for f in "$S"/p1131-green__0.bin "$S"/pix_pa0.bin; do
	[ -f "$f" ] || { echo "no $f: run stage-p1131.sh and copy"; exit 1; }
done
begin
TABLE=$(cat <<'TABLE'
sg-v6-r0|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022c00 "$S/p1131-blue__0.bin"
sg-v6-r4|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022c04 "$S/p1131-blue__0.bin"
sg-v6-r6|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022c06 "$S/p1131-blue__0.bin"
sg-v6-r7|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022c07 "$S/p1131-blue__0.bin"
sg-v6-r9|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022c09 "$S/p1131-blue__0.bin"
sg-v6-r16|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022c10 "$S/p1131-blue__0.bin"
sg-v6-r255|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022cff "$S/p1131-blue__0.bin"
sg-v6-r5-1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022c05 "$S/p1131-blue__0.bin"
sg-v6-r5-2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022c05 "$S/p1131-blue__0.bin"
sg-v6-r5-3|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022c05 "$S/p1131-blue__0.bin"
sg-v1-r4|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022204 "$S/p1131-blue__0.bin"
sg-v1-r5|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022205 "$S/p1131-blue__0.bin"
sg-v1-r6|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022206 "$S/p1131-blue__0.bin"
sg-v1-r7|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022207 "$S/p1131-blue__0.bin"
sg-v2-r5|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022405 "$S/p1131-blue__0.bin"
sg-v7-r4|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022e04 "$S/p1131-blue__0.bin"
sg-v7-r5|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022e05 "$S/p1131-blue__0.bin"
sg-v7-r6|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022e06 "$S/p1131-blue__0.bin"
sg-v7-r9|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9=0x0a022e09 "$S/p1131-blue__0.bin"
TABLE
)
run_table "$TABLE"
health </dev/null || true
echo "## end"
