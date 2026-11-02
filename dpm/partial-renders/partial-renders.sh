# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q038: which pixels of an overflowing scene are missing, tile by tile, and whether a later
# render's background paints them: the triangle at 1024x768 with 0x422, 0x30, 0x28, 0x24 and
# 0x23 pages and at 4096x4096 with 0x422, 0x100, 0x40 and 0x23 pages, each with render details
# word 3 (CR_ISP_CTL) at the kernel's 0xf0100 and at 0xf0000 (PROCESS_EMPTY_TILES clear: a
# region with no control stream is left unwritten, so a pixel a partial render stored and the
# final render has nothing for keeps the partial render's colour). The target is the sentinel
# 0xdeadbeef before the job. Every pixel is read (--pixels) and reduced on the laptop to one
# character per 32x16 tile: G all triangle (0xff00ff00), B all background (0xff203040), S all
# sentinel, g triangle and background, s triangle and sentinel, b background and sentinel, m
# all three, O any other colour; with the counts of each colour (the tool's text image of a
# wrong render is dropped). Then the DPM status registers and TA3DCtl (debugfs buf09).
# render_pb_pages is put back at the end. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
PY=$(cat <<'EOF'
import sys
w, h = int(sys.argv[1]), int(sys.argv[2])
G, B, S = "0xff00ff00", "0xff203040", "0xdeadbeef"
tx, ty = -(-w // 32), -(-h // 16)
cnt = [[[0, 0, 0, 0] for _ in range(tx)] for _ in range(ty)]
tot = [0, 0, 0, 0]
for line in sys.stdin:
    if not line.startswith("row "):
        if line.strip("#.?\n"):     # the tool's text image of a wrong render: dropped
            sys.stdout.write(line)
        continue
    head, _, rest = line.partition(":")
    y = int(head[4:])
    row = cnt[y // 16]
    for x, v in enumerate(rest.split()):
        k = 0 if v == G else 1 if v == B else 2 if v == S else 3
        row[x // 32][k] += 1
        tot[k] += 1
print("pixels: triangle", tot[0], "background", tot[1], "sentinel", tot[2], "other", tot[3])
codes = {(1, 0, 0): "G", (0, 1, 0): "B", (0, 0, 1): "S", (1, 1, 0): "g", (1, 0, 1): "s",
         (0, 1, 1): "b", (1, 1, 1): "m"}
for j, row in enumerate(cnt):
    s = "".join("O" if c[3] else codes.get(tuple(int(n > 0) for n in c[:3]), "?") for c in row)
    print(f"tiles {j:3d}: {s}")
EOF
)
pb() { sudo -n sh -c "echo $1 > $D/render_pb_pages"; }
one() {
	name=$1 pages=$2 w=$3 h=$4 ctl=$5
	pb "$pages"
	echo "== $name: tri ${w}x${h} pb $pages rd:3=$ctl"
	sudo -n "$T" tri --width "$w" --height "$h" --pixels --regs 0x0700-0x0740 \
		--kpoke-render "1:rd:3=$ctl" 2>&1 | python3 -c "$PY" "$w" "$h" |
		grep -vE "^tri: render context|^layout:|^regs:"
	echo "ta3dctl: $(sudo -n od -An -tx4 -v -w4 "$D/buf09" | tr -d ' ' | tr '\n' ' ')"
}
for p in 0x422 0x30 0x28 0x24 0x23; do
	for c in 0xf0100 0xf0000; do
		one "1024x768-pb$p-ctl$c" "$p" 1024 768 "$c"
	done
done
for p in 0x422 0x100 0x40 0x23; do
	for c in 0xf0100 0xf0000; do
		one "4096x4096-pb$p-ctl$c" "$p" 4096 4096 "$c"
	done
done
pb 0x422
echo "pb_pages: $(sudo -n cat "$D/render_pb_pages")"
