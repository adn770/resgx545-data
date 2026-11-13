#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r13-zls's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 05b7039ee021, pinned in FROZEN.commits);
the kept records it compares with are read at the frozen data commit (gen/pins.py).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL and READING lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage gates another)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

zbase: a held-out row holds a model when the store dump's first 2048 dwords are the model's
(gen/z13.zb_predict) and every other dword keeps the store's fill; a row whose tool printed other
buffer addresses than z13's cannot tell. Controls: zb-c-ctl and zb-c-eq0 drawn as frozen and the
store byte for byte E977's z243-ctl and E995's eq-m0; zb-c-id the identity; zb-c-off 1.0.
zbits: a stencil row holds a Z model when its drawn count (`tri 64x32 #1: N triangle`) is the
model's (1024 loaded, 2048 zero); a ramp row holds an L model when its depth dump is byte for
byte E977's z242-c-f0 (tiled) or r10-x's zb-clr-f0 (linear) as the model says. READING lines: a
stencil row's image against zbs-base's, a ramp row's layout.
zfmt: F7K / F7K-FIX hold when the 48 predicted dwords are equal and no other dword changed; F6C /
F6RAW when every applicable group (c7_rule.py, rows from zf-y48-f0's dump or the flat 0.5) is
equal; no applicable group cannot tell. Control zf-y6-ctl: 212 changed and E986's dump.

REQUIRED: the files the scorer reads; read_files(STAGE, DIR) reads exactly what verdicts() reads;
producible(row) is the set of reading keys a row's job can produce."""
import os
import re
import sys
import types

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

REQUIRED = {
    "zbase": (".txt", ".depth-store.1.bin", "cases.tsv", "void.tsv", "readings.tsv"),
    "zbits": (".txt", ".depth.1.bin", "cases.tsv", "void.tsv", "readings.tsv"),
    "zfmt": (".txt", ".depth.1.bin", "cases.tsv", "void.tsv", "readings.tsv"),
}
GATES = {}
R9X = "render/closing-r9-x/out/20261113-081821/zls/"
R10X = "render/closing-r10-x/out/20261113-101116/"
R10Z = "render/closing-r10-zls/out/20261113-102039/zst2/"
KEPT = {
    "zb-c-ctl": "data:" + R9X + "z243-ctl.depth-store.1.bin.gz",          # E977
    "zb-c-eq0": "data:" + R10X + "dcmp/eq-m0.depth-store.1.bin.gz",       # E995
    "tiled": "data:" + R9X + "z242-c-f0.depth.1.bin.gz",                  # E977
    "linear": "data:" + R10X + "zbits/zb-clr-f0.depth.1.bin.gz",          # E997
    "zf-y6-ctl": "data:" + R10Z + "z2y-f6.depth.1.bin.gz",                # E986
}
C7_RULE = "data:cited/closing11/plan/c7-q120/c7_rule.py"                 # E1015


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


def addresses_ok(text):
    """zbase's premise: the depth buffer and the store where z13 places them"""
    import z13 as Z
    t = text or ""
    return (f"depth: {Z.ZB_DEPTH:#010x} {Z.ZB_PAGES} pages," in t and
            f"base {Z.ZB_BASE:#010x}," in t and f"depth store: {Z.ZB_STORE:#010x} " in t)


def pixels(text):
    rows = {}
    for ln in (text or "").splitlines():
        if ln.startswith("row "):
            k, _, vals = ln[4:].partition(": ")
            if k.isdigit():
                rows[int(k)] = tuple(vals.split())
    return rows or None


def c7():
    import pins
    m = types.ModuleType("c7_rule")
    exec(compile(pins.blob(C7_RULE), "c7_rule.py", "exec"), m.__dict__)
    return m


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


def zbase(r):
    import z13 as Z
    controls, per_model, lines = {}, {}, []
    for row in r.table:
        n = row["name"]
        txt = r.text(n)
        st = Z.dwords(r.dump(n, ".depth-store.1.bin"))
        dc = drawn_count(txt)
        if row["set"] == "control":
            if n in Z.ZB_CONTROL_DRAWN:
                ref = kept(n)
                same = None if st is None else r.dump(n, ".depth-store.1.bin") == ref
                fz = Z.ZB_CONTROL_DRAWN[n]
                s = None if dc is None or same is None else (dc == fz and same)
                lines.append(f"CONTROL {n}: drawn {dc} (frozen {fz}); store byte for byte the kept "
                             f"record's: {same}: {_st(s)}")
            else:
                want = list(range(Z.ZB_N)) if n == "zb-c-id" else [Z.ZB_CLEAR] * Z.ZB_N
                ok = None if st is None or not addresses_ok(txt) else (
                    st[:Z.ZB_N] == want and all(v == Z.ZB_SFILL for v in st[Z.ZB_N:]))
                s = ok
                lines.append(f"CONTROL {n}: store {'identity' if n == 'zb-c-id' else '1.0'} at "
                             f"{Z.ZB_N} dwords, the rest the fill: {_st(s)}")
            controls[n] = s
            continue
        res = {}
        fit = None
        if st is not None and addresses_ok(txt):
            ds = {st[k] - k for k in range(Z.ZB_N)}
            fit = f"d = {ds.pop()}" if len(ds) == 1 else f"{len(ds)} offsets"
        rest_fill = Z.zb_store_fill(n)
        for m in Z.ZB_MODELS:
            if st is None or not addresses_ok(txt):
                res[m] = (None, "no dump or other addresses")
                continue
            p = Z.zb_predict(n, m)
            hit = sum(1 for a, b in zip(st[:Z.ZB_N], p) if a == b)
            rest = all(v == (k if rest_fill is None else rest_fill)
                       for k, v in enumerate(st) if k >= Z.ZB_N)
            res[m] = (hit == Z.ZB_N and rest, f"{hit}/{Z.ZB_N}{'' if rest else ', rest changed'}")
        for m, (s, _) in res.items():
            per_model.setdefault(m, []).append(s)
        held = [m for m, (s, _) in res.items() if s]
        lines.append(f"ROW {n}: " + "; ".join(f"{m} {t}" for m, (_, t) in res.items()) + ": "
                     + (f"held {', '.join(held)}" if held else
                        "cannot tell" if any(s is None for s, _ in res.values()) else
                        "no frozen model"))
        lines.append(f"READING {n}: store dword k = depth dword k + {fit}; drawn {dc}")
    return controls, per_model, lines


def zbits(r):
    import z13 as Z
    controls, per_model, lines = {}, {}, []
    base_img = pixels(r.text("zbs-base"))
    for row in r.table:
        n = row["name"]
        txt = r.text(n)
        dump = r.dump(n, ".depth.1.bin")
        if row["set"] == "control":
            k, fz = Z.ZBITS_CONTROL[n]
            if k == "drawn":
                got = drawn_count(txt)
                s = None if got is None else got == fz
                lines.append(f"CONTROL {n}: drawn {got} (frozen {fz}): {_st(s)}")
            else:
                got = changed(txt, "depth")
                same = None if dump is None else dump == kept("tiled")
                s = None if got is None or same is None else (got == fz and same)
                lines.append(f"CONTROL {n}: depth_changed {got} (frozen {fz}); byte for byte "
                             f"E977's z242-c-f0: {same}: {_st(s)}")
            controls[n] = s
            continue
        if n.startswith("zbs-"):
            got = drawn_count(txt)
            models, val = Z.clause_models("Z"), got
            img = pixels(txt)
            lines.append(f"READING {n}: drawn {got}; image "
                         f"{'cannot tell' if img is None or base_img is None else '=' if img == base_img else '!='}"
                         " zbs-base's")
        else:
            val = None if dump is None else ("tiled" if dump == kept("tiled") else
                                             "linear" if dump == kept("linear") else "other")
            models = Z.clause_models("L")
            lines.append(f"READING {n}: layout {val}; depth_changed {changed(txt, 'depth')}")
        res = {}
        for m in models:
            p = Z.zbits_predict(n, m)
            res[m] = (None if val is None else val == p, f"{p}")
        for m, (s, _) in res.items():
            per_model.setdefault(m, []).append(s)
        held = [m for m, (s, _) in res.items() if s]
        lines.append(f"ROW {n}: got {val}: " + (f"held {', '.join(held)}" if held else
                                                 "cannot tell" if val is None else
                                                 "no frozen model"))
    return controls, per_model, lines


def zfmt(r):
    import z13 as Z
    rule = c7()
    controls, per_model, lines = {}, {}, []
    for row in r.table:
        n = row["name"]
        txt = r.text(n)
        b = r.dump(n, ".depth.1.bin")
        dw = Z.dwords(b)
        if row["set"] == "control":
            got = changed(txt, "depth")
            same = None if b is None else b == kept(n)
            s = None if got is None or same is None else (got == Z.ZF_Y6_CHANGED and same)
            controls[n] = s
            lines.append(f"CONTROL {n}: depth_changed {got} (frozen {Z.ZF_Y6_CHANGED}); byte for "
                         f"byte E986's z2y-f6: {same}: {_st(s)}")
            continue
        if row["set"] == "reading":
            rows = None if dw is None else Z.row_values(dw, Z.ZFMT_ROWS[n][1], 32)
            const = None if rows is None else sum(len(set(x)) == 1 for t in rows.values() for x in t)
            lines.append(f"READING {n}: depth_changed {changed(txt, 'depth')}; constant tile rows "
                         f"{const}")
            continue
        res = {}
        if n.startswith("zf-7k"):
            s_byte = int(Z.ZFMT_ROWS[n][4], 16) & 0xFF
            for m in Z.ZF_MODELS_7:
                if dw is None:
                    res[m] = (None, "no dump")
                    continue
                p = Z.f7_pred(s_byte, rule, m == "F7K-FIX")
                ok = sum(1 for i, v in p.items() if dw[i] == v)
                extra = sum(1 for i, v in enumerate(dw) if v != Z.FILL_DEAD and i not in p)
                res[m] = (ok == len(p) and not extra, f"{ok}/{len(p)}, {extra} other changed")
        else:
            w = Z.ZFMT_ROWS[n][1]
            ref = Z.ZF_REF.get(n)
            if ref:
                rd = Z.dwords(r.dump(ref, ".depth.1.bin"))
                rows = None if rd is None else Z.row_values(rd, w, 32)
            else:
                rows = Z.flat_rows(w, 32)
            groups = None if rows is None or dw is None else Z.f6_groups(rows, w, 32, rule)
            for m in Z.ZF_MODELS_6:
                if not groups:
                    res[m] = (None, "no dump, reference or applicable group")
                    continue
                k = 2 if m == "F6C" else 3
                ok = sum(1 for g in groups if dw[512 * g[0] + 12 * g[1]:512 * g[0] + 12 * g[1] + 12]
                         == list(g[k]))
                res[m] = (ok == len(groups), f"{ok}/{len(groups)} groups")
            if groups:
                pred = {512 * g[0] + 12 * g[1] + i for g in groups for i in range(12)}
                other = sum(1 for i, v in enumerate(dw) if v != Z.FILL_DEAD and i not in pred)
                lines.append(f"READING {n}: {len(groups)} applicable groups; {other} changed dwords "
                             "outside them (undecoded)")
        for m, (s, _) in res.items():
            per_model.setdefault(m, []).append(s)
        held = [m for m, (s, _) in res.items() if s]
        lines.append(f"ROW {n}: " + "; ".join(f"{m} {t}" for m, (_, t) in res.items()) + ": "
                     + (f"held {', '.join(held)}" if held else
                        "cannot tell" if any(s is None for s, _ in res.values()) else
                        "no frozen model"))
    return controls, per_model, lines


STAGE_FN = {"zbase": zbase, "zbits": zbits, "zfmt": zfmt}


def verdicts(stage, d, roots=None):
    return STAGE_FN[stage](Run(stage, d))


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
            h = SK.headline(m, controls, states)
            print("SUMMARY: " + argv[1] + ": " + (h if h.startswith(m) else f"{m}: {h}"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
