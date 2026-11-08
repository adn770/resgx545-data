#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.26 mtile-msaa (Q086): which macrotile word sets keep every tile of a 4x multisampled render
# on our stack. tri --tri-full under CR_ISP_MSAA mode 2, the closed driver's TE bits (cmd:1 =
# 0xe0000000) and sample words (cmd:10, cmd:16), the macrotile words (ta:143, ta:144, ta:146) poked
# after the kernel's checks: R the kernel's rule (unpoked), U2 the rule with the macrotile rounded
# to 2 tiles instead of 4, U2Q U2 with the four-macrotile test on four times the area, HS the 1x
# words shifted right by one (stride by two: the closed 64x64 relation), FX the closed driver's
# 64x64 words at every size. Families equal to an earlier family at a size are listed but not run.
# Every pixel is read; per tile row one digit a tile (sixteenths of the tile in the triangle's
# colour). Sets: fit (64x64, 128x64, 128x128, 256x128, 96x48, 192x96), heldout (320x160 .. 1024x768).
# SAFE: R at every size and the closed words at 64x64.
# Raw outputs are KEPT: every tool output, whole, gzip (mtime 0) in $KEEP/NAME.txt.gz, with its raw
# size and sha256 printed ("kept ...") and the case table in $KEEP/cases.tsv, so that the rule can
# be recomputed (recompute/recompute_p1126.py). No clock-gate register is written by this script
# (nothing here writes a register: only the render options, the debugfs kpoke of the render and
# the debugfs GPU reset). Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1124}
S=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
KEEP=${KEEP:-$HOME/p1126-dumps/mtile-msaa}
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
q086-64x64-R|fit|64|64|
q086-64x64-U2|fit|64|64|--kpoke-render 1:ta:143=0x00802002 --kpoke-render 1:ta:144=0x00802002 --kpoke-render 1:ta:146=0x4
q086-128x64-R|fit|128|64|
q086-128x128-R|fit|128|128|
q086-256x128-R|fit|256|128|
q086-96x48-R|fit|96|48|
q086-192x96-R|fit|192|96|
q086-320x160-R|heldout|320|160|
q086-384x192-R|heldout|384|192|
q086-448x224-R|heldout|448|224|
q086-512x256-R|heldout|512|256|
q086-512x384-R|heldout|512|384|
q086-640x480-R|heldout|640|480|
q086-1024x768-R|heldout|1024|768|
TABLE
)
echo "$CASES" | while IFS='|' read -r name set w h args; do
	printf '%s\t%s\t%s\t%s\t%s\n' "$name" "$set" "$w" "$h" "$args" >> "$KEEP/cases.tsv"
	echo "== $name set=$set ${w}x${h}: $args"
	mark "$name"
	# shellcheck disable=SC2086
	sudo -n timeout 120 "$T" tri --tri-full --pixels --width "$w" --height "$h" --max-width "$w" --max-height "$h" \
		--poke "cmd:1=0xe0000000" --poke "cmd:10=$POS" --poke "cmd:13=0x80000002" --poke "cmd:16=$POS" $args --wait-ms 20000 > "$W/$name.out" 2>&1 </dev/null
	rc=$?
	echo "  rc $rc $(grep -E '^job' "$W/$name.out" | head -1 | cut -c1-100) $(grep -E '^diff' "$W/$name.out" | head -1)"
	python3 -c "$PY" "$w" "$h" < "$W/$name.out"
	keep "$name" "$W/$name.out"
	kp_clear
	if grep -qE "failed|faulted|hung|rejected" "$W/$name.out" || [ "$rc" -ne 0 ]; then reset_gpu; health </dev/null || true; fi
	rm -f "$W/$name.out"
done
echo "## end"
