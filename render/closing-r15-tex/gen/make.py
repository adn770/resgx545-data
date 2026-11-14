#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r15-tex's generator. Writes tables/STAGE.txt and predictions/STAGE.tsv of the two
stages (chain, ty, in run order), the per-pixel predictions predictions/STAGE/NAME.MODEL.txt (one
token a pixel, raster order; score/score.py says how each token is compared) and the programs
bins/NAME.bin (+ .s for the generated ones; the controls' are the published bins), every input read
at the commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now
Inputs: RESGX545_DATA (default /Users/jtorra/src/resgx545-data), RESGX545_MAIN (default
/Users/jtorra/src/resgx545, for tools/usse-asm/usse-asm)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import chain as C  # noqa: E402
import pins  # noqa: E402
import prog  # noqa: E402
import scorekit  # noqa: E402
import tex  # noqa: E402
import ty as TY  # noqa: E402

HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("chain", "ty")
TOOL = "t10"
HEADERS = {
    "chain": """# r15-tex chain, Q104 (rank-round15.md section 2): E562's generator (the scratch as the texture, each texel naming its
# dword; level 0 at dword 0) on chains E562 did not reach: a side of 1 (1 x 32, 32 x 1; bias field 0x33), a 16-bit format
# (u16 32 x 16 and 16 x 64; MIPFILTER at f 32), long sides (64 x 32, 256 x 32) and, last, a 1D texture (smp1dreplace on
# 64 x 1; maximum field 3). u = v = the diagonal (32 x + 17) / 2048 (1/2 on a side of 1), LOD = (y >> 2) + c down the rows.
# Frozen per pixel (gen/chain.py): chain=A (tested; E562) against B and D (not D on 256 x 32: past 64 pages), on u16 rows
# A-TX (tested) against A-DW, B-TX, D-TX and the blends -BL8 (tested) and -BL16. Controls that can fail: E562's
# shp-32x16-l5 and shp-128x16-l7-x0 rerun (published programs, kept images). Stop: any fault or hang; the second row
# without its pixel rows.""",
    "ty": """# r15-tex ty, Q177 (rank-round15.md section 2, R15-5 a): texture types 1, 3, 4 in u modes 4 to 7 (E567's 16 x 16 programs,
# T0's u mode only; the same at 32 x 32 with its mode 0 reference), 32 pages, base 0. Frozen (gen/ty.py): H-HALF and H-LIN1
# (E1039's post hoc form and map; tested) against H-WHOLE and H-MODE0; H-AS-U4 on modes 5 to 7 (E1039's kept mode 4 image);
# the n16 row (U = x - 24): NAME-U (tested) against NAME-WRAP; the 32 x 32 references R-W / R-16 (R-2W / R-32 on type 4).
# Controls that can fail: E1000's addr3-16x64-u4 and E1039's addr5-ty1-u4 rerun (kept images). Stop: any fault or hang;
# the second row without its pixel rows.""",
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


def spec_prog(files, name, text):
    files[f"bins/{name}.s"] = text.encode()
    files[f"bins/{name}.bin"] = tex.assemble(text)


def chain(files):
    rows, pred = [], [HEAD]
    specs = json.loads(pins.blob(tex.SPECS))
    for name, case in C.CONTROLS:
        sp = specs[case]
        files[f"bins/{name}.bin"] = pins.blob(C.SHAPES_BIN % sp["bin"])
        rows.append(probe_row(name, "control"))
        put(files, pred, "chain", name, "H-E562", "control",
            ["%08x" % v for v in pins.kept_pixels(C.SHAPES_KEPT % case)],
            f"E562's {case} kept image (p1132 tx-shapes)")
    for j in C.HELDOUT:
        spec_prog(files, j["name"], prog.text(j))
        rows.append(probe_row(j["name"], "heldout"))
        for m in j["models"]:
            put(files, pred, "chain", j["name"], m, "heldout", C.tokens(j, m),
                f"gen/chain.py ({j['why']}): E562's chains, E441's level rule; nothing fitted")
    return rows, pred


def ty(files):
    rows, pred = [], [HEAD]
    for name, st, sp, binpin, pix, other, src in TY.jobs():
        if binpin:
            files[f"bins/{name}.bin"] = pins.blob(binpin)
        else:
            spec_prog(files, name, tex.text(sp))
        rows.append(probe_row(name, st, TY.PAGES))
        for m, toks in pix.items():
            put(files, pred, "ty", name, m, st, toks, src)
        for m, (q, v) in other.items():
            pred.append(line(name, q, v, m, st, src))
    return rows, pred


def build():
    files, tables = {}, {}
    tables["chain"] = chain(files)
    tables["ty"] = ty(files)
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
