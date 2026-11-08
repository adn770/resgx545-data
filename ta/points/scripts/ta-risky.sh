#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.31 ta-risky (draft phase): Q070 and Q117 (OUTSEL bits against the format word and the point size).
# RISKY, run after the safe scripts: the OUTSEL word (blk:13) with one bit flipped at a time (bits 11
# and 12 are the known controls: the colour and 1/w bits that set format bits 19 and 18), the object's
# format word read; then, for the unknown bits, a point job whose vertex program writes the size to
# the one coordinate output (1.0 and 8.0) with that bit flipped: a bit that makes the footprint
# follow the size shows where a size comes from. Faults and hangs are expected for some bits.
# Raw outputs are KEPT: every tool output, whole, gzip (mtime 0) in $KEEP/NAME.txt.gz, the render's
# dumps beside it (NAME.param.bin.gz, NAME.tadata.bin.gz), the raw size and sha256 printed ("kept
# ..."), the case table in $KEEP/cases.tsv (with the exact tool arguments of every job) and the
# kernel log of the run (journalctl -k, as the short ring buffer loses it) in $KEEP/kernel.log.
# Recompute with recompute/recompute_p1131.py. After a failed job the GPU is reset (3 s), a plain
# 64x64 triangle must draw exactly (retry after 5 s waits); three failed recoveries stop the script.
# No clock-gate register is written (see lib1131.sh). Root through sudo -n.
SCRIPT_NAME=ta-risky
. "$(dirname "$0")/lib1131.sh"
for f in "$S"/p1131-green__0.bin "$S"/pix_pa0.bin; do
	[ -f "$f" ] || { echo "no $f: run stage-p1131.sh and copy"; exit 1; }
done
begin
TABLE=$(cat <<'TABLE'
of-outsel-b11|fit|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x00000800 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b12|fit|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x00001000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b8|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x00000100 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b9|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x00000200 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b10|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x00000400 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b13|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x00002000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b14|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x00004000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b15|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x00008000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b20|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x00100000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b21|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x00200000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b22|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x00400000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b23|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x00800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b24|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x01000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b25|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x02000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b26|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x04000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b27|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x08000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b28|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x10000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b29|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x20000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b30|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x40000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
of-outsel-b31|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --blk 13^=0x80000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
ps-outsel-b8-s1|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00000100 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__0.bin"
ps-outsel-b8-s8|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00000100 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__1.bin"
ps-outsel-b9-s1|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00000200 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__0.bin"
ps-outsel-b9-s8|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00000200 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__1.bin"
ps-outsel-b10-s1|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00000400 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__0.bin"
ps-outsel-b10-s8|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00000400 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__1.bin"
ps-outsel-b14-s1|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00004000 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__0.bin"
ps-outsel-b14-s8|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00004000 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__1.bin"
ps-outsel-b15-s1|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00008000 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__0.bin"
ps-outsel-b15-s8|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00008000 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__1.bin"
ps-outsel-b20-s1|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00100000 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__0.bin"
ps-outsel-b20-s8|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00100000 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__1.bin"
ps-outsel-b21-s1|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00200000 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__0.bin"
ps-outsel-b21-s8|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00200000 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__1.bin"
ps-outsel-b22-s1|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00400000 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__0.bin"
ps-outsel-b22-s8|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00400000 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__1.bin"
ps-outsel-b23-s1|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00800000 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__0.bin"
ps-outsel-b23-s8|heldout|64|64|probe --tri vtxuse --temps 32 --pixels --width 64 --height 64 --vtx-coords 1 --blk 1=0x01d18200 --blk 13^=0x00800000 --blk 6=0x41b40000 --blk 7=0x41800000 --blk 8=0x41b40000 --blk 9=0x41800000 --vdm 2=0x88c00003 --slot "pixel=$S/p1131-green__0.bin" --dump-render "$W/dump" "$S/p1131-psize__1.bin"
TABLE
)
run_table "$TABLE"
health </dev/null || true
echo "## end"
