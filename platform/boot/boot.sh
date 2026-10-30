# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Twenty load/boot/stop cycles through the phase-3 kernel's debugfs files.
set -u
D=$(sudo -n sh -c "ls -d /sys/kernel/debug/dri/*/sgx" 2>/dev/null | head -1)
[ -n "$D" ] || { echo "no sgx debugfs directory: is the phase-3 gma500 loaded?"; exit 1; }
w() { echo "${2:-1}" | sudo -n tee "$D/$1" >/dev/null; echo "## write $1: exit $?"; }
r() { echo "## $1"; sudo -n cat "$D/$1"; }
irq() { echo "## interrupts"; grep -i gma500 /proc/interrupts; }
klog() { echo "## dmesg"; sudo -n dmesg | tail -n "${1:-20}"; }
bootlog() { echo "## boot log"; sudo -n dmesg | grep -E 'SGX firmware|SGX boot' | tail -n 3; }
for i in $(seq 1 20); do
	echo "#### cycle $i"
	w load
	r layout
	w boot
	bootlog
	r status
	w stop
	r status
done
irq
