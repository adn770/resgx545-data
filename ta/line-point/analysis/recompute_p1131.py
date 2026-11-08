#!/usr/bin/env python3
"""Recomputation of the 11.31 batch from the kept dumps only. python3 -B recompute_p1131.py DIR
[SCRIPT...] where DIR holds one directory per script (cases.tsv, NAME.txt.gz, NAME.param.bin.gz,
NAME.tadata.bin.gz) and p1131/ holds declared.tsv and predictions-declared.tsv. Shares no code with
the run scripts, the generator or the landed tools: its own decoder of the parameter buffer (3d.md
10.1) and TA data (10.2), its own triangle, line and point geometry from the case arguments.
Prints, per script, the observation of each case, the declared value against the observed one by
set and model, and the counts."""
from __future__ import annotations

import collections
import gzip
import math
import pathlib
import re
import struct
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
BG = 0xff203040
GREEN = 0xff00ff00
BLUE = 0xff0000ff
PAGE = 4096
PB_BASE = 0x1000


def f32(w: int) -> float:
    return struct.unpack("<f", struct.pack("<I", w))[0]


def fbits_arg(s: str) -> float:
    return f32(int(s, 16))


def words(b: bytes, at: int, n: int) -> list[int]:
    n = min(n, (len(b) - at) // 4)
    return list(struct.unpack("<%dI" % n, b[at:at + 4 * n]))


def rd(path: pathlib.Path):
    return gzip.open(path).read() if path.exists() else None


# ------------------------------------------------------------------ decoders
def regions(td: bytes):
    """Region headers of the first written TA data page: (index, x0, y0, flags, stream)."""
    pg = next((i for i in range(len(td) // PAGE) if any(td[i * PAGE:(i + 1) * PAGE])), None)
    if pg is None:
        return []
    ws = words(td, pg * PAGE, 3 * (PAGE // 12))
    out = []
    for i in range(len(ws) // 3):
        w0, w1 = ws[3 * i], ws[3 * i + 1]
        if w0 or w1:
            out.append((i, ((w0 >> 16) & 0xff) * 16, (w0 & 0xfff) * 8, w0 >> 24, w1))
    return out


def stream(param: bytes, addr: int):
    out = []
    for w in words(param, addr - PB_BASE, 32):
        if w == 0xc0000000:
            break
        out.append(w)
    while out and out[-1] == 0:
        out.pop()
    return out


def stream_objects(sw):
    """(prim word, object word, extra dword or None, mask dword or None) per object of one
    region's stream: after the object word one extra dword when the primitive word's bit 21 is set
    (forms 0xa0-0xbf, seen as 0x00000400), then one mask dword in the forms 0x88, 0x8a, 0x8c."""
    out, i = [], 0
    while i + 1 < len(sw):
        t = (sw[i] >> 16) & 0xff
        base = t & ~0x20
        j = i + 2
        extra = None
        if t & 0x20 and j < len(sw):
            extra = sw[j]; j += 1
        mask = None
        if base in (0x88, 0x8a, 0x8c) and j < len(sw):
            mask = sw[j]; j += 1
        out.append((sw[i], sw[i + 1], extra, mask))
        i = j
    return out


def tile_class(tiles: int) -> str:
    return {0x80: "L", 0x8a: "L", 0x98: "R", 0x8c: "R", 0x90: "B"}.get(tiles, "?%02x" % tiles)


def region_map(param: bytes, td: bytes):
    """{(x0, y0): class of the first primitive word} of the regions that have a stream, and the
    first words of each stream."""
    out, first = {}, {}
    for (_i, x0, y0, _fl, st) in regions(td):
        if st:
            sw = stream(param, st)
            if sw:
                out[(x0, y0)] = tile_class((sw[0] >> 16) & 0xff)
                first[(x0, y0)] = sw
    return out, first


def first_object(param: bytes, td: bytes):
    """The first object by 3d.md 10.1, placed by the first stream's object word."""
    for (_i, _x, _y, _f, st) in regions(td):
        if not st:
            continue
        sw = stream(param, st)
        if len(sw) < 2:
            return None
        nv = ((sw[0] >> 25) & 0xf) + 1
        prims = ((sw[1] >> 26) + 1) // 2
        isp_at = (4 * (sw[1] & 0x3ffffff) - PB_BASE) // 4
        ws = words(param, 0, PAGE // 4)
        per, rest = divmod(isp_at - 3, nv)
        plist = (prims + 1) // 2
        tail = isp_at + 2 + plist
        if rest or per < 0 or tail + 6 > len(ws):
            return {"error": "layout isp_at %d nv %d" % (isp_at, nv), "nv": nv, "prims": prims}
        return {"pds": ws[0:3], "per": per, "nv": nv, "prims": prims, "isp": ws[isp_at:isp_at + 2],
                "plist": ws[isp_at + 2:tail], "lw": ws[tail], "fmt": ws[tail + 1],
                "masks": ws[tail + 2:tail + 6], "vertices": [ws[3 + per * v:3 + per * v + per] for v in range(nv)],
                "tail": ws[tail + 6:tail + 6 + 16]}
    return None


def all_objects(param: bytes, td: bytes):
    """Distinct (OBJ_ISP_ADDR, vertices, primitives) over every region stream."""
    seen = {}
    for (_i, _x, _y, _f, st) in regions(td):
        if st:
            for (p, o, _e, _m) in stream_objects(stream(param, st)):
                seen[o & 0x3ffffff] = (((p >> 25) & 0xf) + 1, ((o >> 26) + 1) // 2)
    return seen


# ------------------------------------------------------------------ geometry
NDC = [(-0.75, -0.75), (0.75, -0.375), (-0.375, 0.75)]


def blk_words(args: str):
    return {int(m[1]): m[2] for m in re.finditer(r"--blk (\d+)=(0x[0-9a-f]+)", args)}


def geometry(args: str, w: int, h: int):
    b = blk_words(args)
    if 6 in b:
        ox, sx, oy, sy = (fbits_arg(b[i]) for i in (6, 7, 8, 9))
    else:
        ox, sx, oy, sy = w / 2, w / 2, h / 2, h / 2
    m = re.search(r"--vertices (\d+)", args)
    n = int(m[1]) if m else 3
    v = []
    for k in range(n):
        c, i = divmod(k, 3)
        v.append((ox + sx * (NDC[i][0] + c / (8 * w)), oy + sy * (NDC[i][1] + c / (8 * h))))
    return v


def overlaps(t, x0, y0, x1, y1, bbox_open=False, closed_edge=True):
    bx0, bx1 = min(p[0] for p in t), max(p[0] for p in t)
    by0, by1 = min(p[1] for p in t), max(p[1] for p in t)
    if bx1 < x0 or by1 < y0:
        return False
    if (bx0 >= x1 or by0 >= y1) if bbox_open else (bx0 > x1 or by0 > y1):
        return False
    for i in range(3):
        a, b, c = t[i], t[(i + 1) % 3], t[(i + 2) % 3]
        nx, ny = b[1] - a[1], a[0] - b[0]
        side = nx * (c[0] - a[0]) + ny * (c[1] - a[1])
        vals = [(nx * (x - a[0]) + ny * (y - a[1])) * side for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
        if all(v < 0 for v in vals) if closed_edge else all(v <= 0 for v in vals):
            return False
    return True


def ov_var(t, x0, y0, x1, y1, xhi_open, yhi_open, lo_open=False, edge_open=False):
    bx0, bx1 = min(p[0] for p in t), max(p[0] for p in t)
    by0, by1 = min(p[1] for p in t), max(p[1] for p in t)
    if (bx1 <= x0 if lo_open else bx1 < x0) or (by1 <= y0 if lo_open else by1 < y0):
        return False
    if (bx0 >= x1 if xhi_open else bx0 > x1) or (by0 >= y1 if yhi_open else by0 > y1):
        return False
    for i in range(3):
        a, b, c = t[i], t[(i + 1) % 3], t[(i + 2) % 3]
        nx, ny = b[1] - a[1], a[0] - b[0]
        side = nx * (c[0] - a[0]) + ny * (c[1] - a[1])
        vals = [(nx * (x - a[0]) + ny * (y - a[1])) * side for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
        if all((v <= 0) if edge_open else (v < 0) for v in vals):
            return False
    return True


def tri_regions(verts, w, h, rule):
    """T1: every 16 x 16 tile is half-open on its high sides (bbox), closed on the low sides and in
    the edge test; T0: the landed record's (left tile half-open in x only, the right tile closed)."""
    tris = [verts[i:i + 3] for i in range(0, len(verts) - 2, 3)]
    out = {}
    for y0 in range(0, h, 16):
        for x0 in range(0, w, 32):
            if rule == "T1":
                lf = any(ov_var(t, x0, y0, x0 + 16, y0 + 16, True, True) for t in tris)
                rt = any(ov_var(t, x0 + 16, y0, x0 + 32, y0 + 16, True, True) for t in tris)
            else:
                lf = any(ov_var(t, x0, y0, x0 + 16, y0 + 16, True, False) for t in tris)
                rt = any(ov_var(t, x0 + 16, y0, x0 + 32, y0 + 16, False, False) for t in tris)
            if lf or rt:
                out[(x0, y0)] = "B" if lf and rt else "L" if lf else "R"
    return out


def observed_tiles(par, td, nprims):
    """{(tx, ty): set of primitives, or {"any"} when the form (0x80, 0x90, 0x98) gives no per
    primitive mask} per 16 x 16 tile, from each region's first stream object. Forms 0x88 (both
    tiles) and 0x8a / 0x8c (left / right only) carry the masks in the third dword: low half the
    left tile's, high half the right tile's in 0x88, the low half in 0x8a and 0x8c."""
    obs = collections.defaultdict(set)
    for (_i, x0, y0, _f, st) in regions(td):
        if not st:
            continue
        sw = stream(par, st)
        t = (sw[0] >> 16) & 0xff & ~0x20
        if (sw[0] >> 16) & 0x20 and len(sw) > 2:
            sw = sw[:2] + sw[3:]
        ANY = {"any"}
        low = sw[0] & 0xff
        if t in (0x80, 0x98) and nprims <= 8:
            # one tile: the primitive word's bits 7:0 are that tile's primitive mask (39 of 39
            # single-tile regions of ta-tri-boundary agree with the tile test; bits 15:8 unread)
            m = {q for q in range(nprims) if low >> q & 1}
            L, Rr = (m, set()) if t == 0x80 else (set(), m)
        elif t == 0x90 and nprims <= 8:
            L = Rr = set(range(nprims))
        elif t in (0x80, 0x90, 0x98):
            L = ANY if t in (0x80, 0x90) else set()
            Rr = ANY if t in (0x98, 0x90) else set()
        elif t == 0x88 and len(sw) > 2:
            L = {p for p in range(nprims) if sw[2] & (1 << p)}
            Rr = {p for p in range(nprims) if (sw[2] >> 16) & (1 << p)}
        elif t in (0x8a, 0x8c) and len(sw) > 2:
            m = {p for p in range(nprims) if sw[2] & (1 << p)}
            L, Rr = (m, set()) if t == 0x8a else (set(), m)
        else:
            L = Rr = {"form%02x" % t}
        if L:
            obs[(x0, y0)] |= L
        if Rr:
            obs[(x0 + 16, y0)] |= Rr
    return obs


def tile_pred(tris, tx, ty, rule):
    left = (tx % 32) == 0
    if rule == "T1":
        return {p for p, t in enumerate(tris) if ov_var(t, tx, ty, tx + 16, ty + 16, True, True)}
    if left:
        return {p for p, t in enumerate(tris) if ov_var(t, tx, ty, tx + 16, ty + 16, True, False)}
    return {p for p, t in enumerate(tris) if ov_var(t, tx, ty, tx + 16, ty + 16, False, False)}


def tile_mismatch(obs, tris, w, h, rule):
    """(presence mismatches, per-primitive mismatches where the form has a mask, tiles compared)."""
    pres = prim = n = 0
    for ty in range(0, h, 16):
        for tx in range(0, w, 16):
            pred, o = tile_pred(tris, tx, ty, rule), obs.get((tx, ty), set())
            n += 1
            if bool(pred) != bool(o):
                pres += 1
            elif o and "any" not in o and pred != o:
                prim += len(pred ^ o)
    return pres, prim, n


def seg_hits(a, b, x0, y0, x1, y1):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q < 0:
                return False
        else:
            r = q / p
            if p < 0:
                if r > t1:
                    return False
                t0 = max(t0, r)
            else:
                if r < t0:
                    return False
                t1 = min(t1, r)
    return t0 <= t1


def line_regions(verts, nlines, w, h):
    out = set()
    for y0 in range(0, h, 16):
        for x0 in range(0, w, 32):
            if any(seg_hits(verts[2 * i], verts[2 * i + 1], x0, y0, x0 + 32, y0 + 16) for i in range(nlines)):
                out.add((x0, y0))
    return out


def point_regions(verts, n, w, h):
    return {(int(x // 32) * 32, int(y // 16) * 16) for (x, y) in verts[:n] if 0 <= x < w and 0 <= y < h}


def point_pixels(verts, n, width16, w, h):
    s = width16 / 16.0
    px = set()
    for (x, y) in verts[:n]:
        for i in range(w):
            if abs(i + 0.5 - x) < s / 2:
                for j in range(h):
                    if abs(j + 0.5 - y) < s / 2:
                        px.add((i, j))
    return len(px)


# ------------------------------------------------------------------ tool output
def pixel_counts(txt: str):
    n = collections.Counter()
    pix = {}
    for m in re.finditer(r"row (\d+): ([0-9a-fx ]+)", txt):
        y = int(m[1])
        for x, v in enumerate(m[2].split()):
            v = int(v, 16)
            pix[(x, y)] = v
            n["green" if v == GREEN else "bg" if v == BG else "blue" if v == BLUE else "other"] += 1
    return n, pix


def outcome(txt: str, rc_line: str = "") -> str:
    if re.search(r"failed|faulted|hung|rejected|overflowed", txt):
        return "fail"
    return "ok"


# ------------------------------------------------------------------ cases
def load_cases(d: pathlib.Path):
    out = []
    f = d / "cases.tsv"
    for line in f.read_text().splitlines()[1:]:
        p = line.split("\t")
        if len(p) >= 6:
            out.append(dict(name=p[0], script=p[1], set=p[2], w=int(p[3]), h=int(p[4]), args=p[5]))
    return out


def load_preds():
    pr = collections.defaultdict(dict)
    model = {}
    for fn in ("predictions-declared.tsv", "predictions-followup.tsv", "predictions-followup2.tsv", "predictions-followup3.tsv", "predictions-followup4.tsv", "predictions-followup5.tsv", "predictions-followup6.tsv", "predictions-followup7.tsv", "predictions-followup8.tsv", "predictions-followup9.tsv", "predictions-followup10.tsv"):
        if not (HERE / fn).exists():
            continue
        for line in (HERE / fn).read_text().splitlines()[1:]:
            n, q, v, m = line.split("\t")
            pr[n][q] = v
            model[(n, q, m)] = m
            pr[n]["@" + q + "@" + m] = v
            pr[n].setdefault(q, v)
    return pr, model


class Score:
    def __init__(self):
        self.t = collections.defaultdict(lambda: [0, 0])

    def add(self, model, sset, ok):
        self.t[(model, sset)][0] += 1
        self.t[(model, sset)][1] += 1 if ok else 0

    def show(self):
        for (m, s), (n, k) in sorted(self.t.items()):
            print("  SCORE %-10s %-8s %3d of %3d as declared" % (m, s, k, n))


def load(d, name):
    t = rd(d / (name + ".txt.gz"))
    return (t.decode("utf-8", "replace") if t is not None else None, rd(d / (name + ".param.bin.gz")),
            rd(d / (name + ".tadata.bin.gz")))


def run_fmt(d, preds, model, sc):
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None:
            print("  %-22s NOT KEPT" % c["name"]); continue
        o = first_object(par, td) if par and td else None
        if outcome(txt) == "fail" or not o or "error" in o:
            p = preds[c["name"]]
            for q in ("H70-F", "H70-F", "H70-M"):
                sc.add(q, c["set"], False)
            why = re.search(r"failed: (job [a-z]+)", txt)
            print("  %-22s %-7s job did not complete (%s), declared stored %s: MISS" % (
                c["name"], c["set"], why[1] if why else "no object", p["stored_dwords"])); continue
        stored, it = o["per"], (o["fmt"] >> 8) & 0xff
        masks = ",".join("%x" % m for m in o["masks"])
        p = preds[c["name"]]
        ok = (str(stored) == p["stored_dwords"], str(it) == p["iterated_dwords"], masks == p["masks"])
        for q, k in zip(("H70-F", "H70-F", "H70-M"), ok):
            sc.add(q, c["set"], k)
        print("  %-22s %-7s stored %d (pred %s) iter %d (pred %s) masks %s (pred %s) fmt %08x pds %s %s" % (
            c["name"], c["set"], stored, p["stored_dwords"], it, p["iterated_dwords"], masks, p["masks"],
            o["fmt"], " ".join("%08x" % x for x in o["pds"]), "OK" if all(ok) else "MISS"))


def predicted_regions(s: str):
    out = {}
    for it in filter(None, s.split(";")):
        x, y, v = it.split(":")
        out[(int(x), int(y))] = v
    return out


def run_tri(d, preds, model, sc):
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None:
            print("  %-22s NOT KEPT" % c["name"]); continue
        if outcome(txt) == "fail" or not par:
            print("  %-22s %s FAILED/no dump" % (c["name"], c["set"])); continue
        v = geometry(c["args"], c["w"], c["h"])
        tris = [v[i:i + 3] for i in range(0, len(v) - 2, 3)]
        obs = observed_tiles(par, td, len(tris))
        pdecl = predicted_regions(preds[c["name"]]["regions"])
        # observed region classes from the tiles
        cls = {}
        for (tx, ty) in obs:
            k = (tx - tx % 32, ty)
            cls.setdefault(k, set()).add("L" if tx % 32 == 0 else "R")
        cls = {k: ("B" if len(s_) == 2 else next(iter(s_))) for k, s_ in cls.items()}
        res = {r: tile_mismatch(obs, tris, c["w"], c["h"], r) for r in ("T1", "T0")}
        okd = cls == pdecl
        sc.add("H70-T1", c["set"], okd)
        sc.add("H70-T1-tiles", c["set"], res["T1"][0] == 0 and res["T1"][1] == 0)
        sc.add("H70-T0-tiles", c["set"], res["T0"][0] == 0 and res["T0"][1] == 0)
        unk = sorted({x for s_ in obs.values() for x in s_ if isinstance(x, str) and x.startswith("form")})
        print("  %-24s %-7s regions %d, declared string %s, T1 tiles (presence, prim mismatches) %s, T0 %s %s" % (
            c["name"], c["set"], len(cls), "OK" if okd else "MISS", res["T1"][:2], res["T0"][:2], unk or ""))


def run_lp(d, preds, model, sc):
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None:
            print("  %-22s NOT KEPT" % c["name"]); continue
        fail = outcome(txt) == "fail"
        has = bool(par and td and regions(td) and any(r[4] for r in regions(td)))
        obs, first = region_map(par, td) if has else ({}, {})
        n, _pix = pixel_counts(txt)
        v = geometry(c["args"], c["w"], c["h"])
        nv = len(v)
        m = re.search(r"--vdm 2=0x([0-9a-f]+)", c["args"])
        idx = int(m[1], 16) & 0x3fffff if m else 3
        topo = (int(m[1], 16) >> 26) & 0xf if m else 0
        keys = set(obs)
        if c["name"].startswith("ln"):
            exp = line_regions(v, idx // 2, c["w"], c["h"])
            model_n = "H70-L2"
        else:
            exp = point_regions(v, idx, c["w"], c["h"])
            model_n = "H70-P0"
        extra = {k for k in keys if k not in exp}
        miss = {k for k in exp if k not in keys}
        okk = (not fail) and has and not extra and not miss
        sc.add(model_n, c["set"], okk)
        forms = collections.Counter("%02x" % ((s[0] >> 16) & 0xff) for s in first.values())
        pp = preds[c["name"]].get("pixels")
        pxs = ""
        if pp is not None:
            nonbg = n["green"] + n["other"] + n["blue"]
            pxs = " pixels non-bg %d (H117-W predicts %s)" % (nonbg, pp)
            sc.add("H117-W", c["set"], str(nonbg) == pp)
        print("  %-18s %-7s topo %d %s object %s regions %d (exp %d, extra %d, missing %d) forms %s%s" % (
            c["name"], c["set"], topo, "FAIL" if fail else "ok", has, len(keys), len(exp), len(extra), len(miss),
            dict(forms), pxs))


def run_vtask(d, preds, model, sc):
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None:
            print("  %-22s NOT KEPT" % c["name"]); continue
        fail = outcome(txt) == "fail"
        objs = all_objects(par, td) if par and td else {}
        found = sum(p for (_v, p) in objs.values()) * 3 if False else None
        # vertices that reach distinct objects: primitives over the distinct object words
        verts = sorted((a, nv) for a, (nv, _p) in objs.items())
        total = sum(nv for _a, nv in verts)
        # the last object is the 6-vertex second-object/background pair the tool adds: not counted
        print("  %-14s %-8s %s objects %d vertex counts %s sum %d (declared ids %s)" % (
            c["name"], c["set"], "FAIL" if fail else "ok", len(objs), [nv for _a, nv in verts], total,
            preds[c["name"]].get("ids_found")))
        if not fail and "ids_found" in preds[c["name"]]:
            sc.add("H94-none", c["set"], total == int(preds[c["name"]]["ids_found"]))


def run_q92(d, preds, model, sc):
    ctl = None
    rows = []
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None:
            print("  %-22s NOT KEPT" % c["name"]); continue
        fail = outcome(txt) == "fail"
        o = first_object(par, td) if par and td else None
        key = None if not o or "error" in o else (tuple(o["pds"]), tuple(o["vertices"][0]), o["fmt"], tuple(o["plist"]))
        if c["set"] == "control":
            ctl = key
        rows.append((c, fail, key))
    for c, fail, key in rows:
        eq = (key == ctl) and not fail
        sc.add("H92-none", c["set"], eq)
        print("  %-18s %-8s %s object equals control: %s" % (c["name"], c["set"], "FAIL" if fail else "ok", eq))


def marks(c, txt, par, td):
    n, pix = pixel_counts(txt)
    g = [x for (x, y), v in pix.items() if v == GREEN]
    b = [x for (x, y), v in pix.items() if v == BLUE]
    isp = {"20f0": 0, "10f0": 0}
    if par:
        for w in words(par, 0, 1024):
            if (w & 0xffff) == 0x20f0:
                isp["20f0"] += 1
            if (w & 0xffff) == 0x10f0:
                isp["10f0"] += 1
    return dict(green=len(g), blue=len(b), gx0=min(g) if g else None, bx0=min(b) if b else None, isp=isp)


def run_state(d, preds, model, sc):
    ctl = {}
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None:
            print("  %-26s NOT KEPT" % c["name"]); continue
        fail = outcome(txt) == "fail"
        m = marks(c, txt, par, td) if not fail else {}
        blk = 2 if "-b2-" in c["name"] else 1
        if c["set"] == "control" and not fail:
            ctl[blk] = m
        print("  %-26s %-8s %s %s" % (c["name"], c["set"], "FAIL" if fail else "ok", m))
    # scored: P (all marks as in the control), A (marked object absent), H (hang)
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None or "markers" not in preds.get(c["name"], {}):
            continue
        blk = 2 if "-b2-" in c["name"] else 1
        fail = outcome(txt) == "fail"
        if fail:
            obs = "H"
        else:
            m = marks(c, txt, par, td)
            cm = ctl.get(blk, {})
            # object 1 blue, object 2 green; the marked object's colour count against the control
            col = "green" if blk == 2 else "blue"
            if cm and m[col] == 0:
                obs = "AAA"
            elif cm and (m[col], m["gx0"] if blk == 2 else m["bx0"]) == (cm[col], cm["gx0"] if blk == 2 else cm["bx0"]) \
                    and m["isp"] == cm["isp"]:
                obs = "PPP"
            else:
                obs = "MIX"
        exp = preds[c["name"]]["markers"]
        ok = obs == exp or (exp in ("H", "?") and obs in ("H",)) if exp != "?" else None
        if ok is not None:
            sc.add("H47-N+17", c["set"], ok)
        print("  SCORE-CASE %-26s %-8s observed %s declared %s" % (c["name"], c["set"], obs, exp))


def run_grid(d, preds, model, sc):
    """vdm-state-grid: completes yes / no against H47-G1, H47-G2, H47-N (and the marks of the completed jobs)."""
    ctl_t = load(pathlib.Path(str(d).replace("vdm-state-grid", "vdm-state-units")), "st-b2-ctl-r1")
    ctl = marks(None, *ctl_t)
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None:
            print("  %-12s NOT KEPT" % c["name"]); continue
        fail = outcome(txt) == "fail"
        res = "H" if fail else ("PPP" if (lambda m: (m["green"], m["gx0"]) == (ctl["green"], ctl["gx0"]) and m["isp"] == ctl["isp"])(marks(c, txt, par, td)) else "other")
        line = []
        for m in ("H47-G1", "H47-G2", "H47-N"):
            k = "@completes@" + m
            if k in preds[c["name"]]:
                ok = (preds[c["name"]][k] == "yes") == (not fail)
                sc.add(m, c["set"], ok)
                line.append("%s declared completes=%s %s" % (m, preds[c["name"]][k], "OK" if ok else "MISS"))
        print("  %-12s %-6s %s" % (c["name"], res, "; ".join(line)))


def run_risky(d, preds, model, sc):
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None:
            print("  %-22s NOT KEPT" % c["name"]); continue
        fail = outcome(txt) == "fail"
        o = first_object(par, td) if par and td and not fail else None
        fm = "%08x" % o["fmt"] if o and "fmt" in o else None
        why = re.search(r"failed: (job [a-z]+)", txt)
        n, _ = pixel_counts(txt)
        p = preds[c["name"]]
        ex = ""
        if "format_word" in p:
            ex = "format %s declared %s" % (fm, p["format_word"])
            sc.add("H70-O", c["set"], fm == p["format_word"].replace("0x", ""))
        print("  %-22s %-8s %s %s non-bg %d" % (c["name"], c["set"], ("FAIL " + (why[1] if why else "")) if fail else "ok", ex,
                                                n["green"] + n["other"] + n["blue"]))
    # psize jobs: pixels equal for sizes 1 and 8
    by = collections.defaultdict(dict)
    for c in load_cases(d):
        if c["name"].startswith("ps-"):
            txt, _p, _t = load(d, c["name"])
            if txt:
                n, _ = pixel_counts(txt)
                by[c["name"][:-3] if c["name"][-3] == "-" else c["name"].rsplit("-s", 1)[0]][c["name"].rsplit("-s", 1)[1]] = (
                    n["green"], n["other"], n["bg"])
    for k, v in sorted(by.items()):
        print("  psize %-20s sizes %s -> %s equal %s" % (k, sorted(v), v, len(set(v.values())) == 1))
        sc.add("H117-O0", "heldout", len(set(v.values())) == 1)


HANDLERS = {"ta-object-format": run_fmt, "ta-tri-boundary": run_tri, "ta-line-point": run_lp,
            "vdm-vtask": run_vtask, "vdm-vtask-risky": run_q92, "vdm-state-units": run_state,
            "vdm-state-risky": run_state, "vdm-state-grid": run_grid, "ta-risky": run_risky}


def run_fmt2(d, preds, model, sc):
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None:
            print("  %-16s NOT KEPT" % c["name"]); continue
        o = first_object(par, td) if par and td else None
        p = preds[c["name"]]
        if outcome(txt) == "fail" or not o or "error" in o:
            why = re.search(r"failed: (job [a-z]+)", txt)
            sc.add("H70-F2", c["set"], False)
            print("  %-16s job did not complete (%s), declared stored %s: MISS" % (c["name"], why[1] if why else "no object", p["stored_dwords"])); continue
        stored, it = o["per"], (o["fmt"] >> 8) & 0xff
        ok = str(stored) == p["stored_dwords"] and str(it) == p["iterated_dwords"]
        sc.add("H70-F2", c["set"], ok)
        m = re.search(r"--blk 16=(\d+) --blk 17=(\d+)", c["args"])
        cs_, cf_ = int(m[1]), int(m[2])
        nset = max([1] + [i + 1 for i in range(8) if (cs_ >> (3 * i)) & 7 or (cf_ >> i) & 1])
        mk = [0, 0, 0, 0]
        for i in range(nset):
            sz, bit = (cs_ >> (3 * i)) & 7, 1 << (i + 1)
            if (cf_ >> i) & 1:
                mk[0] |= bit
            if sz == 1:
                mk[1] |= bit
            if sz in (3, 5):
                mk[2] |= bit
            if sz in (4, 5):
                mk[3] |= bit
        sc.add("H70-M", c["set"], mk == list(o["masks"]))
        print("  %-16s stored %d (declared %s) iterated %d (declared %s) masks %s fmt %08x %s" % (
            c["name"], stored, p["stored_dwords"], it, p["iterated_dwords"], ",".join("%x" % m for m in o["masks"]), o["fmt"], "OK" if ok else "MISS"))


def run_vtask2(d, preds, model, sc):
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None:
            print("  %-12s NOT KEPT" % c["name"]); continue
        fail = outcome(txt) == "fail"
        objs = all_objects(par, td) if par and td else {}
        verts = sorted((a, nv) for a, (nv, _p) in objs.items())
        total = sum(nv for _a, nv in verts)
        allr = (not fail) and total == 126
        line = []
        for m in ("H94-MD", "H94-MR", "H94-MR2"):
            if "@vertices_all_reach_objects@" + m not in preds[c["name"]]:
                continue
            v = preds[c["name"]]["@vertices_all_reach_objects@" + m]
            if v != "?":
                ok = (v == "all") == allr
                sc.add(m, c["set"], ok)
                line.append("%s declared %s %s" % (m, v, "OK" if ok else "MISS"))
            else:
                line.append("%s declared ? (exploration)" % m)
        print("  %-12s %s objects %d counts %s sum %d all-reach %s; %s" % (
            c["name"], "FAIL" if fail else "ok", len(objs), [nv for _a, nv in verts], total, allr, "; ".join(line)))


def run_corner(d, preds, model, sc):
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None:
            print("  %-10s NOT KEPT" % c["name"]); continue
        if outcome(txt) == "fail" or not par:
            sc.add("H70-T1", c["set"], False)
            print("  %-10s FAILED/no dump" % c["name"]); continue
        v = geometry(c["args"], c["w"], c["h"])
        tris = [v[i:i + 3] for i in range(0, len(v) - 2, 3)]
        obs = observed_tiles(par, td, len(tris))
        decl = {}
        for it in preds[c["name"]]["tile_prims"].split(";"):
            x, y, ps = it.split(":")
            decl[(int(x), int(y))] = set(int(ch) for ch in ps)
        bad = []
        for ty in range(0, c["h"], 16):
            for tx in range(0, c["w"], 16):
                dset, o = decl.get((tx, ty), set()), obs.get((tx, ty), set())
                if "any" in o:
                    if not dset:
                        bad.append((tx, ty, sorted(dset), "any"))
                elif dset != o:
                    bad.append((tx, ty, sorted(dset), sorted(o, key=str)))
        sc.add("H70-T1", c["set"], not bad)
        print("  %-10s tiles with prims %d, mismatches vs declared %d %s" % (c["name"], len(obs), len(bad), bad[:4]))


HANDLERS.update({"ta-object-format2": run_fmt2, "vdm-vtask2": run_vtask2, "vdm-vtask3": run_vtask2, "ta-tri-corner": run_corner})


def covered_set(verts, size, w, h):
    s = int(size * 16) / 16.0
    out = set()
    for (x, y) in verts:
        for i in range(w):
            if x - s / 2 <= i + 0.5 < x + s / 2:
                for j in range(h):
                    if y - s / 2 <= j + 0.5 < y + s / 2:
                        out.add((i, j))
    return out


def run_points(d, preds, model, sc):
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None:
            print("  %-14s NOT KEPT" % c["name"]); continue
        fail = outcome(txt) == "fail"
        m = re.match(r"pp2?-[ckf]-(?:s)?(-?[0-9.]+)", c["name"])
        size = float(m[1]) if m else None
        p = preds[c["name"]]
        n, pix = pixel_counts(txt) if not fail else (collections.Counter(), {})
        on = {k for k, v in pix.items() if v != BG}
        v = geometry(c["args"], c["w"], c["h"])
        exp = covered_set(v, size, c["w"], c["h"]) if size is not None else set()
        model_n = "H117-R" if c["name"].startswith("pp2") else "H117-S1"
        ok_count = (not fail) and str(len(on)) == p.get("pixels")
        ok_set = (not fail) and on == exp
        sc.add(model_n, c["set"], ok_count)
        extra = ""
        if on and not ok_set:
            extra = " box x %d-%d y %d-%d" % (min(x for x, y in on), max(x for x, y in on), min(y for x, y in on), max(y for x, y in on))
        tile = ""
        if "tile_prims" in p and not fail and par:
            obs = observed_tiles(par, td, 3)
            decl = {}
            for it in filter(None, p["tile_prims"].split(";")):
                x, y, ps = it.split(":")
                decl[(int(x), int(y))] = set(int(ch) for ch in ps)
            bad = []
            for ty in range(0, c["h"], 16):
                for tx in range(0, c["w"], 16):
                    ds, o = decl.get((tx, ty), set()), obs.get((tx, ty), set())
                    if "any" in o:
                        if not ds: bad.append((tx, ty))
                    elif ds != {x for x in o if isinstance(x, int)} and not (o and not ds and False):
                        bad.append((tx, ty, sorted(ds), sorted(map(str, o))))
            sc.add("H70-P1", c["set"], not bad)
            tile = " tiles %s" % ("OK" if not bad else "MISMATCH %d %s" % (len(bad), bad[:2]))
        print("  %-14s %s size %s pixels %d (declared %s) set==model %s%s%s" % (
            c["name"], "FAIL" if fail else "ok", size, len(on), p.get("pixels"), ok_set, extra, tile))


def seg_dist(a, b, x0, y0, x1, y1):
    best = 1e9
    for i in range(4001):
        t = i / 4000
        px, py = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        dx = max(x0 - px, 0, px - x1)
        dy = max(y0 - py, 0, py - y1)
        best = min(best, math.hypot(dx, dy))
    return best


def run_lb(d, preds, model, sc):
    rows = []
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None:
            print("  %-16s NOT KEPT" % c["name"]); continue
        if outcome(txt) == "fail" or not par:
            print("  %-16s FAILED" % c["name"]); continue
        rm, _ = region_map(par, td)
        v = geometry(c["args"], c["w"], c["h"])
        decl = {}
        for it in filter(None, preds[c["name"]]["regions"].split(";")):
            x, y, f = it.split(":")
            decl[(int(x), int(y))] = f
        bad = []
        for ty in range(0, c["h"], 16):
            for tx in range(0, c["w"], 32):
                f = decl.get((tx, ty))
                got = (tx, ty) in rm
                if f == "?":
                    continue
                if (f == "Y") != got:
                    bad.append((tx, ty, f or "-", "in" if got else "out"))
                rows.append((c["name"], tx, ty, got, seg_dist(v[0], v[1], tx, ty, tx + 32, ty + 16)))
        sc.add("H70-L3", c["set"], not bad)
        print("  %-16s regions %d, mismatches vs declared %d %s" % (c["name"], len(rm), len(bad), bad[:4]))
    if rows:
        lo = max((r[4] for r in rows if r[3]), default=0)
        hi = min((r[4] for r in rows if not r[3]), default=None)
        print("  feasible expansion over the bisect jobs: e >= %.4f (listed) and e < %s (not listed)" % (lo, "%.4f" % hi if hi is not None else "-"))
        near = sorted({round(r[4], 3) for r in rows if 0.25 < r[4] < 2.1})
        print("  distances seen between 0.25 and 2.1: %s" % near[:30])
        print("  listed at each distance:", sorted({(round(r[4], 3), r[3]) for r in rows if 0.25 < r[4] < 2.1})[:40])


HANDLERS.update({"ta-points": run_points, "ta-line-bisect": run_lb})


def run_vtask4(d, preds, model, sc):
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None:
            print("  %-16s NOT KEPT" % c["name"]); continue
        fail = outcome(txt) == "fail"
        objs = all_objects(par, td) if par and td else {}
        got = ",".join(str(nv) for _a, (nv, _p) in sorted(objs.items()))
        want = preds[c["name"]]["object_vertex_counts"]
        model_name = "H94-ATTR" if c["name"].startswith("v5-") else "H94-DET"
        sc.add(model_name, c["set"], (not fail) and got == want)
        print("  %-16s %s counts %s %s" % (c["name"], "FAIL" if fail else "ok", got, "same as the first run" if got == want else "DIFFERENT, first run: " + want))


HANDLERS["vdm-vtask4"] = run_vtask4
HANDLERS["vdm-vtask5"] = run_vtask4


def run_lw(d, preds, model, sc):
    rows = []
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None:
            print("  %-18s NOT KEPT" % c["name"]); continue
        fail = outcome(txt) == "fail"
        if c["name"].startswith("pc-"):
            want = preds[c["name"]]["outcome"]
            n, _ = pixel_counts(txt) if not fail else (collections.Counter(), {})
            got = "hangs" if fail and "hung" in txt else "faults" if fail else "completes, %d pixels" % (n["green"] + n["other"] + n["blue"])
            sc.add("H117-C", c["set"], got == want)
            print("  %-18s %s (declared %s) %s" % (c["name"], got, want, "OK" if got == want else "MISS"))
            continue
        if fail or not par:
            print("  %-18s FAILED" % c["name"]); continue
        rm, _ = region_map(par, td)
        decl = {}
        for it in filter(None, preds[c["name"]]["regions"].split(";")):
            x, y, f = it.split(":")
            decl[(int(x), int(y))] = f
        bad = []
        for ty in range(0, c["h"], 16):
            for tx in range(0, c["w"], 32):
                f = decl.get((tx, ty))
                got = (tx, ty) in rm
                if f == "?":
                    continue
                if (f == "Y") != got:
                    bad.append((tx, ty, f or "-", "in" if got else "out"))
        sc.add("H70-L5", c["set"], not bad)
        print("  %-18s regions %d, mismatches vs declared %d %s" % (c["name"], len(rm), len(bad), bad[:4]))


HANDLERS["ta-line-width"] = run_lw


def run_pv(d, preds, model, sc):
    for c in load_cases(d):
        txt, par, td = load(d, c["name"])
        if txt is None:
            print("  %-10s NOT KEPT" % c["name"]); continue
        fail = outcome(txt) == "fail"
        p = preds[c["name"]]
        sizes = [float(x) for x in p["sizes"].split(",")]
        v = geometry(c["args"], c["w"], c["h"])
        n, pix = pixel_counts(txt) if not fail else (collections.Counter(), {})
        on = {k for k, val in pix.items() if val != BG}
        exp = set()
        for (x, y), s in zip(v, sizes):
            exp |= covered_set([(x, y)], s, c["w"], c["h"])
        ok = (not fail) and on == exp and str(len(on)) == p["pixels"]
        sc.add("H117-V", c["set"], ok)
        # what the same pixels would be with one size for every point (the smallest, the largest)
        alt = {sz: len(covered_set(v, sz, c["w"], c["h"])) for sz in sorted(set(sizes))}
        print("  %-10s %s sizes %s pixels %d (declared %s) set==per-vertex model %s; one size for all would give %s" % (
            c["name"], "FAIL" if fail else "ok", p["sizes"], len(on), p["pixels"], on == exp, alt))


HANDLERS["ta-points-vertex"] = run_pv


def main(argv):
    root = pathlib.Path(argv[1])
    preds, model = load_preds()
    sc = Score()
    names = argv[2:] or sorted(HANDLERS)
    for s in names:
        d = root / s
        if not (d / "cases.tsv").exists() or s not in HANDLERS:
            print("== %s: no data" % s); continue
        print("== %s (%d cases)" % (s, len(load_cases(d))))
        HANDLERS[s](d, preds, model, sc)
    sc.show()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
