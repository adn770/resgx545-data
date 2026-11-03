# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q075: the HWPerf counters under each counter group. For each group 0 to 15, debugfs hwperf
# sets HostCtl's group and sends SETHWPERFSTATUS with status word 0x11 (bit 0: the counters
# reset, CR_HWPERF_CTRL 0x1ff and a pulse; status 0x10, non-zero, so the group goes into
# CR_HWPERF_CTRL bits 12:9); then the counter registers (debugfs hwperf: 0x0044-0x0064,
# 0x0e84-0x0e90, 0x0eb4-0x0ec0) are read before and after each of seven jobs that differ in one
# thing: the triangle at 64x64, at 128x128 (four times the pixels) and twice at 64x64 (two
# renders), a 64x64 fill, a 64x64 copy, and fills whose pixel program loops 128 and 1024 times
# (the table's probes, staged). At the end the status goes back to 0 (word 0x1). Root through
# sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1110}
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.10) for the laptop first"; exit 1; }
for f in platform-hwperf-groups-loop-128__0 platform-hwperf-groups-loop-1024__0; do
	[ -f "$B/$f.bin" ] || { echo "no $B/$f.bin: stage the table"; exit 1; }
done
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
regs() { echo "$1 $(sudo -n cat "$D/hwperf" | tr '\n' ' ')"; }
job() {
	name=$1; shift
	regs "before $name:"
	sudo -n "$T" "$@" 2>&1 | grep -E '^(job|diff)|o0 |renders ok|failed' | sed 's/^/  /'
	regs "after $name:"
}
for g in $(seq 0 15); do
	echo "== group $g"
	echo "$g 0x11" | sudo -n tee "$D/hwperf" >/dev/null || echo "set failed"
	job tri64 tri
	job tri128 tri --width 128 --height 128
	job tri64x2 tri -n 2
	job fill64 fill --width 64 --height 64
	job copy64 copy --width 64 --height 64
	job loop128 probe "$B/platform-hwperf-groups-loop-128__0.bin"
	job loop1024 probe "$B/platform-hwperf-groups-loop-1024__0.bin"
done
echo "0 0x1" | sudo -n tee "$D/hwperf" >/dev/null
regs "end:"
