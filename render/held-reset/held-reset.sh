# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# render_uapi.md section 13's kernel follow-ups, on the linux fork's commits 30 and 31: a reset
# written while a recovery is held, the held job's log, and a failed cleanup while held. Each
# case marks the kernel log ("resgx545 case NAME", read with render_words.py log) and sets
# debugfs hold_recovery; debugfs reset is written while it is still set, then it goes back to N.
# - fault: a render faulting on its unmapped stream page (tri --fault, 30 s wait, in the
#   background); 4 s in, the driver's lines since the mark and the state; 6 s later the lines
#   again; the reset (timed); the tool's lines.
# - hang: the pixel task that waits for a fetch it never issued (vdm/state1's hang-pixel job,
#   staged), run as probe --tri; 3 s in, the lines and the state; the reset; the probe's lines.
# - cleanup: a 128x128 triangle on its own context, its every pixel printed (--pixels) into a
#   pipe read only 4 s later, so the tool, its render done, waits there with the context alive;
#   1 s in, the faulting render (30 s wait, background) is held; once the pipe is read the
#   triangle's tool destroys its context, whose cleanup the stopped EDM does not answer; 2 s
#   later the lines, the state and the cleanup trace; the reset; the lines, the state, the
#   faulting render's lines.
# After each, a fill and the triangle. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1110}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.10) for the laptop first"; exit 1; }
[ -f "$B/vdm-state1-hang-pixel__0.bin" ] || { echo "no hang-pixel job: stage vdm/state1"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
W=$(mktemp -d)
RUN=$(date +%s)-$$	# the cases' marks are this run's
TOOL_LINES="^job|^diff|renders ok|FAILED|failed|#[0-9]+: [0-9]+ tri|geometry only"
TOOL_LINES="$TOOL_LINES|^probe .*: (failed|tri)"
hold() { echo "$1" | sudo -n tee "$D/hold_recovery" >/dev/null; echo "hold_recovery: $1"; }
mark() {
	printf 'resgx545 case %s %s\n' "$1" "$RUN" | sudo -n tee /dev/kmsg >/dev/null
	echo "== $1"
}
# the driver's lines since the case's mark, numbered from it
lines() {
	echo "## lines $1"
	sudo -n dmesg | awk -v m="resgx545 case $CASE $RUN" 'index($0, m) {on = 1; next}
		on && /sgxfive|SGX/ {print "kline: " $0}'
}
reset_gpu() {
	s=$(date +%s%N)
	echo 1 | sudo -n tee "$D/reset" >/dev/null
	echo "reset: ret $?, $(( ($(date +%s%N) - s) / 1000 )) us"
}
state() {
	echo "## state $1"
	echo "hold_recovery: $(sudo -n cat "$D/hold_recovery")"
	sudo -n cat "$D/status" 2>&1 | grep -E "^(loaded|reg 0x(008|118))" | sed 's/^/status: /'
	s=$(date +%s%N)
	m=$(sudo -n timeout 20 cat "$D/miscinfo" 2>&1 | head -n 1)
	echo "miscinfo: $(( ($(date +%s%N) - s) / 1000 )) us: $m"
}
health() {
	echo "## health"
	sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
	sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
}
trap 'hold N' EXIT

CASE=fault; mark fault
hold Y
sudo -n "$T" tri --fault --wait-ms 30000 > "$W/fault.out" 2>&1 &
P=$!
sleep 4
lines held-4s
state held
sleep 6
lines held-10s
reset_gpu
hold N
wait $P
echo "## tool fault"; grep -E "$TOOL_LINES" "$W/fault.out"
lines after-reset
state after-reset
health

CASE=hang; mark hang
hold Y
PIX="--tri pixpds:12 --width 64 --height 64 --vtx-coords 2 --slot pixel=$B/pix_pa0.bin"
PIX="$PIX --slot vtxuse=$B/vtx_coords.bin $B/vdm-state1-hang-pixel__0.bin"
# shellcheck disable=SC2086
sudo -n "$T" probe --temps 32 $PIX > "$W/hang.out" 2>&1 &
P=$!
sleep 3
lines held-3s
state held
reset_gpu
hold N
wait $P
echo "## tool hang"; grep -E "$TOOL_LINES" "$W/hang.out"
lines after-reset
state after-reset
health

CASE=cleanup; mark cleanup
hold Y
s=$(date +%s%N)
sudo -n "$T" tri --width 128 --height 128 --pixels 2>&1 | (sleep 4; grep -E "$TOOL_LINES") \
	> "$W/tri.out" &
Q=$!
sleep 1
sudo -n "$T" tri --fault --wait-ms 30000 > "$W/cleanup.out" 2>&1 &
P=$!
wait $Q
echo "tri: $(( ($(date +%s%N) - s) / 1000 )) us"
echo "## tool tri"; cat "$W/tri.out"
sleep 2
lines held-after-cleanup
state held-after-cleanup
sudo -n cat "$D/render_cleanup" | sed 's/^/cleanup: /'
reset_gpu
hold N
wait $P
echo "## tool cleanup"; grep -E "$TOOL_LINES" "$W/cleanup.out"
sleep 1
lines after-reset
state after-reset
sudo -n cat "$D/render_cleanup" | sed 's/^/cleanup: /'
health
sudo -n rm -rf "$W"
