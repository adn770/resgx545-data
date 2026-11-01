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

csc_set0_uyvy_copy() (
# A 64x32 copy over the every-value source, its texture words poked to a UYVY form (tex:1 =
# 0x7d03f01f: TEXTYPE 3, TEXFORMAT 29; tex:0 bits 7 and 4 set), every pixel read back. Three
# runs: the transfer command without the colour-space load (xfer:17 bit 0 clear), with set 0
# loaded as the limited-range BT.601 words (xfer:18-22 = 0x00950095 0x00000095 0x010203ce
# 0x039800cc 0), and with set 0 loaded as zeros.
cp() { echo "#### $1"; shift; sudo -n "$T" copy --every-value --pixels "$@" 2>&1; echo "## exit $?"; }
U="--poke tex:1=0x7d03f01f --poke tex:0^=0x90"
cp "no load" $U
cp "set 0 BT.601" $U --poke xfer:17^=0x1 --poke xfer:18=0x00950095 --poke xfer:19=0x00000095 \
	--poke xfer:20=0x010203ce --poke xfer:21=0x039800cc --poke xfer:22=0
cp "set 0 zeros" $U --poke xfer:17^=0x1 --poke xfer:18=0 --poke xfer:19=0 --poke xfer:20=0 \
	--poke xfer:21=0 --poke xfer:22=0
)

csc_set1_formats() (
# The UYVY copy with set 0 loaded as BT.601 and set 1 as limited-range BT.709 (128ths:
# xfer:23-27 = 0x00950095 0x00000095 0x010e03e5 0x03bc00e6 0), then the texture formats beside
# it: TEXFORMAT 28 (tex:1 = 0x7c03f01f) and TEXFORMAT 26 (tex:1 = 0x7a03f01f) with and without
# tex:0 bit 30. Every pixel read back.
cp() { echo "#### $1"; shift; sudo -n "$T" copy --every-value --pixels "$@" 2>&1; echo "## exit $?"; }
C0="--poke xfer:17^=0x1 --poke xfer:18=0x00950095 --poke xfer:19=0x00000095 --poke xfer:20=0x010203ce --poke xfer:21=0x039800cc --poke xfer:22=0"
C1="--poke xfer:23=0x00950095 --poke xfer:24=0x00000095 --poke xfer:25=0x010e03e5 --poke xfer:26=0x03bc00e6 --poke xfer:27=0"
cp "uyvy, sets 0 and 1 loaded" --poke tex:1=0x7d03f01f --poke tex:0^=0x90 $C0 $C1
cp "texformat 28, sets 0 and 1 loaded" --poke tex:1=0x7c03f01f --poke tex:0^=0x90 $C0 $C1
cp "texformat 26, tex:0 bit 30" --poke tex:1=0x7a03f01f --poke tex:0^=0x40000090 $C0 $C1
cp "texformat 26, no tex:0 bit 30" --poke tex:1=0x7a03f01f --poke tex:0^=0x90 $C0 $C1
)

luma_key_bytes() (
# The luma-key mode (tex:0 bit 31) with the three loaded words at their init values and one
# byte of one word replaced by 0x01, 0x40, 0x80 and 0xff in turn: 12 bytes, 4 values. Every
# pixel read back.
w0=0x02020106; w1=0x00210064; w2=0xff008000
for w in 0 1 2; do
	for b in 0 1 2 3; do
		for v in 1 64 128 255; do
			eval "base=\$w$w"
			val=$(( (base & ~(0xff << (8 * b))) | (v << (8 * b)) ))
			p0=$w0; p1=$w1; p2=$w2
			case $w in 0) p0=$val ;; 1) p1=$val ;; 2) p2=$val ;; esac
			echo "#### word $w byte $b value $v"
			sudo -n "$T" copy --every-value --pixels --poke tex:0^=0x80000000 \
				--poke xfer:17^=0x2 --poke "xfer:29=$p0" --poke "xfer:30=$p1" \
				--poke "xfer:31=$p2" 2>&1
			echo "## exit $?"
		done
	done
done
)

luma_key_fields() (
# The luma-key mode with each field of the loaded words scanned over a few values, the others
# at their init values (0x02020106, 0x00210064, 0xff008000): the weights wR (0x0860 bits 9:0),
# wG (0x0860 bits 25:16) and wB (0x0864 bits 9:0), the offset (0x0864 bits 23:16), the
# threshold (0x0868 bits 15:8) and the two alphas (0x0868 bits 23:16 and 31:24). Every pixel
# read back.
cp() { echo "#### $1"; shift; sudo -n "$T" copy --every-value --pixels --poke tex:0^=0x80000000 \
	--poke xfer:17^=0x2 "$@" 2>&1; echo "## exit $?"; }
W0=0x02020106; W1=0x00210064; W2=0xff008000
for v in 0 256 512 1023; do
	cp "wR $v" --poke "xfer:29=$(( (W0 & ~0x3ff) | v ))" --poke xfer:30=$W1 --poke xfer:31=$W2
	cp "wG $v" --poke "xfer:29=$(( (W0 & ~0x3ff0000) | (v << 16) ))" --poke xfer:30=$W1 --poke xfer:31=$W2
	cp "wB $v" --poke xfer:29=$W0 --poke "xfer:30=$(( (W1 & ~0x3ff) | v ))" --poke xfer:31=$W2
done
for v in 0 32 64 255; do
	cp "offset $v" --poke xfer:29=$W0 --poke "xfer:30=$(( (W1 & ~0xff0000) | (v << 16) ))" --poke xfer:31=$W2
done
for v in 0 64 128 255; do
	cp "threshold $v" --poke xfer:29=$W0 --poke xfer:30=$W1 --poke "xfer:31=$(( (W2 & ~0xff00) | (v << 8) ))"
done
for v in 0 85 255; do
	cp "alpha below $v" --poke xfer:29=$W0 --poke xfer:30=$W1 --poke "xfer:31=$(( (W2 & ~0xff0000) | (v << 16) ))"
	cp "alpha above $v" --poke xfer:29=$W0 --poke xfer:30=$W1 --poke "xfer:31=$(( (W2 & ~0xff000000) | (v << 24) ))"
done
)

luma_key_modes() (
# The copy over the every-value source with the three words that load 0x0860-0x0868 (xfer:29-31,
# loaded by xfer:17 bit 1) and tex:0 bit 31 (the luma-key mode): the plain copy, the mode
# without the load, the mode with the words at their init values (0x02020106, 0x00210064,
# 0xff008000), with zeros and with other values. Every pixel read back.
cp() { echo "#### $1"; shift; sudo -n "$T" copy --every-value --pixels "$@" 2>&1; echo "## exit $?"; }
L="--poke xfer:17^=0x2"
cp "plain"
cp "mode, no load" --poke tex:0^=0x80000000
cp "mode, init values" --poke tex:0^=0x80000000 $L --poke xfer:29=0x02020106 \
	--poke xfer:30=0x00210064 --poke xfer:31=0xff008000
cp "mode, zeros" --poke tex:0^=0x80000000 $L --poke xfer:29=0 --poke xfer:30=0 --poke xfer:31=0
cp "mode, other values" --poke tex:0^=0x80000000 $L --poke xfer:29=0x01020304 \
	--poke xfer:30=0x05060708 --poke xfer:31=0x80402010
)
echo "#### csc-set0-uyvy-copy"
csc_set0_uyvy_copy
echo "## exit $?"
echo "#### csc-set1-formats"
csc_set1_formats
echo "## exit $?"
echo "#### luma-key-bytes"
luma_key_bytes
echo "## exit $?"
echo "#### luma-key-fields"
luma_key_fields
echo "## exit $?"
echo "#### luma-key-modes"
luma_key_modes
echo "## exit $?"
