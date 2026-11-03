# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q028, Q003: a faulting render (tri --fault: the scene's stream page unmapped) with debugfs
# hold_recovery set, so the BIF fault watchdog and the job timeout report the hang once and
# leave the job in the firmware. The tool waits 20 s (--wait-ms) in the background; 2 s in,
# the state is read: the driver's last kernel lines, every register of debugfs regs, kreg,
# status (HostCtl, TA3DCtl, the kernel CCB control), GETMISCINFO through debugfs miscinfo
# (whether the EDM still answers a command, and after how long), the render context's words
# and the render memory (debugfs render_param and render_tadata, summarised and kept as gzip in
# base64); then a fill on another context, with the state after it. hold_recovery is cleared
# and debugfs reset written; the tool's own lines, words and cleanup trace follow, then the
# state after the reset. hold_recovery goes back to N. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1110}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.10) for the laptop first"; exit 1; }
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
state idle
hold Y
mkdir -p "$W/fault"
echo "== fault-held: tri --fault --wait-ms 20000"
sudo -n "$T" tri --fault --wait-ms 20000 --words "$W/fault" > "$W/fault.out" 2>&1 &
P=$!
sleep 2
state held
words_now held
sudo -n cat "$D/render_param" > "$W/held.param.bin"
sudo -n cat "$D/render_tadata" > "$W/held.tadata.bin"
dump "$W/held" fault-held
echo "== held-fill: fill (another context, while held)"
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff|failed|FAIL"
state after-fill
hold N
reset_gpu
wait $P
echo "== fault-held-tool: the tri process's own lines"
grep -E "$TOOL_LINES" "$W/fault.out"
words fault
ta3d_after
cleanup
state after-reset
sudo -n rm -rf "$W"
