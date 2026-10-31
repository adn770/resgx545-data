# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Dummy transfers through the phase-4 kernel's debugfs files: xfer_dummy eleven times in a
# row, then xfer_sync three times (a destination sync one write short holds the command
# until PROCESS_QUEUES).
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
for i in $(seq 1 11); do
	echo "#### repeat $i"
	r xfer_dummy
done
regs repeat
for i in 1 2 3; do
	echo "#### sync-one-short $i"
	r xfer_sync
done
regs sync
r status
w stop
klog stop "SGX power-off|SGX stopped"
