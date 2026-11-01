# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# For each value of HostCtl dword 6 (400000, 200000, 800000 core clocks): write it to the
# timer_clock file, stop, load and boot the firmware (the file is read at boot), then take 200
# register snapshots over about 40 s, each stamped before and after. The knob is put back to 0
# (the firmware's own value) and the firmware booted again at the end.
set -u
D=$(sudo -n sh -c "ls -d /sys/kernel/debug/dri/*/sgx" 2>/dev/null | head -1)
[ -n "$D" ] || { echo "no sgx debugfs directory: is the gma500 with the debug option loaded?"; exit 1; }
w() { echo "${2:-1}" | sudo -n tee "$D/$1" >/dev/null; echo "## write $1 ${2:-1}: exit $?"; }
r() { echo "## $1"; sudo -n cat "$D/$1"; }
for f in timer_clock regs load boot stop; do
	if sudo -n test -e "$D/$f"; then echo "## has $f"; else echo "## lacks $f"; fi
done
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
run_one() {
	echo "#### dword 6 $1"
	w timer_clock "$2"
	r timer_clock
	w stop
	w load
	w boot
	for i in $(seq 1 200); do
		echo "#### snapshot $i $(date +%s.%N)"
		sudo -n cat "$D/regs"
		echo "#### read $i $(date +%s.%N)"
		sleep 0.05
	done
	r status
}
run_one 400000 0x61a80
run_one 200000 0x30d40
run_one 800000 0xc3500
echo "#### default again"
w timer_clock 0x0
w stop
w load
w boot
r status
