# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Hand-run experiments: sgxfive-test (SGXFIVE_TEST, default ~/sgxfive-test) and regtimeline
# (SGXFIVE_REGTIMELINE, default ~/regtimeline) run each case; every output is kept and nothing
# is judged here. Root through sudo -n, for the kernel's debugfs.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null

mte_floats_under_clipping() (
# The MTE's two 1e-6 floats (ta:152 -> 0x0240, ta:153 -> 0x0244) under the clipping scenes of
# the probe mte-clipping-wclip (programs built into $SGXFIVE_PROBE_BINS, default
# $HOME/sgxprobes): each case's image hashed, per value of each float.
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes}
one() { f=$1; poke=$2
	printf '%s\n' clear $poke | sudo -n tee "$D/kpoke" >/dev/null
	r=$(sudo -n "$T" probe --temps 32 --pixels --tri vtxuse --width 64 --height 64 "$f" 2>&1)
	h=$(echo "$r" | grep " row " | md5sum | cut -c1-8)
	s=$(echo "$r" | grep -E "o0 mixed|o0 0x|failed" | sed 's/^probe [^:]*: //' | cut -c1-60)
	echo "$(basename "$f" .bin) ${poke:-base} $h $s | left: $(sudo -n cat "$D/kpoke" | tr '\n' ' ')"
	printf 'clear\n' | sudo -n tee "$D/kpoke" >/dev/null
}
for f in "$B"/mte-clipping-wclip__*.bin; do
	one "$f" ""
	for v in 0 0x3c23d70a 0x3dcccccd 0x3f000000 0x3f800000 0xbf800000 0x447a0000 0x7f7fffff; do
		one "$f" ta:152=$v
		one "$f" ta:153=$v
	done
done
)

wclamp_scan() (
# The triangle w-scan cases 3 to 7 (w 1e-3, 1e-5, 2e-6, 1e-6, 5e-7; programs built into
# $SGXFIVE_PROBE_BINS, default $HOME/sgxprobes) with the state block's WCLAMP word (--blk 14)
# at the default, 1e-7, 1e-3 and 0, and with the TA command's two floats (ta:152, ta:153:
# MTE 0x0240, 0x0244) at 1e-8, 1e-4 and 0. Each case prints the number of triangle pixels of
# its image.
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes}
one() { label=$1 blk=$2 pokes=$3
	for n in 3 4 5 6 7; do
		printf '%s\n' clear $pokes | sudo -n tee "$D/kpoke" >/dev/null
		r=$(sudo -n "$T" probe --temps 32 --pixels --tri vtxuse --width 64 --height 64 \
			$blk "$B/mte-clipping-w-scan__$n.bin" 2>&1)
		echo "$label case $n: $(echo "$r" | grep -E "o0 mixed|o0 0x|failed" |
			sed 's/^probe [^:]*: //' | cut -c1-70) | image $(echo "$r" | grep " row " | md5sum | cut -c1-8)"
	done
	printf 'clear\n' | sudo -n tee "$D/kpoke" >/dev/null
}
one "default" "" ""
one "WCLAMP 1e-7" "--blk 14=0x33D6BF95" ""
one "WCLAMP 1e-3" "--blk 14=0x3A83126F" ""
one "WCLAMP 0" "--blk 14=0" ""
one "ta:152 1e-8" "" "ta:152=0x322BCC77"
one "ta:152 1e-4" "" "ta:152=0x38D1B717"
one "ta:153 1e-8" "" "ta:153=0x322BCC77"
one "ta:153 1e-4" "" "ta:153=0x38D1B717"
one "ta:152,153 0" "" "ta:152=0 ta:153=0"
)
echo "#### mte-floats-under-clipping"
mte_floats_under_clipping
echo "## exit $?"
echo "#### wclamp-scan"
wclamp_scan
echo "## exit $?"
