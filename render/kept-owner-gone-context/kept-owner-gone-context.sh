# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q041: a kept DPM owner through a context that is gone. tri -n 1 --ctx2 --close-first-early
# renders the first context with its render flags (TA command dword 7, kernel value 0x400)
# flipped through the kernel poke ta:7^=V (--kpoke-render 1:ta:7^=V), closes it, and renders the
# second context (other RT data, 0x32423300 against 0x32411300) in the same VM. The control
# block (debugfs buf09) is saved by --words before the first render (0), after the first render
# and before the close (101), after the close (201) and after the second's render (1): dwords 20,
# 21, 25, 46 and 47 are printed for each, and the DPM registers 0x0600-0x0750 (the tool's --regs,
# after the second render only). Cases: no flip; 0x4, 0x8, 0xc in the first; 0xc in both
# (--kpoke-render2); 0x4 in both. Then the same flips of the first with the first context kept
# open (--words-between instead of --close-first-early: a snapshot, 101, between the renders).
# Two runs of each, the GPU reset before each. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1119}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.19) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$SRCV_FILE"
echo "## loaded module"; SRCV_LOADED=$(sudo -n cat /sys/module/gma500_gfx/srcversion); echo "$SRCV_LOADED"
[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
echo "## tool"; sha256sum "$T"
echo "## clock"; date
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
W=$(mktemp -d)
trap 'reset_gpu; rm -rf "$W"' EXIT
KEEP="^(job|diff|tri|tri2|kpoke|reg 0x0[67])|failed|FAILED|cleanup|ta3dctl"
dw() { od -An -tx4 -v -j $((4 * $2)) -N 4 "$1" | tr -d ' '; }
case_run() { # NAME ARGS...
	name=$1; shift
	between=--close-first-early
	[ "${name#open-}" != "$name" ] && between="--words-between"
	echo "== $name: tri -n 1 --ctx2 $between $*"
	reset_gpu
	n=$(sudo -n dmesg | wc -l)
	mkdir -p "$W/$name"
	sudo -n timeout 120 "$T" tri --wait-ms 5000 -n 1 --ctx2 $between --close-trace \
		--words "$W/$name" --regs 0x0600-0x0750 "$@" 2>&1 </dev/null | grep -E "$KEEP" | grep -v "us$" |
		cut -c1-170
	for k in 0 101 201 1; do
		f="$W/$name/ta3d.$k.bin"
		[ -f "$f" ] && echo "ta3d snapshot $k: dword20 0x$(dw $f 20) dword21 0x$(dw $f 21) dword25 0x$(dw $f 25) dword46 0x$(dw $f 46) dword47 0x$(dw $f 47)"
	done
	sudo -n dmesg | tail -n +$((n + 1)) | grep -iE "hang|reset|recover|timed out|fault|lost|cancel" |
		cut -c1-180 | head -6
}
for i in 1 2; do
	case_run "control-$i"
	for v in 0x4 0x8 0xc; do
		case_run "first-flip-$v-$i" --kpoke-render "1:ta:7^=$v"
	done
	case_run "both-flip-0xc-$i" --kpoke-render "1:ta:7^=0xc" --kpoke-render2 "1:ta:7^=0xc"
	case_run "both-flip-0x4-$i" --kpoke-render "1:ta:7^=0x4" --kpoke-render2 "1:ta:7^=0x4"
	for v in 0x4 0x8 0xc; do
		case_run "open-first-flip-$v-$i" --kpoke-render "1:ta:7^=$v"
	done
done
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
