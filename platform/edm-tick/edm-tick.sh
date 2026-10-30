# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 200 register snapshots of the running firmware (about 40 s), each read stamped before and
# after.
set -u
D=$(sudo -n sh -c "ls -d /sys/kernel/debug/dri/*/sgx" 2>/dev/null | head -1)
[ -n "$D" ] || { echo "no sgx debugfs directory: is the phase-3 gma500 loaded?"; exit 1; }
w() { echo "${2:-1}" | sudo -n tee "$D/$1" >/dev/null; echo "## write $1: exit $?"; }
r() { echo "## $1"; sudo -n cat "$D/$1"; }
irq() { echo "## interrupts"; grep -i gma500 /proc/interrupts; }
klog() { echo "## dmesg"; sudo -n dmesg | tail -n "${1:-20}"; }
sudo -n test -e "$D/regs" || { echo "no $D/regs: build the kernel with DRM_GMA500_SGXFIVE_DEBUG"; exit 1; }
w load
w boot
for i in $(seq 1 200); do
	echo "#### snapshot $i $(date +%s.%N)"
	sudo -n cat "$D/regs"
	echo "#### read $i $(date +%s.%N)"
	sleep 0.05
done
r status
w stop
irq
