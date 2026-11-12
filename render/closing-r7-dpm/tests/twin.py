#!/usr/bin/env python3
"""twin.py OUTDIR WORLD: the Python twin of the runner's P resolution against the P column of every kept cases.tsv: r7plan's table rows,
M:G:k:d:0xP the frozen P when the world's steps of G are the model's, else the world's S_k of G + d (a re-pick); uneed rows skipped when
the world's page need of the scene is not HU1's."""
import csv
import pathlib
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "gen"), str(HERE)]
import r7plan as P  # noqa: E402
import world_r7 as W  # noqa: E402

out, world = pathlib.Path(sys.argv[1]), W.World(sys.argv[2] if len(sys.argv) > 2 else "")
bad = n = 0
for st, rows in P.tables().items():
    p = out / st / "cases.tsv"
    if not p.exists():
        continue
    got = {r["name"]: r for r in csv.DictReader(open(p), delimiter="\t")}
    for r in rows:
        n += 1
        f = r["P"].split(":")
        if f[0] == "M":
            if world.shift.get(f[1]):
                wh = P.TARGETS[f[1]]
                S, _, _ = world.scene(dict(w=wh[0], h=wh[1], coords=0))
                want = f"0x{S[int(f[2])] + int(f[3]) + P.D_OFF:x}"
            else:
                want = f[4]
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
