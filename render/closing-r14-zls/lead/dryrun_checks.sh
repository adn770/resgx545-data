#!/bin/bash
# SPDX-License-Identifier: MIT
# lead/dryrun_checks.sh: every row of r14-zls's four tables on the library mock of t10's bound
# source (resgx545 a581c06 userspace/libsgxfive/tools/sgxfive-test.c, sha256 23e1fa76..., checked
# first), built for the Mac from `git archive` into debug/libsrc-t10 (never shipped, never staged),
# with the kpoke file the depth rows write (as the kit's replay does). Prints each row's rc, job
# line, buffer addresses, its poke line and the first dump summary, then the kpoke files of
# zg-m8 (rd:12), zo-g3 (rd:13) and zg-s14 (rd:14): depth_arm's pokes first, the row's after them.
# Mac only. Usage: bash lead/dryrun_checks.sh > lead/dryrun_checks.out
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
export SGXFIVE_KPOKE=$W/kpoke SGXFIVE_DEBUGFS=$W
for st in zgran zodd zbits2 zflat; do
	echo "## $st"
	grep -v '^#' "$KP/tables/$st.txt" | while IFS='|' read -r name set risk knobs tool args; do
		[ -n "$name" ] || continue
		J=$W/rows/$name; mkdir -p "$J"; : > "$W/kpoke"
		(cd "$J" && S=$KP W=$J eval "\"\$T\" --mock $args" > "$J/o" 2>&1); rc=$?
		cp "$W/kpoke" "$J/kpoke"
		r=$(grep -m 1 '^job:' "$J/o" || echo 'no job line')
		a=$(grep -E '^(depth|depth store|stencil|stencil store): 0x' "$J/o" | cut -d' ' -f1-4 | tr '\n' ' ')
		k=$(grep -m 1 ' before render 1: rd:1[234]=' "$J/o" | sed 's/^tri: //')
		s=$(grep -m 1 -E '^(depth|depth store|stencil store) #1:' "$J/o" | cut -d';' -f1)
		echo "$name: rc $rc, $r; $a; ${k:-no base poke}; $s; dumps $(ls "$J" | grep -c '\.1\.bin$')"
	done
done | awk '{ print } / job: ok;/ { ok++ } END { print "rows ending job: ok: " ok }'
for n in zg-m8 zo-g3 zg-s14; do
	echo "## the kpoke file the library mock saw for $n (depth_arm's pokes, then the row's)"
	cat "$W/rows/$n/kpoke"
done
rm -rf "$W"
