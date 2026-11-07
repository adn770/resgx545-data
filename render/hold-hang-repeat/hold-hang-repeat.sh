# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q037 again (hold-hang.sh with more repeats: the pixel control held five times, not held twice,
# the VDM job held three times, the PB page table printed before each held job).
# Q037, Q028: the render memory of hung jobs saved before the kernel recovers. The jobs of
# vdm/state1 (staged, not run, by this table's stage field): the control hung in its pixel
# task (vdm-state1-hang-pixel: its pixel PDS program issues no texture fetch the shader
# waits for) and VDM state word 1 bits 15:13 = 0 (vdm-state1-vdm-state-15-13-0), each run as
# probe --tri with --dump-render. With debugfs hold_recovery set the job stays hung in the
# firmware until the tool's wait (5 s) gives up; the tool then dumps the render memory (the
# hung job's) and closes the context, whose failed cleanup resets the GPU. Without it the
# kernel recovers first and the dump follows the recovery. 2 s in, the state (as in
# hold-fault.sh). The pixel control held, not held, and held again; then the VDM job held.
# Each dump summarised and kept as gzip in base64. hold_recovery goes back to N and debugfs
# reset is written after each held job. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1115}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.15) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
W=$(mktemp -d)
# the snapshots tri --words saved in $W/$1, in render order, and the control block
words() {
	n=0
	while [ -f "$W/$1/words.$n.txt" ]; do
		echo "#### words $n"; cat "$W/$1/words.$n.txt"; echo "#### end"
		echo "ta3d $n: $(od -An -tx4 -v -w4 "$W/$1/ta3d.$n.bin" | tr -d ' ' | tr '\n' ' ')"
		n=$((n + 1))
	done
}
ta3d_after() {
	echo "ta3d after: $(sudo -n od -An -tx4 -v -w4 "$D/buf09" | tr -d ' ' | tr '\n' ' ')"
}
cleanup() { sudo -n cat "$D/render_cleanup" | sed 's/^/cleanup: /'; }
TOOL_LINES="^job|^diff|renders ok|FAILED|overflowed|#[0-9]+: [0-9]+ tri|kpoke before|geometry only"
TOOL_LINES="$TOOL_LINES|failed|^reg 0x"
one() {
	name=$1; shift
	mkdir -p "$W/$name"
	echo "== $name: tri $*"
	sudo -n "$T" tri --keep-going --words "$W/$name" "$@" 2>&1 | grep -E "$TOOL_LINES"
	words "$name"
	ta3d_after
	cleanup
}
hold() { echo "$1" | sudo -n tee "$D/hold_recovery" >/dev/null; echo "hold_recovery: $1"; }
reset_gpu() {
	s=$(date +%s%N)
	echo 1 | sudo -n tee "$D/reset" >/dev/null
	echo "reset: ret $?, $(( ($(date +%s%N) - s) / 1000 )) us"
}
# the driver's last kernel lines, the registers (one line), kreg, status and GETMISCINFO
state() {
	echo "## state $1"
	sudo -n dmesg | tail -n 4 | sed 's/^/dmesg: /'
	echo "regs: $(sudo -n cat "$D/regs" | awk '$1 == "reg" {print $2 "=" $3}' | tr '\n' ' ')"
	echo "kreg: $(sudo -n cat "$D/kreg" 2>&1 | tr '\n' ' ')"
	sudo -n cat "$D/status" 2>&1 | grep -E "^(loaded|reg|ta3dctl|ccbctl)" | sed 's/^/status: /'
	s=$(date +%s%N)
	m=$(sudo -n timeout 20 cat "$D/miscinfo" 2>&1 | head -n 3 | tr '\n' ' ')
	echo "miscinfo: $(( ($(date +%s%N) - s) / 1000 )) us: $m"
}
# the newest render context's words now, labelled
words_now() {
	echo "#### words $1"; sudo -n cat "$D/render_words" 2>&1; echo "#### end"
	echo "ta3d $1: $(sudo -n od -An -tx4 -v -w4 "$D/buf09" | tr -d ' ' | tr '\n' ' ')"
}
# a render dump's non-zero dwords (the first 24 of each), then the files as gzip in base64
# between "#### param NAME" or "#### tadata NAME" and "#### end"
SUM='import struct, sys
for what, f in (("param", sys.argv[1]), ("tadata", sys.argv[2])):
    b = open(f, "rb").read()
    w = struct.unpack("<%dI" % (len(b) // 4), b[:len(b) // 4 * 4])
    nz = [(4 * i, v) for i, v in enumerate(w) if v]
    print(what + ": bytes", hex(len(b)), "nonzero", len(nz),
          " ".join("%#x=%08x" % x for x in nz[:24]))'
dump() {
	sudo -n python3 -c "$SUM" "$1.param.bin" "$1.tadata.bin"
	for f in param tadata; do
		echo "#### $f $2"; sudo -n gzip -c "$1.$f.bin" | base64 -w 76; echo "#### end"
	done
}
trap 'hold N' EXIT
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
PIX="--tri pixpds:12 --width 64 --height 64 --vtx-coords 2 --slot pixel=$B/pix_pa0.bin"
PIX="$PIX --slot vtxuse=$B/vtx_coords.bin $B/vdm-state1-hang-pixel__0.bin"
VDM="--tri pixel --width 64 --height 64 --vdm 1=0x0a020405 $B/vdm-state1-vdm-state-15-13-0__0.bin"
hang() {
	name=$1 held=$2 file=$3; shift 3
	echo "== $name: probe $* (hold_recovery $held)"
	hold "$held"
	mkdir -p "$W/$name"
	# shellcheck disable=SC2086
	sudo -n "$T" probe --temps 32 --dump-render "$W/$name" $* > "$W/$name.out" 2>&1 &
	P=$!
	sleep 2
	state "$name"
	wait $P
	grep -vE "^probe [^ ]+: row " "$W/$name.out" | head -n 20
	dump "$W/$name/$file" "$name"
	hold N
	[ "$held" = Y ] && reset_gpu
	cleanup
}
for f in "$B/vdm-state1-hang-pixel__0.bin" "$B/vdm-state1-vdm-state-15-13-0__0.bin"; do
	[ -f "$f" ] || { echo "no $f: stage vdm/state1"; exit 1; }
done
for r in 1 2 3 4 5; do
	echo "pb pages: $(sudo -n cat "$D/render_pb_pages" 2>&1 | tr '\n' ' ')"
	hang pixel-held-$r Y vdm-state1-hang-pixel__0 $PIX
done
hang pixel-unheld N vdm-state1-hang-pixel__0 $PIX
hang pixel-unheld-2 N vdm-state1-hang-pixel__0 $PIX
for r in 1 2 3; do
	hang vdm-15-13-0-held-$r Y vdm-state1-vdm-state-15-13-0__0 $VDM
done
sudo -n rm -rf "$W"
