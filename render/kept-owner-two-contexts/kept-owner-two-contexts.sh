# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q041: what a later job on a context whose RT data is at another address does with the DPM slot
# word a render leaves set (TA3DCtl dword 20, the first slot's RT data, and 25, the TA's, kept by
# render flag bit 2, bit 3 or both, E316). tri --ctx2 renders the first context, then the second
# (other RT data, 0x32423300 against 0x32411300) in the same VM; the render flags (TA command
# dword 7, kernel value 0x400) are flipped through the kernel poke ta:7 in the first context
# (--kpoke-render 1:ta:7^=V), the second (--kpoke-render2) or both, in render 1 only, with n = 2
# renders (first, second, first, second). The control block (debugfs buf09) is saved by --words
# after each pair of renders: dwords 20, 21, 25, 46 and 47 are printed with each render's outcome.
# Cases: no flip; 0x4, 0x8, 0xc in the first; 0xc in the second; 0xc in both; 0x4 in the first and
# 0x4 in the second. Root through sudo -n.
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
W=$(mktemp -d)
trap 'reset_gpu; rm -rf "$W"' EXIT
KEEP="^(job|diff|tri|tri2|kpoke)|failed|FAILED"
dw() { od -An -tx4 -v -j $((4 * $2)) -N 4 "$1" | tr -d ' '; }
case_run() { # NAME ARGS...
	name=$1; shift
	echo "== $name: tri -n 2 --ctx2 $*"
	reset_gpu
	mkdir -p "$W/$name"
	sudo -n "$T" tri --wait-ms 5000 -n 2 --ctx2 --words "$W/$name" "$@" 2>&1 </dev/null |
		grep -E "$KEEP" | grep -v "us$" | cut -c1-170
	for n in 0 1 2; do
		f="$W/$name/ta3d.$n.bin"
		[ -f "$f" ] && echo "ta3d after render pair $n: dword20 0x$(dw $f 20) dword21 0x$(dw $f 21) dword25 0x$(dw $f 25) dword46 0x$(dw $f 46) dword47 0x$(dw $f 47)"
		[ -f "$W/$name/words.$n.txt" ] && echo "second context words $n: $(sed -n 's/^\(ctx:4\|rtds:0\)=/\1=/p' "$W/$name/words.$n.txt" | tr '\n' ' ')"
	done
}
for i in 1 2; do case_run "control-$i"; done
for v in 0x4 0x8 0xc; do
	for i in 1 2; do case_run "first-flip-$v-$i" --kpoke-render "1:ta:7^=$v"; done
done
for i in 1 2; do case_run "second-flip-0xc-$i" --kpoke-render2 "1:ta:7^=0xc"; done
for i in 1 2; do case_run "both-flip-0xc-$i" --kpoke-render "1:ta:7^=0xc" --kpoke-render2 "1:ta:7^=0xc"; done
for i in 1 2; do case_run "both-flip-0x4-$i" --kpoke-render "1:ta:7^=0x4" --kpoke-render2 "1:ta:7^=0x4"; done
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
