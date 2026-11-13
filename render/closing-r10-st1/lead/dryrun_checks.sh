#!/bin/bash
# SPDX-License-Identifier: MIT
# lead/dryrun_checks.sh: every row of r10-st1's table on the library mock of t10's bound source
# (resgx545 a581c06 userspace/libsgxfive/tools/sgxfive-test.c, sha256 23e1fa76..., checked first),
# built for the Mac from `git archive` into debug/libsrc-t10 (never shipped, never staged), WITH
# the kpoke file the depth rows write (as the kit's replay does since r10-tooling3 287031c). Prints each row's job line, the isp2
# line, the stencil store summary and the pixel rows. Mac only.
# Usage: bash lead/dryrun_checks.sh > lead/dryrun_checks.out
set -u
KP=$(cd "$(dirname "$0")/.." && pwd)
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
SRC=$KP/debug/libsrc-t10
WANT=23e1fa76d10bb4e7cfadb0985ac110d4681e4113f2f55f17dd81bdd4b2fe183b
rm -rf "$SRC"; mkdir -p "$SRC"
git -C "$MAIN" archive a581c06bb24d2f77e03d9b64f7ca1b2d5487b59f userspace/libsgxfive include/uapi | tar -x -C "$SRC"
got=$(shasum -a 256 "$SRC/userspace/libsgxfive/tools/sgxfive-test.c" | cut -d' ' -f1)
[ "$got" = "$WANT" ] || { echo "sgxfive-test.c is not t10's ($got)"; exit 1; }
make -s -C "$SRC/userspace/libsgxfive" build/sgxfive-test > /dev/null 2>&1 || { echo "build failed"; exit 1; }
T=$SRC/userspace/libsgxfive/build/sgxfive-test
W=$(mktemp -d "$KP/debug/dry.XXXXXX")
export SGXFIVE_KPOKE=$W/kpoke SGXFIVE_DEBUGFS=$W; : > "$W/kpoke"
grep -v '^#' "$KP/tables/st1.txt" | while IFS='|' read -r name set risk knobs tool args; do
	[ -n "$name" ] || continue
	J=$W/rows/$name; mkdir -p "$J"; : > "$W/kpoke"
	(cd "$J" && S=$KP W=$J eval "\"\$T\" --mock $args" > "$J/o" 2>&1); rc=$?
	r=$(grep -m 1 '^job:' "$J/o" || echo 'no job line')
	i=$(grep -m 1 '^tri: isp2' "$J/o" || echo 'no isp2')
	s=$(grep -m 1 '^stencil #1:' "$J/o" | cut -d';' -f1)
	echo "$name: rc $rc, $r; $i; $s; pixel rows $(grep -cE '^row [0-9]+: ' "$J/o"); dumps $(ls "$J" | grep -c '\.1\.bin$')"
done | awk '{ print } / job: ok;/ { ok++ } END { print "rows ending job: ok: " ok }'
echo "## the bytes fill: the first bytes of the stencil buffer (bytes:1, st1-s1b1)"
od -A d -t x1 -N 8 "$W/rows/st1-s1b1/stencil.1.bin"
rm -rf "$W"
