#!/usr/bin/env python3
"""The R1 scorers (score_q276, score_geo2) with the R1 frozen predictions on
  - past-run data (S1 and S1b kept files, renamed to the R1 job names where a job is the same condition): a reader check,
    not evidence (those data are the FIT of every '(S1b fit)' hypothesis);
  - synthetic worlds with a known truth: each world must give its hypothesis consistent and the others refuted, a failing
    control must give `cannot tell`, a void job must be NODATA.
Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import collections  # noqa: E402
import gzip  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import struct  # noqa: E402
import tempfile  # noqa: E402

R1 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R1 / "score"), str(R1 / "gen"), str(R1 / "tests")]
import r1_geo as GEN  # noqa: E402
import r1models as M  # noqa: E402
import score_geo2 as G  # noqa: E402
import score_q276 as Q  # noqa: E402
import synth  # noqa: E402
from r1lib import Kept, load_preds  # noqa: E402
from rcommon import f32  # noqa: E402

HOME = pathlib.Path.home()
S1 = HOME / "src/scratch/resgx545/closing/s1/out"
S1B = HOME / "src/scratch/resgx545/closing/s1b-v2/out"
ok = True
TMP = pathlib.Path(tempfile.mkdtemp())


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def summary(text):
    return next((ln for ln in text.splitlines() if ln.startswith("SUMMARY:")), "no SUMMARY")


def table(st):
    out = {}
    for ln in (R1 / "tables" / f"{st}.txt").read_text().splitlines():
        if ln and not ln.startswith("#"):
            f = ln.split("|", 6)
            out[f[0]] = f[6]
    return out


def as_preds(tuples):
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    for c, q, v, m, s in tuples:
        out[c][q].append((v, m, s))
    return out


def import_jobs(src, dst, mapping):
    """Copy kept jobs of an old session under new names (new: old)."""
    dst = pathlib.Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    lines = (pathlib.Path(src) / "cases.tsv").read_text().splitlines()
    hdr, rows = lines[0], [ln.split("\t") for ln in lines[1:]]
    out = [hdr]
    for new, old in mapping.items():
        for r in rows:
            if r[0] == old:
                out.append("\t".join([new] + r[1:]))
        for f in pathlib.Path(src).glob(f"{old}.*"):
            shutil.copy(f, dst / (new + f.name[len(old):]))
    (dst / "cases.tsv").write_text("\n".join(out) + "\n")
    return Kept(dst)


# ===================================================================================================== p-c2
PC = load_preds(None, "p-c2")
# ---- S1b's p-c data (the fit): the readers decode it as S1b's did
pc = load_preds(None, "p-c2")
for n in list(pc):
    pc[n].pop("marker", None)                 # S1b's programs carry other markers
pc.pop("c-u-r2-x", None)                      # S1b ran c-u three times; the frozen R1 criterion covers c-u and c-u-r2
t, _ = Q.score_p_c2(Kept(S1B / "p-c"), pc)
s = summary(t)
check("p-c2 on S1b's p-c: global controls pass (c-e709, c-u at 0.990 >= 0.98)", "global controls pass" in s, s[:90])
check("p-c2 on S1b's p-c: c-g23 (HG x bit 4: 0 exceptions of 485) and c-k7, c-k0 (HQ) are consistent as REPEAT only, "
      "never held out", "repeat only: consistent ['HG (S1b fit: x bit 4, 485 of 485) (1)']" in s and "HQ (S1b fit) (2)" in s
      and "held out: consistent none" in s, s[:400])
# ---- synthetic worlds
UNI = [(x, y) for y in range(14, 44) for x in range(10, 56)]
O4S = [(x, y) for x in range(10, 56, 2) for y in range(26, 44, 2)][:25]


def wordf(sx, tag, marker):
    f = (sx - 31.5) / 32
    return (struct.unpack("<I", struct.pack("<f", f))[0] & 0xffff0000) | ((marker << 4 | tag) & 0xffff)


def render(grid, name):
    return "\n".join(f"probe {name}: row {y}: " + " ".join(f"{v:08x}" for v in grid[y]) for y in range(64)) + "\n"


BG = 0xff203040
MARK = {ln.split("\t")[0]: int(ln.split("\t")[1]) for ln in (R1 / "bins/c2-markers.tsv").read_text().splitlines()}


def pair_images(mx, o1, o4=None, dest4=lambda s: (s[0], s[1] + 20), shift=(0, 0)):
    gx = [[BG] * 64 for _ in range(64)]
    gy = [[BG] * 64 for _ in range(64)]
    for s, tag in o1:
        dx, dy = s[0] + shift[0], s[1] + shift[1]
        gx[dy][dx] = wordf(s[0], tag, mx)
        gy[dy][dx] = wordf(s[1], tag, mx + 1)
    for s, tag in (o4 or []):
        dx, dy = dest4(s)
        gx[dy][dx] = wordf(s[0], tag, mx)
        gy[dy][dx] = wordf(s[1], tag, mx + 1)
    return gx, gy


def lane(s, w):
    return Q.lane(s[0], s[1], w)


def world(name, lane_w, g23_xy, o4_by_k, rd_g25_w, e709_n5=25, bad_marker=None, rd_pa_shift=(0, 0)):
    """A kept directory of every p-c2 job whose truth is: g25 lane identity `lane_w` (A or B), g23 = y<<16|x (or x
    only), o4 write class per configuration `o4_by_k` ({'k7': "5'", ...})."""
    d = synth.Dir(TMP / name, "p-c2")
    rules = {"u": lambda s: True, "u-r2": lambda s: True, "g23r4": lambda s: s[0] >> 4 & 1, "g23": lambda s: s[0] >> 4 & 1,
             "g23r5": lambda s: s[0] >> 5 & 1, "g23r3": lambda s: s[0] >> 3 & 1, "g23r0": lambda s: s[0] & 1,
             "g23r20": (lambda s: s[1] >> 4 & 1) if g23_xy else (lambda s: False)}
    for k in (0, 1, 2, 5, 7):
        rules[f"k{k}"] = (lambda k: lambda s: lane(s, lane_w) == k)(k)
    for cfg in ["e709", "u", "u-r2", "g23r4", "k7", "k0", "g23", "k1", "k2", "k5", "g23r5", "g23r3", "g23r0", "g23r20",
                "o4-k7", "o4-k3", "o4-k0", "o4-u"]:
        for ax in "xy":
            pass
        mx = MARK.get(f"c-{cfg}-x", 0x300)
        if bad_marker == cfg:
            mx += 5
        if cfg == "e709":
            o1, o4 = [], [(s, 5) for s in O4S[:e709_n5]]
        elif cfg.startswith("o4-"):
            o1 = [(s, 2) for s in UNI]
            o4 = [(s, {"5": 5, "5'": 13}[o4_by_k[cfg[3:]]]) for s in O4S]
        else:
            o1 = [(s, 2 if rules[cfg](s) else 12) for s in UNI]
            o4 = []
        gx, gy = pair_images(mx, o1, o4)
        d.job(f"c-{cfg}-x", render(gx, f"c-{cfg}-x"))
        d.job(f"c-{cfg}-y", render(gy, f"c-{cfg}-y"))
    gx, gy = pair_images(MARK["c-k1-x"], [(s, 2 if rules["k1"](s) else 12) for s in UNI])
    d.job("c-k1-x-rep", render(gx, "c-k1-x-rep"))
    g = [[BG] * 64 for _ in range(64)]
    g2 = [[BG] * 64 for _ in range(64)]
    for x, y in UNI:
        g[y][x] = (y << 16 | x) if g23_xy else x
        g2[y][x] = lane((x, y), rd_g25_w)
    d.job("c-rd-g23", render(g, "c-rd-g23"))
    d.job("c-rd-g25", render(g2, "c-rd-g25"))
    px = [[BG] * 64 for _ in range(64)]
    py = [[BG] * 64 for _ in range(64)]
    for x, y in UNI:
        px[y + rd_pa_shift[1]][x + rd_pa_shift[0]] = wordf(x, 15, MARK["c-rd-pa-x"])
        py[y + rd_pa_shift[1]][x + rd_pa_shift[0]] = wordf(y, 15, MARK["c-rd-pa-y"])
    d.job("c-rd-pa-x", render(px, "c-rd-pa-x"))
    d.job("c-rd-pa-y", render(py, "c-rd-pa-y"))
    return Kept(d.d)


W1 = world("w1", "A", True, {"k7": "5", "k3": "5", "k0": "5", "u": "5"}, "A")
t1, _ = Q.score_p_c2(W1, PC)
s1 = summary(t1)
check("p-c2 world 1 (HQ-a, HG, HG-xy, HN-o4, direct reads as HQ-a / HG-xy): controls pass", "global controls pass" in s1, s1[:200])
for label, frag in (("k: HQ-a consistent (k1, k2)", "HQ-a (g25 = x&1 | (y&1)<<1) (2)"),
                    ("k: HQ-b refuted in 2 of 2", "HQ-b (g25 = (x&1)<<1 | y&1, the transpose) (2 of 2)"),
                    ("k: HQ-none consistent", "HQ-none"),
                    ("g23: HG consistent (b5, b3, b0)", "HG (g23 low bits carry x: bit 5) (1)"),
                    ("g23: HG-xy consistent, HG-x refuted", "HG-x (g23 = x: bit 20 never) (1 of 1)"),
                    ("o4: HN-o4 consistent in 3", "HN-o4 (the o4 write is not gated) (3)"),
                    ("o4: HG-o4 refuted at k7, k3", "HG-o4 (o4 gated like o1 by g25 == k) (2 of 3)"),
                    ("o4: H-g25-7 refuted at k3, k0", "H-g25-7 (o4 landings are instances with g25 == 7) (2 of 3)"),
                    ("rd: HG-xy and HQ-a consistent, HQ-b refuted", "HQ-b (g25 = (x&1)<<1 | (y&1)) (1 of 1)")):
    check(f"p-c2 world 1: {label}", frag in s1, "" if frag in s1 else s1[:900])
check("p-c2 world 1: the replicate of c-k1 reads the same", "replicate of c-k1 (1)" in s1)
W2 = world("w2", "B", False, {"k7": "5'", "k3": "5'", "k0": "5", "u": "5"}, "B")
s2 = summary(Q.score_p_c2(W2, PC)[0])
for label, frag in (("HQ-b consistent", "HQ-b (g25 = (x&1)<<1 | y&1, the transpose) (2)"),
                    ("HQ-a refuted", "HQ-a (g25 = x&1 | (y&1)<<1) (2 of 2)"),
                    ("HG-x consistent, HG-xy refuted", "HG-xy (g23 = y<<16 | x: bit 20 is y bit 4) (1 of 1)"),
                    ("HG-o4 consistent in 3", "HG-o4 (o4 gated like o1 by g25 == k) (3)"),
                    ("HN-o4 refuted at k7, k3", "HN-o4 (the o4 write is not gated) (2 of 3)"),
                    ("direct g25 is HQ-b", "HQ-b (g25 = (x&1)<<1 | (y&1)) (1)")):
    check(f"p-c2 world 2: {label}", frag in s2, "" if frag in s2 else s2[:900])
s3 = summary(Q.score_p_c2(world("w3", "A", True, {"k7": "5", "k3": "5", "k0": "5", "u": "5"}, "A", e709_n5=9), PC)[0])
check("p-c2: c-e709 with 9 tag-5 pairs: cannot tell", "cannot tell: global controls failed" in s3, s3[:120])
s4 = summary(Q.score_p_c2(world("w4", "A", True, {"k7": "5", "k3": "5", "k0": "5", "u": "5"}, "A", bad_marker="k1"), PC)[0])
check("p-c2: a config whose marker is not the frozen one is NODATA, not scored", "void configurations ['c-k1']" in s4, s4[-150:])
s5 = summary(Q.score_p_c2(world("w5", "A", True, {"k7": "5", "k3": "5", "k0": "5", "u": "5"}, "A", rd_pa_shift=(3, 0)), PC)[0])
check("p-c2: the premise control c-rd-pa failing (o0 not at the pixel's own position): the direct reads cannot tell",
      "c-rd-g23: cannot tell (the premise control c-rd-pa failed" in s5 and "c-rd-g25: cannot tell" in s5, s5[-300:])
# a config with fewer than 300 decoded sources is void
d = synth.Dir(TMP / "w6", "p-c2")
shutil.copytree(TMP / "w1", TMP / "w6x")
sparse = [(s, 2) for s in UNI[:100]]
gx, gy = pair_images(MARK["c-k1-x"], sparse)
(TMP / "w6x" / "c-k1-x.txt.gz").write_bytes(gzip.compress(render(gx, "c-k1-x").encode()))
(TMP / "w6x" / "c-k1-y.txt.gz").write_bytes(gzip.compress(render(gy, "c-k1-y").encode()))
s6 = summary(Q.score_p_c2(Kept(TMP / "w6x"), PC)[0])
check("p-c2: 100 decoded sources (< 300): c-k1 cannot tell", "c-k1: cannot tell (100 decoded o1 sources < 300)" in s6, s6[:300])
# ===================================================================================================== g-u1 / U
t = table("g-u1")
GP = load_preds(None, "g-u1")
UP = {n: next(int(v) for v, m, s in qs["U"] if m.startswith("HU1")) for n, qs in GP.items() if "U" in qs}


def u1_world(name, U_override=None, dmesg=None, p072c=True, stage="g-u1", skip=()):
    d = synth.Dir(TMP / name, stage)
    for n, args in t.items():
        if n in skip:
            continue
        K = int(re.search(r"-n (\d+)", args)[1])
        geo = "".join(f"tri 1024x768 #{i}: geometry only, the scene left open\n" for i in range(1, K))
        if n in UP:
            u = (U_override or {}).get(n, UP[n])
            txt = synth.dpm_job_text(0x400, [u], with_072c=p072c, count=1)
            d.job(n, geo + txt, 0, "ok", args=args)
        else:                                            # a boundary job
            thr0 = int(GP[n]["knob0624_first"][0][0], 16)
            over = GP[n]["outcome"][0][0] == "overflow"
            txt = synth.dpm_job_text(thr0, [thr0, thr0 + 1], partials=1, with_072c=p072c) if over else \
                synth.dpm_job_text(thr0, [thr0], with_072c=p072c)
            d.job(n, geo + ("probe x: failed: scene overflowed\n" if over else "") + txt, 3 if over else 0, "ok", args=args)
    return Kept(d.d)


ku = u1_world("u1a")
tu, res = G.score_u1(ku, GP)
su = summary(tu)
check("g-u1 world (truth = HU1): controls pass, HU1 exact on all held-out cells, HU2 refuted where it differs, E625's rule holds on the four boundary jobs",
      "controls pass" in su and re.search(r"HU1 \(15\)", su) and "HU2 (" in su and "E625 rule (HU1's U) (4)" in su, su[:420])
ku2 = u1_world("u1b", {"u-m32": 22})
su2 = summary(G.score_u1(ku2, GP)[0])
check("g-u1: one cell off by one (u-m32 reads 22, HU1 says 21): HU1 refuted in 1 of 15 with the residual", "HU1 (1 of 15)" in su2, su2[:300])
ku3 = u1_world("u1c", {"u-ctl-1": 20})
su3 = summary(G.score_u1(ku3, GP)[0])
check("g-u1: control u-ctl-1 reading 20: cannot tell", "cannot tell: control(s) ['u-ctl-1']" in su3, su3[:200])
tu4, _ = G.score_u1(u1_world("u1d", skip=("u-ctl-2a",)), GP)
check("g-u1: a missing control is cannot tell", "cannot tell" in summary(tu4))
ku5 = u1_world("u1e", p072c=False)
tu5 = G.score_u1(ku5, GP)[0]
check("g-u1 without 0x072c: the side table says not scored", "D36: not scored" in tu5)
ku6 = u1_world("u1f")
tu6 = G.score_u1(ku6, GP)[0]
check("g-u1 with 0x072c but a completing job (no abort): D36 is only scored where an abort exists",
      "D36 side table" in tu6 or "D36: not scored" in tu6)
# ---- the real S1 g-e2a data through the U1 reader (names mapped; S1 timelines lack 0x072c)
mp = {"u-ctl-1": "u-1-0x422", "u-ctl-2a": "u-2a-0x422", "x-3a": "u-3a-0x422", "x-4a": "u-4a-0x422", "x-2s": "u-2s-0x422",
      "x-3s": "u-3s-0x422", "x-4s": "u-4s-0x422"}
kr = import_jobs(S1 / "g-e2a", TMP / "u1real", mp)
pr = {"u-ctl-1": 19, "u-ctl-2a": 29, "x-3a": 35, "x-4a": 37, "x-2s": 19, "x-3s": 22, "x-4s": 22}
rp = as_preds([(n, "U", str(u), "HU1 (sgx-pipe TA model)", "control" if n.startswith("u-ctl") else "heldout") for n, u in pr.items()]
              + [(n, "knob0624_first", "0x400", "knob", "heldout") for n in pr])
tr, _ = G.score_u1(kr, rp)
check("g-u1 reader on S1's real g-e2a data (7 scenes, U measured by S1): HU1 exact in 5 of 5, controls 19 and 29",
      "controls pass" in summary(tr) and "HU1 (5)" in summary(tr), summary(tr)[:300])
# ===================================================================================================== g-c1
C1P = load_preds(None, "g-c1")
c1t = table("g-c1")


def c1_world(name, raise_fn, d36_raised=4, reach=None, stage="g-c1"):
    d = synth.Dir(TMP / name, stage)
    for n, args in c1t.items():
        mm = re.fullmatch(r"(?:c|f)-(\d+)-(0x[0-9a-f]+)", n)
        P = int(mm[2], 16)
        thr0 = P - 0x22
        r = raise_fn(int(mm[1]), P)
        rc2 = (reach or (lambda n_: True))(n)
        txt = "probe x: failed: scene overflowed\n" + synth.dpm_job_text(thr0, [thr0, thr0 + 3 if rc2 else 1, thr0], partials=2, count=5)
        buf = [0] * 59
        buf[36], buf[37], buf[38] = (d36_raised if r else 3), (0x10005 if r else 0), (0x20 if r else 0)
        d.job(n, txt, 3, "ok", buf09=buf, args=args, P=hex(P))
    return Kept(d.d)


C = 0x36d
kc = c1_world("c1a", lambda V, P: P - 2 <= C)
tc, _ = G.score_c1(kc, C1P)
sc = summary(tc)
check("g-c1 world (C = 0x36d, one flip, 1350 the same): H-abs holds, last raise 0x36e, first silent 0x370, C in [0x36c, 0x36e), HP1 5 of 5",
      "H-abs holds: one flip, last raise 0x36e, first silent 0x370: C in [0x36c, 0x36e)" in sc and "HP1: 5 of 5" in sc
      and "g-c1f f-1500-0x36f" in sc, sc[:400])
check("g-c1: D36 side table: unraised jobs exact, raised jobs (held out) off by one are reported as misses",
      "D36: unraised jobs " in tc and re.search(r"unraised jobs (\d+) of \1", tc) and "raised jobs (held out) 0 of" in tc, "")
sc2 = summary(G.score_c1(c1_world("c1b", lambda V, P: P - 2 <= C or P == 0x374), C1P)[0])
check("g-c1: 0x374 raising again (raise->none, none->raise, raise->none = 3 flips): the monotone form is REFUTED",
      "monotone form REFUTED: 3 flips" in sc2, sc2[:200])
sc3 = summary(G.score_c1(c1_world("c1c", lambda V, P: (P - 2 <= C) if V == 1500 else (P - 2 <= C or P == 0x372)), C1P)[0])
check("g-c1: 1350 raising at 0x372 where 1500 does not: HP1 REFUTED at that cell", "HP1: 4 of 5" in sc3 and "REFUTED at ['0x372']" in sc3, sc3[:400])
sc4 = summary(G.score_c1(c1_world("c1d", lambda V, P: P - 2 <= C, reach=lambda n: n != "f-1500-0x370"), C1P)[0])
check("g-c1: a void cell (second run does not reach thr0) inside the flip: cannot tell", "cannot tell: a void cell lies inside the flip" in sc4, sc4[:200])
sc5 = summary(G.score_c1(c1_world("c1e", lambda V, P: P != 0x380 or True), C1P)[0])
check("g-c1: the negative control c-1500-0x380 raising: cannot tell", "cannot tell: control(s) ['c-1500-0x380']" in sc5, sc5[:200])
sc6 = summary(G.score_c1(c1_world("c1f", lambda V, P: P - 2 <= 0x2f0), C1P)[0])
check("g-c1: the positive control c-1500-0x360 not raising: cannot tell", "cannot tell: control(s) ['c-1500-0x360']" in sc6, sc6[:200])
# the step-1 cell
F1 = load_preds(None, "g-c1f")
kf = synth.Dir(TMP / "c1f", "g-c1f")
thr0 = 0x36f - 0x22
buf = [0] * 59
buf[36], buf[37], buf[38] = 3, 0x10005, 0x20
kf.job("f-1500-0x36f", "probe x: failed: scene overflowed\n" + synth.dpm_job_text(thr0, [thr0, thr0 + 3, thr0], partials=2, count=5), 3, "ok", buf09=buf)
sf = summary(G.score_c1f(Kept(kf.d), F1)[0])
check("g-c1f: a raise at the step-1 cell 0x36f fixes C in [0x36d, 0x36e)", "raise: C in [0x36d, 0x36e)" in sf, sf)
# ===================================================================================================== g-u2
U2P = load_preds(None, "g-u2")
u2t = table("g-u2")


def u2_world(name, k, s, ctl_override=None):
    d = synth.Dir(TMP / name, "g-u2")
    for n, args in u2t.items():
        P = int(n.split("-")[1], 16)
        thr0 = P - 0x22
        cnt = 1 + (287 + k - thr0) // (thr0 + s)
        if ctl_override and n in ctl_override:
            cnt = ctl_override[n]
        txt = "probe x: failed: scene overflowed\n" + synth.dpm_job_text(thr0, [thr0] * cnt + [5], partials=cnt, count=5)
        d.job(n, txt, 3, "ok", args=args, P=hex(P))
    return Kept(d.d)


tu2, _ = G.score_u2(u2_world("u2a", 6, 0x1f), U2P)
su2 = summary(tu2)
check("g-u2 world (k = 6, s = 0x1f): the pair is among those that fit, the controls hold, the first count-1 cell is named",
      "controls pass" in su2 and "s=0x1f: k in [" in su2 and re.search(r"first count-1 cell 0x", su2), su2[:300])
fits = re.search(r"s=0x1f: k in \[(\d+), (\d+)\]", su2)
check("g-u2: k = 6 lies inside the reported interval for s = 0x1f", fits and int(fits[1]) <= 6 <= int(fits[2]), su2[:300])
su2b = summary(G.score_u2(u2_world("u2b", 6, 0x1f, {"k-0xa0": 3}), U2P)[0])
check("g-u2: control P = 0xa0 reading 3: cannot tell", "cannot tell: control(s) ['k-0xa0']" in su2b, su2b[:200])
su2c = summary(G.score_u2(u2_world("u2c", 40, 0x1f), U2P)[0])
check("g-u2: a k outside 2..13 (counts the formula cannot give): the formula is REFUTED at U = 287 or controls fail",
      "REFUTED" in su2c or "cannot tell" in su2c, su2c[:200])
# ===================================================================================================== objects: T1, T2, T5, T6, T7 on real dumps
P1 = load_preds(None, "g-t1")
k1 = import_jobs(S1 / "g-e3", TMP / "t1", {"o-x64": "e3o-x64", "o-x1000": "e3o-x1000", "o-x8": "e3o-x8"})
s_t1 = summary(G.score_t1(k1, P1)[0])
check("g-t1 on S1's e3o-x64 / e3o-x1000 as the two controls: pass (present, none); the other nine cells not run",
      "controls pass" in s_t1 and "not run" in s_t1, s_t1[:200])
k1b = import_jobs(S1 / "g-e3", TMP / "t1b", {"o-x64": "e3o-x1000", "o-x1000": "e3o-x64"})
check("g-t1 with the controls swapped: cannot tell", "cannot tell" in summary(G.score_t1(k1b, P1)[0]))
# a held-out T1 row with a real object: S1's e3o-x128 (an object absent at min x 104) as o-x104 (HO-region none, HO-band '?')
k1c = import_jobs(S1 / "g-e3", TMP / "t1c", {"o-x64": "e3o-x64", "o-x1000": "e3o-x1000", "o-x104": "e3o-x128", "o-x87.5": "e3o-x8"})
s_t1c = summary(G.score_t1(k1c, P1)[0])
P1sub = {n: qs for n, qs in P1.items() if n in ("o-x64", "o-x1000", "o-x104", "o-x87.5")}
s_t1c = summary(G.score_t1(k1c, P1sub)[0])
check("g-t1 (frozen rows o-x104 and o-x87.5 only) with S1's x128 (none) as o-x104 and x8 (present) as o-x87.5: "
      "HO-region consistent in 2 (held out), HO-band consistent in 1 (its o-x104 cell is not predicted)",
      "HO-region (E542's tile rule on target regions only, low side closed) (2)" in s_t1c
      and "HO-band (a band B > 0 beyond the edge) (1)" in s_t1c, s_t1c[:400])
s_t1d = summary(G.score_t1(k1c, P1)[0])
check("g-t1: rows not run leave the hypotheses with void runs, never consistent", "void runs for" in s_t1d and "not run" in s_t1d)
P2 = load_preds(None, "g-t2")
k2 = import_jobs(S1B / "g-e3", TMP / "t2", {"z-flat099": "e3z-flat099", "z-cut-p": "e3z-cut-p", "z-cut-p05": "e3z-cut-m"})
s_t2 = summary(G.score_t2(k2, P2)[0])
check("g-t2 on S1b's flat099 and cut-p as the two controls: both hold (the frozen SH model reproduces the measured objects); "
      "S1b's cut-m shown as z-cut-p05 is refuted on every hypothesis (a different object)",
      "controls pass" in s_t2 and "refuted" in s_t2 and "HSH" in s_t2, s_t2[:500])
k2b = import_jobs(S1B / "g-e3", TMP / "t2b", {"z-flat099": "e3z-flat099", "z-cut-p": "e3z-cut-m"})
check("g-t2 with cut-m as the cut-p control: cannot tell", "cannot tell" in summary(G.score_t2(k2b, P2)[0]))
# the generator's own prediction of S1b's cut-m (A = 2, B = -1) read back through the scorer: every hypothesis consistent
pl = []
GEN.t2_predict(pl, "z-new", 2.0, -1.0, "x", "heldout", (("+w", "-w"),))
Pn = as_preds(pl + [("z-flat099", "object", "present", "E651", "control"), ("z-flat099", "depth_words", ",".join([f"0x{f32(0.995):08x}"] * 3), "E651", "control")])
k2c = import_jobs(S1B / "g-e3", TMP / "t2c", {"z-flat099": "e3z-flat099", "z-new": "e3z-cut-m"})
s_t2c = summary(G.score_t2(k2c, Pn)[0])
check("g-t2: the predictions the generator writes for z = 2x - 1 are matched by S1b's measured cut-m (set, order, prims, depth): "
      "HSH, HZZ, HPR, HDP all consistent", all(h in s_t2c for h in ("HSH", "HZZ", "HPR", "HDP")) and "refuted none" in s_t2c.split("held out:")[1].split(";")[0],
      s_t2c[:500])
P7 = load_preds(None, "g-t7")
k7 = import_jobs(S1 / "g-e3", TMP / "t7", {"e3f-ctl": "e3f-ctl", "t7-new": "e3f-r3"})
pl = []
for lab, fn in (("HF-trunc", lambda x: int(x // 1)), ("HF-round", lambda x: int(x + 0.5))):
    vs = [8195, 8199, 57347, 20487, 20483, 57351]
    pl.append(("t7-new", "packed_24bit", ";".join(str(fn((c / 1024 + 4096) * 256)) for c in vs), lab, "heldout"))
P7n = as_preds(pl + [(n, q, v, m, s) for n, qs in P7.items() if n == "e3f-ctl" for q, lst in qs.items() for v, m, s in lst])
s_t7 = summary(G.score_t7(k7, P7n)[0])
check("g-t7 on S1's e3f-r3 (step index 3 mod 4) as a held-out row: HF-round consistent, HF-trunc refuted (S1's post hoc finding)",
      "HF-round (1)" in s_t7 and "HF-trunc (1 of 1)" in s_t7, s_t7[:300])
P5 = load_preds(None, "g-t5")
k5 = import_jobs(S1B / "g-e3", TMP / "t5", {"t5-ctl-sq": "e3k-ctl", "t5-ctl-none": "e3k-i-c1e3"})
s_t5 = summary(G.score_t5(k5, P5)[0])
check("g-t5 on S1b's e3k-ctl (0.96-px square, present) and e3k-i-c1e3 (0.48-px triangle, none): controls pass, the ladder is not run: "
      "cannot tell", "cannot tell" in s_t5 and "control" not in s_t5.split("cannot tell")[1][:20], s_t5[:300])
k5b = import_jobs(S1B / "g-e3", TMP / "t5b", {"t5-ctl-sq": "e3k-i-c1e3", "t5-ctl-none": "e3k-ctl"})
check("g-t5 with the controls swapped: cannot tell (control failed)", "control(s)" in summary(G.score_t5(k5b, P5)[0]))
P6 = load_preds(None, "g-t6")
k6 = import_jobs(S1B / "g-e3", TMP / "t6", {"t6-ctl": "e3k-i-c3e5"})
s_t6 = summary(G.score_t6(k6, P6)[0])
check("g-t6 on S1b's e3k-i-c3e5 as the control: holds (0x47023555 = RZ); the ladder cells are not run (no separating cells: mixed)",
      "control t6-ctl holds" in s_t6, s_t6[:300])
k6b = import_jobs(S1B / "g-e3", TMP / "t6b", {"t6-ctl": "e3k-i-c1e4"})
check("g-t6 with a wrong control object: cannot tell", "cannot tell" in summary(G.score_t6(k6b, P6)[0]))
# a cell of the ladder with a real measured clamp job: S1b's e3k-i-c1e4 is clamp 1e-4 over w 1e-5 (stored 0x461c4000, RN = RZ?)
rz, rn = M.recip_words(0x38d1b717)
check("g-t6: S1b's measured 1e-4 clamp word 0x461c4000 is the RZ and RN word of 1/1e-4 (a cell where they agree)", rz == 0x461c4000 and rn == rz,
      f"{rz:#x} {rn:#x}")
# ===================================================================================================== void and rc rules
kv = synth.Dir(TMP / "void", "g-u1").job("u-ctl-1", "", 0, "ok").job("u-ctl-2a", "x" * 30, 124, "ok")
tv = G.score_u1(Kept(kv.d), GP)[0]
check("an empty output and an rc 124 are NODATA (never read), and the verdict is cannot tell", tv.count("NODATA") >= 2 and "cannot tell" in summary(tv), summary(tv)[:120])
sys.exit(0 if ok else 1)
