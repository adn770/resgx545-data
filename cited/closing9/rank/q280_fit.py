#!/usr/bin/env python3
"""Q280 offline: the log2 of E721's footprint. Declared family (before any fit): the length and its
log2 computed exactly (E721's model), with a piecewise-linear log2 (exponent + mantissa - 1, on the
length or on the squared length halved), with the mantissa cut to k bits before an exact log2, and
with the squares and sum in float32. Fit on E721's 8 gradient jobs (lg-*), the best frozen by hash
(q280_rule.json + .sha256), then scored on E721's 8 ladders (lf-*), which no fit here reads.

    /Users/jtorra/src/resgx545/.venv/bin/python -B q280_fit.py fit|score
"""
import gzip, hashlib, json, math, pathlib, re, struct, sys
DATA = pathlib.Path("/Users/jtorra/src/resgx545-data/texture/p1141")
HERE = pathlib.Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(DATA / "recompute")); sys.path.insert(0, str(DATA / "gen"))
import tex2  # noqa: E402
CASES = {c["name"]: c for c in json.loads((DATA / "gen/cases.json").read_text())}
ROW = re.compile(r"row (\d+): (.*)$")

def hw(name):
    txt = gzip.open(DATA / "out-hw/p1141tex-dumps/tex-a-lod" / f"{name}.txt.gz", "rt").read()
    rows = {}
    for ln in txt.splitlines():
        m = ROW.search(ln)
        if m:
            rows[int(m.group(1))] = [int(v, 16) for v in m.group(2).split() if re.fullmatch(r"(0x)?[0-9a-fA-F]{1,8}", v)]
    return [v for y in sorted(rows) for v in rows[y]]

f32 = lambda x: struct.unpack("<f", struct.pack("<f", x))[0]

def linlog(x):
    m, e = math.frexp(x)          # x = m 2^e, m in [0.5, 1)
    return (e - 1) + (2 * m - 1)

def cutlog(x, k):
    m, e = math.frexp(x)
    m2 = math.floor(2 * m * (1 << k)) / (1 << k)
    return (e - 1) + math.log2(m2)

def make(var):
    def lod(g, lw, lh, rule):
        o0, o1, o2, o3 = g
        if var.startswith("f32"):
            a = f32(f32(f32(o0 * lw) ** 2) + f32(f32(o2 * lh) ** 2)); b = f32(f32(f32(o1 * lw) ** 2) + f32(f32(o3 * lh) ** 2))
        else:
            a = (o0 * lw) ** 2 + (o2 * lh) ** 2; b = (o1 * lw) ** 2 + (o3 * lh) ** 2
        s = max(a, b)
        if s == 0:
            return -math.inf
        kind = var.split(":")[-1]
        if kind == "exact":
            return math.log2(s) / 2
        if kind == "lin":
            return linlog(math.sqrt(s))
        if kind == "linsq":
            return linlog(s) / 2
        if kind.startswith("cutsq"):
            return cutlog(s, int(kind[5:])) / 2
        if kind.startswith("cut"):
            return cutlog(math.sqrt(s), int(kind[3:]))
        raise ValueError(var)
    return lod

FAM = [f"{p}:{k}" for p in ("real", "f32") for k in ["exact", "lin", "linsq"] + [f"cut{k}" for k in range(3, 13)] + [f"cutsq{k}" for k in range(3, 13)]]

def render(name, var):
    c = CASES[name]
    label, rules, opts = c["hyps"][0]
    opts = dict(opts); opts.setdefault("foot", "P")
    old = tex2.pair_lod
    lod = make(var)
    def pl(g, lw, lh, rule):
        return lod(g, lw, lh, rule)
    tex2.pair_lod = pl
    try:
        return tex2.predict(c["spec"], rules, **opts)
    finally:
        tex2.pair_lod = old

def total(names, var, H):
    per = []
    for n in names:
        px = render(n, var)
        per.append(sum(a == b for a, b in zip(px, H[n])))
    return sum(per), per

FIT = [f"lg-{s}{i}" for s in ("sq", "ns") for i in (1, 2, 3, 4)]
HO = ["lf-r2", "lf-r3", "lf-r4", "lf-r6", "lf-r8", "lf-r12", "lf-r16", "lf-r24"]

if __name__ == "__main__":
    if sys.argv[1] == "fit":
        H = {n: hw(n) for n in FIT}
        res = sorted(((total(FIT, v, H), v) for v in FAM), key=lambda t: -t[0][0])
        for (t, per), v in res[:12]:
            print(f"  {t:5d} {per} {v}")
        best = res[0][0][0]; ties = [v for (t, _), v in res if t == best]
        rule = {"question": "Q280", "fit_jobs": FIT, "fit_total": best, "tied": ties, "baseline": "real:exact",
                "heldout": HO, "prediction": "the first tied rule scores at least the baseline on each ladder and its sum exceeds the baseline's"}
        blob = json.dumps(rule, sort_keys=True, indent=1) + "\n"
        (HERE / "q280_rule.json").write_text(blob)
        (HERE / "q280_rule.sha256").write_text(hashlib.sha256(blob.encode()).hexdigest() + "  q280_rule.json\n")
        print("baseline real:exact", [r for r in res if r[1] == "real:exact"][0][0])
        print("frozen", ties, hashlib.sha256(blob.encode()).hexdigest())
    else:
        blob = (HERE / "q280_rule.json").read_text()
        assert hashlib.sha256(blob.encode()).hexdigest() == (HERE / "q280_rule.sha256").read_text().split()[0]
        r = json.loads(blob)
        H = {n: hw(n) for n in HO}
        for v in [r["tied"][0], "real:exact"]:
            print(v, total(HO, v, H))
