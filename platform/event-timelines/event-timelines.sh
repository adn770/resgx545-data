# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q082, Q003, Q036, Q048: a few registers sampled fast (regtimeline, SGXFIVE_REGTIMELINE,
# default ~/regtimeline; the first sample and every change) through each job:
# CR_CLKGATESTATUS (0x0008), CR_EVENT_STATUS2 (0x0118), CR_EVENT_STATUS (0x012c),
# CR_BIF_INT_STAT (0x0c04), CR_BIF_FAULT (0x0c08), and the DPM's 0x0658, 0x0660, 0x0700,
# 0x070c, 0x0710, 0x071c, 0x072c and 0x0748. Twice each: the triangle at 64x64 and 256x256 with
# one, two and three renders on its context, at 128x128 with three, at 1024x768 with two
# renders in a 0x30-page parameter buffer (partial renders in each; the TA/3D control block
# after it), a fill, a copy, and fills running the table's two loops (1e7 instructions,
# floating-point and integer), staged as $SGXFIVE_PROBE_BINS. Then with debugfs hold_recovery
# set, once each, sampled for 3 s from 50 ms before the kick: vdm/state1's job hung in its pixel
# task, its job hung in the TA (VDM state word 1 bits 15:13 = 0), and a render faulting on its
# unmapped stream page; debugfs reset is written with the hold set, then it goes back to N.
# Nothing else is written but render_pb_pages, which is put back. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1110}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.10) for the laptop first"; exit 1; }
[ -x "$RT" ] || { echo "no $RT: build tools/sweep/regtimeline.c on the laptop first"; exit 1; }
for f in vdm-state1-hang-pixel__0 vdm-state1-vdm-state-15-13-0__0 \
	platform-event-timelines-fmad__0 platform-event-timelines-int__0; do
	[ -f "$B/$f.bin" ] || { echo "no $B/$f.bin: stage the table"; exit 1; }
done
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
W=$(mktemp -d)
R="0x0008,0x0118,0x012c,0x0c04,0x0c08,0x0658,0x0660,0x0700,0x070c,0x0710,0x071c,0x072c,0x0748"
KEEP="^(job|diff|tri|probe|fill|copy|timeline|tl )|failed"
rt() {
	name=$1 total=$2; shift 2
	echo "== $name: regtimeline $total 0.05 -- $*"
	sudo -n "$RT" "$total" 0.05 "$R" -- "$@" 2>&1 | grep -E "$KEEP" | grep -v "render context"
}
hold() { echo "$1" | sudo -n tee "$D/hold_recovery" >/dev/null; echo "hold_recovery: $1"; }
reset_gpu() {
	echo 1 | sudo -n tee "$D/reset" >/dev/null
	echo "reset: ret $?"
}
ta3d() { echo "ta3d after: $(sudo -n od -An -tx4 -v -w4 "$D/buf09" | tr -d ' ' | tr '\n' ' ')"; }
trap 'hold N' EXIT
PB=$(sudo -n cat "$D/render_pb_pages")
for run in 1 2; do
	for s in 64 256; do
		for n in 1 2 3; do
			rt "tri-${s}-n$n-$run" 0 "$T" tri --width $s --height $s -n $n
		done
	done
	rt "tri-128-n3-$run" 0 "$T" tri --width 128 --height 128 -n 3
	echo 0x30 | sudo -n tee "$D/render_pb_pages" >/dev/null
	rt "partial-1024x768-n2-$run" 0 "$T" tri --width 1024 --height 768 -n 2
	ta3d
	echo "$PB" | sudo -n tee "$D/render_pb_pages" >/dev/null
	rt "fill-$run" 0 "$T" fill
	rt "copy-$run" 0 "$T" copy
	rt "fmad-loop-$run" 0 "$T" probe "$B/platform-event-timelines-fmad__0.bin"
	rt "int-loop-$run" 0 "$T" probe "$B/platform-event-timelines-int__0.bin"
done
echo "## render_pb_pages back to $(sudo -n cat "$D/render_pb_pages")"
PIX="--tri pixpds:12 --width 64 --height 64 --vtx-coords 2 --slot pixel=$B/pix_pa0.bin"
PIX="$PIX --slot vtxuse=$B/vtx_coords.bin $B/vdm-state1-hang-pixel__0.bin"
VDM="--tri pixel --width 64 --height 64 --vdm 1=0x0a020405 $B/vdm-state1-vdm-state-15-13-0__0.bin"
held() {
	name=$1; shift
	hold Y
	# the job in the background, so the timeline runs its 3 s while it stays held
	rt "$name" 3 sh -c "$* > $W/$name.out 2>&1 &"
	reset_gpu
	hold N
	sleep 2
	echo "## tool $name"; grep -E "$KEEP" "$W/$name.out" | grep -v "render context"
}
held held-pixel-hang "$T" probe --temps 32 $PIX
held held-ta-hang "$T" probe --temps 32 $VDM
held held-fault "$T" tri --fault --wait-ms 30000
sudo -n rm -rf "$W"
