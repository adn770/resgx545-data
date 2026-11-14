#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r17-zls's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 c2180e64ecda, pinned in FROZEN.commits);
the kept records it compares with are read at the frozen data commit (gen/pins.py, z17.KEPT).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL and READING lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage gates another)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

zovp2: a load pass row holds a model when the store's dwords at the owner tiles' slots are
z17.ovp_predict's (the plane the kept full-pitch reference's), the rest keeps the store's fill, and
the drawn count is the model's. zovs2: the same on the stencil store (z17.ovs_predict). zb20: a
bit-20-cleared row holds a model when its depth dump is the fill except the twin's tile records
(its slots' dwords other than the fill, in slot order) from the model's start
(z17.pack_predict), its stencil store is the twin's and the drawn count the target's pixels.
Controls: each its frozen reading and the kept dumps (or E996's owner rule) byte for byte; every
model's headline is gated by every control of its stage.

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
import z17 as Z  # noqa: E402

FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
DST, DEP, SST = ".depth-store.1.bin", ".depth.1.bin", ".stencil-store.1.bin"
REQUIRED = {
    "zovp2": (".txt", DST) + FIXED,
    "zovs2": (".txt", SST) + FIXED,
    "zb20": (".txt", DEP, SST) + FIXED,
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


def _split(seq, pred, inside):
    """(mismatches inside the extent, mismatches beyond it) of a prediction over the owner tiles"""
    bad = [i for i, v in pred.items() if i >= len(seq) or seq[i] != v]
    return sum(1 for i in bad if i in inside), sum(1 for i in bad if i not in inside)


# ---- zovp2 and zovs2 -------------------------------------------------------------------------
def _ovp(r, n, lines):
    w, h, g, ref, gref = Z.OVP_ROWS[n]
    full = Z.dwords(Z.kept(ref + ".dep"))
    st, dc = Z.dwords(r.dump(n, DST)), drawn_count(r.text(n))
    inside = Z.inside_positions(w, h, g, False)
    res, parts = {}, []
    for m in Z.OVL_MODELS:
        if st is None or dc is None:
            res[m] = (None, "no dump or count")
            continue
        pred, drawn = Z.ovp_predict(full, w, h, g, gref, m)
        res[m] = _fit_drawn(_dict_fit(st, pred, fill_ok), dc, drawn)
        a, b = _split(st, pred, inside)
        parts.append(f"{m} {a} inside, {b} beyond")
    if parts:
        lines.append(f"READING {n}: dwords off the model, inside the extent / beyond it: "
                     + "; ".join(parts))
    return res


def _ovs(r, n, lines):
    w, h, g = Z.OVS_ROWS[n]
    st, dc = r.dump(n, SST), drawn_count(r.text(n))
    inside = Z.inside_positions(w, h, g, True)
    res, parts = {}, []
    for m in Z.OVS_MODELS:
        if st is None or dc is None:
            res[m] = (None, "no dump or count")
            continue
        pred, drawn = Z.ovs_predict(w, h, g, m)
        res[m] = _fit_drawn(_dict_fit(st, pred, sfill_ok), dc, drawn)
        a, b = _split(st, pred, inside)
        parts.append(f"{m} {a} inside, {b} beyond")
    if parts:
        lines.append(f"READING {n}: bytes off the model, inside the extent / beyond it: "
                     + "; ".join(parts))
    return res


# ---- zb20 ------------------------------------------------------------------------------------
def _zb20(r, n, lines):
    fmt, w, h, g = Z.ZB20_ROWS[n]
    tn = Z.zb20_twin_of(n)
    dep, dc = Z.dwords(r.dump(n, DEP)), drawn_count(r.text(n))
    twin, tdc = Z.dwords(r.dump(tn, DEP)), drawn_count(r.text(tn))
    sst, tsst = r.dump(n, SST), r.dump(tn, SST)
    nslots = Z.tiles(w, h)[1] * (g + 1)
    if twin is not None:
        recs = Z.records(twin, nslots)
        lines.append(f"READING {tn}: drawn {tdc}; records per slot {[len(x) for x in recs]}, "
                     f"each a prefix of its slot: {Z.prefix_records(twin, nslots)}")
    if dep is not None and twin is not None:
        idx = [i for i, v in enumerate(dep) if v != Z.FILL_DEAD]
        cat = [v for x in Z.records(twin, nslots) for v in x]
        lines.append(f"READING {n}: drawn {dc}; written dwords {len(idx)}"
                     + (f", {idx[0]} to {idx[-1]}, contiguous {idx == list(range(idx[0], idx[0] + len(idx)))}"
                        f", the twin's records in slot order: {[dep[i] for i in idx] == cat}"
                        if idx else ""))
    res = {}
    for m in Z.PACK_MODELS:
        if None in (dep, twin, dc, tdc, sst, tsst):
            res[m] = (None, "no dump or count")
            continue
        fit = _dict_fit(dep, Z.pack_predict(twin, w, h, g, m), fill_ok)
        ok = fit[0] and sst == tsst and dc == w * h and tdc == w * h
        res[m] = (ok, f"{fit[1]} from {Z.pack_start(m, w, h, g)}, stencil store as the twin's "
                      f"{sst == tsst}, drawn {dc}/{w * h}, twin {tdc}")
    return res


# ---- controls --------------------------------------------------------------------------------
def _control(r, n, lines):
    txt = r.text(n)
    dc = drawn_count(txt)
    if n in Z.C160:
        _, kr, ks = Z.C160[n]
        dst = n == "zo2-c-160"
        suf = DST if dst else SST
        b = r.dump(n, suf)
        same = None if b is None else b == Z.kept(ks)
        fz = Z.kept_count(kr, "drawn")
        what = "depth store" if dst else "stencil store"
        ch, fch = changed(txt, what), Z.kept_count(kr, what)
        s = None if None in (dc, same, ch) else (dc == fz and same and ch == fch)
        lines.append(f"CONTROL {n}: drawn {dc} (frozen {fz}), {what} changed {ch} (frozen {fch}); "
                     f"store byte for byte the kept {ks.split('.')[0]}: {same}: {_st(s)}")
    elif n in Z.OVC_ROWS:
        w, h, g, ref, gref = Z.OVC_ROWS[n]
        st, got = Z.dwords(r.dump(n, DST)), changed(txt, "depth store")
        fd, fch = Z.ovc_expect(n)
        if st is None or dc is None or got is None:
            s, t = None, "no dump or count"
        else:
            pred, drawn = Z.ovp_predict(Z.dwords(Z.kept(ref + ".dep")), w, h, g, gref,
                                        "H-OVL-PASS-EDGE", load=False)
            s, t = _fit_drawn(_dict_fit(st, pred, fill_ok), dc, drawn)
            s = s and got == fch and drawn == fd
            if n == "zo2-c-65":
                ov = Z.dwords(Z.kept("zo-65-ov.dep"))
                same = st[:fch] == ov[:fch]
                s = s and same
                t += f", first {fch} dwords the kept zo-65-ov's: {same}"
        lines.append(f"CONTROL {n}: E996's owner rule without a load ({t}); dst_changed {got} "
                     f"(frozen {fch}): {_st(s)}")
    else:
        tw, ts = r.dump(n, DEP), r.dump(n, SST)
        sd = None if tw is None else tw == Z.kept("zf-flat-f6.dep")
        ss = None if ts is None else ts == Z.kept("zf-flat-f6.sst")
        got = changed(txt, "depth")
        s = None if None in (sd, ss, got) else (sd and ss and got == Z.ZB20_CTL[n][1])
        lines.append(f"CONTROL {n}: depth_changed {got} (frozen {Z.ZB20_CTL[n][1]}); depth {sd}, "
                     f"stencil store {ss} byte for byte the kept zf-flat-f6: {_st(s)}")
    return s


def stage_verdicts(r, stage):
    controls, per_model, lines = {}, {}, []
    for row in r.table:
        n = row["name"]
        if row["set"] == "control":
            controls[n] = _control(r, n, lines)
            continue
        if row["set"] == "reading":
            continue
        if n in Z.OVP_ROWS:
            res = _ovp(r, n, lines)
        elif n in Z.OVS_ROWS:
            res = _ovs(r, n, lines)
        else:
            res = _zb20(r, n, lines)
        _row(lines, per_model, n, res)
    return controls, per_model, lines


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
            h = SK.headline(m, controls, states)
            print("SUMMARY: " + argv[1] + ": " + (h if h.startswith(m) else f"{m}: {h}"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
