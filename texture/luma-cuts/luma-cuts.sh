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

low_byte() (
# The luma-key mode (T0 bit 31, the three words loaded with xfer:17 bit 1) over the every-value
# source with bits 7:0 of the third word (xfer:31, 0xff0080VV) at each of the 256 values; then
# with the threshold byte (bits 15:8) at 0 and at 255 for nine of those values. Every pixel
# read back.
for v in $(seq 0 255); do
	w2=$(printf 0x%08x $(( 0xff008000 | v )))
	echo "#### low $v threshold 128"
	sudo -n "$T" copy --every-value --pixels --poke tex:0^=0x80000000 --poke xfer:17^=0x2 \
		--poke xfer:29=0x02020106 --poke xfer:30=0x00210064 --poke "xfer:31=$w2" 2>&1
	echo "## exit $?"
done
for t in 0 255; do
	for v in 0 1 16 32 64 96 128 192 255; do
		w2=$(printf 0x%08x $(( 0xff000000 | t << 8 | v )))
		echo "#### low $v threshold $t"
		sudo -n "$T" copy --every-value --pixels --poke tex:0^=0x80000000 \
			--poke xfer:17^=0x2 --poke xfer:29=0x02020106 --poke xfer:30=0x00210064 \
			--poke "xfer:31=$w2" 2>&1
		echo "## exit $?"
	done
done
)
echo "#### low-byte"
low_byte
