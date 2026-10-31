# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Transfers under a client page directory through the phase-4 kernel's debugfs files:
# xfer_iso with the EDM's buffers aliased read-write, read-only (alias_ro) and not at all
# (no_alias); then xfer_ro (a fill into a read-only alias of a kernel buffer), its fault,
# and recovery by reload and boot.
set -u
D=$(sudo -n sh -c "ls -d /sys/kernel/debug/dri/*/sgx" 2>/dev/null | head -1)
[ -n "$D" ] || { echo "no sgx debugfs directory: is the phase-4 gma500 loaded?"; exit 1; }
w() { echo "${2:-1}" | sudo -n tee "$D/$1" >/dev/null; echo "## write $1 ${2:-1}: exit $?"; }
r() { echo "## $1"; sudo -n cat "$D/$1"; echo "## read $1: exit $?"; }
regs() { echo "## regs $1"; sudo -n cat "$D/regs"; }
klog() { echo "## log $1"; sudo -n dmesg | grep -E "$2" | tail -n "${3:-3}"; }
start() {
	echo "## uname"; uname -r
	echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
	for f in miscinfo idle xfer_dummy xfer_sync xfer_fill xfer_copy xfer_iso xfer_ro regs; do
		sudo -n test -e "$D/$f" && echo "## has $f" || echo "## lacks $f"
	done
	w load
	w boot
	klog boot "SGX firmware|SGX boot"
}
start
regs boot
w alias_ro 0
w no_alias 0
for i in 1 2; do
	echo "#### client-fill $i"
	r xfer_iso
done
w alias_ro 1
echo "#### alias-ro"
r xfer_iso
w alias_ro 0
w no_alias 1
echo "#### no-alias"
r xfer_iso
w no_alias 0
regs iso
echo "#### fill-into-ro-alias"
r xfer_ro
klog fault "SGX BIF fault|SGX .*" 8
r status
regs ro
echo "#### recover"
w stop
klog stop "SGX power-off|SGX stopped|SGX .*clocks|SGX .*EDM did not" 4
w alias_ro 0
w load
w boot
klog boot "SGX boot"
r xfer_dummy
r xfer_fill
r status
w stop
klog stop "SGX power-off|SGX stopped"
