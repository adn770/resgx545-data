#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.31 ta-tri-boundary (draft phase): Q070 (the region test's boundary rules on triangles it was not fitted to).
# Triangles with a vertex exactly 2/16 pixel before a tile or region line, five copies moved 1/16
# pixel each (so the copies cover -2/16 to +2/16 round the line), at 64, 128 and 256 pixels (the
# viewport scale W/2); three controls on E180's geometry. H70-T1 (the rule fitted post hoc to
# E180's 26 triangles) is the declared prediction; H70-T0 (the landed record's) is scored too.
# Raw outputs are KEPT: every tool output, whole, gzip (mtime 0) in $KEEP/NAME.txt.gz, the render's
# dumps beside it (NAME.param.bin.gz, NAME.tadata.bin.gz), the raw size and sha256 printed ("kept
# ..."), the case table in $KEEP/cases.tsv (with the exact tool arguments of every job) and the
# kernel log of the run (journalctl -k, as the short ring buffer loses it) in $KEEP/kernel.log.
# Recompute with recompute/recompute_p1131.py. After a failed job the GPU is reset (3 s), a plain
# 64x64 triangle must draw exactly (retry after 5 s waits); three failed recoveries stop the script.
# No clock-gate register is written (see lib1131.sh). Root through sudo -n.
SCRIPT_NAME=ta-tri-boundary
. "$(dirname "$0")/lib1131.sh"
for f in "$S"/p1131-green__0.bin "$S"/pix_pa0.bin; do
	[ -f "$f" ] || { echo "no $f: run stage-p1131.sh and copy"; exit 1; }
done
begin
TABLE=$(cat <<'TABLE'
tb-ctl-e180a-r1|fit|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 6=0x42800000 --blk 7=0x42800000 --blk 8=0x42800000 --blk 9=0x42800000 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-ctl-e180a-r2|fit|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 6=0x42800000 --blk 7=0x42800000 --blk 8=0x42800000 --blk 9=0x42800000 --pixels --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-ctl-e180b|fit|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --blk 6=0x429c0000 --blk 7=0x42800000 --blk 8=0x42800000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w64-k0-16-16|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --blk 6=0x421f8000 --blk 7=0x42000000 --blk 8=0x421f8000 --blk 9=0x42000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w64-k1-16-16|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --blk 6=0xc1020000 --blk 7=0x42000000 --blk 8=0x41df0000 --blk 9=0x42000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w64-k0-32-16|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --blk 6=0x425f8000 --blk 7=0x42000000 --blk 8=0x421f8000 --blk 9=0x42000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w64-k1-32-16|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --blk 6=0x40fc0000 --blk 7=0x42000000 --blk 8=0x41df0000 --blk 9=0x42000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w64-k0-32-32|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --blk 6=0x425f8000 --blk 7=0x42000000 --blk 8=0x425f8000 --blk 9=0x42000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w64-k1-32-32|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --blk 6=0x40fc0000 --blk 7=0x42000000 --blk 8=0x422f8000 --blk 9=0x42000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w64-k0-16-32|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --blk 6=0x421f8000 --blk 7=0x42000000 --blk 8=0x425f8000 --blk 9=0x42000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w64-k1-16-32|heldout|64|64|probe --tri pixel --temps 32 --width 64 --height 64 --vertices 15 --blk 6=0xc1020000 --blk 7=0x42000000 --blk 8=0x422f8000 --blk 9=0x42000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w128-k0-16-16|fit|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 15 --blk 6=0x427f8000 --blk 7=0x42800000 --blk 8=0x427f8000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w128-k1-16-16|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 15 --blk 6=0xc2008000 --blk 7=0x42800000 --blk 8=0x421f8000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w128-k0-32-16|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 15 --blk 6=0x429fc000 --blk 7=0x42800000 --blk 8=0x427f8000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w128-k1-32-16|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 15 --blk 6=0xc1810000 --blk 7=0x42800000 --blk 8=0x421f8000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w128-k0-32-32|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 15 --blk 6=0x429fc000 --blk 7=0x42800000 --blk 8=0x429fc000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w128-k1-32-32|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 15 --blk 6=0xc1810000 --blk 7=0x42800000 --blk 8=0x425f8000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w128-k0-16-32|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 15 --blk 6=0x427f8000 --blk 7=0x42800000 --blk 8=0x429fc000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w128-k1-16-32|heldout|128|128|probe --tri pixel --temps 32 --width 128 --height 128 --vertices 15 --blk 6=0xc2008000 --blk 7=0x42800000 --blk 8=0x425f8000 --blk 9=0x42800000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w256-k0-16-16|heldout|256|256|probe --tri pixel --temps 32 --width 256 --height 256 --vertices 15 --blk 6=0x42dfc000 --blk 7=0x43000000 --blk 8=0x42dfc000 --blk 9=0x43000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w256-k1-16-16|heldout|256|256|probe --tri pixel --temps 32 --width 256 --height 256 --vertices 15 --blk 6=0xc2a04000 --blk 7=0x43000000 --blk 8=0x427f8000 --blk 9=0x43000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w256-k0-32-16|heldout|256|256|probe --tri pixel --temps 32 --width 256 --height 256 --vertices 15 --blk 6=0x42ffc000 --blk 7=0x43000000 --blk 8=0x42dfc000 --blk 9=0x43000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w256-k1-32-16|heldout|256|256|probe --tri pixel --temps 32 --width 256 --height 256 --vertices 15 --blk 6=0xc2804000 --blk 7=0x43000000 --blk 8=0x427f8000 --blk 9=0x43000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w256-k0-32-32|heldout|256|256|probe --tri pixel --temps 32 --width 256 --height 256 --vertices 15 --blk 6=0x42ffc000 --blk 7=0x43000000 --blk 8=0x42ffc000 --blk 9=0x43000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w256-k1-32-32|heldout|256|256|probe --tri pixel --temps 32 --width 256 --height 256 --vertices 15 --blk 6=0xc2804000 --blk 7=0x43000000 --blk 8=0x429fc000 --blk 9=0x43000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w256-k0-16-32|heldout|256|256|probe --tri pixel --temps 32 --width 256 --height 256 --vertices 15 --blk 6=0x42dfc000 --blk 7=0x43000000 --blk 8=0x42ffc000 --blk 9=0x43000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
tb-w256-k1-16-32|heldout|256|256|probe --tri pixel --temps 32 --width 256 --height 256 --vertices 15 --blk 6=0xc2a04000 --blk 7=0x43000000 --blk 8=0x429fc000 --blk 9=0x43000000 --dump-render "$W/dump" "$S/p1131-green__0.bin"
TABLE
)
run_table "$TABLE"
health </dev/null || true
echo "## end"
