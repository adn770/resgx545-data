#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r10-tex's generator. Writes tables/STAGE.txt and predictions/STAGE.tsv of the four
stages (addr3, cube3, t3b, srgb2, in run order), the per-pixel predictions
predictions/STAGE/NAME.MODEL.txt (2048 tokens, raster order, one a line; score/score.py says how
each token is compared) and the probe programs bins/NAME.bin (+ .s), every input read at the
commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now
Inputs: RESGX545_DATA (default /Users/jtorra/src/resgx545-data), RESGX545_MAIN (default
/Users/jtorra/src/resgx545, for tools/usse-asm/usse-asm)."""
import gzip
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import addr as A  # noqa: E402
import cube as C  # noqa: E402
import pins  # noqa: E402
import scorekit  # noqa: E402
import srgb as SRGB  # noqa: E402
import t3 as T3  # noqa: E402
import tex  # noqa: E402
import texprog as T  # noqa: E402

HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("addr3", "cube3", "t3b", "srgb2")
TEMPLATE = "data:texture/p1141/templates/tx_map.s"
E726_XN = "data:texture/p1141/out-hw/p1141tex-dumps/tex-h-cube/cu-xn.txt.gz"
HEADERS = {
    "addr3": """# S10-tex addr3, Q177 (seeds plan closing10/seeds/exp-seeds-r10.md section 2): T0 address modes on twiddled 32-bit
# textures of W != H at page 12 of a 32-page named scratch (T2 0x5CAFC000, --scratch-pages 32 on every row), the swept
# u over 128 positions at one texel a step, v on texel H / 2. Frozen, nothing fitted (gen/addr.py): the offset past
# E561's index is 8 W + 52 (H-W, E957's fit), 8 H + 52 (H-H), 8 sqrt(W H) + 52 (H-SQ), 4 (W + H) + 52 (H-WH); u mode 5
# H-B5 (left 5 W + 52 + t, right 6 W + 52 + t) vs H-B5H. Control: u mode 0 (the repeat image, r9-geo's program).
# Replicates: E957's 16 x 16 mode 4 (+180) and E565's 32 x 8 form (+308). Stop: any fault or hang; the second row
# without its 32 pixel rows (hook_check).""",
    "cube3": """# S10-tex cube3, Q284 (seeds plan section 3): TEXTYPE 2 sampled by smp3d in E726's probe form, 16 x 16 faces. Ties:
# 6 cc rows (both tied coordinates movs of +-0.75) and 6 rr rows (both the bit-identical fmad ramp or its negation),
# 2048 two-axis tie pixels each, and r8-geo's a2 replayed byte for byte (78 tie pixels, 4 of the 7 kept lower reads):
# H-HIGHAXIS (the higher tied axis everywhere), H-FMADNE (the replay repeats r8's image, cc and rr read high), H-THIRD
# (lower reads in cc and rr). Edges +z/+x and -y/+x, bilinear, along coordinate 7.75 and 8.25: H-SEAM-FLOAT vs
# H-SEAM-ADJ, out pixels within 1 a byte, gated by the in pixels. Control: E726's cu-xn program. Stop: any fault or
# hang; the second row without its pixel rows.""",
    "t3b": """# S10-tex t3b, Q078 (seeds plan section 4): T3 bit 14 on strided named memory (E566's tx_map form), six held-out
# geometries (S 256, S 16 x H 64, u off the 1/128 grid, u from -0.5 to 1.5, v a ramp with u fixed, a 16-bit format),
# each followed by its bit-clear reference; frozen per pixel R-4096 / R-4096TX / R-ROUND / H-U01 (+ H-UV, H-URAW on
# their rows), gen/t3.py. Controls that can fail: E566's s64x32-ctl and s64x32-t3b14 (their kept images); replicate
# E975's b14-u01. --scratch-pages holds every rival's reads plus a page. Stop: any fault or hang; the second row
# without its pixel rows.""",
    "srgb2": """# S10-tex srgb2, Q282 (seeds plan section 1): bilinear sRGB (T0 bit 27) in E723's g-bl-st form, held out against
# the frozen R10-BF11 (seeds q282_r10_rule.json, E982's rule): weights off the 1/64 grid (floor vs round vs exact),
# k = 0 with B larger and smaller (bypass vs H-K0FLOOR), subnormal halves, two random rows. Control that can fail:
# E723's g-bl-st-a rerun (its kept image). Stop: any fault or hang; the second row without its pixel rows.""",
}


def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def body(tokens):
    return "".join(t + "\n" for t in tokens)


def put(files, pred, stage, name, model, st, tokens, src):
    b = body(tokens)
    files[f"predictions/{stage}/{name}.{model}.txt"] = b.encode()
    pred.append(line(name, "pixels", "sha256:" + pins.sha(b), model, st, src))


def probe_row(name, st, pages=None):
    knobs = "reads:pixels" if st == "control" else "-"
    pg = f" --scratch-pages {pages}" if pages and pages != 16 else ""
    return f'{name}|{st}|safe|{knobs}|t4|{tex.PROBE}{pg} "$S/bins/{name}.bin"'


def asm_texprog(files, td, name, coords, twords, smp):
    text = T.program_text(pins.blob(TEMPLATE).decode(), coords, twords, smp)
    files[f"bins/{name}.s"] = text.encode()
    files[f"bins/{name}.bin"] = T.assemble(tex.ASM, text, os.path.join(td, name + ".bin"))


def addr3(files, td):
    rows, pred = [], [HEAD]
    for name, st, w, h, um, vm, ims in A.jobs():
        asm_texprog(files, td, name, A.coords(w, h), A.twords(w, h, um, vm), A.SMP)
        rows.append(probe_row(name, st, A.PAGES))
        for m, im in ims.items():
            src = ("E932/E957 mode 0 repeat, base page 12" if m == "REPEAT" else
                   "gen/addr.py, nothing fitted" + (" (E957/E565's reading, replicated)"
                                                    if st == "replicate" else ""))
            put(files, pred, "addr3", name, m, st,
                ["%08x" % (0xD0000000 | (A.BASE + i)) for i in im], src)
    return rows, pred


def kept_xy(pin):
    return T.pixels(gzip.decompress(pins.blob(pin)).decode(errors="replace"))


def cube3(files, td):
    R = C.rule()
    rows, pred = [], [HEAD]
    r8 = kept_xy(C.R8_A2)
    e726 = kept_xy(E726_XN)
    src = "r9-geo's q284_rule.json (sha256 %s..., E923) and gen/cube.py" % C.RULE_SHA[:8]
    for name, st, spec, n, t0, kind in C.jobs3():
        asm_texprog(files, td, name, spec, C.twords(n, t0), C.SMP)
        rows.append(probe_row(name, st))
        if kind == "control":
            put(files, pred, "cube3", name, "E726", st,
                ["%08x" % e726[(x, y)] for y in range(T.H) for x in range(T.W)],
                "E726 cu-xn kept pixels (texture/p1141 tex-h-cube)")
            continue
        if kind in ("tie", "replay"):
            for rv in ("H-HIGHAXIS", "H-FMADNE"):
                toks = C.tie_axis_tokens(spec, rv, n, r8 if kind == "replay" else None, R)
                put(files, pred, "cube3", name, rv, st, toks,
                    src + ("; r8-geo's kept cube-off-a2 image" if rv == "H-FMADNE" and kind == "replay"
                           else "; the higher tied axis at a two-axis tie"))
            lower = 0
            if kind == "replay":
                for (x, y), c in C.tie_cells(spec).items():
                    ax = C.tied_axes(c)
                    if len(ax) == 2 and (r8[(x, y)] & 0x0FFFFFFF) // (n * n) // 2 != max(ax):
                        lower += 1
            pred.append(line(name, "lower", 0, "H-HIGHAXIS", st, "no lower read anywhere"))
            pred.append(line(name, "lower", lower, "H-FMADNE", st,
                             "r8-geo's kept lower reads" if kind == "replay" else
                             "bit-equal tied coordinates: no lower read"))
            if kind == "tie":
                pred.append(line(name, "lower", ">0", "H-THIRD", st,
                                 "a large third coordinate gives lower reads [infer]"))
            continue
        for rv in C.EDGE3_RIVALS:
            put(files, pred, "cube3", name, rv, st, C.edge_tokens(R, spec, rv, n),
                src + "; %s, out pixels within %d a byte, in pixels the gate" % (rv, C.TOL))
    return rows, pred


def texture_stage(stage, jobs, files, src):
    rows, pred = [], [HEAD]
    for j in jobs:
        name, st, knobs, spec, models = j[:5]
        kind = j[5] if len(j) > 5 else "dword"
        npages = j[6] if len(j) > 6 else None
        text = tex.text(spec)
        files[f"bins/{name}.s"] = text.encode()
        files[f"bins/{name}.bin"] = tex.assemble(text)
        rows.append(probe_row(name, st, npages))
        for m, im in models.items():
            toks = ["h:%04x" % v for v in im] if kind == "half" else ["%08x" % v for v in im]
            put(files, pred, stage, name, m, st, toks, src)
    return rows, pred


def build():
    files, tables = {}, {}
    with tempfile.TemporaryDirectory() as td:
        tables["addr3"] = addr3(files, td)
        tables["cube3"] = cube3(files, td)
    tables["t3b"] = texture_stage("t3b", T3.jobs(), files, "gen/t3.py")
    tables["srgb2"] = texture_stage("srgb2", SRGB.jobs(), files, "gen/srgb.py, gen/q282.py")
    import score as SC
    for stage in ORDER:
        rows, pred = tables[stage]
        files[f"tables/{stage}.txt"] = (f"#stage {stage}\n#limit 0\n{HEADERS[stage]}\n"
                                        + "\n".join(rows) + "\n").encode()
        files[f"predictions/{stage}.tsv"] = "".join(pred).encode()
        controls = {}
        for r in rows:
            name, st, _, knobs, tool, args = r.split("|", 5)
            if st == "control":
                reads = [w[6:].split(",") for w in knobs.split() if w.startswith("reads:")]
                controls[name] = (tuple(reads[0]) if reads else (),
                                  dict(name=name, args=args, stage=stage))
        scorekit.refuse_unreadable(controls, SC.producible)
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
        for d in ("bins",) + tuple(f"predictions/{s}" for s in ORDER):
            full = os.path.join(KP, d)
            for n in sorted(os.listdir(full)) if os.path.isdir(full) else []:
                if f"{d}/{n}" not in files:
                    bad.append(f"{d}/{n} (not written by the generator)")
        print("\n".join(f"differs: {b}" for b in bad) or f"generator current: {len(files)} files")
        return 1 if bad else 0
    print(f"wrote {len(files)} files; pins read: {', '.join(sorted(pins.READ))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
