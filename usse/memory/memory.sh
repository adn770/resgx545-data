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

error_state_dumps() (
# The kernel's error state (devcoredump) after forced faults: a TA fault (tri --fault), the
# isolation cases (faults of the transfer path), and a manual reset of the firmware (debugfs
# reset). After each, every devcoredump the kernel holds is printed and then released, with
# the register snapshot (debugfs regs) before and after.
dumps() {
	for f in /sys/class/devcoredump/devcd*/data; do
		[ -e "$f" ] || continue
		echo "## $f"
		sudo -n cat "$f"
		echo 1 | sudo -n tee "$f" >/dev/null
	done
}
case1() { name=$1; shift
	echo "#### $name"
	echo "## regs before"; sudo -n cat "$D/regs"
	"$@"
	echo "## exit $?"
	echo "## regs after"; sudo -n cat "$D/regs"
	dumps
}
fault() { sudo -n "$T" tri --fault 2>&1; }
isolation() { sudo -n "$T" isolation 2>&1; }
reset() { echo 1 | sudo -n tee "$D/reset" >/dev/null; }
dumps >/dev/null
case1 ta-fault fault
case1 xfer-fault isolation
case1 manual-reset reset
)
echo "#### error-state-dumps"
error_state_dumps
echo "## exit $?"
