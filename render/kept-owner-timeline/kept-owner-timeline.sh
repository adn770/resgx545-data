# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q106: regtimeline (a line at every change of the registers 0x0600-0x0750, polled every 10 ms for
# 3 s, whole lines kept) around the faulting case of kept-owner-regs.sh: tri -n 1 --ctx2
# --close-first-early with the first context's render flags flipped by 0xc (bit 3 with bit 2), and
# around the exact one with the first context open (--words-between). Three runs of each, the GPU
# reset before each. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1120}
R=$HOME/regtimeline
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.20) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$SRCV_FILE"
echo "## loaded module"; SRCV_LOADED=$(sudo -n cat /sys/module/gma500_gfx/srcversion); echo "$SRCV_LOADED"
[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
echo "## tool"; sha256sum "$T"
echo "## clock"; date
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
W=$(mktemp -d)
KEEP="^(job|diff|tri|tri2|kpoke)|failed|FAILED|cleanup|ta3dctl"
dw() { od -An -tx4 -v -j $((4 * $2)) -N 4 "$1" | tr -d ' '; }
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
trap 'reset_gpu; rm -rf "$W"' EXIT
[ -x "$R" ] || { echo "no $R: build tools/campaign's regtimeline for the laptop first"; exit 1; }
for i in 1 2 3; do
	for between in "--close-first-early" "--words-between --words $W"; do
		echo "== timeline-flip-0xc-${between%% *}-$i: regtimeline 3.0 0.01 0x0600-0x0750 -- tri -n 1 --ctx2 $between"
		reset_gpu
		sudo -n timeout 120 "$R" 3.0 0.01 0x0600-0x0750 -- "$T" tri --wait-ms 5000 -n 1 --ctx2 \
			$between --kpoke-render 1:ta:7^=0xc 2>&1 </dev/null |
			grep -vE "^tri: (render context|words)|^layout:|us$"
	done
done
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
