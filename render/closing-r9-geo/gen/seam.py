# SPDX-License-Identifier: MIT
"""seam.py: stages seam1 and seam4 (S9-geo, Q141): r8-geo's gen/seam.py (resgx545-data
render/closing-r8-geo/gen/seam.py) with the flag its premise needs. E934's rows ran without --aa4
and the module refused every multisampled TE_AA (sgxfive_render_check); here every row carries
--aa4 (a context made for 4x targets, which takes a TE_AA with bit 31 or 30), and seam1's rows
also dbg:render_rgn_arrays=1 (the context's region headers forced to one array, E502's, E504's
and E727's condition: sgxfive_render.c sgxfive_render_init, ctx->aa_ms = aa4 || setting, the
arrays sgx_render_rgn_arrays(setting, aa4)); seam4's rows take the four arrays --aa4 gives alone.
seam4 adds E828's j1r (288 x 144, mode 2, TE 0xe0000000, --aa4 at the default knob: 0 background,
hash 0x4a61860dcb4ab325) as a control. The rest of this docstring is r8-geo's.

stage seam (R8-1, Q141): tri-full renders at sizes never run and three single
triangles of other slopes, scored against the round's frozen R8-1 table, standard library only.

The table is the O8 offline package's (closing8/offline/r8-1, decision R8-1 (a)): gen/o8/ holds
q141_r8pred.py, .tsv, _cases.json and _sets.json byte for byte, checked against its own
q141_r8pred.sha256 (tsv 7fe3f9ab...) before anything is used. It was written from the landed region
model, resgx545-data texture/p1141/recompute/msaa_model.py (sha256 1c0e8205..., pinned, unchanged
since E727's freeze): per job the holes (tri-full: the pixels the model stores nothing in) or the
stored pixels (a single triangle) under H-REGION (a half tile takes only its half-region's list)
and its null H-UNION (halves=False), each a count and the sha256 of its "x y" lines sorted by
(y, x). Its slopes keep every vertex inside the 1.25 W x 1.25 H box the TA clips --tri-full to
(E762): (0, 0) (76, 0) (0, 38), (0, 0) (26, 0) (0, 78) at 64 x 64 and (0, 0) (150, 0) (0, 75) at
128 x 64, not the ranking's (100, 0) (0, 50) and (30, 0) (0, 90), which reach past it.
tests/test_r8geo.py recomputes every set from the model with the calls below and compares."""
import hashlib
import importlib.util
import os

DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
MODEL = "texture/p1141/recompute/msaa_model.py"
MODEL_SHA = "1c0e82052451eb30bb02bcae28778017e0a889e9a590d665ddb2fd33c6909a12"
SAMPLE = 0xeaa26e26            # E507's sample words, cmd:10 and cmd:16 (E502, E504, E727)
TRI = 0xff00ff00               # the tool's triangle colour
BG = 0xff203040                # the tool's background colour


def model():
    path = os.path.join(DATA, MODEL)
    blob = open(path, "rb").read()
    if hashlib.sha256(blob).hexdigest() != MODEL_SHA:
        raise SystemExit(f"{path} is not the landed region model")
    spec = importlib.util.spec_from_file_location("msaa_model", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


O8 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "o8")


def o8_checked():
    """The O8 files, each checked against q141_r8pred.sha256."""
    for ln in open(os.path.join(O8, "q141_r8pred.sha256")).read().splitlines():
        want, name = ln.split()
        if hashlib.sha256(open(os.path.join(O8, name), "rb").read()).hexdigest() != want:
            raise SystemExit(f"gen/o8/{name} is not the frozen O8 file")
    return O8


def jobs():
    """[(name, set, W, H, mode, te, vertices in pixels or None)]: the controls first, then the
    O8 table's order."""
    import json
    cases = json.load(open(os.path.join(o8_checked(), "q141_r8pred_cases.json")))
    out = []
    for c in sorted(cases, key=lambda c: c["set"] != "control"):
        v = None if c.get("triangle") == "tri-full" else tuple(
            (x // 256, y // 256) for x, y in c["vertices256"])
        out.append((c["name"], c["set"], c["W"], c["H"], c["mode"], int(c["te"], 16), v))
    return out


def args(w, h, mode, te, verts):
    a = ["tri"] + (["--tri-full"] if verts is None else []) + [
        "--keep-going", "--wait-ms", "20000", "--width", str(w), "--height", str(h),
        "--max-width", str(w), "--max-height", str(h), "--aa4", "--pixels",
        "--poke", "cmd:1=0x%08x" % te, "--poke", "cmd:10=0x%08x" % SAMPLE,
        "--poke", "cmd:13=0x%08x" % (0x80000000 | mode), "--poke", "cmd:16=0x%08x" % SAMPLE]
    if verts is not None:
        a += ["--tri-v", ",".join(str(c * 256) for p in verts for c in p),
              "--tri-z", "0.5,0.5,0.5", "--poke", "blk:2^=0x8"]
    return a


def prims(w, h, verts, M):
    return M.tri_full(w, h) if verts is None else [tuple((x * 16, y * 16) for x, y in verts)]


def stored(M, w, h, mode, te, verts, halves=True):
    """The set of (x, y) the triangle colour is stored at, under the model."""
    return set(M.predict(prims(w, h, verts, M), w, h, mode, te, halves=halves))


def cells_sha(cells):
    """The O8 table's set hash: "x y" lines sorted by (y, x)."""
    text = "".join(f"{x} {y}\n" for x, y in sorted(cells, key=lambda p: (p[1], p[0])))
    return hashlib.sha256(text.encode()).hexdigest()


# E828's j1r: the four-array 4x render that completed (render-closing-r3-rgn4 out/rgn4)
J1R = ("ctl-j1r-288x144", "control", 288, 144, 2, 0xe0000000, None)
J1R_HASH = "0x4a61860dcb4ab325"
