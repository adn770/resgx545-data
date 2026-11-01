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

0520_under_4x() (
# 0x0520 (rd:19) against 4x multisampling and against ISP0 bit 28 (blk:1): the 4x setup (the
# sample positions 0xeaa26e26 in cmd:16 and cmd:10, 0x042c = 0x80000002 in cmd:13, the TE
# anti-aliasing bits 0xe0000000 in cmd:1) with 0x0520 at 0, 0x88888888 and 0xffffffff, ISP0
# as 0x01d00200 and with bit 28 set; then the single-sampled triangle with bit 28 and cmd:16
# moved (0x88, 0xffffffff, 0) at 0x0520 = 0x0c0c0c0c; then mode 3 (8x) with 0x0520 holding a
# second rotated grid (0x2e62a6ea) with and without ISP0 bit 28. Each case prints a hash of
# the pixels and the triangle count of its job.
kp() { printf '%s\n' clear "$@" | sudo -n tee "$D/kpoke" >/dev/null; }
run() { name=$1 k=$2; shift 2
	kp "$k"
	r=$(sudo -n "$T" tri --keep-going --pixels "$@" 2>&1)
	echo "$name: $(echo "$r" | grep '^row ' | md5sum | cut -c1-12) $(echo "$r" |
		grep -E '^job|^tri 64x64 #1: [0-9]+ tri' | tr '\n' ' ') left: $(sudo -n cat "$D/kpoke" | tr '\n' ' ')"
	kp
}
X4="--poke cmd:16=0xeaa26e26 --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:1=0xe0000000"
for r in 1 2; do
	for isp0 in 0x01d00200 0x11d00200; do
		for v in 0 0x88888888 0xffffffff; do
			run "4x isp0 $isp0 0520 $v" rd:19=$v $X4 --poke blk:1=$isp0
		done
	done
	for m in 0x88 0xffffffff 0x00000000; do
		run "1x isp0 bit 28, 04c8 $m, 0520 0x0c0c0c0c" rd:19=0x0c0c0c0c --poke cmd:16=$m \
			--poke blk:1=0x11d00200
	done
	run "1x isp0 bit 28, 0520 0" rd:19=0 --poke blk:1=0x11d00200
done
for isp0 in 0x01d00200 0x11d00200; do
	for v in 0 0x2e62a6ea; do
		run "8x isp0 $isp0 0520 $v" rd:19=$v --poke cmd:16=0xeaa26e26 --poke cmd:10=0xeaa26e26 \
			--poke cmd:13=0x80000003 --poke cmd:1=0xe0000000 --poke blk:1=$isp0
	done
done
)
echo "#### 0520-under-4x"
0520_under_4x
echo "## exit $?"
