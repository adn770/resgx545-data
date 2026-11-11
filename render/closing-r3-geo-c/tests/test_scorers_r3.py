#!/usr/bin/env python3
"""The R3GC scorers (score/score_r3.py) with the frozen predictions on
  - past-run data: E730's kept depth dumps under the g-z control names (the reader and the layout, rule A's set, the controls), E779's
    kept timelines under the qf names (the count reader and the three controls): a reader check, not evidence;
  - synthetic worlds with a known truth: each world of g-z must give its rule consistent and the others refuted (A, RSTRICT, ROUND);
    a failing control must give `cannot tell`; a void job must be reported as such; each of the 20 (k, s) pairs as the truth of the
    count stages must come out as the pinned pair; a world with another formula must refute the family.
Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import gzip  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import struct  # noqa: E402
import tempfile  # noqa: E402

R3 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R3 / "score"), str(R3 / "gen"), str(R3 / "tests")]
import r3_geo as M  # noqa: E402
import score_r3 as S  # noqa: E402
import synth  # noqa: E402
from r1lib import Kept, load_preds  # noqa: E402

FX = R3 / "tests/fixtures"
ok = True
(R3 / "debug/tmp").mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(R3 / "debug/tmp")
TMP = pathlib.Path(tempfile.mkdtemp())


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def summary(text):
    return next((ln for ln in text.splitlines() if ln.startswith("SUMMARY:")), "no SUMMARY")


def table(st):
    out = {}
    for ln in (R3 / "tables" / f"{st}.txt").read_text().splitlines():
        if ln and not ln.startswith("#"):
            f = ln.split("|", 6)
            out[f[0]] = dict(set=f[1], P=f[3], knobs=f[4], args=f[6])
    return out


# ===================================================================================================== g-z
ZP = load_preds(None, "g-z")
ZT = table("g-z")


def depth_bytes(st, w, h):
    tw, th = M.tiles(w, h)
    n = 512 * ((th - 1) * (M.pitch_g(w) + 1) + tw) + 4096
    words = [M.FILL] * n
    aw, ah = M.area(w, h)
    for y in range(ah):
        for x in range(aw):
            words[M.dword_index(x, y, w, h)] = (0x3e800000 + (x + y)) if (x, y) in st else M.BG
    return struct.pack("<%dI" % n, *words)


def z_world(name, rule_of, ctl_rule="A", overrides=None, skip=()):
    """A kept dir for g-z whose truth is a rule (rule_of(name) -> rule name or an explicit set); controls follow ctl_rule."""
    d = synth.Dir(TMP / name, "g-z")
    for n, row in ZT.items():
        if n in skip:
            continue
        w, h = (int(re.search(rf"--{k} (\d+)", row["args"])[1]) for k in ("width", "height"))
        full = "--tri-full" in row["args"]
        truth = (overrides or {}).get(n)
        if truth is None:
            r = ctl_rule if row["set"] == "control" else rule_of(n)
            truth = M.band_set(r, w, h) if full else None
        if truth is None:                                                  # a triangle row: the raster of the named rule
            v = [int(t) for t in re.search(r"--tri-v (\S+)", row["args"])[1].split(",")]
            dd, _ = M.tri_raster(v, ctl_rule if row["set"] == "control" else rule_of(n), w, h)
            truth = dd
        out = f"tri: ok\ndiff: 0 of {w * h} pixels\n" if full else "tri: ok\ndiff: 3 of 612 pixels\n"
        d.job(n, out, 0, "ok", args=row["args"], dumps={"depth.1.bin": depth_bytes(truth, w, h)})
    return Kept(d.d)


r = S.score_z(z_world("zA", lambda n: "A"), ZP)[0]
s = summary(r)
check("g-z world A: controls pass, A consistent on every held-out cell, the other rules refuted where they differ",
      "controls pass" in s and "A (" in s.split("consistent")[1].split("refuted")[0] and "RSTRICT" in s.split("refuted")[1]
      and "rule A 10 of 10" in s, s[:500])
r = S.score_z(z_world("zR", lambda n: "RSTRICT"), ZP)[0]
s = summary(r)
check("g-z world RSTRICT (agrees with A at E730's .5 cells, one less at the integers): controls pass, A refuted, RSTRICT consistent",
      "controls pass" in s and "A (" in s.split("refuted")[1].split(";")[0] and "RSTRICT" in s.split("consistent")[1].split("refuted")[0], s[:500])
r = S.score_z(z_world("zRo", lambda n: "A", ctl_rule="ROUND"), ZP)[0]
check("g-z: controls following ROUND (E730's refuted rule) give cannot tell", "cannot tell: control(s)" in summary(r), summary(r)[:200])
# the whole tile stored (E730's frozen recompute observable): no control passes
tile = {(x, y) for x in range(64) for y in range(32)}
r = S.score_z(z_world("zTile", lambda n: "A", overrides={"z-ctl-34x18-x": tile}), ZP)[0]
check("g-z: a control job with the whole tile stored: cannot tell", "cannot tell" in summary(r), summary(r)[:200])
r = S.score_z(z_world("zNo", lambda n: "A", skip=("z-ctl-66x34-x",)), ZP)[0]
check("g-z: a control not run: cannot tell", "cannot tell" in summary(r) and "z-ctl-66x34-x" in summary(r), summary(r)[:200])
# a held-out job that no rule explains: reported, not scored as a hit
odd = {(x, y) for x in range(30) for y in range(11)}
r = S.score_z(z_world("zOdd", lambda n: "A", overrides={"z-w36": odd}), ZP)[0]
check("g-z: a cell no rule explains is listed ('no model's set matches') and refutes A", "z-w36" in r.split("no model's set matches")[1] and "rule A 9 of 10" in summary(r), summary(r)[:400])
# deadbeef inside the tile area -> void
d = z_world("zDead", lambda n: "A")
raw = bytearray(gzip.decompress((d.d / "z-w20.depth.1.bin.gz").read_bytes()))
struct.pack_into("<I", raw, 4 * M.dword_index(3, 3, 20, 18), M.FILL)
(d.d / "z-w20.depth.1.bin.gz").write_bytes(gzip.compress(bytes(raw)))
r = S.score_z(d, ZP)[0]
check("g-z: a tile-area dword still 0xdeadbeef is NODATA (the store did not write whole tiles), never a hit or a miss",
      "NODATA: 1 tile-area dwords still 0xdeadbeef" in r and "void jobs ['z-w20']" in summary(r), summary(r)[:300])
# a missing diff line, an empty output, rc 124, a hang -> NODATA
d = z_world("zVoid", lambda n: "A")
(d.d / "z-w36.txt.gz").write_bytes(gzip.compress(b"tri: ok\n" * 5))
cs = (d.d / "cases.tsv").read_text().splitlines()
cs = [ln.replace("\t0\tok\t", "\t124\tok\t") if ln.startswith("z-h28\t") else ln for ln in cs]
(d.d / "cases.tsv").write_text("\n".join(cs) + "\n")
r = S.score_z(Kept(d.d), ZP)[0]
check("g-z: no `diff: 0 of W*H pixels` line and an rc 124 are NODATA", "z-w36" in summary(r) and "z-h28" in summary(r) and "NODATA" in r, summary(r)[-200:])
d = z_world("zHang", lambda n: "A")
(d.d / "z-h20.dmesg.gz").write_bytes(gzip.compress(b"sgxfive: job 3 hung, recovering"))
r = S.score_z(d, ZP)[0]
check("g-z: a hang line in the job's kernel log is NODATA", "z-h20" in summary(r) and "NODATA: class" in r, summary(r)[-200:])
# triangle rows
d = z_world("zTri", lambda n: "A", overrides={"z-tri-in": {(x, y) for x in range(0, 5) for y in range(0, 5)}})
r = S.score_z(d, ZP)[0]
check("g-z: a stored set that differs from the raster of z-tri-in is reported OUTSIDE (the raster model refuted, the band verdict unaffected)",
      "z-tri-in: A raster" in r and "OUTSIDE" in r.split("z-tri-in: A raster")[1].split("\n")[0], r.split("\n")[-3][:200])
r = S.score_z(z_world("zTri2", lambda n: "A"), ZP)[0]
check("g-z: the raster of z-tri-in and z-tri-cross (rule A) is consistent in an A world", "A raster (2)" in summary(r), summary(r)[:500])

# ---- E730's real dumps under the control names
d = synth.Dir(TMP / "z730", "g-z")
ren = {"gb-34x18-rampx": "z-ctl-34x18-x", "gb-34x18-rampy": "z-ctl-34x18-y", "gb-66x34-rampx": "z-ctl-66x34-x"}
for old, new in ren.items():
    row = ZT[new]
    d.job(new, gzip.decompress((FX / f"e730/{old}.txt.gz").read_bytes()).decode(errors="replace"), 0, "ok", args=row["args"],
          dumps={"depth.1.bin": gzip.decompress((FX / f"e730/{old}.depth.1.bin.gz").read_bytes())})
r = S.score_z(Kept(d.d), ZP)[0]
check("E730's real dumps for 34x18 (x, y) and 66x34 pass as the g-z controls (924, 924, 3444 and rule A's set)",
      "controls pass" in summary(r) and "cannot tell" not in summary(r), summary(r)[:300])
check("... through the tool's own `diff: 0 of 612 pixels` text of E730's run", "NODATA" not in r, r[:200])

# ===================================================================================================== g-qf, g-qh
FP, HP = load_preds(None, "g-qf"), load_preds(None, "g-qh")
FT, HT = table("g-qf"), table("g-qh")


def jobtext(P, count, U=None, knob=None, extra=""):
    """One DPM job text: thr0 = P - 0x22 as the 0x0624 value, `count` partial renders of 20 pages (or the scene gate's U pages)."""
    if U is not None:
        return synth.dpm_job_text(knob if knob is not None else P - 0x22, [U], 0, with_072c=True, extra=extra)
    return synth.dpm_job_text(knob if knob is not None else P - 0x22, [20] * (count + 1), count, with_072c=True, extra=extra)


def q_world(name, tbl, preds, truth, stage, overrides=None, skip=(), gate=None, texts=None):
    """truth(U, P) -> count; gate: {scene: U measured at P = 0x422}."""
    d = synth.Dir(TMP / name, stage)
    for n, row in tbl.items():
        if n in skip:
            continue
        P = int(row["P"], 16)
        if n.startswith("qc-"):
            sc = n[3:]
            txt = jobtext(P, 0, U=(gate or {}).get(sc, M.SCENES[sc][0]))
            d.job(n, txt, 0, "ok", args=row["args"], P=row["P"])
            continue
        sc = re.fullmatch(r"qh-(s\d+)-0x[0-9a-f]+", n)
        U = M.SCENES[sc[1]][0] if sc else M.U_DEFAULT
        cnt = (overrides or {}).get(n, truth(U, P))
        txt = (texts or {}).get(n) or jobtext(P, cnt)
        last = 2 if "-n 2" in row["args"] else 1
        d.job(n, (f"tri 4096x4096 #{last}: overflowed\n" if cnt else "") + txt, 0, "ok", args=row["args"], P=row["P"])
    return Kept(d.d)


worlds = {}
for (k_, s_) in M.PAIRS:
    tr = lambda U, P, k_=k_, s_=s_: M.count(U, k_, s_, P)       # noqa: E731
    f = q_world(f"qf_{k_}_{s_}", FT, FP, tr, "g-qf")
    h = q_world(f"qh_{k_}_{s_}", HT, HP, tr, "g-qh")
    rf = S.score_qf(f, FP)
    rh = S.score_qh(h, HP, f.d)
    worlds[(k_, s_)] = (rf, rh)
bad_f = [p for p, (rf, rh) in worlds.items() if p not in rf[1].get("left", [])]
check("g-qf: each of the 20 pairs as the truth: the pair is among the survivors", not bad_f, str(bad_f))
check("g-qf: the survivors of a world are exactly the pairs that predict the same counts at U = 287 (classes of 1 or 2)",
      all(1 <= len(rf[1]["left"]) <= 2 for rf, _ in worlds.values()))
bad_h = [p for p, (rf, rh) in worlds.items() if rh[1].get("survive") != [p]]
check("g-qh: each of the 20 pairs as the truth is pinned exactly (the held-out cells separate every pair)", not bad_h, str(bad_h[:3]))
t = worlds[(-3, 29)][1][0]
check("g-qh SUMMARY names the pinned pair", "pinned (k, s) = (-3, 29)" in summary(t), summary(t)[:300])
check("g-qf SUMMARY lists the controls, the survivors and the class count", "controls pass; monotone; 2 of 20" in summary(worlds[(-3, 29)][0][0]) or "1 of 20" in summary(worlds[(-3, 29)][0][0]),
      summary(worlds[(-3, 29)][0][0])[:300])
# a world with another formula: the family is refuted by the fit cells or the held-out ones
tr2 = lambda U, P: 1 + max(0, U - (P - 0x22)) // (2 * (P - 0x22) + 5)                                   # noqa: E731
f2 = q_world("qf_other", FT, FP, lambda U, P: tr2(U, P) if P not in (0xa0, 0xb0, 0xa3) else {0xa0: 2, 0xb0: 1, 0xa3: 1}[P], "g-qf")
s = summary(S.score_qf(f2, FP)[0])
check("g-qf: counts of another formula: controls pass (they are E625's), the family is REFUTED or monotone-failed", "REFUTED" in s or "cannot tell" in s, s[:300])
# the held-out stage refutes a family that the fit stage let through
f3 = q_world("qf_p", FT, FP, lambda U, P: M.count(U, -3, 29, P), "g-qf")
h3 = q_world("qh_other", HT, HP, lambda U, P: M.count(U, -3, 29, P) + (1 if P == 0x79 else 0), "g-qh")
s = summary(S.score_qh(h3, HP, f3.d)[0])
check("g-qh: one held-out count off by one from every pair: REFUTED or fewer pairs, never `pinned` to (-3, 29)", "pinned (k, s) = (-3, 29)" not in s and ("REFUTED" in s or "survive" in s or "pinned" in s), s[:300])
h4 = q_world("qh_agree", HT, HP, lambda U, P: M.count(U, -3, 29, P) + (1 if P in (0x52, 0x7b) else 0), "g-qh")
s = summary(S.score_qh(h4, HP, f3.d)[0])
check("g-qh: the cells where all pairs agree miss -> the family fails at the new U: REFUTED with the agree-cell misses listed",
      "REFUTED" in s and "agree-cell misses" in s, s[:400])
# controls
f5 = q_world("qf_c", FT, FP, lambda U, P: M.count(U, -3, 29, P), "g-qf", overrides={"qf-0xa0": 1})
s = summary(S.score_qf(f5, FP)[0])
check("g-qf: E625's 0xa0 control reading 1 instead of 2: cannot tell", "cannot tell: control(s) ['qf-0xa0']" in s, s[:300])
f6 = q_world("qf_m", FT, FP, lambda U, P: M.count(U, -3, 29, P), "g-qf", overrides={"qf-0x6d": 1, "qf-0x6e": 3})
s = summary(S.score_qf(f6, FP)[0])
check("g-qf: a count that rises with P (stop condition) gives cannot tell", "not monotone" in s, s[:300])
f7 = q_world("qf_k", FT, FP, lambda U, P: M.count(U, -3, 29, P), "g-qf")
txts = {"qf-0x6d": jobtext(0x6d, 2, knob=0x30)}
f7 = q_world("qf_k2", FT, FP, lambda U, P: M.count(U, -3, 29, P), "g-qf", texts=txts)
t = S.score_qf(f7, FP)[0]
check("g-qf: a job whose 0x0624 read 0x30, not P - 0x22, is NODATA (the knob did not land), never a count",
      "knob did not land" in t and "qf-0x6d" in summary(t), summary(t)[-200:])
f8 = q_world("qf_hang", FT, FP, lambda U, P: M.count(U, -3, 29, P), "g-qf")
(f8.d / "qf-0x44.dmesg.gz").write_bytes(gzip.compress(b"sgxfive: job 9 hung, recovering"))
t = S.score_qf(f8, FP)[0]
check("g-qf: a hung job is NODATA and excluded", "qf-0x44" in summary(t) and "NODATA: class" in t, summary(t)[-160:])
# g-qh scene gate and the lost kick
h9 = q_world("qh_gate", HT, HP, lambda U, P: M.count(U, -3, 29, P), "g-qh", gate={"s438": 430})
s = summary(S.score_qh(h9, HP, f3.d)[0])
t = S.score_qh(h9, HP, f3.d)[0]
check("g-qh: the scene gate s438 reading U = 430 (not E773's 438) is FAILED and its cells are not scored", "scene gate qc-s438: U 430 (E773: 438) FAILED" in t and "qh-s438" not in s.split("pinned")[0], s[:300])
n438 = [n for n in HT if n.startswith("qh-s438")][0]
h10 = q_world("qh_kick", HT, HP, lambda U, P: M.count(U, -3, 29, P), "g-qh", texts={n438: "tri 4096x4096 #1: overflowed\ntri 4096x4096 #2: overflowed\n" + jobtext(int(HT[n438]["P"], 16), 3)})
h10.d
t = S.score_qh(h10, HP, f3.d)[0]
check("g-qh: a scene with -n 2 whose render #1 overflowed (kicks lost) is void by E773's rule", "a kick lost" in t or f"{n438}" in summary(t), summary(t)[-200:])
h11 = q_world("qh_nofit", HT, HP, lambda U, P: M.count(U, -3, 29, P), "g-qh")
t = S.score_qh(h11, HP, TMP / "nonexistent")[0]
check("g-qh without the fit stage's data: cannot tell", "cannot tell" in summary(t), summary(t)[:200])

# ---- E779's real timelines under the qf control names (the count reader on hardware data)
d = synth.Dir(TMP / "q779", "g-qf")
for new, old in (("qf-0xa0", "k-0xa0"), ("qf-0xb0", "k-0xb0"), ("qf-0xa3", "k-0xa3")):
    d.job(new, gzip.decompress((FX / f"e779/{old}.txt.gz").read_bytes()).decode(errors="replace"), 0, "ok", args=FT[new]["args"], P=FT[new]["P"])
rf = S.score_qf(Kept(d.d), FP)
check("E779's real timelines for P = 0xa0 (2), 0xb0 (1), 0xa3 (1) read as the controls (no control failure)",
      "cannot tell: control" not in summary(rf[0]) and "no usable fit cell" in summary(rf[0]), summary(rf[0])[:300])
import subprocess  # noqa: E402
rr = subprocess.run([sys.executable, str(R3 / "score/score_r3.py")], capture_output=True, text=True)
check("score_r3.py without arguments prints its usage and exits 2", rr.returncode == 2 and "STAGE" in rr.stdout)
sys.exit(0 if ok else 1)
