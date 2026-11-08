# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q029: who sends the cleanups of a parameter buffer two render contexts share. tri --ctx2
# --share-pb --close-trace closes the contexts in both orders (--close-first closes the donor,
# the first context, first) and prints debugfs render_cleanup (the last cleanup: the RT, RC and PB
# steps with the TA and 3D loaded-PB slots before and after each) and TA3DCtl dwords 32, 46, 47
# after each close and 500 ms after both. Each case is preceded by a marker run (own PBs, first
# context closed first: the last cleanup is the second context's, ctx 0x32423000) so that a trace
# seen unchanged is the marker's. Three runs of each order on a shared PB, one each on own PBs as
# the control. The kernel's log follows. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1118}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.18) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## installed module"; INST=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$INST"
echo "## loaded module"; LOAD=$(sudo -n cat /sys/module/gma500_gfx/srcversion); echo "$LOAD"
[ -n "$INST" ] && [ "$INST" = "$LOAD" ] || { echo "the loaded module is not the installed one"; exit 1; }
echo "## tool"; sha256sum "$T"
echo "## clock"; date
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
trap 'echo N | sudo -n tee "$D/render_share_pb" >/dev/null; reset_gpu' EXIT
KEEP="^(job|diff|tri|tri2)|closing|cleanup|ta3dctl|failed|FAILED"
kl() { sudo -n dmesg | tail -n +$(($1 + 1)) | grep -iE 'fault|recover|hung|share|cleanup|cancel' |
	sed 's/^\[[ 0-9.]*\] //' | cut -c1-150 | head -n 8 | sed 's/^/klog: /'; }
case_run() { # NAME ARGS...
	name=$1; shift
	reset_gpu
	echo "== marker for $name"
	sudo -n "$T" tri -n 1 --ctx2 --close-first --close-trace 2>&1 </dev/null |
		grep -E "cleanup 500 ms after both are closed: rtds"
	n=$(sudo -n dmesg | wc -l)
	echo "== $name: tri $*"
	sudo -n "$T" tri --wait-ms 8000 "$@" 2>&1 </dev/null | grep -E "$KEEP" | grep -v "us$"
	kl "$n"
}
for i in 1 2 3; do
	case_run "shared-pb-second-closed-first-$i" -n 1 --ctx2 --share-pb --close-trace
	case_run "shared-pb-donor-closed-first-$i" -n 1 --ctx2 --share-pb --close-first --close-trace
done
case_run "own-pb-second-closed-first" -n 1 --ctx2 --close-trace
case_run "own-pb-donor-closed-first" -n 1 --ctx2 --close-first --close-trace
case_run "shared-pb-two-renders-overlap" -n 2 --ctx2 --share-pb --overlap --close-trace
case_run "shared-pb-donor-closed-first-overlap" -n 2 --ctx2 --share-pb --overlap --close-first --close-trace
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
