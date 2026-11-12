#!/usr/bin/env python3
"""g_q291.py: r7-rp stages q291g (the gate row) and q291 (Q291, the attribute band, 26 rows), plan
closing7/a/exp-pixel-r7.md section 3.3.  Writes tables/q291g.txt, tables/q291.txt,
predictions/q291g.tsv, predictions/q291.tsv, templates/pix_posstore.s (+ .lst), the five programs
in bins/ (hash-pinned in gen/data/bins-q291.txt) and gen/data/sources-q291.lst.  Deterministic.
  PY gen/g_q291.py

Programs (bins/, staged as $S/...):
  pix_posstore.bin  the landed probes/pds/templates/pix_posstore.s (main 1c64f3a, E898), assembled
                    with the landed tools/usse-asm/usse-asm: sha256 8a136e52... (E898, the plan's)
  q291_pos.bin      E437's primary pixel PDS program (pds_iter_nofetch.s, DOUTI0 0x20400000, B 0,
                    U1 0x01000004): a byte copy of E437's kept bin (dataset dpm-partial-reload-pos)
  q291_vtx.bin      E606's vertex pair (the same template, DOUTI0 0x20400800): E606 kept no bin
                    (isp-arith-1138 publishes the templates): assembled with the landed pds-asm the
                    way tools/usse-asm/probe.py renders a case; the position pair assembled the same
                    way gives E437's kept bin byte for byte (checked here)
  vtx_attr_zx.bin   E606's templates/vtx_attr_zx.s (o4 = clip z, o5 = clip x), landed usse-asm
  pix_pa0.bin       E437's kept pix_pa0.bin (= the landed pix_pa0.s assembled, checked here)
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import hashlib  # noqa: E402
import os  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
import score_q291 as M  # noqa: E402
import scorekit  # noqa: E402

MAIN = "/Users/jtorra/src/resgx545"
DATA = "/Users/jtorra/src/resgx545-data"
USSE_ASM = MAIN + "/tools/usse-asm/usse-asm"
PDS_ASM = MAIN + "/tools/usse-asm/pds-asm"
T_POSSTORE = MAIN + "/probes/pds/templates/pix_posstore.s"
T_NOFETCH = MAIN + "/probes/pds/templates/pds_iter_nofetch.s"
T_PA0 = MAIN + "/probes/pds/templates/pix_pa0.s"
E437_BINS = DATA + "/dpm/partial-reload-pos/dpm-partial-reload-pos-pa0/bins"
E437_PDS = E437_BINS + "/dpm-partial-reload-pos-pa0__0.bin"
E437_PA0 = E437_BINS + "/pix_pa0.bin"
E606_ZX = DATA + "/isp/arith-1138/templates/vtx_attr_zx.s"
E606_NOFETCH = DATA + "/isp/arith-1138/templates/pds_iter_nofetch.s"
PINS = os.path.join(KP, "gen", "data", "bins-q291.txt")
SOURCES = [USSE_ASM, PDS_ASM, T_POSSTORE, T_NOFETCH, T_PA0, E437_PDS, E437_PA0, E606_ZX, E606_NOFETCH]

S = '"$S/%s"'
CUT_X = "8192,0,32768,0,8192,12288"        # (32,0) (128,0) (32,48) in 1/256 pixel: tile (1,0)
CUT_Y = "0,4096,24576,4096,0,16384"        # (0,16) (96,16) (0,64): tile (0,1)
NEED = ["pix_posstore.bin", "q291_pos.bin", "q291_vtx.bin", "vtx_attr_zx.bin", "pix_pa0.bin"]


# ---- rows ----------------------------------------------------------------------------------------
def probe_args(w, h, geom, prog="P", pixel="pix_posstore"):
    g = "--tri-full" if geom == "full" else "--tri-v " + geom
    a = f"probe --tri pixpds:12 --temps 32 --pixels --width {w} --height {h} {g}"
    if prog == "V":
        a += " --vtx-coords 2 --slot vtxuse=" + S % "vtx_attr_zx.bin"
    a += " --slot pixel=" + S % (pixel + ".bin")
    return a + " " + S % ("q291_pos.bin" if prog == "P" else "q291_vtx.bin")


def depth_args(w, h):
    # E831 / E885's row (3.2's shape), x ramp, the tile-area pages at ZLSCTL G (pitch 2 tiles) + 16
    return (f"tri --keep-overflow --wait-ms 20000 --width {w} --height {h} --tri-full --tri-z "
            f"0.25,0.75,0.25 --depth --depth-ctl 0x{M.depth_ctl(w):x} --depth-fill 0xdeadbeef "
            f'--depth-dump "$W/depth" --depth-pages {M.depth_pages(w, h)} --poke blk:1=0x00400200')


def rows_q291g():
    return [("q291-ps-gate-32x16", "gate", "strict", probe_args(32, 16, "full"))]


def rows_q291():
    r = [("q291-pa0-ctl-20x12", "control", "-", probe_args(20, 12, "full", pixel="pix_pa0")),
         ("q291-ps-ctl-cutx-64x16", "control", "-", probe_args(64, 16, CUT_X)),
         ("q291-ps-ctl-cuty-32x32", "control", "-", probe_args(32, 32, CUT_Y)),
         ("q291-pv-ctl-32x16", "control", "-", probe_args(32, 16, "full", "V")),
         ("q291-ps-fit-20x12-r1", "fit", "-", probe_args(20, 12, "full")),
         ("q291-ps-fit-20x12-r2", "fit", "-", probe_args(20, 12, "full"))]
    for w, h in ((18, 12), (24, 8), (12, 12), (20, 8), (26, 10), (10, 6)):
        r.append((f"q291-ps-{w}x{h}", "heldout", "-", probe_args(w, h, "full")))
    for w in (34, 36, 44, 50):
        r.append((f"q291-ps-cutx-{w}x16", "heldout", "-", probe_args(w, 16, CUT_X)))
    for h in (18, 24):
        r.append((f"q291-ps-cuty-32x{h}", "heldout", "-", probe_args(32, h, CUT_Y)))
    for w, h in ((20, 12), (18, 12), (24, 8)):
        r.append((f"q291-pv-{w}x{h}", "heldout", "-", probe_args(w, h, "full", "V")))
    for w, h in ((20, 12), (18, 12), (24, 8), (12, 12), (10, 6)):
        r.append((f"q291-pz-{w}x{h}", "twin", "expectdiff", depth_args(w, h)))
    assert tuple(n for n, *_ in r if n.startswith("q291-pz-")) == M.TWINS
    return r


HEAD = {
    "q291g": [
        "#stage q291g", "#limit 1",
        "# Q291 gate (plan closing7/a/exp-pixel-r7.md 3.3, stop rc 24): pix_posstore.bin (E898) as the",
        "# triangle's pixel program with E437's position pair (q291_pos.bin) at 32 x 16 --tri-full: the",
        "# target is one tile, so all 512 slots are known: dword 1 = f32(x + 0.5), dword 2 = f32(y + 0.5),",
        "# dword 3 = 0x7E570000 | (x & 1) | (y & 1) << 1 (E808's g23, g24, g25; E437).  score_q291.py gate",
        "# q291g = 0 only when the 512 slots are exactly these; otherwise the driver skips stage q291 and",
        "# the session goes on.  First job of the new program: a fault ends the stage (strict health, rc 4).",
    ],
    "q291": [
        "#stage q291", "#limit 1",
        "# Q291, the attribute band (plan 3.3), t6 (R6's d9b2969 build: --tri-v, pixpds:12, --slot and",
        "# --vtx-coords for probe --tri).  Valid set = the slots whose scratch dword 1 changed; every row",
        "# touches one tile (pix_posstore reads only g23-g25).  Frozen, exact set equality: H-BAND",
        "# (predicted: covered, in the tile area, x + 0.5 < 1.25 W and y + 0.5 < 1.25 H) against H-TARGET",
        "# (inside W x H) and H-TILE (the tile area); the 12 held-out P rows separate H-BAND from both.",
        "# Values: P (q291_pos.bin, E437) f32(x + 0.5), f32(y + 0.5) past the target too (H-LIN); V",
        "# (q291_vtx.bin, E606's vertex pair, vtx_attr_zx.bin) clip z 0 within 4, clip x within 23 units",
        "# of 2^-23 (E661).  Controls that can fail: pix_pa0's image at 20 x 12 (x + 0.5 words), the cut",
        "# triangles at 64 x 16 (tile (1,0)) and 32 x 32 (tile (0,1)) (512 slots each), V at 32 x 16.",
        "# Depth twins (tri --depth, E831's row shape, x ramp): rule A's stored set at sizes never run.",
        "# No fault expected (fault limit 1).",
    ],
}


# ---- predictions ---------------------------------------------------------------------------------
def predict(name, sset, args):
    r = M.parse_row(args)
    out = [(name, "size", "%dx%d" % (r["W"], r["H"]), "all", sset)]
    if r["cmd"] == "tri":
        for rule in M.RULES:
            st = M.band_set(rule, r["W"], r["H"])
            out += [(name, "stored_count", str(len(st)), rule, sset),
                    (name, "stored_set_sha", M.set_sha(st), rule, sset),
                    (name, "extent", "%d,%d" % M.extent(st), rule, sset)]
        out.append((name, "dead", "0", "all", sset))
        return out
    ms = M.model_sets(r)
    if r["kind"] == "image":
        v = M.vertices256(r)
        img = [M.f32(x + 0.5) if M.covered(v, x, y) else M.BG_COLOUR
               for y in range(r["H"]) for x in range(r["W"])]
        n = sum(1 for w in img if w != M.BG_COLOUR)
        out += [(name, "image_covered", str(n), "E437", sset),
                (name, "image_sha", hashlib.sha256(repr(img).encode()).hexdigest(), "E437", sset)]
        return out
    ox, oy = M.tile_of(r)
    out.append((name, "tile", "%d,%d" % (ox // M.TILE_W, oy // M.TILE_H), "all", sset))
    for m in M.MODELS:
        s = ms[m]
        assert len({M.slot(x, y) for x, y in s}) == len(s), (name, m, "shared slots")
        out += [(name, "valid_count", str(len(s)), m, sset),
                (name, "valid_sha", M.set_sha(s), m, sset)]
    band = ms["H-BAND"]
    sep = band != ms["H-TARGET"] and band != ms["H-TILE"]
    out.append((name, "separates", "yes" if sep else "no", "H-BAND-vs-rivals", sset))
    out.append((name, "intarget_count", str(len(ms["H-TARGET"])), "all", sset))
    out.append((name, "dword0_count", str(len(M.quads(band))), "E111", sset))
    if r["set"] == "P":
        out.append((name, "values", "dword1=f32(x+0.5) dword2=f32(y+0.5) at every valid slot",
                    "H-LIN", sset))
    else:
        out.append((name, "values", "dword1=clip z 0 within %d; dword2=(x+0.5)/(W/2)-1 within %d "
                    "(units of 2^-23)" % (M.TOL_Z, M.TOL_X), "E661", sset))
    out.append((name, "lanes", "dword3=0x7E570000|(x&1)|(y&1)<<1", "E808", sset))
    if sset == "gate":
        assert len(band) == 512 and band == ms["H-TARGET"] == ms["H-TILE"]
    if sset == "control":
        assert len(band) == 512 and band == ms["H-TILE"], name
    if sset == "heldout" and r["set"] == "P":
        assert sep, f"{name}: H-BAND does not separate from its rivals"
    return out


# ---- controls (HACKING session build rules) ------------------------------------------------------
def _rows(stage):
    return rows_q291g() if stage == "q291g" else rows_q291()


def controls(stage):
    out = []
    for name, sset, _, args in _rows(stage):
        if sset not in ("gate", "control"):
            continue
        r = M.parse_row(args)
        reads = ["image"] if r["kind"] == "image" else ["scratch", "valid_set", "values", "lanes"]
        out.append({"name": name, "reads": reads, "row": args})
    return out


def producible(row):
    """The reading keys a row's job can produce, from its argv."""
    r = M.parse_row(row)
    keys = set()
    if r["cmd"] == "probe":
        if "--pixels" in row:
            keys.add("image")
        if r["kind"] == "store":
            keys |= {"scratch", "valid_set", "values", "lanes", "dword0"}
    elif r["kind"] == "depth" and "--depth-dump" in row:
        keys |= {"depth_dump", "stored_set"}
    return keys


# ---- programs ------------------------------------------------------------------------------------
def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _asm(tool, text, out, listing=False):
    r = subprocess.run([tool] + (["-l"] if listing else []) + ["-o", out, "-"], input=text,
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{tool}: {r.stderr.strip()}")
    return r.stdout


def _nofetch(a, b, u):
    t = open(T_NOFETCH).read()
    return t.replace("{A}", "0x%08X" % a).replace("{B}", "0x%08X" % b).replace("{U}", "0x%08X" % u)


def programs(kp):
    bins, tdir = os.path.join(kp, "bins"), os.path.join(kp, "templates")
    os.makedirs(bins, exist_ok=True)
    os.makedirs(tdir, exist_ok=True)
    assert open(T_NOFETCH, "rb").read() == open(E606_NOFETCH, "rb").read(), \
        "E606's pds_iter_nofetch.s is not the landed one"
    shutil.copyfile(T_POSSTORE, os.path.join(tdir, "pix_posstore.s"))
    lst = _asm(USSE_ASM, open(os.path.join(tdir, "pix_posstore.s")).read(),
               os.path.join(bins, "pix_posstore.bin"), listing=True)
    with open(os.path.join(tdir, "pix_posstore.lst"), "w") as f:
        f.write(lst)
    shutil.copyfile(E437_PDS, os.path.join(bins, "q291_pos.bin"))
    shutil.copyfile(E437_PA0, os.path.join(bins, "pix_pa0.bin"))
    _asm(PDS_ASM, _nofetch(0x20400800, 0, 0x01000004), os.path.join(bins, "q291_vtx.bin"))
    _asm(USSE_ASM, open(E606_ZX).read(), os.path.join(bins, "vtx_attr_zx.bin"))
    # cross-checks: the assembly route reproduces E437's kept bins (pos pair and pix_pa0)
    chk = os.path.join(kp, "debug", "q291-chk.bin")
    os.makedirs(os.path.dirname(chk), exist_ok=True)
    _asm(PDS_ASM, _nofetch(0x20400000, 0, 0x01000004), chk)
    assert open(chk, "rb").read() == open(E437_PDS, "rb").read(), "pos pair: not E437's bin"
    _asm(USSE_ASM, open(T_PA0).read(), chk)
    assert open(chk, "rb").read() == open(E437_PA0, "rb").read(), "pix_pa0: not E437's bin"
    os.remove(chk)
    pins = dict(reversed(ln.split()) for ln in open(PINS) if ln.strip() and not ln.startswith("#"))
    for n in NEED:
        got = _sha(open(os.path.join(bins, n), "rb").read())
        if pins.get(n) != got:
            raise RuntimeError(f"bins/{n}: sha256 {got} is not the pinned {pins.get(n)}")


# ---- write ---------------------------------------------------------------------------------------
def write(kp=KP):
    programs(kp)
    for stage in ("q291g", "q291"):
        rows = _rows(stage)
        cs = {c["name"]: (tuple(c["reads"]), c["row"]) for c in controls(stage)}
        scorekit.refuse_unreadable(cs, producible)
        lines = HEAD[stage] + ["#need $S/" + n for n in NEED
                               if any(n in a for *_, a in rows)]
        lines += ["%s|%s|safe|%s|t6|%s" % (n, s, k, a) for n, s, k, a in rows]
        with open(os.path.join(kp, "tables", stage + ".txt"), "w") as f:
            f.write("\n".join(lines) + "\n")
        with open(os.path.join(kp, "predictions", stage + ".tsv"), "w") as f:
            f.write("case\tquantity\tvalue\tmodel\tset\n")
            for n, s, _, a in rows:
                for p in predict(n, s, a):
                    f.write("\t".join(p) + "\n")
    with open(os.path.join(kp, "gen", "data", "sources-q291.lst"), "w") as f:
        f.write("\n".join(SOURCES) + "\n")


if __name__ == "__main__":
    write()
    for st in ("q291g", "q291"):
        n = sum(1 for ln in open(os.path.join(KP, "tables", st + ".txt")) if not ln.startswith("#"))
        print(f"tables/{st}.txt: {n} rows")
