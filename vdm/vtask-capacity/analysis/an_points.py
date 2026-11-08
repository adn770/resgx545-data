"""Post hoc: tile membership of each point primitive against a square footprint of side s centred on
the vertex ([v - s/2, v + s/2], the tile half-open on its high sides, closed low), s swept, for the
points jobs of ta-line-point (OUTSEL untouched: no size row read) and ta-risky's ps-outsel-b8 jobs."""
import sys, re, collections
sys.path.insert(0, "recompute")
import recompute_p1131 as R
def tile_hits(vx, vy, s, tx, ty, w=16):
    lo_x, hi_x, lo_y, hi_y = vx - s / 2, vx + s / 2, vy - s / 2, vy + s / 2
    return hi_x >= tx and lo_x < tx + w and hi_y >= ty and lo_y < ty + w
def cases(d, prefix):
    for c in R.load_cases(R.pathlib.Path(d)):
        if c["name"].startswith(prefix):
            yield c
def run(d, prefix, sizes):
    tot = collections.Counter(); n = 0
    for c in cases(d, prefix):
        t, p, td = R.load(R.pathlib.Path(d), c["name"])
        if R.outcome(t) == "fail" or not p: continue
        v = R.geometry(c["args"], c["w"], c["h"])
        m = re.search(r"--vdm 2=0x([0-9a-f]+)", c["args"]); npnt = int(m[1], 16) & 0x3fffff
        obs = R.observed_tiles(p, td, npnt)
        for s in sizes:
            mis = 0
            for ty in range(0, c["h"], 16):
                for tx in range(0, c["w"], 16):
                    pred = {i for i in range(npnt) if tile_hits(v[i][0], v[i][1], s, tx, ty)}
                    o = obs.get((tx, ty), set())
                    if "any" in o: mis += 0 if pred else 1
                    elif pred != o: mis += len(pred ^ o)
            tot[s] += mis
        n += 1
    print(d.split("/")[-1], prefix, n, "jobs:", " ".join("s=%g:%d" % (s, tot[s]) for s in sizes))
run("data/ta-line-point", "pt-", [0, 0.5, 1, 2, 4, 8, 16, 32])

print("--- single-object 3-point jobs, detail")
for c in cases("data/ta-line-point", "pt-"):
    m = re.search(r"--vdm 2=0x([0-9a-f]+)", c["args"]); npnt = int(m[1], 16) & 0x3fffff
    if npnt != 3 or "pt-o" in c["name"] or "-w" in c["name"] and "pt-f" not in c["name"]: continue
    t, p, td = R.load(R.pathlib.Path("data/ta-line-point"), c["name"])
    v = R.geometry(c["args"], c["w"], c["h"])
    obs = R.observed_tiles(p, td, 3)
    print(c["name"], [(round(x, 3), round(y, 3)) for x, y in v], {k: sorted(map(str, s)) for k, s in sorted(obs.items(), key=lambda kv: (kv[0][1], kv[0][0]))})

print("--- 3-point single-object jobs: mismatches per s")
tot = collections.Counter(); jobs = 0
for c in cases("data/ta-line-point", "pt-"):
    m = re.search(r"--vdm 2=0x([0-9a-f]+)", c["args"]); npnt = int(m[1], 16) & 0x3fffff
    if npnt != 3 or "pt-o" in c["name"]: continue
    t, p, td = R.load(R.pathlib.Path("data/ta-line-point"), c["name"])
    v = R.geometry(c["args"], c["w"], c["h"]); obs = R.observed_tiles(p, td, 3); jobs += 1
    for s in (0, 0.25, 0.5, 1, 1.5, 2):
        for ty in range(0, c["h"], 16):
            for tx in range(0, c["w"], 16):
                pred = {i for i in range(3) if tile_hits(v[i][0], v[i][1], s, tx, ty)}
                o = obs.get((tx, ty), set())
                if pred != o and not ("any" in o and pred): tot[s] += len(pred ^ o)
print(jobs, "jobs", dict(tot))
print("--- mismatches at s=1")
for c in cases("data/ta-line-point", "pt-"):
    m = re.search(r"--vdm 2=0x([0-9a-f]+)", c["args"]); npnt = int(m[1], 16) & 0x3fffff
    if npnt != 3 or "pt-o" in c["name"]: continue
    t, p, td = R.load(R.pathlib.Path("data/ta-line-point"), c["name"])
    v = R.geometry(c["args"], c["w"], c["h"]); obs = R.observed_tiles(p, td, 3)
    for ty in range(0, c["h"], 16):
        for tx in range(0, c["w"], 16):
            pred = {i for i in range(3) if tile_hits(v[i][0], v[i][1], 1, tx, ty)}
            o = obs.get((tx, ty), set())
            if pred != o and not ("any" in o and pred): print(c["name"], (tx, ty), "pred", sorted(pred), "obs", sorted(map(str, o)))
