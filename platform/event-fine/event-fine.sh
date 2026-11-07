# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q082: when CR_EVENT_STATUS2 (0x0118) bit 6 latches. Each case of the table's fill (a pixel program
# looping 48 to 56 times in steps of 1, integer) runs after a debugfs reset, which puts the register
# back to 0x400, inside regtimeline (SGXFIVE_REGTIMELINE, default ~/regtimeline) over
# CR_CLKGATESTATUS (0x0008), CR_EVENT_STATUS2 and CR_EVENT_STATUS (0x012c), from 50 ms before the
# job; the register is read once more after each job. Three runs of the nine cases, the cases in
# a different order each run (ascending, descending, interleaved). Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1116}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.16) for the laptop first"; exit 1; }
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
	sudo -n "$RT" 0 0.05 "$R" -- "$@" 2>&1 </dev/null | grep -E "$KEEP" | grep -v "render context"
	status2
}
ORDERS="0 1 2 3 4 5 6 7 8
8 7 6 5 4 3 2 1 0
0 5 1 6 2 7 3 8 4"
echo "$ORDERS" | while read order; do
	run=$((${run:-0} + 1))
	for i in $order; do
		f=$B/platform-event-fine-int__${i}.bin
		[ -f "$f" ] || { echo "no $f: stage the table"; exit 1; }
		rt "case$((i + 48))-order$run" "$T" probe "$f"
	done
done
echo 1 | sudo -n tee "$D/reset" >/dev/null
status2
echo "## end"
