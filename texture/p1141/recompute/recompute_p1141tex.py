#!/usr/bin/env python3
"""Recompute the p1141/tex results from the kept dumps, sharing no code with the run scripts.

    ~/src/sgxhumation/.venv/bin/python -B recompute/recompute_p1141tex.py DIR     report on DIR/<script>/
    ~/src/sgxhumation/.venv/bin/python -B recompute/recompute_p1141tex.py --selftest

DIR holds one subdirectory per script (the laptop's ~/p1141tex-dumps/*): cases.tsv, NAME.txt.gz (the tool's whole
output), NAME.FILE.gz (dumps), journal-k.txt.gz. Predictions are re-derived from gen/cases.json with recompute/tex2.py,
msaa_model.py and q140_rescore.py and checked against the frozen sha256 of predictions-declared.tsv. numpy needed.
"""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
import pathlib
import re
import struct
import sys
import tempfile

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
P = HERE.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(P / "gen"))
import msaa_model as M   # noqa: E402
import q140_rescore as Q  # noqa: E402
import tex2             # noqa: E402

BG = 0xFF203040
ROW = re.compile(r"row (\d+): (.*)$")
CASES = {c["name"]: c for c in json.loads((P / "gen/cases.json").read_text())}
PRED = collections.defaultdict(dict)
for ln in (P / "predictions-declared.tsv").read_text().splitlines()[1:]:
    s, c, st, h, sh = ln.split("\t")
    PRED[c][h] = sh


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def read_txt(d, name):
    p = d / f"{name}.txt.gz"
    return gzip.open(p, "rt", errors="replace").read() if p.exists() else None


def rows_of(txt, w=None):
    rows = {}
    for ln in txt.splitlines():
        m = ROW.search(ln)
        if m:
            rows[int(m.group(1))] = [int(v[2:] if v.startswith("0x") else v, 16) for v in m.group(2).split() if re.fullmatch(r"(0x)?[0-9a-fA-F]{1,8}", v)]
    return rows


def failed(txt):
    return txt is None or bool(re.search(r"failed|faulted|hung|FAILED", txt))


# ------------------------------------------------------------------------------------------ fills
def tex_section(root):
    print("== A. texture fills: exact pixels against each frozen hypothesis, per script, set")
    tab = collections.defaultdict(lambda: [0, 0])
    stale = 0
    seen = 0
    for sd in sorted(p for p in root.iterdir() if p.is_dir()):
        for name, c in CASES.items():
            if c["script"] != sd.name or c["kind"] != "probe":
                continue
            txt = read_txt(sd, name)
            if txt is None:
                continue
            seen += 1
            r = rows_of(txt)
            pix = [v for y in sorted(r) for v in r[y]]
            if failed(txt) or len(pix) != 2048:
                print(f"  {name}: no image (failed or {len(pix)} pixels)")
                continue
            if "pred_pixels" in c or c["group"] == "types":
                import cat1141
                ty = int(name[2]); w, h = (int(x) for x in name.split("-")[1].split("x"))
                preds = {k: v for k, v in cat1141.types_pred(ty, w, h).items()}
                for k, px in preds.items():
                    ok = sum(a == b for a, b in zip(px, pix))
                    tab[(c["script"], c["set"], k)][0] += ok == 2048
                    tab[(c["script"], c["set"], k)][1] += 1
                print(f"  {name}: " + "; ".join(f"{k} {sum(a == b for a, b in zip(px, pix))}" for k, px in preds.items()))
                continue
            if not c["hyps"]:
                print(f"  {name}: exploration, {len(set(pix))} distinct values, commonest "
                      f"{collections.Counter(pix).most_common(3)}")
                continue
            for label, rules, opts in c["hyps"]:
                px = tex2.predict(c["spec"], rules, **opts)
                if px is None:
                    continue
                ok = sum(a == b for a, b in zip(px, pix))
                if tex2.tm.digest(px) != PRED[name].get(label):
                    stale += 1
                tab[(c["script"], c["set"], label)][0] += ok == 2048
                tab[(c["script"], c["set"], label)][1] += 1
                if ok != 2048:
                    print(f"  {name:18s} {label:34s} {ok:4d} of 2048")
    for (s, st, h), (a, b) in sorted(tab.items()):
        print(f"  {s:18s} {st:8s} {h:42s} exact {a:2d} of {b:2d}")
    print(f"  fills read {seen}; frozen predictions the model no longer re-renders: {stale}")


# ------------------------------------------------------------------------------------------- msaa
def regs_of(txt):
    return {int(a, 16): int(b, 16) for a, b in re.findall(r"^reg (0x[0-9a-f]+) (0x[0-9a-f]+)", txt, re.M)}


def vis_section(root):
    d = root / "msaa-a-vis"
    if not d.exists():
        return
    print("\n== B. msaa-a-vis: stored image against the region model; visibility count (reg 0x0498)")
    res = {}
    for name, c in CASES.items():
        if c["script"] != "msaa-a-vis":
            continue
        txt = read_txt(d, name)
        if txt is None:
            continue
        r = rows_of(txt)
        obs = {(x, y) for y, row in r.items() for x, v in enumerate(row) if v != BG}
        m = c["meta"]
        tri = [tuple(tuple(q * 16 for q in p) for p in m["tri"])]
        pred = set(M.predict(tri, 64, 64, m["mode"], m["te"]))
        cnt = regs_of(txt).get(0x0498)
        res[name] = (len(obs), len(obs ^ pred), cnt)
        print(f"  {name:22s} {c['set']:8s} stored {len(obs):4d} px, model off by {len(obs ^ pred):4d}, count {cnt}")
    for name, c in CASES.items():
        if c["script"] != "msaa-a-vis" or name not in res or c["meta"].get("last_region", True) or c["set"] == "control":
            continue
        cnt = res[name][2]
        verdict = "no counter read" if cnt is None else ("W (walked: count > 0)" if cnt > 0 else "S (skipped: count = 0)")
        print(f"  DECISION {name}: {verdict}")


def read_bin(d, name):
    p = d / f"{name}.gz"
    return np.frombuffer(gzip.open(p, "rb").read(), dtype="<u4") if p.exists() else None


LANDED = pathlib.Path.home() / "src/resgx545-data/isp/msaa-te-dumps/dumps"


def te29_section(root):
    d = root / "msaa-b-te29"
    if not d.exists():
        return
    print("\n== C. msaa-b-te29: dwords differing from the landed dumps (te 0x00 and the job with bit 29 set)")
    for name, c in CASES.items():
        if c["script"] != "msaa-b-te29":
            continue
        m = c["meta"]
        for f in ("param", "tadata"):
            new = read_bin(d, f"{name}.tri.{f}.bin")
            if new is None:
                print(f"  {name} {f}: no dump")
                continue
            refs = {"te 0x00": 0x00000000, "bit 29 set": m["te"] | 0x20000000 if m["te"] & 0x20000000 == 0 else m["te"],
                    "the job itself, landed": m["te"]}
            for lab, te in refs.items():
                p = LANDED / f"te-m{m['mode']}-{te >> 28:x}0-{m['W']}x{m['H']}.{f}.txt.gz"
                if not p.exists():
                    continue
                old = np.frombuffer(gzip.open(p, "rb").read(), dtype="<u4")
                n = min(len(old), len(new))
                print(f"  {name} {f}: {len(new)} dwords; against {lab} ({p.name}): {int((old[:n] != new[:n]).sum())} differ"
                      + ("" if len(old) == len(new) else f" (sizes {len(old)} vs {len(new)})"))


def q140_section(root):
    d = root / "msaa-c-q140"
    if not d.exists():
        return
    print("\n== D. msaa-c-q140: faulted or completed, fault page from the kernel log")
    jr = d / "journal-k.txt.gz"
    jl = gzip.open(jr, "rt", errors="replace").read().splitlines() if jr.exists() else []
    for name, c in CASES.items():
        if c["script"] != "msaa-c-q140":
            continue
        txt = read_txt(d, name)
        if txt is None:
            continue
        i = next((k for k, ln in enumerate(jl) if f"p1141tex case {name} " in ln), None)
        nxt = next((k for k in range(i + 1, len(jl)) if "p1141tex case" in jl[k]), len(jl)) if i is not None else 0
        pages = re.findall(r"BIF fault 0x[0-9a-f]+ at (0x[0-9a-f]+)", "\n".join(jl[i:nxt])) if i is not None else []
        fl = failed(txt)
        pg = sorted({int(p, 16) >> 12 for p in pages})
        w, h = c["meta"]["W"], c["meta"]["H"]
        pred = {f: Q.predict(w, h, f) for f in (3, 4, 5, 6)}
        ok = [f for f, p in pred.items() if (p is None) != fl and (p is None or (pg and p == (pg[0] & 0xFFFF)))]
        print(f"  {name}: {'FAULTED' if fl else 'completed'}, fault pages {[hex(p) for p in pg]}; factors consistent: {ok}")


# ------------------------------------------------------------------------------------------ depth
def mort(x, y):
    r = 0
    for k, (v, b) in enumerate([(y, 0), (x, 0), (y, 1), (x, 1), (y, 2), (x, 2), (y, 3), (x, 3)]):
        r |= ((v >> b) & 1) << k
    return r | (((x >> 4) & 1) << 8)


def dindex(x, y, g):
    return 512 * ((y // 16) * (g + 1) + x // 32) + mort(x % 32, y % 16)


def guard_section(root):
    d = root / "isp-a-guard"
    if not d.exists():
        return
    print("\n== E. isp-a-guard: stored depth dwords (not 0xdeadbeef) over the tile area against the clip hypotheses")
    for name, c in CASES.items():
        if c["script"] != "isp-a-guard":
            continue
        buf = read_bin(d, f"{name}.depth.1.bin")
        if buf is None:
            continue
        m = c["meta"]
        w, h, g = m["W"], m["H"], m["G"]
        tw, th = (w + 31) // 32, (h + 15) // 16
        area = [(x, y) for y in range(th * 16) for x in range(tw * 32)]
        obs = [p for p in area if dindex(*p, g) < len(buf) and buf[dindex(*p, g)] != 0xDEADBEEF]
        line = []
        for k, v in c["preds"].items():
            line.append(f"{k}: {'MATCH' if sha(obs) == v else 'no'}")
        print(f"  {name:20s} {len(obs):5d} stored of {len(area)}; " + "; ".join(line))


def f32(a):
    return np.asarray(a, dtype=np.uint32).view(np.float32)


def ulp32(a):
    return 2.0 ** (np.floor(np.log2(np.abs(a))) - 23)


def depth_section(root):
    d = root / "isp-b-depth"
    if not d.exists():
        return
    print("\n== F. isp-b-depth: tile-corner value T(i, j) from the stored words, against the frozen candidates")
    tot = collections.defaultdict(lambda: [0, 0, 0])
    from fractions import Fraction
    import tri1141
    for name, c in CASES.items():
        if c["script"] != "isp-b-depth":
            continue
        buf = read_bin(d, f"{name}.depth.1.bin")
        if buf is None:
            continue
        m = c["meta"]
        w, h, g = m["W"], m["H"], m["G"]
        z0, A, B, ox, oy = tri1141.plane_of([tuple(p) for p in m["V"]], m["Z"])
        A, B = float(A), float(B)
        z = f32(np.array([buf[dindex(x, y, g)] if dindex(x, y, g) < len(buf) else 0 for y in range(h) for x in range(w)],
                         dtype=np.uint32)).astype(np.float64).reshape(h, w)
        ys, xs = np.mgrid[0:h, 0:w]
        cands = tri1141.tile_T([tuple(p) for p in m["V"]], m["Z"], w, h) if "planar" not in m else None
        res = {}
        for ty in range(h // 16):
            for tx in range(w // 32):
                zz = z[ty * 16:ty * 16 + 16, tx * 32:tx * 32 + 32].ravel()
                X = xs[ty * 16:ty * 16 + 16, tx * 32:tx * 32 + 32].ravel() + 0.5
                Y = ys[ty * 16:ty * 16 + 16, tx * 32:tx * 32 + 32].ravel() + 0.5
                ok = (zz > 0) & (zz != float(f32([0xDEADBEEF])[0]))
                if ok.sum() < 60:
                    continue
                gx = A * (X[ok] - 32 * tx) + B * (Y[ok] - 16 * ty)
                lo, hi = np.max(zz[ok] - gx), np.min(zz[ok] + ulp32(zz[ok]) - gx)
                res[(tx, ty)] = (lo, hi)
        feas = sum(1 for lo, hi in res.values() if hi >= lo)
        line = [f"{len(res)} tiles, {feas} with a consistent T"]
        for k, v in (cands or tri1141.tile_T([tuple(p) for p in m["planar"][0]], list(m["planar"][1]), w, h)).items():
            hit = 0
            for (tx, ty), (lo, hi) in res.items():
                t = v[ty * (w // 32) + tx]
                hit += lo - 1e-15 <= t <= hi + 1e-15
            line.append(f"{k}: {hit}")
            tot[(m["cls"], k)][0] += hit
            tot[(m["cls"], k)][1] += len(res)
        print(f"  {name:14s} " + "; ".join(line))
    for (cls, k), (a, b, _) in sorted(tot.items()):
        print(f"  class {cls} {k}: {a} of {b} tiles contain the candidate")


# ---------------------------------------------------------------------------------------- selftest
def selftest():
    """Fake kept dumps from the first frozen hypothesis of each case, then the report over them."""
    import cat1141
    import tri1141
    root = pathlib.Path(tempfile.mkdtemp(prefix="p1141tex-selftest-"))

    def gz(p, data):
        with open(p, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=6, mtime=0) as g:
                g.write(data if isinstance(data, bytes) else data.encode())

    for c in CASES.values():
        d = root / c["script"]
        d.mkdir(exist_ok=True)
        nm = c["name"]
        if c["kind"] == "probe":
            if "pred_pixels" in c or c["group"] == "types":
                ty = int(nm[2]); w, h = (int(x) for x in nm.split("-")[1].split("x"))
                px = cat1141.types_pred(ty, w, h)["fixed 16"]
            elif c["hyps"]:
                label, rules, opts = c["hyps"][0]
                px = tex2.predict(c["spec"], rules, **opts)
            else:
                px = [0xA0A1A2A3] * 2048
            gz(d / f"{nm}.txt.gz", "".join(f"probe {nm}: row {y}: " + " ".join(f"{v:08x}" for v in px[y * 64:(y + 1) * 64])
                                           + "\n" for y in range(32)))
            continue
        m = c["meta"]
        out = ""
        if c["script"] == "msaa-a-vis":
            tri = [tuple(tuple(q * 16 for q in p) for p in m["tri"])]
            cov = M.predict(tri, 64, 64, m["mode"], m["te"])
            out = "".join(f"row {y}: " + " ".join(f"{0xFF00FF00 if (x, y) in cov else BG:08x}" for x in range(64)) + "\n"
                          for y in range(64))
            out += "reg 0x0498 0x%08x\n" % (len(cov) if m["te"] == 0x20000000 or m.get("last_region") else 1)
        if c["script"] == "msaa-c-q140":
            f = 4
            if Q.predict(m["W"], m["H"], f) is not None:
                out = "tri: FAILED job faulted\n"
        gz(d / f"{nm}.txt.gz", out or "tri: ok\n")
        if c["script"] == "msaa-b-te29":
            for f in ("param", "tadata"):
                src = LANDED / f"te-m{m['mode']}-{m['te'] >> 28 | 2:x}0-{m['W']}x{m['H']}.{f}.txt.gz"
                if src.exists():
                    gz(d / f"{nm}.tri.{f}.bin.gz", gzip.open(src, "rb").read())
        if c["script"] in ("isp-a-guard", "isp-b-depth"):
            w, h, g = m["W"], m["H"], m["G"]
            buf = np.full(512 * (((h + 15) // 16 - 1) * (g + 1) + (w + 31) // 32 + 1), 0xDEADBEEF, dtype="<u4")
            if c["script"] == "isp-a-guard":
                for y in range(((h + 15) // 16) * 16):
                    for x in range(((w + 31) // 32) * 32):
                        if x + .5 < 1.25 * w and y + .5 < 1.25 * h:
                            buf[dindex(x, y, g)] = 0x3F000000
            else:
                z0, A, B, ox, oy = tri1141.plane_of([tuple(p) for p in m["V"]], m["Z"])
                for ty in range(h // 16):
                    for tx in range(w // 32):
                        T = tri1141.rn32(z0 + A * (32 * tx - ox) + B * (16 * ty - oy))
                        for ly in range(16):
                            for lx in range(32):
                                v = T + float(A) * (lx + .5) + float(B) * (ly + .5)
                                bits_ = struct.unpack("<I", struct.pack("<f", v))[0]
                                if struct.unpack("<f", struct.pack("<I", bits_))[0] > v:
                                    bits_ -= 1          # truncation toward zero
                                buf[dindex(32 * tx + lx, 16 * ty + ly, g)] = bits_
            with open(d / f"{nm}.depth.1.bin.gz", "wb") as raw:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as g_:
                    g_.write(buf.tobytes())
    jl = "".join(f"Nov 09 10:00:00 cedar unknown: resgx545 p1141tex case {n} RUN\n"
                 + ("Nov 09 10:00:01 cedar kernel: [drm] *ERROR* sgxfive: BIF fault 0x90004 at 0x20006061 (PD 0x1) stalls\n"
                    if Q.predict(c["meta"]["W"], c["meta"]["H"], 4) is not None else "")
                 for n, c in CASES.items() if c["script"] == "msaa-c-q140")
    gz(root / "msaa-c-q140" / "journal-k.txt.gz", jl)
    report(root)
    return root


def report(root):
    tex_section(root)
    vis_section(root)
    te29_section(root)
    q140_section(root)
    guard_section(root)
    depth_section(root)
    unknown = [p.name for p in root.iterdir() if p.is_dir() and p.name not in {c["script"] for c in CASES.values()}]
    if unknown:
        print("\ndirectories not in the plan:", unknown)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--selftest"]:
        selftest()
    else:
        report(pathlib.Path(sys.argv[1]))
