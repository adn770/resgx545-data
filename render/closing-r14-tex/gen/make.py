#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r14-tex's generator. Writes tables/STAGE.txt and predictions/STAGE.tsv of the two
stages (srgb4, addr5, in run order), the per-pixel predictions predictions/STAGE/NAME.MODEL.txt
(one token a pixel, raster order; score/score.py says how each token is compared) and the programs
bins/NAME.bin (+ .s for the generated ones; the replicates' are the published bins), every input
read at the commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now
Inputs: RESGX545_DATA (default /Users/jtorra/src/resgx545-data), RESGX545_MAIN (default
/Users/jtorra/src/resgx545, for tools/usse-asm/usse-asm)."""
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
import addr5 as A5  # noqa: E402
import pins  # noqa: E402
import scorekit  # noqa: E402
import srgb4 as S4  # noqa: E402
import tex  # noqa: E402
import texprog as T  # noqa: E402

HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("srgb4", "addr5")
TOOL = "t10"
HEADERS = {
    "srgb4": """# r14-tex srgb4, Q282 (rank-round14.md section 2): the trilinear sRGB level lerp (T0 0x0FFC1600: bit 27, bit 9;
# smp2dreplace) on srgb3-tri's 16 x 16 counting chain at LOD 1.125, 1.5, 1.75, 1.984375, 0.25 and 1.2 (Q-FLOOR against
# Q-NEAR) and on a dark 4 x 4 chain (LOD 0.125); frozen per pixel (gen/srgb4.py, c2's rule_b.py pinned): TRI-RNTU (tested;
# -NF its third result unflushed) against TRI-G15 (-NF), TRI-RNE, TRI-BF11, TRI-OUT. Bytes 2 and 3 (tx_map_r11.s: the
# sample's second dword) on the x stage alone, the y stage alone and both: B2-FTZ-OUT (low half), A-LIN against A-SRGB
# and A-BYTE (high half). Controls that can fail: E723's g-bl-st-a, srgb3-tri rerun (kept images), the r11 program on
# srgb3-x1's texture with byte 2 = byte 0 (srgb3-x1's kept low halves). Stop: any fault or hang; the second row
# without its pixel rows.""",
    "addr5": """# r14-tex addr5, Q177 (rank-round14.md section 2): u and v in mode 5 swept past both ends on twiddled 32-bit textures
# at page 12 of a 32-page named scratch (T2 0x5CAFC000): 8 x 8, 32 x 32, 128 x 32, 32 x 128, 128 x 128 and, last, 256 x
# 32. Corner bases frozen (gen/addr5.py): C-LOG4 (tested) against C-SAT24, C-FLOOR16 and E1026's CO-WH2, CO-12M4,
# CO-12W4; the other regions as r13-tex froze them (IN / LR / AB with M, W, H). Types 1, 3 and 4 (E567's 16 x 16
# programs): the mode 0 reference (a replicate, H-E567) then u mode 4, T-MODE0 against T-OFFSET (+180) on the
# reference's image of this run. Controls that can fail: E1000's 16 x 64 mode 4 and E565's bd-uv5 rerun (kept images).
# Stop: any fault or hang; the second row without its pixel rows.""",
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
    return f'{name}|{st}|safe|{knobs}|{TOOL}|{tex.PROBE}{pg} "$S/bins/{name}.bin"'


def dwords(img):
    return ["-" if v is None else "%08x" % v for v in img]


def spec_prog(files, name, text):
    files[f"bins/{name}.s"] = text.encode()
    files[f"bins/{name}.bin"] = tex.assemble(text)


def srgb4(files):
    rows, pred = [], [HEAD]
    for name, st, tmpl, spec, binpin, models in S4.jobs():
        if binpin:
            files[f"bins/{name}.bin"] = pins.blob(binpin)
        else:
            spec_prog(files, name, S4.r11_text(spec) if tmpl == "r11" else tex.text(spec))
        rows.append(probe_row(name, st))
        for m, toks in models.items():
            src = ("kept image" if st == "control" else
                   "gen/srgb4.py, c2's rule_b.py (sha256 84bd4264...); TRI-RNTU E1025's post hoc "
                   "form, TRI-G15 fitted on srgb3-tri (README.md 'Deviations' 1)")
            put(files, pred, "srgb4", name, m, st, toks, src)
    return rows, pred


def addr5(files, td):
    rows, pred = [], [HEAD]
    files["bins/addr5-ctl.bin"] = pins.blob(A5.E1000_BIN)
    rows.append(probe_row("addr5-ctl", "control", A.PAGES))
    put(files, pred, "addr5", "addr5-ctl", "H-E1000", "control",
        dwords(pins.kept_pixels(A5.E1000_KEPT)), "E1000's addr3-16x64-u4 kept image (r10-tex)")
    files["bins/addr5-bduv5.bin"] = pins.blob(A5.BDUV5_BIN)
    rows.append(probe_row("addr5-bduv5", "control"))
    put(files, pred, "addr5", "addr5-bduv5", "H-E565", "control",
        dwords(pins.kept_pixels(A5.BDUV5_KEPT)), "E565's bd-uv5 kept image (p1132 tx-border)")

    def corners(shapes):
        for job, ims in A5.corner_jobs(shapes):
            name, st, w, h, um, vm, form, fmt = job
            text = T.program_text(pins.blob(tex.TEMPLATE).decode(), A.coords(w, h, form),
                                  A.twords(w, h, um, vm, fmt), A.SMP)
            files[f"bins/{name}.s"] = text.encode()
            files[f"bins/{name}.bin"] = T.assemble(tex.ASM, text, os.path.join(td, name + ".bin"))
            rows.append(probe_row(name, st, A.PAGES))
            for m, im in ims.items():
                put(files, pred, "addr5", name, m, st, dwords(im),
                    "gen/addr5.py (E1026's post hoc C-LOG4, its rivals and r13-tex's region "
                    "forms), nothing fitted on these shapes")

    corners(A5.SHAPES)
    for name, st, spec, binpin, pages, models, q in A5.type_jobs():
        if binpin:
            files[f"bins/{name}.bin"] = pins.blob(binpin)
        else:
            spec_prog(files, name, tex.text(spec))
        rows.append(probe_row(name, st, pages))
        for m, v in models.items():
            if q == "pixels":
                put(files, pred, "addr5", name, m, st, v, "E567's kept image (p1132)")
            else:
                pred.append(line(name, "rel", v, m, st, "gen/addr5.py: the reference's image "
                                 "of this run, plus the offset (E1000, E1026)"))
    corners(A5.LAST)
    return rows, pred


def build():
    files, tables = {}, {}
    tables["srgb4"] = srgb4(files)
    with tempfile.TemporaryDirectory() as td:
        tables["addr5"] = addr5(files, td)
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
        for d in ("bins", "tables") + tuple(f"predictions/{s}" for s in ORDER):
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
