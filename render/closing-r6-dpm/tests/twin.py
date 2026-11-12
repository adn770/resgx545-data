#!/usr/bin/env python3
"""twin.py OUTDIR WORLD: the Python twin of the runner's P resolution against the P column of every kept cases.tsv: r6plan's table
rows, S:G:k:off from the WORLD's steps of G's target, E:G:k:off from the world's burst ends (the world puts its 200 us waits at B_k,
so the frozen timeline rule reads E_k = B_k), M:G:k:off:0xP the frozen P when the world's steps of G are the model's and the E cell
otherwise (a re-pick), uneed rows skipped when the world's page need of the scene is not HU1's, vvoid's r-v cells skipped."""
import csv
import pathlib
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "gen"), str(HERE)]
import r6plan as P  # noqa: E402
import world_r6 as W  # noqa: E402

out, world = pathlib.Path(sys.argv[1]), W.World(sys.argv[2])
VG = {"v4": 4, "v8": 8}


def sb(g):
    if g in VG:
        return world.scene(dict(w=2048, h=2048, coords=VG[g]))[:2]
    w, h = P.TARGETS[g]
    return world.scene(dict(w=w, h=h, coords=0))[:2]


bad = n = 0
for st, rows in P.tables().items():
    p = out / st / "cases.tsv"
    if not p.exists():
        continue
    got = {r["name"]: r for r in csv.DictReader(open(p), delimiter="\t")}
    for r in rows:
        n += 1
        f = r["P"].split(":")
        if f[0] == "S":
            S, B = sb(f[1])
            want = f"0x{S[int(f[2])] + int(f[3]) + P.D_OFF:x}"
        elif f[0] == "E" or (f[0] == "M" and world.shift.get(f[1])):
            S, B = sb(f[1])
            bs = set(B.values())
            def end(k):     # f4_phase.ends on the world's waits
                nxt = S.get(k + 1, 1 << 30)
                return next((T for T in range(S[k] + 2, min(nxt, S[k] + 0x200)) if T in bs), None)
            if f[2].endswith("+"):
                e = next((end(k) for k in sorted(S) if k >= int(f[2][:-1]) and end(k) is not None), None)
            else:
                e = end(int(f[2]))
            want = "-" if (f[1] in VG and world.vvoid) or e is None else f"0x{e + int(f[3]) + P.D_OFF:x}"
        elif f[0] == "M":
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
