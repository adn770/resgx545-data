# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q088, Q071: what a render loads, from CR_ISP_ZLSCTL bits 1, 13 and 14. 256x128 target, G (bits
# 11:3) 33 (control 0x17110c). The load buffers (tri --depth, --stencil) hold a pattern: each
# dword's own index (--depth-fill index), or 0.25f / 0.75f by bit K of the index (bit:K); the
# store buffers (--depth-store, --stencil-store) hold 0xdeadbeef. The triangle covers the target
# at depth 0.5. A) depth test "never" (blk:1 0x00000200): what the stores hold against the
# loaded dwords; B) depth test "less" (0x00400200) with the 0.25f / 0.75f patterns: the triangle
# pixels the loaded depth leaves and the stored depth; C) loaded values with the sign bit set.
# Reduced here (python3). The GPU is reset before each case. Root through sudo -n.
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
W=$(mktemp -d)
trap 'reset_gpu; rm -rf "$W"' EXIT
cat > "$W/ld.py" <<'PYEOF'
import array, collections, os, re, subprocess, sys

T, WORK = sys.argv[1], sys.argv[2]
NEVER, LESS = "0x00000200", "0x00400200"
CASES = [("clear and store", 0x17110c), ("bit 1", 0x17110e), ("bit 13", 0x17310c),
         ("bit 14", 0x17510c), ("bits 13, 14", 0x17710c), ("bits 1, 13", 0x17310e),
         ("bits 1, 14", 0x17510e), ("bits 1, 13, 14", 0x17710e),
         ("load only, bits 1, 13, 14 (0x11710a + 0x6000)", 0x11d10a),
         ("load only, bit 1 (0x11710a)", 0x11710a)]

def load(p):
    a = array.array("I")
    with open(p, "rb") as fh:
        a.frombytes(fh.read())
    return a

def run(ctl, dfill, sfill, blk, tag):
    d = os.path.join(WORK, tag)
    os.makedirs(d, exist_ok=True)
    cmd = ["sudo", "-n", "timeout", "120", T, "tri", "--width", "256", "--height", "128",
           "--tri-full", "--tri-z", "0.5,0.5,0.5", "--depth", "--depth-ctl", hex(ctl),
           "--depth-fill", dfill, "--depth-store", "--depth-store-fill", "0xdeadbeef",
           "--stencil", "--stencil-fill", sfill, "--stencil-store", "--stencil-store-fill",
           "0xdeadbeef", "--depth-pages", "300", "--depth-dump", d, "--poke", "blk:1=" + blk]
    out = subprocess.run(cmd, capture_output=True, text=True,
                         stdin=subprocess.DEVNULL).stdout.split("\n")
    jobs = [l for l in out if l.startswith("job")]
    m = [re.match(r"tri 256x128 #1: (\d+) triangle", l) for l in out]
    tri = [x.group(1) for x in m if x]
    return jobs, tri, load(os.path.join(d, "depth-store.1.bin")), \
        load(os.path.join(d, "stencil-store.1.bin"))

def relation(a, fillkind):
    ch = [i for i, v in enumerate(a) if v != 0xdeadbeef]
    c = collections.Counter()
    for i in ch:
        v = a[i]
        if v == 0:
            c["0 (the clear value of a stencil, or loaded dword 0)"] += 1
        elif fillkind == "index" and v == i:
            c["the loaded dword"] += 1
        elif v == 0x3f800000:
            c["1.0 (the clear value)"] += 1
        else:
            c["other"] += 1
    return len(ch), dict(c)

print("## A copy: load buffers hold each dword's index, depth test never")
for name, ctl in CASES:
    jobs, tri, ds, ss = run(ctl, "index", "index", NEVER, "a")
    print("%s ctl=0x%08x %s: depth store %s | stencil store %s" % (
        name, ctl, " ".join(jobs), relation(ds, "index"), relation(ss, "index")), flush=True)
print("## B depth test less against loaded 0.25f / 0.75f (bit K of the dword index)")
for k in (0, 3, 9):
    for name, ctl in CASES[:1] + CASES[5:8]:
        jobs, tri, ds, ss = run(ctl, "bit:%d" % k, "index", LESS, "b")
        cnt = collections.Counter(v for v in ds if v != 0xdeadbeef)
        print("bit:%d %s ctl=0x%08x %s: triangle pixels %s of 32768, stored depth %s" % (
            k, name, ctl, " ".join(jobs), tri, [("%08x" % v, n) for v, n in cnt.most_common(3)]),
            flush=True)
print("## C loaded depth values with the sign bit set or all bits set, depth test never")
for fill in ("0xbe800000", "0xdeadbeef", "0xffffffff", "0x80000000"):
    for name, ctl in (CASES[7], CASES[0]):
        jobs, tri, ds, ss = run(ctl, fill, "0xdeadbeef", NEVER, "c")
        cnt = collections.Counter(v for v in ds if v != 0xdeadbeef)
        print("load %s %s ctl=0x%08x %s: stored depth %s" % (
            fill, name, ctl, " ".join(jobs), [("%08x" % v, n) for v, n in cnt.most_common(3)]),
            flush=True)
PYEOF
reset_gpu
python3 "$W/ld.py" "$T" "$W"
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
