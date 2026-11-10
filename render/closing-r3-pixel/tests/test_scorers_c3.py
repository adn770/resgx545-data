#!/usr/bin/env python3
"""The p-c3 scorer (Q276) on R1's p-c2 and S1b's p-c kept images (the structural G-o4 control passes in every real run; the scorer
on R1's own data) and on synthetic worlds built from R1's real landing geometry with the tags re-written by a truth model: M (the
frozen model), the transpose, g23 = x, g23 = y << 16 | x, a gated o4 write; a control failing voids ITS group only; the premise
controls scope the direct reads.  Prints ok / FAIL lines; exit 1 on any FAIL.   PY tests/test_scorers_c3.py"""
import collections
import pathlib
import re
import shutil
import sys

sys.dont_write_bytecode = True
R3 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R3 / "score"), str(R3 / "gen"), str(R3 / "tests")]
import r3lib as L  # noqa: E402
import score_c3 as Q  # noqa: E402
import worlds as W  # noqa: E402

FX = R3 / "tests/fixtures"
failed, nok = [], 0
BG = 0xff203040


def check(cond, what):
    global nok
    if cond:
        nok += 1
        print("ok   " + what)
    else:
        failed.append(what)
        print("FAIL " + what)


# ------------------------------------------------------------------------------------------------ real data
runs, passes = 0, 0
for d in ("r1-p-c2", "s1b-p-c"):
    k = L.Kept(FX / d)
    for c in sorted({n[:-2] for n in k.names() if n.endswith("-x") and not n.endswith("-rep") and "rd-" not in n}):
        gx, gy = Q.read_grid(k, c + "-x"), Q.read_grid(k, c + "-y")
        if not gx or not gy:
            continue
        src, _, _ = Q.c_decode(gx, gy)
        ok, why = Q.g_o4_control(Q.o4_words(gx, gy), Q.measure(src))
        runs += 1
        passes += ok
check(runs == 26 and passes == 26, f"the structural G-o4 control passes in {passes} of {runs} real runs (R1's 18 and S1b's 8 configurations; design: 26 of 26)")
k = L.Kept(FX / "r1-p-c2")
gx, gy = Q.read_grid(k, "c-k1-x"), Q.read_grid(k, "c-k1-y")
src, _, _ = Q.c_decode(gx, gy)
meas = Q.measure(src)
check(Q.disagree(src, "lane:1:A") <= Q.allowed(src, "lane:1:A") and Q.disagree(src, "lane:1:B") > Q.allowed(src, "lane:1:B"),
      "R1's c-k1 (real data): HQ-a (lane A) holds and the transpose (lane B) fails, as E772 read it")
gx0, gy0 = Q.read_grid(k, "c-e709-x"), Q.read_grid(k, "c-e709-y")
s0, _, _ = Q.c_decode(gx0, gy0)
m0 = Q.measure(s0)
ow = Q.o4_words(gx0, gy0)
check(Q.g_o4_control(ow, m0)[0], "real c-e709: the control passes")
bad = dict(ow, x5=3, y5=2)
check(not Q.g_o4_control(bad, m0)[0], "synthetic world with no o4 landing (3 and 2 tag-5 words): G-o4 FAILS")
bad = dict(ow, x5=400, y5=380)
check(not Q.g_o4_control(bad, m0)[0], "synthetic flood (400 tag-5 words): G-o4 FAILS")
m_odd = dict(m0, p5={(0, 0): 5, (1, 0): 4})
check(not Q.g_o4_control(ow, m_odd)[0], "synthetic odd sources (4 of 9 pair sources not (even, even)): G-o4 FAILS")
check(not Q.g_o4_control(dict(ow, x13=9), m0)[0], "tag-5' words in the x job (9): G-o4 FAILS")
check(Q.o4_class_words(dict(x5=19, y5=22, x13=0, y13=1)) == "5" and Q.o4_class_words(dict(x5=0, y5=0, x13=30, y13=31)) == "5'"
      and Q.o4_class_words(dict(x5=15, y5=14, x13=12, y13=11)) == "mixed" and Q.o4_class_words(dict(x5=3, y5=2, x13=0, y13=0)) is None,
      "o4 class from the WORDS of both jobs (R1's lowest real count 19 gives 5; 5'; mixed; no landing -> None)")


# ------------------------------------------------------------------------------------------------ synthetic worlds
def rows_text(grid, name):
    return "".join("probe %s: row %d: %s\n" % (name, y, " ".join("%08x" % v for v in row)) for y, row in enumerate(grid)) + \
        "probe %s: o0 mixed 0xff203040 x2998 0x00000001 x1098\n" % name


tpl = {ax: Q.read_grid(k, f"c-k0-{ax}") for ax in "xy"}
rd_pa_tpl = {ax: Q.read_grid(k, f"c-rd-pa-{ax}") for ax in "xy"}
markers = {ln.split("\t")[0]: int(ln.split("\t")[1]) for ln in (R3 / "bins/c3-markers.tsv").read_text().splitlines()}


def f32hi(f):
    import struct
    return struct.unpack("<I", struct.pack("<f", f))[0] & 0xffff0000


class Truth:
    def __init__(self, lane="A", g23="mod32", o4gated=False, g24="mod16", rd128="mod32"):
        self.lane, self.g23, self.o4gated, self.g24, self.rd128 = lane, g23, o4gated, g24, rd128

    def g25(self, x, y):
        return Q.lane(x, y, self.lane)

    def g23v(self, x, y):
        return {"mod32": x % 32, "x": x, "xy": y << 16 | x}[self.g23]

    def g24v(self, x, y):
        return {"mod16": y % 16, "y": y}[self.g24]

    def p1(self, cfg, x, y):
        m = re.fullmatch(r"k(\d)", cfg)
        if m:
            return self.g25(x, y) == int(m[1])
        m = re.fullmatch(r"g23r(\d+)", cfg)
        if m:
            return bool(self.g23v(x, y) & (1 << int(m[1])))
        if cfg == "g23m18":
            return bool(self.g23v(x, y) & 0x18)
        m = re.fullmatch(r"g23eq(\d+)", cfg)
        if m:
            return self.g23v(x, y) == int(m[1])
        m = re.fullmatch(r"g25b(\d)", cfg)
        if m:
            return bool(self.g25(x, y) & (1 << int(m[1])))
        m = re.fullmatch(r"o4s?-k(\d)", cfg)
        if m:
            return self.g25(x, y) == int(m[1])
        return True                                         # unpredicated: the p1 write (the second) wins


def synth_pair(cfg, tr, m):
    """x and y images of an o1/o4 configuration: R1's real landing geometry, tags rewritten by the truth model."""
    out = {}
    for ax in "xy":
        mm = m if ax == "x" else m + 1
        g = []
        for y in range(64):
            row = []
            for x in range(64):
                v = tpl[ax][y][x]
                if v == BG:
                    row.append(v)
                    continue
                tag = v & 15
                src = Q.source_of(tpl["x"][y][x], tpl["y"][y][x])
                if tag in (2, 12) and src:
                    t = 2 if tr.p1(cfg, *src) else 12
                    if not re.match(r"k\d|g23|g25", cfg):
                        t = 2
                    nt = t
                elif tag in (5, 13) and src:
                    p = tr.p1(cfg, *src)
                    if cfg.startswith("o4s"):
                        nt = (5 if p else 13) if tr.o4gated else 13
                    elif cfg.startswith("o4"):
                        nt = (5 if p else 13) if tr.o4gated else 5
                    else:
                        nt = 5
                else:
                    nt = tag
                row.append((v & 0xffff0000) | (((mm << 4) | nt) & 0xffff))
            g.append(row)
        out[ax] = g
    return out


def rd_grid(cfg, tr, w, full, pa_ax=None, mk=0):
    cover = {(x, y) for y in range(64) for x in range(64) if rd_pa_tpl["x"][y][x] != BG} if not full else {(x, y) for y in range(w) for x in range(w)}
    g = [[BG] * w for _ in range(w)]
    for x, y in cover:
        if pa_ax:
            f = ((x if pa_ax == "x" else y) + .5 - w / 2) / (w / 2)
            v = f32hi(f) | ((mk << 4 | 15) & 0xffff)
        else:
            which = cfg.split("-")[-1]
            v = {"g23": tr.g23v(x, y) if w == 64 else (x % 32 if tr.rd128 == "mod32" else x % 64 if tr.rd128 == "mod64" else x),
                 "g24": tr.g24v(x, y), "g25": tr.g25(x, y)}[which]
        g[y][x] = v
    return g


def p_c3_world(tr, fail_o4=False, fail_o1=False, fail_prem=None, drop=()):
    jobs = []
    for ln in (R3 / "tables/p-c3.txt").read_text().splitlines():
        if not ln or ln.startswith("#"):
            continue
        name = ln.split("|")[0]
        if name in drop:
            continue
        mm = re.fullmatch(r"c-(.+?)(?:-([xy]))?(-rep)?", name)
        cfg, ax = mm[1], mm[2]
        if cfg.startswith(("rd", "rdf")) and "-pa" not in cfg:
            w = 128 if "rdf128" in cfg else 64
            g = rd_grid(cfg, tr, w, full=cfg.startswith("rdf"))
            jobs.append(dict(name=name, out=rows_text(g, name), pre=None, post=None))
            continue
        if "-pa" in cfg:
            w = 128 if "rdf128" in cfg else 64
            g = rd_grid(cfg, tr, w, full=cfg.startswith("rdf"), pa_ax=ax, mk=markers[name])
            if fail_prem == cfg:
                g = [[BG] * w for _ in range(w)]
            jobs.append(dict(name=name, out=rows_text(g, name), pre=None, post=None))
            continue
        if name.endswith("-rep"):
            base = name[:-len("-rep")]
            pair = synth_pair("k1", tr, markers[base])
            jobs.append(dict(name=name, out=rows_text(pair["x"], name), pre=None, post=None))
            continue
        base_cfg = "o4-u" if cfg == "e709" else ("u" if cfg in ("u", "u-r2") else cfg)
        mk = markers.get(f"c-{cfg}-x", 0x7ff)
        pair = synth_pair(base_cfg, Truth() if cfg in ("u", "u-r2") else tr, mk)
        g = pair[ax]
        if fail_o4 and cfg in ("e709", "o4-u"):
            g = [[(BG if (v & 15) in (5, 13) else v) for v in row] for row in g]
        if fail_o1 and cfg in ("u", "u-r2"):
            g = [[((v & 0xfff0) == v and v or ((v & 0xfffffff0) | 12)) if (v != BG and (v & 15) == 2) else v for v in row] for row in g]
        jobs.append(dict(name=name, out=rows_text(g, name), pre=None, post=None))
    return jobs


def score(jobs):
    d = W.stage("p-c3", jobs)
    text, res = Q.score_p_c3(L.Kept(d), L.load_preds(stage="p-c3"))
    return text, res, next(x for x in text.splitlines() if x.startswith("SUMMARY:"))


text, res, s = score(p_c3_world(Truth()))
check("Q276 ANSWERED" in s and not res["gate_text"], "p-c3 world M (the frozen model true everywhere): Q276 ANSWERED, every group control passes, no row cannot tell; " + s[:120])
for want in ("k", "g23", "g25", "o4", "o4s", "rd", "rdf", "rdf128"):
    check(want + ": held out:" in s, f"  the group {want} is tallied in the SUMMARY")
seg = s.split("o4s:")[1].split(";  ")[0] if "o4s:" in s else ""
check("consistent [\"M (a predicate on the o4 write is ignored: the last write, tag 5', wins) (3)\"]" in seg and "refuted ['G (the o4 write gated like o1: the p1-true instances keep tag 5) (3 of 3)']" in seg,
      "  the swapped-order o4 rows: M consistent on 3 of 3, the gated alternative refuted on 3 of 3 in world M: " + seg[:100])
text, res, s = score(p_c3_world(Truth(lane="B")))
check("NOT ANSWERED" in s and "lane" not in s[:20], "p-c3 world T (g25 transposed): NOT ANSWERED; " + s[:200])
check(re.search(r"k: held out: consistent .*refuted \[.*M \(g25", s) is not None or "M (g25 = (x&1) | (y&1)<<1)" in s.split("k:")[1][:500], "  M is refuted on the lane rows of world T (k1, k2) and the transpose stands")
text, res, s = score(p_c3_world(Truth(g23="x")))
check("NOT ANSWERED" in s and "X (g23 = x" in s, "p-c3 world X (g23 = x, no wrap): NOT ANSWERED, M refuted at g23r5 (bit 5 true for x in 32..63)")
text, res, s = score(p_c3_world(Truth(g23="xy")))
check("NOT ANSWERED" in s, "p-c3 world XY (g23 = y << 16 | x): NOT ANSWERED (r20 reads y bit 4)")
text, res, s = score(p_c3_world(Truth(o4gated=True)))
check("NOT ANSWERED" in s and "M (a predicate on the o4 write is ignored" in s, "p-c3 world G (the o4 write gated like o1): NOT ANSWERED, M refuted on the o4 rows")
# controls scoped to their group
text, res, s = score(p_c3_world(Truth(), fail_o4=True))
check(res["g_o4"] is False and any("c-o4-k0" in g for g in res["gate_text"]) and not any("c-k0" in g for g in res["gate_text"]) and not any("c-g23r0" in g for g in res["gate_text"]),
      "G-o4 control failing (no o4 words): the o4 and o4s rows cannot tell, the o1 rows (k, g23) are still scored (scoped control, R3-P6)")
check("NOT ANSWERED" in s, "  ... and the verdict is not `answered`")
text, res, s = score(p_c3_world(Truth(), fail_o1=True))
check(res["g_o1"] is False and any("c-k0" in g for g in res["gate_text"]) and not any("c-o4-k0" in g for g in res["gate_text"]),
      "G-o1 control failing (tag-2 fraction low): the k / g23 / g25 rows cannot tell, the o4 rows are still scored")
text, res, s = score(p_c3_world(Truth(), fail_prem="rdf128-pa"))
check(any("c-rdf128-g23" in g for g in res["gate_text"]) and not any("c-rdf-g23" in g or "c-rd-g23" in g for g in res["gate_text"]),
      "the 128x128 premise control failing voids only the 128x128 direct reads (the default and full 64x64 reads stand)")
text, res, s = score(p_c3_world(Truth(), fail_prem="rd-pa"))
check(any("c-rd-g23" in g for g in res["gate_text"]) and not any("c-rdf-g23" in g for g in res["gate_text"]), "the default-triangle premise control failing voids only c-rd-g*")
text, res, s = score(p_c3_world(Truth(), drop=("c-k3-y",)))
check("c-k3: NODATA" in text, "a missing y job of a pair is NODATA for that configuration, nothing else")
# an alternative that cannot be told from M at a row is void, not consistent: g23eq40's X differs at x = 40 only (sources exist there)
text, res, s = score(p_c3_world(Truth()))
ent = res["entries"]["g23"]
eq20 = [e for e in ent if e[0].startswith("X (g23 = x: true only at x == 20")]
eq40 = [e for e in ent if e[0].startswith("X (g23 = x: true only at x == 40")]
check(eq40 and eq40[0][2] is False, "g23eq40: X (true only at x = 40) is REFUTED by the real sources at x = 40 (tag 2 never there)")
check(eq20 and eq20[0][2] in (False, None), "g23eq20: X (true only at x = 20) is refuted or void (sources at x = 52 are few): " + str(eq20))
# direct reads: the three values
text, res, s = score(p_c3_world(Truth(g24="y")))
check("NOT ANSWERED" in s and "M (g24 = y mod 16" in s, "world g24 = y: c-rd-g24 / c-rdf-g24 refute M (y mod 16)")
text, res, s = score(p_c3_world(Truth(rd128="x")))
check("NOT ANSWERED" in s, "world g23 = x at 128x128 (no wrap): the 128x128 read refutes M (x mod 32)")

print(f"\n{nok} ok, {len(failed)} FAIL")
sys.exit(1 if failed else 0)
