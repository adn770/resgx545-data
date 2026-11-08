#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.26 msaa-te-dumps (Q030): does CR_TE_AA (cmd:1, bits 31:29) change what the TA writes (the
# parameter buffer and TA data, E281 saw them equal for CR_ISP_MSAA bit 31) or only the 3D pipe's
# stored image? tri --tri-full under CR_ISP_MSAA mode M (cmd:13) and the sample words with each
# value of the TE bits, the render memory dumped (--dump-render: render_param, render_tadata),
# registers 0x0200-0x0218 read back after the job (--regs, read-only), the image's colour counts and
# hash. The reduction compares each dump with the case of the same size and mode at TE 0x20000000
# (dword counts); the raw dumps are kept. Sets: 64x64 fit, 128x128 held out, repeats.
# Raw outputs are KEPT: every tool output, whole, gzip (mtime 0) in $KEEP/NAME.txt.gz, with its raw
# size and sha256 printed ("kept ...") and the case table in $KEEP/cases.tsv, so that the rule can
# be recomputed (recompute/recompute_p1126.py). No clock-gate register is written by this script
# (nothing here writes a register: only the render options, the debugfs kpoke of the render and
# the debugfs GPU reset). Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1124}
S=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
KEEP=${KEEP:-$HOME/p1126-dumps/msaa-te-dumps}
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
import gzip, struct, sys
a, b = sys.argv[1], sys.argv[2]
def words(p):
    d = open(p, "rb").read()
    return struct.unpack("<%dI" % (len(d) // 4), d[:len(d) // 4 * 4])
try:
    x, y = words(a), words(b)
except OSError as e:
    print("  no dump:", e)
    sys.exit(0)
n = min(len(x), len(y))
print("  %s: %d dwords against %d, differing %d%s" % (sys.argv[3], len(x), len(y),
      sum(1 for i in range(n) if x[i] != y[i]), "" if len(x) == len(y) else " (sizes differ)"))
PYEOF
)
POS=0xeaa26e26
printf 'name\tset\tW\tH\tmode\tte\n' > "$KEEP/cases.tsv"
CASES=$(cat <<'TABLE'
te-m0-20-64x64 fit 64 64 0 0x20000000
te-m0-00-64x64 fit 64 64 0 0x00000000
te-m0-40-64x64 fit 64 64 0 0x40000000
te-m0-60-64x64 fit 64 64 0 0x60000000
te-m0-80-64x64 fit 64 64 0 0x80000000
te-m0-a0-64x64 fit 64 64 0 0xa0000000
te-m0-c0-64x64 fit 64 64 0 0xc0000000
te-m0-e0-64x64 fit 64 64 0 0xe0000000
te-m2-20-64x64 fit 64 64 2 0x20000000
te-m2-00-64x64 fit 64 64 2 0x00000000
te-m2-40-64x64 fit 64 64 2 0x40000000
te-m2-60-64x64 fit 64 64 2 0x60000000
te-m2-80-64x64 fit 64 64 2 0x80000000
te-m2-a0-64x64 fit 64 64 2 0xa0000000
te-m2-c0-64x64 fit 64 64 2 0xc0000000
te-m2-e0-64x64 fit 64 64 2 0xe0000000
te-m2-20-128x128 heldout 128 128 2 0x20000000
te-m2-00-128x128 heldout 128 128 2 0x00000000
te-m2-e0-128x128 heldout 128 128 2 0xe0000000
te-m2-20-64x64-r2 repeat 64 64 2 0x20000000
te-m2-e0-64x64-r2 repeat 64 64 2 0xe0000000
TABLE
)
echo "$CASES" | while read -r name set w h mode te; do
	printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$set" "$w" "$h" "$mode" "$te" >> "$KEEP/cases.tsv"
	echo "== $name set=$set ${w}x${h} mode $mode te $te"
	mark "$name"
	mkdir -p "$W/$name"
	sudo -n timeout 120 "$T" tri --tri-full --pixels --width "$w" --height "$h" --max-width "$w" --max-height "$h" \
		--poke "cmd:1=$te" --poke "cmd:10=$POS" --poke "cmd:13=0x8000000$mode" --poke "cmd:16=$POS" \
		--regs 0x0200-0x0218 --dump-render "$W/$name" --wait-ms 20000 > "$W/$name.out" 2>&1 </dev/null
	echo "  rc $?"
	grep -E "^job|^diff|^target|^reg 0x020[4-9a-f]|^reg 0x021" "$W/$name.out" | cut -c1-100
	keep "$name" "$W/$name.out"
	for f in param tadata; do
		[ -f "$W/$name/tri.$f.bin" ] && { cp "$W/$name/tri.$f.bin" "$W/$name.$f.bin"; keep "$name.$f" "$W/$name.$f.bin"; }
	done
	ctl="te-m$mode-20-${w}x${h}"
	if [ "$te" != 0x20000000 ] && [ -f "$W/$ctl.param.bin" ]; then
		python3 -c "$PY" "$W/$name.param.bin" "$W/$ctl.param.bin" "param against te 0x20000000"
		python3 -c "$PY" "$W/$name.tadata.bin" "$W/$ctl.tadata.bin" "tadata against te 0x20000000"
	fi
	if grep -qE "failed|faulted|hung" "$W/$name.out"; then reset_gpu; health </dev/null || true; fi
	rm -rf "$W/$name" "$W/$name.out"
done
echo "## end"
