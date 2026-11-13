#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r10-x's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 dd2912899299, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Per stage (gen/z.py and gen/probes.py say what each row tests): a row is scored against each
frozen model; for a model the row is held when the kept output equals every quantity the model
freezes (a drawn count, a target hash, a dump's sha256, a `depth store #1:` line, the dwords a rule
gives, an image), FAILED when one differs, cannot tell when the job did not complete or a file is
missing. A control passes when its one model holds. One SUMMARY line per model
(scorekit.headline over the rows that model predicts), gated by every control of the stage.

REQUIRED: the files each stage's scorer reads (the runner and sessioncheck.py kept check them);
read_files(STAGE, DIR) reads exactly what score() reads; producible(row) is the set of reading
keys a row's job can produce (the freeze refuses a control that reads anything else)."""
import hashlib
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
DUMP = ".depth.1.bin"
REQUIRED = {"dcmp": BASE, "zov": BASE + (DUMP,), "zbits": BASE + (DUMP,),
            "isp0x": BASE + (DUMP,), "sb": BASE, "win0": BASE}
GATES = {}          # {stage: the earlier stage whose controls gate it}: none, each stage has its own
ROW = re.compile(r"(?:^|: )row (\d+): ([0-9a-fA-Fx ]+)$", re.M)


def producible(row):
    a = row["args"].split()
    keys = set()
    if a[:1] == ["tri"]:
        keys |= {"job", "drawn"}
        if "--depth" in a:
            keys.add("depth_changed")
    if a[:1] == ["probe"] or "--pixels" in a:
        keys.add("pixels")
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


def first(text, pattern):
    m = re.search(pattern, text or "", re.M)
    return m.group(1) if m else None


def tri_reading(text):
    d = first(text, r"^tri \d+x\d+ #1: (\d+) triangle")
    z = first(text, r"^depth #1: \d+ dwords, (\d+) changed")
    return {"drawn": None if d is None else int(d),
            "depth_changed": None if z is None else int(z),
            "hash": first(text, r"^target: \d+x\d+ hash (0x[0-9a-f]+)"),
            "store_line": first(text, r"^(depth store #1: .*)$")}


def dump(d, name):
    b = K._read(os.path.join(d, name))
    return None if b is None or len(b) % 4 else b


def words(b):
    return None if b is None else list(struct.unpack("<%dI" % (len(b) // 4), b))


def done(cases, n):
    return n in cases and K.completed(cases[n]) is True


def size_of(args):
    a = args.split()
    return int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for r in K.table(KP, stage):
        n = r["name"]
        if n in cases:
            K.text(d, n + ".txt")
            if DUMP in REQUIRED[stage]:
                dump(d, n + DUMP)


# ---- verdicts ---------------------------------------------------------------------------------
def verdict_word(st):
    return "PASS" if st else "FAILED" if st is False else "cannot tell"


def collect(stage, d, check):
    """check(row, ok, want) -> {model: (state, text)} per row; the CONTROL / ROW lines."""
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    controls, per_model, lines = {}, {}, []
    for r in K.table(KP, stage):
        n = r["name"]
        ok = done(cases, n)
        res = check(r, ok, preds.get(n, {}))
        desc = "; ".join(f"{m} {t}" for m, (_, t) in res.items())
        if r["set"] == "control":
            st = None if not res or any(s is None for s, _ in res.values()) else \
                all(s for s, _ in res.values())
            controls[n] = st
            lines.append(f"CONTROL {n}: {desc}: {verdict_word(st)}")
            continue
        for m, (s, _) in res.items():
            per_model.setdefault(m, []).append(s)
        held = [m for m, (s, _) in res.items() if s]
        lines.append(f"ROW {n} ({r['set']}): {desc}: " + (
            f"held {', '.join(held)}" if held else "no frozen model held" if ok else "cannot tell"))
    return controls, per_model, lines


def by_model(want):
    """{model: {quantity: value}} from predictions' {quantity: {model: value}}."""
    out = {}
    for q, mv in want.items():
        for m, v in mv.items():
            out.setdefault(m, {})[q] = v
    return out


def check_tri(d):
    def check(r, ok, want):
        n = r["name"]
        text = K.text(d, n + ".txt") if ok else ""
        got = tri_reading(text) if ok else {}
        b = dump(d, n + DUMP) if ok and "depth.1.bin" in want else None
        res = {}
        for m, q in by_model(want).items():
            st, parts = True, []
            for k, v in q.items():
                if k == "depth.1.bin":
                    g = None if b is None else "sha256:" + hashlib.sha256(b).hexdigest()
                    parts.append("dump " + ("missing" if g is None else "equal" if g == v else
                                            "differs (%s)" % (got.get("depth_changed"),)))
                elif k in ("drawn", "depth_changed"):
                    g = got.get(k)
                    parts.append(f"{k} {g} (frozen {v})")
                    v = int(v)
                else:
                    g = got.get(k)
                    parts.append(f"{k} {'equal' if g == v else g}")
                if g is None:
                    st = None if st is not False else False
                elif g != v:
                    st = False
            res[m] = (st if ok else None, ", ".join(parts) if ok else "not completed")
        return res
    return check


def check_zov(d):
    import z as Z
    geo = {f"zov-{w}x{h}-ctl": (w, h) for w, h, _ in Z.ZOV}
    cases = K.rows(d, "cases.tsv")

    def check(r, ok, want):
        n = r["name"]
        res = {}
        if r["set"] == "control":
            got = tri_reading(K.text(d, n + ".txt")) if ok else {}
            w, h = geo[n]
            tx, ty = Z.tiles(w, h)
            dw = words(dump(d, n + DUMP)) if ok else None
            nd = None if dw is None else len(set(dw[:512 * tx * ty]))
            for m, q in by_model(want).items():
                parts, st = [], True
                for k, v in q.items():
                    g = got.get(k) if k == "depth_changed" else nd
                    parts.append(f"{k} {g} (frozen {v})")
                    st = None if g is None else st and g == int(v)
                res[m] = (st if ok else None, ", ".join(parts) if ok else "not completed")
            return res
        ctl = next(iter(want["dwords"].values()))[5:]
        w, h = geo[ctl]
        g = int(n.split("-g")[1].split("-")[0])
        fmt = 1 if n.endswith("-f1") else 0
        full = words(dump(d, ctl + DUMP)) if done(cases, ctl) else None
        dw = words(dump(d, n + DUMP)) if ok else None
        for m in want["dwords"]:
            if full is None or dw is None:
                res[m] = (None, "no dump")
                continue
            pred = Z.zov_predict(full, w, h, g, m, fmt)
            same = sum(i < len(dw) and dw[i] == v for i, v in pred.items())
            res[m] = (same == len(pred), f"{same}/{len(pred)} dwords")
        return res
    return check


def check_images(stage, d):
    def check(r, ok, want):
        n = r["name"]
        w, h = (64, 64) if "--width" not in r["args"] else size_of(r["args"])
        px = pixels(K.text(d, n + ".txt"), w * h) if ok else None
        res = {}
        for m in want.get("pixels", {}):
            im = [int(v, 16) for v in open(os.path.join(KP, "predictions", stage,
                                                        f"{n}.{m}.txt")).read().split()]
            if px is None:
                res[m] = (None, "no image")
                continue
            same = sum(a == b for a, b in zip(px, im))
            res[m] = (same == w * h, f"{same}/{w * h} pixels")
        return res
    return check


def verdicts(stage, d):
    if stage in ("sb", "win0"):
        return collect(stage, d, check_images(stage, d))
    if stage == "zov":
        return collect(stage, d, check_zov(d))
    return collect(stage, d, check_tri(d))


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
