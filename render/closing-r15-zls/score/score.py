#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r15-zls's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 158bdc5455b2, pinned in FROZEN.commits);
the kept records it compares with are read at the frozen data commit (gen/pins.py).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL and READING lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage gates another)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Rows are grouped in stages by the dump their scorer reads (gen/z15.py STAGE_ROWS); a model's
headline is gated by the controls of its own rows' form (GATED_BY), the stage's otherwise.
A zpass row holds a model when the depth store's dwords over the target's tiles are the model's
(gen/z15.pass_predict), every other dword keeps the store's fill and the drawn count is the
model's. A zbits3 row when the stencil store's bytes over the tiles are the model's
(z15.stencil_predict; H23-LOADED's map fitted here on E1042's kept zb2-b23), the rest keeps the
fill, and the drawn count is the model's. A zflat2 row by z15.rec0_check against E1031's kept
block (H-FLATPLANE from the twin's floats). A zovl overlap row when every dword the model
predicts from the kept full-pitch reference is equal and no other dword changed; an integer row
when its whole store is the model's word; a sized row when the pages holding changed dwords are
the model's, each page's dwords and value the model's. Controls: each its frozen reading and,
where it replicates a kept job, that job's dump byte for byte.

REQUIRED: the files the scorer reads (every row of a stage writes its stage's dump);
read_files(STAGE, DIR) reads exactly what verdicts() reads; producible(row) is the set of
reading keys a row's job can produce."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402
import z15 as Z  # noqa: E402

FIXED = ("cases.tsv", "void.tsv", "readings.tsv")

REQUIRED = {
    "zpass": (".txt", ".depth-store.1.bin") + FIXED,
    "zbits3": (".txt", ".stencil-store.1.bin") + FIXED,
    "zflat2": (".txt", ".depth.1.bin") + FIXED,
    "zovl": (".txt", ".depth.1.bin") + FIXED,
}
GATES = {}
R10X = "render/closing-r10-x/out/20261113-101116/"
R10Z = "render/closing-r10-zls/out/20261113-102039/zst2/"
R13Z = "render/closing-r13-zls/out/20261113-213117/"
R14Z = "render/closing-r14-zls/out/20261114-054846/"
KEPT = {
    "zp-c-id": "data:" + R13Z + "zbase/zb-c-id.depth-store.1.bin.gz",        # E1029
    "zb3-c-base": "data:" + R14Z + "zbits2/zb2-c-base.stencil-store.1.bin.gz",  # E1042
    "zb3-c-set": "data:" + R14Z + "zbits2/zb2-c-set.stencil-store.1.bin.gz",    # E1042
    "zb3-c-b23": "data:" + R14Z + "zbits2/zb2-b23.stencil-store.1.bin.gz",      # E1042
    "zb2-b23-txt": "data:" + R14Z + "zbits2/zb2-b23.txt.gz",                    # E1042
    "zl2-c-flat": "data:" + R13Z + "zfmt/zf-flat-f6.depth.1.bin.gz",          # E1031
    "zl2-c-y6": "data:" + R10Z + "z2y-f6.depth.1.bin.gz",                     # E986
    "zl2-c-f5": "data:" + R14Z + "zflat/zl-f5-flat.depth.1.bin.gz",           # E1043
    "zv-c-ov": "data:" + R10X + "zov/zov-64x32-g0.depth.1.bin.gz",            # E996
    "zv-c-g3": "data:" + R14Z + "zodd/zo-g3.depth.1.bin.gz",                  # E1041
    "zov-64x32-ctl": "data:" + R10X + "zov/zov-64x32-ctl.depth.1.bin.gz",     # E996
    "zov-160x48-ctl": "data:" + R10X + "zov/zov-160x48-ctl.depth.1.bin.gz",   # E996
    "zo-65-f0": "data:" + R14Z + "zodd/zo-65-f0.depth.1.bin.gz",              # E1041
    "zo-640-f0": "data:" + R14Z + "zodd/zo-640-f0.depth.1.bin.gz",            # E1041
}


def producible(row):
    a = row["args"].split()
    keys = {"job", "drawn"} if a[:1] == ["tri"] else set()
    if "--pixels" in a:
        keys.add("pixels")
    if "--depth" in a:
        keys.add("depth_changed")
    if "--depth-store" in a:
        keys.add("dst_changed")
    if "--stencil-store" in a:
        keys.add("sst_changed")
    return keys


def drawn_count(text):
    m = re.search(r"^tri \d+x\d+ #1: (\d+) triangle", text or "", re.M)
    return int(m.group(1)) if m else None


def changed(text, what):
    m = re.search(r"^%s #1: \d+ dwords, (\d+) changed" % what, text or "", re.M)
    return int(m.group(1)) if m else None


def drawn_set(text):
    """the pixels of the `row Y:` lines in the triangle's colour, or None"""
    out, seen = set(), False
    for ln in (text or "").splitlines():
        if ln.startswith("row "):
            k, _, vals = ln[4:].partition(": ")
            if k.isdigit():
                seen = True
                for x, v in enumerate(vals.split()):
                    if int(v, 16) == Z.TRI_COLOUR:
                        out.add((x, int(k)))
    return out if seen else None


def kept(key):
    import pins
    return pins.blob(KEPT[key])


def g23_map():
    """H23-LOADED's map: on E1042's kept zb2-b23 (bytes fill, 64 x 32 G 1), the loaded byte ->
    the byte the test read (the stored one, XOR 0xff where the pixel drew); None where it is
    not a function"""
    st = kept("zb3-c-b23")
    dr = drawn_set(kept("zb2-b23-txt").decode())
    m = {}
    for y in range(32):
        for x in range(64):
            p = Z.st_pos(x, y)
            r = st[p] ^ (0xFF if (x, y) in dr else 0)
            if m.setdefault(Z.fill_byte("bytes", p), r) != r:
                return None
    return m


def _st(s):
    return "PASS" if s else "FAILED" if s is False else "cannot tell"


class Run:
    def __init__(self, stage, d):
        self.d = d
        self.cases = K.rows(d, "cases.tsv")
        K.rows(d, "void.tsv")
        K.rows(d, "readings.tsv")
        self.preds = K.predictions(KP, stage)
        self.table = K.table(KP, stage)
        self.seen = {}

    def done(self, n):
        return n in self.cases and K.completed(self.cases[n])

    def text(self, n):
        return K.text(self.d, n + ".txt") if self.done(n) else None

    def dump(self, n, suffix):
        if (n, suffix) not in self.seen:
            self.seen[(n, suffix)] = (K._read(os.path.join(self.d, n + suffix))
                                      if self.done(n) else None)
        return self.seen[(n, suffix)]


def _row(lines, per_model, n, res):
    for m, (s, _) in res.items():
        per_model.setdefault(m, []).append(s)
    held = [m for m, (s, _) in res.items() if s]
    lines.append(f"ROW {n}: " + "; ".join(f"{m} {t}" for m, (_, t) in res.items()) + ": "
                 + (f"held {', '.join(held)}" if held else
                    "cannot tell" if any(s is None for s, _ in res.values()) else
                    "no frozen model"))


def _dict_fit(dw, pred, rest):
    """(held, text) of a {index: value} prediction: equal there, `rest(i, v)` true elsewhere"""
    hit = sum(1 for i, v in pred.items() if i < len(dw) and dw[i] == v)
    other = sum(1 for i, v in enumerate(dw) if i not in pred and not rest(i, v))
    return hit == len(pred) and not other, f"{hit}/{len(pred)}{f', {other} other' if other else ''}"


def fill_ok(i, v):
    return v == Z.FILL_DEAD


def sfill_ok(i, v):
    return v == (Z.FILL_DEAD >> (8 * (i % 4)) & 0xFF)


def pass_fit(r, n, m):
    st = Z.dwords(r.dump(n, ".depth-store.1.bin"))
    dc = drawn_count(r.text(n))
    if st is None or dc is None:
        return None, "no dump or count"
    pred, drawn = Z.pass_predict(n, m)
    s, t = _dict_fit(st, pred, fill_ok)
    return s and dc == drawn, f"{t}, drawn {dc}/{drawn}"


def stencil_fit(r, n, m, g23):
    st = r.dump(n, ".stencil-store.1.bin")
    dc = drawn_count(r.text(n))
    if st is None or dc is None:
        return None, "no dump or count"
    if m == "H23-LOADED" and g23 is None:
        return None, "no map"
    pred, drawn, _ = Z.stencil_predict(n, m, g23=g23)
    s, t = _dict_fit(st, pred, sfill_ok)
    return s and dc == drawn, f"{t}, drawn {dc}/{drawn}"


def _control(r, n, lines):
    txt = r.text(n)
    if n in Z.ZP_CONTROL:
        b = r.dump(n, ".depth-store.1.bin")
        if n == "zp-c-id":
            same = None if b is None else b == kept(n)
            s = None if changed(txt, "depth store") is None else same
            lines.append(f"CONTROL {n}: store byte for byte E1029's kept zb-c-id: {same}: {_st(s)}")
        else:
            s, t = pass_fit(r, n, "H-EDGE")
            lines.append(f"CONTROL {n}: store and drawn by the whole-tile pass ({t}): {_st(s)}")
    elif n in Z.ZB3_CONTROL:
        got = drawn_count(txt)
        fz = Z.ZB3_CONTROL[n][1]
        st = r.dump(n, ".stencil-store.1.bin")
        if n == "zb3-c-ref1":
            pred, drawn, _ = Z.stencil_predict(n, "E988")
            same = None if st is None else _dict_fit(st, pred, sfill_ok)[0]
        else:
            same = None if st is None else st == kept(n)
        s = None if got is None or same is None else (got == fz and same)
        lines.append(f"CONTROL {n}: drawn {got} (frozen {fz}); stencil store "
                     f"{'E988 against reference 1' if n == 'zb3-c-ref1' else 'byte for byte the kept'}"
                     f": {same}: {_st(s)}")
    else:
        b = r.dump(n, ".depth.1.bin")
        got = changed(txt, "depth")
        fz = {**Z.ZL2_CHANGED, **Z.ZV_CONTROL}[n]
        if n == "zv-c-075":
            dw = Z.dwords(b)
            same = None if dw is None else all(v == Z.ZV_C075 for v in dw[:2048]) and all(
                v == Z.FILL_DEAD for v in dw[2048:])
            how = f"all 2048 {Z.ZV_C075:#010x}"
        else:
            same = None if b is None else b == kept(n)
            how = "byte for byte the kept record's"
        s = None if got is None or same is None else (got == fz and same)
        lines.append(f"CONTROL {n}: depth_changed {got} (frozen {fz}); {how}: {same}: {_st(s)}")
    return s


def _zpass(r, n, lines):
    res = {m: pass_fit(r, n, m) for m in Z.ZPASS[n][8]}
    st = Z.dwords(r.dump(n, ".depth-store.1.bin"))
    if st is not None:
        vals = sorted({v for v in st if v != Z.FILL_DEAD})
        lines.append(f"READING {n}: drawn {drawn_count(r.text(n))}; store values "
                     f"{[f'{v:#010x}' for v in vals[:8]]}{' ...' if len(vals) > 8 else ''}")
    return res


def _zbits3(r, n, lines, g23):
    res = {m: stencil_fit(r, n, m, g23) for m in Z.ZBITS3[n][6]}
    st = r.dump(n, ".stencil-store.1.bin")
    dr = drawn_set(r.text(n))
    if st is not None and dr is not None:
        w, h, ctl = Z.ZBITS3[n][:3]
        g = Z.ctl_g(ctl)
        cols = {}
        for y in range(h):
            for x in range(w):
                cols.setdefault(x % 16, set()).add(st[Z.st_pos(x, y, g)] ^ (0xFF if (x, y) in dr else 0))
        lines.append(f"READING {n}: drawn {len(dr)}; the read byte by x mod 16 "
                     + " ".join(f"{c}:{','.join(f'{v:#x}' for v in sorted(vs)[:3])}"
                                f"{'+' if len(vs) > 3 else ''}" for c, vs in sorted(cols.items())))
    return res


def twin_value(r, k):
    dw = Z.dwords(r.dump(f"zl2-f0-{k}", ".depth.1.bin"))
    if dw is None:
        return None, None
    vals = {v for v in dw[:2048]}
    return (vals.pop() if len(vals) == 1 else False), len(set(dw[:2048]))


def _zflat2(r, n, lines, ref176):
    b = r.dump(n, ".depth.1.bin")
    v_any = Z.rec0_any(b, ref176)
    res = {}
    if n in Z.REC0_DEPTHS:
        res["FL-REC0"] = Z.rec0_check(b, ref176, Z.f32_bits(Z.REC0_DEPTHS[n]))
    else:
        k = n.split("-")[-1]
        v = Z.f32_bits(Z.flat_depth(n))
        if b is None:
            res = {m: (None, "no dump") for m in Z.FLAT_MODELS}
        else:
            res["H-LOW16"] = (Z.rec0_check(b, ref176, v) if v & 0xFFFF == 0 else
                              (v_any is None, f"not FL-REC0: {v_any is None}"))
            u, nd = twin_value(r, k)
            if u is None:
                res["H-FLATPLANE"] = (None, "no twin")
            elif u is False:
                res["H-FLATPLANE"] = (v_any is None, f"twin {nd} values; not FL-REC0: {v_any is None}")
            else:
                s, t = Z.rec0_check(b, ref176, u)
                res["H-FLATPLANE"] = (s, f"twin one value {u:#010x}; {t}")
    if b is not None:
        dw = Z.dwords(b)
        per = [sum(1 for x in dw[512 * k:512 * k + 512] if x != Z.FILL_DEAD) for k in range(4)]
        lines.append(f"READING {n}: FL-REC0 of v {'none' if v_any is None else f'{v_any:#010x}'}; "
                     f"changed per block {per}; block 0 bytes {b[:4 * max(per[0], 1)].hex()[:400]}")
    return res


def _zovl(r, n, lines):
    txt = r.text(n)
    dw = Z.dwords(r.dump(n, ".depth.1.bin"))
    res = {}
    if n in Z.OV_ROWS:
        w, h, g, fmt, ref, gref = Z.OV_ROWS[n]
        full = Z.dwords(kept(ref))
        for m in Z.OV_MODELS:
            res[m] = (None, "no dump") if dw is None else _dict_fit(
                dw, Z.ov_predict(full, w, h, g, fmt, gref, m), fill_ok)
    elif n in Z.INT_OUT:
        for m in Z.INT_OUT_MODELS:
            res[m] = (None, "no dump") if dw is None else _dict_fit(
                dw, Z.int_out_predict(n, m), fill_ok)
        if dw is not None:
            lines.append(f"READING {n}: values {sorted({f'{v:#010x}' for v in dw if v != Z.FILL_DEAD})[:6]}")
    else:
        ok = dw is not None and g_addresses_ok(txt, Z.G_CTLS[n][1])
        pages = {} if not ok else {
            p: [v for v in dw[1024 * p:1024 * p + 1024] if v != Z.FILL_DEAD]
            for p in range(len(dw) // 1024)}
        got = {p: (len(v), v[0]) for p, v in pages.items() if v and len(set(v)) == 1}
        mixed = sorted(p for p, v in pages.items() if len(set(v)) > 1)
        ms = Z.B25_MODELS if n == "zv-b25" else Z.G_MODELS
        for m in ms:
            want = Z.g_pages(n, m)
            res[m] = (None, "no dump or other addresses") if not ok else (
                got == want and not mixed, f"pages {sorted(got)}{f', mixed {mixed}' if mixed else ''}")
        if ok:
            lines.append(f"READING {n}: changed per page "
                         f"{[(p, len(v)) for p, v in pages.items() if v]}; values "
                         f"{sorted({f'{x:#x}' for v in pages.values() for x in v})[:4]}")
    return res


def g_addresses_ok(text, pages):
    t = text or ""
    return (f"depth: 0x3e001000 {pages} pages," in t and "base 0x3e000000," in t
            and f"rd:13={Z.RD13:#x}" in t)


# the controls that gate a model's headline: those of its rows' own form, in the stage
GATED_BY = {**{m: ("zv-c-ov",) for m in Z.OV_MODELS},
            **{m: ("zv-c-075",) for m in Z.INT_OUT_MODELS},
            **{m: ("zv-c-g3",) for m in Z.G_MODELS + Z.B25_MODELS}}


def stage_verdicts(r, stage):
    controls, per_model, lines = {}, {}, []
    g23 = g23_map() if stage == "zbits3" else None
    ref176 = kept("zl2-c-flat")[:176] if stage == "zflat2" else None
    for row in r.table:
        n = row["name"]
        if row["set"] == "control":
            controls[n] = _control(r, n, lines)
            continue
        if row["set"] == "reading":
            dw = Z.dwords(r.dump(n, ".depth.1.bin"))
            ch = None if dw is None else set(dw[:2048])
            lines.append(f"READING {n}: depth_changed {changed(r.text(n), 'depth')}; distinct "
                         f"{None if ch is None else len(ch)}"
                         + (f" ({next(iter(ch)):#010x})" if ch and len(ch) == 1 else ""))
            continue
        if stage == "zpass":
            res = _zpass(r, n, lines)
        elif stage == "zbits3":
            res = _zbits3(r, n, lines, g23)
        elif stage == "zflat2":
            res = _zflat2(r, n, lines, ref176)
        else:
            res = _zovl(r, n, lines)
        _row(lines, per_model, n, res)
    return controls, per_model, lines


def gating(stage, controls, model):
    want = GATED_BY.get(model)
    if stage == "zbits3" and model in Z.EDGE_MODELS:
        want = ("zb3-c-base",)
    return controls if want is None else {c: s for c, s in controls.items() if c in want}


def verdicts(stage, d, roots=None):
    return stage_verdicts(Run(stage, d), stage)


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
            h = SK.headline(m, gating(argv[1], controls, m), states)
            print("SUMMARY: " + argv[1] + ": " + (h if h.startswith(m) else f"{m}: {h}"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
