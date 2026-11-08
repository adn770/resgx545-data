# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q038: tri --depth (a depth buffer the ZLS pokes point at, filled with a sentinel or 1.0f before
# the render) on the triangle with depth test less (blk:1 = 0x00400200) at z 0.5, 1024x768 with
# 0x422, 0x30, 0x28, 0x24 and 0x23 pages and 4096x4096 with 0x422, 0x100, 0x40 and 0x23, each
# with --keep-overflow; the buffer is dumped (--depth-dump) and reduced here to its distinct
# values with the first and last dword of each, and the count of dwords that left the fill.
# Part B: two renders, the second with the load-only control 0x11700a (--depth-ctl-next) on the
# depth the first stored, in a buffer that holds the scene and in one that overflows. The GPU is
# reset before each case; render_pb_pages is put back at the end. Root through sudo -n.
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
import array, sys
path, fill = sys.argv[1], int(sys.argv[2], 0)
w = array.array("I")
with open(path, "rb") as f:
    w.frombytes(f.read())
first, last, cnt = {}, {}, {}
nchg = 0
fchg = lchg = -1
for i, v in enumerate(w):
    if v in cnt:
        cnt[v] += 1
    else:
        cnt[v] = 1
        first[v] = i
        if len(cnt) > 4096:
            break
    last[v] = i
    if v != fill:
        nchg += 1
        lchg = i
        if fchg < 0:
            fchg = i
print("dwords %d, changed %d, first changed %d, last changed %d, distinct %d%s" % (
    len(w), nchg, fchg, lchg, len(cnt), "+" if len(cnt) > 4096 else ""))
for v, n in sorted(cnt.items(), key=lambda kv: -kv[1])[:12]:
    print("  0x%08x x %d, dwords %d to %d" % (v, n, first[v], last[v]))
PYEOF
)
KEEP="^(job|diff|tri|depth|tri:)|FAILED|failed|renders ok"
case_run() { # NAME PAGES FILL ARGS...
	name=$1 pages=$2 fill=$3; shift 3
	echo "== $name: pb $pages, tri $* --depth --depth-fill $fill"
	reset_gpu
	pb "$pages"
	rm -rf "$W/dump"; mkdir -p "$W/dump"
	n=$(sudo -n dmesg | wc -l)
	sudo -n timeout 300 "$T" tri --keep-overflow --wait-ms 20000 --depth --depth-fill "$fill" \
		--depth-dump "$W/dump" --poke blk:1=0x00400200 "$@" 2>&1 </dev/null |
		grep -E "$KEEP" | grep -v "us$" | cut -c1-200
	for f in "$W"/dump/depth.*.bin; do
		[ -f "$f" ] || continue
		echo "$(basename "$f"):"
		python3 -c "$PY" "$f" "$fill"
	done
	sudo -n dmesg | tail -n +$((n + 1)) | grep -iE "hang|reset|recover|timed out|fault|lost|cancel|overflow|partial" |
		cut -c1-180 | head -6
}
for i in 1 2; do
	for p in 0x422 0x30 0x28 0x24 0x23; do
		case_run "1024x768-pb$p-sentinel-$i" "$p" 0xdeadbeef --width 1024 --height 768
	done
	for p in 0x422 0x28 0x23; do
		case_run "1024x768-pb$p-fill1-$i" "$p" 0x3f800000 --width 1024 --height 768
	done
done
for p in 0x422 0x100 0x40 0x23; do
	case_run "4096x4096-pb$p-sentinel-1" "$p" 0xdeadbeef --width 4096 --height 4096
done
for i in 1 2; do
	for p in 0x422 0x28; do
		case_run "load-1024x768-pb$p-$i" "$p" 0xdeadbeef --width 1024 --height 768 -n 2 \
			--depth-ctl-next 0x11700a
	done
done
pb 0x422
echo "pb_pages: $(sudo -n cat "$D/render_pb_pages")"
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
