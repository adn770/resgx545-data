#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r10-st1's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 287031c64102, pinned in FROZEN.commits).

  score.py st1 KEPT_DIR [ROOTS...]   ROW, CONTROL and READING lines, then SUMMARY lines (exit 0)
  score.py gate st1 ROOTS...         exit 0 (no stage gates st1)
  score.py premise st1 KEPT_DIR      STOP lines and exit 1 when a control has no reading

A control passes at its frozen drawn count (`tri WxH #1: N triangle`). A held-out row is scored
per frozen model (gen/st1.py) on two quantities: the image (the set of pixels of the triangle
colour in the `row N:` lines equals the model's drawn set) and the stencil store (every byte the
model predicts, the target's pixels, equals the kept dump's); a model holds on a row when both
do. q071 rows: H-INERT, the image and the whole stencil-store dump equal to their base row's. A row
whose job (or base row) did not complete, or kept no image or dump, cannot tell.

REQUIRED: the files the scorer reads; read_files(STAGE, DIR) reads exactly what verdicts() reads;
producible(row) is the set of reading keys a row's job can produce."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

REQUIRED = {"st1": (".txt", "cases.tsv", "void.tsv", "readings.tsv", ".stencil-store.1.bin")}
GATES = {}


def producible(row):
    a = row["args"].split()
    keys = {"job", "drawn"} if a[:1] == ["tri"] else set()
    if "--pixels" in a:
        keys.add("pixels")
    if "--depth" in a:
        keys.add("depth_changed")
    if "--stencil-store" in a:
        keys.add("sst_changed")
    return keys


def drawn_count(text):
    m = re.search(r"^tri \d+x\d+ #1: (\d+) triangle", text or "", re.M)
    return int(m.group(1)) if m else None


def _st(s):
    return "PASS" if s else "FAILED" if s is False else "cannot tell"


def verdicts(stage, d, roots=None):
    import st1 as S
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    done = lambda n: n in cases and K.completed(cases[n])  # noqa: E731
    controls, per_model, lines = {}, {}, []
    seen = {}

    def got(n):
        if n not in seen:
            w, h = S.ROWS[n][:2]
            txt = K.text(d, n + ".txt") if done(n) else None
            sst = K._read(os.path.join(d, n + ".stencil-store.1.bin")) if done(n) else None
            seen[n] = (None if txt is None else S.pixels_drawn(txt, w, h), sst, txt)
        return seen[n]

    for r in K.table(KP, stage):
        n = r["name"]
        want = preds.get(n, {})
        img, sst, txt = got(n)
        if r["set"] == "control":
            dc = drawn_count(txt)
            fz = int(want["drawn"]["H-E284"])
            st = None if dc is None else dc == fz
            controls[n] = st
            lines.append(f"CONTROL {n}: drawn {dc} (frozen {fz}); image pixels "
                         f"{None if img is None else len(img)}: {_st(st)}")
            continue
        res = {}
        for m in want.get("image", {}):
            if "same:" in want["image"][m]:
                base = want["image"][m].split(":", 1)[1]
                bimg, bsst, _ = got(base)
                if None in (img, sst, bimg, bsst):
                    res[m] = (None, "no image or dump (or its base's)")
                else:
                    res[m] = (img == bimg and sst == bsst,
                              f"image {'=' if img == bimg else '!='} {base}'s, store "
                              f"{'=' if sst == bsst else '!='}")
                continue
            if img is None or sst is None:
                res[m] = (None, "no image or dump")
                continue
            pd, ps = S.predict(n, m)
            sok = sum(1 for o, v in ps.items() if o < len(sst) and sst[o] == v)
            res[m] = (img == pd and sok == len(ps),
                      f"image {len(img & pd)}/{len(pd)} drawn, {len(img - pd)} extra; store "
                      f"{sok}/{len(ps)} bytes")
        for m, (s, _) in res.items():
            per_model.setdefault(m, []).append(s)
        held = [m for m, (s, _) in res.items() if s]
        lines.append(f"ROW {n}: " + "; ".join(f"{m} {t}" for m, (_, t) in res.items()) + ": "
                     + (f"held {', '.join(held)}" if held else
                        "cannot tell" if any(s is None for s, _ in res.values()) else
                        "no frozen model"))
    return controls, per_model, lines


def read_files(stage, d):
    verdicts(stage, d)


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, per_model, lines = verdicts(argv[1], argv[2], argv[3:])
        print("\n".join(lines))
        for m, states in sorted(per_model.items()):
            print("SUMMARY: " + argv[1] + ": " + SK.headline(m, controls, states))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
