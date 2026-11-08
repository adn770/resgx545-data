"""(primitive, tile) pairs and mismatches of H70-T1 and H70-T0 over ta-tri-boundary and ta-tri-corner."""
import sys, collections
sys.path.insert(0, "recompute")
import recompute_p1131 as R
for sc in ("ta-tri-boundary", "ta-tri-corner"):
    d = R.pathlib.Path("data/" + sc)
    tot = collections.Counter(); jobs = 0; onbound = 0
    for c in R.load_cases(d):
        t, p, td = R.load(d, c["name"])
        if R.outcome(t) == "fail" or not p: tot["failed jobs"] += 1; continue
        v = R.geometry(c["args"], c["w"], c["h"]); tris = [v[i:i + 3] for i in range(0, len(v) - 2, 3)]
        obs = R.observed_tiles(p, td, len(tris)); jobs += 1
        for rule in ("T1", "T0"):
            for ty in range(0, c["h"], 16):
                for tx in range(0, c["w"], 16):
                    pred = R.tile_pred(tris, tx, ty, rule); o = obs.get((tx, ty), set())
                    n = len(tris)
                    tot[(rule, "pairs")] += n
                    if "any" in o: bad = 0 if pred else 1
                    else: bad = len(pred ^ {x for x in o if isinstance(x, int)})
                    tot[(rule, "mismatch")] += bad
        # vertices exactly on a 16 px line
        if any((x % 16 == 0) or (y % 16 == 0) for (x, y) in v): onbound += 1
    print(sc, "jobs", jobs, "jobs with a vertex on a 16-pixel line", onbound, {k: v_ for k, v_ in sorted(tot.items(), key=str)})
