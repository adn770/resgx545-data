"""Score check A (rule_a.py, frozen). Run: python -I score_a.py > score_a.out"""
import gzip, importlib.util, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
D = "/Users/jtorra/src/resgx545-data"
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("rule_a", HERE + "/rule_a.py")
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
sys.path.insert(0, D + "/render/closing-r9-geo/gen")
import addr as A9   # r9-geo gen/addr.py (and its texprog): texel() of the swept-u form
import texprog as T9

ROW = re.compile(r"row (\d+): ([0-9a-fA-Fx ]+)$", re.M)
def pixels(path):
    t = gzip.open(path, "rt", errors="replace").read()
    rows = {int(m.group(1)): [int(v, 16) for v in m.group(2).split()] for m in ROW.finditer(t)}
    px = [v for y in sorted(rows) for v in rows[y]]
    assert len(px) == 2048, (path, len(px))
    return px

def f32(h): return struct.unpack("<f", struct.pack("<I", h))[0]

# ---- tx-border jobs: parse each case's program (resgx545 probes/texture/tx-border.toml)
tb = open("/Users/jtorra/src/resgx545/probes/texture/tx-border.toml").read()
labels = re.search(r"labels = \[(.*?)\]", tb, re.S).group(1)
labels = re.findall(r'"([^"]+)"', labels)
progs = re.findall(r'\["", "(.*?)", "smp2d', tb)
assert len(labels) == len(progs) == 37
FITREAD = {  # earlier reads of the job's offset
 "E565": "read, no offset rule", "E932": "", }
def tx_jobs():
    for name, p in zip(labels, progs):
        mv = dict(re.findall(r"mov r(\d+), #(0x[0-9a-f]+)", p))
        # coordinate consts: fmad r24 = r1 * r2 + r3 (u), fmad r25 = r1 * r2 + r3 (v)
        seq = re.findall(r"mov\.skipinv r2, #(0x[0-9a-f]+)\\?n?mov\.skipinv r3, #(0x[0-9a-f]+)", p.replace("\\n", "\\n"))
        yield name, p, int(mv["20"], 16), int(mv["21"], 16), int(mv["22"], 16)

def tx_coords(p):
    p = p.replace("\\n", "\n") if "\\n" in p else p
    consts = re.findall(r"mov\.skipinv r2, #(0x[0-9a-f]+)\nmov\.skipinv r3, #(0x[0-9a-f]+)", p)
    (ku, cu), (kv, cv) = [(f32(int(a, 16)), f32(int(b, 16))) for a, b in consts]
    return ku, cu, kv, cv

jobs = []
for name, p, t0, t1, t2 in tx_jobs():
    um, vm = (t0 >> 6) & 7, (t0 >> 3) & 7
    if um < 4 or t1 >> 28:
        continue
    w, h = ((t1 >> 12) & 0xfff) + 1, (t1 & 0xfff) + 1
    ku, cu, kv, cv = tx_coords(p)
    base = (t2 - 0x5caf0000) // 4
    px = pixels(f"{D}/texture/p1132/tx-border/{name}.txt.gz")
    st = []
    for y in range(32):
        for x in range(64):
            u = ku * (1 + (x & 63) / 64) + cu
            v = kv * (1 + y / 32) + cv
            # coordinates: (x & 63) << 17 | 1.0 is 1 + x/64; y << 18 | 1.0 is 1 + y/32
            st.append((int((u * w).__floor__()), int((v * h).__floor__()), (px[y * 64 + x] & 0x0FFFFFFF) - base))
    jobs.append((f"p1132/tx-border/{name}", w, h, um, vm, st))

# ---- r8-geo addr and r9-geo addr2 (the swept-u form of r9-geo gen/addr.py; r8's at N = 16)
def sweep_job(path, n, um, vm, kind):
    px = pixels(path)
    st = []
    for y in range(32):
        for x in range(64):
            s, t = A9.texel(n, kind, x, y)
            st.append((s, t, (px[y * 64 + x] & 0x0FFFFFFF) - 12288))
    return st
r8 = D + "/render/closing-r8-geo/out/20261113-015842/addr"
for m in (4, 5, 6, 7):
    jobs.append((f"r8-geo/addr-u{m}", 16, 16, m, 0, sweep_job(f"{r8}/addr-u{m}.txt.gz", 16, m, 0, "u")))
r9 = D + "/render/closing-r9-geo/out/20261113-081038/addr2"
for name, st_, n, um, vm, t3, kind in A9.jobs():
    if um >= 4:
        jobs.append((f"r9-geo/{name}", n, n, um, vm, sweep_job(f"{r9}/{name}.txt.gz", n, um, vm, kind)))

READ_BY = {  # which earlier record read or fitted the job's offset
 "p1132/tx-border/bd-hb-ns-uv4": "E983 (u4 v4, 32 x 8; W fitted)", "p1132/tx-border/bd-hb-ns-uv5": "E983 (mode 5 fit)",
 "p1132/tx-border/bd-hb-ns-uv6": "E983", "p1132/tx-border/bd-hb-ns-uv7": "E983",
}
for j in [j[0] for j in jobs]:
    pass
def reader(name):
    if name in READ_BY: return READ_BY[name]
    if name.startswith("r8-geo"): return "E932 (16 x 16: 180; fits all of H-MAX/H-W/H-H)"
    if name.startswith("r9-geo"): return "E957 (fitted 8N + 52 on squares; same data)"
    return "E565 read, no offset; E957/E932 fit 16 x 16 only"

print("job; WxH; um vm; reader; H-MAX / H-W / H-H pixels equal of scored; pred differ MAX-W, MAX-H; corner C-CONST / C-ROW")
tot = {"disc_W": [], "disc_H": []}
for name, w, h, um, vm, st in jobs:
    eq = {m: 0 for m in ("H-MAX", "H-W", "H-H")}
    sc = 0; diffW = diffH = 0; unscored = 0
    cc = {"C-CONST": 0, "C-ROW": 0}; ncorner = 0
    for s, t, got in st:
        pm = R.predict("H-MAX", w, h, um, vm, s, t)
        if pm is None:
            if um == 5 and not 0 <= s < w and not 0 <= t < h:
                ncorner += 1
                for m in cc: cc[m] += R.corner(m, w, h, s, t) == got
            else:
                unscored += 1
            continue
        sc += 1
        pw, ph = R.predict("H-W", w, h, um, vm, s, t), R.predict("H-H", w, h, um, vm, s, t)
        eq["H-MAX"] += pm == got; eq["H-W"] += pw == got; eq["H-H"] += ph == got
        diffW += pm != pw; diffH += pm != ph
    if diffW: tot["disc_W"].append(name)
    if diffH: tot["disc_H"].append(name)
    c = f"corners {ncorner}: C-CONST {cc['C-CONST']}, C-ROW {cc['C-ROW']}" if ncorner else "-"
    print(f"{name}; {w}x{h}; u{um} v{vm}; {reader(name)}; MAX {eq['H-MAX']} W {eq['H-W']} H {eq['H-H']} of {sc} (unscored {unscored}); differ MAX/W {diffW} MAX/H {diffH}; {c}")
print("jobs that discriminate max from W:", tot["disc_W"])
print("jobs that discriminate max from H:", tot["disc_H"])
