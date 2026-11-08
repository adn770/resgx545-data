# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.24 rerun of store-format.sh that KEEPS the raw dumps of parts A and B (gzip, KEEP dir).
# Q101, Q071: the bits of CR_ISP_ZLSCTL that change what a ZLS store writes. 1024x768 target, a
# depth ramp across the whole target as in store-layout.sh (tri --tri-full --tri-z, run 1 across x,
# run 2 across y), G (bits 11:3) 33 so that no two tiles share an address; the control
# 0x17110c with A) bits 26:24 set to each value 0 to 7; B) bit 19; C) bits 2, 17 and 18 cleared;
# D) bits 26:24 each value with a stencil buffer (tri --stencil, the stencil flag and bases).
# The stored dwords are reduced here (python3) against the format-0 store of the same job. The
# GPU is reset before each case. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1122}
KEEP=${KEEP:-$HOME/zls-dumps-1124/store-format}
mkdir -p "$KEEP"; export KEEP
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
W=$(mktemp -d)
trap 'reset_gpu; rm -rf "$W"' EXIT
cat > "$W/fmt.py" <<'PYEOF'
import array, math, os, struct, subprocess, sys, collections

T, WORK = sys.argv[1], sys.argv[2]
W, H, G = 1024, 768, 33
PAGES = 1000
BASE = 0x17110c


import gzip, hashlib, shutil

def keep(path, name):
    kd = os.environ.get("KEEP")
    if not kd:
        return
    raw = open(path, "rb").read()
    out = os.path.join(kd, name + ".bin.gz")
    with open(out, "wb") as fh:
        with gzip.GzipFile(filename="", mode="wb", fileobj=fh, compresslevel=6, mtime=0) as gz:
            gz.write(raw)
    print("  kept %s: %d bytes raw, %d gz, raw sha256 %s" % (name, len(raw), os.path.getsize(out),
          hashlib.sha256(raw).hexdigest()), flush=True)

def load(p):
    a = array.array("I")
    with open(p, "rb") as fh:
        a.frombytes(fh.read())
    return a

def f32(v):
    return struct.unpack("f", struct.pack("I", v))[0]

def mort(x, y):
    r = 0
    for k, (v, b) in enumerate([(y, 0), (x, 0), (y, 1), (x, 1), (y, 2), (x, 2), (y, 3), (x, 3)]):
        r |= ((v >> b) & 1) << k
    return r | (((x >> 4) & 1) << 8)

def addr32(x, y):
    return 512 * ((y // 16) * (G + 1) + x // 32) + mort(x % 32, y % 16)

def addr16(x, y):                   # 256 dwords a tile, two rows (y even, y odd) in one dword
    lx, ly = x % 32, y % 16
    k = (lx & 1) | (((ly >> 1) & 1) << 1) | (((lx >> 1) & 1) << 2) | (((ly >> 2) & 1) << 3) | \
        (((lx >> 2) & 1) << 4) | (((ly >> 3) & 1) << 5) | (((lx >> 3) & 1) << 6) | \
        (((lx >> 4) & 1) << 7)
    return 256 * ((y // 16) * (G + 1) + x // 32) + k, (ly & 1) * 16

def run(ctl, tag, stencil=False):
    res = {}
    for ax, z in (("x", "0.25,0.75,0.25"), ("y", "0.25,0.25,0.75")):
        d = os.path.join(WORK, tag + ax)
        os.makedirs(d, exist_ok=True)
        cmd = ["sudo", "-n", "timeout", "300", T, "tri", "--width", str(W), "--height", str(H),
               "--tri-full", "--tri-z", z, "--depth", "--depth-ctl", hex(ctl), "--depth-fill",
               "0xdeadbeef", "--depth-dump", d, "--depth-pages", str(PAGES), "--poke",
               "blk:1=0x00400200"]
        if stencil:
            cmd += ["--stencil", "--stencil-fill", "0xdeadbeef"]
        out = subprocess.run(cmd, capture_output=True, text=True,
                             stdin=subprocess.DEVNULL).stdout.split("\n")
        if ax == "x":
            res["lines"] = [l for l in out if l.startswith(("job", "depth #", "stencil #")) or
                            "FAIL" in l]
        res[ax] = load(os.path.join(d, "depth.1.bin"))
        if tag.startswith(("f", "b")):
            keep(os.path.join(d, "depth.1.bin"), "%s-ramp%s" % (tag, ax))
        if stencil:
            res[ax + "s"] = load(os.path.join(d, "stencil.1.bin"))
    return res

def changed(a):
    return [i for i, v in enumerate(a) if v != 0xdeadbeef]

def head(r, key="x", n=6):
    return " ".join("%08x" % r[key][i] for i in range(n))

def line(name, ctl, r):
    ch = changed(r["x"])
    print("%s ctl=0x%08x %s: changed %d, slots of 512 dwords %d, first %s last %s" % (
        name, ctl, " ".join(l for l in r["lines"] if l.startswith("job")), len(ch),
        len({i // 512 for i in ch}), ch[0] if ch else "-", ch[-1] if ch else "-"), flush=True)
    return ch

print("## A bits 26:24 (the stored format), no stencil buffer")
base = run(BASE, "f0")
line("format 0", BASE, base)
Z = {}                              # the hardware's z at each pixel, from the format-0 store
for y in range(H):
    for x in range(W):
        Z[(x, y)] = f32(base["x"][addr32(x, y)])
exact = sum(1 for (x, y), z in Z.items() if abs(z - (0.25 + (x + 0.5) / (6 * W))) < 1e-5)
print("  format 0: the stored dword is the float z of the ramp at %d of %d pixels (1e-5)" % (
    exact, W * H))
for code in range(1, 8):
    ctl = BASE | code << 24
    r = run(ctl, "f%d" % code)
    ch = line("format %d" % code, ctl, r)
    print("  x run first dwords %s | y run %s" % (head(r, "x"), head(r, "y")))
    if code == 1:
        c = collections.Counter()
        for (x, y), z in Z.items():
            c[r["x"][addr32(x, y)] - round(z * 0xffffff)] += 1
        print("  24-bit: stored minus round(z * 0xffffff), by difference: %s" % sorted(c.items()))
        c = collections.Counter()
        for (x, y), z in Z.items():
            c[r["x"][addr32(x, y)] - math.floor(z * 0xffffff)] += 1
        print("  24-bit: stored minus floor(z * 0xffffff), by difference: %s" % sorted(c.items()))
    if code == 2:
        for name, fn in (("round(z * 0xffffff) >> 8", lambda z: round(z * 0xffffff) >> 8),
                         ("floor(z * 65536)", lambda z: math.floor(z * 65536)),
                         ("round(z * 65535)", lambda z: round(z * 65535))):
            c = collections.Counter()
            for (x, y), z in Z.items():
                i, sh = addr16(x, y)
                c[(r["x"][i] >> sh & 0xffff) - fn(z)] += 1
            print("  16-bit (256 dwords a tile, rows y even and odd in the low and high half): "
                  "stored minus %s, by difference: %s" % (name, sorted(c.items())))
print("## B bit 19")
for extra, name in ((0, "bit 19"), (1 << 24, "bit 19, format 1"), (2 << 24, "bit 19, format 2")):
    ctl = BASE | 1 << 19 | extra
    r = run(ctl, "b19_%d" % (extra >> 24))
    ch = line(name, ctl, r)
    cnt = collections.Counter(r["x"][i] for i in ch)
    print("  distinct %d, most frequent %s" % (len(cnt), [("%08x" % k, v) for k, v in
                                                              cnt.most_common(3)]))
print("## C store enables")
for bit in (2, 17, 18):
    ctl = BASE & ~(1 << bit)
    r = run(ctl, "c%d" % bit)
    line("bit %d cleared" % bit, ctl, r)
print("## D bits 26:24 with a stencil buffer (the stencil flag, both stencil bases)")
for code in range(8):
    ctl = BASE | code << 24
    r = run(ctl, "d%d" % code, stencil=True)
    chd = changed(r["x"])
    chs = changed(r["xs"])
    print("format %d ctl=0x%08x %s: depth changed %d (slots of 512 dwords %d), stencil changed "
          "%d (first %s last %s), stencil first dwords %s" % (
              code, ctl, " ".join(l for l in r["lines"] if l.startswith("job")), len(chd),
              len({i // 512 for i in chd}), len(chs), chs[0] if chs else "-",
              chs[-1] if chs else "-", head(r, "xs", 4)), flush=True)
PYEOF
reset_gpu
python3 "$W/fmt.py" "$T" "$W"
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
