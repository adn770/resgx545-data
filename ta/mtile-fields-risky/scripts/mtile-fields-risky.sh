#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.26 mtile-fields-risky (Q100): what the fields of CR_TE_MTILE1 and CR_TE_MTILE2 count.
# tri --tri-full (a triangle over the whole target, so every 32x16 tile has pixels) with the TA
# command's te_mtile1 (ta:143), te_mtile2 (ta:144) and macrotile stride (ta:146) poked after the
# kernel's checks (--kpoke-render 1:, as E407), every pixel read; the reduction prints the colour
# counts and, per tile row, one digit a tile (sixteenths of the tile's pixels in the triangle's
# colour, g = all, 0 = none, ? = another colour). Fields (E247 widths): MTILE1 bit 31, 29:22 B1,
# 19:12 B2, 7:0 B3; MTILE2 30:22, 20:12, 8:0. Sets (declared before any run, plan.md): control
# (the rule's words, unpoked), fit (256x256 and 640x480), heldout (512x384, 768x640, 1280x720).
# RISKY, run last: the cases the safe script leaves (non-monotone boundaries, larger ones, other strides, bit 31 toggled). Faults expected; the GPU is reset and a plain triangle checked after each.
# Raw outputs are KEPT: every tool output, whole, gzip (mtime 0) in $KEEP/NAME.txt.gz, with its raw
# size and sha256 printed ("kept ...") and the case table in $KEEP/cases.tsv, so that the rule can
# be recomputed (recompute/recompute_p1126.py). No clock-gate register is written by this script
# (nothing here writes a register: only the render options, the debugfs kpoke of the render and
# the debugfs GPU reset). Root through sudo -n.
set -u
# 11.26 resume change (recovery path only, no case changed): after a failed job the debugfs GPU
# reset is followed by a 3 s wait, then the health triangle, which is retried once after a second
# reset and a 5 s wait before a failed recovery is counted (three stop the script).
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1124}
S=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
KEEP=${KEEP:-$HOME/p1126-dumps/mtile-fields-risky}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build the 11.24 userspace/libsgxfive for the laptop first"; exit 1; }
[ -n "$D" ] || { echo "no sgx debugfs directory (debug option off?)"; exit 1; }
mkdir -p "$KEEP"
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$SRCV_FILE"
echo "## loaded module"; SRCV_LOADED=$(sudo -n cat /sys/module/gma500_gfx/srcversion); echo "$SRCV_LOADED"
[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
echo "## tool"; sha256sum "$T"
echo "## clock"; date
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 3; }
kp_clear() { printf 'clear\n' | sudo -n tee "$D/kpoke" >/dev/null; }
mark() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee /dev/kmsg >/dev/null; }
RUN=$(date +%s)-$$
W=$(mktemp -d)
trap 'kp_clear; reset_gpu; rm -rf "$W"' EXIT
keep() { # NAME FILE: gzip the whole raw output, print its sizes and the raw sha256
	raw=$(wc -c < "$2" | tr -d ' ')
	sha=$(sha256sum "$2" | cut -d' ' -f1)
	gzip -n -6 -c "$2" > "$KEEP/$1.txt.gz"
	echo "  kept $1: $raw bytes raw, $(wc -c < "$KEEP/$1.txt.gz" | tr -d ' ') gz, raw sha256 $sha"
}
BAD=0
health() { # a plain triangle must still draw exactly; three failed recoveries stop the script
	sleep 3
	if sudo -n timeout 60 "$T" tri 2>&1 </dev/null | grep -q "^diff: 0 of 4096"; then BAD=0; return 0; fi
	reset_gpu; sleep 5
	if sudo -n timeout 60 "$T" tri 2>&1 </dev/null | grep -q "^diff: 0 of 4096"; then BAD=0; return 0; fi
	sleep 5
	if sudo -n timeout 60 "$T" tri 2>&1 </dev/null | grep -q "^diff: 0 of 4096"; then BAD=0; echo "  health: recovered on the retry"; return 0; fi
	BAD=$((BAD + 1)); echo "  health: the plain triangle does not draw ($BAD)"
	[ "$BAD" -ge 3 ] && { echo "## abort: the GPU did not recover three times"; exit 1; }
	return 1
}
health

PY=$(cat <<'PYEOF'

import re, sys
G, B, SENT = "ff00ff00", "ff203040", "deadbeef"
w, h = int(sys.argv[1]), int(sys.argv[2])
tx, ty = -(-w // 32), -(-h // 16)
cnt = [[[0, 0, 0, 0] for _ in range(tx)] for _ in range(ty)]
rows = 0
for line in sys.stdin:
    m = re.search(r"row (\d+): (.*)$", line)
    if not m:
        continue
    y = int(m.group(1))
    rows += 1
    for x, v in enumerate(m.group(2).split()):
        v = v[2:] if v.startswith("0x") else v
        k = 0 if v == G else 1 if v == B else 2 if v == SENT else 3
        cnt[y // 16][x // 32][k] += 1
if not rows:
    print("  no pixel rows")
    sys.exit(0)
tot = [sum(cnt[j][i][k] for j in range(ty) for i in range(tx)) for k in range(4)]
print("  pixels: green %d background %d sentinel %d other %d" % tuple(tot))
digs = "0123456789abcdefg"
for j in range(ty):
    s = ""
    for i in range(tx):
        c = cnt[j][i]
        area = sum(c)
        s += digs[round(16 * c[0] / area)] if c[3] == 0 else "?"
    print("  tiles %3d: %s" % (j, s))

PYEOF
)
POS=0xeaa26e26
printf 'name\tset\tW\tH\targs\n' > "$KEEP/cases.tsv"
CASES=$(cat <<'TABLE'
q100-256x256-m1-B1-5|fit|256|256|--kpoke-render 1:ta:143=0x01404004
q100-256x256-m1-B1-6|fit|256|256|--kpoke-render 1:ta:143=0x01804004
q100-256x256-m1-B1-7|fit|256|256|--kpoke-render 1:ta:143=0x01c04004
q100-256x256-m1-B1-8|fit|256|256|--kpoke-render 1:ta:143=0x02004004
q100-256x256-m1-B1-9|fit|256|256|--kpoke-render 1:ta:143=0x02404004
q100-256x256-m1-B1-10|fit|256|256|--kpoke-render 1:ta:143=0x02804004
q100-256x256-m1-B1-11|fit|256|256|--kpoke-render 1:ta:143=0x02c04004
q100-256x256-m1-B1-12|fit|256|256|--kpoke-render 1:ta:143=0x03004004
q100-256x256-m1-B1-16|fit|256|256|--kpoke-render 1:ta:143=0x04004004
q100-256x256-m1-B1-20|fit|256|256|--kpoke-render 1:ta:143=0x05004004
q100-256x256-m1-B2-0|fit|256|256|--kpoke-render 1:ta:143=0x01000004
q100-256x256-m1-B2-1|fit|256|256|--kpoke-render 1:ta:143=0x01001004
q100-256x256-m1-B2-2|fit|256|256|--kpoke-render 1:ta:143=0x01002004
q100-256x256-m1-B2-3|fit|256|256|--kpoke-render 1:ta:143=0x01003004
q100-256x256-m1-B2-5|fit|256|256|--kpoke-render 1:ta:143=0x01005004
q100-256x256-m1-B2-6|fit|256|256|--kpoke-render 1:ta:143=0x01006004
q100-256x256-m1-B2-7|fit|256|256|--kpoke-render 1:ta:143=0x01007004
q100-256x256-m1-B2-8|fit|256|256|--kpoke-render 1:ta:143=0x01008004
q100-256x256-m1-B2-9|fit|256|256|--kpoke-render 1:ta:143=0x01009004
q100-256x256-m1-B2-10|fit|256|256|--kpoke-render 1:ta:143=0x0100a004
q100-256x256-m1-B2-11|fit|256|256|--kpoke-render 1:ta:143=0x0100b004
q100-256x256-m1-B2-12|fit|256|256|--kpoke-render 1:ta:143=0x0100c004
q100-256x256-m1-B2-16|fit|256|256|--kpoke-render 1:ta:143=0x01010004
q100-256x256-m1-B2-20|fit|256|256|--kpoke-render 1:ta:143=0x01014004
q100-256x256-m1-B3-0|fit|256|256|--kpoke-render 1:ta:143=0x01004000
q100-256x256-m1-B3-1|fit|256|256|--kpoke-render 1:ta:143=0x01004001
q100-256x256-m1-B3-2|fit|256|256|--kpoke-render 1:ta:143=0x01004002
q100-256x256-m1-B3-3|fit|256|256|--kpoke-render 1:ta:143=0x01004003
q100-256x256-m1-B3-9|fit|256|256|--kpoke-render 1:ta:143=0x01004009
q100-256x256-m1-B3-10|fit|256|256|--kpoke-render 1:ta:143=0x0100400a
q100-256x256-m1-B3-11|fit|256|256|--kpoke-render 1:ta:143=0x0100400b
q100-256x256-m1-B3-12|fit|256|256|--kpoke-render 1:ta:143=0x0100400c
q100-256x256-m1-B3-16|fit|256|256|--kpoke-render 1:ta:143=0x01004010
q100-256x256-m1-B3-20|fit|256|256|--kpoke-render 1:ta:143=0x01004014
q100-256x256-m2-B1-9|fit|256|256|--kpoke-render 1:ta:144=0x02408008
q100-256x256-m2-B1-10|fit|256|256|--kpoke-render 1:ta:144=0x02808008
q100-256x256-m2-B1-11|fit|256|256|--kpoke-render 1:ta:144=0x02c08008
q100-256x256-m2-B1-12|fit|256|256|--kpoke-render 1:ta:144=0x03008008
q100-256x256-m2-B1-16|fit|256|256|--kpoke-render 1:ta:144=0x04008008
q100-256x256-m2-B1-20|fit|256|256|--kpoke-render 1:ta:144=0x05008008
q100-256x256-m2-B2-0|fit|256|256|--kpoke-render 1:ta:144=0x02000008
q100-256x256-m2-B2-1|fit|256|256|--kpoke-render 1:ta:144=0x02001008
q100-256x256-m2-B2-2|fit|256|256|--kpoke-render 1:ta:144=0x02002008
q100-256x256-m2-B2-3|fit|256|256|--kpoke-render 1:ta:144=0x02003008
q100-256x256-m2-B2-4|fit|256|256|--kpoke-render 1:ta:144=0x02004008
q100-256x256-m2-B2-5|fit|256|256|--kpoke-render 1:ta:144=0x02005008
q100-256x256-m2-B2-6|fit|256|256|--kpoke-render 1:ta:144=0x02006008
q100-256x256-m2-B2-7|fit|256|256|--kpoke-render 1:ta:144=0x02007008
q100-256x256-m2-B2-9|fit|256|256|--kpoke-render 1:ta:144=0x02009008
q100-256x256-m2-B2-10|fit|256|256|--kpoke-render 1:ta:144=0x0200a008
q100-256x256-m2-B2-11|fit|256|256|--kpoke-render 1:ta:144=0x0200b008
q100-256x256-m2-B2-12|fit|256|256|--kpoke-render 1:ta:144=0x0200c008
q100-256x256-m2-B2-16|fit|256|256|--kpoke-render 1:ta:144=0x02010008
q100-256x256-m2-B2-20|fit|256|256|--kpoke-render 1:ta:144=0x02014008
q100-256x256-m2-B3-0|fit|256|256|--kpoke-render 1:ta:144=0x02008000
q100-256x256-m2-B3-1|fit|256|256|--kpoke-render 1:ta:144=0x02008001
q100-256x256-m2-B3-2|fit|256|256|--kpoke-render 1:ta:144=0x02008002
q100-256x256-m2-B3-3|fit|256|256|--kpoke-render 1:ta:144=0x02008003
q100-256x256-m2-B3-4|fit|256|256|--kpoke-render 1:ta:144=0x02008004
q100-256x256-m2-B3-5|fit|256|256|--kpoke-render 1:ta:144=0x02008005
q100-256x256-m2-B3-6|fit|256|256|--kpoke-render 1:ta:144=0x02008006
q100-256x256-m2-B3-7|fit|256|256|--kpoke-render 1:ta:144=0x02008007
q100-256x256-m2-B3-16|fit|256|256|--kpoke-render 1:ta:144=0x02008010
q100-256x256-m2-B3-20|fit|256|256|--kpoke-render 1:ta:144=0x02008014
q100-256x256-stride-0|fit|256|256|--kpoke-render 1:ta:146=0x0
q100-256x256-stride-1|fit|256|256|--kpoke-render 1:ta:146=0x1
q100-256x256-stride-2|fit|256|256|--kpoke-render 1:ta:146=0x2
q100-256x256-stride-4|fit|256|256|--kpoke-render 1:ta:146=0x4
q100-256x256-stride-8|fit|256|256|--kpoke-render 1:ta:146=0x8
q100-256x256-stride-16|fit|256|256|--kpoke-render 1:ta:146=0x10
q100-256x256-stride-24|fit|256|256|--kpoke-render 1:ta:146=0x18
q100-256x256-stride-31|fit|256|256|--kpoke-render 1:ta:146=0x1f
q100-256x256-stride-33|fit|256|256|--kpoke-render 1:ta:146=0x21
q100-256x256-stride-40|fit|256|256|--kpoke-render 1:ta:146=0x28
q100-256x256-stride-64|fit|256|256|--kpoke-render 1:ta:146=0x40
q100-256x256-stride-128|fit|256|256|--kpoke-render 1:ta:146=0x80
q100-256x256-m1-flag1|fit|256|256|--kpoke-render 1:ta:143=0x81004004
q100-256x256-part1-2_2_2|fit|256|256|--kpoke-render 1:ta:143=0x00802002
q100-256x256-part1-3_3_3|fit|256|256|--kpoke-render 1:ta:143=0x00c03003
q100-256x256-part1-5_5_5|fit|256|256|--kpoke-render 1:ta:143=0x01405005
q100-256x256-part1-6_6_6|fit|256|256|--kpoke-render 1:ta:143=0x01806006
q100-256x256-part1-8_8_8|fit|256|256|--kpoke-render 1:ta:143=0x02008008
q100-256x256-part1-4_8_8|fit|256|256|--kpoke-render 1:ta:143=0x01008008
q100-256x256-part1-2_6_8|fit|256|256|--kpoke-render 1:ta:143=0x00806008
q100-256x256-part1-1_2_3|fit|256|256|--kpoke-render 1:ta:143=0x00402003
q100-256x256-part1-0_0_0|fit|256|256|--kpoke-render 1:ta:143=0x00000000
q100-256x256-part1-4_6_8|fit|256|256|--kpoke-render 1:ta:143=0x01006008
q100-256x256-part2-2_2_2|fit|256|256|--kpoke-render 1:ta:144=0x00802002
q100-256x256-part2-4_4_4|fit|256|256|--kpoke-render 1:ta:144=0x01004004
q100-256x256-part2-6_6_6|fit|256|256|--kpoke-render 1:ta:144=0x01806006
q100-256x256-part2-10_10_10|fit|256|256|--kpoke-render 1:ta:144=0x0280a00a
q100-256x256-part2-12_12_12|fit|256|256|--kpoke-render 1:ta:144=0x0300c00c
q100-256x256-part2-2_4_6|fit|256|256|--kpoke-render 1:ta:144=0x00804006
q100-256x256-part2-2_4_8|fit|256|256|--kpoke-render 1:ta:144=0x00804008
q100-256x256-part2-0_0_0|fit|256|256|--kpoke-render 1:ta:144=0x00000000
q100-640x480-m1-B1-17|fit|640|480|--kpoke-render 1:ta:143=0x84410018
q100-640x480-m1-B1-20|fit|640|480|--kpoke-render 1:ta:143=0x85010018
q100-640x480-m1-B1-23|fit|640|480|--kpoke-render 1:ta:143=0x85c10018
q100-640x480-m1-B1-24|fit|640|480|--kpoke-render 1:ta:143=0x86010018
q100-640x480-m1-B1-25|fit|640|480|--kpoke-render 1:ta:143=0x86410018
q100-640x480-m1-B1-28|fit|640|480|--kpoke-render 1:ta:143=0x87010018
q100-640x480-m1-B1-32|fit|640|480|--kpoke-render 1:ta:143=0x88010018
q100-640x480-m1-B1-36|fit|640|480|--kpoke-render 1:ta:143=0x89010018
q100-640x480-m1-B1-40|fit|640|480|--kpoke-render 1:ta:143=0x8a010018
q100-640x480-m1-B2-0|fit|640|480|--kpoke-render 1:ta:143=0x82000018
q100-640x480-m1-B2-1|fit|640|480|--kpoke-render 1:ta:143=0x82001018
q100-640x480-m1-B2-2|fit|640|480|--kpoke-render 1:ta:143=0x82002018
q100-640x480-m1-B2-4|fit|640|480|--kpoke-render 1:ta:143=0x82004018
q100-640x480-m1-B2-5|fit|640|480|--kpoke-render 1:ta:143=0x82005018
q100-640x480-m1-B2-6|fit|640|480|--kpoke-render 1:ta:143=0x82006018
q100-640x480-m1-B2-7|fit|640|480|--kpoke-render 1:ta:143=0x82007018
q100-640x480-m1-B2-8|fit|640|480|--kpoke-render 1:ta:143=0x82008018
q100-640x480-m1-B2-9|fit|640|480|--kpoke-render 1:ta:143=0x82009018
q100-640x480-m1-B2-12|fit|640|480|--kpoke-render 1:ta:143=0x8200c018
q100-640x480-m1-B2-15|fit|640|480|--kpoke-render 1:ta:143=0x8200f018
q100-640x480-m1-B2-17|fit|640|480|--kpoke-render 1:ta:143=0x82011018
q100-640x480-m1-B2-20|fit|640|480|--kpoke-render 1:ta:143=0x82014018
q100-640x480-m1-B2-23|fit|640|480|--kpoke-render 1:ta:143=0x82017018
q100-640x480-m1-B2-24|fit|640|480|--kpoke-render 1:ta:143=0x82018018
q100-640x480-m1-B2-25|fit|640|480|--kpoke-render 1:ta:143=0x82019018
q100-640x480-m1-B2-28|fit|640|480|--kpoke-render 1:ta:143=0x8201c018
q100-640x480-m1-B2-32|fit|640|480|--kpoke-render 1:ta:143=0x82020018
q100-640x480-m1-B2-36|fit|640|480|--kpoke-render 1:ta:143=0x82024018
q100-640x480-m1-B2-40|fit|640|480|--kpoke-render 1:ta:143=0x82028018
q100-640x480-m1-B3-0|fit|640|480|--kpoke-render 1:ta:143=0x82010000
q100-640x480-m1-B3-1|fit|640|480|--kpoke-render 1:ta:143=0x82010001
q100-640x480-m1-B3-2|fit|640|480|--kpoke-render 1:ta:143=0x82010002
q100-640x480-m1-B3-4|fit|640|480|--kpoke-render 1:ta:143=0x82010004
q100-640x480-m1-B3-5|fit|640|480|--kpoke-render 1:ta:143=0x82010005
q100-640x480-m1-B3-6|fit|640|480|--kpoke-render 1:ta:143=0x82010006
q100-640x480-m1-B3-7|fit|640|480|--kpoke-render 1:ta:143=0x82010007
q100-640x480-m1-B3-8|fit|640|480|--kpoke-render 1:ta:143=0x82010008
q100-640x480-m1-B3-9|fit|640|480|--kpoke-render 1:ta:143=0x82010009
q100-640x480-m1-B3-12|fit|640|480|--kpoke-render 1:ta:143=0x8201000c
q100-640x480-m1-B3-15|fit|640|480|--kpoke-render 1:ta:143=0x8201000f
q100-640x480-m1-B3-32|fit|640|480|--kpoke-render 1:ta:143=0x82010020
q100-640x480-m1-B3-36|fit|640|480|--kpoke-render 1:ta:143=0x82010024
q100-640x480-m1-B3-40|fit|640|480|--kpoke-render 1:ta:143=0x82010028
q100-640x480-m2-B1-17|fit|640|480|--kpoke-render 1:ta:144=0x04410018
q100-640x480-m2-B1-20|fit|640|480|--kpoke-render 1:ta:144=0x05010018
q100-640x480-m2-B1-23|fit|640|480|--kpoke-render 1:ta:144=0x05c10018
q100-640x480-m2-B1-24|fit|640|480|--kpoke-render 1:ta:144=0x06010018
q100-640x480-m2-B1-25|fit|640|480|--kpoke-render 1:ta:144=0x06410018
q100-640x480-m2-B1-28|fit|640|480|--kpoke-render 1:ta:144=0x07010018
q100-640x480-m2-B1-32|fit|640|480|--kpoke-render 1:ta:144=0x08010018
q100-640x480-m2-B1-36|fit|640|480|--kpoke-render 1:ta:144=0x09010018
q100-640x480-m2-B1-40|fit|640|480|--kpoke-render 1:ta:144=0x0a010018
q100-640x480-m2-B2-0|fit|640|480|--kpoke-render 1:ta:144=0x02000018
q100-640x480-m2-B2-1|fit|640|480|--kpoke-render 1:ta:144=0x02001018
q100-640x480-m2-B2-2|fit|640|480|--kpoke-render 1:ta:144=0x02002018
q100-640x480-m2-B2-4|fit|640|480|--kpoke-render 1:ta:144=0x02004018
q100-640x480-m2-B2-5|fit|640|480|--kpoke-render 1:ta:144=0x02005018
q100-640x480-m2-B2-6|fit|640|480|--kpoke-render 1:ta:144=0x02006018
q100-640x480-m2-B2-7|fit|640|480|--kpoke-render 1:ta:144=0x02007018
q100-640x480-m2-B2-8|fit|640|480|--kpoke-render 1:ta:144=0x02008018
q100-640x480-m2-B2-9|fit|640|480|--kpoke-render 1:ta:144=0x02009018
q100-640x480-m2-B2-12|fit|640|480|--kpoke-render 1:ta:144=0x0200c018
q100-640x480-m2-B2-15|fit|640|480|--kpoke-render 1:ta:144=0x0200f018
q100-640x480-m2-B2-17|fit|640|480|--kpoke-render 1:ta:144=0x02011018
q100-640x480-m2-B2-20|fit|640|480|--kpoke-render 1:ta:144=0x02014018
q100-640x480-m2-B2-23|fit|640|480|--kpoke-render 1:ta:144=0x02017018
q100-640x480-m2-B2-24|fit|640|480|--kpoke-render 1:ta:144=0x02018018
q100-640x480-m2-B2-25|fit|640|480|--kpoke-render 1:ta:144=0x02019018
q100-640x480-m2-B2-28|fit|640|480|--kpoke-render 1:ta:144=0x0201c018
q100-640x480-m2-B2-32|fit|640|480|--kpoke-render 1:ta:144=0x02020018
q100-640x480-m2-B2-36|fit|640|480|--kpoke-render 1:ta:144=0x02024018
q100-640x480-m2-B2-40|fit|640|480|--kpoke-render 1:ta:144=0x02028018
q100-640x480-m2-B3-0|fit|640|480|--kpoke-render 1:ta:144=0x02010000
q100-640x480-m2-B3-1|fit|640|480|--kpoke-render 1:ta:144=0x02010001
q100-640x480-m2-B3-2|fit|640|480|--kpoke-render 1:ta:144=0x02010002
q100-640x480-m2-B3-4|fit|640|480|--kpoke-render 1:ta:144=0x02010004
q100-640x480-m2-B3-5|fit|640|480|--kpoke-render 1:ta:144=0x02010005
q100-640x480-m2-B3-6|fit|640|480|--kpoke-render 1:ta:144=0x02010006
q100-640x480-m2-B3-7|fit|640|480|--kpoke-render 1:ta:144=0x02010007
q100-640x480-m2-B3-8|fit|640|480|--kpoke-render 1:ta:144=0x02010008
q100-640x480-m2-B3-9|fit|640|480|--kpoke-render 1:ta:144=0x02010009
q100-640x480-m2-B3-12|fit|640|480|--kpoke-render 1:ta:144=0x0201000c
q100-640x480-m2-B3-15|fit|640|480|--kpoke-render 1:ta:144=0x0201000f
q100-640x480-m2-B3-32|fit|640|480|--kpoke-render 1:ta:144=0x02010020
q100-640x480-m2-B3-36|fit|640|480|--kpoke-render 1:ta:144=0x02010024
q100-640x480-m2-B3-40|fit|640|480|--kpoke-render 1:ta:144=0x02010028
q100-640x480-stride-0|fit|640|480|--kpoke-render 1:ta:146=0x0
q100-640x480-stride-1|fit|640|480|--kpoke-render 1:ta:146=0x1
q100-640x480-stride-4|fit|640|480|--kpoke-render 1:ta:146=0x4
q100-640x480-stride-16|fit|640|480|--kpoke-render 1:ta:146=0x10
q100-640x480-stride-36|fit|640|480|--kpoke-render 1:ta:146=0x24
q100-640x480-stride-63|fit|640|480|--kpoke-render 1:ta:146=0x3f
q100-640x480-stride-65|fit|640|480|--kpoke-render 1:ta:146=0x41
q100-640x480-stride-100|fit|640|480|--kpoke-render 1:ta:146=0x64
q100-640x480-stride-128|fit|640|480|--kpoke-render 1:ta:146=0x80
q100-640x480-stride-256|fit|640|480|--kpoke-render 1:ta:146=0x100
q100-640x480-m1-flag0|fit|640|480|--kpoke-render 1:ta:143=0x02010018
q100-640x480-part1-5_10_15|fit|640|480|--kpoke-render 1:ta:143=0x8140a00f
q100-640x480-part1-4_8_12|fit|640|480|--kpoke-render 1:ta:143=0x8100800c
q100-640x480-part1-6_12_18|fit|640|480|--kpoke-render 1:ta:143=0x8180c012
q100-640x480-part1-7_14_21|fit|640|480|--kpoke-render 1:ta:143=0x81c0e015
q100-640x480-part1-10_20_30|fit|640|480|--kpoke-render 1:ta:143=0x8281401e
q100-640x480-part1-8_12_24|fit|640|480|--kpoke-render 1:ta:143=0x8200c018
q100-640x480-part1-8_8_8|fit|640|480|--kpoke-render 1:ta:143=0x82008008
q100-640x480-part1-0_0_0|fit|640|480|--kpoke-render 1:ta:143=0x80000000
q100-640x480-part1-5_5_5|fit|640|480|--kpoke-render 1:ta:143=0x81405005
q100-640x480-part1-20_20_20|fit|640|480|--kpoke-render 1:ta:143=0x85014014
q100-640x480-part1-16_24_32|fit|640|480|--kpoke-render 1:ta:143=0x84018020
q100-640x480-part2-4_8_12|fit|640|480|--kpoke-render 1:ta:144=0x0100800c
q100-640x480-part2-6_12_18|fit|640|480|--kpoke-render 1:ta:144=0x0180c012
q100-640x480-part2-10_20_30|fit|640|480|--kpoke-render 1:ta:144=0x0281401e
q100-640x480-part2-8_8_8|fit|640|480|--kpoke-render 1:ta:144=0x02008008
q100-640x480-part2-0_0_0|fit|640|480|--kpoke-render 1:ta:144=0x00000000
q100-640x480-part2-15_15_15|fit|640|480|--kpoke-render 1:ta:144=0x03c0f00f
q100-640x480-part2-7_14_21|fit|640|480|--kpoke-render 1:ta:144=0x01c0e015
q100-640x480-part2-8_12_24|fit|640|480|--kpoke-render 1:ta:144=0x0200c018
q100-512x384-m1-B2p1|heldout|512|384|--kpoke-render 1:ta:143=0x02009008
q100-512x384-m1-B2p4|heldout|512|384|--kpoke-render 1:ta:143=0x0200c008
q100-512x384-m2-B2p1|heldout|512|384|--kpoke-render 1:ta:144=0x0300d00c
q100-512x384-m2-B2p4|heldout|512|384|--kpoke-render 1:ta:144=0x0301000c
q100-768x640-m1-B2p1|heldout|768|640|--kpoke-render 1:ta:143=0x82011018
q100-768x640-m1-B2p4|heldout|768|640|--kpoke-render 1:ta:143=0x82014018
q100-768x640-m2-B2p1|heldout|768|640|--kpoke-render 1:ta:144=0x03019024
q100-768x640-m2-B2p4|heldout|768|640|--kpoke-render 1:ta:144=0x0301c024
q100-1280x720-m1-B2p1|heldout|1280|720|--kpoke-render 1:ta:143=0x83019024
q100-1280x720-m1-B2p4|heldout|1280|720|--kpoke-render 1:ta:143=0x8301c024
q100-1280x720-m2-B2p1|heldout|1280|720|--kpoke-render 1:ta:144=0x03019024
q100-1280x720-m2-B2p4|heldout|1280|720|--kpoke-render 1:ta:144=0x0301c024
TABLE
)
echo "$CASES" | while IFS='|' read -r name set w h args; do
	printf '%s\t%s\t%s\t%s\t%s\n' "$name" "$set" "$w" "$h" "$args" >> "$KEEP/cases.tsv"
	echo "== $name set=$set ${w}x${h}: $args"
	mark "$name"
	# shellcheck disable=SC2086
	sudo -n timeout 120 "$T" tri --tri-full --pixels --width "$w" --height "$h" --max-width "$w" --max-height "$h" \
		 $args --wait-ms 20000 > "$W/$name.out" 2>&1 </dev/null
	rc=$?
	echo "  rc $rc $(grep -E '^job' "$W/$name.out" | head -1 | cut -c1-100) $(grep -E '^diff' "$W/$name.out" | head -1)"
	python3 -c "$PY" "$w" "$h" < "$W/$name.out"
	keep "$name" "$W/$name.out"
	kp_clear
	if grep -qE "failed|faulted|hung|rejected" "$W/$name.out" || [ "$rc" -ne 0 ]; then reset_gpu; health </dev/null || true; fi
	rm -f "$W/$name.out"
done
echo "## end"
