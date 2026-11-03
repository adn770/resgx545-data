# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q049, Q065, Q067, Q081: kernel pokes of single words of a render's run (debugfs kpoke through
# tri --kpoke-render), each case's image, kernel lines (since its "resgx545 case" mark), cleanup
# trace and render memory compared with an unpoked control of the same shape:
# - ctx7: render context dword 7 (the scratch primitive block's address) set to 0xdeadbeef and
#   to the background object's address (slot + 0x464000) at the first kick, on one render, a
#   scene of three kicks and a 1024x768 render in a 0x30-page parameter buffer; twice each;
#   the 0x40 bytes at the scratch primitive block after each, from the parameter dump;
# - pbflag: the PB descriptor's flag bit 0 set at the first kick; the page table (parameter
#   dump from +0x423000) compared with the control's; twice;
# - reg074c: TA command word 167 (CR_DPM_REG_074C) with bit 8 and with 0x1ff, on contexts for
#   4096x4096 and 1024x768 targets, the TA data compared with the control's;
# - flag0: render flag bit 0 (TA command word 7) with debugfs hold_recovery set: 2 s in, the
#   context's words (render_words) and the TA/3D control block, then debugfs reset with the hold
#   set, then the hold goes back to N.
# Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1110}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.10) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
W=$(mktemp -d)
RUN=$(date +%s)-$$
KEEP="^job|^diff|renders ok|FAILED|failed|#[0-9]+: [0-9]+ tri|kpoke before|geometry only"
mark() { printf 'resgx545 case %s %s\n' "$1" "$RUN" | sudo -n tee /dev/kmsg >/dev/null; }
lines() {
	sudo -n dmesg | awk -v m="resgx545 case $1 $RUN" 'index($0, m) {on = 1; next}
		on && /sgxfive|SGX/ && !/ta3dctl|hostctl|ccbctl|reg 0x|loaded 1/ {print "kline: " $0}'
}
# DIFF A B OFF LEN: the dwords of B's [OFF, OFF+LEN) that differ from A's (at most 40)
DIFF='import struct, sys
a, b = open(sys.argv[1], "rb").read(), open(sys.argv[2], "rb").read()
off, n = int(sys.argv[3], 0), int(sys.argv[4], 0)
d = [(i, struct.unpack_from("<I", a, i)[0], struct.unpack_from("<I", b, i)[0])
     for i in range(off, min(off + n, len(a), len(b)) - 3, 4)
     if a[i:i + 4] != b[i:i + 4]]
print("differ:", len(d), "dwords;", " ".join("%#x:%08x>%08x" % x for x in d[:40]))'
# WORDS F OFF N: N dwords of F from OFF
WORDS='import struct, sys
b = open(sys.argv[1], "rb").read(); o = int(sys.argv[2], 0); n = int(sys.argv[3])
print(" ".join("%08x" % struct.unpack_from("<I", b, o + 4 * i)[0] for i in range(n)))'
# one NAME ARGS...: tri with ARGS, its render memory to $W/NAME
one() {
	name=$1; shift
	mark "$name"
	mkdir -p "$W/$name"
	echo "== $name: tri $*"
	sudo -n "$T" tri --keep-going --dump-render "$W/$name" --words "$W/$name" "$@" 2>&1 |
		grep -E "$KEEP"
	n=0; while [ -f "$W/$name/words.$((n + 1)).txt" ]; do n=$((n + 1)); done
	echo "ctx:7 after render $n: $(grep '^ctx:7=' "$W/$name/words.$n.txt" 2>/dev/null)"
	sudo -n cat "$D/render_cleanup" | head -n 1 | sed 's/^/cleanup: /'
	lines "$name"
}
param() { echo "$3: $(sudo -n python3 -c "$WORDS" "$W/$1/tri.param.bin" "$2" 16)"; }
cmp_dump() {	# CONTROL CASE FILE OFF LEN
	[ -f "$W/$1/tri.$3.bin" ] && [ -f "$W/$2/tri.$3.bin" ] || { echo "differ: no dump"; return; }
	sudo -n python3 -c "$DIFF" "$W/$1/tri.$3.bin" "$W/$2/tri.$3.bin" "$4" "$5"
}
hold() { echo "$1" | sudo -n tee "$D/hold_recovery" >/dev/null; echo "hold_recovery: $1"; }
trap 'hold N' EXIT
PB=$(sudo -n cat "$D/render_pb_pages")
SCENE="-n 3 --geometry 1 --geometry 2"
for r in 1 2; do
	one "ctx7-control-r$r" -n 1
	param "ctx7-control-r$r" 0x463000 "primitive block"
	one "ctx7-dead-r$r" -n 1 --kpoke-render "1:ctx:7=0xdeadbeef"
	param "ctx7-dead-r$r" 0x463000 "primitive block"
	one "ctx7-bg-r$r" -n 1 --kpoke-render "1:ctx:7=0x10464000"
	param "ctx7-bg-r$r" 0x463000 "primitive block"
	param "ctx7-bg-r$r" 0x464000 "background object"
	param "ctx7-control-r$r" 0x464000 "background object (control)"
	one "ctx7-scene-control-r$r" $SCENE
	one "ctx7-scene-dead-r$r" $SCENE --kpoke-render "1:ctx:7=0xdeadbeef"
	echo 0x30 | sudo -n tee "$D/render_pb_pages" >/dev/null
	one "ctx7-partial-control-r$r" --width 1024 --height 768
	one "ctx7-partial-dead-r$r" --width 1024 --height 768 --kpoke-render "1:ctx:7=0xdeadbeef"
	echo "$PB" | sudo -n tee "$D/render_pb_pages" >/dev/null
	one "pbflag-r$r" -n 1 --kpoke-render "1:pb:0^=0x1"
	echo "page table vs ctx7-control-r$r: $(cmp_dump "ctx7-control-r$r" "pbflag-r$r" param \
		0x423000 0x1088)"
	param "pbflag-r$r" 0x423000 "page table"
	param "ctx7-control-r$r" 0x423000 "page table (control)"
done
for m in 4096x4096 1024x768; do
	B="--max-width ${m%x*} --max-height ${m#*x}"
	# shellcheck disable=SC2086
	one "reg074c-$m-control" -n 1 $B
	for v in 0x100 0x1ff; do
		# shellcheck disable=SC2086
		one "reg074c-$m-$v" -n 1 $B --kpoke-render "1:ta:167=$v"
		echo "tadata vs control: $(cmp_dump "reg074c-$m-control" "reg074c-$m-$v" tadata 0 \
			0x200000)"
	done
done
mark flag0
hold Y
mkdir -p "$W/flag0"
echo "== flag0: tri -n 1 --kpoke-render 1:ta:7^=0x1 --wait-ms 20000 (hold_recovery Y)"
sudo -n "$T" tri -n 1 --wait-ms 20000 --words "$W/flag0" --kpoke-render "1:ta:7^=0x1" \
	> "$W/flag0.out" 2>&1 &
P=$!
sleep 2.5
echo "#### words held"; sudo -n cat "$D/render_words"; echo "#### end"
echo "ta3d held: $(sudo -n od -An -tx4 -v -w4 "$D/buf09" | tr -d ' ' | tr '\n' ' ')"
lines flag0
echo 1 | sudo -n tee "$D/reset" >/dev/null
echo "reset: ret $?"
hold N
wait $P
grep -E "$KEEP" "$W/flag0.out"
sudo -n cat "$D/render_cleanup" | head -n 1 | sed 's/^/cleanup: /'
lines flag0
echo "## render_pb_pages $(sudo -n cat "$D/render_pb_pages")"
sudo -n rm -rf "$W"
