#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r16-zls's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 b2b5288c82ed, pinned in FROZEN.commits);
the kept records it compares with are read at the frozen data commit (gen/pins.py, z16.KEPT).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL and READING lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage gates another)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Rows are grouped in stages by the dump their scorer reads (gen/z16.py STAGE_ROWS); a model's
headline is gated by the controls of its own rows' form (GATED_BY), the stage's otherwise.
zpass2: a pass row holds a model when the store's 2048 tile dwords are the model's
(z16.pass_predict: H-PASS-TWIN from the twin row's kept store, the next row), the rest keeps the
store's fill, and the drawn count is the model's; the 0.125 pair's verdict is printed on its twin
(zp2-t-z125), the pass being the control zp2-c-z125. zbits4: bit 0 and bit 20 rows by their dumps
against the kept twin's (or the fill), bit 23's rows by the byte the test read (the stored byte,
XOR 0xff where the pixel drew), the stencil overlap rows by z16.ovs_predict. zovp: the overlap
rows by z16.ovp_predict on the kept full-pitch reference, the NaN rows by their word at every
dword, bit 20's d12 row by its kept twin. zoff: z16.zoff_fit outside BEND, and the drawn count.
Controls: each its frozen reading and the kept dumps (or the rule) byte for byte.

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
import z16 as Z  # noqa: E402

FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
DST, DEP, SST = ".depth-store.1.bin", ".depth.1.bin", ".stencil-store.1.bin"
REQUIRED = {
    "zpass2": (".txt", DST) + FIXED,
    "zbits4": (".txt", DEP, SST) + FIXED,
    "zovp": (".txt", DST) + FIXED,
    "zoff": (".txt", DEP) + FIXED,
}
GATES = {}


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


def _fit_drawn(fit, dc, want):
    s, t = fit
    return (None, "no count") if dc is None else (s and dc == want, f"{t}, drawn {dc}/{want}")


# ---- zpass2 ----------------------------------------------------------------------------------
def pass_fit(st, dc, k, m, twin):
    if st is None or dc is None:
        return None, "no dump or count"
    if m == "H-PASS-TWIN" and twin is None:
        return None, "no twin"
    pred, drawn = Z.pass_predict(k, "H-PASS-TWIN" if m == "H-PASS-TWIN" else "H-PASS-OWN", twin)
    return _fit_drawn(_dict_fit(st, pred, fill_ok), dc, drawn)


def _zpass2(r, n, lines):
    k = n[6:]
    pn = Z.pass_name(k)
    twin = Z.dwords(r.dump(f"zp2-t-{k}", DST))
    st, dc = Z.dwords(r.dump(pn, DST)), drawn_count(r.text(pn))
    ms = Z.PASS_MODELS + (("H-PASS-EXACT",) if k in Z.ONE_FLOAT else ())
    if twin is not None:
        vals = sorted(set(twin[:2048]))
        lines.append(f"READING zp2-t-{k}: drawn {drawn_count(r.text(f'zp2-t-{k}'))}; "
                     f"{len(vals)} values {[f'{v:#010x}' for v in vals[:9]]}"
                     f"{' ...' if len(vals) > 9 else ''}")
    return {m: pass_fit(st, dc, k, m, twin) for m in ms}


# ---- zbits4 ----------------------------------------------------------------------------------
def kept(key):
    return Z.kept(key)


def _same_kept(r, n, twin):
    """(dep equal, sst equal) to the kept twin's, None where a dump is missing"""
    d, s = r.dump(n, DEP), r.dump(n, SST)
    return (None if d is None else d == kept(twin + ".dep"),
            None if s is None else s == kept(twin + ".sst"))


def _b0(r, n):
    twin = Z.ZB4_TWIN[n]
    dc = drawn_count(r.text(n))
    sd, ss = _same_kept(r, n, twin)
    d, s = r.dump(n, DEP), r.dump(n, SST)
    fill = Z.depth_fill_of(Z.ARGS[n])
    res = {}
    if None in (sd, ss, dc):
        return {m: (None, "no dump or count") for m in Z.B0_MODELS}
    res["H-B0"] = (sd and ss and dc == 0, f"depth {sd}, stencil {ss} as {twin}; drawn {dc}/0")
    dfill = all(v == fill for v in Z.dwords(d))
    sfill = all(sfill_ok(i, v) for i, v in enumerate(s))
    res["H-B0-NOSTORE"] = (dfill and sfill and dc == 0,
                           f"depth fill {dfill}, stencil fill {sfill}; drawn {dc}/0")
    return res


def _inert20(r, n, suffixes):
    twin = Z.ZB4_TWIN[n]
    dc = drawn_count(r.text(n))
    want = Z.kept_drawn(twin)
    eq = {}
    for suf, key in suffixes:
        b = r.dump(n, suf)
        eq[key] = None if b is None else b == kept(twin + "." + key)
    if dc is None or None in eq.values():
        return {"H-INERT20": (None, "no dump or count")}
    return {"H-INERT20": (all(eq.values()) and dc == want,
                          f"{', '.join(f'{k} {v}' for k, v in eq.items())} as {twin}; drawn {dc}/{want}")}


def read_bytes(r, n, w=64, h=32, g=1):
    """{(x, y): the byte the test read}, or None"""
    st, dr = r.dump(n, SST), drawn_set(r.text(n))
    if st is None or dr is None:
        return None
    return {(x, y): st[Z.st_pos(x, y, g)] ^ (0xFF if (x, y) in dr else 0)
            for y in range(h) for x in range(w)}


def _b23(r, n, lines):
    rb = read_bytes(r, n)
    st, dc = r.dump(n, SST), drawn_count(r.text(n))
    res = {}
    for m in Z.B23_MODELS:
        p = Z.b23_predict(n, m)
        if rb is None or dc is None:
            res[m] = (None, "no dump or pixels")
        elif p is None:
            off = sum(1 for (x, y), v in rb.items() if v != Z.COL23[x % 16])
            res[m] = (off > 0, f"{off} read bytes not COL23")
        else:
            res[m] = _fit_drawn(_dict_fit(st, p[0], sfill_ok), dc, p[1])
    if rb is not None:
        cols = {}
        for (x, y), v in rb.items():
            cols.setdefault(x % 16, set()).add(v)
        lines.append(f"READING {n}: drawn {dc}; the read byte by x mod 16 "
                     + " ".join(f"{c}:{','.join(f'{v:#x}' for v in sorted(vs)[:3])}"
                                f"{'+' if len(vs) > 3 else ''}" for c, vs in sorted(cols.items())))
    return res


def _ovs(r, n):
    w, h, g = Z.OVS_ROWS[n]
    st, dc = r.dump(n, SST), drawn_count(r.text(n))
    res = {}
    for m in Z.OVS_MODELS:
        if st is None or dc is None:
            res[m] = (None, "no dump or count")
            continue
        pred, drawn = Z.ovs_predict(w, h, g, m)
        res[m] = _fit_drawn(_dict_fit(st, pred, sfill_ok), dc, drawn)
    return res


# ---- zovp ------------------------------------------------------------------------------------
def _ovp(r, n, lines):
    w, h, g, ref, gref = Z.OVP_ROWS[n]
    full = Z.dwords(kept(ref))
    st, dc = Z.dwords(r.dump(n, DST)), drawn_count(r.text(n))
    res = {}
    for m in Z.OVL_MODELS:
        if st is None or dc is None:
            res[m] = (None, "no dump or count")
            continue
        pred, drawn = Z.ovp_predict(full, w, h, g, gref, m)
        res[m] = _fit_drawn(_dict_fit(st, pred, fill_ok), dc, drawn)
    return res


def _nan(r, n, lines):
    st, dc = Z.dwords(r.dump(n, DST)), drawn_count(r.text(n))
    res = {}
    for m in Z.NAN_MODELS:
        res[m] = ((None, "no dump or count") if st is None or dc is None else
                  _fit_drawn(_dict_fit(st, Z.nan_predict(n, m), fill_ok), dc, 0))
    if st is not None:
        lines.append(f"READING {n}: values {sorted({f'{v:#010x}' for v in st if v != Z.FILL_DEAD})[:6]}")
    return res


# ---- zoff ------------------------------------------------------------------------------------
def _zoff(r, n, lines):
    w, s = Z.ZOFF_ROWS[n]
    dep, dc = Z.dwords(r.dump(n, DEP)), drawn_count(r.text(n))
    ms = Z.OFF_MODELS if s == 0.5 else Z.SCALE_MODELS
    res = {}
    for m in ms:
        if dep is None or dc is None:
            res[m] = (None, "no dump or count")
            continue
        res[m] = _fit_drawn(Z.zoff_fit(dep, m, w, s, Z.BEND()), dc, Z.zoff_drawn(m, w, s))
    if dep is not None:
        k = Z.lin_k("H-LIN-S", w, s)
        off = set()
        for y in range(128):
            for x in range(256):
                v = Z.f32s(dep[Z.store_dword(x, y, 7)])
                if abs(v - k * Z.t_of(x)) > Z.LIN_TOL * k * Z.t_of(x):
                    off.add((x, y))
        y0 = [Z.f32s(dep[Z.store_dword(x, 0, 7)]) / Z.t_of(x) for x in (0, 64, 128, 255)]
        lines.append(f"READING {n}: drawn {dc}; z / t at y 0, x 0 64 128 255: "
                     f"{' '.join(f'{v:.5f}' for v in y0)}; off {k:.5g} t: {len(off)} pixels, "
                     f"{'BEND' if off == Z.BEND() else f'{len(off & Z.BEND())} of them in BEND'}")
    return res


# ---- controls --------------------------------------------------------------------------------
def _control(r, n, lines):
    txt = r.text(n)
    dc = drawn_count(txt)
    if n in Z.ZP_CONTROL:
        key, fz = Z.ZP_CONTROL[n]
        b = r.dump(n, DST)
        same = None if b is None else b == kept(key)
        s = None if dc is None or same is None else (dc == fz and same)
        lines.append(f"CONTROL {n}: drawn {dc} (frozen {fz}); store byte for byte the kept "
                     f"{key[:-4]}: {same}: {_st(s)}")
    elif n in Z.ZB4_CONTROL:
        k, fz = Z.ZB4_CONTROL[n]
        got = dc if k == "drawn" else changed(txt, "depth")
        sd, ss = _same_kept(r, n, Z.ZB4_TWIN[n])
        s = None if got is None or sd is None or ss is None else (got == fz and sd and ss)
        lines.append(f"CONTROL {n}: {k} {got} (frozen {fz}); depth {sd}, stencil store {ss} byte "
                     f"for byte the kept {Z.ZB4_TWIN[n]}: {_st(s)}")
    elif n == "zo-c-64":
        st = Z.dwords(r.dump(n, DST))
        got = changed(txt, "depth store")
        if st is None or dc is None or got is None:
            s, t = None, "no dump or count"
        else:
            w, h, g, ref, gref = Z.OVP_ROWS["zo-p-64"]
            pred, drawn = Z.ovp_predict(Z.dwords(kept(ref)), w, h, g, gref, "H-OVL-PASS", load=False)
            s, t = _fit_drawn(_dict_fit(st, pred, fill_ok), dc, drawn)
            s = s and got == Z.ZO_CONTROL[n][1]
        lines.append(f"CONTROL {n}: E996's owner rule without a load ({t}); dst_changed {got} "
                     f"(frozen {Z.ZO_CONTROL[n][1]}): {_st(s)}")
    elif n == "zo-c-f1":
        b = r.dump(n, DST)
        same = None if b is None else b == kept("zp-f1.dst")
        s = None if dc is None or same is None else (dc == Z.ZO_C_F1_DRAWN and same)
        lines.append(f"CONTROL {n}: drawn {dc} (frozen {Z.ZO_C_F1_DRAWN}); store byte for byte the "
                     f"kept zp-f1: {same}: {_st(s)}")
    else:
        b = r.dump(n, DEP)
        same = None if b is None else b == kept("zw-0125.dep")
        s = None if dc is None or same is None else (dc == 32768 and same)
        lines.append(f"CONTROL {n}: drawn {dc} (frozen 32768); depth byte for byte the kept "
                     f"zw-0125: {same}: {_st(s)}")
    return s


# the controls that gate a model's headline: those of its rows' own form, in the stage
GATED_BY = {
    "zbits4": {"H-OVL-PASS": ("zb4-c-base",), "H-OVL-SKIP": ("zb4-c-base",)},
    "zovp": {**{m: ("zo-c-64",) for m in Z.OVL_MODELS}, **{m: ("zo-c-f1",) for m in Z.NAN_MODELS}},
}


def stage_verdicts(r, stage):
    controls, per_model, lines = {}, {}, []
    for row in r.table:
        n = row["name"]
        if row["set"] == "control":
            controls[n] = _control(r, n, lines)
            continue
        if row["set"] == "reading":
            continue
        if stage == "zpass2":
            res = _zpass2(r, n, lines)
        elif n.startswith("zb4-b0-"):
            res = _b0(r, n)
        elif n.startswith("zb4-20-"):
            res = _inert20(r, n, {"zbits4": ((DEP, "dep"), (SST, "sst")), "zovp": ((DST, "dst"),),
                                  "zoff": ((DEP, "dep"),)}[stage])
        elif n in Z.B23_ROWS:
            res = _b23(r, n, lines)
        elif n in Z.OVS_ROWS:
            res = _ovs(r, n)
        elif n in Z.OVP_ROWS:
            res = _ovp(r, n, lines)
        elif n in Z.NAN_ROWS:
            res = _nan(r, n, lines)
        else:
            res = _zoff(r, n, lines)
        _row(lines, per_model, n, res)
    return controls, per_model, lines


def gating(stage, controls, model):
    want = GATED_BY.get(stage, {}).get(model)
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
