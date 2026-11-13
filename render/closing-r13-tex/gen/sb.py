# SPDX-License-Identifier: MIT
"""sb.py: stage sb12 (r13-tex, Q046 sideband bit 12; closing13/plan/rank-round13.md section 2
"sb12"): E383's form (probes/pbe/sideband-channels.toml, r10-x's sb rows: the 64 x 64 triangle,
the eot slot eot_plain, a pixel shader writing 0xc0804020 (colour 0) or 0x13579bdf (colour 1),
every pixel read back) with sideband bit 12 in pack modes 0 to 6, both colours, and one row at a
moved triangle. The programs are E383's published bins (copied into bins/ by gen/make.py).

E383 ran bit 12 twice per mode, both runs colour 0 (its two bins are the same file, colour 0's):
its words are not one image run to run (modes 1, 2, 3, 4, 5, 6 differ on 256, 14, 138, 5, 6
and 10 of 4096 pixels; mode 0 on none), but each mode's set of words is the same in both runs
(mode 3: 2 pixels of a word the other run lacks). So the reading is the set: `inset`, the pixels
whose word is one of E383's words of that mode (both runs, predictions/sb12/words-mN.txt).

Frozen (nothing here ran with colour 1 or a moved triangle):
  H-FIXED     the words do not depend on the colour or the triangle's place: inset >= 4055
              (99% of 4096; E383's two runs: 4094 to 4096)
  H-O0        the words are a function of o0: colour 1 changes them, inset < 4055
  H-FIXED-PX  (mode 0 rows) E383's mode 0 image pixel for pixel (its two runs were equal)
  H-SHIFT     (the moved row, colour 0, so only the place changes) E383's mode 0 image moved
              with the triangle (4, 4) pixels (the pixels moved in from outside `-`); H-FIXED's
              inset rule holds the moved row too
Controls that can fail: E383's mode 8 job at field 0 (0x208, colour 0, its kept image, r10-x's
control) and the mode 0 colour 0 replicate (H-FIXED's inset rule: E383's own row again)."""
import re

E383 = "data:pbe/sideband-channels"
EOT = f"{E383}/pbe-sideband-channels-0208/bins/eot_plain.bin"
COLOUR = {0: f"{E383}/pbe-sideband-channels-0208/bins/pbe-sideband-channels-0208__0.bin",
          1: f"{E383}/pbe-sideband-channels-0208/bins/pbe-sideband-channels-0208__1.bin"}
BINS = {"eot_plain.bin": EOT, "sb-c0.bin": COLOUR[0], "sb-c1.bin": COLOUR[1]}
RAW = f"{E383}/pbe-sideband-channels-%s/raw.txt"
BIT12 = "bit12-12%02x"
ROW = re.compile(r"^probe (\S+): row (\d+): ([0-9a-fA-F ]+)$", re.M)
INSET_MIN = 4055
DEFAULT_V = ((8, 8), (56, 20), (20, 56))      # sgxfive_tri_default at 64 x 64 (render.c)
MOVE = (4, 4)


def tri_v():
    """--tri-v of the default triangle moved by MOVE pixels, in 1/256 pixel."""
    return ",".join(str((c + MOVE[i]) * 256) for v in DEFAULT_V for i, c in enumerate(v))


def args(sideband, colour, moved=False):
    mv = f" --tri-v {tri_v()}" if moved else ""
    return (f'probe --tri pixel --pixels --slot eot="$S/bins/eot_plain.bin" --sideband '
            f'{sideband:#x}{mv} "$S/bins/sb-c{colour}.bin"')


def case_images(text):
    rows = {}
    for m in ROW.finditer(text):
        rows.setdefault(m.group(1), {})[int(m.group(2))] = [int(t, 16) for t in m.group(3).split()]
    return {n: [v for y in sorted(r) for v in r[y]] for n, r in rows.items()
            if sorted(r) == list(range(len(r)))}


def kept(blob, code):
    """[images of the kept runs] of E383's sideband code (0x208, 0x1200 ...)."""
    d = f"{code:04x}" if code < 0x1000 else BIT12 % (code & 0xFF)
    ims = case_images(blob(RAW % d).decode())
    return [ims[k] for k in sorted(ims)]


def words(blob, mode):
    return sorted({v for im in kept(blob, 0x1200 | mode) for v in im})


def shifted(img):
    out = []
    for y in range(64):
        for x in range(64):
            sx, sy = x - MOVE[0], y - MOVE[1]
            out.append(img[sy * 64 + sx] if 0 <= sx < 64 and 0 <= sy < 64 else None)
    return out


def jobs(blob):
    """[(name, set, knobs, args, {model: image or None}, {quantity: {model: value}}, mode)]"""
    m8 = kept(blob, 0x208)[0]
    m0 = kept(blob, 0x1200)[0]
    q = {"inset": {"H-FIXED": f">={INSET_MIN}", "H-O0": f"<{INSET_MIN}"}}
    qrep = {"inset": {"H-FIXED": f">={INSET_MIN}"}}
    out = [("sb12-ctl-m8", "control", "reads:pixels", args(0x208, 0), {"H-E383": m8}, {}, 8),
           ("sb12-rep-m0-c0", "control", "reads:pixels", args(0x1200, 0), {}, qrep, 0)]
    for mode in range(1, 7):
        out.append((f"sb12-m{mode}-c0", "replicate", "-", args(0x1200 | mode, 0), {}, qrep, mode))
    for mode in range(7):
        px = {"H-FIXED-PX": m0} if mode == 0 else {}
        out.append((f"sb12-m{mode}-c1", "heldout", "-", args(0x1200 | mode, 1), px, q, mode))
    out.append(("sb12-mv-m0-c0", "heldout", "-", args(0x1200, 0, moved=True),
                {"H-FIXED-PX": m0, "H-SHIFT": shifted(m0)}, qrep, 0))
    return out
