#!/usr/bin/env python3
"""Q139 round 9 offline step: the three residue dumps of E944 whose slots can be read (256 x 256
m1-B2-10, m1-B2-11 and 640 x 480 m1-B1-23; the baselines from the same attempt give the header
base) against variants of R7-BLK's slot rule and block order where the first macrotile's bound
is not a multiple of 4. In sample (a fit): every variant is scored on the same three rows.
Reads session r8-lgeo's kept files and its gen/score modules by path; writes nothing.
    python3 residue_fit.py [R8LGEO_DIR]"""
import gzip, io, os, re, sys, contextlib

S = sys.argv[1] if len(sys.argv) > 1 else "/Users/jtorra/src/scratch/resgx545/closing8/r8-lgeo"
sys.path.insert(0, S + "/gen"); sys.path.insert(0, S + "/score"); sys.path.insert(0, S + "/kit")
import q139_fit as F  # noqa
import lib_dump as L  # noqa
D = S + "/out/20261113-024441/q139"


def rd(n, ext):
    for p in (f"{D}/{n}{ext}.gz", f"{D}/{n}{ext}"):
        if os.path.exists(p):
            b = gzip.open(p).read() if p.endswith(".gz") else open(p, "rb").read()
            return b
    return None


def args_of(n):
    for line in open(S + "/tables/q139.txt"):
        if line.startswith(n + "|"):
            return line.rstrip("\n").split("|")[-1]


def cdiv(a, b):
    return -(-a // b)


def predict(w, h, args, bcols, key, local_key):
    tx, ty = cdiv(w, 32), cdiv(h, 16)
    m1, m2, s = F.words(w, h, args)
    n, bx, by = F.bounds(m1, m2)
    fx, fy = bx[1], by[1]
    ws = []
    for r in range(max(ty, by[-1] + fy)):
        for c in range(max(tx, bx[-1] + fx)):
            mcol, lx = F.place(c, bx)
            mrow, ly = F.place(r, by)
            nb = bcols(fx)
            sl = (mcol * n + mrow) * s + (ly >> 2) * nb + (lx >> 2) * 16 + ((ly if local_key else r) & 3) * 4 + ((lx if local_key else c) & 3)
            rr, cc = (ly, lx) if local_key else (r, c)
            k = (mcol * n + mrow, rr >> 2, cc >> 2, rr, cc) if key == "mt" else (r >> 2, c >> 2, r, c) if key == "abs" else (mrow, rr >> 2, mcol, cc >> 2, rr, cc)
            ws.append((k, sl, (c, r)))
    ws.sort(key=lambda t: t[0])
    own = {}
    for _, sl, t in ws:
        own[sl] = t
    pred = {(c, r): None for r in range(ty) for c in range(tx)}
    for sl, t in own.items():
        if t in pred:
            pred[t] = sl
    return pred, (n, bx, by, s)


# slots a block row of the first macrotile's width takes: R7-BLK's 16 floor(fx / 4), 16 ceil(fx / 4),
# and 4 fx (a block row is fx tiles of 4 rows: a partial block takes only its own columns' slots)
BCOLS = {"floor": lambda f: 16 * (f >> 2), "ceil": lambda f: 16 * cdiv(f, 4), "row4fx": lambda f: 4 * f,
         "row8half": lambda f: 8 * (f >> 1)}   # 4 rows of fx rounded down to even (fitted on B2-10/11)
KEYS = ("abs", "mt", "mrow")
lay = {}
for n, wh in (("q139-ctl-256x256", (256, 256)), ("q139-ctl-640x480", (640, 480))):
    ok, txt, ly = L.baseline_layout(rd(n, ".tri.tadata.bin"), rd(n, ".tri.param.bin"), *wh)
    print(f"baseline {n}: {ok} {txt}")
    lay[wh] = ly
rows = [("q139-res-256x256-m1-B2-10", (256, 256)), ("q139-res-256x256-m1-B2-11", (256, 256)),
        ("q139-res-640x480-m1-B1-23", (640, 480))]
tot = {}
for n, (w, h) in rows:
    txt = rd(n, ".txt").decode()
    comp, bad = L.image_tiles(txt, w, h)
    obs = L.observed_slots(rd(n, ".tri.tadata.bin"), lay[(w, h)]["base"], w, h)
    a = args_of(n)
    print(f"\n{n}: image complete {comp}, {len(bad)} wrong tiles; args {re.findall(r'ta:[0-9]+=0x[0-9a-f]+', a)}")
    for bc in BCOLS:
        for key in KEYS:
            for lk in (False, True):
                pred, geo = predict(w, h, a, BCOLS[bc], key, lk)
                wr = {t for t, v in pred.items() if v is None}
                ag = sum(1 for t, v in pred.items() if (v is None and not obs.get(t)) or (v is not None and v in obs.get(t, [])))
                ok = wr == bad and ag == len(pred)
                tot.setdefault((bc, key, lk), []).append(ok)
                print(f"  bcols={bc:5s} order={key:4s} localbits={int(lk)}: wrong {len(wr):3d} ({'=' if wr == bad else 'differs'}), slots {ag}/{len(pred)} {'EXACT' if ok else ''}  geo n={geo[0]} bx={geo[1]} by={geo[2]} s={geo[3]}")
print("\nvariant: exact rows of 3")
for k, v in sorted(tot.items(), key=lambda kv: -sum(kv[1])):
    print(f"  bcols={k[0]:5s} order={k[1]:4s} localbits={int(k[2])}: {sum(v)} {v}")
