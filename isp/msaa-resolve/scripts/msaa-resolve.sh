#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.26 msaa-resolve (Q089), RISKY, run last: does any bit of the end-of-tile emit's sideband make
# the stored image of the 4x render (CR_ISP_MSAA mode 2, the closed driver's TE words and sample
# words, as E439) hold blended colours? E439 ran the sidebands 0x200 and 0x2200 only. Each of the
# 32 bits is flipped in turn from 0x200 and 0x2200 (64 jobs) on the plain green pixel shader at
# 64x64; the reduction counts the colours that are neither the triangle's nor the background's
# (a blend of samples would be one). Faults and hangs are expected for some bits (E074: pack modes
# 9 and 10 leave pixels unwritten); the GPU is reset and a plain triangle checked after each.
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
KEEP=${KEEP:-$HOME/p1126-dumps/msaa-resolve}
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
import collections, re, sys
c = collections.Counter()
rows = 0
for line in sys.stdin:
    m = re.search(r"row (\d+): (.*)$", line)
    if not m:
        continue
    rows += 1
    for v in m.group(2).split():
        c[v[2:] if v.startswith("0x") else v] += 1
tot = sum(c.values())
other = tot - c["ff00ff00"] - c["ff203040"]
print("  pixels %d: green %d background %d other %d (%d colours); commonest %s" % (
    tot, c["ff00ff00"], c["ff203040"], other, len(c), " ".join("%s x%d" % kv for kv in c.most_common(4))))
PYEOF
)
for f in eot_plain p1126-green__0; do
	[ -f "$S/$f.bin" ] || { echo "no $S/$f.bin: run stage-p1126.sh and copy"; exit 1; }
done
POS=0xeaa26e26
printf 'name\tset\tW\tH\tsideband\n' > "$KEEP/cases.tsv"
CASES=$(cat <<'TABLE'
sb200-ctl 0x200
sb200-b0 0x201
sb200-b1 0x202
sb200-b2 0x204
sb200-b3 0x208
sb200-b4 0x210
sb200-b5 0x220
sb200-b6 0x240
sb200-b7 0x280
sb200-b8 0x300
sb200-b9 0x0
sb200-b10 0x600
sb200-b11 0xa00
sb200-b12 0x1200
sb200-b13 0x2200
sb200-b14 0x4200
sb200-b15 0x8200
sb200-b16 0x10200
sb200-b17 0x20200
sb200-b18 0x40200
sb200-b19 0x80200
sb200-b20 0x100200
sb200-b21 0x200200
sb200-b22 0x400200
sb200-b23 0x800200
sb200-b24 0x1000200
sb200-b25 0x2000200
sb200-b26 0x4000200
sb200-b27 0x8000200
sb200-b28 0x10000200
sb200-b29 0x20000200
sb200-b30 0x40000200
sb200-b31 0x80000200
sb2200-ctl 0x2200
sb2200-b0 0x2201
sb2200-b1 0x2202
sb2200-b2 0x2204
sb2200-b3 0x2208
sb2200-b4 0x2210
sb2200-b5 0x2220
sb2200-b6 0x2240
sb2200-b7 0x2280
sb2200-b8 0x2300
sb2200-b9 0x2000
sb2200-b10 0x2600
sb2200-b11 0x2a00
sb2200-b12 0x3200
sb2200-b13 0x200
sb2200-b14 0x6200
sb2200-b15 0xa200
sb2200-b16 0x12200
sb2200-b17 0x22200
sb2200-b18 0x42200
sb2200-b19 0x82200
sb2200-b20 0x102200
sb2200-b21 0x202200
sb2200-b22 0x402200
sb2200-b23 0x802200
sb2200-b24 0x1002200
sb2200-b25 0x2002200
sb2200-b26 0x4002200
sb2200-b27 0x8002200
sb2200-b28 0x10002200
sb2200-b29 0x20002200
sb2200-b30 0x40002200
sb2200-b31 0x80002200
TABLE
)
echo "$CASES" | while read -r name sb; do
	printf '%s\theldout\t64\t64\t%s\n' "$name" "$sb" >> "$KEEP/cases.tsv"
	echo "== $name sideband $sb"
	mark "$name"
	sudo -n timeout 120 "$T" probe --tri pixel --temps 32 --pixels --width 64 --height 64 \
		--cmd "1=0xe0000000" --cmd "10=$POS" --cmd "13=0x80000002" --cmd "16=$POS" \
		--kpoke ta:143=0x802002 --kpoke ta:144=0x802002 --kpoke ta:146=0x4 \
		--slot "eot=$S/eot_plain.bin" --sideband "$sb" "$S/p1126-green__0.bin" > "$W/$name.out" 2>&1 </dev/null
	rc=$?
	echo "  rc $rc $(grep -E 'failed|FAILED|faulted|hung' "$W/$name.out" | head -1 | cut -c1-100)"
	python3 -c "$PY" < "$W/$name.out"
	keep "$name" "$W/$name.out"
	kp_clear
	if grep -qE "failed|faulted|hung" "$W/$name.out" || [ "$rc" -ne 0 ]; then reset_gpu; health </dev/null || true; fi
	rm -f "$W/$name.out"
done
echo "## end"
