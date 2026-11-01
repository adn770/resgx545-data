# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Readback of 0x0810, 0x0814 and 0x0818 (set by the init script to 0x1, 0xffff and 0x7ff):
# for each, the value it holds, then ~0, then 0 written through kreg and read back, then the
# init value restored. kreg lists the registers it may write, "0xOFFS 0xVALUE" a line.
set -u
D=$(sudo -n sh -c "ls -d /sys/kernel/debug/dri/*/sgx" 2>/dev/null | head -1)
[ -n "$D" ] || { echo "no sgx debugfs directory: is the gma500 with the debug option loaded?"; exit 1; }
w() { echo "${2:-1}" | sudo -n tee "$D/$1" >/dev/null; echo "## write $1 ${2:-1}: exit $?"; }
for f in kreg kpoke regs; do
	if sudo -n test -e "$D/$f"; then echo "## has $f"; else echo "## lacks $f"; fi
done
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
w load
w boot
echo "## kreg at boot"
sudo -n cat "$D/kreg"
rb() { echo "reads $1: $(sudo -n cat "$D/kreg" | grep -i "^$1 ")"; }
for pair in 0x0810:0x1 0x0814:0xffff 0x0818:0x7ff; do
	reg=${pair%%:*}; init=${pair#*:}
	echo "#### $reg (init $init)"
	rb "$reg"
	w kreg "$reg=0xffffffff"
	rb "$reg"
	w kreg "$reg=0x0"
	rb "$reg"
	w kreg "$reg=$init"
	rb "$reg"
done
echo "## dmesg"; sudo -n dmesg | grep -i kreg | tail -n 20
echo "## status"; sudo -n cat "$D/status"
