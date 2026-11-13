"""lib_dump.py: the readers of the r7-rp `dump` area (stages q293 and q139), standard library and the session's own
modules only.  Shared by gen/g_dump.py (which freezes from kept precedent files), score/score_dump.py (which reads the
run) and tests/world_dump.py (the fake tool).  Nothing here decides a verdict.

The region headers are read with byte copies of resgx545 1c64f3a tools/usse-asm/pbdump.py (score/pbdump_dump.py) and
region_tiles.py (score/region_tiles_dump.py): a header is three dwords, word 0 = flags << 24 | col << 16 | row
(REGION_HDR.POS; col 2 per 32-pixel column, row 2 per 16-pixel row of a 1x target, bits 15:12 the macrotile), word 1 the
stream block (REGION_HDR.STREAM, slot-relative; 0 for an empty region).  pbdump.regions() reads the first written TA data
page only (341 headers): a 640 x 480 target has 600, so headers() here walks the slots ACROSS pages from the first written
page (the 2048 x 2048 dump c3-2048-cal of render/closing-r2-geo holds 8192 contiguous headers across pages)."""
import gzip
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import pbdump_dump as pbdump  # noqa: E402

sys.modules.setdefault("pbdump", pbdump)          # region_tiles.py imports pbdump by that name
import region_tiles_dump as region_tiles  # noqa: E402

GREEN = 0xff00ff00                  # --tri-full's triangle colour (the datasets' and E877's reading)
OBJ_HEAD = (0x04000004, 0x00030001, 0x04000000)   # how the one-triangle scene's object opens (E897)
FORMAT = 0x00040101                 # PB_OBJ.FORMAT of that object
TW, TH = 32, 16                     # a 1x tile (one region header)


# ---- files ---------------------------------------------------------------------------------------------------------------------
def read_bytes(p):
    """The bytes of p or p.gz (gunzipped); None when neither exists (an empty file is b"", a kept empty kernel-log slice)."""
    for q in (p, p + ".gz") if not p.endswith(".gz") else (p,):
        if os.path.exists(q):
            if q.endswith(".gz"):
                with gzip.open(q, "rb") as f:
                    b = f.read()
            else:
                with open(q, "rb") as f:
                    b = f.read()
            return b
    return None


def read_text(p):
    b = read_bytes(p)
    return None if b is None else b.decode("utf-8", "replace")


def read_cases(kept):
    """cases.tsv of a kept stage directory: {name: {column: value}} (header line first), None if absent."""
    p = os.path.join(kept, "cases.tsv")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        lines = f.read().splitlines()
    if not lines:
        return None
    head = lines[0].split("\t")
    out = {}
    for ln in lines[1:]:
        if not ln.strip() or ln.startswith("#"):
            continue
        f = ln.split("\t")
        if len(f) == len(head):
            out[f[0]] = dict(zip(head, f))
    return out


def load_predictions(path):
    """predictions/STAGE.tsv: {(case, quantity): [(value, model, set), ...]}."""
    out = {}
    with open(path) as f:
        lines = f.read().splitlines()
    for ln in lines[1:]:
        if not ln.strip():
            continue
        c = ln.split("\t")
        out.setdefault((c[0], c[1]), []).append((c[2], c[3], c[4]))
    return out


def pred(P, case, q, model=None):
    for val, m, _ in P.get((case, q), []):
        if model is None or m == model:
            return val
    raise KeyError((case, q, model))


# ---- the tool's text -----------------------------------------------------------------------------------------------------------
def tri_counts(text, n):
    """(triangle, background, other) of render n's result line, the last such line; None if none."""
    m = None
    for m2 in re.finditer(r"^tri \d+x\d+ #%d: (?:overflowed, )?(\d+) triangle, (\d+) background, (\d+) other" % n,
                          text or "", re.M):
        m = m2
    return None if m is None else tuple(int(x) for x in m.groups())


def counts_text(c):
    return None if c is None else "%d triangle, %d background, %d other" % c


def diff_count(text):
    m = re.search(r"^diff: (\d+) of (\d+) pixels", text or "", re.M)
    return None if not m else (int(m.group(1)), int(m.group(2)))


def target_hash(text):
    m = re.search(r"^target: \d+x\d+ hash (0x[0-9a-f]+)", text or "", re.M)
    return m.group(1) if m else None


def geometry_lines(text):
    """The renders the tool reports as geometry only: [n, ...]."""
    return [int(x) for x in re.findall(r"^tri \d+x\d+ #(\d+): geometry only", text or "", re.M)]


def kpoke_applied(text):
    """The kernel's 'kpoke SPEC applied' lines of a job's kernel-log slice: ['par:38=0x00040101', ...]."""
    return re.findall(r"kpoke ((?:par|ta):\d+=0x[0-9a-f]+) applied", text or "")


def tool_kpokes(text, render):
    """The tool's own 'tri: kpoke before render N: SPEC' lines for render N."""
    return re.findall(r"^tri: kpoke before render %d: (\S+)$" % render, text or "", re.M)


def norm_spec(spec):
    """'par:39=0' -> 'par:39=0x00000000' (the kernel prints 0x%08x)."""
    m = re.fullmatch(r"(par|ta):(\d+)=(0x[0-9a-fA-F]+|\d+)", spec)
    if not m:
        raise ValueError("not a kpoke spec: %r" % spec)
    return "%s:%s=0x%08x" % (m.group(1), m.group(2), int(m.group(3), 0))


# ---- the parameter buffer: objects (q293) --------------------------------------------------------------------------------------
def dwords(b, n=None):
    if b is None:
        return None
    k = len(b) // 4 if n is None else min(n, len(b) // 4)
    return list(struct.unpack("<%dI" % k, b[: 4 * k]))


def objects(words, limit=4096):
    """[(start, offset of the format word from the start or None, the dword before it or None)] for every object that opens
    as the one-triangle scene's does (closing7/a/q293/obj2_scan.py's reading, the first `limit` dwords)."""
    w = words[:limit]
    out = []
    for i in range(len(w) - 16):
        if tuple(w[i:i + 3]) == OBJ_HEAD:
            off = next((k for k in range(8, 16) if w[i + k] == FORMAT), None)
            out.append((i, off, w[i + off - 1] if off else None))
    return out


# ---- the image (q139: --pixels) ------------------------------------------------------------------------------------------------
def image_tiles(text, w, h):
    """The --pixels rows of a w x h job: (complete, wrong tile set {(tx, ty)}).  complete is False when a row is missing, cut or
    of the wrong length (the set is then of the rows read).  A tile is wrong when any of its pixels is not the triangle's
    0xff00ff00 (E877's reading, closing6/rank/q139_tiles.py)."""
    rows = {}
    complete = True
    for m in re.finditer(r"^row (\d+): (.*)$", text or "", re.M):
        vals = m.group(1), m.group(2).split()
        y = int(vals[0])
        px = []
        for x in vals[1]:
            if not re.fullmatch(r"0x[0-9a-f]{8}", x):
                complete = False
                break
            px.append(int(x, 16))
        if len(px) != w or y in rows:
            complete = False
        rows[y] = px
    if sorted(rows) != list(range(h)):
        complete = False
    bad = set()
    for y, px in rows.items():
        for x, p in enumerate(px):
            if p != GREEN:
                bad.add((x // TW, y // TH))
    return complete, bad


def tiles_text(tiles):
    """A tile set as frozen text: 'x.y,x.y,...' sorted by (y, x), or 'none'."""
    return ",".join("%d.%d" % t for t in sorted(tiles, key=lambda t: (t[1], t[0]))) or "none"


def tiles_parse(s):
    return set() if s == "none" else {tuple(int(v) for v in p.split(".")) for p in s.split(",")}


def target_tiles(w, h):
    return {(x, y) for x in range(-(-w // TW)) for y in range(-(-h // TH))}


# ---- the region headers (q139) -------------------------------------------------------------------------------------------------
def tile_of(col, row):
    """A header's 1x tile: region_tiles.py's pixel origin (col * 16, (row & 0xfff) * 8) in 32 x 16 tiles."""
    return (col * 16 // TW, (row & 0xfff) * 8 // TH)


def header_base(tadata):
    """The byte offset of the region headers: the first written TA data page (pbdump.written), None if nothing is written."""
    pages = pbdump.written(tadata) if tadata else []
    return pages[0] * pbdump.PAGE if pages else None


def slot(tadata, base, i):
    """Slot i's header: (word 0, word 1, word 2) or None past the dump's end."""
    o = base + 12 * i
    if tadata is None or o + 12 > len(tadata):
        return None
    return struct.unpack_from("<3I", tadata, o)


def headers(tadata, base, stop_zero=16):
    """[(slot, col, row, flags, stream)] from base, across pages, up to the first run of stop_zero all-zero slots."""
    out, zeros, i = [], 0, 0
    while True:
        s = slot(tadata, base, i)
        if s is None:
            break
        if s == (0, 0, 0):
            zeros += 1
            if zeros >= stop_zero:
                break
        else:
            zeros = 0
            w0 = s[0]
            out.append((i, (w0 >> 16) & 0xff, w0 & 0xffff, w0 >> 24, s[1]))
        i += 1
    return out


def baseline_layout(tadata, param, w, h):
    """The baseline reading of an unpoked job: (ok, text, layout).  ok iff every tile of the w x h target has exactly one
    header among the slots, with a non-zero stream whose block in the parameter buffer decodes (pbdump.stream: words before
    the filler).  layout = {'base': byte offset, 'slot': {tile: slot}, 'nslots': slots read}."""
    if tadata is None or param is None:
        return False, "no dump (tadata %s, param %s)" % ("read" if tadata else "none", "read" if param else "none"), None
    base = header_base(tadata)
    if base is None:
        return False, "the TA data dump has no written page", None
    hs = headers(tadata, base)
    want = target_tiles(w, h)
    seen = {}
    for i, col, row, flags, stream in hs:
        t = tile_of(col, row)
        if t in want and stream:
            seen.setdefault(t, []).append((i, stream))
    missing = sorted(want - set(seen))
    dup = sorted(t for t, v in seen.items() if len(v) > 1)
    nostream = []
    for t, v in sorted(seen.items()):
        st = v[0][1]
        if len(v) == 1 and (not 0 <= st - pbdump.PB_BASE <= len(param) - 128 or not pbdump.stream(param, st)):
            nostream.append(t)
    lay = {"base": base, "slot": {t: v[0][0] for t, v in seen.items() if len(v) == 1}, "nslots": len(hs)}
    if missing or dup or nostream:
        return False, ("headers of %d target tiles: %d without a header with a stream, %d with more than one, %d whose stream "
                       "block does not decode (first: %s)" % (len(want), len(missing), len(dup), len(nostream),
                                                              (missing + dup + nostream)[:3])), lay
    return True, "every one of the %d target tiles has one header with a stream (base 0x%x, %d header slots read)" % (
        len(want), base, len(hs)), lay


def in_place(tadata, layout, tile):
    """Whether the job's header at the baseline's slot of tile names that tile (word 0's position)."""
    s = slot(tadata, layout["base"], layout["slot"][tile])
    return s is not None and (s[0] or s[1]) and tile_of((s[0] >> 16) & 0xff, s[0] & 0xffff) == tile


def moved_tiles(tadata, layout, w, h):
    """(moved, emptied): the target tiles whose header is not at the baseline's slot (H-MOVED's 'moved'), and those whose
    header is in place with stream 0 (reported, not part of H-MOVED)."""
    moved, emptied = set(), set()
    for t in sorted(target_tiles(w, h)):
        if not in_place(tadata, layout, t):
            moved.add(t)
        else:
            s = slot(tadata, layout["base"], layout["slot"][t])
            if not s[1]:
                emptied.add(t)
    return moved, emptied


def observed_slots(tadata, base, w, h):
    """{tile: [slots]} of every header naming a target tile, wherever it is (the placement data the fold fits on)."""
    want = target_tiles(w, h)
    out = {}
    for i, col, row, flags, stream in headers(tadata, base, stop_zero=1 << 30) if tadata else []:
        t = tile_of(col, row)
        if t in want:
            out.setdefault(t, []).append(i)
    return out
