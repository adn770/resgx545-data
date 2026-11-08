# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q048: the length at which a loop still finishes. Each of the table's programs (the floating-point
# and the integer loop at 2500000, 5000000, 7500000 and 10000000 iterations, staged as
# $SGXFIVE_PROBE_BINS) is run three times under regtimeline (SGXFIVE_REGTIMELINE, default
# ~/regtimeline) over CR_CLKGATESTATUS (0x0008) and CR_CLKGATECTL2 (0x0004), 50 ms before the
# job, with no write, after a GPU reset; a job that does not finish within 20 s is killed. The
# time the sampled status register reads busy is the loop's. Root through sudo -n.
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
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
[ -x "$RT" ] || { echo "no $RT: build tools/sweep/regtimeline.c on the laptop first"; exit 1; }
KEEP="^(job|diff|tri|probe|fill|copy|timeline|tl )|failed"
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
trap 'reset_gpu' EXIT
for loop in fmad int; do
	for c in 0 1 2 3; do
		for run in 1 2 3; do
			reset_gpu
			echo "== $loop case $c run $run: $B/usse-madd-length-${loop}__$c.bin"
			s=$(date +%s%N)
			sudo -n timeout -s KILL 20 "$RT" 0 0.05 "0x0008,0x0004" -- "$T" probe "$B/usse-madd-length-${loop}__$c.bin" 2>&1 </dev/null |
				grep -E "$KEEP" | grep -v "render context" | cut -c1-160 | head -n 40
			echo "wall: $(( ($(date +%s%N) - s) / 1000000 )) ms"
		done
	done
done
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
