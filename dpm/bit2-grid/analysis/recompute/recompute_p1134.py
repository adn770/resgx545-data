#!/usr/bin/env python3
"""Recompute of the 11.34 batch from the kept dumps only: python3 -B recompute_p1134.py DIR SCRIPT...
DIR holds one directory per script (cases.tsv, NAME.txt.gz, ...). Own decoders; shares no code with the run
scripts or the generator. Prints, per script, observed against declared by set and model."""
import collections, gzip, math, pathlib, re, struct, sys
HERE = pathlib.Path(__file__).resolve().parent.parent
BG = 0xff203040

def f32(w): return struct.unpack("<f", struct.pack("<I", w & 0xffffffff))[0]
def rd(p): return gzip.open(p).read() if p.exists() else None

def load_preds():
    out = collections.defaultdict(list)
    for ln in (HERE / "predictions-declared.tsv").read_text().splitlines()[1:]:
        c, q, v, m = ln.split("\t"); out[c].append((q, v, m))
    return out

def load_sets():
    return {l.split("\t")[0]: l.split("\t")[2] for l in (HERE / "declared.tsv").read_text().splitlines()[1:]}

def pixel_rows(txt):
    rows = {}
    for line in txt.decode().splitlines():
        m = re.search(r"row (\d+): (.*)$", line)
        if m: rows[int(m.group(1))] = [int(v, 16) for v in m.group(2).split()]
    return [rows[i] for i in sorted(rows)]

class Score:
    def __init__(self): self.t = collections.defaultdict(lambda: collections.Counter())
    def add(self, model, sset, ok):
        if ok is None: self.t[(model, sset)]["explore"] += 1
        else: self.t[(model, sset)]["ok" if ok else "MISS"] += 1
    def show(self):
        for (m, s), c in sorted(self.t.items()):
            print("  %-8s %-8s scored %d: ok %d miss %d; explore %d" % (m, s, c["ok"] + c["MISS"], c["ok"], c["MISS"], c["explore"]))

# ------------------------------------------------------------------ o23-tiles
def run_o23(d, preds, sets, sc):
    mk = {}
    for ln in (d / "cases.tsv").read_text().splitlines()[1:]:
        pass
    mfile = HERE / "gen/o23-markers.tsv"
    for ln in mfile.read_text().splitlines():
        n, m = ln.split("\t"); mk[n] = int(m)
    configs = sorted({n[:-2] for n in mk})
    print("o23-tiles: %d configs" % len(configs))
    res = {}
    for cfg in configs:
        tx_, ty_ = rd(d / (cfg + "-x.txt.gz")), rd(d / (cfg + "-y.txt.gz"))
        if tx_ is None or ty_ is None:
            print("  %s: missing dump" % cfg); continue
        rx, ry = pixel_rows(tx_), pixel_rows(ty_)
        H, W = len(rx), len(rx[0])
        mx, my = mk[cfg + "-x"], mk[cfg + "-y"]
        tw = math.ceil(W / 32)
        stats = {k: collections.Counter() for k in (2, 3, 4, 5, 6, 7, 8)}
        stale = 0
        offs = {k: collections.Counter() for k in (2, 3, 4, 5, 6, 7, 8)}
        for y in range(H):
            for x in range(W):
                vx, vy = rx[y][x], ry[y][x]
                if vx == BG and vy == BG: continue
                if vx == BG or vy == BG: stats[(vx if vy == BG else vy) & 15 if ((vx if vy == BG else vy) & 15) in stats else 2]["onlyone"] += 1; continue
                kx, ky = vx & 15, vy & 15
                if (vx & 0xffff) >> 4 != mx or (vy & 0xffff) >> 4 != my: stale += 1; continue
                if kx != ky or kx not in stats: continue
                k = kx
                sx = round(f32(vx & 0xffff0000) * W / 2 + W / 2 - 0.5)
                sy = round(f32(vy & 0xffff0000) * H / 2 + H / 2 - 0.5)
                if not (0 <= sx < W and 0 <= sy < H): stats[k]["badsrc"] += 1; continue
                nd = (y // 16) * tw + x // 32
                ns = (sy // 16) * tw + sx // 32
                same = (sx % 32 == x % 32 and sy % 16 == y % 16)
                offs[k][ns - nd] += 1
                stats[k]["pairs"] += 1
                if same and ns == nd + (k - 1): stats[k]["fit"] += 1
                if same and ns == nd: stats[k]["own"] += 1
        res[cfg] = (W, H, stats, offs, stale)
        print("  %-14s %dx%d tiles/row %d stale %d" % (cfg, W, H, tw, stale))
        for k in (2, 3, 4, 5):
            s = stats[k]
            print("     tag %d (o%d): pairs %d  H23-T fit %d  own-place %d  tile offsets %s" % (
                k, k - 1, s["pairs"], s["fit"], s["own"], dict(sorted(offs[k].items(), key=lambda a: -a[1])[:4])))
        for ax in "xy":
            name = "o23-%s-%s" % (cfg[4:], ax)
            sset = sets.get(name, "?")
            for q, v, m in preds.get(name, []):
                if not q.startswith("disp-tag"): continue
                k = int(q[8])
                s = stats[k]
                allfit = s["pairs"] > 0 and s["fit"] == s["pairs"]
                if v == "?": sc.add(m, sset, None)
                elif m == "H23-T": sc.add(m, sset, allfit if v == "all" else (not allfit))
                else: sc.add(m, sset, (not allfit) if v == "not-all" else allfit)
    return res


# ------------------------------------------------------------------ o23-order (follow-up 1)
PAGE = 4096
def regions_with_stream(td):
    """Region headers (3 dwords each) of the first written TA data page: [(index, tile x, tile y)] with a stream."""
    pg = next((i for i in range(len(td) // PAGE) if any(td[i * PAGE:(i + 1) * PAGE])), None)
    if pg is None: return []
    n = PAGE // 12
    ws = struct.unpack("<%dI" % (3 * n), td[pg * PAGE: pg * PAGE + 12 * n])
    out = []
    for i in range(n):
        w0, w1 = ws[3 * i], ws[3 * i + 1]
        if w0 or w1:
            x0, y0 = ((w0 >> 16) & 0xff) * 16, (w0 & 0xfff) * 8
            if w1: out.append((i, x0 // 32, y0 // 16))
    return out

def run_o23order(d, preds, sets, sc):
    mk = {l.split("\t")[0]: int(l.split("\t")[1]) for l in (HERE / "gen/o23d-markers.tsv").read_text().splitlines()}
    cfgs = sorted({n[:-2] for n in mk})
    print("o23-order: %d configs" % len(cfgs))
    summary = {}
    for cfg in cfgs:
        tdb = rd(d / (cfg + "-x.tadata.bin.gz")); tx_, ty_ = rd(d / (cfg + "-x.txt.gz")), rd(d / (cfg + "-y.txt.gz"))
        if tdb is None or tx_ is None or ty_ is None: print("  %s: missing" % cfg); continue
        L = [(x, y) for (_i, x, y) in regions_with_stream(tdb)]
        pos = {t: i for i, t in enumerate(L)}
        rx, ry = pixel_rows(tx_), pixel_rows(ty_)
        H, W = len(rx), len(rx[0]); mx, my = mk[cfg + "-x"], mk[cfg + "-y"]
        line = []
        for k in (2, 3, 4):
            c = collections.Counter()
            for y in range(H):
                for x in range(W):
                    vx, vy = rx[y][x], ry[y][x]
                    if vx == BG or vy == BG or (vx & 15) != k or (vy & 15) != k: continue
                    if (vx & 0xffff) >> 4 != mx or (vy & 0xffff) >> 4 != my: c["stale"] += 1; continue
                    sx = round(f32(vx & 0xffff0000) * W / 2 + W / 2 - 0.5); sy = round(f32(vy & 0xffff0000) * H / 2 + H / 2 - 0.5)
                    if sx % 32 != x % 32 or sy % 16 != y % 16: c["place"] += 1; continue
                    s, dd = (sx // 32, sy // 16), (x // 32, y // 16)
                    if s not in pos: c["src-no-stream"] += 1
                    elif dd not in pos: c["dest-no-stream"] += 1
                    else: c[pos[s] - pos[dd]] += 1
            tot = sum(c.values()); ok = c[k - 1]
            summary[(cfg, k)] = (ok, tot, dict(c))
            line.append("o%d %d/%d at -%d [%s]" % (k - 1, ok, tot, k - 1, " ".join("%s:%d" % kv for kv in sorted(c.items(), key=lambda a: -a[1])[:4])))
        print("  %-16s L=%d  %s" % (cfg, len(L), " | ".join(line)))
        for ax in "xy":
            name = "o23d-%s-%s" % (cfg[5:], ax)
            sset = sets.get(name) or load_sets_f1().get(name, "?")
            for q, v, m in load_preds_f1().get(name, []):
                k = int(q[8]); ok, tot, c = summary[(cfg, k)]
                if v == "?": sc.add(m, sset, None)
                else: sc.add(m, sset, tot > 0 and ok == tot)
    return summary

_F1 = {}
def load_preds_f1():
    if not _F1:
        for ln in (HERE / "predictions-followup1.tsv").read_text().splitlines()[1:]:
            c, q, v, m = ln.split("\t"); _F1.setdefault(c, []).append((q, v, m))
    return _F1
def load_sets_f1():
    return {l.split("\t")[0]: l.split("\t")[2] for l in (HERE / "declared-followup1.tsv").read_text().splitlines()[1:]}


# ------------------------------------------------------------------ o23-size (follow-up 2)
def pair_offsets(d, cfg, mx, my, prefix, k):
    tdb = rd(d / (prefix + cfg + "-x.tadata.bin.gz")); tx_, ty_ = rd(d / (prefix + cfg + "-x.txt.gz")), rd(d / (prefix + cfg + "-y.txt.gz"))
    if tdb is None or tx_ is None or ty_ is None: return None
    pos = {(x, y): i for i, (_j, x, y) in enumerate(regions_with_stream(tdb))}
    rx, ry = pixel_rows(tx_), pixel_rows(ty_); H, W = len(rx), len(rx[0]); c = collections.Counter()
    for y in range(H):
        for x in range(W):
            vx, vy = rx[y][x], ry[y][x]
            if vx == BG or vy == BG or (vx & 15) != k or (vy & 15) != k: continue
            if (vx & 0xffff) >> 4 != mx or (vy & 0xffff) >> 4 != my: c["stale"] += 1; continue
            sx = round(f32(vx & 0xffff0000) * W / 2 + W / 2 - 0.5); sy = round(f32(vy & 0xffff0000) * H / 2 + H / 2 - 0.5)
            if sx % 32 != x % 32 or sy % 16 != y % 16: c["place"] += 1; continue
            s_, d_ = (sx // 32, sy // 16), (x // 32, y // 16)
            if s_ not in pos or d_ not in pos: c["no-stream"] += 1
            else: c[pos[s_] - pos[d_]] += 1
    return c

def run_o23size(d, preds, sets, sc):
    mk = {l.split("\t")[0]: int(l.split("\t")[1]) for l in (HERE / "gen/o23e-markers.tsv").read_text().splitlines()}
    fp = collections.defaultdict(list)
    for ln in (HERE / "predictions-followup2.tsv").read_text().splitlines()[1:]:
        c, q, v, m = ln.split("\t"); fp[c].append((q, v, m))
    cfgs = sorted({n[:-2] for n in mk}); print("o23-size: %d configs" % len(cfgs))
    for cfg in cfgs:
        obs = {}
        for k in (2, 3, 4):
            c = pair_offsets(d, cfg, mk[cfg + "-x"], mk[cfg + "-y"], "", k)
            if c is None: print("  %s: missing" % cfg); break
            offs = {a: b for a, b in c.items() if isinstance(a, int)}
            obs[k] = (max(offs, key=offs.get) if offs else None, dict(c))
        else:
            print("  %-16s o1 %s | o2 %s | o3 %s" % (cfg, obs[2], obs[3], obs[4]))
            for ax in "xy":
                for q, v, m in fp.get(cfg + "-" + ax, []):
                    k = {"o1": 2, "o2": 3, "o3": 4}[q[:2]]
                    if v == "?": sc.add(m, "heldout", None)
                    else: sc.add(m, "heldout", obs[k][0] == int(v))

# ------------------------------------------------------------------ q053-vtx
PB_BASE = 0x1000
def words(b, at, n):
    n = min(n, (len(b) - at) // 4)
    return list(struct.unpack("<%dI" % n, b[at:at + 4 * n]))

def stream_of(param, addr):
    out = []
    for w in words(param, addr - PB_BASE, 32):
        if w == 0xc0000000: break
        out.append(w)
    while out and out[-1] == 0: out.pop()
    return out

PER = 12   # dwords of a stored vertex of this batch: 1 + 11 coordinate outputs
def objects_of(param, td):
    """{OBJ_ISP_ADDR: [vertex dword lists]} over every region stream (decoder of 3d.md 10.1; vertex = per dwords)."""
    pg = next((i for i in range(len(td) // PAGE) if any(td[i * PAGE:(i + 1) * PAGE])), None)
    res = {}
    if pg is None: return res
    n = PAGE // 12
    ws = struct.unpack("<%dI" % (3 * n), td[pg * PAGE: pg * PAGE + 12 * n])
    pw = words(param, 0, len(param) // 4)
    for i in range(n):
        st = ws[3 * i + 1]
        if not st: continue
        sw = stream_of(param, st)
        j = 0
        while j + 1 < len(sw):
            t = (sw[j] >> 16) & 0xff; base = t & ~0x20; k = j + 2
            if t & 0x20 and k < len(sw): k += 1
            if base in (0x88, 0x8a, 0x8c) and k < len(sw): k += 1
            prim, obj = sw[j], sw[j + 1]; j = k
            nv = ((prim >> 25) & 0xf) + 1
            isp_at = (4 * (obj & 0x3ffffff) - PB_BASE) // 4
            per = PER
            start = isp_at - nv * per
            if start < 3: continue
            res.setdefault(obj & 0x3ffffff, [pw[start + per * v: start + per * (v + 1)] for v in range(nv)])
    return res

def run_q053vtx(d, preds, sets, sc):
    tab = [l.split("|") for l in (HERE / "gen/table-q053-vtx.txt").read_text().splitlines()]
    print("q053-vtx: %d jobs" % len(tab))
    summary = {}
    for name, sset, w, h, args, mkn, marker, regs in tab:
        par, td = rd(d / (name + ".param.bin.gz")), rd(d / (name + ".tadata.bin.gz"))
        if par is None or td is None: print("  %s: missing" % name); continue
        verts = {}
        for vs in objects_of(par, td).values():
            for v in vs: verts[(v[1], v[2])] = v          # the identity: o4, o5 (the clip x, y)
        marks = collections.Counter(v[11] for v in verts.values())
        mk_ok = (marks.get(int(marker, 16), 0) == len(verts))
        rl = [int(g) for g in regs.split(",")]
        row = []
        for i, g in enumerate(rl):
            vals = collections.Counter(v[3 + i] for v in verts.values())
            summary[(name, g)] = vals
            row.append("g%d=%s" % (g, ("0x%x" % next(iter(vals))) if len(vals) == 1 else "{" + ",".join("0x%x:%d" % kv for kv in sorted(vals.items())[:6]) + "}"))
        print("  %-12s vertices %d marker %s %s" % (name, len(verts), "ok" if mk_ok else "WRONG %s" % dict(marks), " ".join(row)))
        for q, v, m in preds.get(name, []):
            g = int(q[1:q.index("-")]); vals = summary[(name, g)]
            if v == "?": sc.add(m, sset, None); continue
            ok = mk_ok and len(verts) > 0 and len(vals) == 1 and next(iter(vals)) == int(v, 16)
            sc.add(m, sset, ok)
    return summary

# ------------------------------------------------------------------ q053-eot2 (follow-up 3)
def run_eot2(d, preds, sets, sc):
    tab = [l.split("|") for l in (HERE / "gen/table-q053-eot2.txt").read_text().splitlines()]
    fp = collections.defaultdict(list)
    for ln in (HERE / "predictions-followup3.tsv").read_text().splitlines()[1:]:
        c, q, v, m = ln.split("\t"); fp[c].append((q, v, m))
    sets3 = {l.split("\t")[0]: l.split("\t")[2] for l in (HERE / "declared-followup3.tsv").read_text().splitlines()[1:]}
    print("q053-eot2: %d jobs" % len(tab))
    seen = collections.defaultdict(dict)
    for name, sset, w, h, args, m, g, off in tab:
        txt = rd(d / (name + ".txt.gz"))
        if txt is None: print("  %s: missing" % name); continue
        t = txt.decode()
        got = {int(a, 16): int(b, 16) for a, b in re.findall(r"scratch \+0x([0-9a-f]+) 0x([0-9a-f]+)", t)}
        failed = "failed" in t
        v = got.get(int(off))
        other = {hex(a): hex(b) for a, b in got.items() if a != int(off)}
        seen[int(g)][(int(w), int(h))] = v
        print("  %-18s g%-3s %s at +0x%x: %s%s%s" % (name, g, "FAILED-after-store" if failed else "completed", int(off), "none" if v is None else "0x%x" % v,
              "  other dwords %s" % other if other else "", ""))
        for q, pv, mdl in fp.get(name, []):
            if pv == "?": sc.add(mdl, sets3.get(name, "?"), None)
            else: sc.add(mdl, sets3.get(name, "?"), v is not None and v == int(pv, 16))
    print("  per register, by target size:")
    for g in sorted(seen): print("   g%d %s" % (g, {"%dx%d" % k: ("none" if v is None else hex(v)) for k, v in seen[g].items()}))

# ------------------------------------------------------------------ q053-vtx2 (follow-up 4) and the vertex sequence of q053-vtx
def seq_vertices(par, td):
    objs = objects_of(par, td)
    return [v for a in sorted(objs) for v in objs[a]]

MODELS = {   # (task, lane, v, V) -> value
    "g17": {"H53-Q": lambda v, V: (v // V) % 4, "H53-F": lambda v, V: (v // 8) % 4},
    "g22": {"H53-Q": lambda v, V: (v % V) // 4 % 2, "H53-F": lambda v, V: v // 4 % 2},
    "g24": {"H53-Q": lambda v, V: 8 * ((v // V) % 2), "H53-F": lambda v, V: 8 * ((v // 8) % 2)},
    "g25": {"H53-Q": lambda v, V: (v % V) % 4, "H53-F": lambda v, V: v % 4},
    "g39": {"H53-Q": lambda v, V: 4 * ((v % V) // 4 % 2), "H53-F": lambda v, V: 4 * (v // 4 % 2)},
}

def run_vtx2(d, preds, sets, sc, table="q053-vtx2", pred_file="predictions-followup4.tsv"):
    tab = [l.split("|") for l in (HERE / ("gen/table-%s.txt" % table)).read_text().splitlines()]
    fp = collections.defaultdict(list)
    for ln in (HERE / pred_file).read_text().splitlines()[1:]:
        c, q, v, m = ln.split("\t"); fp[c].append((q, v, m))
    print("%s: %d jobs" % (table, len(tab)))
    for row in tab:
        name, sset, w, h, args, mkn, marker, regs = row[:8]; V = int(row[8]) if len(row) > 8 else 8
        par, td = rd(d / (name + ".param.bin.gz")), rd(d / (name + ".tadata.bin.gz"))
        if par is None or td is None: print("  %s: missing" % name); continue
        allv = seq_vertices(par, td)
        vs_idx = [i for i, v in enumerate(allv) if v[11] == int(marker, 16)]     # the decodable vertices (the marker is right)
        vs = allv
        mk_ok = len(vs_idx) >= 119
        rl = [int(g) for g in regs.split(",")]
        print("  %-16s V=%d vertices %d, marker right on %d (the rest read as zero words: undecoded)" % (name, V, len(vs), len(vs_idx)))
        for q, pv, m in fp.get(name, []):
            g = q.split("-")[0]; gi = int(g[1:]); col = 3 + rl.index(gi)
            obs = [v[col] for v in vs]
            exp = [MODELS[g][m](i, V) for i in range(len(vs))]
            bad = [i for i in vs_idx if obs[i] != exp[i]]
            print("     %s %-6s %d/%d decodable vertices match" % (m, g, len(vs_idx) - len(bad), len(vs_idx)))
            sc.add(m, sset, mk_ok and not bad)

# ------------------------------------------------------------------ bif-alias (Q076)
def parse_tl(txt):
    regs, rows = None, []
    for line in txt.splitlines():
        if line.startswith("timeline: regs"):
            regs = [int(x, 16) for x in line.split("samples")[0].split()[2:]]
        elif line.startswith("tl ") and regs:
            f = line.split()
            rows.append((int(f[1]), [int(x, 16) for x in f[2:]]))
    return regs, rows

def run_bif(d, preds, sets, sc, script):
    tab = [l.split("|") for l in (HERE / "gen/table-bif-alias.txt").read_text().splitlines()]
    risk = script.split("-")[-1]
    print("%s: cases of the %s class" % (script, risk))
    for name, sset, rk, mask in tab:
        if rk != risk: continue
        raw = rd(d / (name + ".txt.gz"))
        if raw is None: print("  %-26s NOT KEPT" % name); continue
        t = raw.decode()
        ok = "2 renders ok" in t
        failed = "FAILED" in t or "failed" in t
        outcome = "exact" if ok and not failed else "fault"
        regs, rows = parse_tl(t)
        lay = rd(d / (name + ".layout.txt.gz"))
        pd = re.search(r'"pd_phys": "0x([0-9a-f]+)"', lay.decode()).group(1) if lay else None
        info = ""
        if regs and rows:
            last = dict(zip(regs, rows[-1][1]))
            first = dict(zip(regs, rows[0][1]))
            lists = {i: last.get(0x0c34 + 4 * i, 0) for i in range(16)}
            changed = [i for i in range(16) if last.get(0x0c34 + 4 * i, 0) != first.get(0x0c34 + 4 * i, 0)]
            bank0 = sorted({r[1][regs.index(0x0c78)] for r in rows})
            base15 = lists[15]
            info = "lists changed %s BASE15 %#x layout pd_phys %s BANK0 values %s" % (changed, base15, pd, [hex(b) for b in bank0])
            e_ok = pd is not None and base15 == int(pd, 16)
        print("  %-26s %-6s %s" % (name, outcome, info))
        for q, v, m in preds.get(name, []):
            if q == "outcome": sc.add(m, sset, outcome == v)
            elif q == "base1-is-client-pd": sc.add(m, sset, None)

# ------------------------------------------------------------------ dpm-bit2 (Q036/Q045)
def run_dpm(d, preds, sets, sc, script):
    tab = [l.split("|") for l in (HERE / "gen/table-dpm-bit2.txt").read_text().splitlines()]
    risk = script.split("-")[-1]
    print("%s: %s class" % (script, risk))
    res = collections.defaultdict(list)
    for name, sset, rk, n, pages in tab:
        if rk != risk: continue
        raw = rd(d / (name + ".txt.gz"))
        if raw is None: print("  %-22s NOT KEPT" % name); continue
        t = raw.decode()
        regs, rows = parse_tl(t)
        if not regs: print("  %-22s no timeline: %s" % (name, t[-120:].replace("\n", " "))); res[(n, pages)].append(None); continue
        col = {r: regs.index(r) for r in (0x0710, 0x071c, 0x0740, 0x0748, 0x0730, 0x072c) if r in regs}
        b748 = sorted({r[1][col[0x0748]] for r in rows})
        clears = any(v & 4 == 0 for v in b748)
        hi = any((r[1][col[0x0710]] >> 16) or (r[1][col[0x071c]] >> 16) for r in rows)
        r740 = any(r[1][col[0x0740]] for r in rows)
        over = "scene overflowed the parameter buffer" in t
        failed = ("failed" in t and not over) or "hung" in t or "faulted" in t
        outcome = "FAILED" if failed else ("overflow" if over else "ok")
        res[(n, pages)].append(clears)
        print("  %-22s %-6s samples %d  0x0748 values %s  bit2 %s  hi-halves %s  0x0740 %s" % (
            name, outcome, len(rows), [hex(v) for v in b748], "CLEARS" if clears else "stays", "NONZERO" if hi else "zero", "NONZERO" if r740 else "zero"))
        for q, v, m in preds.get(name, []):
            if q == "bit2-clears":
                sc.add(m, sset, None if v == "?" else (clears == (v == "yes")))
            elif q == "hi-halves-zero":
                sc.add(m, sset, (not hi) == (v == "yes"))
    print("  bit 2 clears, per cell (vertices, pages): %s" % {k: sum(1 for x in v if x) for k, v in res.items()})
SCRIPTS = {"q053-vtx2": run_vtx2, "q053-eot2": run_eot2, "q053-vtx": run_q053vtx, "o23-tiles": run_o23, "o23-order": run_o23order, "o23-size": run_o23size}
def main(a):
    d = pathlib.Path(a[0]); preds, sets = load_preds(), load_sets(); sc = Score()
    for s in (a[1:] or SCRIPTS):
        if (d / s).is_dir() and s in SCRIPTS: SCRIPTS[s](d / s, preds, sets, sc)
        elif (d / s).is_dir() and s.startswith("bif-alias-"): run_bif(d / s, preds, sets, sc, s)
        elif (d / s).is_dir() and s.startswith("dpm-bit2-"): run_dpm(d / s, preds, sets, sc, s)
    sc.show()
if __name__ == "__main__": main(sys.argv[1:])
