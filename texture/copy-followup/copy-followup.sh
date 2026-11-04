# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Copy follow-ups of the 11.12 triage (sub-phase 11.14): sgxfive-test (SGXFIVE_TEST, default
# ~/sgxfive-test) runs each case; every output is kept and nothing is judged here. Root through
# sudo -n, for the kernel's debugfs.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T"; exit 1; }
[ -n "$D" ] || { echo "no sgx debugfs directory"; exit 1; }
echo "## uname"; uname -r
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
cp() { echo "#### $1"; shift; sudo -n "$T" copy --pixels "$@" 2>&1; echo "## exit $?"; }

t3_low() (
# T3 bits 7:0 (Q078) at every value in the copy over the every-value source, and twice at
# sixteen of them; every pixel read back.
for v in $(seq 0 255); do
	cp "run 1: tex:3 bits 7:0 = $v" --every-value --poke "tex:3=$(( (0x00800800 & ~0xff) | v ))"
done
for v in 0 1 7 8 9 15 16 17 112 127 128 136 240 247 248 255; do
	cp "run 2: tex:3 bits 7:0 = $v" --every-value --poke "tex:3=$(( (0x00800800 & ~0xff) | v ))"
done
)

tag_layers() (
# The transfer command's word 0 (Q011): bits 30:25 (the background tag's layer count, 1 as the
# library builds a copy) at 0, 1, 2, 3, 31 and 63 with bits 24:0 as built, twice; and CR_ISP_MSAA mode 2 (word 7 bit 1)
# on a 128x64 copy, twice. Every pixel read back.
for run in 1 2; do
	cp "run $run: baseline" --every-value
	for n in 0 1 2 3 31 63; do
		cp "run $run: xfer:0 bits 30:25 = $n" --every-value \
			--poke "xfer:0^=$(( (n ^ 1) << 25 ))"
	done
	cp "run $run: 128x64 baseline" --every-value --width 128 --height 64
	cp "run $run: 128x64 xfer:7 bit 1" --every-value --width 128 --height 64 --poke xfer:7^=0x2
done
)

csc_after_reset() (
# Colour-space set 0 across a GPU reset (Q010): a YUYV copy (T1 bit 28) that loads set 0, one
# that does not, then the driver's reset (debugfs reset), then the copy without the load; and
# the same after the GPU has idled (5 s); twice.
C0="--poke xfer:17^=0x1 --poke xfer:18=0x00950095 --poke xfer:19=0x00000095 --poke xfer:20=0x010203ce --poke xfer:21=0x039800cc --poke xfer:22=0"
for run in 1 2; do
	cp "run $run: YUYV copy loading set 0" --poke tex:1^=0x10000000 $C0
	cp "run $run: YUYV copy without the load" --poke tex:1^=0x10000000
	echo "#### run $run: reset"; echo 1 | sudo -n tee "$D/reset" >/dev/null; echo "## exit $?"
	sleep 1
	cp "run $run: YUYV copy without the load, after the reset" --poke tex:1^=0x10000000
	cp "run $run: YUYV copy loading set 0, again" --poke tex:1^=0x10000000 $C0
	sleep 5
	cp "run $run: YUYV copy without the load, after 5 s idle" --poke tex:1^=0x10000000
done
)
echo "#### t3-low"
t3_low
echo "#### tag-layers"
tag_layers
echo "#### csc-after-reset"
csc_after_reset
