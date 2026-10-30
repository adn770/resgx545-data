# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Register snapshots around one boot (needs the debug option's sgx/regs).
set -u
D=$(sudo -n sh -c "ls -d /sys/kernel/debug/dri/*/sgx" 2>/dev/null | head -1)
[ -n "$D" ] || { echo "no sgx debugfs directory: is the phase-3 gma500 loaded?"; exit 1; }
w() { echo "${2:-1}" | sudo -n tee "$D/$1" >/dev/null; echo "## write $1: exit $?"; }
r() { echo "## $1"; sudo -n cat "$D/$1"; }
irq() { echo "## interrupts"; grep -i gma500 /proc/interrupts; }
klog() { echo "## dmesg"; sudo -n dmesg | tail -n "${1:-20}"; }
sudo -n test -e "$D/regs" || { echo "no $D/regs: build the kernel with DRM_GMA500_SGXFIVE_DEBUG"; exit 1; }
echo "#### before load"; irq; r regs
w load
echo "#### loaded"; r regs
w boot
echo "#### booted"; irq; r regs; r status
w stop
echo "#### stopped"; irq; r regs
w load
w boot
echo "#### booted again"; irq; r regs
w stop
klog 40
