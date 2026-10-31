# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Solid fills through the phase-4 kernel's debugfs files: xfer_fill (four rectangles, each
# destination dword and a guard page checked) three times, then interleaved with dummies.
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
for i in 1 2 3; do
	echo "#### fill $i"
	r xfer_fill
done
regs fill
for i in 1 2; do
	echo "#### interleaved-dummy $i"
	r xfer_dummy
	r xfer_fill
done
r xfer_dummy
regs interleaved
r status
w stop
klog stop "SGX power-off|SGX stopped"
