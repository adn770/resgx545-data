# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q045: tri --width 1024 --height 768 --keep-overflow --dump-render DIR --dump-each --regs
# 0x0700-0x0750 on a parameter buffer of 0x28 pages (the scene overflows and is finished by
# partial renders; 0x422 pages is the control that does not). After each render the dump of the TA
# data (debugfs render_tadata, tri.N.tadata.bin) is reduced here to the non-zero dwords of its
# control (0x4000), OTPM (0x5000) and state (0x6000) pages. Cases, two runs of each: P1 one render;
# P2 two renders; P3 two renders with the second's render flags flipped by 0x8 (kernel poke
# ta:7^=0x8, --kpoke-render 2:), so the TA kick of the second is issued with flag 0x8 changed; P4 one
# render with debugfs tadata_fill writing the state page (page 6) with a ramp (word i holds
# 0xa5000000 + i) just before the kick; P5 the same on the whole PB (no partial render); P6 one
# render with 0x0740 = 0x200 written (debugfs kregnow) before it; P7 as P6 with 0x3fe00. The
# GPU is reset before each case; render_pb_pages is put back at the end. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1120}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.20) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$SRCV_FILE"
echo "## loaded module"; SRCV_LOADED=$(sudo -n cat /sys/module/gma500_gfx/srcversion); echo "$SRCV_LOADED"
[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
echo "## tool"; sha256sum "$T"
echo "## clock"; date
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
pb() { sudo -n sh -c "echo $1 > $D/render_pb_pages"; }
W=$(mktemp -d)
trap 'pb 0x422; reset_gpu; rm -rf "$W"' EXIT
PY=$(cat <<'PYEOF'
import struct, sys
d = open(sys.argv[1], "rb").read()
ramp = len(sys.argv) > 2
for off in (0x4000, 0x5000, 0x6000):
    w = struct.unpack("<1024I", d[off:off + 4096])
    nz = [(4 * i, v) for i, v in enumerate(w) if v]
    s = "tadata %#x: %d non-zero" % (off, len(nz))
    if ramp and off == 0x6000:
        s += ", %d equal to the ramp" % sum(1 for i, v in enumerate(w) if v == 0xa5000000 + i)
    print(s + "".join(" %#05x=%08x" % kv for kv in nz[:10]) + (" ..." if len(nz) > 10 else ""))
PYEOF
)
KEEP="^(job|diff|tri|tri:|reg 0x07[24]|reg 0x0740)|failed|FAILED|renders ok|overflowed"
case_run() { # NAME PAGES PRE RAMP ARGS...
	name=$1 pages=$2 pre=$3 ramp=$4; shift 4
	echo "== $name: pb $pages, kregnow ${pre:-none}, tadata_fill ${ramp:-none}; tri $*"
	reset_gpu
	pb "$pages"
	n=$(sudo -n dmesg | wc -l)
	[ -n "$pre" ] && echo "$pre" | sudo -n tee "$D/kregnow" >/dev/null
	[ -n "$ramp" ] && echo "6 0xa5000000 ramp" | sudo -n tee "$D/tadata_fill" >/dev/null
	rm -rf "$W/$name"; mkdir -p "$W/$name"
	sudo -n timeout 300 "$T" tri --width 1024 --height 768 --keep-overflow --wait-ms 20000 \
		--dump-render "$W/$name" --dump-each --regs 0x0700-0x0750 "$@" 2>&1 </dev/null |
		grep -E "$KEEP" | grep -v "us$" | cut -c1-200
	for f in "$W/$name"/tri.[0-9]*.tadata.bin; do
		[ -f "$f" ] || continue
		echo "$(basename "$f"): $(python3 -c "$PY" "$f" $ramp | tr '\n' '|' | sed 's/|/ | /g')"
	done
	sudo -n dmesg | tail -n +$((n + 1)) | grep -iE "kregnow|hang|reset|recover|timed out|fault|lost|cancel" |
		cut -c1-180 | head -6
}
for i in 1 2; do
	case_run "P1-one-render-$i" 0x28 "" ""
	case_run "P2-two-renders-$i" 0x28 "" "" -n 2
	case_run "P3-second-flag8-$i" 0x28 "" "" -n 2 --kpoke-render 2:ta:7^=0x8
	case_run "P4-ramp-partial-$i" 0x28 "" ramp
	case_run "P5-ramp-whole-pb-$i" 0x422 "" ramp
	case_run "P6-reg0740-0x200-$i" 0x28 "0x0740=0x200" ""
	case_run "P7-reg0740-0x3fe00-$i" 0x28 "0x0740=0x3fe00" ""
	case_run "P0-whole-pb-$i" 0x422 "" ""
done
pb 0x422
echo "pb_pages: $(sudo -n cat "$D/render_pb_pages")"
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
