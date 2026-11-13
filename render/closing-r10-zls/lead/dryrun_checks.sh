#!/bin/bash
# SPDX-License-Identifier: MIT
# lead/dryrun_checks.sh: every row of r10-zls's tables on the library mock of its tool's bound
# source (t4: resgx545 4623753, sgxfive-test.c sha256 703cbcea...; t9: 97447b04, 5de42943...;
# each checked first), built for the Mac from `git archive` into debug/libsrc-* (never shipped,
# never staged), WITH the kpoke file the depth rows write (the kit's own libmock replay runs
# without it, so a --depth row ends at `kpoke: No such file`, rc 1, unflagged: r10-x's finding 6).
# Then the flags of st1 that neither bound tool takes (--isp2, --stencil-fill bytes): st1 waits for
# t10. Mac only. Usage: bash lead/dryrun_checks.sh > lead/dryrun_checks.out
set -u
KP=$(cd "$(dirname "$0")/.." && pwd)
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
build() { # NAME COMMIT SHA
	local src=$KP/debug/libsrc-$1
	rm -rf "$src"; mkdir -p "$src"
	git -C "$MAIN" archive "$2" userspace/libsgxfive include/uapi | tar -x -C "$src"
	local got; got=$(shasum -a 256 "$src/userspace/libsgxfive/tools/sgxfive-test.c" | cut -d' ' -f1)
	[ "$got" = "$3" ] || { echo "$1: sgxfive-test.c is not the bound one ($got)"; exit 1; }
	make -s -C "$src/userspace/libsgxfive" build/sgxfive-test > /dev/null 2>&1 || { echo "$1: build failed"; exit 1; }
	echo "$src/userspace/libsgxfive/build/sgxfive-test"
}
T4=$(build t4 4623753f2cc5b9a34b357736801a4c6e66138bf9 703cbceaae8cdff3eda280b7ef89f3c5ef14ba7d378dd269bc66ef714aaead69) || exit 1
T9=$(build t9 97447b04b38cadac7733f0cd12503e2ef207a3bf 5de429431a93ddbdcd9c20141f5c286dcc5cc72265f95d662279e09b655a3f50) || exit 1
W=$(mktemp -d "$KP/debug/dry.XXXXXX")
export SGXFIVE_KPOKE=$W/kpoke SGXFIVE_DEBUGFS=$W; : > "$W/kpoke"
echo "## every row, with the kpoke file (the job line; the kpoke the row wrote)"
for t in "$KP"/tables/*.txt; do
	st=$(basename "$t" .txt)
	grep -v '^#' "$t" | while IFS='|' read -r name set risk knobs tool args; do
		[ -n "$name" ] || continue
		case $tool in t4) T=$T4 ;; t9) T=$T9 ;; *) echo "$st $name: tool $tool"; continue ;; esac
		J=$W/rows/$st-$name; mkdir -p "$J"; : > "$W/kpoke"
		(cd "$J" && S=$KP W=$J eval "\"\$T\" --mock $args" > "$J/o" 2>&1); rc=$?
		r=$(grep -m 1 '^job:' "$J/o" || echo 'no job line')
		d=$(grep -m 1 '^depth #1:' "$J/o" | cut -d';' -f1)
		k=$(tr '\n' ' ' < "$W/kpoke")
		echo "$st $name ($tool): rc $rc, $r; $d; dump $(ls "$J" | grep -c 'depth.1.bin'); kpoke [${k% }]"
	done
done | awk '{ print } / job: ok;/ { ok++ } END { print "rows ending job: ok: " ok }'
run() { echo "### $1"; shift; (cd "$W" && "$@" > "$W/o" 2>&1); rc=$?
	grep -E '^job:|bad option|usage|unknown' "$W/o" | head -2; echo "rc $rc"; }
echo "## the tools the session does not use for st1"
run "t4 --isp2 (st1's flag): refused" "$T4" --mock tri --width 64 --height 32 --depth --stencil --stencil-store --isp2 0x040001ff
run "t9 --isp2 (st1's flag): refused" "$T9" --mock tri --width 64 --height 32 --depth --stencil --stencil-store --isp2 0x040001ff
run "t4 --stencil-fill bytes (st1's fill): refused" "$T4" --mock tri --width 64 --height 32 --depth --stencil --stencil-fill bytes
rm -rf "$W"
