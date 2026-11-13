# SPDX-License-Identifier: MIT
"""mock/world.py: r9-k1's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv, the world's tokens and, as the real tool does, the two knobs it reads
(render_bg_layer, render_bg_src: the fake debugfs FAKE_DBGREAL the runner writes); never a case
name. It is as strict as t9 (sgxfive-test at 97447b04): an option the rows do not use, the
option without the knob or the knob without the option, a bgpixel slot without a bgpds one, or
a source address that is not the session's is a usage refusal (rc 2). Images come from
gen/bgl_model.py on the hardware's background (gen/bgmask.txt: 3034 of 4096), not the library
mock's 2998.

Worlds (EXPECT: the driver's status, {stage: the runner's status}; a stage a gate shut is absent):
  model     H-VM true (u, v iterated, vertex-major, the plane at the render box): every gate opens
            but s1n's (H-NONE fails), 94 jobs
  none      the layer's coordinates are not iterated (H-NONE): s0t and s0p run, the c-tex/c-noop
            texels are one texel, L-RAW reads one value; s1n opens, s1, s2 and s3 stay shut; s4
            runs (the layer was built)
  noread    H-ITER true but no poke of words 3-8 is read (H-NOREAD): s1 runs, its gate for s2
            and s3 stays shut (H-VM right on 0 held-out rows); s4 runs
  hang      the first layered probe (c-pos) hangs: an unexpected hang, the stage stops (rc 4)
  stale     a knob left on: the tool refuses the first layerless row (c-off, rc 2): rc 4
  eexist    the source overlaps the render's own pages (the tool builder's open check 4): the
            source maps first, the render context's mapping then fails (-EEXIST), so the first
            layered row (c-tex) ends rc 1 with `render context: File exists` (the library mock's
            own line for a source at 0x3e000000): rc 4
  rawvbad   c-rawv's pa1 varies along x (the second component is not v): hook_check stops s0p
            (rc 24); the s1n, s1, s2 and s3 gates stay shut (c-rawv FAILED), s4 runs (the
            layer was built)
  noline    c-tex prints no layer summary (inplace missing): the premise stops s0t (rc 25)
  mockgeom  the library mock's own geometry (2998 background pixels): c-off's hash is not E590's
            and c-tex finds 2998 identity texels of 3034: s0t's controls fail, every gate shuts"""
import os
import struct
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import bgl_model as M  # noqa: E402

EXPECT = {
    "model": (0, {"s0t": 0, "s0p": 0, "s1": 0, "s2": 0, "s3": 0, "s4": 0}),
    "none": (0, {"s0t": 0, "s0p": 0, "s1n": 0, "s4": 0}),
    "noread": (0, {"s0t": 0, "s0p": 0, "s1": 0, "s4": 0}),
    "hang": (4, {"s0t": 0, "s0p": 4}),
    "stale": (4, {"s0t": 4}),
    "eexist": (4, {"s0t": 4}),
    "rawvbad": (0, {"s0t": 0, "s0p": 24, "s4": 0}),
    "noline": (25, {"s0t": 25}),
    "mockgeom": (0, {"s0t": 0}),
}
TRI_OPTS = {"--bg-layer": 0, "--pixels": 0, "--keep-going": 0, "--dump-render": 1, "--words": 1,
            "--kpoke-render": 1, "--poke": 1}
PROBE_OPTS = {"--tri": 1, "--slot": 1, "--bg-layer": 0, "--pixels": 0}
USAGE = "usage: sgxfive-test [--mock[=rev1|harness|none]] ... (mock world: %s)\n"
_MASK = None


def mask(world):
    global _MASK
    if _MASK is None:
        _MASK = M.load_mask()
    if "mockgeom" in world:        # 36 more triangle pixels: the first 36 next to the triangle
        lines = open(M.MASK).read().split()
        edge = [(x, y) for x, y in _MASK if (x > 0 and lines[y][x - 1] == "#")
                or (x < 63 and lines[y][x + 1] == "#")][:36]
        return [p for p in _MASK if p not in set(edge)]
    return _MASK


def knobs():
    d = os.environ.get("FAKE_DBGREAL")
    vals = {"render_bg_layer": "N", "render_bg_src": "0"}
    for k in vals:
        p = os.path.join(d, k) if d else None
        if p and os.path.exists(p):
            vals[k] = open(p).read().strip() or vals[k]
    return vals["render_bg_layer"][:1] in ("Y", "y", "1"), int(vals["render_bg_src"], 0)


def parse(argv, table):
    """(opts {name: [values]}, positional) or None for an option t9 would refuse here."""
    opts, pos, i = {}, [], 1
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            if a not in table or i + table[a] >= len(argv):
                return None
            opts.setdefault(a, []).append(argv[i + 1] if table[a] else True)
            i += 1 + table[a]
        else:
            pos.append(a)
            i += 1
    return opts, pos


def kpokes(opts):
    out = {}
    for s in opts.get("--kpoke-render", []):
        if not s.startswith("1:bg:"):
            return None
        w, v = s[5:].split("=")
        if not 3 <= int(w) <= 22:
            return None
        out[int(w)] = int(v, 0)
    return out


def truth(world, pokes, layer):
    """{(x, y): pixel} of the background under the world's truth."""
    if not layer:
        return {p: M.BG for p in mask(world)}
    if "none" in world:
        return {p: M.texel(5, 5) for p in mask(world)}
    if "noread" in world:
        pokes = {w: v for w, v in pokes.items() if w not in range(3, 9)}
    o = M.obj(pokes)
    u, v, verts = M.coords("H-VM", o)
    out = {}
    for x, y in mask(world):
        px, py = Fraction(2 * x + 1, 2), Fraction(2 * y + 1, 2)
        pu, pv = M.plane(verts, u, px, py), M.plane(verts, v, px, py)
        tx = min(max(int(pu * 64 // 1), 0), 63) if pu is not None else 0      # clamp (the world's)
        ty = min(max(int(pv * 64 // 1), 0), 63) if pv is not None else 0
        out[(x, y)] = M.texel(tx, ty)
    return out


def image_rows(bg, fill):
    return {y: [bg.get((x, y), fill) for x in range(64)] for y in range(64)}


def param_bytes(layer, pokes, world):
    """A render_param dump: the object at E590's offset (words 0-2 the EDM's)."""
    words = [0x04000004, 0x00030001 if layer else 0x00030000, 0x04000002]
    if layer:
        o = M.obj(pokes)
        words += [o[w] for w in range(3, 23)]
    else:
        words += [0] * 6 + [0x00100000, 0x1000, 0, 0x10400010, 0, 0x00104000, 0x1000, 0]
        words += [0] * 6
    return bytes(M.OBJ_OFF) + struct.pack("<23I", *words)


def tri(argv, world):
    p = parse(argv, TRI_OPTS)
    if p is None:
        return dict(rc=2, err=USAGE % "an option tri does not take here")
    opts, pos = p
    if pos:
        return dict(rc=2, err=USAGE % "a stray argument")
    layer = "--bg-layer" in opts
    on, src = knobs()
    if "stale" in world and not layer:
        on = True
    if layer and (not on or src != M.SRC):
        return dict(rc=2, err="usage: sgxfive-test --bg-layer: debugfs render_bg_layer is N\n")
    if on and not layer:
        return dict(rc=2, err="usage: sgxfive-test --bg-layer: debugfs render_bg_layer is Y\n")
    pokes = kpokes(opts)
    if pokes is None:
        return dict(rc=2, err=USAGE % "a --kpoke-render that is not 1:bg:3..22")
    for s in opts.get("--poke", []):
        if not s.startswith("cmd:24="):
            return dict(rc=2, err=USAGE % "a --poke other than cmd:24")
    head = ""
    if layer:
        if "eexist" in world:
            return dict(rc=1, out="bg-layer: source 0x%08x 64x64 RGBA8888, knob Y\n" % M.SRC,
                        err="sgxfive-test: render context: File exists\n")
        head = "bg-layer: source 0x%08x 64x64 RGBA8888, knob Y\n" % M.SRC
    bg = truth(world, pokes, layer)
    rows = image_rows(bg, M.TRI)
    ref = {p: (M.texel(*p) if layer else M.BG) for p in bg}
    diff = sum(1 for p in bg if bg[p] != ref[p])
    inplace = sum(1 for p in bg if bg[p] == M.texel(*p))
    other = sum(1 for p in bg if M.decode(bg[p]) is None)
    h = M.HASH_OFF if not layer and "mockgeom" not in world else "0x%016x" % (
        hash(tuple(sorted(bg.items()))) & 0xffffffffffffffff)
    out = head + "tri: render context for targets up to 64x64\njob: ok\n"
    out += "target: 64x64 hash %s\ndiff: %d of 4096 pixels\noutside: 0 dwords\n" % (h, diff)
    if "--pixels" in opts:
        out += "".join("row %d: %s\n" % (y, " ".join("0x%08x" % v for v in rows[y]))
                       for y in range(64))
    out += "layout: fb 0x3e001000\n"
    summ = "tri 64x64 #1: %d triangle, %d background, 0 other; wrong 0 inside, %d outside, 0 at " \
        "edges; 0 if flipped; guard 0" % (4096 - len(bg), len(bg), diff)
    if layer and not ("noline" in world and "--words" in opts):
        summ += "; %d layer texels in place, %d elsewhere, %d not a texel" % (
            inplace, len(bg) - inplace - other, other)
    out += summ + "\n"
    files = {}
    for dd in opts.get("--words", []):
        tag = 0x00046400 | (1 << 25 if layer else 0)
        for k in (0, 1):
            files[os.path.join(dd, "words.%d.txt" % k)] = "rd:17=0x00000300\nrd:18=0x%08x\n" % tag
            files[os.path.join(dd, "ta3d.%d.bin" % k)] = bytes(192)
        out += "tri: words 1 to %s/words.1.txt (40 bytes), %s/ta3d.1.bin (192 bytes)\n" % (dd, dd)
    for dd in opts.get("--dump-render", []):
        files[os.path.join(dd, "tri.param.bin")] = param_bytes(layer, pokes, world)
        files[os.path.join(dd, "tri.tadata.bin")] = bytes(64)
    out += "tri: 1 renders ok\n" if diff == 0 else "tri: 0 of 1 renders ok\n"
    return dict(rc=0 if diff == 0 else 1, out=out, files=files)


def probe(argv, world):
    p = parse(argv, PROBE_OPTS)
    if p is None:
        return dict(rc=2, err=USAGE % "an option probe does not take here")
    opts, pos = p
    slots = opts.get("--slot", [])
    if opts.get("--tri") != ["bgpds:12"] or len(pos) != 1 or len(slots) != 1 \
            or not slots[0].startswith("bgpixel="):
        return dict(rc=2, err=USAGE % "not probe --tri bgpds:12 --slot bgpixel=FILE FILE")
    for f in (pos[0], slots[0][len("bgpixel="):]):
        if not os.path.exists(f):
            return dict(rc=1, err="sgxfive-test: %s: No such file or directory\n" % f)
    layer = "--bg-layer" in opts
    on, src = knobs()
    if layer and (not on or src != M.SRC):
        return dict(rc=2, err="usage: sgxfive-test --bg-layer: debugfs render_bg_layer is N\n")
    if on and not layer:
        return dict(rc=2, err="usage: sgxfive-test --bg-layer: debugfs render_bg_layer is Y\n")
    name = os.path.basename(pos[0])[:-4]
    comp = 1 if slots[0].endswith("pa1.bin") else 0
    head = "bg-layer: source 0x%08x 64x64 RGBA8888, knob Y\n" % M.SRC if layer else ""
    head += "probe %s: scratch at 0x3e00e000 (64 KiB)\nprobe %s: tri 64x64, bgpds bgpixel " \
        "replaced\n" % (name, name)
    if "hang" in world and layer and name == "r9k-pos":
        return dict(rc=3, out=head + "probe %s: failed: job hung, context lost (Timer expired)\n"
                    "probe %s: scratch unchanged\n" % (name, name), kmsg=["job 7 hung"])
    vals = {}
    for x, y in mask(world):
        if name == "r9k-pos":
            v = M.bits(x + 0.5)
        elif "none" in world:
            v = 0x3e000000
        elif comp == 1 and "rawvbad" in world:
            v = M.bits((x + 0.5) / 64)
        else:
            v = M.bits((x + 0.5) / 64 if comp == 0 else (y + 0.5) / 64)
        vals[(x, y)] = v
    rows = image_rows(vals, M.TRI)
    cnt = {}
    for v in vals.values():
        cnt[v] = cnt.get(v, 0) + 1
    top = sorted(cnt.items(), key=lambda kv: -kv[1])[:3]
    out = head + "probe %s: o0 mixed %s 0xff00ff00 x%d\n" % (
        name, " ".join("0x%08x x%d" % kv for kv in top), 4096 - len(vals))
    if "--pixels" in opts:
        out += "".join("probe %s: row %d: %s\n" % (name, y, " ".join("%08x" % v for v in rows[y]))
                       for y in range(64))
    out += "probe %s: scratch unchanged\n" % name
    return dict(rc=0, out=out)


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None                      # the health pair (t4): an exact draw
    if tool != "t9":
        return dict(rc=2, err=USAGE % "only t9 runs rows")
    if argv[0] == "tri":
        return tri(argv, world)
    if argv[0] == "probe":
        return probe(argv, world)
    return dict(rc=2, err=USAGE % "a command the rows do not use")
