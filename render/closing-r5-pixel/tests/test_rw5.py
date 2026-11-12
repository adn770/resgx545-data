#!/usr/bin/env python3
"""g5-rw (Q230) offline tests: the design (48 rows, every w exact in float32, every vertex inside the viewport, the dense table's 60
new mantissas and its sha256 split, the m rows' mantissas equal R4's, 11 RZ + 1 among the 42 frozen deltas, the controls' known
words), every program run in sgx-sim (vtx_zws.s and R4's vtx_zw.s: o0 = S x, o1 = S y, o2 = 0, o3 = w exactly at the tool's three
vertices; R4's reused programs equal a rebuild from R4's template), and the scorer on mock worlds whose dumps are REAL kept objects
rewritten by tests/fake_rw.py from each staged program run in sgx-sim (argv-driven): a hidden mantissa rule (H-MANT held), a rule that
follows the exponent (refuted), pure RZ (the controls fail), R4's unscaled design (the q jobs clip to 7 vertices: FAILED shape, part a's
gate stops), a void job, a replicate that differs (not deterministic).  Prints ok/FAIL; exit 1 on any FAIL."""
import collections
import gzip
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
R5 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R5 / "gen"), str(R5 / "score"), str(R5 / "tests")]
(R5 / "debug/tmp").mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(R5 / "debug/tmp")
import fake_rw as FR  # noqa: E402
import r4lib as L  # noqa: E402
import r5common as K  # noqa: E402
import r5_rw  # noqa: E402
import rwdesign5 as D  # noqa: E402
import score_r5 as SR  # noqa: E402
import score_rw5 as S  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


rows = D.all_rows()
check("48 rows: 6 controls, 6 q, 14 m, 2 replicates, 20 dense", len(rows) == 48 and collections.Counter(p["kind"] for p in rows)
      == {"control-r4": 4, "control-new": 2, "q": 6, "m": 14, "replicate": 2, "d": 20})
check("every w, C, D, S and S x, S y exact in float32", all(D.exact(p) for p in rows))
check("every vertex of every row inside the viewport [0, 64]", all(D.viewport_ok(p["w"], p["S"]) for p in rows))
r4 = D.r4_words()
check("m rows: the mantissas of R4's rw-01..rw-14, w at scale 1/2 (m-01..07) and 16 (m-08..14)",
      all((p["words"][v] & 0x7fffff) == (r4[(p["r4"], v)][0] & 0x7fffff) for p in D.m_rows() for v in range(3))
      and {float(p["S"]) for p in D.m_rows()[:7]} == {0.5} and {float(p["S"]) for p in D.m_rows()[7:]} == {16.0})
dl = [r4[(p["r4"], v)][2] - r4[(p["r4"], v)][1] for p in D.m_rows() for v in range(3)]
check("the 42 frozen m deltas are R4's words: 11 RZ + 1 and 31 RZ", dl.count(1) == 11 and dl.count(0) == 31, str(collections.Counter(dl)))
dw = D.dense_words()
kd = D.known_deltas()
check("dense table: 60 distinct words, 60 new mantissas (none read before, none of R4's), the 32 odd k of 1 + k/64 among the designed",
      len(set(dw)) == 60 and len({w & 0x7fffff for w in dw}) == 60 and not any((w & 0x7fffff) in kd for w in dw)
      and all(any((p["words"][v] & 0x7fffff) == k << 17 for p in D.d_rows() for v in (0, 1)) for k in range(1, 64, 2)))
check("dense table: scales 1/4, 1/2, 1, 2, 4, four jobs each", collections.Counter(float(p["S"]) for p in D.d_rows()) == {0.25: 4, 0.5: 4, 1.0: 4, 2.0: 4, 4.0: 4})
sp = D.split()
check("the dense split: 30 FIT, 30 HELD OUT, deterministic", list(sp.values()).count("FIT") == 30 and sp == D.split())
c = {p["name"]: p for p in D.controls()}
check("controls: R4's known words; rw-k4 RZ(1/0.3), rw-k5 0x3fb6db6e (E795: one ulp above RZ at w 0.7)",
      c["rw-k5"]["known"] == (0x3fb6db6e,) * 3 and c["rw-k4"]["known"] == (D.rz_word(D.bits(0.3)),) * 3 and c["rw-k1"]["known"][1] == 0x3de38e39)
check("H-MANT predicts 4 of the 18 q words (rw_band.out: 1.1875, 1.4375, 1.375, 1.625 RZ)",
      sum(1 for p in D.q_rows() for b in p["words"] if D.hmant(b) is not None) == 4)
# ---------------------------------------------------------------- every program in sgx-sim
f2b = lambda f: struct.unpack("<I", struct.pack("<f", f))[0]
bad = []
for p in rows:
    for i in range(3):
        o = FR.vertex(R5 / "bins" / f"{p['name']}.bin", float(D.VX[i]), float(D.VY[i]))
        want = {"o0": D.bits(p["S"] * D.VX[i]), "o1": D.bits(p["S"] * D.VY[i]), "o2": 0, "o3": p["words"][i]}
        if any(o.get(k_) != v for k_, v in want.items()):
            bad.append((p["name"], i, {k_: hex(o.get(k_, 0)) for k_ in want}))
check("every g5-rw program (48) in sgx-sim: o0 = S x, o1 = S y, o2 = 0, o3 = w exactly at the three vertices", not bad, str(bad[:2]))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="rw-rebuild-"))
same = True
for p in rows:
    if p["template"] == "vtx_zw":
        K.probe._assemble(r5_rw.text_of(p), tmp / f"{p['name']}.bin")
        same &= (tmp / f"{p['name']}.bin").read_bytes() == (R5 / "bins" / f"{p['name']}.bin").read_bytes()
check("R4's reused programs (rw-k0..k3, rw-07, rw-10) equal a rebuild from R4's template and R4's C, D", same)
# ---------------------------------------------------------------- mock worlds through the fake tool's dumps
preds = SR.preds_rw()
HEAD = "name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tnote"
CACHE = {}


def kept(stage, rule, void=(), patch=None):
    d = pathlib.Path(tempfile.mkdtemp(prefix=f"{stage}-{rule}-"))
    lines = [HEAD]
    for ln in (R5 / "tables" / f"{stage}.txt").read_text().splitlines():
        if not ln or ln.startswith("#"):
            continue
        n = ln.split("|")[0]
        if n in void:
            lines.append("\t".join([n, stage, "x", "safe", "x", "x", "x", "124", "fail", "-"]))
            continue
        key = (n, rule)
        if key not in CACHE:
            w = pathlib.Path(tempfile.mkdtemp(prefix="fk-"))
            args = ["probe", "--temps", "8", "--pixels", "--tri", "vtxuse", "--width", "64", "--height", "64", "--vtx-coords", "2",
                    "--dump-render", str(w), "--slot", f"pixel={R5}/bins/pix_green.bin", str(R5 / "bins" / f"{n}.bin")]
            r = subprocess.run([sys.executable, str(R5 / "tests/fake_rw.py")] + args, capture_output=True, text=True,
                               env={"FAKE_RW_RULE": rule, "PATH": "/usr/bin:/bin"})
            CACHE[key] = (r.stdout, (w / f"{n}.param.bin").read_bytes(), (w / f"{n}.tadata.bin").read_bytes())
        txt, pb, tb = CACHE[key]
        if patch and n in patch:
            pb = patch[n](pb)
        lines.append("\t".join([n, stage, "x", "safe", "x", "x", "x", "0", "ok", "-"]))
        for suf, data in ((".txt.gz", txt.encode()), (f".{n}.param.bin.gz", pb), (f".{n}.tadata.bin.gz", tb)):
            with gzip.open(d / f"{n}{suf}", "wb") as f:
                f.write(data)
    (d / "cases.tsv").write_text("\n".join(lines) + "\n")
    return L.Kept(d)


def world(rule, **kw):
    ka, kb = kept("g5-rwa", rule, **kw), kept("g5-rw", rule, **kw)
    t, r = S.score(ka, kb, preds)
    g, _ = S.gate_a(ka, preds)
    return t, r, g


t, r, g = world("hmant")
check("hidden mantissa rule: controls pass, part a's gate passes, every shape held, H-MANT held 42 of 42",
      g.ok and r["gate"].ok and r["verdict"].startswith("H-MANT held: 42 of 42") and all(v is True for v in r["shape"].values()), t.splitlines()[-1][:140])
check("  every word RZ or RZ + 1 (126 words: 18 q, 42 m, 6 replicate, 60 dense)", sum(1 for x in r["recs"] if x[6] is True) == 126 and
      len(r["recs"]) == 126, str(len(r["recs"])))
check("  the q words with a read mantissa held (4)", "H-MANT on the q words with a read mantissa: 4 held" in t)
t, r, g = world("exp")
check("a rule that follows the exponent (one ulp more at w >= 16): H-MANT REFUTED on the m-08..m-14 words", r["verdict"].startswith("H-MANT REFUTED")
      and r["hmant"].failed == 21, r["verdict"][:120])
t, r, g = world("rz")
check("pure RZ: the controls that know an RZ + 1 word fail (rw-k1, rw-k3, rw-k5): part a's gate FAILED, H-MANT cannot tell",
      not g.ok and g.failed and "cannot tell" in r["verdict"], str(g.problems))
t, r, g = world("noscale")
qs = {n: v for n, v in r["shape"].items() if n.startswith("q-")}
check("R4's unscaled design: the six q jobs clip (7 vertices): FAILED shape, never cannot tell; part a's gate FAILED (>= 3)",
      all(v is False for v in qs.values()) and not g.ok and "fewer than 3 q jobs FAILED shape" in g.failed, f"{qs} {g.problems}")
check("  printed as FAILED shape", "q-16: FAILED shape (7 vertices" in t, [x for x in t.splitlines() if x.startswith("q-16:")])
t, r, g = world("hmant", void=("m-03",))
check("a void m job: H-MANT cannot tell (3 m words not read), never a pass", "cannot tell: 3 m words" in r["verdict"], r["verdict"])


def bump(pb):
    b = bytearray(pb)
    w = struct.unpack_from("<I", b, 12)[0]
    struct.pack_into("<I", b, 12, w ^ 1)
    return bytes(b)


t, r, g = world("hmant", patch={"rw-10": bump})
check("a replicate that differs from R4 (rw-10's first word): H-MANT cannot tell, not deterministic", "not deterministic" in r["verdict"], r["verdict"])
t, r, g = world("hmant", patch={"rw-k5": bump})
check("a control word off (rw-k5): part a's gate FAILED: the driver stops before g5-rw", not g.ok and "rw-k5" in " ".join(g.failed), str(g.problems))
shutil.rmtree(tmp, ignore_errors=True)
sys.exit(0 if ok else 1)
