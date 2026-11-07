# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q036: what the DPM status registers' high halves, TA3DCtl dword 36 and the page table hold after
# scenes that fill the global list: the triangle and copies of it (probe --tri pixel --vertices N,
# 3 to 1500, the rig's wide scene) on a 4096x4096 and a 1024x768 target with 0x422, 0x100, 0x40
# and 0x23 pages of parameter buffer, three runs of each case (a new context each). Each job runs
# as `probe --tri pixel` with its render memory dumped while the context lives (a job that
# overflows the buffer fails with its context kept); after it the registers 0x0600-0x0750 (debugfs
# regs, read-only), TA3DCtl (debugfs buf09) and, from the dumps, the page table walked from its
# head and the TA data's DPM pages as in free-list.sh. render_pb_pages is put back to the whole
# PB at the end. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1116}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}/dpm-partial-wide-green__0.bin
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
	name=$1 pages=$2 w=$3 h=$4 n=$5
	pb "$pages"
	echo "== $name: probe --tri pixel ${w}x${h} vertices $n pb $pages"
	sudo -n "$T" probe --tri pixel --width "$w" --height "$h" --vertices "$n" --dump-render "$W" \
		"$B" 2>&1 | grep -vE "^probe [^ ]+: row |^programs|: scratch at"
	state
	summary dpm-partial-wide-green__0 "$pages" "$w" "$h"
}
for run in 1 2 3; do
	for pages in 0x422 0x100 0x40 0x23; do
		for n in 3 300 900 1500; do
			one "4096x4096-pb$pages-v$n-r$run" "$pages" 4096 4096 "$n"
		done
	done
	for pages in 0x422 0x23; do
		for n in 3 300 1500; do
			one "1024x768-pb$pages-v$n-r$run" "$pages" 1024 768 "$n"
		done
	done
done
pb 0x422
sudo -n rm -rf "$W"
echo "pb_pages: $(sudo -n cat "$D/render_pb_pages")"
