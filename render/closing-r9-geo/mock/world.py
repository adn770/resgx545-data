# SPDX-License-Identifier: MIT
"""mock/world.py: r9-geo's argv-driven fake laptop for kit/session.py mock (r8-geo's world,
copied and extended). answer() sees the tool's name, the argv and the world's tokens, never a case
name: a probe's program is named by its file in argv (the generator's program of that name,
gen/), a tri render by its options. As strict as sgxfive-test (resgx545 4623753): an option the
command does not take, a missing value, a --tri-z outside 0 to 1, a --scratch-pages outside 16 to
64 or a program file that is not there is refused (rc 2, usage), as the real tool does.

The kernel side of a tri render is modelled as the module B60AB0B4 (fork 2a650d74) does it: a
context takes a TE_AA with bit 31 or 30 only when made with --aa4 or while the debugfs knob
render_rgn_arrays is set (sgxfive_render_init: ctx->aa_ms = aa4 || setting), else the job is
refused at submission (`job: rejected (Invalid argument)`, rc 1, a diff line and the untouched
target, as E934 saw); the context's region-header arrays are the knob when 1, 2 or 4, else 4
with --aa4 and 1 without. The knob is read from the fake debugfs the kit's mock keeps
(FAKE_DBGREAL/render_rgn_arrays), or from the world token knob1 when there is none (the tests'
argv twin).

Worlds (the hypotheses the scorer must tell apart, and the stops the plan relies on):
  model     seam: one array H-REGION, four arrays H-SAME4; cube: H-E561, H-NN, H-HIGHAXIS,
            H-SEAM-ADJ; addr: H-OFF180 (T3 inert, u5 as E932)
  alt       seam: one array H-UNION (seam1's control fails), four arrays H-FULL4; cube: H-MORTON at
            32 and H-PAIRSWAP at 64, H-PAD64, H-LOWAXIS, H-SEAM-WRAP; addr: H-OFFSCALE, H-OFF360,
            T3 0 removes the offset, u5 reads 128 outside
  nopix     no cube2 row but the control prints pixel rows: the second stops cube2 by its rule
            (rc 24), the driver goes on and addr2 runs
  ctlnopix  seam1's first control prints no pixel rows: the premise stops the session (rc 25)
  reject    the kernel refuses every multisampled TE_AA even with --aa4: seam1's first control
            is `job: rejected` with a diff line, which expectdiff does not take: stop (rc 4)
  fault     the first held-out addr2 row faults (a BIF fault latched): addr2 stops (rc 4)
  hang      the first held-out cube2 row never returns (timeout rc 124): cube2 stops (rc 6)
"""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
import addr as A  # noqa: E402
import cube as C  # noqa: E402
import seam as S  # noqa: E402
import texprog as T  # noqa: E402

EXPECT = {"model": (0, {"seam1": 0, "seam4": 0, "cube2": 0, "addr2": 0}),
          "alt": (0, {"seam1": 0, "seam4": 0, "cube2": 0, "addr2": 0}),
          "nopix": (0, {"seam1": 0, "seam4": 0, "cube2": 24, "addr2": 0}),
          "ctlnopix": (25, {"seam1": 25}),
          "reject": (4, {"seam1": 4}),
          "fault": (4, {"seam1": 0, "seam4": 0, "cube2": 0, "addr2": 4}),
          "hang": (6, {"seam1": 0, "seam4": 0, "cube2": 6})}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
PROBE_VAL = {"--temps", "--scratch-pages", "--tri", "--width", "--height", "--vertices",
             "--vtx-coords", "--vdm", "--dump-render", "--slot"}
PROBE_FLAG = {"--coords", "--pixels"}
TRI_VAL = {"--wait-ms", "--width", "--height", "--max-width", "--max-height", "--poke",
           "--tri-v", "--tri-z"}
TRI_FLAG = {"--tri-full", "--keep-going", "--pixels", "--aa4"}
_RULE = []
_JOBS = {}


def parse(argv, vals, flags):
    """(options as {name: [values]}, positional) or None for a usage error."""
    o, pos, i = {}, [], 1
    while i < len(argv):
        a = argv[i]
        if a in flags:
            o.setdefault(a, []).append(True)
            i += 1
        elif a in vals and i + 1 < len(argv):
            o.setdefault(a, []).append(argv[i + 1])
            i += 2
        elif a.startswith("--"):
            return None
        else:
            pos.append(a)
            i += 1
    return o, pos


def rows_text(prefix, img, w, h, hexfmt):
    return "".join(prefix + "row %d: " % y + " ".join(hexfmt % img[(x, y)] for x in range(w))
                   + "\n" for y in range(h))


def rule():
    if not _RULE:
        _RULE.append(C.rule())
    return _RULE[0]


def jobs_by_bin():
    if not _JOBS:
        for name, st, spec, n, t0, kind in C.jobs():
            _JOBS[name + ".bin"] = ("cube", (spec, n, kind), st)
        for name, st, n, um, vm, t3, kind in A.jobs():
            _JOBS[name + ".bin"] = ("addr", (name, n, um, vm, t3, kind), st)
    return _JOBS


def knob():
    """render_rgn_arrays as the fake debugfs holds it (0 when the file is not there)."""
    real = os.environ.get("FAKE_DBGREAL")
    if real and os.path.isfile(os.path.join(real, "render_rgn_arrays")):
        v = open(os.path.join(real, "render_rgn_arrays")).read().strip() or "0"
        return int(v, 0)
    return None


# ---- probe: cube2 and addr2 --------------------------------------------------------------------
def cube_value(R, c, n, kind, world):
    alt = "alt" in world
    fn = (64 if alt else 16) if kind == "n4" else n * n
    law = "MORTON" if kind == "n4" else ("MORTON" if n == 32 else "PAIRSWAP") if alt else "E561"
    st, v = C.predict(R, c, n, law, fn)
    if st == "face-tie":
        f = C.tie_face(c, "H-LOWAXIS" if alt else "H-HIGHAXIS")
        a = f // 2
        c = tuple(t * 2 if i == a else t for i, t in enumerate(c))
        st, v = C.predict(R, c, n, law, fn)
    if st == "texel-tie":
        q = C.st(R, c, n)
        face, vs, vt, ma, order = q
        s, t = min(max(C.flo(vs), 0), n - 1), min(max(C.flo(vt), 0), n - 1)
        v = 0xD0000000 | (face * fn + C.local(s, t, order, n, law))
    return "ok", v


def cube_image(spec, n, kind, world):
    R = rule()
    img = {}
    for p, c in C.coords_of(spec).items():
        img[p] = cube_value(R, c, n, kind, world)[1]
        if kind == "edge":
            tl = C.blend(R, c, n, "H-SEAM-WRAP" if "alt" in world else "H-SEAM-ADJ")
            if tl is not None:
                img[p] = sum(int(b + T.F(1, 2)) << (8 * i) for i, b in enumerate(C.blend_bytes(tl)))
    return img


def addr_image(name, n, um, vm, t3, kind, world):
    if um == 0:
        model = "REPEAT"
    elif "alt" not in world:
        model = A.models(name, um, n, kind)[0]
    elif kind == "uv":
        model = "H-OFF360"
    elif "-t3-" in name:
        model = "H-MASK-V" if t3 == 0 else "H-T3-INERT"
    elif um == 5:
        model = "ALT5"
    else:
        model = "H-OFFSCALE"
    if model == "ALT5":
        img = A.image(n, um, vm, kind, "H-U5-E932")
        return {p: 128 if v in (140, 156) else v for p, v in img.items()}
    return A.image(n, um, vm, kind, model)


def probe(argv, world):
    r = parse(argv, PROBE_VAL, PROBE_FLAG)
    if r is None or len(r[1]) != 1:
        return USAGE
    o, (path,) = r
    if "--scratch-pages" in o and not 16 <= int(o["--scratch-pages"][0], 0) <= 64:
        return USAGE
    if not os.path.isfile(path):
        return dict(rc=2, err="sgxfive-test: %s: No such file or directory\n" % path)
    base = os.path.basename(path)
    name = base[:-4]
    j = jobs_by_bin().get(base)
    if j is None:
        return USAGE
    pages = int(o.get("--scratch-pages", ["16"])[0], 0)
    out = ["programs asm", "probe %s: scratch at 0x3e003000 (%d KiB)" % (name, 4 * pages)]
    held = j[2] != "control"
    if "hang" in world and j[0] == "cube" and held and name == first_held("cube"):
        return dict(rc=124, out="")
    if "fault" in world and j[0] == "addr" and held and name == first_held("addr"):
        return dict(rc=3, out="probe %s: failed: job faulted\n" % name,
                    kmsg=["sgxfive: BIF fault 0x90004 at 0x1000c016 stalls job 9"],
                    latch=(4, 0x1000c016))
    nopix = "nopix" in world and j[0] == "cube" and held
    if j[0] == "cube":
        spec, n, kind = j[1]
        if n == 64 and pages < 24:
            return dict(rc=3, out="probe %s: failed: job faulted\n" % name,
                        kmsg=["sgxfive: BIF fault 0x90004 at 0x1000f016"], latch=(4, 0x1000f016))
        img = cube_image(spec, n, kind, world)
    else:
        name_, n, um, vm, t3, kind = j[1]
        if pages < A.PAGES:
            return dict(rc=3, out="probe %s: failed: job faulted\n" % name,
                        kmsg=["sgxfive: BIF fault 0x90004 at 0x1000c016"], latch=(4, 0x1000c016))
        im = addr_image(name_, n, um, vm, t3, kind, world)
        img = {p: 0xD0000000 | (v + A.BASE) for p, v in im.items()}
    if not nopix:
        out.append(rows_text("probe %s: " % name, img, T.W, T.H, "%08x").rstrip("\n"))
    return dict(out="\n".join(out) + "\n")


def first_held(kind):
    js = C.jobs() if kind == "cube" else A.jobs()
    return next(j[0] for j in js if j[1] != "control")


# ---- tri: seam1 and seam4 ----------------------------------------------------------------------
def tri(argv, world):
    r = parse(argv, TRI_VAL, TRI_FLAG)
    if r is None or r[1]:
        return USAGE
    o = r[0]
    w, h = int(o["--width"][0]), int(o["--height"][0])
    pokes = dict(p.split("=", 1) for p in o.get("--poke", []) if "^=" not in p)
    if "--tri-z" in o and not all(0 <= float(z) <= 1 for z in o["--tri-z"][0].split(",")):
        return dict(rc=2, err="sgxfive-test: bad option --tri-z (three screen depths, 0 to 1, "
                              "comma separated)\n")
    te, mode = int(pokes["cmd:1"], 16), int(pokes["cmd:13"], 16) & 3
    verts = None
    if "--tri-v" in o:
        c = [int(v) // 256 for v in o["--tri-v"][0].split(",")]
        verts = ((c[0], c[1]), (c[2], c[3]), (c[4], c[5]))
    elif "--tri-full" not in o:
        return USAGE
    aa4 = "--aa4" in o
    setting = knob()
    if setting is None:
        setting = 1 if "knob1" in world else 0
    head = ["tri: render context for targets up to %dx%d" % (w, h)]
    if aa4:
        head.append("tri: render context made for 4x targets (DRM_SGXFIVE_CTX_RENDER_AA_4X)")
    ms = te >> 30 & 3
    if ms and (not (aa4 or setting) or "reject" in world):
        img = {(x, y): 0xdeadbeef for y in range(h) for x in range(w)}
        out = head + ["job: rejected (Invalid argument)", "target: %dx%d hash 0x0" % (w, h),
                      "diff: %d of %d pixels" % (w * h, w * h), "outside: 0 dwords",
                      rows_text("", img, w, h, "0x%08x").rstrip("\n")]
        return dict(rc=1, out="\n".join(out) + "\n", err="sgxfive-test: render: Invalid argument\n")
    arrays = setting if setting in (1, 2, 4) else 4 if aa4 else 1
    if arrays == 1:
        st = S.stored(S.model(), w, h, mode, te, verts, halves="alt" not in world)
    elif "alt" in world and verts is None:
        st = {(x, y) for y in range(h) for x in range(w)}          # H-FULL4
    else:
        st = S.stored(S.model(), w, h, mode, te, verts)            # H-SAME4
    img = {(x, y): S.TRI if (x, y) in st else S.BG for y in range(h) for x in range(w)}
    wrong = w * h - len(st) if verts is None else 0
    if "ctlnopix" in world and (w, h, te, verts) == (64, 64, 0x60000000, None):
        img = None
    hsh = S.J1R_HASH if (w, h) == (288, 144) and not wrong else "0x0123456789abcdef"
    out = head + ["job: ok", "target: %dx%d hash %s" % (w, h, hsh),
                  "diff: %d of %d pixels" % (wrong, w * h), "outside: 0 dwords"]
    if img is not None:
        out.append(rows_text("", img, w, h, "0x%08x").rstrip("\n"))
    return dict(rc=1 if wrong else 0, out="\n".join(out) + "\n")


def answer(tool, argv, world):
    if tool != "t4" or not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe":
        return probe(argv, world)
    if argv[0] == "tri":
        return tri(argv, world)
    return None
