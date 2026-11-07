# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q038: whether a background object that fetches the render target at the pixel's position (a
# strided ARGB8888 texture at the target's address, the pixel position iterated by the background's
# primary program, bg_reload_*.s and pds_bg_pos.s) gives the whole image of a scene that overflows
# the parameter buffer: the triangle at 1024x768 with 0x422 pages (no overflow) and 0x23 pages
# (overflow, partial renders) and at 4096x4096 with 0x422 and 0x100 pages, each with the library's
# background (control) and with the reload, three runs. The target is the sentinel 0xdeadbeef before
# the job; every pixel is read and counted: G triangle 0xff00ff00, B the library's background
# 0xff203040, S sentinel, O any other colour (per 32x16 tile as partial-renders.sh does, at
# 1024x768; at 4096x4096 the probe's colour counts, its four commonest values, are the reading). render_pb_pages is put back at the end. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1116}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
S=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
G=$S/dpm-partial-reload-green__0.bin
W=$(mktemp -d)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
[ -f "$G" ] || { echo "no $G: stage the table's probes"; exit 1; }
echo "## uname"; uname -r
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
PY=$(cat <<'EOF'
import sys
w, h = int(sys.argv[1]), int(sys.argv[2])
G, B, S = "ff00ff00", "ff203040", "deadbeef"
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
	name=$1 pages=$2 w=$3 h=$4 mode=$5
	pb "$pages"
	set --
	[ "$mode" = reload ] && set -- --temps 32 --slot "bgpixel=$S/bg_reload_$w.bin" \
		--slot "bgpds=$S/pds_bg_pos.bin:12"
	echo "== $name: probe --tri pixel ${w}x${h} pb $pages $mode"
	px=
	[ "$w" = 1024 ] && px=--pixels
	sudo -n timeout 300 "$T" probe --tri pixel --width "$w" --height "$h" $px "$@" "$G" > "$W/out" 2>&1
	grep -E "^probe [^ ]+: (failed|tri |o0 )" "$W/out" | cut -c1-200
	[ -n "$px" ] && sed -n 's/^probe [^ ]*: row /row /p' "$W/out" | python3 -c "$PY" "$w" "$h" | cut -c1-200
}
for run in 1 2 3; do
	for mode in control reload; do
		one "1024x768-pb0x422-$mode-r$run" 0x422 1024 768 $mode
		one "1024x768-pb0x23-$mode-r$run" 0x23 1024 768 $mode
		one "4096x4096-pb0x422-$mode-r$run" 0x422 4096 4096 $mode
		one "4096x4096-pb0x100-$mode-r$run" 0x100 4096 4096 $mode
	done
done
pb 0x422
rm -rf "$W"
echo "pb_pages: $(sudo -n cat "$D/render_pb_pages")"
