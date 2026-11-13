#!/bin/bash
# SPDX-License-Identifier: MIT
# lead/dryrun_checks.sh: the plan's three dry-run checks (rank-round9.md, session r9-x) on the
# library mock of tool t4's source (resgx545 4623753 userspace/libsgxfive/tools/sgxfive-test.c,
# sha256 703cbcea..., checked first), built for the Mac from `git archive` into debug/tool4-src
# (never shipped, never staged). Check 3 (scratch extents) is tests/test_gen.py's
# test_t3_scratch_holds_every_read. Mac only. Usage: bash lead/dryrun_checks.sh > lead/dryrun_checks.out
set -u
KP=$(cd "$(dirname "$0")/.." && pwd)
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
SRC=$KP/debug/tool4-src
WANT=703cbceaae8cdff3eda280b7ef89f3c5ef14ba7d378dd269bc66ef714aaead69
rm -rf "$SRC"; mkdir -p "$SRC"
git -C "$MAIN" archive 4623753 userspace/libsgxfive include/uapi | tar -x -C "$SRC"
got=$(shasum -a 256 "$SRC/userspace/libsgxfive/tools/sgxfive-test.c" | cut -d' ' -f1)
[ "$got" = "$WANT" ] || { echo "sgxfive-test.c is not the rgn4 tool's ($got)"; exit 1; }
make -s -C "$SRC/userspace/libsgxfive" build/sgxfive-test > /dev/null 2>&1 || { echo "build failed"; exit 1; }
T=$SRC/userspace/libsgxfive/build/sgxfive-test
W=$(mktemp -d "$KP/debug/dry.XXXXXX")
export SGXFIVE_KPOKE=$W/kpoke SGXFIVE_DEBUGFS=$W
run() { echo "### $1"; shift; "$T" --mock "$@" > "$W/o" 2>&1; rc=$?
	grep -E '^job:|^tri: vertices|^depth|^stencil|bad option|usage|need' "$W/o" | head -4; echo "rc $rc"; }
echo "## check 1 (R9-D): ISP word 2 with the ZLS stencil buffers"
run "tri with --isp2 (the plan's Q121 row): refused" tri --width 64 --height 32 --depth --stencil --stencil-store --isp2 0x0e490000
run "probe --tri with --stencil (the other way): refused" probe --tri pixpds --stencil "$KP/bins/t3-ctl.bin"
echo "## check 2 (R9-E): --tri-unit 0 near 2^30, and the unit used"
run "--tri-unit 0: refused" tri --width 64 --height 64 --tri-unit 0 --tri-v 0,0,1,0,0,1
run "--tri-unit 5, -2^30 (-2^25 pixels): taken, printed back" tri --width 64 --height 64 --max-width 64 --max-height 64 --tri-unit 5 --tri-v 1800,248,-1073741824,-268435456,1808,1784
run "--tri-unit 5, +2^30: refused" tri --width 64 --height 64 --tri-unit 5 --tri-v 0,0,1073741824,0,0,64
rm -rf "$W"
