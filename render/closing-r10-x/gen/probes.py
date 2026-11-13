# SPDX-License-Identifier: MIT
"""probes.py: r10-x's `probe --tri` stages, sb and win0, their programs the published bins of the
records they repeat (copied into bins/ by gen/make.py from the pinned data files).

sb (R10-F: Q046): E383's form (probes/pbe/sideband-channels.toml: the 64 x 64 triangle, the eot
slot eot_plain, a pixel shader writing 0xc0804020 or 0x13579bdf, colours whose bytes all differ,
every pixel read) in pack modes 20 and 27 (never run with the field) with sideband bits 8:6 at 0
to 3 and both colours: 16 jobs. Frozen per pixel from E383's kept images: H-LOW16 (the field
ignored, the image of E383's mode 15 job of the same colour: modes 15, 18 and 28, which also store
the low 16 bits, gave byte-identical images at every field value) and H-M7 (the field selects as
in mode 7: E383's 0x207 image at field 0, 0x247 at 1 to 3). Controls that can fail: E383's mode 8
jobs at field 0 (0x208, both colours, their kept images).

win0 (R10-B: Q030): E502's identity maps (probes/isp/msaa-ident.toml: probe --tri pixpds:12
--tri-full, E437's primary PDS program iterating source 0, a pixel shader writing pa0 (an x job)
or pa1 (a y job) as the colour, cmd:13 the mode, cmd:10 and cmd:16 0xeaa26e26, cmd:1 the TE word)
in mode 0 with TE 0x60000000, 0xa0000000, 0xe0000000 at 64 x 64 and 128 x 96: 12 jobs. Every row
carries dbg:render_rgn_arrays=1: a TE_AA with bit 31 or 30 needs a context that may take one, and
the probe has no --aa4; the knob makes every new render context take one (fork 2a650d74
sgxfive_render.c sgxfive_render_init: ctx->aa_ms = aa4 || setting, for every context of the render
type, the probe's included) and forces E502's one region-header array. E502's own program files
(p1126-pos-x__0.bin, p1126-pos-y__0.bin) are not published; the rows use E437's published program
(dpm-partial-reload-pos-pa0__0.bin, the same file for pa0 and pa1, 12 data dwords, DOUTI
0x20400000) and its pix_pa0/pix_pa1 shaders, and the controls say whether that is E502's set.
Frozen per pixel (x job: the float of the source x + 0.375, y job: y + 0.125, E502; a hole: the
background 0xff203040): H-IDENT (the landed region model, msaa_model.py, mode 0: holes where it
stores nothing (E953), every other pixel its own), H-IDFULL (every pixel its own, no hole) and
H-WIN (the region model's pixels, each the pixel 16 b31 right and 8 b30 down of its own, modes 1
and 2's window offsets of E503). Controls that can fail: E502's A-m1-tee0-64x64-x (mode 1, TE
0xe0000000) and A-m0-te20-64x64-x (mode 0, TE 0x20000000), their kept images."""
import re
import struct

BG = 0xFF203040
SAMPLE = 0xEAA26E26
E383 = "pbe/sideband-channels"
E502 = "isp/msaa-ident/dumps"
POS = "dpm/partial-reload-pos/dpm-partial-reload-pos-pa0/bins/dpm-partial-reload-pos-pa0__0.bin"
PIX = {"x": "dpm/partial-reload-pos/dpm-partial-reload-pos-pa0/bins/pix_pa0.bin",
       "y": "dpm/partial-reload-pos/dpm-partial-reload-pos-pa1/bins/pix_pa1.bin"}
EOT = f"{E383}/pbe-sideband-channels-0208/bins/eot_plain.bin"
COLOUR = {0: f"{E383}/pbe-sideband-channels-0208/bins/pbe-sideband-channels-0208__0.bin",
          1: f"{E383}/pbe-sideband-channels-0208/bins/pbe-sideband-channels-0208__1.bin"}
BINS = {"pos.bin": POS, "pix_pa0.bin": PIX["x"], "pix_pa1.bin": PIX["y"], "eot_plain.bin": EOT,
        "sb-c0.bin": COLOUR[0], "sb-c1.bin": COLOUR[1]}
ROW = re.compile(r"^probe (\S+): row (\d+): ([0-9a-fA-F ]+)$", re.M)


def case_images(text):
    """{probe case name: [pixels in raster order]} of an output holding one or more cases."""
    rows = {}
    for m in ROW.finditer(text):
        rows.setdefault(m.group(1), {})[int(m.group(2))] = [int(t, 16) for t in m.group(3).split()]
    return {n: [v for y in sorted(r) for v in r[y]] for n, r in rows.items()
            if sorted(r) == list(range(len(r)))}


# ---- sb -----------------------------------------------------------------------------------
SB_MODES = (20, 27)


def sb_args(sideband, colour):
    return (f'probe --tri pixel --pixels --slot eot="$S/bins/eot_plain.bin" --sideband '
            f'{sideband:#x} "$S/bins/sb-c{colour}.bin"')


def sb_jobs(kept):
    """kept(code) the {case: image} of E383's sideband code (0x208 ...). [(name, set, knobs,
    args, {model: image})]."""
    out = []
    ctl = kept(0x208)
    for c in (0, 1):
        out.append((f"sb-ctl-0208-c{c}", "control", "reads:pixels", sb_args(0x208, c),
                    {"H-E383": ctl[f"pbe-sideband-channels-0208__{c}"]}))
    low = kept(0x20F)
    m7 = {0: kept(0x207), 1: kept(0x247)}
    for mode in SB_MODES:
        for f in range(4):
            sb = 0x200 | f << 6 | mode
            for c in (0, 1):
                models = {"H-LOW16": low[f"pbe-sideband-channels-020f__{c}"],
                          "H-M7": m7[min(f, 1)][f"pbe-sideband-channels-{0x207 if f == 0 else 0x247:04x}__{c}"]}
                out.append((f"sb-m{mode}-f{f}-c{c}", "heldout", "-", sb_args(sb, c), models))
    return out


# ---- win0 ----------------------------------------------------------------------------------
WIN_TE = (0x60000000, 0xA0000000, 0xE0000000)
WIN_SIZES = ((64, 64), (128, 96))
KNOB = "dbg:render_rgn_arrays=1"


def win_args(w, h, mode, te, ax):
    return (f"probe --tri pixpds:12 --temps 32 --pixels --width {w} --height {h} --tri-full "
            f"--cmd 1={te:#010x} --cmd 10={SAMPLE:#010x} --cmd 13={0x80000000 | mode:#010x} "
            f'--cmd 16={SAMPLE:#010x} --slot pixel="$S/bins/pix_pa{0 if ax == "x" else 1}.bin" '
            '"$S/bins/pos.bin"')


def f32bits(v):
    return struct.unpack("<I", struct.pack("<f", v))[0]


def win_image(M, w, h, te, ax, model):
    """The frozen image of a mode-0 identity-map job under a model (M: the region model)."""
    b31, b30 = te >> 31 & 1, te >> 30 & 1
    drawn = (None if model == "H-IDFULL" else
             M.predict(M.tri_full(w, h), w, h, 0, te))
    im = []
    for y in range(h):
        for x in range(w):
            if drawn is not None and (x, y) not in drawn:
                im.append(BG)
                continue
            sx, sy = (x + 16 * b31, y + 8 * b30) if model == "H-WIN" else (x, y)
            im.append(f32bits(sx + 0.375) if ax == "x" else f32bits(sy + 0.125))
    return im


WIN_MODELS = ("H-IDENT", "H-IDFULL", "H-WIN")


def win_jobs(M, kept):
    """kept(name) the image of E502's kept job NAME. [(name, set, knobs, args, {model: image})]."""
    out = [("w0-ctl-m1-tee0-64x64-x", "control", f"{KNOB} reads:pixels",
            win_args(64, 64, 1, 0xE0000000, "x"), {"H-E502": kept("A-m1-tee0-64x64-x")}),
           ("w0-ctl-m0-te20-64x64-x", "control", f"{KNOB} reads:pixels",
            win_args(64, 64, 0, 0x20000000, "x"), {"H-E502": kept("A-m0-te20-64x64-x")})]
    for w, h in WIN_SIZES:
        for te in WIN_TE:
            for ax in ("x", "y"):
                out.append((f"w0-te{te >> 24:02x}-{w}x{h}-{ax}", "heldout", KNOB,
                            win_args(w, h, 0, te, ax),
                            {m: win_image(M, w, h, te, ax, m) for m in WIN_MODELS}))
    return out
