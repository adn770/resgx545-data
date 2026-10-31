# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Jobs from userspace through the render node: sgxfive-test (SGXFIVE_TEST, default
# ~/sgxfive-test) runs each case; every exit status and output is kept, nothing is judged
# here. The kernel log after each group shows faults, recoveries and timeouts; only lines
# after this run's marker count. Run it on a fresh boot, so the first job boots the firmware.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
ls /dev/dri/renderD* >/dev/null 2>&1 || { echo "no render node: is a gma500 with the render node loaded?"; exit 1; }
run() { echo "#### $*"; "$T" "$@"; echo "## exit $?"; }
M="client-jobs run $(date +%s)"
echo "$M" | sudo -n tee /dev/kmsg >/dev/null
klog() {
	echo "## log $1"
	sudo -n dmesg | awk -v m="$M" 'f; index($0, m) { f = 1 }' |
		grep -E "\[drm\].*(SGX|sgxfive)" | tail -n "${2:-5}"
}
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
run query
run dummy -n 8
klog dummy
for i in 1 2 3; do
	run fill
	run fill --width 64 --height 32 --x 3 --y 2 --stride 512 --colour 0xff00ff00
	run fill --width 300 --height 70 --stride 1280 --colour 0x80402010
	run fill --width 1 --height 1 --colour 0xffffffff
done
klog fill
for i in 1 2 3; do
	run copy
	run copy --width 64 --height 32 --sx 5 --sy 1 --src-stride 512 --dx 2 --dy 3 --dst-stride 512
	run copy --width 300 --height 70 --src-stride 1280 --dst-stride 1280
done
klog copy
run tri -n 4
run tri --width 128 --height 96 -n 2
run tri --width 64 --height 64 --max-width 256 --max-height 256 -n 2
klog tri
run contexts -n 32
klog contexts
run isolation
klog isolation 20
run tri --fault
klog fault 10
run tri -n 2
run fill
klog after 5
