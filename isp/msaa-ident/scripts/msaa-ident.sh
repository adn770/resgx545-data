#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.26 msaa-ident (Q030, Q089): where each stored pixel of a multisampled render comes from.
# probe --tri pixpds:12 runs the triangle's primary PDS program of E437 (source 0, two components:
# the pixel's x + 0.5 in pa0, y + 0.5 in pa1) and a pixel shader that writes pa0 (x job) or pa1
# (y job) as the colour, so every stored pixel of the target says which pixel it holds. Per case two
# jobs (x, y) under CR_ISP_MSAA mode M (cmd:13 = 0x8000000M), the sample words in cmd:10 and cmd:16,
# CR_TE_AA (cmd:1) TE, on a target W x H. With the option --tri-full (11.26 tool change; the
# script tests for it with the mock and falls back to the default triangle) the triangle covers
# the whole target, so every tile has pixels. Sets (declared before any run, plan.md section 2):
# A 64x64 fit (E415's size), B and C held out, D repeats. The tables below are the cases; the
# lines printed after each case are the run script's reduction (per stored 32x16 tile: how many
# pixels decode to a pixel centre and the source bounding box); the fit is in the recompute script.
# Order: A, B, C, D. The case with the most unusual state (new combination of the position
# iteration with multisampling) is the first, 64x64 mode 0.
# Raw outputs are KEPT: every tool output, whole, gzip (mtime 0) in $KEEP/NAME.txt.gz, with its raw
# size and sha256 printed ("kept ...") and the case table in $KEEP/cases.tsv, so that the rule can
# be recomputed (recompute/recompute_p1126.py). No clock-gate register is written by this script
# (nothing here writes a register: only the render options, the debugfs kpoke of the render and
# the debugfs GPU reset). Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1124}
S=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
KEEP=${KEEP:-$HOME/p1126-dumps/msaa-ident}
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

import re, struct, sys
fx, fy, w, h = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
def img(path):
    d = {}
    for line in open(path, errors="replace"):
        m = re.search(r"row (\d+): (.*)$", line)
        if not m:
            continue
        for x, v in enumerate(m.group(2).split()):
            d[(x, int(m.group(1)))] = int(v, 16)
    return d
def dec(v):
    f = struct.unpack("<f", struct.pack("<I", v))[0]
    q = round(f - 0.5)
    return q if 0 <= q < 8192 and abs(f - 0.5 - q) <= 0.05 else None
X, Y = img(fx), img(fy)
if not X or not Y:
    print("  missing rows (x %d, y %d)" % (len(X), len(Y)))
    sys.exit(0)
n = ok = 0
tiles = {}
for (x, y), vx in X.items():
    vy = Y.get((x, y))
    px, py = dec(vx), dec(vy) if vy is not None else None
    n += 1
    if px is None or py is None:
        continue
    ok += 1
    t = tiles.setdefault((x // 32, y // 16), [0, 99999, -1, 99999, -1])
    t[0] += 1
    t[1] = min(t[1], px); t[2] = max(t[2], px); t[3] = min(t[3], py); t[4] = max(t[4], py)
print("  stored %d, decodable (x and y a pixel centre) %d, background or other %d" % (n, ok, n - ok))
for (tx, ty) in sorted(tiles, key=lambda k: (k[1], k[0])):
    c, x0, x1, y0, y1 = tiles[(tx, ty)]
    print("  tile (%d,%d): %4d decodable, source x %d-%d y %d-%d" % (tx, ty, c, x0, x1, y0, y1))

PYEOF
)
for f in pix_pa0 pix_pa1 p1126-pos-x__0 p1126-pos-y__0 p1126-green__0; do
	[ -f "$S/$f.bin" ] || { echo "no $S/$f.bin: run stage-p1126.sh and copy"; exit 1; }
done
FULL=
if "$T" --mock probe --tri pixel --tri-full --width 64 --height 64 "$S/p1126-green__0.bin" >/dev/null 2>&1; then
	FULL=--tri-full
fi
echo "## tri-full: ${FULL:-unsupported by this tool (the default triangle)}"
POS=0xeaa26e26
printf 'name\tset\tW\tH\tmode\tte\n' > "$KEEP/cases.tsv"
CASES=$(cat <<'TABLE'
A-m0-te20-64x64 fit 64 64 0 0x20000000
A-m1-te00-64x64 fit 64 64 1 0x00000000
A-m1-te20-64x64 fit 64 64 1 0x20000000
A-m1-te60-64x64 fit 64 64 1 0x60000000
A-m1-tea0-64x64 fit 64 64 1 0xa0000000
A-m1-tee0-64x64 fit 64 64 1 0xe0000000
A-m2-te00-64x64 fit 64 64 2 0x00000000
A-m2-te20-64x64 fit 64 64 2 0x20000000
A-m2-te60-64x64 fit 64 64 2 0x60000000
A-m2-tea0-64x64 fit 64 64 2 0xa0000000
A-m2-tee0-64x64 fit 64 64 2 0xe0000000
B-m0-te20-128x128 heldout 128 128 0 0x20000000
B-m1-te00-128x128 heldout 128 128 1 0x00000000
B-m1-te20-128x128 heldout 128 128 1 0x20000000
B-m1-te60-128x128 heldout 128 128 1 0x60000000
B-m1-tea0-128x128 heldout 128 128 1 0xa0000000
B-m1-tee0-128x128 heldout 128 128 1 0xe0000000
B-m2-te00-128x128 heldout 128 128 2 0x00000000
B-m2-te20-128x128 heldout 128 128 2 0x20000000
B-m2-te60-128x128 heldout 128 128 2 0x60000000
B-m2-tea0-128x128 heldout 128 128 2 0xa0000000
B-m2-tee0-128x128 heldout 128 128 2 0xe0000000
C-m1-te00-128x64 heldout 128 64 1 0x00000000
C-m1-te20-128x64 heldout 128 64 1 0x20000000
C-m1-tee0-128x64 heldout 128 64 1 0xe0000000
C-m2-te00-128x64 heldout 128 64 2 0x00000000
C-m2-te20-128x64 heldout 128 64 2 0x20000000
C-m2-tee0-128x64 heldout 128 64 2 0xe0000000
C-m1-te00-64x128 heldout 64 128 1 0x00000000
C-m1-te20-64x128 heldout 64 128 1 0x20000000
C-m1-tee0-64x128 heldout 64 128 1 0xe0000000
C-m2-te00-64x128 heldout 64 128 2 0x00000000
C-m2-te20-64x128 heldout 64 128 2 0x20000000
C-m2-tee0-64x128 heldout 64 128 2 0xe0000000
C-m1-te00-96x80 heldout 96 80 1 0x00000000
C-m1-te20-96x80 heldout 96 80 1 0x20000000
C-m1-tee0-96x80 heldout 96 80 1 0xe0000000
C-m2-te00-96x80 heldout 96 80 2 0x00000000
C-m2-te20-96x80 heldout 96 80 2 0x20000000
C-m2-tee0-96x80 heldout 96 80 2 0xe0000000
D-m2-tee0-64x64-r2 repeat 64 64 2 0xe0000000
D-m1-te00-64x64-r2 repeat 64 64 1 0x00000000
D-m2-te00-64x64-r2 repeat 64 64 2 0x00000000
D-m1-tee0-64x64-r2 repeat 64 64 1 0xe0000000
D-m2-tee0-64x64-r3 repeat 64 64 2 0xe0000000
D-m1-te00-64x64-r3 repeat 64 64 1 0x00000000
D-m2-te00-64x64-r3 repeat 64 64 2 0x00000000
D-m1-tee0-64x64-r3 repeat 64 64 1 0xe0000000
TABLE
)
echo "$CASES" | while read -r name set w h mode te; do
	printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$set" "$w" "$h" "$mode" "$te" >> "$KEEP/cases.tsv"
	echo "== $name set=$set ${w}x${h} mode $mode te $te"
	mark "$name"
	for ax in x y; do
		sudo -n timeout 120 "$T" probe --tri pixpds:12 --temps 32 --pixels --width "$w" --height "$h" $FULL \
			--cmd "1=$te" --cmd "10=$POS" --cmd "13=0x8000000$mode" --cmd "16=$POS" \
			--slot "pixel=$S/pix_pa$([ $ax = x ] && echo 0 || echo 1).bin" "$S/p1126-pos-$ax""__0.bin" \
			> "$W/$name-$ax.out" 2>&1 </dev/null
		echo "  $ax: rc $? $(grep -E "failed|FAILED|faulted|hung" "$W/$name-$ax.out" | head -1 | cut -c1-120)"
		keep "$name-$ax" "$W/$name-$ax.out"
	done
	python3 -c "$PY" "$W/$name-x.out" "$W/$name-y.out" "$w" "$h"
	if grep -qE "failed|faulted|hung" "$W/$name-x.out" "$W/$name-y.out"; then reset_gpu; health </dev/null || true; fi
	rm -f "$W/$name-x.out" "$W/$name-y.out"
done
echo "## end"
