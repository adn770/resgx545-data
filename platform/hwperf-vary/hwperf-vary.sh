# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q075: the HWPerf counters under each counter group (as hwperf-groups.sh sets them: debugfs hwperf,
# "G 0x11"), read before and after each of nine jobs that differ in one thing: the triangle probe
# with 1, 5, 15 and 42 triangles at 64x64 (the table's probes, staged), fills of 64x64, 128x32 and
# 256x16 (the same 4096 pixels in other shapes), and copies of 64x64 and 128x32 (strides set to the width), three runs. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1116}
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.16) for the laptop first"; exit 1; }
for n in 1 5 15 42; do
	[ -f "$B/platform-hwperf-vary-tris${n}__0.bin" ] || { echo "no staged tris$n: stage the table"; exit 1; }
done
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
regs() { echo "$1 $(sudo -n cat "$D/hwperf" | tr '\n' ' ')"; }
job() {
	name=$1; shift
	regs "before $name:"
	sudo -n timeout 60 "$T" "$@" 2>&1 </dev/null | grep -E '^(job|diff)|o0 |renders ok|failed' | sed 's/^/  /'
	regs "after $name:"
}
for run in 1 2 3; do
for g in $(seq 0 15); do
	echo "== group $g run $run"
	echo "$g 0x11" | sudo -n tee "$D/hwperf" >/dev/null || echo "set failed"
	for n in 1 5 15 42; do
		job tris$n probe --tri pixel --width 64 --height 64 --vertices $((n == 1 ? 3 : 3 * n)) "$B/platform-hwperf-vary-tris${n}__0.bin"
	done
	job fill64x64 fill --width 64 --height 64
	job fill128x32 fill --width 128 --height 32 --stride 512
	job fill256x16 fill --width 256 --height 16 --stride 1024
	job copy64x64 copy --width 64 --height 64
	job copy128x32 copy --width 128 --height 32 --src-stride 512 --dst-stride 512
done
done
echo "0 0x1" | sudo -n tee "$D/hwperf" >/dev/null
regs "end:"
