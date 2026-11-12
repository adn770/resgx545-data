#!/usr/bin/env python3
"""twin.py OUTDIR WORLD: the Python twin of the runner's P resolution (r5plan's table rows, S:G:k:off read from the WORLD's steps of
G's target, uneed rows skipped when the world's page need of the scene is not HU1's) against the P column of every kept cases.tsv."""
import csv
import pathlib
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "gen"), str(HERE)]
import r5plan as P  # noqa: E402
import world_r5 as W  # noqa: E402

out, world = pathlib.Path(sys.argv[1]), W.World(sys.argv[2])
bad = n = 0
for st, rows in P.tables().items():
    got = {r["name"]: r for r in csv.DictReader(open(out / st / "cases.tsv"), delimiter="\t")}
    for r in rows:
        n += 1
        if r["P"].startswith("S:"):
            _, g, k, off = r["P"].split(":")
            want = f"0x{world.steps(P.TARGETS[g])[int(k)] + int(off) + P.D_OFF:x}"
        else:
            want = r["P"]
        if "uneed:" in r["knobs"]:
            sc = r["knobs"].split("uneed:")[1].split()[0]
            if world.uoff.get(sc):
                want = "-"
        g_ = got.get(r["name"], {}).get("P")
        if g_ != want:
            bad += 1
            print(f"{st} {r['name']}: runner P {g_}, twin {want}")
print(f"{n - bad} of {n} rows equal")
sys.exit(1 if bad else 0)
