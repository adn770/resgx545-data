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

fault_addresses() (
# TA command word 167 (register 0x074c) with bit 8 set and different high bits, one render each,
# and the kernel's fault report for each: whether the faulting address follows the high bits.
# The kernel log is read from the line count before the case (never cleared: the runner's mark).
for v in 0x100 0x1100 0x10100 0x100100 0x1000100 0x10000100 0x80000100 0x101; do
	n=$(sudo -n dmesg | wc -l)
	echo "== ta:167=$v: $(sudo -n "$T" tri -n 1 --keep-going --kpoke-render "1:ta:167=$v" 2>&1 |
		grep -E '^job' | tr '\n' ' ')"
	sudo -n dmesg | tail -n +$((n + 1)) | grep -iE "fault|bif|0x0*74c" | head -4
done
)
echo "#### fault-addresses"
fault_addresses
