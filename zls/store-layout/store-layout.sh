# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q107, Q101: where the ZLS store of a render puts each tile's depth. tri --tri-full --tri-z draws
# a triangle over the whole target whose depth ramps across x (run 1) or across y (run 2), so that
# every stored dword says which pixel it holds; --depth-fill 0xdeadbeef marks the dwords a store
# never touches; --depth-dump keeps the buffer. A) CR_ISP_ZLSCTL 0x17100c with its bits 11:3
# (G) replaced, on targets of many sizes: each stored dword is checked against
# 512 * (tile_y * (G + 1) + tile_x) + the in-tile order; B) the same with a parameter buffer
# that overflows (--keep-overflow, render_pb_pages). The reduction is done here (python3). The
# GPU is reset before each case; render_pb_pages is put back at the end. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1122}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.22) for the laptop first"; exit 1; }
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
cat > "$W/red.py" <<'PYEOF'
import array, struct, subprocess, sys, os

def load(p):
    a = array.array("I")
    with open(p, "rb") as fh:
        a.frombytes(fh.read())
    return a

def f32(v):
    return struct.unpack("f", struct.pack("I", v))[0]

def mort(x, y):                     # in-tile order of a 32 x 16 tile: y0 x0 y1 x1 y2 x2 y3 x3 x4
    r = 0
    for k, (v, b) in enumerate([(y, 0), (x, 0), (y, 1), (x, 1), (y, 2), (x, 2), (y, 3), (x, 3)]):
        r |= ((v >> b) & 1) << k
    return r | (((x >> 4) & 1) << 8)

def predict(x, y, g):
    return 512 * ((y // 16) * (g + 1) + x // 32) + mort(x % 32, y % 16)

def tool(tool_path, w, h, ctl, z, dump, pages, extra):
    cmd = ["sudo", "-n", "timeout", "300", tool_path, "tri", "--keep-overflow", "--wait-ms", "20000",
           "--width", str(w), "--height", str(h), "--tri-full", "--tri-z", z, "--depth",
           "--depth-ctl", hex(ctl), "--depth-fill", "0xdeadbeef", "--depth-dump", dump,
           "--depth-pages", str(pages), "--poke", "blk:1=0x00400200"] + extra
    out = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout
    return [l for l in out.split("\n") if l.startswith(("job", "depth #", "tri:")) and "us" not in l[-4:]]

def case(tool_path, work, name, w, h, g, pb=None, base=0x17100c):
    ctl = (base & ~(0x1ff << 3)) | (g << 3)
    tw, th = (w + 31) // 32, (h + 15) // 16
    tiles = (th - 1) * (g + 1) + tw
    pages = max((w * h * 4 + 4095) // 4096, tiles // 2) + 16
    ramps = {}
    jobs = None
    for ax, z in (("x", "0.25,0.75,0.25"), ("y", "0.25,0.25,0.75")):
        d = os.path.join(work, ax)
        os.makedirs(d, exist_ok=True)
        lines = tool(tool_path, w, h, ctl, z, d, pages, [])
        if ax == "x":
            jobs = [l for l in lines if l.startswith("job")]
        ramps[ax] = load(os.path.join(d, "depth.1.bin"))
        os.remove(os.path.join(d, "depth.1.bin"))
    return ctl, jobs, ramps["x"], ramps["y"], tw, th, tiles

def report(name, w, h, g, ctl, jobs, xa, ya, tw, th, tiles, signed=False):
    fill = 0xdeadbeef
    ch = [i for i, v in enumerate(xa) if v != fill]
    bad = outside = n = 0
    slots = set()
    for i in ch:
        vx, vy = xa[i], ya[i]
        n += 1
        slots.add(i // 512)
        if vx == 0x3f800000 and vy == 0x3f800000:
            outside += 1               # a pixel outside the target: the background depth 1.0
            continue
        x = (f32(vx) - 0.25) * 6 * w
        y = (f32(vy) - 0.25) * 6 * h
        xi, yi = int(x), int(y)
        if abs(x - xi - 0.5) > 0.05 or abs(y - yi - 0.5) > 0.05 or predict(xi, yi, g) != i:
            bad += 1
    pred = {ty * (g + 1) + tx for ty in range(th) for tx in range(tw)}
    print("%s %dx%d G=%d ctl=0x%08x %s: changed %d, slots %d, predicted slots %d (window %d "
          "dwords), dwords not at the predicted address %d, background outside the target %d, "
          "slot sets equal %s" % (name, w, h, g, ctl, " ".join(jobs), len(ch), len(slots),
                                  len(pred), 512 * tiles, bad, outside, slots == pred), flush=True)
    return ch

def overflow_report(w, h, g, xa, ya, tw, th):
    fill = 0xdeadbeef
    nz = ng = pos = bad = 0
    zero_tiles = neg_tiles = mixed = 0
    rows_zero = set()
    mixed_cols = set()
    for ty in range(th):
        for tx in range(tw):
            base = 512 * (ty * (g + 1) + tx)
            z = 0
            for j in range(512):
                v = xa[base + j]
                if v == 0:
                    z += 1
                elif v != fill:
                    if v >> 31:
                        ng += 1
                    else:
                        pos += 1
                    x = (f32(v & 0x7fffffff) - 0.25) * 6 * w
                    y = (f32(ya[base + j] & 0x7fffffff) - 0.25) * 6 * h
                    xi, yi = int(x), int(y)
                    if abs(x - xi - 0.5) > 0.05 or abs(y - yi - 0.5) > 0.05 or \
                       predict(xi, yi, g) != base + j:
                        bad += 1
            nz += z
            if z == 512:
                zero_tiles += 1
                rows_zero.add(ty)
            elif z == 0:
                neg_tiles += 1
            else:
                mixed += 1
                mixed_cols.add(tx)
    outside = sum(1 for i, v in enumerate(xa) if v != fill and (i // 512) % (g + 1) >= tw)
    print("  overflow window, G=%d: %d dwords zero, %d with the sign bit set, %d positive, %d with "
          "the sign cleared not at the predicted address; tiles all zero %d (tile rows %s), all "
          "non-zero %d, half zero %d (tile columns %s); %d stored dwords in the %d slots a row "
          "has beyond its %d tiles" % (g, nz, ng, pos, bad, zero_tiles,
          "%d-%d" % (min(rows_zero), max(rows_zero)) if rows_zero else "none", neg_tiles, mixed,
          sorted(mixed_cols), outside, g + 1 - tw, tw), flush=True)

def tile_orders(tw, th):
    raster = [(tx, ty) for ty in range(th) for tx in range(tw)]
    first = lambda t: t[0] < 8 and t[1] < 12     # the first macrotile, 8 x 12 tiles
    return {"raster": raster, "raster, first macrotile last":
            [t for t in raster if not first(t)] + [t for t in raster if first(t)]}

def compare(xs33, xs1, tw, th):
    """The aliased job (G = 1) against the no-alias job (G = 33) written in some tile order."""
    obs = {i: v for i, v in enumerate(xs1) if v != 0xdeadbeef}
    for name, order in tile_orders(tw, th).items():
        mem = {}
        for tx, ty in order:
            b33, b1 = 512 * (ty * 34 + tx), 512 * (ty * 2 + tx)
            for j in range(512):
                v = xs33[b33 + j]
                if v != 0xdeadbeef:
                    mem[b1 + j] = v
        diff = sum(1 for i in set(mem) | set(obs) if mem.get(i) != obs.get(i))
        print("  G=1 job against the G=33 job's tiles written in %s order: %d of %d dwords "
              "differ" % (name, diff, len(obs)), flush=True)

if __name__ == "__main__":
    tool_path, work, part = sys.argv[1:4]
    cases = [c.split(",") for c in sys.argv[4:]]
    for name, w, h, g in [(c[0], int(c[1]), int(c[2]), int(c[3])) for c in cases]:
        ctl, jobs, xa, ya, tw, th, tiles = case(tool_path, work, name, w, h, g)
        report(name, w, h, g, ctl, jobs, xa, ya, tw, th, tiles)
PYEOF
cat > "$W/ovf.py" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[1])
from red import *
tool_path, work, w, h = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
res = {}
for g in (33, 1):
    ctl, jobs, xa, ya, tw, th, tiles = case(tool_path, work, "ovf", w, h, g)
    print("overflow %dx%d G=%d ctl=0x%08x %s: changed %d dwords" % (
        w, h, g, ctl, " ".join(jobs), sum(1 for v in xa if v != 0xdeadbeef)), flush=True)
    if g == 33:
        overflow_report(w, h, g, xa, ya, tw, th)
    res[g] = xa
compare(res[33], res[1], tw, th)
PYEOF
run_cases() { # NAME,W,H,G ...
	reset_gpu
	python3 "$W/red.py" "$T" "$W" A "$@"
}
echo "## A fit: 1024x768, G (control bits 11:3) 0, 1, 2, 33"
run_cases fit,1024,768,0 fit,1024,768,1 fit,1024,768,2 fit,1024,768,33
echo "## A held out: sizes and G not used to find the formula"
run_cases ho,1000,600,7 ho,640,480,12 ho,258,130,4 ho,96,48,0 ho,2048,1024,0 ho,2000,2000,9 \
	ho,1536,1010,12 ho,640,480,511 ho,34,18,3 ho,64,64,1 ho,128,64,1 ho,256,256,1
echo "## A the largest target (a parameter buffer of 0x2000 pages holds its scene)"
pb 0x2000
run_cases ho,4096,4096,1 ho,4096,4096,0
pb 0x422
echo "## B overflowing parameter buffer: the same stores"
for p in 0x28 0x23 0x30; do
	echo "== pb $p 1024x768"
	reset_gpu; pb "$p"
	python3 "$W/ovf.py" "$W" "$T" "$W" 1024 768
done
pb 0x422
echo "pb_pages: $(sudo -n cat "$D/render_pb_pages")"
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
