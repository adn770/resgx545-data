# SPDX-License-Identifier: MIT
"""pk.py: r35-pk's rows and frozen models (Q302, closing29/plan/rank-round35.md section 3.3,
R35-1 (a), R35-4 (a) as the lead took it). Every row is the 64 x 64 triangle of `probe --tri
pixel` (t10) with eot_plain in the end-of-tile slot, the render command's word 11 (pixelbe, the
word that loads CR_REG_0400) set by --cmd, the sideband 0x200 | pack mode, every pixel read.
Two shader forms:

  colour  E031's and E268's kept program: o0 = 0x80ff8040 over the background 0xff203040 (the
          known-value controls of each pack mode's layout: E031's kept images)
  ramp    our own src/ramp_xy.s (bins/ramp_xy.bin, assembled by tools/usse-asm): with E385's
          pds_iter_xy (pa0 = x + 0.5, pa1 = y + 0.5, E382's kept xy image) and vtx_coords, X
          and Y as integers from 2^22 + v, then o0 = XOR of X << SX and Y << SY: on the 1062
          triangle pixels every colour is unique and every byte lane (A, R, G, B) takes all
          256 values (2 to 6 pixels each); the background stays 0xff203040

Readings are taken from THIS session's own references (round 34's lesson): each stage starts with
the mode 0 ramp row at 0x80 (a control frozen to the ramp's image by construction, H-RAMP), and
every model's expected image of a row is computed at score time from that stage reference's
pixels, never from a frozen reading:

  match  modes 3 to 6: the mode's image packed from the reference's o0 by the model's rule (the
         per-mode packer, FORMATS), against the row's 4096 dwords: "all" or "N/4096"
         ARGB8888-like modes (and 11): the reference image itself (H-AS0)
  whole  modes 9, 10, 12, 13: every dword written (target, and the scratch past it for 12 and 13)
         is one of the reference's 4096 values: "all", else "notall"
  rel    stage r3: the row against its mode's 0x80 reference of the stage and the stage's mode 0
         reference by H-1136's rule (bit 25 inverts the mode's alpha field, the low byte sets
         mode 4's alpha where alpha >= it): "all" or "N/4096"
  thr    s0's mode 4 ramp control: "MAXCLEAR,MINSET" of the stored alpha bit over the ramp's alphas
"""
import re
import struct

SENT = 0xDEADBEEF
BG = 0xFF203040
E031 = "data:pbe/pack-modes/pbe-pack-modes-packmode-%02d"
E385 = "data:pbe/reg-0400-alpha/pbe-reg-0400-alpha-%s"
E382 = "data:pbe/emit-transforms/pbe-emit-transforms-xy"
BINS = {
    "eot_plain.bin": E031 % 0 + "/bins/eot_plain.bin",
    "colour.bin": E031 % 0 + "/bins/pbe-pack-modes-packmode-00__0.bin",
    "pds_iter_xy.bin": E385 % "mode4" + "/bins/pds_iter_xy.bin",
    "vtx_coords.bin": E385 % "mode4" + "/bins/vtx_coords.bin",
}
RAMP_SRC = "src/ramp_xy.s"
RAMP_BIN = "ramp_xy.bin"
PDS_DATA = 12                     # pds_iter_xy.s's data dwords (probe.py: pixpds=...:12)
W080 = 0x80
R3_WORDS = (0x02000040, 0x020000C0)  # clause (e): bit 25 with another low byte
SX = (0, 8, 16, 20, 25)
SY = (4, 11, 19, 22, 29)

# ---- E031's classes -------------------------------------------------------------------------
ARGB = [0, 11, 16, 17, 19, 21, 23] + list(range(29, 34)) + list(range(35, 64))
assert len(ARGB) == 41
ARGB40 = [m for m in ARGB if m != 0]
NARROW = (3, 4, 5, 6)              # the narrowed modes of the line: (d) is 3, (a) 4 to 6
WHOLE = (9, 10, 12, 13)            # E031: whole 32-bit colours into part of the target
PAST = (12, 13)                    # E031: they write past the target (stage pw, last)
FAULTS = (14,)                     # E031: faults in both runs: never run (R35-4 (a))
Q012 = (22, 26, 34)                # not this question's (Q012): never run
R1_MODES = (3, 4, 5, 6, 9, 10, 11)
R3_MODES = (0, 4, 5, 6)
COL_CONTROLS = (3, 4, 5, 6, 7, 9, 10)   # s0's E031 colour repeats (the layout of each form)

# fields of the narrowed modes (E031's table, read from the stored bit patterns): (channel,
# width, shift); width "thr" is mode 4's one-bit alpha, set where alpha >= the low byte (E1136)
FORMATS = {
    3: (("R", 5, 11), ("G", 6, 5), ("B", 5, 0)),
    4: (("A", "thr", 15), ("R", 5, 10), ("G", 5, 5), ("B", 5, 0)),
    5: (("A", 4, 12), ("R", 4, 8), ("G", 4, 4), ("B", 4, 0)),
    6: (("A", 8, 8), ("R", 3, 5), ("G", 3, 2), ("B", 2, 0)),
    7: (("A", 8, 8), ("R", 8, 0)),
}
SHIFT = {"A": 24, "R": 16, "G": 8, "B": 0}
# the bit-25 field of each mode (E268, E1135): what H-1136 inverts
INV25 = {0: 0xFF000000, 4: 0x80008000, 5: 0xF000F000, 6: 0xFF00FF00}


# ---- the four frozen rounding rules: an 8-bit channel v to w bits ---------------------------
def rz(v, w):
    """H-RZ: truncate."""
    return v >> (8 - w)


def rn(v, w):
    """H-RN: round half up, saturated."""
    return min((v + (1 << (7 - w))) >> (8 - w), (1 << w) - 1)


def rne(v, w):
    """H-RNE: round half to even, saturated."""
    s = 8 - w
    q, r, h = v >> s, v & ((1 << s) - 1), 1 << (s - 1)
    if r > h or (r == h and q & 1):
        q += 1
    return min(q, (1 << w) - 1)


def scale(v, w):
    """H-SCALE: round(v (2^w - 1) / 255), half up."""
    m = (1 << w) - 1
    return (2 * v * m + 255) // 510


RULES = {"H-RZ": rz, "H-RN": rn, "H-RNE": rne, "H-SCALE": scale}


# ---- the ramp -------------------------------------------------------------------------------
def ramp_word(x, y):
    w = 0
    for s in SX:
        w ^= x << s
    for s in SY:
        w ^= y << s
    return w & 0xFFFFFFFF


def single(v):
    return struct.unpack("<I", struct.pack("<f", v))[0]


ROW = re.compile(r"^probe (\S+): row (\d+): ([0-9a-fA-F ]+)$", re.M)
SCR = re.compile(r"^probe \S+: scratch \+0x([0-9a-fA-F]+) 0x([0-9a-fA-F]+)$", re.M)


def images(text):
    rows = {}
    for m in ROW.finditer(text):
        rows.setdefault(m.group(1), {})[int(m.group(2))] = [int(t, 16) for t in m.group(3).split()]
    out = {}
    for n, r in rows.items():
        if sorted(r) == list(range(64)) and all(len(v) == 64 for v in r.values()):
            out[n] = [v for y in range(64) for v in r[y]]
    return out


def kept(blob, base, case):
    return images(blob(base + "/raw.txt").decode(errors="replace"))[case]


def xy_image(blob):
    """E382's kept xy image (pix_xy: (pa0 & 0xffff0000) | (pa1 >> 16)), its neutral case."""
    return kept(blob, E382, "pbe-emit-transforms-xy__0")


def triangle(blob):
    """The 64 x 64 triangle's pixels (raster order: True on the triangle), E382's kept image."""
    return [v != BG for v in xy_image(blob)]


def ramp_image(tri):
    return [ramp_word(i % 64, i // 64) if t else BG for i, t in enumerate(tri)]


# ---- the per-mode packers (the decoder forms) -----------------------------------------------
def pack16(v, mode, rule, low=W080):
    out = 0
    for ch, w, sh in FORMATS[mode]:
        c = (v >> SHIFT[ch]) & 0xFF
        if w == "thr":
            out |= (1 if c >= low else 0) << sh
        elif w == 8:
            out |= c << sh
        else:
            out |= rule(c, w) << sh
    return out


def image16(src, mode, rule, low=W080):
    """The mode's 4096-dword image of a 64 x 64 o0 image: two pixels a dword (pixel 2i in bits
    15:0), raster order, the second half of the target left at the sentinel (E031)."""
    p = [pack16(v, mode, rule, low) for v in src]
    return [p[2 * i] | p[2 * i + 1] << 16 for i in range(2048)] + [SENT] * 2048


def predict(src, mode, model, low=W080):
    """The image `model` predicts for a mode-`mode` row at low byte `low` from the o0 image src."""
    if model in RULES:
        return image16(src, mode, RULES[model], low)
    if model == "H-AS0":
        return list(src)
    raise KeyError(model)


def rel1136(ref_mode, ref0, mode, word):
    """H-1136's image of a stage r3 row: its mode's 0x80 reference with bit 25's field inverted
    (E1135, E268) and, in mode 4, the one-bit alpha set where alpha >= the low byte (E1136)
    before the inversion; alphas from the stage's mode 0 reference."""
    if mode != 4:
        return [v if v == SENT else v ^ INV25[mode] for v in ref_mode]
    low, out = word & 0xFF, []
    for i, v in enumerate(ref_mode):
        if i >= 2048:
            out.append(v)
            continue
        hs = []
        for k, h in enumerate((v & 0xFFFF, v >> 16)):
            a = ref0[2 * i + k] >> 24
            bit = (1 if a >= low else 0) ^ (1 if word & 0x02000000 else 0)
            hs.append((h & 0x7FFF) | bit << 15)
        out.append(hs[0] | hs[1] << 16)
    return out


def match(want, got):
    """"all" when the 4096 dwords agree, else "N/4096"; None without an image."""
    if want is None or got is None:
        return None
    n = sum(a == b for a, b in zip(want, got))
    return "all" if n == len(want) == len(got) else f"{n}/{len(want)}"


def whole(ref, img, scratch=()):
    """"all" when every dword written (not the sentinel) and every scratch dword is one of the
    reference's values, else "notall"; with (written, members, pixels named)."""
    if ref is None or img is None:
        return None, (0, 0, 0)
    vals = set(ref)
    wr = [v for v in img if v != SENT] + list(scratch)
    inn = [v for v in wr if v in vals]
    return ("all" if wr and len(inn) == len(wr) else "notall"), (len(wr), len(inn), len(set(inn)))


def thr_of(alpha, img):
    """`thr` of a mode-4 image over the alphas of the pixels: "MAXCLEAR,MINSET" or "mixed"."""
    if img is None:
        return None
    halves = [h for v in img[:2048] for h in (v & 0xFFFF, v >> 16)]
    clear = [a for a, h in zip(alpha, halves) if not h >> 15]
    sets = [a for a, h in zip(alpha, halves) if h >> 15]
    mc, ms = (max(clear) if clear else None), (min(sets) if sets else None)
    if mc is not None and ms is not None and mc >= ms:
        return "mixed"
    return f"{'-' if mc is None else mc},{'-' if ms is None else ms}"


def channel_fits(src, mode, img):
    """Per channel of a narrowed mode, the rules that fit every pixel (a reading, not a verdict):
    {channel: [model, ...]}."""
    if src is None or img is None:
        return None
    halves = [h for v in img[:2048] for h in (v & 0xFFFF, v >> 16)]
    out = {}
    for ch, w, sh in FORMATS[mode]:
        if w in ("thr", 8):
            continue
        mask = (1 << w) - 1
        out[ch] = [m for m, f in RULES.items()
                   if all((h >> sh) & mask == f((v >> SHIFT[ch]) & 0xFF, w)
                          for v, h in zip(src, halves))]
    return out


# ---- argv -----------------------------------------------------------------------------------
HEAD = "probe --temps 32 --pixels --tri pixel --width 64 --height 64"


def args(form, mode, word):
    sb = 0x200 | mode
    if form == "colour":
        return (f'{HEAD} --cmd 11=0x{word:08x} --sideband 0x{sb:08x} '
                f'--slot eot="$S/bins/eot_plain.bin" "$S/bins/colour.bin"')
    return (f'{HEAD} --vtx-coords 2 --cmd 11=0x{word:08x} --sideband 0x{sb:08x} '
            f'--slot eot="$S/bins/eot_plain.bin" --slot pixpds="$S/bins/pds_iter_xy.bin:{PDS_DATA}" '
            f'--slot vtxuse="$S/bins/vtx_coords.bin" "$S/bins/{RAMP_BIN}"')


# ---- the rows -------------------------------------------------------------------------------
def row(name, st, form, mode, word, pixels=None, q=None, src=""):
    knobs = "reads:pixels" if st == "control" else "-"
    return dict(name=name, set=st, knobs=knobs, args=args(form, mode, word),
                pixels=pixels or {}, q=q or {}, src=src, mode=mode, word=word, form=form)


def ramp_ref(stage, ramp):
    return row(f"{stage}-m00-ref", "control", "ramp", 0, W080, {"H-RAMP": ramp},
               src="the ramp's image by construction (src/ramp_xy.s, gen/pk.py ramp_word) on "
                   "E382's triangle: mode 0 stores o0 as it is (E031); the stage's reference")


def q_round():
    return {"match": {m: "all" for m in RULES}}


def jobs(blob):
    """{stage: [row]} in run order."""
    tri = triangle(blob)
    ramp = ramp_image(tri)
    k031 = lambda m: kept(blob, E031 % m, f"pbe-pack-modes-packmode-{m:02d}__0")  # noqa: E731
    out = {}
    s0 = [row("s0-m00-ref", "control", "ramp", 0, W080, {"H-RAMP": ramp},
              src="the ramp's image by construction (src/ramp_xy.s, gen/pk.py ramp_word) on "
                  "E382's triangle: mode 0 stores o0 as it is (E031)"),
          row("s0-m04-ramp", "control", "ramp", 4, W080,
              q={"thr": {"H-E1136": thr_of([v >> 24 for v in ramp], image16(ramp, 4, rz))}},
              src="E1136: mode 4's alpha bit set where alpha >= the low byte 0x80; the ramp's "
                  "alphas 0 to 255 by construction")]
    for m in COL_CONTROLS:
        s0.append(row(f"s0-m{m:02d}-col", "control", "colour", m, W080, {"H-E031": k031(m)},
                      src="E031's kept image of the mode (r34-q044 repeated it, E1135)"))
    out["s0"] = s0
    r1 = [ramp_ref("r1", ramp)]
    for rep, modes in (("a", R1_MODES), ("b", tuple(reversed(R1_MODES)))):
        for m in modes:
            if m in NARROW:
                q, src = q_round(), ("fit: E385's mode 5 alpha (4 bits, 47 alphas) H-RZ only; "
                                     "E031's mode 6 green 0x30 H-RZ and H-SCALE")
            elif m in WHOLE:
                q, src = {"whole": {"H-WHOLE": "all", "H-NARROW": "notall"}}, \
                    "E031: modes 9 and 10 store whole 32-bit colours"
            else:
                q, src = {"match": {"H-AS0": "all", "H-AS0-PART": "notall"}}, \
                    "E031: mode 11 stores as ARGB8888 for its two colours"
            r1.append(row(f"r1-m{m:02d}-{rep}", "heldout", "ramp", m, W080, q=q, src=src))
    out["r1"] = r1
    r2 = [ramp_ref("r2", ramp)]
    for m in ARGB40:
        r2.append(row(f"r2-m{m:02d}", "heldout", "ramp", m, W080,
                      q={"match": {"H-AS0": "all", "H-AS0-PART": "notall"}},
                      src="E031: the 40 ARGB8888-like modes store mode 0's image for its colours"))
    out["r2"] = r2
    r3 = [ramp_ref("r3", ramp)]
    for m in R3_MODES[1:]:
        r3.append(row(f"r3-m{m:02d}-ref", "ref", "ramp", m, W080,
                      src="the stage's reference of the mode at 0x80"))
    for rep in ("a", "b"):
        cells = [(m, w) for m in R3_MODES for w in R3_WORDS]
        for m, w in (cells if rep == "a" else list(reversed(cells))):
            r3.append(row(f"r3-m{m:02d}-w{w:08x}-{rep}", "heldout", "ramp", m, w,
                          q={"rel": {"H-1136": "all", "H-LOWDEP": "notall"}},
                          src="E1135 (bit 25 inverts the alpha in 0, 4, 5, 6 at 0x80), E1136 "
                              "(the low byte thresholds mode 4's alpha only), E268"))
    out["r3"] = r3
    pw = [ramp_ref("pw", ramp)]
    for m in PAST:
        pw.append(row(f"pw-m{m:02d}-col", "control", "colour", m, W080, {"H-E031": k031(m)},
                      src="E031's kept image of the mode (the target's 4096 dwords)"))
    for m in PAST + tuple(reversed(PAST)):
        rep = "a" if not [r for r in pw if r["name"] == f"pw-m{m:02d}-a"] else "b"
        pw.append(row(f"pw-m{m:02d}-{rep}", "heldout", "ramp", m, W080,
                      q={"whole": {"H-WHOLE": "all", "H-NARROW": "notall"}},
                      src="E031: modes 12 and 13 store whole colours, in the target and past it"))
    out["pw"] = pw
    return out
