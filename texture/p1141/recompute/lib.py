"""Shared helpers of the p1141/tex recomputations: the stored 11.32 dumps, p1132's texmodel
(imported unchanged, hypotheses patched at run time) and a tile law written from E561's words.
Scratch only: numpy is allowed here, nothing landing imports it."""
import collections, gzip, hashlib, json, math, pathlib, re, struct, sys
sys.dont_write_bytecode = True
P1132 = pathlib.Path.home() / "src/sgxhumation/debug/wt-phase10/debug/phase11/p1132"
DATA = pathlib.Path.home() / "src/resgx545-data"
D32 = DATA / "texture/p1132"
sys.path.insert(0, str(P1132 / "recompute"))
import texmodel as tm  # noqa: E402

SPECS = json.loads((P1132 / "gen/specs.json").read_text())
ROW = re.compile(r"row (\d+):(.*)$")


def declared():
    out = {}
    for ln in (P1132 / "declared.tsv").read_text().splitlines()[1:]:
        s, c, st, rk, q = ln.split("\t")
        out[c] = (s, st, rk)
    return out


def load_pix(script, name, root=D32):
    p = root / script / f"{name}.txt.gz"
    if not p.exists():
        return None
    txt = gzip.open(p, "rt", errors="replace").read()
    if re.search(r"failed|faulted|hung", txt):
        return None
    rows = {}
    for ln in txt.splitlines():
        m = ROW.search(ln)
        if m:
            rows[int(m.group(1))] = [int(v[2:] if v.startswith("0x") else v, 16) for v in m.group(2).split()]
    pix = [v for y in sorted(rows) for v in rows[y]]
    return pix if len(pix) == 2048 else None


def tile_index(x, y, w, h):
    """E561: tiles of min(w,16) x min(h,16) texels, inside a tile the interleave with y in bit 0,
    tiles in raster order, x first. For a tile that is not square the longer side's excess bits
    sit above the interleave (the plain 8x128 / 16x64 rule, which E561 fits)."""
    tw, th = min(w, 16), min(h, 16)
    bx, by = tw.bit_length() - 1, th.bit_length() - 1
    cm = min(bx, by)
    xx, yy = x % tw, y % th
    i = 0
    for b in range(cm):
        i |= (yy >> b & 1) << (2 * b) | (xx >> b & 1) << (2 * b + 1)
    i |= (xx if bx > by else yy) >> cm << (2 * cm)
    return (x // tw + (y // th) * (w // tw)) * tw * th + i


def use_tile_law(on=True):
    tm.morton = tile_index if on else _plain


_plain = tm.morton


def digest(pix):
    return hashlib.sha256(",".join(f"{v:08x}" for v in pix).encode()).hexdigest()
