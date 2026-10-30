# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Run on the laptop by the campaign runner (sh, home directory); prints sections "## ...".
set -u
D=$(sudo -n sh -c "ls -d /sys/kernel/debug/dri/*/sgx" 2>/dev/null | head -1)
[ -n "$D" ] || { echo "no sgx debugfs directory: is the phase-3 gma500 loaded?"; exit 1; }
w() { echo "${2:-1}" | sudo -n tee "$D/$1" >/dev/null; echo "## write $1: exit $?"; }
r() { echo "## $1"; sudo -n cat "$D/$1"; }
irq() { echo "## interrupts"; grep -i gma500 /proc/interrupts; }
klog() { echo "## dmesg"; sudo -n dmesg | tail -n "${1:-20}"; }
echo "## uname"; uname -r
for f in 00:00.0 00:02.0; do echo "## lspci $f"; lspci -nnvvk -s $f; done
for f in 0000:00:00.0 0000:00:02.0; do
	for a in vendor device revision subsystem_vendor subsystem_device irq resource; do
		echo "## sysfs $f $a"; cat /sys/bus/pci/devices/$f/$a
	done
done
echo "## iomem"; sudo -n grep -i -A3 '0000:00:02.0' /proc/iomem
irq
echo "## gma500 log"; sudo -n dmesg | grep -i -E 'gma500|stolen|gtt|gatt'
r status
sudo -n test -e "$D/regs" && r regs
