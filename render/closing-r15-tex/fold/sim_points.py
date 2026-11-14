"""The kept pixels sgx-sim's tests hold (crates/sgx-sim/src/tex.rs, E1052 and E1055), printed as
Rust tuples: chain rows (W, H, format, 1D, T0, LOD, x, kept), each at y = 0, 8, 20, 28 (LOD
(y >> 2) + c) and x = 5, 50 (u = v = (32 x + 17) / 2048, 1/2 on a side of 1), and the type rows in u mode 4
(type, W, u, kept) at y = 0 (the rows are alike), x = 0 to 63 step 7: ty's three 32 x 32 rows and
its n16 row (u = (x - 23.5) / 16) and E1039's type 4 row (r14-tex, resgx545-data cddc7b60b; E567's
`map` u = 1 + (x mod W + 1/2) / W)."""
import subprocess
import gzip, os, re, sys
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import chain as C  # noqa: E402
OUT = os.path.join(KP, "out/20261114-073318")


def px(stage, name):
    t = gzip.open(os.path.join(OUT, stage, name + ".txt.gz"), "rt").read()
    rows = {int(m.group(1)): [int(v, 16) for v in m.group(2).split()]
            for m in re.finditer(r"row (\d+): ([0-9a-f ]+)$", t, re.M)}
    return [v for y in sorted(rows) for v in rows[y]]


print("// chain: (w, h, format, one_d, t0, lod, x, kept)")
for j in C.HELDOUT:
    p = px("chain", j["name"])
    for y in (0, 8, 20, 28):
        lod = C.coord(j["lod"], 0, y)
        for x in (5, 50):
            print(f"({j['w']}, {j['h']}, {j['fmt']}, {str(j['one_d']).lower()}, 0x{j['t0']:08x}, "
                  f"{float(lod)}, {x}, 0x{p[64 * y + x]:08x}),")
print("// ty mode 4: (type, w, u, kept)")
for name, ty, w in (("ty-32-ty1-u4", 1, 32), ("ty-32-ty3-u4", 3, 32), ("ty-32-ty4-u4", 4, 32),
                    ("ty-16-ty1-n16", 1, 16), ("r14:addr5-ty4-u4", 4, 16)):
    if name.startswith("r14:"):
        b = subprocess.run(["git", "-C", os.environ.get("RESGX545_DATA",
                            "/Users/jtorra/src/resgx545-data"), "show", "cddc7b60b:render/"
                            "closing-r14-tex/out/20261114-054258/addr5/" + name[4:] + ".txt.gz"],
                           capture_output=True, check=True).stdout
        t = gzip.decompress(b).decode()
        p = [int(v, 16) for m in re.finditer(r"row (\d+): ([0-9a-f ]+)$", t, re.M)
             for v in m.group(2).split()]
    else:
        p = px("ty", name)
    for x in range(0, 64, 7):
        u = (x - 23.5) / 16 if name.endswith("n16") else 1 + (x % w + 0.5) / w
        print(f"({ty}, {w}, {u}, 0x{p[x]:08x}),")
