#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.31 vdm-state-units (draft phase): Q047 (which unit takes a state block: the marks of a two-block stream).
# Two objects (12 vertices, --obj2 6), each with its own state block. One block carries three marks:
# its viewport x offset moved 16 pixels (the MTE side), ISP word 1 = 0x20f0 against 0x10f0 (the TA
# copies it into the object), and its own pixel shader (green, the second block's; blue the first's).
# Block 2 variant: the second block marked, word 9 changed. Block 1 variant: the first block marked,
# word 1 changed. Every field value that completed in E427 and E414, twice, a control per variant
# first: a field that names units must move some marks and not others; a size or validity field
# moves them together. A control that does not show all three marks voids the job (plan.md 5).
# Raw outputs are KEPT: every tool output, whole, gzip (mtime 0) in $KEEP/NAME.txt.gz, the render's
# dumps beside it (NAME.param.bin.gz, NAME.tadata.bin.gz), the raw size and sha256 printed ("kept
# ..."), the case table in $KEEP/cases.tsv (with the exact tool arguments of every job) and the
# kernel log of the run (journalctl -k, as the short ring buffer loses it) in $KEEP/kernel.log.
# Recompute with recompute/recompute_p1131.py. After a failed job the GPU is reset (3 s), a plain
# 64x64 triangle must draw exactly (retry after 5 s waits); three failed recoveries stop the script.
# No clock-gate register is written (see lib1131.sh). Root through sudo -n.
SCRIPT_NAME=vdm-state-units
. "$(dirname "$0")/lib1131.sh"
for f in "$S"/p1131-green__0.bin "$S"/pix_pa0.bin; do
	[ -f "$f" ] || { echo "no $f: run stage-p1131.sh and copy"; exit 1; }
done
begin
TABLE=$(cat <<'TABLE'
st-b2-ctl-r1|control|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-blue__0.bin"
st-b2-ctl-r2|control|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-blue__0.bin"
st-b2-b8-r1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9^=0x00000100 "$S/p1131-blue__0.bin"
st-b2-b8-r2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9^=0x00000100 "$S/p1131-blue__0.bin"
st-b2-b119-0-r1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9^=0x00000400 "$S/p1131-blue__0.bin"
st-b2-b119-0-r2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9^=0x00000400 "$S/p1131-blue__0.bin"
st-b2-b119-3-r1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9^=0x00000200 "$S/p1131-blue__0.bin"
st-b2-b119-3-r2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9^=0x00000200 "$S/p1131-blue__0.bin"
st-b2-b119-4-r1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9^=0x00000c00 "$S/p1131-blue__0.bin"
st-b2-b119-4-r2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9^=0x00000c00 "$S/p1131-blue__0.bin"
st-b2-b119-5-r1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9^=0x00000e00 "$S/p1131-blue__0.bin"
st-b2-b119-5-r2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9^=0x00000e00 "$S/p1131-blue__0.bin"
st-b2-b1513-2-r1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9^=0x00006000 "$S/p1131-blue__0.bin"
st-b2-b1513-2-r2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9^=0x00006000 "$S/p1131-blue__0.bin"
st-b2-b1513-3-r1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9^=0x00004000 "$S/p1131-blue__0.bin"
st-b2-b1513-3-r2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9^=0x00004000 "$S/p1131-blue__0.bin"
st-b2-b1513-4-r1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9^=0x0000a000 "$S/p1131-blue__0.bin"
st-b2-b1513-4-r2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 9^=0x0000a000 "$S/p1131-blue__0.bin"
st-b1-ctl-r1|control|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-blue__0.bin"
st-b1-ctl-r2|control|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-blue__0.bin"
st-b1-b8-r1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 1^=0x00000100 "$S/p1131-blue__0.bin"
st-b1-b8-r2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 1^=0x00000100 "$S/p1131-blue__0.bin"
st-b1-b119-0-r1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 1^=0x00000400 "$S/p1131-blue__0.bin"
st-b1-b119-0-r2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 1^=0x00000400 "$S/p1131-blue__0.bin"
st-b1-b119-3-r1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 1^=0x00000200 "$S/p1131-blue__0.bin"
st-b1-b119-3-r2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 1^=0x00000200 "$S/p1131-blue__0.bin"
st-b1-b119-4-r1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 1^=0x00000c00 "$S/p1131-blue__0.bin"
st-b1-b119-4-r2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 1^=0x00000c00 "$S/p1131-blue__0.bin"
st-b1-b119-5-r1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 1^=0x00000e00 "$S/p1131-blue__0.bin"
st-b1-b119-5-r2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 1^=0x00000e00 "$S/p1131-blue__0.bin"
st-b1-b1513-2-r1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 1^=0x00006000 "$S/p1131-blue__0.bin"
st-b1-b1513-2-r2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 1^=0x00006000 "$S/p1131-blue__0.bin"
st-b1-b1513-3-r1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 1^=0x00004000 "$S/p1131-blue__0.bin"
st-b1-b1513-3-r2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 1^=0x00004000 "$S/p1131-blue__0.bin"
st-b1-b1513-4-r1|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 1^=0x0000a000 "$S/p1131-blue__0.bin"
st-b1-b1513-4-r2|heldout|64|64|probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --blk 6=0x42400000 --blk 2=0x000020f0 --obj2 6 --obj2-blk 6=0x42000000 --obj2-blk 2=0x000010f0 --obj2-pixel "$S/p1131-green__0.bin" --dump-render "$W/dump" --vdm 1^=0x0000a000 "$S/p1131-blue__0.bin"
TABLE
)
run_table "$TABLE"
health </dev/null || true
echo "## end"
