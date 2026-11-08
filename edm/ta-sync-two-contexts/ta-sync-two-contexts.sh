# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q034: whether the EDM's TA pick holds back a command whose syncs are incomplete when another
# context is queued (3d.md 4.2 steps 3 and 6). tri --ctx2 --overlap submits the second context's
# job before the first's is waited for; the commands are poked through the kernel poke ta:N (the
# first context's before its kick, the second's with --kpoke-render2, 30 ms after the first's job
# is submitted). The TA transfer-queue sync (dwords 25 to 28: write pending, its address, read
# pending, its address) is made incomplete with dword 25 = 0x5a5a5a5a and dwords 26 and 28 naming
# a zero word of the context's page (the context's ctx:4 less 0x100 plus 0x280: complete for
# dword 27 = 0, incomplete for dword 25). The source sync (dword 33 = 1, dwords 34 to 37) the
# same. Cases: no poke; the first's transfer-queue sync; the second's source sync; both; the
# second's transfer-queue sync; the first's source sync; both source syncs. Each job waited for 4
# s; a held command hangs its job and the kernel recovers (the GPU is reset before each case).
# Words by tri --words. Root through sudo -n.
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
trap 'reset_gpu' EXIT
W=$(mktemp -d)
trap 'reset_gpu; rm -rf "$W"' EXIT
KEEP="^(job|diff|tri|tri2|kpoke)|failed|FAILED"
kl() { sudo -n dmesg | tail -n +$(($1 + 1)) | grep -iE 'fault|recover|hung|kpoke|cancel|lost' |
	sed 's/^\[[ 0-9.]*\] //' | cut -c1-150 | head -n 8 | sed 's/^/klog: /'; }
reset_gpu
mkdir -p "$W/w"
sudo -n "$T" tri -n 1 --ctx2 --words "$W/w" >/dev/null 2>&1
XB=$(printf 0x%08x $(( $(sed -n 's/^ctx:4=//p' "$W/w/words.1.txt") - 0x100 + 0x280 )))
mkdir -p "$W/v"
sudo -n "$T" tri -n 1 --words "$W/v" >/dev/null 2>&1
XA=$(printf 0x%08x $(( $(sed -n 's/^ctx:4=//p' "$W/v/words.1.txt") - 0x100 + 0x280 )))
echo "sync words: first context $XA, second context $XB"
TQ1="--kpoke-render 1:ta:25=0x5a5a5a5a --kpoke-render 1:ta:26=$XA --kpoke-render 1:ta:28=$XA"
SS1="--kpoke-render 1:ta:33=1 --kpoke-render 1:ta:34=0x5a5a5a5a --kpoke-render 1:ta:35=$XA --kpoke-render 1:ta:36=0x5a5a5a5a --kpoke-render 1:ta:37=$XA"
TQ2="--kpoke-render2 1:ta:25=0x5a5a5a5a --kpoke-render2 1:ta:26=$XB --kpoke-render2 1:ta:28=$XB"
SS2="--kpoke-render2 1:ta:33=1 --kpoke-render2 1:ta:34=0x5a5a5a5a --kpoke-render2 1:ta:35=$XB --kpoke-render2 1:ta:36=0x5a5a5a5a --kpoke-render2 1:ta:37=$XB"
case_run() { # NAME ARGS...
	name=$1; shift
	echo "== $name: tri $*" | sed 's/--kpoke-render2\? /&/' | cut -c1-200
	reset_gpu
	n=$(sudo -n dmesg | wc -l)
	sudo -n "$T" tri --wait-ms 4000 -n 1 --ctx2 --overlap "$@" 2>&1 </dev/null | grep -E "$KEEP" | grep -v "us$"
	kl "$n"
}
for i in 1 2 3; do case_run "control-$i"; done
for i in 1 2 3; do case_run "first-tq-sync-$i" $TQ1; done
for i in 1 2 3; do case_run "second-src-sync-$i" $SS2; done
for i in 1 2 3; do case_run "first-tq-second-src-$i" $TQ1 $SS2; done
for i in 1 2 3; do case_run "second-tq-sync-$i" $TQ2; done
for i in 1 2 3; do case_run "first-src-sync-$i" $SS1; done
for i in 1 2 3; do case_run "both-src-sync-$i" $SS1 $SS2; done
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
