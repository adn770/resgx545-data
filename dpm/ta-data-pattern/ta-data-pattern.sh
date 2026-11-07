# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q081: a 64x64 triangle on a render context for 4096x4096 (whose TA data covers page 6, offset
# 0x6000) with the TA command's word 167 (CR_DPM_REG_074C) poked to each value below (--kpoke-render
# 1:ta:167=V), and before the job debugfs tadata_fill writing page 6 with a ramp (word i holds
# 0xa5000000 + i) or, for the last cases, a constant (0x5a5a5a5a). After the job the tool's
# --dump-render copy of the TA data (debugfs render_tadata) is compared on this machine with python3
# with what was written: the count of words equal to it, the words that differ (offset and value,
# first 12) and the TA data's other pages that are not zero. The tool's lines tell the image and
# the job. Cases: no poke, 0x0ff (bit 8 clear) and bit 8 with bits 7:0 = 0x00, 0x01, 0x02, 0x04,
# 0x08, 0x10, 0x20, 0x40, 0x80, 0xff, 0x55, 0xaa; the constant: no poke, 0x100, 0x1ff.
# Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1117}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.17) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
W=$(mktemp -d)
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
trap 'reset_gpu; rm -rf "$W"' EXIT
cat > "$W/cmp.py" <<'PY'
import struct, sys
kind, base = sys.argv[1], int(sys.argv[2], 0)
d = open(sys.argv[3], "rb").read()
w = struct.unpack("<%dI" % (len(d) // 4), d)
page = w[0x6000 // 4:0x7000 // 4]
want = [(base + i) & 0xffffffff if kind == "ramp" else base for i in range(1024)]
bad = [(i * 4, page[i]) for i in range(1024) if page[i] != want[i]]
print("tadata %d bytes; page 0x6000: %d of 1024 words as written, %d differ" % (len(d), 1024 - len(bad), len(bad)))
print("differ: " + " ".join("+0x%x=0x%08x" % b for b in bad[:12]))
others = []
for p in range(len(d) // 4096):
    if p == 6:
        continue
    n = sum(1 for x in w[p * 1024:(p + 1) * 1024] if x)
    if n:
        others.append("page %d: %d nonzero" % (p, n))
print("other pages: " + ("; ".join(others[:16]) if others else "all zero"))
PY
case_run() { # NAME KIND BASE POKEVALUE|-
	name=$1 kind=$2 base=$3 v=$4
	echo "== $name: tadata_fill 6 $base $kind, ta:167=$v"
	reset_gpu
	echo "6 $base $([ "$kind" = ramp ] && echo ramp)" | sudo -n tee "$D/tadata_fill" >/dev/null
	echo "armed: $(sudo -n cat "$D/tadata_fill")"
	mkdir -p "$W/$name"
	poke=""
	[ "$v" != - ] && poke="--kpoke-render 1:ta:167=$v"
	n=$(sudo -n dmesg | wc -l)
	sudo -n "$T" tri -n 1 --width 64 --height 64 --max-width 4096 --max-height 4096 --wait-ms 8000 \
		--dump-render "$W/$name" $poke 2>&1 | grep -E "^(job|diff|tri|kpoke)|failed"
	echo "kernel: $(sudo -n dmesg | tail -n +$((n + 1)) | grep -iE 'tadata_fill|fault|kpoke|recover' | sed 's/^\[[ 0-9.]*\] //' | head -n 4 | tr '\n' ';')"
	python3 "$W/cmp.py" "$kind" "$base" "$W/$name/tri.tadata.bin"
	echo "armed after: $(sudo -n cat "$D/tadata_fill" | tr '\n' ' ')"
}
case_run ramp-none ramp 0xa5000000 -
case_run ramp-0ff ramp 0xa5000000 0x0ff
for lo in 0x00 0x01 0x02 0x04 0x08 0x10 0x20 0x40 0x80 0xff 0x55 0xaa; do
	v=$(printf '0x%03x' $(( 0x100 | lo )))
	case_run "ramp-$v" ramp 0xa5000000 "$v"
done
case_run const-none const 0x5a5a5a5a -
case_run const-0x100 const 0x5a5a5a5a 0x100
case_run const-0x1ff const 0x5a5a5a5a 0x1ff
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
