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

t1_bit28() (
# T1 bit 28 (TEXFORMAT 12 to 28) of the copy: alone, with colour-space set 0 loaded as BT.601,
# with T0 bits 7 and 4 as the UYVY copy has them, after a copy that loads set 0 and the luma
# key, with the luma-key mode (T0 bit 31) and its load, and TEXFORMAT 29 (bits 28 and 24);
# plain and every-value sources, twice. Every pixel read back.
cp() { echo "#### $1"; shift; sudo -n "$T" copy --pixels "$@" 2>&1; echo "## exit $?"; }
C0="--poke xfer:17^=0x1 --poke xfer:18=0x00950095 --poke xfer:19=0x00000095 --poke xfer:20=0x010203ce --poke xfer:21=0x039800cc --poke xfer:22=0"
L="--poke xfer:17^=0x2 --poke xfer:29=0x02020106 --poke xfer:30=0x00210064 --poke xfer:31=0xff008000"
for run in 1 2; do
	for src in plain every; do
		E=""
		[ $src = every ] && E=--every-value
		cp "run $run $src: baseline" $E
		cp "run $run $src: tex:1 bit 28" $E --poke tex:1^=0x10000000
		cp "run $run $src: tex:1 bit 28, set 0" $E --poke tex:1^=0x10000000 $C0
		cp "run $run $src: tex:1 bit 28, set 0, tex:0 bits 7 and 4" $E \
			--poke tex:1^=0x10000000 --poke tex:0^=0x90 $C0
		cp "run $run $src: tex:1 bits 28 and 24, set 0" $E --poke tex:1^=0x11000000 $C0
		cp "run $run $src: set 0 and the luma key loaded" $E $C0 $L
		cp "run $run $src: tex:1 bit 28 after it" $E --poke tex:1^=0x10000000
		cp "run $run $src: tex:1 bit 28, tex:0 bit 31, luma key" $E \
			--poke tex:1^=0x10000000 --poke tex:0^=0x80000000 $L
	done
done
)

t2_bits() (
# T2 (the source address) with bits 11, 12, 13 and 14 flipped, over both sources, with the
# source where the copy puts it and moved 4 rows down (--sy 4) or 16 texels on (--sx 16), with
# the target 32 rows long (the default) and 16 rows long; twice. Every pixel read back.
cp() { echo "#### $1"; shift; sudo -n "$T" copy --pixels "$@" 2>&1; echo "## exit $?"; }
for run in 1 2; do
	for src in plain every; do
		E=""
		[ $src = every ] && E=--every-value
		for at in "" "--sy 4" "--sx 16" "--height 16"; do
			for flip in none 0x800 0x1000 0x2000 0x4000; do
				P=""
				[ $flip = none ] || P="--poke tex:2^=$flip"
				cp "run $run $src ${at:-as built}: tex:2 $flip" $E $at $P
			done
		done
	done
done
)

xfer_0_7() (
# The transfer command's word 0 with bit 24 or bit 30 flipped and at 0, and word 7 with bit 1
# flipped, over the plain and the every-value source, twice. Every pixel read back.
cp() { echo "#### $1"; shift; sudo -n "$T" copy --pixels "$@" 2>&1; echo "## exit $?"; }
for run in 1 2; do
	for src in plain every; do
		E=""
		[ $src = every ] && E=--every-value
		cp "run $run $src: baseline" $E
		cp "run $run $src: xfer:0 bit 24" $E --poke xfer:0^=0x1000000
		cp "run $run $src: xfer:0 bit 30" $E --poke xfer:0^=0x40000000
		cp "run $run $src: xfer:0 = 0" $E --poke xfer:0=0
		cp "run $run $src: xfer:7 bit 1" $E --poke xfer:7^=0x2
	done
done
)
echo "#### t1-bit28"
t1_bit28
echo "#### t2-bits"
t2_bits
echo "#### xfer-0-7"
xfer_0_7
