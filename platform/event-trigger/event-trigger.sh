# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q082: when CR_EVENT_STATUS2 (0x0118) bit 6 latches. Each of the table's fills (a pixel program
# looping 16 to 12500 times, integer, then 1024 and 4096 times floating-point) runs after a debugfs
# reset, which puts the register back to 0x400, inside regtimeline (SGXFIVE_REGTIMELINE,
# default ~/regtimeline) over CR_CLKGATESTATUS (0x0008), CR_EVENT_STATUS2 and CR_EVENT_STATUS
# (0x012c), from 50 ms before the job; then the triangle and a copy, after a reset too. The
# register is read once more after each job. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1110}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.10) for the laptop first"; exit 1; }
[ -x "$RT" ] || { echo "no $RT: build tools/sweep/regtimeline.c on the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
R="0x0008,0x0118,0x012c"
KEEP="^(job|diff|tri|probe|fill|copy|timeline|tl )|failed"
status2() { sudo -n cat "$D/regs" | awk '$1 == "reg" && $2 == "0x0118" {print "status2: " $3}'; }
rt() {
	name=$1; shift
	echo 1 | sudo -n tee "$D/reset" >/dev/null
	echo "== $name: reset, then regtimeline 0 0.05 -- $*"
	status2
	sudo -n "$RT" 0 0.05 "$R" -- "$@" 2>&1 | grep -E "$KEEP" | grep -v "render context"
	status2
}
for c in int-16 int-128 int-1024 int-2048 int-4096 int-12500 fmad-1024 fmad-4096; do
	f=$B/platform-event-trigger-${c}__0.bin
	[ -f "$f" ] || { echo "no $f: stage the table"; exit 1; }
	rt "$c" "$T" probe "$f"
done
rt tri "$T" tri
rt copy "$T" copy
echo 1 | sudo -n tee "$D/reset" >/dev/null
status2
