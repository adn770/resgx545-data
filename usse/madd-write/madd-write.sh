# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q048: the MADD fields of CR_CLKGATECTL2 (MADD0 bits 13:12, MADD1 bits 21:20; the other bits stay
# at the boot's 0x00aaaaaa; nothing is ever written to the fields at bits 11:2, a run over which
# froze the laptop) written through debugfs kregnow (the linux fork's commit 36) while a loop
# that finishes runs. The programs (the floating-point and the integer loop at 2500000 iterations,
# and the floating-point one at 5000000, found to finish in 3 of 3 runs without a write in
# usse/madd-length) are staged as $SGXFIVE_PROBE_BINS. The tool's probe --stamp prints the job's
# window in wall-clock ns and the write is stamped the same way, so that the write's place in
# the job is known: sgxfive-test starts about 70 ms after the shell launches it and the job lasts
# 88 ms (2500000 iterations) or 175 ms (5000000), so the write is issued 90 ms after the launch
# (and, for a second set, 130 ms). Each case after a GPU reset (which puts the register back at
# 0x00aaaaaa), three runs: no write; both fields at 0, 1 and 3; MADD0 alone at 0; MADD1 alone at
# 0. The registers are read after each run. A job that does not finish within 20 s is killed.
# Root through sudo -n.
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
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
for f in usse-madd-write-fmad__0 usse-madd-write-int__0 usse-madd-write-fmad__1; do
	[ -f "$B/$f.bin" ] || { echo "no $B/$f.bin: stage the table"; exit 1; }
done
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
trap 'reset_gpu' EXIT
rdk() { sudo -n cat "$D/kregnow" | awk -v r="$1" '$1 == r { print $2 }'; }
rdreg() { sudo -n cat "$D/regs" | awk -v r="$1" '$1 == "reg" && $2 == r { print $3 }'; }
BASE=0x00aaaaaa
run() { # NAME BIN DELAY VALUE|none
	name=$1 bin=$2 delay=$3 val=$4
	reset_gpu
	echo "== $name: $bin, write $val after $delay s"
	w=$(mktemp)
	l0=$(date +%s%N)
	if [ "$val" != none ]; then
		( sleep "$delay"; a=$(date +%s%N); echo "0x0004=$val" | sudo -n tee "$D/kregnow" >/dev/null; b=$(date +%s%N); echo "$a $b" > "$w" ) &
	fi
	out=$(sudo -n timeout -s KILL 20 "$T" probe --stamp "$B/$bin.bin" 2>&1 </dev/null | grep -E "job (time|window)|failed|o0")
	wait
	echo "$out" | cut -c1-140
	ws=$(awk '{print $1}' "$w"); we=$(awk '{print $2}' "$w")
	js=$(echo "$out" | awk '/job window/ {print $5}'); je=$(echo "$out" | awk '/job window/ {print $6}')
	if [ -n "$ws" ] && [ -n "$js" ]; then
		echo "write at $(( (ws - l0) / 1000000 )) ms after the launch, $(( (ws - js) / 1000000 )) ms after the job's start, done $(( (we - ws) / 1000 )) us later; job lasted $(( (je - js) / 1000000 )) ms"
	elif [ -n "$ws" ]; then
		echo "write at $(( (ws - l0) / 1000000 )) ms after the launch (no job window)"
	fi
	echo "after: ctl2 $(rdk 0x0004) status $(rdreg 0x0008)"
	rm -f "$w"
}
# calibration of the write's place and the control runs with no write
for loop in fmad int; do
	for i in 1 2 3; do run "nowrite-$loop-2500k-$i" "usse-madd-write-${loop}__0" 0 none; done
done
for i in 1 2 3; do run "nowrite-fmad-5000k-$i" "usse-madd-write-fmad__1" 0 none; done
for v in 0 1 3; do
	val=$(printf '0x%08x' $(( (0x00aaaaaa & ~(3 << 12) & ~(3 << 20)) | (v << 12) | (v << 20) )))
	for i in 1 2 3; do
		for loop in fmad int; do
			run "both-$v-$loop-2500k-90ms-$i" "usse-madd-write-${loop}__0" 0.09 "$val"
		done
		run "both-$v-fmad-5000k-130ms-$i" "usse-madd-write-fmad__1" 0.13 "$val"
	done
done
val0=$(printf '0x%08x' $(( 0x00aaaaaa & ~(3 << 12) )))
val1=$(printf '0x%08x' $(( 0x00aaaaaa & ~(3 << 20) )))
for i in 1 2 3; do
	for loop in fmad int; do
		run "madd0-only-0-$loop-2500k-90ms-$i" "usse-madd-write-${loop}__0" 0.09 "$val0"
		run "madd1-only-0-$loop-2500k-90ms-$i" "usse-madd-write-${loop}__0" 0.09 "$val1"
	done
done
echo "#### health"
reset_gpu
echo "ctl2 now: $(rdk 0x0004)"
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
