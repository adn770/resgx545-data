#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r14-zls's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 dddadbdd001b, pinned in FROZEN.commits);
the kept records it compares with are read at the frozen data commit (gen/pins.py).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL and READING lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage gates another)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Rows are grouped in stages by the dump their scorer reads (gen/z14.py STAGE_ROWS); a model's
headline is gated by the controls of its own rows' form (GATED_BY), the stage's otherwise.
A granule or integer row holds a model when the store dump's predicted dwords are the
model's and every other dword keeps the store's fill (gen/z14.gran_predict, int_predict); a
stencil row when every pixel's loaded byte (the stored byte at E988's position, XOR 0xff where the
pixel drew) is the model's. A row whose tool printed other buffer addresses cannot tell. An
integer or overlap row holds a model when every dword the model predicts from the row's
format-0 reference is equal and no other dword changed; zo-g3 when the pages holding changed
dwords are the model's, 1024 changed each. A set-half row by its drawn count; a pitch row
when every byte is explained (z14.pitch_check); zb2-d12 and zb2-f2-16 by their dumps. The flat rows'
blocks (FL-HEAD, FL-CONST, FL-SHAPE), zl-f7-idx against E986's kept format-7 dumps,
zl-f5-flat against E1031's. Controls: each its frozen reading and, where it replicates a kept job,
that job's dump byte for byte.

REQUIRED: the files the scorer reads (every row of a stage writes its stage's dump: gen/z14.py
STAGE_ROWS); read_files(STAGE, DIR) reads exactly what verdicts() reads;
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
import z14 as Z  # noqa: E402

FIXED = ("cases.tsv", "void.tsv", "readings.tsv")


REQUIRED = {
    "zgran": (".txt", ".depth-store.1.bin") + FIXED,
    "zodd": (".txt", ".depth.1.bin") + FIXED,
    "zbits2": (".txt", ".stencil-store.1.bin") + FIXED,
    "zflat": (".txt", ".depth.1.bin") + FIXED,
}
GATES = {}
R9X = "render/closing-r9-x/out/20261113-081821/zls/"
R10X = "render/closing-r10-x/out/20261113-101116/"
R10Z = "render/closing-r10-zls/out/20261113-102039/zst2/"
R13Z = "render/closing-r13-zls/out/20261113-213117/"
KEPT = {
    "zg-c-ctl": "data:" + R9X + "z243-ctl.depth-store.1.bin.gz",            # E977 (E1029 kept)
    "zg-c-m4": "data:" + R13Z + "zbase/zb-m4.depth-store.1.bin.gz",         # E1029
    "zg-c-m40": "data:" + R13Z + "zbase/zb-m40.depth-store.1.bin.gz",       # E1029
    "zo-c-ov": "data:" + R10X + "zov/zov-64x32-g0.depth.1.bin.gz",          # E996
    "zb2-c-r16": "data:" + R10X + "zbits/zb-clr-f0.depth.1.bin.gz",         # E997 (E1030)
    "z242-c-f2": "data:" + R9X + "z242-c-f2.depth.1.bin.gz",                # E977
    "zl-c-flat": "data:" + R13Z + "zfmt/zf-flat-f6.depth.1.bin.gz",         # E1031
    "zl-c-y6": "data:" + R10Z + "z2y-f6.depth.1.bin.gz",                    # E986
    "z2y-f7": "data:" + R10Z + "z2y-f7.depth.1.bin.gz",                     # E986
    "z2d-f7": "data:" + R10Z + "z2d-f7.depth.1.bin.gz",                     # E986
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


def zb_addresses_ok(text):
    """the zbase form's premise: the depth buffer and the store where z14 places them"""
    t = text or ""
    return (f"depth: {Z.ZB_DEPTH:#010x} {Z.ZB_PAGES} pages," in t and
            f"base {Z.ZB_BASE:#010x}," in t and f"depth store: {Z.ZB_STORE:#010x} " in t)


def st_addresses_ok(text):
    t = text or ""
    return (f"depth: {Z.ST_DEPTH:#010x} 18 pages," in t and f"base {Z.ZB_BASE:#010x}," in t and
            f"stencil: {Z.ST_STENCIL:#010x} 18 pages" in t and
            f"stencil store: {Z.ST_SSTORE:#010x} " in t)


def g3_addresses_ok(text):
    t = text or ""
    return f"depth: {Z.ZB_DEPTH:#010x} {Z.ZB_PAGES} pages," in t and f"base {Z.ZB_BASE:#010x}," in t


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
    """(held, text) of a {dword: value} prediction: equal there, `rest(i, v)` true elsewhere"""
    hit = sum(1 for i, v in pred.items() if i < len(dw) and dw[i] == v)
    other = sum(1 for i, v in enumerate(dw) if i not in pred and not rest(i, v))
    return hit == len(pred) and not other, f"{hit}/{len(pred)}{f', {other} other' if other else ''}"


def stencil_fit(st, drawn, model, sfill="index"):
    if st is None or drawn is None:
        return None, "no dump or image"
    ok = sum(1 for y in range(32) for x in range(64)
             if st[Z.st_pos(x, y)] ^ (0xFF if (x, y) in drawn else 0) == Z.s_loaded(model, x, y, sfill))
    return ok == 2048, f"{ok}/2048"


def flat_ref():
    """E1031's flat block: its 44 dwords and the byte places of its 0x9e markers"""
    b = kept("zl-c-flat")
    return Z.dwords(b)[:Z.FLAT_N], {i for i, x in enumerate(b[:4 * Z.FLAT_N]) if x == 0x9E}


def _control(r, n, lines):
    txt = r.text(n)
    if n == "zg-c-sid":
        st = r.dump(n, ".stencil-store.1.bin")
        s, t = stencil_fit(st, drawn_set(txt), "S-UNMOVED") if st_addresses_ok(txt) else (None, "")
        lines.append(f"CONTROL {n}: the loaded stencil the index fill in E988's order at {t} "
                     f"pixels: {_st(s)}")
    elif n in Z.ZG_CONTROL:
        b = r.dump(n, ".depth-store.1.bin")
        same = None if b is None else b == kept(n)
        dc = drawn_count(txt)
        s = same if n != "zg-c-ctl" else (None if dc is None or same is None else
                                          dc == 2048 and same)
        lines.append(f"CONTROL {n}: drawn {dc}; store byte for byte the kept record's: {same}: "
                     f"{_st(s)}")
    elif n in ("zo-c-ov", "zb2-c-r16", "zl-c-flat", "zl-c-y6"):
        b = r.dump(n, ".depth.1.bin")
        got = changed(txt, "depth")
        fz = {"zo-c-ov": Z.ZO_OV_CHANGED, "zb2-c-r16": Z.ZB2_CONTROL["zb2-c-r16"][1],
              **Z.ZL_CHANGED}[n]
        same = None if b is None else b == kept(n)
        s = None if got is None or same is None else (got == fz and same)
        lines.append(f"CONTROL {n}: depth_changed {got} (frozen {fz}); byte for byte the kept "
                     f"record's: {same}: {_st(s)}")
    else:
        fz = Z.ZB2_CONTROL[n][1]
        got = drawn_count(txt)
        s = None if got is None else got == fz
        if n == "zb2-c-set":
            st = r.dump(n, ".stencil-store.1.bin")
            allff = None if st is None else all(
                st[Z.st_pos(x, y)] == 0xFF for y in range(32) for x in range(64))
            s = None if s is None or allff is None else (s and allff)
            lines.append(f"CONTROL {n}: drawn {got} (frozen {fz}); every stored byte 0xff: {allff}: "
                         f"{_st(s)}")
        else:
            lines.append(f"CONTROL {n}: drawn {got} (frozen {fz}): {_st(s)}")
    return s


def _zbase_form(r, n, lines):
    txt = r.text(n)
    st = Z.dwords(r.dump(n, ".depth-store.1.bin"))
    ok = st is not None and zb_addresses_ok(txt)
    res = {}
    keep = lambda i, v: v == Z.ZB_SFILL  # noqa: E731
    if n in Z.GRAN_MOVES:
        for m in Z.GRAN_MODELS:
            p = dict(enumerate(Z.gran_predict(m, Z.GRAN_MOVES[n])))
            res[m] = _dict_fit(st, p, keep) if ok else (None, "no dump or other addresses")
        if ok:
            ds = {st[k] - k for k in range(Z.ZB_N)}
            lines.append(f"READING {n}: store dword k = depth dword k + "
                         + (f"d = {ds.pop()}" if len(ds) == 1 else f"{len(ds)} offsets"))
    elif n in Z.INT_ROWS:
        fmt = Z.INT_ROWS[n]
        for m in Z.INT_MODELS[fmt]:
            res[m] = _dict_fit(st, Z.int_predict(fmt, m), lambda i, v: v == Z.INT_SFILL) if ok else (
                None, "no dump or other addresses")
        if ok:
            k = Z.ZB_N if fmt == 1 else Z.ZB_N // 2
            lines.append(f"READING {n}: the first {k} store dwords hold "
                         f"{sorted({f'{v:#x}' for v in st[:k]})[:6]}")
    else:
        for m in Z.D12_MODELS:
            res[m] = _dict_fit(st, dict(enumerate(Z.d12_predict(m))), keep) if ok else (
                None, "no dump or other addresses")
        if ok:
            ds = {st[k] - k for k in range(Z.ZB_N)}
            lines.append(f"READING {n}: {len(ds)} offsets of store dword k from depth dword k")
    return res


def _depth_row(r, n, lines):
    txt = r.text(n)
    dw = Z.dwords(r.dump(n, ".depth.1.bin"))
    dead = lambda i, v: v == Z.FILL_DEAD  # noqa: E731
    res = {}
    if n in Z.OV_ROWS:
        w, h, g, ref = Z.OV_ROWS[n]
        full = Z.dwords(r.dump(ref, ".depth.1.bin"))
        for m in Z.OV_MODELS:
            res[m] = (None, "no dump or reference") if dw is None or full is None else \
                _dict_fit(dw, Z.ov_predict(full, w, h, g, m), dead)
    elif n == "zo-g3":
        ok = dw is not None and g3_addresses_ok(txt)
        pages = {} if not ok else {
            p: sum(1 for v in dw[1024 * p:1024 * p + 1024] if v != Z.FILL_DEAD)
            for p in range(Z.ZB_PAGES)}
        got = sorted(p for p, c in pages.items() if c)
        for m in Z.G3_MODELS:
            want = Z.g3_pages(m)
            res[m] = (None, "no dump or other addresses") if not ok else (
                got == want and all(pages[p] == 1024 for p in want), f"pages {got}")
        if ok:
            lines.append(f"READING {n}: changed per page {[(p, c) for p, c in pages.items() if c]}; "
                         f"values {sorted({f'{v:#x}' for v in dw if v != Z.FILL_DEAD})[:4]}")
    elif n == "zb2-f2-16":
        f2 = Z.dwords(kept("z242-c-f2"))
        for m in Z.L16_MODELS:
            res[m] = (None, "no dump") if dw is None else _dict_fit(
                dw, Z.l16_predict(m, f2), dead)
        lines.append(f"READING {n}: depth_changed {changed(txt, 'depth')}")
    else:
        k, fmt = n[3:5], int(n[-1])
        w, h, g = Z.ODD[k]
        ref = Z.dwords(r.dump(f"zo-{k}-f0", ".depth.1.bin"))
        for m in Z.INT_PAST_MODELS:
            res[m] = (None, "no dump or reference") if dw is None or ref is None else \
                _dict_fit(dw, Z.int_past_predict(ref, w, h, g, fmt, m), dead)
    return res


def _stencil_row(r, n, lines, base_img):
    txt = r.text(n)
    st = r.dump(n, ".stencil-store.1.bin")
    dr = drawn_set(txt)
    res = {}
    if n == "zg-s14":
        ok = st_addresses_ok(txt)
        for m in Z.S_MODELS:
            res[m] = stencil_fit(st, dr, m) if ok else (None, "no dump or other addresses")
        lines.append(f"READING {n}: drawn {drawn_count(txt)}")
    elif n in Z.PITCH_ROWS:
        w, bit = Z.PITCH_ROWS[n]
        for m in Z.P_MODELS:
            if st is None or dr is None:
                res[m] = (None, "no dump or image")
                continue
            ok, tot = Z.pitch_check(st, dr, w, bit, m)
            res[m] = (ok == tot, f"{ok}/{tot}")
        lines.append(f"READING {n}: drawn {drawn_count(txt)}")
    else:
        got = drawn_count(txt)
        for m in Z.z_models():
            p = Z.z_predict(n, m)
            res[m] = (None if got is None else got == p, str(p))
        lines.append(f"READING {n}: drawn {got}; image "
                     f"{'cannot tell' if dr is None or base_img is None else '=' if dr == base_img else '!='}"
                     " zb2-c-base's")
    return res


def _flat_row(r, n, lines):
    b = r.dump(n, ".depth.1.bin")
    dw = Z.dwords(b)
    res = {}
    if dw is None:
        models = (Z.FL_MODELS if n in Z.FLAT_DEPTHS else Z.F7I_MODELS if n == "zl-f7-idx"
                  else Z.F5_MODELS)
        return {m: (None, "no dump") for m in models}
    if n in Z.FLAT_DEPTHS:
        v = Z.flat_v(n)
        ref, r9e = flat_ref()
        blocks = [dw[512 * k:512 * k + 512] for k in range(4)]
        changed_at = [sorted(i for i, x in enumerate(bk) if x != Z.FILL_DEAD) for bk in blocks]
        outside = sum(1 for i, x in enumerate(dw) if i >= 2048 and x != Z.FILL_DEAD)
        head = sum(bk[:4] == Z.f6c_head(v) for bk in blocks)
        res["FL-HEAD"] = (head == 4, f"{head}/4 blocks")
        const = sum(bk[:Z.FLAT_N] == ref and changed_at[k] == list(range(Z.FLAT_N))
                    for k, bk in enumerate(blocks))
        res["FL-CONST"] = (const == 4 and not outside, f"{const}/4 blocks")
        shape = sum(changed_at[k] == list(range(Z.FLAT_N)) and bk == blocks[0]
                    for k, bk in enumerate(blocks))
        p9e = {i for i, x in enumerate(b[:4 * Z.FLAT_N]) if x == 0x9E}
        res["FL-SHAPE"] = (shape == 4 and not outside and p9e == r9e,
                           f"{shape}/4 blocks, 0x9e at E1031's places {p9e == r9e}")
        last = max(changed_at[0]) + 1 if changed_at[0] else 0
        lines.append(f"READING {n}: v {v:#010x}; changed per block {[len(c) for c in changed_at]}, "
                     f"outside {outside}; block 0 bytes {b[:4 * last].hex()}")
    elif n == "zl-f7-idx":
        y7, d7 = Z.dwords(kept("z2y-f7")), Z.dwords(kept("z2d-f7"))
        common = {i: a for i, (a, c) in enumerate(zip(y7, d7)) if a == c and a != Z.FILL_DEAD}
        hit = sum(1 for i, a in common.items() if dw[i] == a)
        res["F7I-COMMON"] = (hit == len(common), f"{hit}/{len(common)}")
        per = [sum(1 for x in dw[512 * k:512 * k + 512] if x != Z.FILL_DEAD) for k in range(2)]
        tot = sum(1 for x in dw if x != Z.FILL_DEAD)
        res["F7I-COUNT"] = (tot == 784 and per == [392, 392], f"{tot} changed, blocks 0-1 {per}")
        lines.append(f"READING {n}: {tot} changed; "
                     f"{sum(1 for i in range(len(dw)) if dw[i] != y7[i])} dwords differ from z2y-f7")
    else:
        same = b == kept("zl-c-flat")
        res["F5-EQ-F6"] = (same, "byte for byte" if same else "differs")
        per = [sum(1 for x in dw[512 * k:512 * k + 512] if x != Z.FILL_DEAD) for k in range(8)]
        lines.append(f"READING {n}: changed per block {per}")
    return res


# the controls that gate a model's headline: those of its rows' own form, in the stage
GATED_BY = {**{m: ("zb2-c-r16",) for m in Z.L16_MODELS},
            **{m: ("zg-c-sid", "zb2-c-base") for m in Z.S_MODELS},
            **{m: ("zo-c-ov",) for m in Z.INT_PAST_MODELS + Z.OV_MODELS + Z.G3_MODELS},
            **{m: ("zb2-c-base", "zb2-c-set") for m in Z.z_models() + list(Z.P_MODELS)}}


def stage_verdicts(r):
    controls, per_model, lines = {}, {}, []
    base_img = drawn_set(r.text("zb2-c-base")) if "zb2-c-base" in [x["name"] for x in r.table] \
        else None
    for row in r.table:
        n = row["name"]
        if row["set"] == "control":
            controls[n] = _control(r, n, lines)
            continue
        if row["set"] == "reading":
            dw = Z.dwords(r.dump(n, ".depth.1.bin"))
            ch = None if dw is None else [v for v in dw if v != Z.FILL_DEAD]
            lines.append(f"READING {n}: depth_changed {changed(r.text(n), 'depth')}; distinct "
                         f"{None if ch is None else len(set(ch))}")
            continue
        if n in Z.GRAN_MOVES or n in Z.INT_ROWS or n == "zb2-d12":
            res = _zbase_form(r, n, lines)
        elif n in Z.ZODD or n == "zb2-f2-16":
            res = _depth_row(r, n, lines)
        elif n in Z.ZFLAT:
            res = _flat_row(r, n, lines)
        else:
            res = _stencil_row(r, n, lines, base_img)
        _row(lines, per_model, n, res)
    return controls, per_model, lines


def gating(stage, controls, model):
    want = GATED_BY.get(model)
    return controls if want is None else {c: s for c, s in controls.items() if c in want}


def verdicts(stage, d, roots=None):
    return stage_verdicts(Run(stage, d))


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
