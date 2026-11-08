# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q076: which page directory the TA and 3D requestors of a render translate through, and whether
# the read-only aliases of the EDM's buffers in the client directory (made when a VM gets its first
# render context) are enough. debugfs alias_skip leaves the buffers whose bits are set out of that
# alias (ids 6 CCB, 7 its control block, 8 kicker, 9 TA3DCtl, 10 HostCtl, 11 misc): the GPU is
# reset, the mask written, and the triangle rendered twice on a new VM (tri -n 2 --keep-going)
# under regtimeline sampling the BIF registers 0x0c00-0x0c8c (CR_BIF_BANK0 is 0x0c78, the
# directory lists 0x0c38-0x0c84), then the mask is put back to 0. Cases: no mask (control), each
# of the ids 6 to 11 alone, all six (0xfc0), every id (0xffff) and, for comparison with E-known
# behaviour, alias_ta3d_ro (TA3DCtl read-only). Two runs of each. A render that does not complete
# or faults is reported by the tool as such; the kernel log lines are printed after each. Root
# through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1119}
R=${REGTIMELINE:-$HOME/regtimeline}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.19) for the laptop first"; exit 1; }
[ -x "$R" ] || { echo "no $R"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$SRCV_FILE"
echo "## loaded module"; SRCV_LOADED=$(sudo -n cat /sys/module/gma500_gfx/srcversion); echo "$SRCV_LOADED"
[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
echo "## tool"; sha256sum "$T"
echo "## clock"; date
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
setf() { sudo -n sh -c "echo $2 > $D/$1"; }
W=$(mktemp -d)
trap 'setf alias_skip 0; setf alias_ta3d_ro N; reset_gpu; rm -rf "$W"' EXIT
KEEP="^(job|diff|tri|tri2)|FAILED|failed|renders ok|^timeline:|^tl "
case_run() { # NAME MASK TA3D_RO
	name=$1 mask=$2 ro=$3
	echo "== $name: alias_skip $mask alias_ta3d_ro $ro; tri -n 2 --keep-going"
	reset_gpu
	setf alias_skip "$mask"
	setf alias_ta3d_ro "$ro"
	echo "alias_skip=$(sudo -n cat "$D/alias_skip") alias_ta3d_ro=$(sudo -n cat "$D/alias_ta3d_ro")"
	n=$(sudo -n dmesg | wc -l)
	sudo -n timeout 120 "$R" 0 0.3 0x0c00-0x0c8c -- "$T" tri -n 2 --keep-going --wait-ms 6000 2>&1 </dev/null |
		grep -E "$KEEP" | grep -v "us$" | cut -c1-400
	setf alias_skip 0
	setf alias_ta3d_ro N
	sudo -n dmesg | tail -n +$((n + 1)) | grep -iE "bif|fault|hang|reset|recover|timed out|lost|cancel" |
		cut -c1-180 | head -8
}
for i in 1 2; do
	case_run "control-$i" 0 N
	for id in 6 7 8 9 10 11; do
		case_run "skip-id$id-$i" $(printf '0x%x' $((1 << id))) N
	done
	case_run "skip-ids-6-11-$i" 0xfc0 N
	case_run "skip-all-$i" 0xffff N
	case_run "ta3d-ro-$i" 0 Y
done
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
