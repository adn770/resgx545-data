#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r13-tex's generator. Writes tables/STAGE.txt and predictions/STAGE.tsv of the four
stages (srgb3, addr4, t3c, sb12, in run order), the per-pixel predictions
predictions/STAGE/NAME.MODEL.txt (one token a pixel, raster order; score/score.py says how each
token is compared), sb12's word sets predictions/sb12/words-mN.txt and the programs bins/NAME.bin
(+ .s; sb12's are E383's published bins), every input read at the commits session.toml's [freeze]
names (gen/pins.py).

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
import pins  # noqa: E402
import sb as SB  # noqa: E402
import scorekit  # noqa: E402
import srgb as SRGB  # noqa: E402
import t3 as T3  # noqa: E402
import tex  # noqa: E402
import texprog as T  # noqa: E402

HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("srgb3", "addr4", "t3c", "sb12")
TOOL = "t10"
TOOL_FILL = "t10p"     # the probe-fill rows: t10's binary, replayed by tests/test_libmock.py
TEMPLATE = "data:texture/p1141/templates/tx_map.s"
E1000_BIN = "data:render/closing-r10-tex/bins/addr3-16x64-u4.bin"
E1000_KEPT = "data:render/closing-r10-tex/out/20261113-102730/addr3/addr3-16x64-u4.txt.gz"
BDUV5_BIN = "data:texture/p1132-recomp/raw/tx-border/bins/tx-border__17.bin"
BDUV5_KEPT = "data:texture/p1132/tx-border/bd-uv5.txt.gz"
HEADERS = {
    "srgb3": """# r13-tex srgb3, Q282 (rank-round13.md section 2): bilinear sRGB (T0 bit 27) in r10-tex's srgb2 forms. The x stage alone
# (ky 0, kx 0 to 63: corners (0, 1) and (1, 0), and bytes 1 to 3), the y stage alone (kx 0), both stages on bytes 0 to 3, a
# trilinear row on a twiddled 16 x 16 chain (LOD 1.25, bit 9). Frozen per pixel (gen/srgb.py, c2's rule_b.py pinned):
# FTZ-OUT (tested) against FTZ-IN, R10-BF11 and FTZ-T64; TRI-OUT against TRI-NOFLUSH and TRI-LO. Controls that can
# fail: E723's g-bl-st-a and p1132's an-t0b27 rerun (their kept images). End replicate: srgb3-x1r. Stop: any fault or
# hang; the second row without its pixel rows.""",
    "addr4": """# r13-tex addr4, Q177 (rank-round13.md section 2): T0 u address modes on twiddled textures at page 12 of a 32-page named
# scratch (T2 0x5CAFC000). Swept u (r10-tex's form) at 32 x 64, 8 x 64 and 128 x 32 in modes 4 and 6, 32 x 64 in mode 7
# and a 16-bit (u16) 32 x 64 in mode 4: H-MAX 8 max(W, H) + 52 against H-W and H-H (texels and dwords on the 16-bit
# row). u and v in mode 5 swept past both ends at 64 x 16 and 16 x 64: per region IN / LR / AB with M, W or H, and the
# corner bases CO-WH2 / CO-12M4 / CO-12W4 (gen/addr.py). Controls that can fail: E1000's 16 x 64 mode 4 and E565's
# bd-uv5 16 x 16 rerun (their kept images). Stop: any fault or hang; the second row without its pixel rows.""",
    "t3c": """# r13-tex t3c, Q078 (rank-round13.md section 2, closing11 c8's list): T3 bits 12:11 on twiddled chains with
# smp2dreplace (bit 11 clear at LOD 0 to 6; bit 12 with T0's max level 3 and 5; bits 12:11 = 10; a 32 x 32 chain; mips
# off), frozen per pixel from texmodel's level images (gen/t3.py): B11-LEVEL0 / B11-NORMAL / B11-BIAS, B12-CAPLVL /
# CHAINLAST / ADDR / BIAS / NORMAL, AS-00 / 01 / 11. Bit 14 under a bilinear sample on a strided 64 x 32 (H-FOOT vs H-TAP)
# followed by its bit-clear reference, which gates it. Control that can fail: E564's an-t3b11 rerun (its kept image).
# Stop: any fault or hang; the second row without its pixel rows.""",
    "sb12": """# r13-tex sb12, Q046 bit 12 (rank-round13.md section 2): E383's form (probe --tri, eot_plain, colours 0xc0804020 and
# 0x13579bdf) with sideband 0x1200 | mode, modes 0 to 6, both colours, and mode 0 at a triangle moved (4, 4) pixels.
# Frozen (gen/sb.py): H-FIXED (inset >= 4055: the words are E383's set of that mode) against H-O0 (inset < 4055 on
# colour 1); mode 0 H-FIXED-PX (E383's image) and H-SHIFT (moved). Controls that can fail: E383's 0x208 colour 0 (its
# kept image) and the mode 0 colour 0 replicate (inset). Stop: any fault or hang; the second row without its rows.""",
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
    return f'{name}|{st}|safe|{knobs}|{TOOL_FILL}|{tex.PROBE}{pg} "$S/bins/{name}.bin"'


def dwords(img):
    return ["-" if v is None else "%08x" % v for v in img]


def spec_prog(files, name, spec):
    text = tex.text(spec)
    files[f"bins/{name}.s"] = text.encode()
    files[f"bins/{name}.bin"] = tex.assemble(text)


def srgb3(files):
    rows, pred = [], [HEAD]
    for name, st, knobs, spec, models in SRGB.jobs():
        spec_prog(files, name, spec)
        rows.append(probe_row(name, st))
        for m, im in models.items():
            src = ("kept image" if st == "control" else
                   "gen/srgb.py, c2's rule_b.py (sha256 84bd4264...), nothing fitted")
            put(files, pred, "srgb3", name, m, st, dwords(im), src)
    return rows, pred


def addr4(files, td):
    rows, pred = [], [HEAD]
    files["bins/addr4-ctl.bin"] = pins.blob(E1000_BIN)
    rows.append(probe_row("addr4-ctl", "control", A.PAGES))
    put(files, pred, "addr4", "addr4-ctl", "H-E1000", "control",
        dwords(pins.kept_pixels(E1000_KEPT)), "E1000's addr3-16x64-u4 kept image (r10-tex)")
    files["bins/addr4-bduv5.bin"] = pins.blob(BDUV5_BIN)
    rows.append(probe_row("addr4-bduv5", "control"))
    put(files, pred, "addr4", "addr4-bduv5", "H-E565", "control",
        dwords(pins.kept_pixels(BDUV5_KEPT)), "E565's bd-uv5 kept image (p1132 tx-border)")
    for job, ims in A.jobs():
        name, st, w, h, um, vm, form, fmt = job
        text = T.program_text(pins.blob(TEMPLATE).decode(), A.coords(w, h, form),
                              A.twords(w, h, um, vm, fmt), A.SMP)
        files[f"bins/{name}.s"] = text.encode()
        files[f"bins/{name}.bin"] = T.assemble(tex.ASM, text, os.path.join(td, name + ".bin"))
        rows.append(probe_row(name, st, A.PAGES))
        for m, im in ims.items():
            toks = (["-" if v is None else "h:%04x" % v for v in im] if fmt == A.FMT16
                    else dwords(im))
            put(files, pred, "addr4", name, m, st, toks,
                "gen/addr.py (E1000, E1017, c2's rule_a.py and post_a.py forms), nothing fitted")
    return rows, pred


def t3c(files):
    rows, pred = [], [HEAD]
    for name, st, knobs, spec, models, pages in T3.jobs():
        spec_prog(files, name, spec)
        rows.append(probe_row(name, st, pages))
        for m, toks in models.items():
            src = ("E564's an-t3b11 kept image" if st == "control" else
                   "gen/t3.py: texmodel's level image (c8's forms, B11/B12 post hoc on E564)")
            put(files, pred, "t3c", name, m, st, toks, src)
    return rows, pred


def sb12(files):
    rows, pred = [], [HEAD]
    for n, pin in SB.BINS.items():
        files[f"bins/{n}"] = pins.blob(pin)
    for mode in range(7):
        files[f"predictions/sb12/words-m{mode}.txt"] = body(
            "%08x" % w for w in SB.words(pins.blob, mode)).encode()
    for name, st, knobs, args, px, qs, mode in SB.jobs(pins.blob):
        rows.append(f"{name}|{st}|safe|{knobs}|{TOOL}|{args}")
        for m, im in px.items():
            put(files, pred, "sb12", name, m, st, dwords(im), "E383's kept images (gen/sb.py)")
        for q, ms in qs.items():
            for m, v in ms.items():
                pred.append(line(name, q, v, m, st, f"words-m{mode}.txt: E383's words of mode "
                                 f"{mode}, both runs (gen/sb.py)"))
    return rows, pred


def build():
    files, tables = {}, {}
    tables["srgb3"] = srgb3(files)
    with tempfile.TemporaryDirectory() as td:
        tables["addr4"] = addr4(files, td)
    tables["t3c"] = t3c(files)
    tables["sb12"] = sb12(files)
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
