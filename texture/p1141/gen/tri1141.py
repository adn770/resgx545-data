# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""The render jobs of p1141/tex (multisampling, Q140, guard band, per-tile depth): options of the
`sgxfive-test tri` command line, the geometry, and the frozen predictions. numpy-free except where noted."""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import sys
from fractions import Fraction

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "recompute"))
import msaa_model as M  # noqa: E402
import q140_rescore as Q  # noqa: E402

POS = "0xeaa26e26"
DEPTH_CTL = 0x0017100C


def sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def case(script, group, name, st, risk, opts, **meta):
    return dict(script=script, group=group, name=name, set=st, risk=risk, kind="tri", opts=opts, meta=meta,
                preds={})


def msaa_base(w, h, mode, te):
    return ["--keep-going", "--wait-ms", "20000", "--width", str(w), "--height", str(h), "--max-width", str(w),
            "--max-height", str(h), "--pixels", "--poke", f"cmd:1={te:#x}", "--poke", f"cmd:10={POS}",
            "--poke", f"cmd:13=0x8000000{mode}", "--poke", f"cmd:16={POS}"]


# ----------------------------------------------------------------------------------- msaa-a-vis
def vis():
    """A triangle of 12 x 6 pixels confined to one region of the split grid, CR_TE_AA 0xe0000000 / 0xa0000000
    / 0x60000000 against the unsplit 0x20000000, ISP word 1 bit 3 (E070) counting visible pixels."""
    out = []
    groups = [(2, 0xE0000000, [(0, 0), (16, 0), (0, 8), (16, 8)]), (2, 0xA0000000, [(0, 0), (16, 0)]),
              (2, 0x60000000, [(0, 0), (0, 8)]), (1, 0xA0000000, [(0, 0), (16, 0)])]
    seen = set()
    for mode, te, boxes in groups:
        for bx, by in boxes:
            for tag, t in ((f"te{te >> 28:x}", te), ("te2", 0x20000000)):
                nm = f"v-m{mode}-{tag}-x{bx}y{by}"
                if nm in seen:
                    continue
                seen.add(nm)
                tri = ((bx + 2, by + 1), (bx + 14, by + 1), (bx + 2, by + 7))
                v256 = ",".join(str(c * 256) for p in tri for c in p)
                opts = msaa_base(64, 64, mode, t) + ["--tri-v", v256, "--tri-z", "0.5,0.5,0.5", "--poke", "blk:2^=0x8",
                                                    "--regs", "0x0494-0x04b4"]
                prim = [tuple((c * 16) for c in p) for p in tri]
                pred = sorted(M.predict([tuple(prim)], 64, 64, mode, t))
                c = case("msaa-a-vis", "vis", nm, "heldout" if t != 0x20000000 else "control", "safe", opts,
                         W=64, H=64, mode=mode, te=t, tri=tri, box=(bx, by))
                c["preds"] = {"image region model": sha(pred)}
                if t != 0x20000000:
                    # which regions the walk visits: the region of the stored tile is (2tx+b31, 2ty+b30)
                    b31, b30 = t >> 31 & 1, t >> 30 & 1
                    last = (bx, by) == (16 * b31, 8 * b30)
                    c["meta"]["last_region"] = bool(last)
                    if not last:
                        c["preds"]["W walks every region (count > 0)"] = sha({"count_gt0": True})
                        c["preds"]["S skips the even regions (count = 0)"] = sha({"count_gt0": False})
                    else:
                        c["preds"]["last region (count > 0)"] = sha({"count_gt0": True})
                out.append(c)
    # a repeat of the deciding case (the even region at the TE bits of the closed driver, mode 2)
    c = dict(out[0]); c["name"] = "v-m2-tee-x0y0-r2"; c["set"] = "repeat"
    out.append(c)
    return out


# ---------------------------------------------------------------------------------- msaa-b-te29
def te29():
    out = []
    for w, h, mode in ((64, 64, 0), (64, 64, 2), (128, 128, 2)):
        for te in (0x40000000, 0x80000000, 0xC0000000):
            opts = ["--tri-full", "--keep-going", "--wait-ms", "20000", "--width", str(w), "--height", str(h),
                    "--max-width", str(w), "--max-height", str(h), "--pixels", "--poke", f"cmd:1={te:#x}",
                    "--poke", f"cmd:10={POS}", "--poke", f"cmd:13=0x8000000{mode}", "--poke", f"cmd:16={POS}",
                    "--regs", "0x0200-0x0218", "--dump-render", "@D@"]
            c = case("msaa-b-te29", "te29", f"t29-m{mode}-{te >> 28:x}0-{w}x{h}", "heldout", "safe", opts, W=w, H=h,
                     mode=mode, te=te)
            c["preds"] = {"H gate: dumps equal the te 0x00 job's": sha({"equal": "te00"}),
                          "H bits: dumps equal the job with bit 29 set": sha({"equal": "bit29"})}
            out.append(c)
    for te in (0x20000000, 0xE0000000):
        opts = ["--tri-full", "--keep-going", "--wait-ms", "20000", "--width", "64", "--height", "64", "--max-width",
                "64", "--max-height", "64", "--pixels", "--poke", f"cmd:1={te:#x}", "--poke", f"cmd:10={POS}",
                "--poke", "cmd:13=0x80000002", "--poke", f"cmd:16={POS}", "--regs", "0x0200-0x0218",
                "--dump-render", "@D@"]
        c = case("msaa-b-te29", "te29", f"t29-m2-{te >> 28:x}0-64x64-ctl", "control", "safe", opts, W=64, H=64, mode=2,
                 te=te)
        c["preds"] = {"equals the landed te-m2-%s-64x64 dumps" % ("20" if te == 0x20000000 else "e0"):
                      sha({"equal": "landed"})}
        out.append(c)
    return out


# ------------------------------------------------------------------------------------ msaa-c-q140
def q140():
    out = []
    sizes = [(256, 160), (320, 128), (288, 144), (256, 288), (384, 384)]
    for w, h in sizes:
        opts = ["--tri-full", "--keep-going", "--wait-ms", "20000", "--width", str(w), "--height", str(h), "--max-width",
                str(w), "--max-height", str(h), "--poke", "cmd:1=0xe0000000", "--poke", f"cmd:10={POS}",
                "--poke", "cmd:13=0x80000002", "--poke", f"cmd:16={POS}"]
        c = case("msaa-c-q140", "q140", f"q140-{w}x{h}", "heldout", "risky", opts, W=w, H=h)
        L = Q.layout(w, h)
        c["meta"].update(rgn_size=L["rgn_size"], size=L["size"])
        for f in (3, 4, 5, 6):
            pg = Q.predict(w, h, f)
            c["preds"][f"factor {f}: " + ("completes" if pg is None else f"BIF fault at page 0x2{pg:04x}")] = sha(
                {"f": f, "fault_page": pg})
        out.append(c)
    return out


# ------------------------------------------------------------------------------------ isp-a-guard
def pitch_g(w):
    return max(1, (w + 31) // 32 - 1)


def depth_args(w, h):
    g = pitch_g(w)
    tw, th = (w + 31) // 32, (h + 15) // 16
    tiles = (th - 1) * (g + 1) + tw
    pages = max((w * h * 4 + 4095) // 4096, tiles // 2) + 16
    ctl = (DEPTH_CTL & ~(0x1FF << 3)) | g << 3
    return ["--depth", "--depth-ctl", hex(ctl), "--depth-fill", "0xdeadbeef", "--depth-dump", "@D@", "--depth-pages",
            str(pages), "--poke", "blk:1=0x00400200"]


def guard():
    out = []
    for w, h, st in ((34, 18, "control"), (18, 18, "heldout"), (50, 26, "heldout"), (66, 34, "heldout"),
                     (98, 50, "heldout"), (34, 50, "heldout")):
        for ax, z in (("x", "0.25,0.75,0.25"), ("y", "0.25,0.25,0.75")):
            opts = ["--keep-overflow", "--wait-ms", "20000", "--width", str(w), "--height", str(h), "--tri-full",
                    "--tri-z", z] + depth_args(w, h)
            c = case("isp-a-guard", "guard", f"gb-{w}x{h}-ramp{ax}", st, "safe", opts, W=w, H=h, ramp=ax, G=pitch_g(w))
            tw, th = (w + 31) // 32, (h + 15) // 16
            area = [(x, y) for y in range(th * 16) for x in range(tw * 32)]
            hyps = {"clip at 1.25 W, 1.25 H": lambda x, y: x + .5 < 1.25 * w and y + .5 < 1.25 * h,
                    "whole tile area stored": lambda x, y: True,
                    "clip at the target": lambda x, y: x < w and y < h}
            for k, f in hyps.items():
                c["preds"][k] = sha([p for p in area if f(*p)])
            out.append(c)
    return out


# ---------------------------------------------------------------------------------------- isp-b-depth
def rn32(x: Fraction, mode="rn") -> float:
    """float32 nearest-even (or toward zero) of an exact positive rational, returned as a python float."""
    if x == 0:
        return 0.0
    s = -1 if x < 0 else 1
    x = abs(x)
    e = math.floor(math.log2(float(x)))
    while Fraction(2) ** e > x:
        e -= 1
    while Fraction(2) ** (e + 1) <= x:
        e += 1
    q = x / Fraction(2) ** (e - 23)
    n = q.numerator // q.denominator
    r = q - n
    if mode == "rn" and (r > Fraction(1, 2) or (r == Fraction(1, 2) and n % 2)):
        n += 1
    return s * float(n * Fraction(2) ** (e - 23))


def f32(x: float) -> float:
    import struct
    return struct.unpack("<f", struct.pack("<f", x))[0]


def plane_of(V, Z):
    (x0, y0), (x1, y1), (x2, y2) = V
    z0, z1, z2 = (Fraction(z) for z in Z)
    det = Fraction((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0))
    A = ((z1 - z0) * (y2 - y0) - (z2 - z0) * (y1 - y0)) / det
    B = ((x1 - x0) * (z2 - z0) - (x2 - x0) * (z1 - z0)) / det
    return z0, A, B, x0, y0


def tile_T(V, Z, w=256, h=128):
    """Per hypothesis the tile-corner values T(i, j), tile order (row major), as float32 bit-exact floats."""
    z0, A, B, x0, y0 = plane_of(V, Z)
    nx, ny = w // 32, h // 16
    ex = {(i, j): z0 + A * (32 * i - x0) + B * (16 * j - y0) for j in range(ny) for i in range(nx)}
    H = {"T = RN(plane at the corner)": [rn32(ex[k]) for k in ex],
         "T = trunc(plane at the corner)": [rn32(ex[k], "tr") for k in ex]}
    Sx, Sy = f32(rn32(32 * A)), f32(rn32(16 * B))
    col0 = [rn32(ex[(0, 0)])]
    for j in range(1, ny):
        col0.append(f32(col0[-1] + Sy))
    walk = []
    for j in range(ny):
        t = col0[j]
        for i in range(nx):
            walk.append(t)
            t = f32(t + Sx)
    H["walk T(i+1) = fl(T(i) + RN(32 A))"] = walk
    return H


def depth():
    out = []
    w, h = 256, 128
    for k, z0 in ((0, 0.5), (1, 0.25), (2, 0.125)):
        for cls in ("a", "b", "c"):
            for ax in ("x", "y"):
                if cls == "a":
                    D, dz = 512, 2.0 ** -4
                elif cls == "b":
                    D, dz = 400, 0.0625
                else:
                    D = 512
                    dz = 5 * 2.0 ** -(21 + k) if ax == "x" else 5 * 2.0 ** -(20 + k)
                V = ((0, 0), (D, 0), (0, D))
                Z = (z0, z0 + dz, z0) if ax == "x" else (z0, z0, z0 + dz)
                out.append(mk_depth(f"dp-{cls}{ax}-b{k}", cls, V, Z, w, h, "heldout" if cls != "a" else "control"))
    base = ((0, 0), (400, 0), (0, 400))
    Zb = (0.5, 0.5625, 0.5)
    for nm, order in (("p1", (1, 2, 0)), ("p2", (2, 0, 1)), ("r", (0, 2, 1))):
        V = tuple(base[i] for i in order)
        Z = tuple(Zb[i] for i in order)
        out.append(mk_depth(f"dp-bx-b0-{nm}", "b", V, Z, w, h, "heldout", planar=(base, Zb)))
    return out


def mk_depth(name, cls, V, Z, w, h, st, planar=None):
    v256 = ",".join(str(c * 256) for p in V for c in p)
    zs = ",".join(repr(float(z)) for z in Z)
    opts = ["--keep-overflow", "--wait-ms", "20000", "--width", str(w), "--height", str(h), "--tri-v", v256, "--tri-z", zs]
    opts += depth_args(w, h) + ["--pixels"]
    c = case("isp-b-depth", "depth", name, st, "safe", opts, W=w, H=h, V=V, Z=list(Z), cls=cls, G=pitch_g(w))
    bV, bZ = planar if planar else (V, Z)
    for k, vals in tile_T(bV, bZ, w, h).items():
        c["preds"][k] = sha([f"{v:.17g}" for v in vals])
    c["meta"]["tiles"] = (w // 32) * (h // 16)
    return c


def all_tri():
    return vis() + te29() + guard() + depth() + q140()
