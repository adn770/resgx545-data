#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r9-x's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 f32dfacc8db8, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Per stage (gen/*.py say what each row tests): a row is scored against each frozen model; for a
model the row is held when the kept output equals the model's frozen prediction everywhere it is
determined, FAILED when it differs, cannot tell when the job did not complete or its file is
missing. One SUMMARY line per model (scorekit.headline over the rows that model predicts), gated
by every control of the stage. Reading rows (set `reading`) print their reading only.

REQUIRED: the files each stage's scorer reads (the runner and sessioncheck.py kept check them);
read_files(STAGE, DIR) reads exactly what score() reads; producible(row) is the set of reading
keys a row's job can produce (the freeze refuses a control that reads anything else)."""
import os
import re
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

BASE = (".txt", "cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {"t3": BASE, "srgb": BASE, "zls": BASE + (".depth.1.bin",),
            "zst": BASE + (".depth.1.bin", ".stencil-store.1.bin"), "far": BASE}
GATES = {}          # {stage: the earlier stage whose controls gate it}: none, each stage has its own
ROW = re.compile(r"row (\d+): ([0-9a-fA-Fx ]+)$", re.M)
TRI_COLOUR = 0xFF00FF00


def producible(row):
    a = row["args"].split()
    keys = {"job"} if a[:1] == ["tri"] else set()
    if a[:1] == ["probe"] or "--pixels" in a:
        keys.add("pixels")
    if a[:1] == ["tri"]:
        keys.add("drawn")
    if "--depth" in a:
        keys.add("depth_changed")
    if "--stencil-store" in a:
        keys.add("sst_changed")
    return keys


# ---- reading the kept files -------------------------------------------------------------------
def pixels(text, n):
    rows = {}
    for m in ROW.finditer(text or ""):
        rows[int(m.group(1))] = [int(t, 16) for t in m.group(2).split()]
    if not rows or sorted(rows) != list(range(len(rows))):
        return None
    px = [v for y in sorted(rows) for v in rows[y]]
    return px if len(px) == n else None


def changed(text, name):
    m = re.search(r"^%s #1: (\d+) dwords, (\d+) changed" % re.escape(name), text or "", re.M)
    return int(m.group(2)) if m else None


def drawn(text):
    m = re.search(r"^tri \d+x\d+ #1: (\d+) triangle", text or "", re.M)
    return int(m.group(1)) if m else None


def dwords(d, name):
    b = K._read(os.path.join(d, name))
    return None if b is None or len(b) % 4 else list(struct.unpack("<%dI" % (len(b) // 4), b))


def done(cases, n):
    return n in cases and K.completed(cases[n])


def pred_file(stage, name, model):
    return open(os.path.join(KP, "predictions", stage, f"{name}.{model}.txt")).read()


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for r in K.table(KP, stage):
        n = r["name"]
        if n in cases:
            K.text(d, n + ".txt")
            if stage in ("zls", "zst"):
                dwords(d, n + ".depth.1.bin")
            if stage == "zst":
                dwords(d, n + ".stencil-store.1.bin")


# ---- verdicts ---------------------------------------------------------------------------------
def word(state):
    return "held" if state else "FAILED" if state is False else "cannot tell"


def image_rows(stage, d, n_px):
    """t3, srgb, far: {name: (row, kept image or None)}"""
    cases = K.rows(d, "cases.tsv")
    out = {}
    for r in K.table(KP, stage):
        n = r["name"]
        px = pixels(K.text(d, n + ".txt"), n_px) if done(cases, n) else None
        out[n] = (r, px)
    return out


def score_images(stage, d):
    preds = K.predictions(KP, stage)
    controls, per_model, lines = {}, {}, []
    for n, (r, px) in image_rows(stage, d, 2048).items():
        want = preds.get(n, {})
        res = {}
        for m in want.get("pixels", {}):
            im = [int(v, 16) for v in pred_file(stage, n, m).split()]
            if px is None:
                res[m] = (None, "no image")
                continue
            same = sum(a == b for a, b in zip(px, im))
            ch = sum(((a ^ b) & 0xFFFF == 0) + ((a ^ b) >> 16 == 0) for a, b in zip(px, im))
            res[m] = (same == 2048, f"{same}/2048 pixels, {ch}/4096 halves")
        for m, v in want.get("distinct", {}).items():
            if px is not None:
                ok = len(set(px)) == int(v)
                prev = res.get(m, (True, ""))
                res[m] = (prev[0] and ok, prev[1] + f", {len(set(px))} distinct (frozen {v})")
        desc = "; ".join(f"{m} {t}" for m, (_, t) in res.items())
        if r["set"] == "control":
            st = None if any(s is None for s, _ in res.values()) else all(s for s, _ in res.values())
            controls[n] = st
            lines.append(f"CONTROL {n}: {desc}: "
                         f"{'PASS' if st else 'FAILED' if st is False else 'cannot tell'}")
            continue
        for m, (s, _) in res.items():
            per_model.setdefault(m, []).append(s)
        held = [m for m, (s, _) in res.items() if s]
        lines.append(f"ROW {n} ({r['set']}): {desc}: " + (f"held {', '.join(held)}" if held else
                     "no frozen model exact" if px is not None else "cannot tell"))
    return controls, per_model, lines


def score_far(d):
    preds = K.predictions(KP, "far")
    controls, per_model, lines = {}, {}, []
    for n, (r, px) in image_rows("far", d, 4096).items():
        res = {}
        for m in preds.get(n, {}).get("pixels", {}):
            want = "".join(pred_file("far", n, m).split())
            if px is None:
                res[m] = (None, "no image")
                continue
            got = ["1" if v == TRI_COLOUR else "0" for v in px]
            det = [i for i, c in enumerate(want) if c != "?"]
            bad = sum(got[i] != want[i] for i in det)
            res[m] = (bad == 0, f"{len(det) - bad}/{len(det)} determined pixels "
                                f"({4096 - len(det)} in the band), {got.count('1')} drawn")
        desc = "; ".join(f"{m} {t}" for m, (_, t) in res.items())
        if r["set"] == "control":
            st = None if any(s is None for s, _ in res.values()) else all(s for s, _ in res.values())
            controls[n] = st
            lines.append(f"CONTROL {n}: {desc}: "
                         f"{'PASS' if st else 'FAILED' if st is False else 'cannot tell'}")
            continue
        for m, (s, _) in res.items():
            per_model.setdefault(m, []).append(s)
        held = [m for m, (s, _) in res.items() if s]
        lines.append(f"ROW {n}: {desc}: " + (f"held {', '.join(held)}" if held else
                     "no frozen model" if px is not None else "cannot tell"))
    return controls, per_model, lines


def f32(b):
    return struct.unpack("<f", struct.pack("<I", b))[0]


def round24(z):
    return int(z * 16777215 + 0.5)


def floor24(z):
    return min(int(z * 16777216), 0xFFFFFF)


def q242_models(z0, w, h, g, fmt):
    """{model: {dword index: value}} over the target's pixels (format 1: each dword; format 2:
    each pair of rows), from the format-0 dump z0 of the same geometry (gen/zls.py)."""
    import zls as Z
    tx, ty = Z.tiles(w, h)
    z = {}
    for t_y in range(ty):
        for t_x in range(tx):
            for k in range(512):
                x, y = Z.in_tile_pixel(k)
                z[(32 * t_x + x, 16 * t_y + y)] = f32(z0[512 * (t_y * (g + 1) + t_x) + k])
    out = {}
    if fmt == 1:
        for name, fn in (("H-ROUND", round24), ("H-FLOOR", floor24)):
            out[name] = {512 * ((y >> 4) * (g + 1) + (x >> 5)) + Z.in_tile_index(x, y): fn(z[(x, y)])
                         for y in range(h) for x in range(w)}
        return out
    for lay, slot in (("H-E490", 256), ("H-SLOT512", 512)):
        for val, fn in (("H-ROUND", lambda v: round24(v) >> 8),
                        ("H-FLOOR", lambda v: min(int(v * 65536), 0xFFFF))):
            out[f"{lay}/{val}"] = {
                slot * ((y >> 4) * (g + 1) + (x >> 5)) + Z.in_tile_index16(x, y):
                fn(z[(x, y)]) | fn(z[(x, y + 1)]) << 16
                for y in range(0, h, 2) for x in range(w)}
    return out


def score_zls(stage, d):
    import zls as Z
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    controls, per_model, lines = {}, {}, []
    geo = {stem: (w, h) for stem, w, h, _ in Z.Q242}
    for r in K.table(KP, stage):
        n = r["name"]
        ok = done(cases, n)
        text = K.text(d, n + ".txt") if ok else ""
        want = preds.get(n, {})
        got = {"depth_changed": changed(text, "depth"), "sst_changed": changed(text, "stencil store"),
               "drawn": drawn(text)} if ok else {}
        res = {}
        for q, mv in want.items():
            if q == "dwords":
                stem = n.rsplit("-", 1)[0]
                w, h = geo[stem]
                g = Z.tiles(w, h)[0] - 1
                z0 = dwords(d, stem + "-f0.depth.1.bin") if done(cases, stem + "-f0") else None
                dump = dwords(d, n + ".depth.1.bin") if ok else None
                if z0 is None or dump is None:
                    res.update({m: (None, "no dump") for m in mv})
                    continue
                for m, pred in q242_models(z0, w, h, g, int(n[-1])).items():
                    same = sum(dump[i] == v for i, v in pred.items() if i < len(dump))
                    res[m] = (same == len(pred), f"{same}/{len(pred)} dwords")
                continue
            v = got.get(q)
            for m, frozen in mv.items():
                res[f"{m}:{q}"] = (None if v is None else v == int(frozen), f"{q} {v} (frozen {frozen})")
        if not want:
            lines.append(f"READ {n}: " + ", ".join(f"{k} {v}" for k, v in got.items()))
            continue
        desc = "; ".join(f"{m} {t}" for m, (_, t) in res.items())
        if r["set"] == "control":
            st = None if any(s is None for s, _ in res.values()) else all(s for s, _ in res.values())
            controls[n] = st
            lines.append(f"CONTROL {n}: {desc}: "
                         f"{'PASS' if st else 'FAILED' if st is False else 'cannot tell'}")
            continue
        for m, (s, _) in res.items():
            per_model.setdefault(m.split(":")[0], []).append(s)
        held = [m for m, (s, _) in res.items() if s]
        lines.append(f"ROW {n}: {desc}: " + (f"held {', '.join(held)}" if held else
                     "no frozen model" if ok else "cannot tell"))
    return controls, per_model, lines


def verdicts(stage, d):
    if stage in ("t3", "srgb"):
        return score_images(stage, d)
    if stage == "far":
        return score_far(d)
    return score_zls(stage, d)


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        dep = GATES.get(argv[2])
        if dep is None:
            return 0
        for root in argv[3:]:
            dd = os.path.join(root, dep)
            if os.path.isdir(dd):
                g = SK.gate(verdicts(dep, dd)[0])
                print(f"gate {argv[2]} on {dep}: {'open' if g.ok else '; '.join(g.problems)}")
                return 0 if g.ok else 1
        print(f"gate {argv[2]}: {dep} has not run")
        return 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, per_model, lines = verdicts(argv[1], argv[2])
        print("\n".join(lines))
        for m, states in sorted(per_model.items()):
            print("SUMMARY: " + argv[1] + ": " + SK.headline(m, controls, states))
        if not per_model:
            print("SUMMARY: " + argv[1] + ": " + SK.headline("no model", controls, []))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
