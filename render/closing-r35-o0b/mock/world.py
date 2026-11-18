# SPDX-License-Identifier: MIT
"""mock/world.py: r35-o0b's argv-driven fake laptop for kit/session.py mock (the corrected rerun of
r35-o0, E1143). answer() sees the tool's name, the argv, the world's tokens and the fake laptop's
state (its reset count and this world's own state files in FAKE_DIR), never a case name; it
returns dict(rc, out, err, kmsg, latch) or a refusal (usage, rc 2). As strict as t10 (resgx545
a581c06) on this session's rows: `probe --temps 32 --pixels --tri pixel --width N --height N
--max-width 128 --max-height 128 [--vtx-coords 2 --slot pixpds=F:12 --slot vtxuse=F] FILE`, N 64
or 128, the A' form with both slots and --vtx-coords 2 and only it, FILE one of bins/a.bin,
k.bin, p.bin; and t10's bare `fill` and `tri` (the health pair and the h5 fill alike).

Images: the triangle's pixels are E417's job A at 64 and 128 (mock/kept/tri*.txt), the pixels a
pass-through keeps are E417's P jobs (mock/kept/left*.txt). A' writes A'(x, y), K 0xff00ff00. P
reads, on its kept pixels, the previous job's image at a pixel the world names (the state in
FAKE_DIR: the last job's image, the last triangle probe's image, the reset count at the last
job).

Worlds (EXPECT: the driver's status and the stage's runner status):
  model      = offsets (the kit's default world name)                                   0
  offsets    H-OFFSETS: P reads the previous job at the same pixel or 16 rows higher (every
             fifth pixel where that pixel was drawn); P 128 after A' 64 at (-64, -16) right of
             x 64; P 64 after A' 128 keeps nothing; a reset keeps it, the fill replaces it  0
  samepix    every kept pixel at the same pixel (P 64 after 128 still keeps nothing)        0
  shift      P reads the previous job one pixel to the right (offsets outside the fit)     0
  other      after an A', P reads values no job wrote                                     0
  sizekeep   P 64 after A' 128 keeps the same pixels                                      0
  resetclear after a reset P reads the background                                         0
  trionly    P reads the last triangle probe's image, through the fill                    0
  anopix     the first A' prints no pixel rows: hook_check stops o first (24)
  pshort     the second P prints one pixel row short: hook_check stops o (24)
  fillbad    the h5 fill prints `fill: FAIL`: hook_check stops o (24)
  fault      the first A' faults (no expectfault): o 4
  hang       the first P does not return (timeout rc 124): o 6
"""
import json
import os
import struct

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECT = {
    "model": (0, {"o": 0}),
    "offsets": (0, {"o": 0}),
    "samepix": (0, {"o": 0}),
    "shift": (0, {"o": 0}),
    "sizekeep": (0, {"o": 0}),
    "other": (0, {"o": 0}),
    "resetclear": (0, {"o": 0}),
    "trionly": (0, {"o": 0}),
    "anopix": (24, {"o": 24}),
    "pshort": (24, {"o": 24}),
    "fillbad": (24, {"o": 24}),
    "fault": (4, {"o": 4}),
    "hang": (6, {"o": 6}),
}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")


def constants():
    out = {}
    for ln in open(os.path.join(KP, "gen", "constants.txt")).read().splitlines():
        k, _, v = ln.partition("=")
        out[k] = v
    return out


C = constants()
K, BG, FILL = (int(C[k], 16) for k in ("K", "BG", "FILL"))


def pixels(name):
    with open(os.path.join(KP, "mock", "kept", name)) as f:
        return [tuple(int(t) for t in ln.split()) for ln in f if ln.strip()]


TRI = {n: pixels(f"tri{n}.txt") for n in (64, 128)}
LEFT = {n: pixels(f"left{n}.txt") for n in (64, 128)}


def kept(name):
    return open(os.path.join(KP, "mock", "kept", name)).read()


def fbits(f):
    return struct.unpack("<I", struct.pack("<f", f))[0]


def f_a(x, y, n):
    return (fbits((x + 0.5) * 2.0 / n - 1.0) & 0xFFFF0000) | (fbits((y + 0.5) * 2.0 / n - 1.0) >> 16)


# ---- the images: {"kind", "n", "pix": {(x, y): value}} (pixels not named are BG) -------------
def img_a(n):
    return {"kind": "a", "n": n, "pix": {(x, y): f_a(x, y, n) for x, y in TRI[n]}}


def img_k(n):
    return {"kind": "k", "n": n, "pix": {p: K for p in TRI[n]}}


def img_fill():
    return {"kind": "fill", "n": 64, "pix": {(x, y): FILL for y in range(32) for x in range(64)}}


def img_tri():
    return {"kind": "tri", "n": 64, "pix": {p: K for p in TRI[64]}}


def img_p(n, last, lasttri, reset_between, world):
    if "resetclear" in world and reset_between:
        return {"kind": "p", "n": n, "pix": {}}
    src = lasttri if "trionly" in world and last and last["kind"] == "fill" else last
    if src is not None and src["kind"] == "a" and src["n"] > n and "sizekeep" not in world:
        return {"kind": "p", "n": n, "pix": {}}
    samepix = "samepix" in world or "sizekeep" in world or "resetclear" in world \
        or "trionly" in world
    out = {}
    for x, y in LEFT[n]:
        if src is None:
            continue
        if "other" in world and src["kind"] == "a":
            out[(x, y)] = 0x0BAD0000 | x << 8 | y
            continue
        q = (x, y)
        if "shift" in world:
            q = (x + 1, y)
        elif not samepix and src["n"] < n and x >= 64:
            q = (x - 64, y - 16)
        elif not samepix and (x + y) % 5 == 0 and (x, y - 16) in src["pix"]:
            q = (x, y - 16)
        v = src["pix"].get(q)
        if v is not None:
            out[(x, y)] = v
    return {"kind": "p", "n": n, "pix": out}


def text(name, img, rows=None):
    n = img["n"]
    counts = {}
    for y in range(n):
        for x in range(n):
            v = img["pix"].get((x, y), BG)
            counts[v] = counts.get(v, 0) + 1
    items = sorted(counts.items(), key=lambda kv: -kv[1])
    if len(items) == 1:
        o0 = "probe %s: o0 0x%08x (%d of %d)" % (name, items[0][0], n * n, n * n)
    else:
        o0 = "probe %s: o0 mixed " % name + " ".join("0x%08x x%d" % kv for kv in items[:4])
        rest = sum(c for _, c in items[4:])
        o0 += " other x%d" % rest if rest else ""
    lines = ["programs asm", "probe %s: scratch at 0x3e012000 (64 KiB)" % name,
             "probe %s: tri %dx%d, pixel replaced" % (name, n, n), o0]
    for y in range(n if rows is None else rows):
        lines.append("probe %s: row %d: " % (name, y)
                     + " ".join("%08x" % img["pix"].get((x, y), BG) for x in range(n)))
    return "\n".join(lines) + "\n"


# ---- the argv -----------------------------------------------------------------------------
def parse(argv):
    """(kind, n, path) of a probe argv of this session's forms, or None (usage)."""
    if not argv or argv[0] != "probe":
        return None
    a, i, o, path = argv, 1, {}, None
    vals = {"--temps", "--tri", "--width", "--height", "--max-width", "--max-height",
            "--vtx-coords", "--slot"}
    while i < len(a):
        if a[i] == "--pixels":
            o.setdefault("--pixels", []).append(True)
            i += 1
        elif a[i] in vals and i + 1 < len(a):
            o.setdefault(a[i], []).append(a[i + 1])
            i += 2
        elif a[i].startswith("--") or path is not None:
            return None
        else:
            path = a[i]
            i += 1
    one = {k: v[0] for k, v in o.items() if len(v) == 1}
    if (path is None or one.get("--temps") != "32" or one.get("--tri") != "pixel"
            or "--pixels" not in o or one.get("--max-width") != "128"
            or one.get("--max-height") != "128" or one.get("--width") not in ("64", "128")
            or one.get("--height") != one.get("--width")):
        return None
    kind = {"a.bin": "a", "k.bin": "k", "p.bin": "p"}.get(os.path.basename(path))
    slots = dict(s.split("=", 1) for s in o.get("--slot", []) if "=" in s)
    if kind is None or len(slots) != len(o.get("--slot", [])):
        return None
    if kind == "a":
        if (set(slots) != {"pixpds", "vtxuse"} or not slots["pixpds"].endswith(":12")
                or one.get("--vtx-coords") != "2"):
            return None
        files = [slots["pixpds"][:-3], slots["vtxuse"]]
    else:
        if slots or "--vtx-coords" in o:
            return None
        files = []
    for f in [path] + files:
        if not os.path.isfile(f):
            return dict(rc=2, err="sgxfive-test: %s: No such file or directory\n" % f)
    return kind, int(one["--width"]), path


# ---- the state in FAKE_DIR ---------------------------------------------------------------
def _path(name):
    d = os.environ.get("FAKE_DIR")
    return os.path.join(d, name) if d else None


def load(name):
    p = _path(name)
    if not p or not os.path.exists(p):
        return None
    j = json.load(open(p))
    j["pix"] = {tuple(int(t) for t in k.split(",")): v for k, v in j["pix"].items()}
    return j


def save(name, img):
    p = _path(name)
    if p and img is not None:
        with open(p, "w") as f:
            json.dump(dict(img, pix={"%d,%d" % k: v for k, v in img["pix"].items()}), f)


def count(name):
    p = _path(name)
    n = (int(open(p).read()) if p and os.path.exists(p) else 0) + 1
    if p:
        open(p, "w").write(str(n))
    return n


def resets():
    p = _path("writes")
    return sum(1 for ln in open(p) if ln.startswith("reset")) if p and os.path.exists(p) else 0


def reset_since_last():
    p = _path("r35o_resets")
    was = int(open(p).read()) if p and os.path.exists(p) else -1
    return resets() != was


def mark_job():
    p = _path("r35o_resets")
    if p:
        open(p, "w").write(str(resets()))


# ---- one job (shared with tests/test_score.py's simulation) --------------------------------
def job(kind, n, last, lasttri, reset_between, world):
    """The image a job draws: (image, new last, new lasttri)."""
    if kind == "a":
        img = img_a(n)
    elif kind == "k":
        img = img_k(n)
    elif kind == "fill":
        img = img_fill()
    elif kind == "tri":
        img = img_tri()
    else:
        img = img_p(n, last, lasttri, reset_between, world)
    return img, img, (img if kind in ("a", "k", "p", "tri") else lasttri)


def answer(tool, argv, world):
    if tool != "t10":
        return USAGE
    if argv in (["fill"], ["tri"]):
        kind = argv[0]
        img, last, lasttri = job(kind, 64, load("r35o_last"), load("r35o_lasttri"), False, world)
        save("r35o_last", last)
        save("r35o_lasttri", lasttri)
        mark_job()
        if kind == "tri":
            return dict(out=kept("tri.txt"))
        t = kept("fill.txt")
        if "fillbad" in world and count("r35o_fill") == 2:      # the stage-begin health's is 1
            t = t.replace("fill: ok", "fill: FAIL")
        return dict(out=t)
    r = parse(argv)
    if r is None:
        return USAGE
    if isinstance(r, dict):
        return r
    kind, n, path = r
    name = os.path.basename(path).split(".")[0]
    seen = count("r35o_" + kind)
    if "fault" in world and kind == "a" and seen == 1:
        return dict(rc=3, out="programs asm\nprobe a: failed: job faulted, context lost "
                    "(Input/output error)\nprobe a: scratch unchanged\n",
                    kmsg=["sgxfive: BIF fault 0x80020 at 0x3e012001 stalls job 7, recovering"],
                    latch=(0x1000, 0x3E012001))
    if "hang" in world and kind == "p" and seen == 1:
        return dict(rc=124, out="")
    img, last, lasttri = job(kind, n, load("r35o_last"), load("r35o_lasttri"),
                             reset_since_last(), world)
    save("r35o_last", last)
    save("r35o_lasttri", lasttri)
    mark_job()
    rows = None
    if "anopix" in world and kind == "a" and seen == 1:
        rows = 0
    if "pshort" in world and kind == "p" and seen == 2:
        rows = n - 1
    return dict(out=text(name, img, rows))


def simulate(rows, world):
    """{row name: output text} of a table run in order on a fresh laptop (tests): the stage
    begins with the health pair, every row but `noreset` ones after a reset."""
    last, lasttri = None, None
    for kind in ("fill", "tri"):
        _, last, lasttri = job(kind, 64, last, lasttri, False, world)
    out = {}
    for r in rows:
        a = r["args"].split()
        between = "noreset" not in r["knobs"]
        if a == ["fill"]:
            img, last, lasttri = job("fill", 64, last, lasttri, between, world)
            out[r["name"]] = kept("fill.txt")
            continue
        kind = os.path.basename(a[-1].strip('"')).split(".")[0]
        n = int(a[a.index("--width") + 1])
        img, last, lasttri = job(kind, n, last, lasttri, between, world)
        out[r["name"]] = text(kind, img)
    return out
