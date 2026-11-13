#!/bin/bash
# SPDX-License-Identifier: MIT
# lead/dryrun_checks.sh: the plan's four checks (closing10/rank/rank-round10.md, session r10-x) on the
# library mock of tool t4's source (resgx545 4623753 userspace/libsgxfive/tools/sgxfive-test.c,
# sha256 703cbcea..., checked first), built for the Mac from `git archive` into debug/tool4-src
# (never shipped, never staged), with the published bins the rows use (resgx545-data 1324301be).
# Mac only. Usage: bash lead/dryrun_checks.sh > lead/dryrun_checks.out
set -u
KP=$(cd "$(dirname "$0")/.." && pwd)
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
DATA=${RESGX545_DATA:-/Users/jtorra/src/resgx545-data}
DC=1324301bef136f1ada33dd3450c5665738bde435
SRC=$KP/debug/tool4-src
WANT=703cbceaae8cdff3eda280b7ef89f3c5ef14ba7d378dd269bc66ef714aaead69
rm -rf "$SRC"; mkdir -p "$SRC"
git -C "$MAIN" archive 4623753 userspace/libsgxfive include/uapi | tar -x -C "$SRC"
got=$(shasum -a 256 "$SRC/userspace/libsgxfive/tools/sgxfive-test.c" | cut -d' ' -f1)
[ "$got" = "$WANT" ] || { echo "sgxfive-test.c is not the rgn4 tool's ($got)"; exit 1; }
make -s -C "$SRC/userspace/libsgxfive" build/sgxfive-test > /dev/null 2>&1 || { echo "build failed"; exit 1; }
T=$SRC/userspace/libsgxfive/build/sgxfive-test
W=$(mktemp -d "$KP/debug/dry.XXXXXX")
export SGXFIVE_KPOKE=$W/kpoke SGXFIVE_DEBUGFS=$W; : > "$W/kpoke"   # the depth rows arm the ZLS through kpoke
blob() { git -C "$DATA" show "$DC:$1" > "$W/$2"; }
blob dpm/partial-reload-pos/dpm-partial-reload-pos-pa0/bins/dpm-partial-reload-pos-pa0__0.bin pos.bin
blob dpm/partial-reload-pos/dpm-partial-reload-pos-pa0/bins/pix_pa0.bin pix_pa0.bin
blob pbe/sideband-channels/pbe-sideband-channels-0208/bins/eot_plain.bin eot_plain.bin
blob pbe/sideband-channels/pbe-sideband-channels-0208/bins/pbe-sideband-channels-0208__0.bin c0.bin
run() { echo "### $1"; shift; (cd "$W" && "$T" --mock "$@" > "$W/o" 2>&1); rc=$?
	grep -vE '^row |: row ' "$W/o" | grep -E '^job:|^tri:|^depth|probe .*: (tri|o0|failed)|bad option|usage|need|failed' | head -6
	echo "pixel rows $(grep -cE '(^|: )row [0-9]+: ' "$W/o")"; echo "rc $rc"; }
echo "## check 1 (R10-A dcmp): --tri-z 0,0,0 prints and runs (t = 0x0), a negative fill is taken"
run "z0-neg25-m1" tri --keep-going --wait-ms 20000 --width 64 --height 32 --max-width 64 --max-height 32 --tri-full --tri-z 0,0,0 --depth --depth-ctl 0x0017500e --depth-fill 0xbe800000 --depth-store --depth-dump . --poke blk:1=0x00400200 --pixels
echo "## check 2 (R10-E isp0x): blk:2 is ISP word 1"
grep -n 'isp0\|isp1' "$SRC/userspace/libsgxfive/src/render.c" | head -2
run "z242-c with ISP word 1 bit 23 flipped (two pokes)" tri --keep-going --wait-ms 20000 --width 80 --height 40 --max-width 80 --max-height 40 --tri-v 0,0,40960,0,0,20480 --tri-z 1,0,1 --depth --depth-ctl 0x00171014 --depth-fill 0xdeadbeef --depth-dump . --poke blk:1=0x00400200 --poke 'blk:2^=0x00800000'
echo "## check 3 (R10-B win0): the probe's render and the knob; E502's bins"
run "E502 form, mode 0, TE 0x20000000 (no knob needed)" probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --tri-full --cmd 1=0x20000000 --cmd 10=0xeaa26e26 --cmd 13=0x80000000 --cmd 16=0xeaa26e26 --slot pixel=pix_pa0.bin pos.bin
run "E502 form, mode 0, TE 0x60000000 (needs the knob: the library mock has no counterpart)" probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --tri-full --cmd 1=0x60000000 --cmd 10=0xeaa26e26 --cmd 13=0x80000000 --cmd 16=0xeaa26e26 --slot pixel=pix_pa0.bin pos.bin
echo "mock-knob listed by t4: $("$T" 2>&1 | grep -c -- --mock-knob)"
echo "E502's own bins (p1126-pos-x__0, p1126-pos-y__0) in resgx545-data at $DC: $(git -C "$DATA" ls-tree -r --name-only $DC | grep -c 'p1126-pos')"
echo "## check 4 (R10-F sb): one E383 job (mode 8, bits 8:6 = 0, colour 0xc0804020) as a kit probe row"
run "E383 0208__0" probe --tri pixel --pixels --slot eot=eot_plain.bin --sideband 0x208 c0.bin
run "mode 20, bits 8:6 = 3" probe --tri pixel --pixels --slot eot=eot_plain.bin --sideband 0x2d4 c0.bin
echo "## check 5: every row of the tables on the library mock, with the kpoke file the depth rows write"
echo "## (the kit's own libmock replay runs without it: a --depth row ends at 'kpoke: No such file',"
echo "## rc 1, which it does not flag; and a TE_AA with bit 31 or 30 is refused by the library mock,"
echo "## which has no counterpart of the knob: those rows are listed, not counted as passes)"
for t in "$KP"/tables/*.txt; do
	st=$(basename "$t" .txt)
	grep -v '^#' "$t" | while IFS='|' read -r name set risk knobs tool args; do
		[ -n "$name" ] || continue
		J=$W/rows/$st-$name; mkdir -p "$J"; : > "$W/kpoke"
		(cd "$J" && S=$KP W=$J eval "\"\$T\" --mock $args" > "$J/o" 2>&1); rc=$?
		if [ "${args%% *}" = tri ]; then
			r=$(grep -m 1 '^job:' "$J/o" || echo 'no job line')
		else
			r="$(grep -cE ': row [0-9]+: ' "$J/o") rows$(grep -m 1 -o 'failed: .*' "$J/o" | sed 's/^/, /')"
		fi
		echo "$st $name: rc $rc, $r"
	done
done | awk '{ print } / (job: ok|64 rows|96 rows)$/ { ok++ } END { print "rows ending as the tool takes them: " ok }'
rm -rf "$W"
echo "## check 6 (win0): the same rows on a copy of the library mock whose render check takes the knob"
echo "## as the kernel does (fork 2a650d74 sgxfive_render_check: ms = ctx->aa_ms = aa4 || setting); the"
echo "## copy is debug/tool4-knob (never staged); only the line of check_render below is changed"
K=$KP/debug/tool4-knob
rm -rf "$K"; cp -R "$SRC" "$K"; rm -rf "$K/userspace/libsgxfive/build"
grep -n 'te_aa & 0xc0000000u && !ctx->aa4' "$K/userspace/libsgxfive/src/mock.c"
sed -i.orig 's/if (c->te_aa \& 0xc0000000u \&\& !ctx->aa4)/if (c->te_aa \& 0xc0000000u \&\& !ctx->aa4 \&\& !getenv("R10X_KNOB"))/' "$K/userspace/libsgxfive/src/mock.c"
diff "$K/userspace/libsgxfive/src/mock.c.orig" "$K/userspace/libsgxfive/src/mock.c"
grep -q '#include <stdlib.h>' "$K/userspace/libsgxfive/src/mock.c" || echo "mock.c has no stdlib.h"
make -s -C "$K/userspace/libsgxfive" build/sgxfive-test > /dev/null 2>&1 || { echo "knob build failed"; exit 1; }
TK=$K/userspace/libsgxfive/build/sgxfive-test
W=$(mktemp -d "$KP/debug/dry.XXXXXX")
grep -v '^#' "$KP/tables/win0.txt" | while IFS='|' read -r name set risk knobs tool args; do
	[ -n "$name" ] || continue
	J=$W/$name; mkdir -p "$J"
	(cd "$J" && S=$KP W=$J R10X_KNOB=1 eval "\"\$TK\" --mock $args" > "$J/o" 2>&1); rc=$?
	echo "win0 $name (knob): rc $rc, $(grep -cE ': row [0-9]+: ' "$J/o") rows$(grep -m 1 -o 'failed: .*' "$J/o" | sed 's/^/, /')"
done
rm -rf "$W"
