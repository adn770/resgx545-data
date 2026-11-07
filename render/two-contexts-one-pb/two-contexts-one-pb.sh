# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q049, Q067: sgxfive-test tri --ctx2 (a second render context in the VM that renders the same
# scene in other colours, each render checked against its own triangle). A: two contexts, each on a
# PB of its own, sequential then overlapping, 4 renders each, 64x64 and 256x256. B: the second
# context on the first's PB (--share-pb): the same. C: render context dword 7 (--kpoke-render
# 1:ctx:7=V, and --kpoke-render2 for the second context's HW context, so that each kernel word is
# poked once; with overlapping jobs the tool arms the second context's poke 30 ms after the first
# context's job is submitted, so that each lands on its own context's kick) with V = 0xdeadbeef and 0xffffffff, in the first context, the second, both, with the
# PB shared and overlapping jobs; the last context's words (debugfs render_words, --words) show its
# dword 7 after each render. D: the DPM registers (0x0630, 0x0640-0x0660, 0x0700-0x0760) and the
# event registers sampled under regtimeline (SGXFIVE_REGTIMELINE, default ~/regtimeline) from 50 ms
# before the jobs of two contexts on PBs of their own, overlapping, three times, and on a shared PB.
# The kernel's lines about faults and recoveries follow each case. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1117}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.17) for the laptop first"; exit 1; }
[ -x "$RT" ] || { echo "no $RT: build tools/sweep/regtimeline.c on the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
W=$(mktemp -d)
KEEP="^(job|diff|tri|kpoke)|failed|FAILED"
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
trap 'reset_gpu; rm -rf "$W"' EXIT
kl() { sudo -n dmesg | tail -n +$(($1 + 1)) | grep -iE 'fault|recover|hung|shares|share|cleanup|kpoke|cancel' |
	sed 's/^\[[ 0-9.]*\] //' | cut -c1-150 | head -n 8 | sed 's/^/klog: /'; }
case_run() { # NAME ARGS...
	name=$1; shift
	echo "== $name: tri $*"
	reset_gpu
	n=$(sudo -n dmesg | wc -l)
	sudo -n "$T" tri --wait-ms 8000 "$@" 2>&1 </dev/null | grep -E "$KEEP" | grep -v "us$"
	kl "$n"
}
for size in "64 64" "256 256"; do
	set -- $size
	for mode in "" "--overlap"; do
		case_run "own-pb-$1 $mode" -n 4 --width "$1" --height "$2" --ctx2 $mode
		case_run "shared-pb-$1 $mode" -n 4 --width "$1" --height "$2" --ctx2 --share-pb $mode
	done
done
V1=0xdeadbeef
for v in 0xdeadbeef 0xffffffff; do
	case_run "dword7-first-$v" -n 2 --ctx2 --share-pb --overlap --kpoke-render "1:ctx:7=$v"
	case_run "dword7-second-$v" -n 2 --ctx2 --share-pb --overlap --kpoke-render2 "1:ctx:7=$v"
	case_run "dword7-both-$v" -n 2 --ctx2 --share-pb --overlap --kpoke-render "1:ctx:7=$v" --kpoke-render2 "1:ctx:7=$v"
	case_run "dword7-both-sequential-$v" -n 2 --ctx2 --share-pb --kpoke-render "1:ctx:7=$v" --kpoke-render2 "1:ctx:7=$v"
	case_run "dword7-both-own-pb-$v" -n 2 --ctx2 --overlap --kpoke-render "1:ctx:7=$v" --kpoke-render2 "1:ctx:7=$v"
done
mkdir -p "$W/words"
case_run "dword7-words" -n 2 --ctx2 --share-pb --overlap --kpoke-render "1:ctx:7=0xdeadbeef" --kpoke-render2 "1:ctx:7=0xdeadbeef" --words "$W/words"
echo "last context's dword 7 after each render: $(grep -h '^ctx:7=' "$W"/words/words.*.txt 2>/dev/null | tr '\n' ' ')"
R="0x0118,0x012c,0x0630,0x0640-0x0660,0x0700-0x0760"
for run in 1 2 3; do
	echo "== timeline own-pb-$run: regtimeline 0 0.05 -- tri -n 3 --ctx2 --overlap"
	reset_gpu
	sudo -n timeout -s KILL 60 "$RT" 0 0.05 "$R" -- "$T" tri -n 3 --ctx2 --overlap 2>&1 </dev/null |
		grep -E "^(job|diff|tri|timeline|tl )|failed" | grep -v "us$"
done
for run in 1 2; do
	echo "== timeline shared-pb-$run: regtimeline 0 0.05 -- tri -n 3 --ctx2 --share-pb --overlap"
	reset_gpu
	sudo -n timeout -s KILL 60 "$RT" 0 0.05 "$R" -- "$T" tri -n 3 --ctx2 --share-pb --overlap 2>&1 </dev/null |
		grep -E "^(job|diff|tri|timeline|tl )|failed" | grep -v "us$"
done
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
