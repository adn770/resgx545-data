# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q036, Q067, Q045: the parameter buffer's page table, the DPM status registers and the TA data's
# DPM pages after one job at each case: the triangle at 64x64, 256x256, 1024x768 and 4096x4096
# with the whole PB (0x422 pages), at 1024x768 with 0x40 and 0x30 pages (the second a partial
# render) and at 4096x4096 with 0x100 pages (one partial render), and the 64x64 triangle on
# contexts for targets up to 1024x768 and 4096x4096 (a larger TA data); then two renders on one
# 64x64 context. Each job runs as `probe --tri pixel` (the green pixel shader of the
# table's probe, staged) with its render memory dumped while the context lives; after it the
# registers 0x0600-0x0750 (debugfs regs, read-only), TA3DCtl (debugfs buf09) and, from the
# dumps, the page table walked from its head as runs of pages, every entry the host's chain
# does not hold, and the non-zero dwords of the TA data's DPM control, OTPM and state pages.
# render_pb_pages is put back to the whole PB at the end. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}/dpm-free-list-green__0.bin
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
[ -f "$B" ] || { echo "no $B: stage the table's probe"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
W=$(mktemp -d)
PY=$(cat <<'EOF'
import struct, sys
param, tadata = sys.argv[1], sys.argv[2]
pages, mw, mh = int(sys.argv[3], 0), int(sys.argv[4]), int(sys.argv[5])
p = open(param, "rb").read()
PT = 0x423000 - 0x1000          # the page table, as a slot offset less the dump's start
pt = struct.unpack_from("<%dI" % (pages + 2), p, PT)
host = {i: ((0xffff if i == 1 else i - 1) << 16) | (0xffff if i == pages else i + 1)
        for i in range(1, pages + 1)}
heads = [i for i in range(1, pages + 1) if pt[i] >> 16 == 0xffff]
print("pt: entries", pages, "heads", " ".join(hex(h) for h in heads))
if len(heads) == 1:
    order, seen, i = [], set(), heads[0]
    while i != 0xffff and i not in seen and 1 <= i <= pages:
        seen.add(i)
        order.append(i)
        i = pt[i] & 0xffff
    bad = [j for k, j in enumerate(order[1:]) if pt[j] >> 16 != order[k]]
    runs, s = [], order[0]
    for a, b in zip(order, order[1:] + [None]):
        if b != a + 1:
            runs.append(f"{s:#x}" if s == a else f"{s:#x}-{a:#x}")
            s = b
    print("pt: walk", len(order), "pages, tail", hex(order[-1]), "prev of tail",
          hex(pt[order[-1]] >> 16), "bad prev", len(bad))
    print("pt: order", ",".join(runs))
diff = [(i, pt[i]) for i in range(0, pages + 2) if pt[i] != host.get(i, 0)]
print("pt: changed", len(diff), " ".join(f"{i:#x}={v:#010x}" for i, v in diff[:80]))
# the TA data layout of the kernel for targets up to mw x mh
tx, ty = -(-mw // 32), -(-mh // 16)
n = 4 if mw * mh >= 640 * 480 else 2
mx, my = -(-(-(-tx // n)) // 4) * 4, -(-(-(-ty // n)) // 4) * 4
side = 1
while side < max(n * mx, n * my):
    side <<= 1
ctl = -(-4 * side * side // 4096) * 4096
t = open(tadata, "rb").read()
print("tadata: bytes", hex(len(t)), "control", hex(ctl), "otpm", hex(ctl + 0x1000),
      "state", hex(ctl + 0x2000), "rgn", hex(ctl + 0x3000))
for name, off in (("control", ctl), ("otpm", ctl + 0x1000), ("state", ctl + 0x2000)):
    w = struct.unpack_from("<1024I", t, off) if off + 4096 <= len(t) else ()
    nz = [(k, v) for k, v in enumerate(w) if v]
    print(f"tadata {name}: nonzero {len(nz)}",
          " ".join(f"{4 * k:#05x}={v:#010x}" for k, v in nz[:64]))
EOF
)
state() {
	sudo -n cat "$D/regs" | awk '$1 == "reg" && $2 >= "0x0600" && $2 <= "0x0750"' |
		tr '\n' ' ' | sed 's/^/regs: /'; echo
	echo "ta3dctl: $(sudo -n od -An -tx4 -v -w4 "$D/buf09" | tr -d ' ' | tr '\n' ' ')"
}
summary() {
	sudo -n python3 -c "$PY" "$W/$1.param.bin" "$W/$1.tadata.bin" "$2" "$3" "$4"
	sudo -n rm -f "$W/$1.param.bin" "$W/$1.tadata.bin"
}
pb() { sudo -n sh -c "echo $1 > $D/render_pb_pages"; }
one() {
	name=$1 pages=$2 w=$3 h=$4 mw=$5 mh=$6
	pb "$pages"
	echo "== $name: probe --tri pixel ${w}x${h} max ${mw}x${mh} pb $pages"
	sudo -n "$T" probe --tri pixel --width "$w" --height "$h" --max-width "$mw" \
		--max-height "$mh" --dump-render "$W" "$B" 2>&1 | grep -vE "^probe [^ ]+: row "
	state
	summary dpm-free-list-green__0 "$pages" "$mw" "$mh"
}
one full-64x64 0x422 64 64 64 64
one full-256x256 0x422 256 256 256 256
one full-1024x768 0x422 1024 768 1024 768
one full-4096x4096 0x422 4096 4096 4096 4096
one pb40-1024x768 0x40 1024 768 1024 768
one pb30-1024x768 0x30 1024 768 1024 768
one pb100-4096x4096 0x100 4096 4096 4096 4096
one max1024-64x64 0x422 64 64 1024 768
one max4096-64x64 0x422 64 64 4096 4096
pb 0x422
echo "== two-renders-64x64: tri -n 2 pb 0x422"
sudo -n "$T" tri -n 2 --regs 0x0700-0x0740 --dump-render "$W" 2>&1 |
	grep -E "^job|^diff|^reg 0x07[0-4]|renders ok|FAILED|overflowed|#[0-9]+: [0-9]+ tri"
state
summary tri 0x422 64 64
sudo -n rm -rf "$W"
echo "pb_pages: $(sudo -n cat "$D/render_pb_pages")"
