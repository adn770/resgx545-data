#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.26 mtile-fields (Q100): what the fields of CR_TE_MTILE1 and CR_TE_MTILE2 count.
# tri --tri-full (a triangle over the whole target, so every 32x16 tile has pixels) with the TA
# command's te_mtile1 (ta:143), te_mtile2 (ta:144) and macrotile stride (ta:146) poked after the
# kernel's checks (--kpoke-render 1:, as E407), every pixel read; the reduction prints the colour
# counts and, per tile row, one digit a tile (sixteenths of the tile's pixels in the triangle's
# colour, g = all, 0 = none, ? = another colour). Fields (E247 widths): MTILE1 bit 31, 29:22 B1,
# 19:12 B2, 7:0 B3; MTILE2 30:22, 20:12, 8:0. Sets (declared before any run, plan.md): control
# (the rule's words, unpoked), fit (256x256 and 640x480), heldout (512x384, 768x640, 1280x720).
# SAFE cases: monotone boundaries, none beyond the rule's, stride and bit 31 the rule's.
# Raw outputs are KEPT: every tool output, whole, gzip (mtime 0) in $KEEP/NAME.txt.gz, with its raw
# size and sha256 printed ("kept ...") and the case table in $KEEP/cases.tsv, so that the rule can
# be recomputed (recompute/recompute_p1126.py). No clock-gate register is written by this script
# (nothing here writes a register: only the render options, the debugfs kpoke of the render and
# the debugfs GPU reset). Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1124}
S=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
KEEP=${KEEP:-$HOME/p1126-dumps/mtile-fields}
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
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
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
	if sudo -n timeout 60 "$T" tri 2>&1 </dev/null | grep -q "^diff: 0 of 4096"; then BAD=0; return 0; fi
	reset_gpu; sleep 2
	if sudo -n timeout 60 "$T" tri 2>&1 </dev/null | grep -q "^diff: 0 of 4096"; then BAD=0; return 0; fi
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
q100-256x256-ctl-r1|control|256|256|
q100-256x256-ctl-r2|control|256|256|
q100-256x256-ctl-r3|control|256|256|
q100-256x256-m1-B1-0|fit|256|256|--kpoke-render 1:ta:143=0x00004004
q100-256x256-m1-B1-1|fit|256|256|--kpoke-render 1:ta:143=0x00404004
q100-256x256-m1-B1-2|fit|256|256|--kpoke-render 1:ta:143=0x00804004
q100-256x256-m1-B1-3|fit|256|256|--kpoke-render 1:ta:143=0x00c04004
q100-256x256-m1-B3-5|fit|256|256|--kpoke-render 1:ta:143=0x01004005
q100-256x256-m1-B3-6|fit|256|256|--kpoke-render 1:ta:143=0x01004006
q100-256x256-m1-B3-7|fit|256|256|--kpoke-render 1:ta:143=0x01004007
q100-256x256-m1-B3-8|fit|256|256|--kpoke-render 1:ta:143=0x01004008
q100-256x256-m2-B1-0|fit|256|256|--kpoke-render 1:ta:144=0x00008008
q100-256x256-m2-B1-1|fit|256|256|--kpoke-render 1:ta:144=0x00408008
q100-256x256-m2-B1-2|fit|256|256|--kpoke-render 1:ta:144=0x00808008
q100-256x256-m2-B1-3|fit|256|256|--kpoke-render 1:ta:144=0x00c08008
q100-256x256-m2-B1-4|fit|256|256|--kpoke-render 1:ta:144=0x01008008
q100-256x256-m2-B1-5|fit|256|256|--kpoke-render 1:ta:144=0x01408008
q100-256x256-m2-B1-6|fit|256|256|--kpoke-render 1:ta:144=0x01808008
q100-256x256-m2-B1-7|fit|256|256|--kpoke-render 1:ta:144=0x01c08008
q100-256x256-m2-B3-9|fit|256|256|--kpoke-render 1:ta:144=0x02008009
q100-256x256-m2-B3-10|fit|256|256|--kpoke-render 1:ta:144=0x0200800a
q100-256x256-m2-B3-11|fit|256|256|--kpoke-render 1:ta:144=0x0200800b
q100-256x256-m2-B3-12|fit|256|256|--kpoke-render 1:ta:144=0x0200800c
q100-256x256-part1-2_4_6|fit|256|256|--kpoke-render 1:ta:143=0x00804006
q100-256x256-part1-2_4_8|fit|256|256|--kpoke-render 1:ta:143=0x00804008
q100-256x256-part1-4_4_8|fit|256|256|--kpoke-render 1:ta:143=0x01004008
q100-256x256-part1-0_4_8|fit|256|256|--kpoke-render 1:ta:143=0x00004008
q100-256x256-part2-4_8_12|fit|256|256|--kpoke-render 1:ta:144=0x0100800c
q100-256x256-part2-4_8_8|fit|256|256|--kpoke-render 1:ta:144=0x01008008
q100-256x256-part2-8_8_12|fit|256|256|--kpoke-render 1:ta:144=0x0200800c
q100-256x256-part2-0_8_8|fit|256|256|--kpoke-render 1:ta:144=0x00008008
q100-640x480-ctl-r1|control|640|480|
q100-640x480-ctl-r2|control|640|480|
q100-640x480-ctl-r3|control|640|480|
q100-640x480-m1-B1-0|fit|640|480|--kpoke-render 1:ta:143=0x80010018
q100-640x480-m1-B1-1|fit|640|480|--kpoke-render 1:ta:143=0x80410018
q100-640x480-m1-B1-2|fit|640|480|--kpoke-render 1:ta:143=0x80810018
q100-640x480-m1-B1-4|fit|640|480|--kpoke-render 1:ta:143=0x81010018
q100-640x480-m1-B1-5|fit|640|480|--kpoke-render 1:ta:143=0x81410018
q100-640x480-m1-B1-6|fit|640|480|--kpoke-render 1:ta:143=0x81810018
q100-640x480-m1-B1-7|fit|640|480|--kpoke-render 1:ta:143=0x81c10018
q100-640x480-m1-B1-9|fit|640|480|--kpoke-render 1:ta:143=0x82410018
q100-640x480-m1-B1-12|fit|640|480|--kpoke-render 1:ta:143=0x83010018
q100-640x480-m1-B1-15|fit|640|480|--kpoke-render 1:ta:143=0x83c10018
q100-640x480-m1-B1-16|fit|640|480|--kpoke-render 1:ta:143=0x84010018
q100-640x480-m1-B3-16|fit|640|480|--kpoke-render 1:ta:143=0x82010010
q100-640x480-m1-B3-17|fit|640|480|--kpoke-render 1:ta:143=0x82010011
q100-640x480-m1-B3-20|fit|640|480|--kpoke-render 1:ta:143=0x82010014
q100-640x480-m1-B3-23|fit|640|480|--kpoke-render 1:ta:143=0x82010017
q100-640x480-m1-B3-25|fit|640|480|--kpoke-render 1:ta:143=0x82010019
q100-640x480-m1-B3-28|fit|640|480|--kpoke-render 1:ta:143=0x8201001c
q100-640x480-m2-B1-0|fit|640|480|--kpoke-render 1:ta:144=0x00010018
q100-640x480-m2-B1-1|fit|640|480|--kpoke-render 1:ta:144=0x00410018
q100-640x480-m2-B1-2|fit|640|480|--kpoke-render 1:ta:144=0x00810018
q100-640x480-m2-B1-4|fit|640|480|--kpoke-render 1:ta:144=0x01010018
q100-640x480-m2-B1-5|fit|640|480|--kpoke-render 1:ta:144=0x01410018
q100-640x480-m2-B1-6|fit|640|480|--kpoke-render 1:ta:144=0x01810018
q100-640x480-m2-B1-7|fit|640|480|--kpoke-render 1:ta:144=0x01c10018
q100-640x480-m2-B1-9|fit|640|480|--kpoke-render 1:ta:144=0x02410018
q100-640x480-m2-B1-12|fit|640|480|--kpoke-render 1:ta:144=0x03010018
q100-640x480-m2-B1-15|fit|640|480|--kpoke-render 1:ta:144=0x03c10018
q100-640x480-m2-B1-16|fit|640|480|--kpoke-render 1:ta:144=0x04010018
q100-640x480-m2-B3-16|fit|640|480|--kpoke-render 1:ta:144=0x02010010
q100-640x480-m2-B3-17|fit|640|480|--kpoke-render 1:ta:144=0x02010011
q100-640x480-m2-B3-20|fit|640|480|--kpoke-render 1:ta:144=0x02010014
q100-640x480-m2-B3-23|fit|640|480|--kpoke-render 1:ta:144=0x02010017
q100-640x480-m2-B3-25|fit|640|480|--kpoke-render 1:ta:144=0x02010019
q100-640x480-m2-B3-28|fit|640|480|--kpoke-render 1:ta:144=0x0201001c
q100-640x480-part1-8_16_20|fit|640|480|--kpoke-render 1:ta:143=0x82010014
q100-640x480-part1-4_16_24|fit|640|480|--kpoke-render 1:ta:143=0x81010018
q100-640x480-part1-8_16_16|fit|640|480|--kpoke-render 1:ta:143=0x82010010
q100-640x480-part2-8_16_16|fit|640|480|--kpoke-render 1:ta:144=0x02010010
q100-640x480-part2-4_16_24|fit|640|480|--kpoke-render 1:ta:144=0x01010018
q100-512x384-ctl-r1|control|512|384|
q100-512x384-ctl-r2|control|512|384|
q100-512x384-ctl-r3|control|512|384|
q100-512x384-m1-B1zero|heldout|512|384|--kpoke-render 1:ta:143=0x00008008
q100-512x384-m1-B1m1|heldout|512|384|--kpoke-render 1:ta:143=0x01c08008
q100-512x384-m1-B3p1|heldout|512|384|--kpoke-render 1:ta:143=0x02008009
q100-512x384-m1-B3p4|heldout|512|384|--kpoke-render 1:ta:143=0x0200800c
q100-512x384-m2-B1zero|heldout|512|384|--kpoke-render 1:ta:144=0x0000c00c
q100-512x384-m2-B1m1|heldout|512|384|--kpoke-render 1:ta:144=0x02c0c00c
q100-512x384-m2-B3p1|heldout|512|384|--kpoke-render 1:ta:144=0x0300c00d
q100-512x384-m2-B3p4|heldout|512|384|--kpoke-render 1:ta:144=0x0300c010
q100-768x640-ctl-r1|control|768|640|
q100-768x640-ctl-r2|control|768|640|
q100-768x640-ctl-r3|control|768|640|
q100-768x640-m1-B1zero|heldout|768|640|--kpoke-render 1:ta:143=0x80010018
q100-768x640-m1-B1m1|heldout|768|640|--kpoke-render 1:ta:143=0x81c10018
q100-768x640-m1-B3p1|heldout|768|640|--kpoke-render 1:ta:143=0x82010019
q100-768x640-m1-B3p4|heldout|768|640|--kpoke-render 1:ta:143=0x8201001c
q100-768x640-m2-B1zero|heldout|768|640|--kpoke-render 1:ta:144=0x00018024
q100-768x640-m2-B1m1|heldout|768|640|--kpoke-render 1:ta:144=0x02c18024
q100-768x640-m2-B3p1|heldout|768|640|--kpoke-render 1:ta:144=0x03018025
q100-768x640-m2-B3p4|heldout|768|640|--kpoke-render 1:ta:144=0x03018028
q100-1280x720-ctl-r1|control|1280|720|
q100-1280x720-ctl-r2|control|1280|720|
q100-1280x720-ctl-r3|control|1280|720|
q100-1280x720-m1-B1zero|heldout|1280|720|--kpoke-render 1:ta:143=0x80018024
q100-1280x720-m1-B1m1|heldout|1280|720|--kpoke-render 1:ta:143=0x82c18024
q100-1280x720-m1-B3p1|heldout|1280|720|--kpoke-render 1:ta:143=0x83018025
q100-1280x720-m1-B3p4|heldout|1280|720|--kpoke-render 1:ta:143=0x83018028
q100-1280x720-m2-B1zero|heldout|1280|720|--kpoke-render 1:ta:144=0x00018024
q100-1280x720-m2-B1m1|heldout|1280|720|--kpoke-render 1:ta:144=0x02c18024
q100-1280x720-m2-B3p1|heldout|1280|720|--kpoke-render 1:ta:144=0x03018025
q100-1280x720-m2-B3p4|heldout|1280|720|--kpoke-render 1:ta:144=0x03018028
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
