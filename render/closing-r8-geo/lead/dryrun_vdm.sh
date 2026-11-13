#!/bin/bash
# SPDX-License-Identifier: MIT
# lead/dryrun_vdm.sh: the dry run behind gen/vdm.py's NATURAL7 (the plan's [check] "the tool prints
# the VDM words": it does not; --emit-scene writes them). Builds the laptop tool's source (resgx545
# 4623753, the rgn4 tool's: sgxfive-test.c sha256 703cbcea..., checked first) for the Mac from
# `git archive` into debug/tool4-src (never shipped, never staged), runs E703's natural capacity
# form at N = 8 and N = 2 against the library's mock with --emit-scene, and prints VDM words 0 to 11
# of the gen page (word 7 is the natural rows word). Mac only; no laptop, no build host.
set -eu
KP=$(cd "$(dirname "$0")/.." && pwd)
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
DATA=${RESGX545_DATA:-/Users/jtorra/src/resgx545-data}
SRC=$KP/debug/tool4-src
WANT=703cbceaae8cdff3eda280b7ef89f3c5ef14ba7d378dd269bc66ef714aaead69
rm -rf "$SRC"; mkdir -p "$SRC"
git -C "$MAIN" archive 4623753 userspace/libsgxfive include/uapi | tar -x -C "$SRC"
got=$(shasum -a 256 "$SRC/userspace/libsgxfive/tools/sgxfive-test.c" | cut -d' ' -f1)
[ "$got" = "$WANT" ] || { echo "sgxfive-test.c is not the rgn4 tool's ($got)"; exit 1; }
make -s -C "$SRC/userspace/libsgxfive" build/sgxfive-test
T=$SRC/userspace/libsgxfive/build/sgxfive-test
B=$DATA/render/closing-s1/bins
for n in 8 2; do
	"$T" --mock probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 \
		--vtx-coords $n --emit-scene "$SRC/n$n.json" --slot "pixel=$B/pix_pa0.bin" \
		--slot "vtxuse=$B/vtx_c$n.bin" "$B/p1131-fmt-${n}__0.bin" > /dev/null
	python3 -c 'import json, sys
d = json.load(open(sys.argv[1]))
g = [m for m in d["memory"] if m["role"] == "gen"][0]["dwords"]
print("N=%s VDM words 0-11:" % sys.argv[2], " ".join(g[:12]), "word 7", g[7])' "$SRC/n$n.json" $n
done
