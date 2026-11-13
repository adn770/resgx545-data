#!/usr/bin/env python3
"""Q141, round 8 decision R8-1: the frozen prediction table of r8-geo's Q141 stage, written from the
landed region model (resgx545-data texture/p1141/recompute/msaa_model.py, sha256 1c0e8205...,
E727's freeze, unchanged; checked here before anything is computed). Standard library only.

Two rivals per job: H-REGION (the model as landed: a tile's left half takes only the left half-
region's primitive list, its right half only the right one's) and H-UNION (the same with
halves=False: both halves take the union of the two lists). `--tri-full` is the tool's one triangle
(0, 0), (3W, 0), (0, 3H), which the TA clips to the quad (0, 0) to (1.25 W, 1.25 H) split along
(1.25 W, 0) to (0, 1.25 H) (E762's decode): the model's tri_full(W, H). The single triangles
(`--tri-v`, 1/256 pixel) lie inside that quad, so the clip leaves them whole [infer: no clip
inside the 1.25 box, E762]; the rivals differ for them where a stored half's samples fall outside
its own half-region (both lists then hold the one triangle or neither).

Quantities: tri-full jobs `holes` (pixels of the target the model stores nothing in) and
`holes_sha256`; single triangles `stored` and `stored_sha256` (the pixels the model stores the
triangle in). A set's sha256 is over the text of its pixels sorted by (y, x), one "x y" line each.

    python3 q141_r8pred.py OUTDIR   writes OUTDIR/q141_r8pred.tsv, q141_r8pred_cases.json and
                                     q141_r8pred_sets.json, prints a summary
"""
import hashlib
import importlib.util
import json
import os
import sys

DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
MODEL = DATA + "/texture/p1141/recompute/msaa_model.py"
MODEL_SHA = "1c0e82052451eb30bb02bcae28778017e0a889e9a590d665ddb2fd33c6909a12"

TE = {"2": 0x20000000, "6": 0x60000000, "a": 0xa0000000, "e": 0xe0000000}
# (name, set, W, H, mode, te nibble, vertices in pixels or None for --tri-full)
CASES = [
    ("tf-96x64-m0-e", "heldout", 96, 64, 0, "e", None),
    ("tf-96x64-m1-6", "heldout", 96, 64, 1, "6", None),
    ("tf-96x64-m1-e", "heldout", 96, 64, 1, "e", None),
    ("tf-112x80-m0-6", "heldout", 112, 80, 0, "6", None),
    ("tf-112x80-m1-6", "heldout", 112, 80, 1, "6", None),
    ("tf-112x80-m1-e", "heldout", 112, 80, 1, "e", None),
    ("tf-128x96-m0-e", "heldout", 128, 96, 0, "e", None),
    ("tf-128x96-m1-6", "heldout", 128, 96, 1, "6", None),
    ("tf-128x96-m2-6", "heldout", 128, 96, 2, "6", None),
    ("tf-64x96-m1-6", "heldout", 64, 96, 1, "6", None),
    ("tf-64x96-m2-6", "heldout", 64, 96, 2, "6", None),
    ("tf-64x96-m0-a", "heldout", 64, 96, 0, "a", None),
    ("tf-80x48-m0-a", "heldout", 80, 48, 0, "a", None),
    ("tf-80x48-m1-6", "heldout", 80, 48, 1, "6", None),
    ("tf-96x64-m2-a", "twin", 96, 64, 2, "a", None),
    ("tf-128x96-m2-a", "twin", 128, 96, 2, "a", None),
    ("sl-a-64x64-m1-6", "heldout", 64, 64, 1, "6", ((0, 0), (76, 0), (0, 38))),
    ("sl-a-64x64-m2-e", "heldout", 64, 64, 2, "e", ((0, 0), (76, 0), (0, 38))),
    ("sl-b-64x64-m1-6", "heldout", 64, 64, 1, "6", ((0, 0), (26, 0), (0, 78))),
    ("sl-b-64x64-m2-e", "heldout", 64, 64, 2, "e", ((0, 0), (26, 0), (0, 78))),
    ("sl-c-128x64-m1-6", "heldout", 128, 64, 1, "6", ((0, 0), (150, 0), (0, 75))),
    ("sl-c-128x64-m2-e", "heldout", 128, 64, 2, "e", ((0, 0), (150, 0), (0, 75))),
    # controls that can fail: E502's A-m1-te60-64x64 (64 holes, its set kept in isp/msaa-ident)
    # and E504's te-m2-20-64x64 (0 holes)
    ("ctl-a-m1-6-64x64", "control", 64, 64, 1, "6", None),
    ("ctl-tf-64x64-m2-2", "control", 64, 64, 2, "2", None),
]


def sha(cells):
    text = "".join(f"{x} {y}\n" for x, y in sorted(cells, key=lambda p: (p[1], p[0])))
    return hashlib.sha256(text.encode()).hexdigest()


def main(out):
    blob = open(MODEL, "rb").read()
    if hashlib.sha256(blob).hexdigest() != MODEL_SHA:
        sys.exit("msaa_model.py is not E727's frozen model")
    spec = importlib.util.spec_from_file_location("msaa_model", MODEL)
    mm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mm)
    rows, cases, sets = [], [], {}
    for name, cset, W, H, mode, te, tri in CASES:
        prims = mm.tri_full(W, H) if tri is None else [tuple((16 * x, 16 * y) for x, y in tri)]
        c = {"name": name, "set": cset, "W": W, "H": H, "mode": mode, "te": f"{TE[te]:#010x}"}
        if tri is None:
            c["triangle"] = "tri-full"
        else:
            c["vertices256"] = [[256 * x, 256 * y] for x, y in tri]
        cases.append(c)
        for model, kw in (("H-REGION", {}), ("H-UNION", {"halves": False})):
            got = mm.predict(prims, W, H, mode, TE[te], **kw)
            if tri is None:
                cells = [(x, y) for y in range(H) for x in range(W) if (x, y) not in got]
                q = "holes"
            else:
                cells = list(got)
                q = "stored"
            cells = sorted(cells, key=lambda p: (p[1], p[0]))
            rows.append((name, q, str(len(cells)), model, cset))
            rows.append((name, q + "_sha256", sha(cells), model, cset))
            sets[f"{name} {model}"] = cells
    src = f"msaa_model.py {MODEL_SHA[:8]}"
    with open(f"{out}/q141_r8pred.tsv", "w") as fh:
        fh.write("case\tquantity\tvalue\tmodel\tset\tsource\n")
        for r in rows:
            fh.write("\t".join(r + (src,)) + "\n")
    with open(f"{out}/q141_r8pred_cases.json", "w") as fh:
        json.dump(cases, fh, indent=1)
        fh.write("\n")
    with open(f"{out}/q141_r8pred_sets.json", "w") as fh:
        json.dump(sets, fh, separators=(",", ":"))
        fh.write("\n")
    for name, q, v, model, cset in rows:
        if not q.endswith("sha256"):
            print(f"{name:20s} {cset:8s} {model:9s} {q} {v}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__)))
