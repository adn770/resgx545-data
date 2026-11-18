#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r35-o0's generator (closing29/plan/rank-round35.md section 3.1, Q073). Writes
tables/o.txt, predictions/o.tsv, the programs bins/*.bin, gen/constants.txt and the mock's kept
texts; every input is read at the commits session.toml's [freeze] names or at the bound tool
source's own commit (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Q073: "what does o0 hold at the start of an opaque pass's pixel shader?" Every row is a t10
`probe --temps 32 --pixels --tri pixel` triangle in a 128 x 128 render context (E417's argv:
--max-width/--max-height 128) at 64 x 64 or 128 x 128, or t10's bare `fill`.

Programs (bins/):
  a.bin  A' (control at every use): the pixel's place in o0, unique per pixel by construction:
         o0 = (pa0 & 0xffff0000) | ((pa1 >> 16) & 0xffff), with the usse probes' pds_iter_xy
         (coordinate set 1) and vtx_coords (--vtx-coords 2): pa0 = (x + 0.5) * 2 / W - 1 and
         pa1 = (y + 0.5) * 2 / H - 1 as singles (E081's oreg-x/oreg-y images: 1062 of 1062 each,
         tests/test_gen.py). Every such single has at most 7 significant bits, so the top 16
         bits of each are exact and the value names the pixel; bit 31 of a negative single never
         makes 0xff203040, 0xff00ff00 or 0xff336699 (the top halves are not finite singles).
  k.bin  K (control): o0 = 0xff00ff00 (E417's job A, its kept bytes).
  p.bin  P: o0 = o0, the pass-through (E417's job P, its kept bytes).
  t10 `fill` (between, h5): the 64 x 32 fill, colour 0xff336699 (t10's source).
"""
import hashlib
import os
import pathlib
import re
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pins  # noqa: E402

sys.path.insert(0, os.path.join(pins.MAIN, "tools", "usse-asm"))
import probe as P  # noqa: E402

STAGE = "o"
TOOL = "t10"
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
K = 0xFF00FF00                      # E417's job A colour (k.bin's constant)
MAXWH = 128                         # E417's render context (max_size [0x80, 0x80])
E417 = "data:isp/o0-start/isp-o0-start-%d/raw.txt"
E417_BIN = "data:isp/o0-start/isp-o0-start-64/bins/isp-o0-start-64__%d.bin"
E417_TOML = "resgx545:probes/isp/o0-start.toml"
E081 = "data:usse/output-registers/usse-output-registers-oreg-%s/raw.txt"
E081_BINS = "data:usse/output-registers/usse-output-registers-oreg-x/bins/%s"
TEMPLATE = "resgx545:probes/usse/templates/pix_op.s"
# the health pair's kept texts on this module and t10 (r34-q010, E1134): the mock's t10 answers
Q010_C = "data:render/closing-r34-q010/out/20261116-231015/c"
KEPT_FILL = Q010_C + "/begin.fill1.txt.gz"
KEPT_TRI = Q010_C + "/begin.health1.txt.gz"
A_BODY = ["and.skipinv r0, pa0, #0xFFFF0000", "shr.skipinv r1, pa1, #16",
          "and.skipinv r1, r1, #0x0000FFFF", "or.skipinv r0, r0, r1", "mov.skipinv.end o0, r0"]
# groups: (group, rows as (role, size)), role a = A', k = K, p = P, f = t10 fill
GROUPS = {
    "c0": [("a", 64), ("a", 128)],
    "c1": [("k", 64), ("p", 64)],
    "h1": [("a", 64), ("p", 64)],
    "h2": [("a", 128), ("p", 64)],
    "h3": [("a", 64), ("p", 128)],
    "h4": [("a", 64), ("p", 64)],
    "h5": [("a", 64), ("f", 0), ("p", 64)],
}
# replicate a in plan order, b reversed (c0 and h5 once), c: h1 once more (frozen before the run)
ORDER = [("a", ["c0", "c1", "h1", "h2", "h3", "h4", "h5"]),
         ("b", ["h4", "h3", "h2", "h1", "c1"]),
         ("c", ["h1"])]
RESET_P = {"h4"}                     # the P row of these groups gets the kit's debugfs reset
CAT = ("H-SAMEPIX", "H-SLOTMAP", "H-OTHER")
SIZE = ("h2", "h3")


def fbits(f):
    return struct.unpack("<I", struct.pack("<f", f))[0]


def clip(c, n):
    """pa of pixel coordinate c on a side of n pixels (E081): (c + 0.5) * 2 / n - 1, its bits."""
    return fbits((c + 0.5) * 2.0 / n - 1.0)


def f_a(x, y, w, h):
    """A' at pixel (x, y) of a w x h target: the top halves of pa0 and pa1."""
    return (clip(x, w) & 0xFFFF0000) | (clip(y, h) >> 16)


def kept_image(pin, case):
    """{(x, y): value} of one probe case of a kept raw.txt (its `row Y:` lines)."""
    out = {}
    for m in re.finditer(r"^probe \S+__%d: row (\d+): ([0-9a-f ]+)$" % case,
                         pins.blob(pin).decode(), re.M):
        for x, t in enumerate(m.group(2).split()):
            out[(x, int(m.group(1)))] = int(t, 16)
    return out


def asm(text):
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "x.bin"
        P._assemble(text, f, "usse")
        return f.read_bytes()


def program(body):
    t = pins.blob(TEMPLATE).decode()
    return t.replace("{OP}", "\n".join(body))


def fill_colour():
    """t10's bare `fill` colour (its default fill job) from its bound source."""
    src = pins.tool_source(TOOL).decode()
    m = re.search(r"\.width = 64, \.height = 32, \.stride = 256, \.colour = (0x[0-9a-f]+)", src)
    return int(m.group(1), 16)


def background():
    """The probe triangle's background: E417's kept A job at 64 x 64, pixel (0, 0)."""
    return kept_image(E417 % 64, 0)[(0, 0)]


def args(role, size):
    if role == "f":
        return "fill"
    a = (f"probe --temps 32 --pixels --tri pixel --width {size} --height {size} "
         f"--max-width {MAXWH} --max-height {MAXWH}")
    if role == "a":
        a += (' --vtx-coords 2 --slot pixpds="$S/bins/pds_iter_xy.bin:12"'
              ' --slot vtxuse="$S/bins/vtx_coords.bin"')
    return a + f' "$S/bins/{role}.bin"'


def all_rows():
    """[(name, set, knobs, args, group, rep, role, size)] in run order."""
    out = []
    for rep, groups in ORDER:
        for g in groups:
            for role, size in GROUPS[g]:
                name = f"{g}{rep}-{role}{size if role in 'ap' and g == 'c0' else ''}"
                if role == "a":
                    sset, knobs = "control", "reads:pixels"
                elif role == "k":
                    sset, knobs = "control", "reads:pixels"
                elif role == "f":
                    sset, knobs = "between", "noreset"
                elif g == "c1":
                    sset, knobs = "control", "noreset reads:pixels"
                else:
                    sset = "fit" if (g, rep) == ("h1", "a") else "heldout"
                    knobs = "-" if g in RESET_P else "noreset"
                out.append((name, sset, knobs, args(role, size), g, rep, role, size))
    return out


def predictions(rows):
    pred = [HEAD]

    def line(*f):
        pred.append("\t".join(str(x) for x in f) + "\n")

    for name, sset, knobs, a, g, rep, role, size in rows:
        if role == "a":
            line(name, "image", f"A:{size}", "H-REF", sset,
                 "by construction: every non-background pixel (x, y) = (pa0 & 0xffff0000) | "
                 "(pa1 >> 16), pa = (c + 0.5) * 2 / n - 1 (E081's oreg images, 1062 of 1062)")
        elif role == "k":
            line(name, "image", "0x%08x" % K, "H-REF", sset,
                 "by construction: k.bin's constant on every non-background pixel (E417 job A)")
        elif role == "p" and g == "c1":
            line(name, "image", "0x%08x" % K, "H-REF", sset,
                 "E417 [HW]: the pass-through after a constant colour shows that colour on part "
                 "of the triangle, the background elsewhere (390 to 450 of 1062 at 64 x 64)")
        elif role == "p" and g in ("h1", "h2", "h3"):
            line(name, "cat", "SAMEPIX", "H-SAMEPIX", sset,
                 "every non-background pixel (x, y) reads A'(x, y) of its group's A' row")
            line(name, "cat", "SLOTMAP", "H-SLOTMAP", sset,
                 "every non-background pixel reads A' of another pixel by the map fitted on h1a "
                 "(not the identity)")
            line(name, "cat", "OTHER", "H-OTHER", sset,
                 "no named map: values not of A' or a map that does not repeat")
            if g in SIZE:
                line(name, "cat", "TILESLOT", "H-TILESLOT", sset,
                     "the pixel of the same 32 x 16 tile index in drawing order (tiles row by "
                     "row, W / 32 a row) [infer]")
        elif role == "p" and g == "h4":
            line(name, "life", "KEEP", "H-RESETKEEP", sset,
                 "a debugfs reset between keeps A' values (E1140 kept sa0 and pa0 over a reset)")
            line(name, "life", "CLEAR", "H-RESETCLEAR", sset,
                 "a debugfs reset between leaves no A' value")
        elif role == "p" and g == "h5":
            line(name, "life", "FILL", "H-FILLREPLACE", sset,
                 "the t10 fill between replaces it: every non-background pixel is the fill's "
                 "colour")
            line(name, "life", "AKEEP", "H-TRIONLY", sset,
                 "A' values survive a fill between (only triangle jobs replace it)")
    return pred


HEADER = """#stage o
#limit 0
# r35-o0 o, Q073 (rank-round35.md 3.1; SAFE: no expectfault, #limit 0, no kreg, no dbg knob): what does o0 hold at the
# start of an opaque pass's pixel shader? A' (control): o0 = a value unique per pixel by construction (pa0/pa1 top
# halves, E081). K (control): o0 = 0xff00ff00 (E417 job A). P: o0 = o0 (E417's pass-through), after its group's A'
# with noreset. Groups c0 (A' 64, 128: the decoder's known value), c1 (K ; P: E417's form), h1 (A' 64 ; P 64, fit
# on h1a), h2 (A' 128 ; P 64), h3 (A' 64 ; P 128), h4 (A' 64 ; reset ; P 64), h5 (A' 64 ; t10 fill ; P 64);
# replicate b reversed, h1 thrice. Frozen: H-SAMEPIX, H-SLOTMAP, H-OTHER (h1-h3), H-TILESLOT (h2, h3), H-RESETKEEP/
# CLEAR (h4), H-FILLREPLACE / H-TRIONLY (h5). Stop: any fault or hang (4, 6); a control without its pixel rows
# (25); a probe without its H pixel rows or with a failed line, a fill without `fill: ok` (24, ends)."""


def build():
    files = {}
    rows = all_rows()
    files["bins/a.bin"] = asm(program(A_BODY))
    files["bins/k.bin"] = pins.blob(E417_BIN % 0)
    files["bins/p.bin"] = pins.blob(E417_BIN % 1)
    files["bins/pds_iter_xy.bin"] = pins.blob(E081_BINS % "pds_iter_xy.bin")
    files["bins/vtx_coords.bin"] = pins.blob(E081_BINS % "vtx_coords.bin")
    tab = [HEADER] + [f"{n}|{s}|safe|{k}|{TOOL}|{a}" for n, s, k, a, *_ in rows]
    files[f"tables/{STAGE}.txt"] = ("\n".join(tab) + "\n").encode()
    files[f"predictions/{STAGE}.tsv"] = "".join(predictions(rows)).encode()
    consts = (f"K=0x{K:08x}\nBG=0x{background():08x}\nFILL=0x{fill_colour():08x}\n"
              f"MAXWH={MAXWH}\n"
              f"T10_SOURCE={hashlib.sha256(pins.tool_source(TOOL)).hexdigest()}\n")
    files["gen/constants.txt"] = consts.encode()
    files["mock/kept/fill.txt"] = pins.blob(KEPT_FILL)
    files["mock/kept/tri.txt"] = pins.blob(KEPT_TRI)
    # the mock's masks: the triangle (E417's A jobs) and the pixels a P kept (E417's P jobs)
    for size, tri, left in ((64, 0, 1), (128, 0, 6)):
        img_t, img_l = kept_image(E417 % size, tri), kept_image(E417 % size, left)
        bg = img_t[(0, 0)]
        for nm, img in (("tri", img_t), ("left", img_l)):
            px = sorted((y, x) for (x, y), v in img.items() if v != bg)
            files[f"mock/kept/{nm}{size}.txt"] = "".join(f"{x} {y}\n" for y, x in px).encode()
    return files


def main(argv):
    files = build()
    if "--check" in argv:
        bad = [p for p, b in files.items()
               if not os.path.exists(os.path.join(KP, p)) or open(os.path.join(KP, p), "rb").read() != b]
        for d in ("bins", "tables", "predictions"):
            full = os.path.join(KP, d)
            bad += [f"{d}/{n}" for n in sorted(os.listdir(full)) if f"{d}/{n}" not in files] \
                if os.path.isdir(full) else []
        for p in bad:
            print(f"stale: {p}")
        return 1 if bad else 0
    for d in ("tables", "predictions"):
        for n in os.listdir(os.path.join(KP, d)):
            if f"{d}/{n}" not in files:
                os.unlink(os.path.join(KP, d, n))
    for p, b in files.items():
        f = os.path.join(KP, p)
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f, "wb") as fh:
            fh.write(b)
    print(f"wrote {len(files)} files; pins read: {', '.join(sorted(pins.READ))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
