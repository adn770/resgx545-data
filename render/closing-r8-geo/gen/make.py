#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r8-geo's generator. Writes tables/STAGE.txt, predictions/STAGE.tsv and the per-pixel
predictions predictions/STAGE/NAME[.MODEL].txt of the four stages (cube, seam, addr, vdm), the
probe programs bins/cube-*.bin and bins/addr-*.bin (assembled from the pinned p1141 template by
resgx545's usse-asm) and copies of the published vdm programs (render/closing-s1/bins, pinned).

  python3 gen/make.py          write everything (refuses nothing it cannot regenerate)
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now
Inputs: RESGX545_DATA (default /Users/jtorra/src/resgx545-data), RESGX545_MAIN (default
/Users/jtorra/src/resgx545, for tools/usse-asm/usse-asm)."""
import hashlib
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import addr as A  # noqa: E402
import cube as C  # noqa: E402
import seam as S  # noqa: E402
import texprog as T  # noqa: E402
import vdm as V  # noqa: E402

DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
MAIN = os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545")
ASM = os.path.join(MAIN, "tools/usse-asm/usse-asm")
TEMPLATE = "texture/p1141/templates/tx_map.s"
E726_XN = "texture/p1141/out-hw/p1141tex-dumps/tex-h-cube/cu-xn.txt.gz"
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
PROBE = 'probe --temps 32 --coords --pixels'


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def tline(*f):
    return "\t".join(str(x) for x in f) + "\n"


def cube(files):
    R = C.rule()
    tpl = open(os.path.join(DATA, TEMPLATE)).read()
    rows, pred = [], [HEAD]
    import gzip
    e726 = T.pixels(gzip.open(os.path.join(DATA, E726_XN), "rt").read())
    with tempfile.TemporaryDirectory() as td:
        for name, st, spec, n, t0, kind in C.jobs():
            text = T.program_text(tpl, spec, C.twords(n, t0), C.SMP)
            files[f"bins/{name}.bin"] = T.assemble(ASM, text, os.path.join(td, name + ".bin"))
            files[f"bins/{name}.s"] = text.encode()
            knobs = "reads:pixels" if st == "control" else "-"
            rows.append(f'{name}|{st}|safe|{knobs}|t4|{PROBE} "$S/bins/{name}.bin"')
            pp = C.pixel_predictions(R, spec, n)
            if kind == "control":
                body = "".join("%d %d ok 0x%08x\n" % (x, y, e726[(x, y)])
                               for y in range(T.H) for x in range(T.W))
                files[f"predictions/cube/{name}.txt"] = body.encode()
                pred.append(tline(name, "pixels_sha", sha(body), "E726", st,
                                  "E726 cu-xn kept pixels (texture/p1141 tex-h-cube), E844's control"))
                agree = sum(1 for p, (s, v) in pp.items() if s == "ok" and v == e726[p])
                pred.append(tline(name, "rule_agrees", agree, "RULE", st,
                                  "q284_rule.json on E726's fit job (fit, 2048 of 2048)"))
                continue
            body = "".join("%d %d %s %s\n" % (x, y, pp[(x, y)][0],
                                              "-" if pp[(x, y)][1] is None else "0x%08x" % pp[(x, y)][1])
                           for y in range(T.H) for x in range(T.W))
            files[f"predictions/cube/{name}.txt"] = body.encode()
            cnt = {k: sum(1 for s, _ in pp.values() if s == k) for k in ("ok", "face-tie", "texel-tie")}
            src = "q284_rule.json (sha256 %s..., frozen offline before this session)" % C.RULE_SHA[:8]
            pred.append(tline(name, "pixels_sha", sha(body), "RULE", st, src))
            for k, v in cnt.items():
                pred.append(tline(name, k, v, "RULE", st, src))
            if kind == "edge":
                e = C.edge_cells(R, spec, n)
                body = "".join("%d %d %d %s\n" % (x, y, f, k) for (x, y), (f, k) in sorted(e.items()))
                files[f"predictions/cube/{name}.edge.txt"] = body.encode()
                pred.append(tline(name, "edge_sha", sha(body), "EDGE", st, "gen/cube.py edge_cells"))
                nout = sum(1 for f, k in e.values() if k == "out")
                pred.append(tline(name, "out_g", "own", "H-CLAMP", st,
                                  f"the filter clamped inside the face: {nout} out pixels read G = own face"))
                pred.append(tline(name, "out_g", "other", "H-SEAM", st,
                                  f"taps from the neighbour face [infer]: {nout} out pixels read G != own face"))
    return rows, pred


def seam(files):
    rows = []
    for name, st, w, h, mode, te, verts in S.jobs():
        knobs = "expectdiff reads:pixels" if st == "control" else "expectdiff"
        rows.append(f"{name}|{st}|safe|{knobs}|t4|" + " ".join(S.args(w, h, mode, te, verts)))
    tsv = open(os.path.join(S.o8_checked(), "q141_r8pred.tsv")).read()
    return rows, [tsv]


def addr(files):
    tpl = open(os.path.join(DATA, TEMPLATE)).read()
    rows, pred = [], [HEAD]
    with tempfile.TemporaryDirectory() as td:
        for name, st, axis, mode in A.jobs():
            text = T.program_text(tpl, A.coords(axis), A.twords(axis, mode), A.SMP)
            files[f"bins/{name}.bin"] = T.assemble(ASM, text, os.path.join(td, name + ".bin"))
            files[f"bins/{name}.s"] = text.encode()
            knobs = "reads:pixels" if st == "control" else "-"
            rows.append(f'{name}|{st}|safe|{knobs}|t4|{PROBE} --scratch-pages {A.PAGES} "$S/bins/{name}.bin"')
            models = ("REPEAT",) if mode == 0 else A.MODELS
            for m in models:
                img = A.image(axis, mode, "H-MASK-V" if m == "REPEAT" else m)
                body = "".join("%d %d %s\n" % (x, y, "-" if img[(x, y)] is None else img[(x, y)])
                               for y in range(T.H) for x in range(T.W))
                files[f"predictions/addr/{name}.{m}.txt"] = body.encode()
                why = ("E033/E565 mode 0 repeat, base page 12" if m == "REPEAT"
                       else "gen/addr.py rival, nothing fitted")
                pred.append(tline(name, "image_sha", sha(body), m, st, why))
    return rows, pred


def vdm(files):
    for b in V.BINS:
        files[f"bins/{b}"] = open(os.path.join(DATA, V.BINS_FROM, b), "rb").read()
    rows, pred = [], [HEAD]
    for name, st, n, v, r, twin in V.jobs():
        knobs = "after reads:pixels" if st == "control" else "after"
        rows.append(f"{name}|{st}|risky|{knobs}|t4|" + " ".join(
            '"%s"' % a if "$" in a else a for a in V.args(n, v, r)))
        if twin:
            pred.append(tline(name, "twin", twin, "all", st, "the natural job run before it"))
        for m, val in V.predicted(name, r, n, twin).items():
            pred.append(tline(name, "vs_twin", val, m, st, f"twin {twin}; gen/vdm.py"))
        pred.append(tline(name, "job", "ok", "all", st, "E703: 10 of 10 forced jobs completed"))
    return rows, pred


HEADERS = {
    "cube": """#stage cube
#limit 0
# R8-2, Q284 (decision R8-4 (a)): TEXTYPE 2 sampled by smp3d in E726/E844's probe form (64 x 32 fill, scratch dword i =
# 0xD0000000 | i). Frozen: gen/q284_rule.json (sha256 52162471..., fitted on E726, held out offline on E844 4090/4096) for
# (a) 4 new off-axis programs at 16 x 16 and (b) 8 x 8 and 32 x 32 faces (T1 0x4c007007 / 0x4c01f01f, E725's size field;
# faces N * N dwords apart), every pixel's dword in predictions/cube/NAME.txt, face ties and texel ties at a |ma| that is
# no power of two "cannot tell". (c) exploratory readings: two face-tie sweeps (|w| = |u| in column 32) and four texel-tie
# grids at |ma| 1.75, 1.625, 1.875, 0.90625. (d) bilinear (T0 0x07fe1400) at a face edge: H-CLAMP (G byte = own face) vs
# H-SEAM (G != own face) on the "out" pixels, gated by the "in" pixels' blend. Control: E726's cu-xn program (its 2048
# pixels known, E844 read them again byte for byte). Stop: any fault or hang (none in E726/E844's 11 cube jobs); the
# second row without its pixel rows (hook_check).""",
    "seam": """#stage seam
#limit 0
# R8-1, Q141 (decision R8-3 (a)): tri-full and single-triangle colour renders with E504's pokes (cmd:1 CR_TE_AA, cmd:10
# and cmd:16 E507's sample words, cmd:13 the MSAA mode), held out at sizes and slopes never run. Frozen per job: the O8
# R8-1 table (predictions/seam.tsv = gen/o8/q141_r8pred.tsv byte for byte): holes or stored pixels under the landed region
# model (H-REGION, msaa_model.predict unchanged) and its null H-UNION (halves=False). Controls that can fail: tri-full
# 64 x 64 mode 1 TE 0x60000000 (64 holes: E502's configuration as a colour job) and mode 2 TE 0x20000000 (no hole, E504's
# control). expectdiff: a hole is a diff of the tool's reference check (rc 1 with its diff line). Stop: any fault or hang
# (none in E502/E504/E727's 134 jobs); the second row without its pixel rows.""",
    "addr": """#stage addr
#limit 0
# R8-5, Q177: T0 address modes 4 to 7 on E565's 16 x 16 twiddled texture at page 12 of a 24-page named scratch (T2 word
# 0x5CAFC000, --scratch-pages 24), u then v swept over 128 positions at one texel a step. Frozen rivals (gen/addr.py, no
# fit): H-MASK-V, H-NOMASK-PAGE, H-BORDER; predictions/addr/NAME.MODEL.txt. Control that can fail: mode 0 on u (the
# repeat image). Every read names its dword, so a row no rival takes is tabled per index. Stop: any fault or hang (none in
# E565's 37 jobs); the second row without its pixel rows.""",
    "vdm": """#stage vdm
#limit 0
# R8-4, Q271: E703's capacity form with VDM word 7 SET (--vdm 7=V) instead of xored. Frozen (gen/vdm.py): forced =
# natural leaves the image of its natural twin (H-FORCE-NEUTRAL; N = 8 V = 4, N = 2 V = 2); forced = natural + 1 at N = 2
# V = 2: H-COUNT (same image) vs H-LAYOUT (changed), twice; forced below natural at N = 8 V = 8 a reading. The forced =
# natural rows are the controls (they can fail: a forcing that breaks a job changes the image), each after its natural
# twin (set reference). Risky as E703's 10 jobs (none hung): last stage, health after every job (after), any fault or
# hang stops it.""",
}


def build():
    files = {}
    for stage, fn in (("cube", cube), ("seam", seam), ("addr", addr), ("vdm", vdm)):
        rows, pred = fn(files)
        files[f"tables/{stage}.txt"] = (HEADERS[stage] + "\n" + "\n".join(rows) + "\n").encode()
        files[f"predictions/{stage}.tsv"] = "".join(pred).encode()
    return files


def main(argv):
    files = build()
    check = "--check" in argv
    bad = []
    for rel, b in sorted(files.items()):
        p = os.path.join(KP, rel)
        if check:
            if not os.path.exists(p) or open(p, "rb").read() != b:
                bad.append(rel)
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b)
    if check:
        for d in ("predictions/cube", "predictions/addr", "bins"):
            for n in os.listdir(os.path.join(KP, d)):
                if f"{d}/{n}" not in files:
                    bad.append(f"{d}/{n} (not generated)")
        print("\n".join("differs: " + b for b in bad) or f"gen current: {len(files)} files")
        return 1 if bad else 0
    print(f"wrote {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
