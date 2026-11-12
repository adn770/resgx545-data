"""rlib.py: what the r5-render4x generator and scorer read from kept files (standard library only).  Copied from R4-G's (closing4/
r4-render4x/gen/rlib.py) with three additions: the dump name of a row from its verb (dump_stem: round 4's scorer looked for
NAME.tri.* where a probe writes NAME.PROG.*), the region-header rule of a four-array 4x dump (headers) and the published R4-G
directories.  The tool's lines are searched in the WHOLE output (R1-events lost "scene overflowed" in a 4000-character tail)."""
import gzip
import hashlib
import os
import re
import shlex
import struct
import subprocess

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
MAIN = os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545")
K2 = DATA + "/render/closing-r3k-pixel/out/20261110-193547/k-f4"
RGN4 = DATA + "/render/closing-r3-rgn4/out/rgn4"
REG = DATA + "/render/closing-r3k-regress/out/20261110-222647/rg-pb"
CUBE = DATA + "/texture/p1141/out-hw/p1141tex-dumps/tex-h-cube"
LINE = DATA + "/ta/line-point/dumps/ta-line-point"
POINT = DATA + "/ta/points/dumps/ta-points"
R4G = DATA + "/render/closing-r4-render4x"
R4G_A1 = R4G + "/out/20261111-211315"     # s0, c, p
R4G_A2 = R4G + "/out/20261111-211649"     # o, t, h (s0 in the first attempt: round 4's NODATA slip)


def read_bytes(p):
    if not os.path.exists(p):
        return None
    if p.endswith(".gz"):
        with gzip.open(p, "rb") as f:
            b = f.read()
    else:
        with open(p, "rb") as f:
            b = f.read()
    return b if b else None


def read_text(p):
    b = read_bytes(p)
    return None if b is None else b.decode("utf-8", "replace")


def read_cases(outdir):
    p = os.path.join(outdir, "cases.tsv")
    if not os.path.exists(p):
        return None
    lines = open(p).read().splitlines()
    if not lines:
        return None
    head = lines[0].split("\t")
    rows = {}
    for ln in lines[1:]:
        f = ln.split("\t")
        if len(f) == len(head):
            rows[f[0]] = dict(zip(head, f))
    return rows


def load_predictions(name, kp=KP):
    out = {}
    for ln in open(os.path.join(kp, "predictions", name)).read().splitlines()[1:]:
        if not ln.strip():
            continue
        case, q, val, model, sset, _src = ln.split("\t")
        out.setdefault((case, q), []).append((val, model, sset))
    return out


def pred(P, case, q, model=None):
    for val, m, _ in P.get((case, q), []):
        if model is None or m == model:
            return val
    raise KeyError((case, q, model))


def pred_or(P, case, q, default=None):
    v = P.get((case, q))
    return default if not v else v[0][0]


def verify_freeze():
    r = subprocess.run([os.path.join(KP, "run", "freeze_k.sh"), "verify"], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def dwords(b):
    n = len(b) // 4
    return list(struct.unpack("<%dI" % n, b[: 4 * n]))


def words(b, a, z):
    if b is None or len(b) < 4 * z:
        return None
    return ",".join("%08x" % x for x in dwords(b[4 * a: 4 * z]))


def target_hash(text):
    m = re.search(r"^target: \d+x\d+ hash (0x[0-9a-f]+)", text or "", re.M)
    return m.group(1) if m else None


def diff_text(text):
    m = re.search(r"^diff: (.*)$", text or "", re.M)
    return m.group(1) if m else None


def diff_count(text):
    m = re.search(r"^diff: (\d+) of (\d+) pixels", text or "", re.M)
    return None if not m else (int(m.group(1)), int(m.group(2)))


def tri_text(text, n=1):
    m = None
    for m2 in re.finditer(r"^tri \d+x\d+ #%d: (.*triangle, .*)$" % n, text or "", re.M):
        m = m2
    return m.group(1) if m else None


def tri_counts_text(text, n=1):
    """'N triangle, M background, K other' of render n's result line (the overflow mark and the wrong-pixel counts left out)."""
    t = tri_text(text, n)
    m = t and re.match(r"(?:overflowed, )?(\d+ triangle, \d+ background, \d+ other);", t)
    return m.group(1) if m else None


def tri_overflowed_line(text, n=1):
    t = tri_text(text, n)
    return bool(t and t.startswith("overflowed, "))


def renders(text):
    m = None
    for m2 in re.finditer(r"^tri: ((?:\d+ of )?\d+ renders ok(?:, \d+ overflowed)?)$", text or "", re.M):
        m = m2
    return m.group(1) if m else None


def echo(text):
    m = re.search(r"^tri: render context for targets up to (\d+x\d+)", text or "", re.M)
    return m.group(1) if m else None


def overflow_count(text):
    m = re.search(r"(\d+) overflowed$", renders(text) or "")
    return int(m.group(1)) if m else 0


def overflowed(*texts):
    return any(re.search(r"scene overflowed|overflowed the parameter buffer|overflowed, ", t or "") for t in texts)


def tool_failed(text):
    return re.search(r"rejected|FAILED after|cancelled|Segmentation|failed:|sgxfive-test: ", text or "") is not None


def reg(text, off):
    """A register of the tool's own `--regs` print ('reg 0x0724 0x000b000b') or of a debugfs regs snapshot: the value, or None."""
    m = re.search(r"^reg 0x%04x (0x[0-9a-f]+)$" % off, text or "", re.M)
    return m.group(1) if m else None


def bif_faults(text):
    """The kernel's job fault lines 'BIF fault 0xSTAT at 0xWORD': [(stat, word)] in order."""
    return [(int(a, 16), int(b, 16)) for a, b in re.findall(r"BIF fault 0x([0-9a-f]+) at 0x([0-9a-f]+)", text or "")]


def decode_fault(word):
    """BIF_FAULT word: (page, SB, CID) (hw_spec 5.5: the page number above bit 12, the sideband 7:4, the context list 3:0)."""
    return (word >> 12, (word >> 4) & 0xf, word & 0xf)


# ---- the dump a row writes (the name census) -------------------------------------------------------------------------------------
def dump_stem(args):
    """The stem the tool gives a row's --dump-render files: `tri` writes DIR/tri.{param,tadata}.bin; `probe ... PROG.bin` writes
    DIR/PROG.{param,tadata}.bin (the program's label: its file name without .bin, sgxfive-test.c dump_render(f->name)).  The runner keeps
    DIR/X as NAME.X.gz.  None if the row asks for no dump."""
    t = shlex.split(args.replace('"$W/dump"', "DUMP").replace('"$S/', '"S/'))
    if "--dump-render" not in t:
        return None
    if t[0] == "tri":
        return "tri"
    if t[0] == "probe":
        return os.path.basename(t[-1])[:-4] if t[-1].endswith(".bin") else None
    return None


def dump_names(name, args):
    s = dump_stem(args)
    return None if s is None else (name + "." + s + ".param.bin.gz", name + "." + s + ".tadata.bin.gz")


# ---- the region headers of a four-array 4x dump (closing5/render4x/rgn_check.py, fit 12 of 12 kept dumps) --------------------------
def _lay(w, h):
    tx, ty = (w + 31) // 32, (h + 15) // 16
    n = 4 if w * h >= 640 * 480 else 2
    r4 = lambda a: (a + 3) // 4 * 4  # noqa: E731
    mx, my = r4((tx + n - 1) // n), r4((ty + n - 1) // n)
    span = max(n * mx, n * my)
    side = 1
    while side < span:
        side <<= 1
    return tx, ty, n, mx, my, (4 * side * side + 4095) // 4096 * 4096 + 0x3000


def headers(tadata, w, h, mw=None, mh=None):
    """The doubled-grid rule on a TA-data dump: the TA writes the single-sampled layout's macrotiles with both spans doubled (2mx x 2my
    tiles of 16 x 8 pixels), column-major, each in 4 x 4 blocks; word 0 = flags | x << 16 | mt << 12 | y, bit 25 = no stream (outside
    the target), word 1 = the stream's offset (non-zero inside), word 2 = 0.  The grid is the TARGET's (the job's tiling words), the
    base the CONTEXT's `td.rgn` (its maximum's layout) [infer for a maximum larger than the target: never kept].
    Returns {'n': headers, 'off': [byte offsets of the headers off the rule], 'base': td.rgn} or None if the dump is too short."""
    mw, mh = mw or w, mh or h
    tx, ty, n, mx, my, _ = _lay(w, h)
    base = _lay(mw, mh)[5]
    count = n * n * (2 * my // 4) * (2 * mx // 4) * 16
    if tadata is None or len(tadata) < base + 12 * count:
        return None
    off, i = [], 0
    for col in range(n):
        for row in range(n):
            mt = col * n + row
            for by in range(2 * my // 4):
                for bx in range(2 * mx // 4):
                    for yy in range(4):
                        for xx in range(4):
                            x, y = col * 2 * mx + bx * 4 + xx, row * 2 * my + by * 4 + yy
                            o = base + 12 * i
                            w0, w1, w2 = struct.unpack_from("<3I", tadata, o)
                            i += 1
                            inside = x < 2 * tx and y < 2 * ty
                            ok = (((w0 >> 16) & 0xff) == x and (w0 & 0xfff) == y and ((w0 >> 12) & 0xf) == mt
                                  and bool(w0 & (1 << 25)) == (not inside) and bool(w1) == inside and w2 == 0)
                            if not ok:
                                off.append(o)
    return {"n": count, "off": off, "base": base}
