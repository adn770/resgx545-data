# SPDX-License-Identifier: MIT
"""q044.py: r34-q044's rows and frozen models (Q044, closing29/plan/rank-round34.md section 3.2,
R34-1 (a), R34-4 (a)). Every row is the 64 x 64 triangle of `probe --tri pixel` (t10) with
eot_plain in the end-of-tile slot, the render command's word 11 (pixelbe, the word that loads
CR_REG_0400: include/uapi/sgxfive_drm.h at a581c06, word 11 of drm_sgxfive_render_cmd, 0x80 as
render.c builds it) set by --cmd on every row, the sideband 0x200 | pack mode, every pixel read.
Two shader forms, both kept programs (bins/ copies the published bins byte for byte):

  colour  E031's and E268's form: o0 = 0x80ff8040 over the background 0xff203040
  ramp    E385's form: pds_iter_xy (pa0 = x + 0.5) and an alpha of bits 23:16 of pa0 as a
          single, 0x00ff8040 in RGB, vtx_coords; the alpha per pixel is E385's kept mode 0 image
          (64 values over the columns, 47 of them on the triangle's columns 8 to 54)

The reading of a row against a reference row of THIS stage (the lesson of r30-evst and r33-tim:
no control value is frozen from an old reading where a reference of the session can give it):
`xor` is the one value every written dword of the row differs from the reference by (dwords the
reference left at the sentinel 0xdeadbeef must stay so), "mixed" when there are several. The
mode-4 rows of p2 read `thr`: the largest ramp alpha whose stored bit is clear and the smallest
whose bit is set, "MAXCLEAR,MINSET". Kept images (E031, E268, E385) are frozen only as the
controls and as the p1 references' replicate model H-E031."""
import re
import struct

SENT = 0xDEADBEEF
BG = 0xFF203040
E031 = "data:pbe/pack-modes/pbe-pack-modes-packmode-%02d"
E268 = "data:pbe/reg-0400-modes/pbe-reg-0400-modes-0"
E385 = "data:pbe/reg-0400-alpha/pbe-reg-0400-alpha-%s"
TOML268 = "resgx545:probes/pbe/reg-0400-modes.toml"
TOML385 = "resgx545:probes/pbe/reg-0400-alpha.toml"
BINS = {
    "eot_plain.bin": E031 % 0 + "/bins/eot_plain.bin",
    "colour.bin": E031 % 0 + "/bins/pbe-pack-modes-packmode-00__0.bin",
    "ramp.bin": E385 % "mode4" + "/bins/pbe-reg-0400-alpha-mode4__0.bin",
    "pds_iter_xy.bin": E385 % "mode4" + "/bins/pds_iter_xy.bin",
    "vtx_coords.bin": E385 % "mode4" + "/bins/vtx_coords.bin",
}
PDS_DATA = 12                     # pds_iter_xy.s's data dwords (probe.py: pixpds=...:12)
W080, B25 = 0x80, 0x02000080

# ---- E031's classes (its table) and the frozen bit-25 masks ------------------------------------
ARGB = [0, 11, 16, 17, 19, 21, 23] + list(range(29, 34)) + list(range(35, 64))
assert len(ARGB) == 41
NOALPHA = [3, 15, 18, 20, 24, 25, 27, 28, 26]      # E031: RGB565, G/B halves, B8; 26: Q012 (E270)
Q012 = (22, 34)                                     # not repeating (E031, E032): Q012's formats
FAULTS = (14,)                                      # E031: faults in both runs: never run
PAST = (12, 13)                                     # E031: write past the target (stage pw)
INV25 = {4: 0x80008000, 5: 0xF000F000, 6: 0xFF00FF00, 7: 0xFF00FF00, 8: 0,
         9: 0xFF000000, 10: 0xFF000000, 12: 0xFF000000, 13: 0xFF000000}
INV25.update({m: 0xFF000000 for m in ARGB})
INV25.update({1: 0xFF000000, 2: 0x000000FF})
INV25.update({m: 0 for m in NOALPHA})
SUBSET = {m: (INV25[m] if m in (0, 1, 2, 4, 5) else 0) for m in INV25}
P1_MODES = [m for m in range(4, 64) if m not in FAULTS + PAST]
P1_FIT = (4, 5, 8)                 # E385 ran bit 25 in these (ramp form): fit, not held out
REPEAT2 = (22, 26, 34)             # a second reference after the bit-25 row (E031: 22, 34 vary)

# ---- p2 -------------------------------------------------------------------------------------
EQ = (0x02, 0x08, 0x3E, 0x42, 0x78, 0x84, 0xBC, 0xC4, 0xFC)   # ramp values on the triangle
LOW_MODES_FULL = (5, 6, 7, 8)       # alpha 4 or 8 bits beside other channels, or alone
LOW_MODES = (1, 2, 9, 10, 11)       # 8-bit alpha, as mode 0 (E385: no low byte changes mode 0)
LOW_FULL = (0x000, 0x040, 0x0C0, 0x0FF, 0xF80)
LOW_SHORT = (0x040, 0x0C0, 0xF80)
F80_MODES = (3, 15, 20, 24, 26, 27)  # one mode of each class without alpha: bits 11:8 only
P2_REPEAT2 = (26,)


def ramp_alpha():
    """E385's alpha per column: bits 23:16 of x + 0.5 as a single."""
    return [(struct.unpack("<I", struct.pack("<f", x + 0.5))[0] >> 16) & 0xFF for x in range(64)]


# ---- argv -----------------------------------------------------------------------------------
HEAD = "probe --temps 32 --pixels --tri pixel --width 64 --height 64"


def args(form, mode, word):
    sb = 0x200 | mode
    if form == "colour":
        return (f'{HEAD} --cmd 11=0x{word:08x} --sideband 0x{sb:08x} '
                f'--slot eot="$S/bins/eot_plain.bin" "$S/bins/colour.bin"')
    return (f'{HEAD} --vtx-coords 2 --cmd 11=0x{word:08x} --sideband 0x{sb:08x} '
            f'--slot eot="$S/bins/eot_plain.bin" --slot pixpds="$S/bins/pds_iter_xy.bin:{PDS_DATA}" '
            f'--slot vtxuse="$S/bins/vtx_coords.bin" "$S/bins/ramp.bin"')


# ---- kept images ----------------------------------------------------------------------------
ROW = re.compile(r"^probe (\S+): row (\d+): ([0-9a-fA-F ]+)$", re.M)


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


def case_words(blob, pin, probe):
    """The word-11 value of each case of a probe of a pinned table (case index -> value)."""
    import tomllib
    t = tomllib.loads(blob(pin).decode())
    p = [p for p in t["probe"] if p["name"] == probe][0]
    return [c["cmd"]["11"] for c in p["case_set"]]


def alpha_map(blob):
    """E385's kept mode 0 image at 0x80: the alpha byte per triangle pixel, None elsewhere."""
    im = kept(blob, E385 % "mode0", "pbe-reg-0400-alpha-mode0__0")
    return [None if v == BG else v >> 24 for v in im]


def thr_of(alpha, img):
    """`thr` of a mode-4 image (two pixels a dword, the alpha in bit 15 of each half)."""
    if img is None:
        return None
    halves = [h for v in img for h in (v & 0xFFFF, v >> 16)]
    clear = [a for a, h in zip(alpha, halves) if a is not None and not h >> 15]
    sets = [a for a, h in zip(alpha, halves) if a is not None and h >> 15]
    mc, ms = (max(clear) if clear else None), (min(sets) if sets else None)
    if mc is not None and ms is not None and mc >= ms:
        return "mixed"
    return f"{'-' if mc is None else mc},{'-' if ms is None else ms}"


def thr_model(alpha, low, ge):
    vals = sorted({a for a in alpha if a is not None})
    if ge:
        clear, sets = [a for a in vals if a < low], [a for a in vals if a >= low]
    else:
        clear, sets = [a for a in vals if a <= low], [a for a in vals if a > low]
    return f"{max(clear) if clear else '-'},{min(sets) if sets else '-'}"


def xor_of(ref, img, ref2=None):
    """(`xor`, dwords compared): the one value img differs from ref by over the dwords ref wrote
    (and ref2 repeats, when given), the sentinel dwords unchanged; "mixed" otherwise."""
    if ref is None or img is None:
        return None, 0
    xs, n = set(), 0
    for i, (r, v) in enumerate(zip(ref, img)):
        if ref2 is not None and ref2[i] != r:
            continue
        if r == SENT:
            if v != SENT:
                return "mixed", n
            continue
        n += 1
        xs.add(r ^ v)
    if len(xs) != 1:
        return ("mixed" if xs else None), n
    return f"0x{xs.pop():08x}", n


# ---- the rows -------------------------------------------------------------------------------
def row(name, st, form, mode, word, pixels=None, q=None, src=""):
    knobs = "reads:pixels" if st == "control" else "-"
    return dict(name=name, set=st, knobs=knobs, args=args(form, mode, word),
                pixels=pixels or {}, q=q or {}, src=src, mode=mode, word=word, form=form)


def jobs(blob):
    """{stage: [row]} in run order."""
    w268 = case_words(blob, TOML268, "pbe-reg-0400-modes-0")
    assert (w268[0], w268[1], w268[13]) == (W080, B25, 0x880), w268
    assert case_words(blob, TOML385, "pbe-reg-0400-alpha-mode0")[0] == W080
    assert case_words(blob, TOML385, "pbe-reg-0400-alpha-mode4")[0] == W080
    for m in ("4", "5", "8"):
        assert case_words(blob, TOML385, f"pbe-reg-0400-alpha-bit25-mode{m}")[:2] == [W080, B25]
    k268 = lambda c: kept(blob, E268, f"pbe-reg-0400-modes-0__{c}")      # noqa: E731
    k385 = lambda p, c: kept(blob, E385 % p, f"pbe-reg-0400-alpha-{p}__{c}")  # noqa: E731
    k031 = lambda m: kept(blob, E031 % m, f"pbe-pack-modes-packmode-{m:02d}__0")  # noqa: E731
    alpha = alpha_map(blob)
    out = {}
    out["s0"] = [
        row("s0-m00-w080", "control", "colour", 0, W080, {"H-E268": k268(0)},
            src="E268's kept pbe-reg-0400-modes-0__0 (= E031's mode 0)"),
        row("s0-m00-b25", "control", "colour", 0, B25, {"H-E268": k268(1)},
            src="E268's kept pbe-reg-0400-modes-0__1 (bit 25 inverts the alpha)"),
        row("s0-m00-w880", "control", "colour", 0, 0x880, {"H-E268": k268(13)},
            src="E268's kept pbe-reg-0400-modes-0__13 (bit 11: nothing)"),
        row("s0-m04-w080", "control", "colour", 4, W080, {"H-E031": k031(4)},
            src="E031's kept packmode-04 (alpha 0x80 at low byte 0x80 stores 1)"),
        row("s0-m04r-w080", "control", "ramp", 4, W080, {"H-E385": k385("mode4", 0)},
            src="E385's kept mode4__0 (clear to 120, set from 132)"),
        row("s0-m04r-b25", "control", "ramp", 4, B25, {"H-E385": k385("bit25-mode4", 1)},
            src="E385's kept bit25-mode4__1 (bit 25 inverts the one-bit alpha)"),
        row("s0-m08r-b25", "control", "ramp", 8, B25, {"H-E385": k385("bit25-mode8", 1)},
            src="E385's kept bit25-mode8__1 (bit 25 changes nothing in mode 8)"),
    ]
    p1 = [row("p1-ctl-m00", "control", "colour", 0, W080, {"H-E268": k268(0)},
              src="E268's kept pbe-reg-0400-modes-0__0")]
    for m in P1_MODES:
        ref = {} if m in Q012 else {"H-E031": k031(m)}
        p1.append(row(f"p1-m{m:02d}-ref", "ref" if m in Q012 else "replicate", "colour", m, W080,
                      ref, src="E031's kept image of the mode (a replicate on 7CE8E38E)"))
        if m in Q012:
            p1.append(row(f"p1-m{m:02d}-b25", "q012", "colour", m, B25,
                          src="no model: mode 22 and 34's formats are Q012's (R34-4 (a))"))
        else:
            st = "fit" if m in P1_FIT else "heldout"
            q = {"xor": {"H-INV25": f"0x{INV25[m]:08x}", "H-SUBSET": f"0x{SUBSET[m]:08x}"}}
            p1.append(row(f"p1-m{m:02d}-b25", st, "colour", m, B25, q=q,
                          src="E031's class of the mode, E268, E385 (gen/q044.py INV25)"))
        if m in REPEAT2:
            q = {} if m in Q012 else {"same": {"H-REPEAT": "4096"}}
            p1.append(row(f"p1-m{m:02d}-ref2", "q012" if m in Q012 else "replicate", "colour", m,
                          W080, q=q, src="E031: mode 26 repeats in two runs, 22 and 34 do not"))
    out["p1"] = p1
    p2 = [row("p2-m00-ref", "control", "ramp", 0, W080, {"H-E385": k385("mode0", 0)},
              src="E385's kept mode0__0 (the alpha map of every ramp row)"),
          row("p2-m04-ref", "control", "ramp", 4, W080, {"H-E385": k385("mode4", 0)},
              src="E385's kept mode4__0")]
    for low in EQ:
        q = {"thr": {"H-GE": thr_model(alpha, low, True), "H-GT": thr_model(alpha, low, False)}}
        p2.append(row(f"p2-m04-e{low:02x}", "heldout", "ramp", 4, low, q=q,
                      src="E385's alpha map; H-GE fit on E031's mode 4 (0x80 at 0x80 set) and "
                          "E385's background (0xff at 0xff set)"))
    for m in LOW_MODES_FULL + LOW_MODES:
        ctl = {5: ("bit25-mode5", 0), 8: ("bit25-mode8", 0)}.get(m)
        p2.append(row(f"p2-m{m:02d}-ref", "control" if ctl else "ref", "ramp", m, W080,
                      {"H-E385": k385(*ctl)} if ctl else {},
                      src=f"E385's kept {ctl[0]}__{ctl[1]}" if ctl else "the stage's reference"))
        for low in (LOW_FULL if m in LOW_MODES_FULL else LOW_SHORT):
            if low == 0xF80:
                q = {"xor": {"H-NULL": "0x00000000", "H-ACT": "nonzero"}}
            else:
                q = {"xor": {"H-THR1": "0x00000000", "H-THRN": "nonzero"}}
            p2.append(row(f"p2-m{m:02d}-w{low:03x}", "heldout", "ramp", m, low, q=q,
                          src="H-THR1 / H-NULL: E268, E385 (nothing in modes 0 to 3, 11:8 nothing "
                              "in 0 and 4)"))
    for m in F80_MODES:
        p2.append(row(f"p2-m{m:02d}-ref", "ref", "ramp", m, W080, src="the stage's reference"))
        p2.append(row(f"p2-m{m:02d}-wf80", "heldout", "ramp", m, 0xF80,
                      q={"xor": {"H-NULL": "0x00000000", "H-ACT": "nonzero"}},
                      src="H-NULL: E268 (bits 11:8 nothing in modes 0 to 3), E385 (0 and 4)"))
        if m in P2_REPEAT2:
            p2.append(row(f"p2-m{m:02d}-ref2", "replicate", "ramp", m, W080,
                          q={"same": {"H-REPEAT": "4096"}}, src="E031: mode 26 repeats"))
    out["p2"] = p2
    pw = [row("pw-ctl-m00", "control", "colour", 0, W080, {"H-E268": k268(0)},
              src="E268's kept pbe-reg-0400-modes-0__0")]
    for m in PAST:
        pw.append(row(f"pw-m{m:02d}-ref", "replicate", "colour", m, W080, {"H-E031": k031(m)},
                      src="E031's kept image of the mode"))
        pw.append(row(f"pw-m{m:02d}-b25", "heldout", "colour", m, B25,
                      q={"xor": {"H-INV25": f"0x{INV25[m]:08x}", "H-SUBSET": "0x00000000"}},
                      src="E031: whole 32-bit colours (gen/q044.py INV25)"))
    out["pw"] = pw
    return out
