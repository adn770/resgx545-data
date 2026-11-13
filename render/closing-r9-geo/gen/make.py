#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r9-geo's generator (r8-geo's gen/make.py, resgx545-data render/closing-r8-geo, copied
and extended). Writes tables/STAGE.txt, predictions/STAGE.tsv and the per-pixel predictions
predictions/STAGE/NAME.MODEL.txt of the four stages (seam1, seam4, cube2, addr2) and the probe
programs bins/cube-*.bin and bins/addr-*.bin (assembled from the pinned p1141 template by
resgx545's usse-asm; the .s text beside each).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now
Inputs: RESGX545_DATA (default /Users/jtorra/src/resgx545-data), RESGX545_MAIN (default
/Users/jtorra/src/resgx545, for tools/usse-asm/usse-asm)."""
import gzip
import hashlib
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import addr as A  # noqa: E402
import cube as C  # noqa: E402
import seam as S  # noqa: E402
import texprog as T  # noqa: E402

DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
MAIN = os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545")
ASM = os.path.join(MAIN, "tools/usse-asm/usse-asm")
TEMPLATE = "texture/p1141/templates/tx_map.s"
E726_XN = "texture/p1141/out-hw/p1141tex-dumps/tex-h-cube/cu-xn.txt.gz"
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
PROBE = 'probe --temps 32 --coords --pixels'
EMPTY_SHA = hashlib.sha256(b"").hexdigest()
F4 = "f4-"      # seam4's row names: the O8 names with this prefix


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def tline(*f):
    return "\t".join(str(x) for x in f) + "\n"


# ---- seam1 and seam4 -------------------------------------------------------------------------
SEAM1_KNOB = "dbg:render_rgn_arrays=1"


def seam_row(name, st, w, h, mode, te, verts, knob, reads="pixels,jobok"):
    words = ["expectdiff"] + ([f"reads:{reads}"] if st == "control" else []) + (
        [knob] if knob else [])
    return f"{name}|{st}|safe|{' '.join(words)}|t4|" + " ".join(S.args(w, h, mode, te, verts))


def seam1(files):
    rows = [seam_row(n, st, w, h, m, te, v, SEAM1_KNOB) for n, st, w, h, m, te, v in S.jobs()]
    tsv = open(os.path.join(S.o8_checked(), "q141_r8pred.tsv")).read()
    return rows, [tsv]


def seam4_set(st, name):
    """seam4's set of an O8 row: E502's control is a held-out row here (H-FULL4 parts it)."""
    return "heldout" if name == "ctl-a-m1-6-64x64" else st


def seam4(files):
    """The O8 rows with --aa4 alone, E502's control moved to the held-out rows, E828's j1r a
    control. Frozen per job: H-SAME4 (the O8 table's H-REGION set), H-UNION (its H-UNION set) and,
    on the tri-full rows, H-FULL4 [infer] (no hole)."""
    import csv
    o8 = {}
    with open(os.path.join(S.o8_checked(), "q141_r8pred.tsv")) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            o8.setdefault(r["case"], []).append(r)
    jobs = sorted(S.jobs(), key=lambda j: seam4_set(j[1], j[0]) != "control")
    rows, pred = [], [HEAD]
    jn, jst, jw, jh, jm, jte, jv = S.J1R
    rows.append(seam_row(F4 + jn, jst, jw, jh, jm, jte, jv, None, "pixels,jobok,hash"))
    pred.append(tline(F4 + jn, "hash", S.J1R_HASH, "all", jst,
                      "E828 j1r (render-closing-r3-rgn4 out/rgn4/j1r-aa4-auto.out)"))
    pred.append(tline(F4 + jn, "background", 0, "all", jst, "E828 j1r: 0 background of 41472"))
    for n, st, w, h, m, te, v in jobs:
        st4 = seam4_set(st, n)
        rows.append(seam_row(F4 + n, st4, w, h, m, te, v, None))
        for r in o8[n]:
            model = {"H-REGION": "H-SAME4", "H-UNION": "H-UNION"}[r["model"]]
            pred.append(tline(F4 + n, r["quantity"], r["value"], model, st4,
                              f"O8 R8-1 table {r['model']} ({r['source']})"))
        if v is None:
            pred.append(tline(F4 + n, "holes", 0, "H-FULL4", st4, "no hole [infer]"))
            pred.append(tline(F4 + n, "holes_sha256", EMPTY_SHA, "H-FULL4", st4, "no hole [infer]"))
    return rows, pred


# ---- cube2 -----------------------------------------------------------------------------------
def pix_body(pp):
    return "".join("%d %d %s %s\n" % (x, y, pp[(x, y)][0],
                                      "-" if pp[(x, y)][1] is None else "0x%08x" % pp[(x, y)][1])
                   for y in range(T.H) for x in range(T.W))


def cube2(files):
    R = C.rule()
    tpl = open(os.path.join(DATA, TEMPLATE)).read()
    rows, pred = [], [HEAD]
    e726 = T.pixels(gzip.open(os.path.join(DATA, E726_XN), "rt").read())
    src = "q284_rule.json (sha256 %s..., E923; r8-geo's frozen file)" % C.RULE_SHA[:8]
    with tempfile.TemporaryDirectory() as td:
        for name, st, spec, n, t0, kind in C.jobs():
            text = T.program_text(tpl, spec, C.twords(n, t0), C.SMP)
            files[f"bins/{name}.bin"] = T.assemble(ASM, text, os.path.join(td, name + ".bin"))
            files[f"bins/{name}.s"] = text.encode()
            knobs = "reads:pixels" if st == "control" else "-"
            pg = f" --scratch-pages {C.pages(n)}" if C.pages(n) else ""
            rows.append(f'{name}|{st}|safe|{knobs}|t4|{PROBE}{pg} "$S/bins/{name}.bin"')

            def put(model, pp, why):
                body = pix_body(pp)
                files[f"predictions/cube2/{name}.{model}.txt"] = body.encode()
                pred.append(tline(name, "pixels_sha", sha(body), model, st, why))
                for k in ("ok", "face-tie", "texel-tie"):
                    pred.append(tline(name, k, sum(1 for s, _ in pp.values() if s == k), model, st,
                                      why))

            if kind == "control":
                body = "".join("%d %d ok 0x%08x\n" % (x, y, e726[(x, y)])
                               for y in range(T.H) for x in range(T.W))
                files[f"predictions/cube2/{name}.E726.txt"] = body.encode()
                pred.append(tline(name, "pixels_sha", sha(body), "E726", st,
                                  "E726 cu-xn kept pixels (texture/p1141 tex-h-cube), E930's control"))
                continue
            if kind == "size":
                for law in C.SIZE_LAWS:
                    put("H-" + law, C.pixel_predictions(R, spec, n, law),
                        f"{src}; face-local index {law} (gen/cube.py local)")
            elif kind == "n4":
                for m, fn in C.N4_RIVALS.items():
                    put(m, C.pixel_predictions(R, spec, n, "MORTON", fn),
                        f"{src}; faces {fn} dwords apart")
            else:
                put("RULE", C.pixel_predictions(R, spec, n), src)
            if kind == "facetie":
                cells = C.tie_cells(spec)
                body = "".join("%d %d %s\n" % (x, y, " ".join(str(C.tie_face(c, rv))
                                                             for rv in C.TIE_RIVALS))
                               for (x, y), c in sorted(cells.items(), key=lambda i: (i[0][1], i[0][0])))
                files[f"predictions/cube2/{name}.ties.txt"] = body.encode()
                for i, rv in enumerate(C.TIE_RIVALS):
                    faces = sorted({C.tie_face(c, rv) for c in cells.values()})
                    pred.append(tline(name, "ties_sha", sha(body), rv, st,
                                      f"gen/cube.py tie_face: column {i + 3} of NAME.ties.txt"))
                    pred.append(tline(name, "tie_faces", ",".join(map(str, faces)), rv, st,
                                      f"{len(cells)} tie pixels"))
            if kind == "edge":
                body = edge_body(R, spec, n)
                files[f"predictions/cube2/{name}.edge.txt"] = body.encode()
                pred.append(tline(name, "edge_sha", sha(body), "EDGE", st,
                                  "gen/cube.py edge_cells and blend, exact per-byte blends"))
                cells = C.edge_cells(R, spec, n)
                for rv in C.EDGE_RIVALS:
                    pred.append(tline(name, "out_within", "every", rv, st,
                                      f"each out pixel's bytes within {C.TOL} of the blend "
                                      f"({sum(1 for f, k in cells.values() if k == 'out')} out)"))
    return rows, pred


def edge_body(R, spec, n):
    """`x y kind b0 b1 b2 b3` (in: the in-face blend) or `x y out RIVAL b0 b1 b2 b3` per rival,
    each byte an exact fraction."""
    out = []
    for (x, y), (f, k) in sorted(C.edge_cells(R, spec, n).items(), key=lambda i: (i[0][1], i[0][0])):
        c = tuple(T.coord(s, x, y) for s in spec)
        if k == "in":
            out.append("%d %d in %s\n" % (x, y, " ".join(str(b) for b in
                                                           C.blend_bytes(C.blend(R, c, n, "H-SEAM-ADJ")))))
            continue
        for rv in C.EDGE_RIVALS:
            tl = C.blend(R, c, n, rv)
            out.append("%d %d out %s %s\n" % (x, y, rv, "-" if tl is None else
                                              " ".join(str(b) for b in C.blend_bytes(tl))))
    return "".join(out)


# ---- addr2 -----------------------------------------------------------------------------------
def addr2(files):
    tpl = open(os.path.join(DATA, TEMPLATE)).read()
    rows, pred = [], [HEAD]
    with tempfile.TemporaryDirectory() as td:
        for name, st, n, um, vm, t3, kind in A.jobs():
            text = T.program_text(tpl, A.coords(n, kind), A.twords(n, um, vm, t3), A.SMP)
            files[f"bins/{name}.bin"] = T.assemble(ASM, text, os.path.join(td, name + ".bin"))
            files[f"bins/{name}.s"] = text.encode()
            knobs = "reads:pixels" if st == "control" else "-"
            rows.append(f'{name}|{st}|safe|{knobs}|t4|{PROBE} --scratch-pages {A.PAGES} '
                        f'"$S/bins/{name}.bin"')
            for m in A.models(name, um, n, kind):
                img = A.image(n, um, vm, kind, m)
                body = "".join("%d %d %d\n" % (x, y, img[(x, y)])
                               for y in range(T.H) for x in range(T.W))
                files[f"predictions/addr2/{name}.{m}.txt"] = body.encode()
                why = ("E033/E565/E932 mode 0 repeat, base page 12" if m == "REPEAT"
                       else "gen/addr.py, nothing fitted" if st != "replicate"
                       else "E932's post hoc reading, replicated")
                pred.append(tline(name, "image_sha", sha(body), m, st, why))
    return rows, pred


HEADERS = {
    "seam1": """#stage seam1
#limit 0
# S-1 (a) seam1, Q141's held-out row (seeds plan exp-seeds-r9.md section 1): r8-geo's seam rows (E934) with the flag their
# premise needs: --aa4 (a context made for 4x targets, which the module requires for a TE_AA with bit 31 or 30) and
# dbg:render_rgn_arrays=1 (that context's region headers forced to ONE array: E502's, E504's and E727's condition). Frozen:
# the O8 R8-1 table (predictions/seam1.tsv = gen/o8/q141_r8pred.tsv byte for byte, E922): holes (tri-full) or stored set (a
# single triangle) under the landed region model (H-REGION) and its null H-UNION (halves off). Controls that can fail:
# tri-full 64 x 64 mode 1 TE 0x60000000 (64 holes, E502's A-m1-te60-64x64 set) and mode 2 TE 0x20000000 (no hole, E504).
# expectdiff with job: ok (a hole is the tool's diff; a rejected job stops the stage). Stop: any fault or hang (none in
# E502/E504/E727's 134 one-array jobs); the second row without its pixel rows or job: ok line (hook_check).""",
    "seam4": """#stage seam4
#limit 0
# S-1 (a) seam4, a reading: the same rows with --aa4 alone (four region-header arrays, the knob at its default 0), never run
# in modes 0 or 1. Frozen per job: H-SAME4 (four arrays store the H-REGION set), H-UNION, and on the tri-full rows H-FULL4
# [infer] (no hole: each half reads a complete list). E502's control is a held-out row here (H-FULL4 parts it); controls
# that can fail: E828's j1r (288 x 144, mode 2, TE 0xe0000000, --aa4: hash 0x4a61860dcb4ab325, 0 background) and tri-full
# 64 x 64 mode 2 TE 0x20000000 (no hole under every rival). Stop: any fault or hang (none in the 55 kept four-array
# jobs); the second row without its pixel rows or job: ok line.""",
    "cube2": """#stage cube2
#limit 0
# S9-geo cube2, Q284 (seeds plan section 3): TEXTYPE 2 sampled by smp3d in E726/E930's probe form (64 x 32 fill, scratch dword
# i = 0xD0000000 | i). Frozen: r8-geo's q284_rule.json (E923, held out by E930 at 16 and 8) for the face and (s, t); per job
# kind the rivals of gen/cube.py: 32 x 32 (3 new directions) and 64 x 64 (T1 0x4c03f03f, --scratch-pages 32) faces H-E561
# vs H-MORTON, H-PAIRSWAP; 4 x 4 faces (T1 0x4c003003) H-NN (16 dwords apart) vs H-PAD64 (64) [infer]; face ties of x = y
# and y = z with both signs, H-HIGHAXIS vs H-LOWAXIS, H-POS [infer]; texel ties at |ma| 1.5 and 1.25 (readings); bilinear
# (T0 0x07fe1400) at the +z/+x and -y/+x edges, H-SEAM-ADJ vs H-SEAM-WRAP on the out pixels' bytes within 1, gated by the
# in pixels' exact blend. Control: E726's cu-xn program (its 2048 pixels known). Stop: any fault or hang (none in E726,
# E844, E930 or E931's jobs); the second row without its pixel rows.""",
    "addr2": """#stage addr2
#limit 0
# S9-geo addr2, Q177 (seeds plan section 4): T0 address modes on twiddled 32-bit textures at page 12 of a 32-page named
# scratch (T2 0x5CAFC000, --scratch-pages 32 on every row), the swept axis over 128 positions at one texel a step.
# Frozen, nothing fitted (gen/addr.py): u modes 4 and 6 at 8 x 8 and 32 x 32, H-OFF180 vs H-OFFSCALE, H-OFFNONE; u mode 4
# at 16 x 16 with T3 0, 0x800 and 0x800000, the null H-T3-INERT; u and v mode 4 together, H-OFF180 vs H-OFF360, H-MASK-V;
# replicates of E932's addr-u4 (+180) and addr-u5 (its per-position read). Control: mode 0 on u (the repeat image). Stop:
# any fault or hang (none in E565's or E932's jobs); the second row without its pixel rows.""",
}
STAGES = (("seam1", seam1), ("seam4", seam4), ("cube2", cube2), ("addr2", addr2))


def build():
    files = {}
    for stage, fn in STAGES:
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
        for d in ("predictions/cube2", "predictions/addr2", "bins"):
            for n in os.listdir(os.path.join(KP, d)):
                if f"{d}/{n}" not in files:
                    bad.append(f"{d}/{n} (not generated)")
        print("\n".join("differs: " + b for b in bad) or f"gen current: {len(files)} files")
        return 1 if bad else 0
    print(f"wrote {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
