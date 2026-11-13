#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r10-zls's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 9849dab7540c, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL and READING lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

zst2 (gen/zst2.py): a control passes at its frozen changed-dword counts (`depth #1`, `stencil
store #1`); a held-out row is scored per frozen model on its whole depth dump (gen/zst2.check:
every predicted byte, every changed dword predicted whole) from the plane's format-0 reference and
the row's own loaded stencil, and per H-E978 on its stencil store (0 changed). zbgc, zbg
(gen/zbg.py): every background dword at the poked word (controls) or at a model's value (rows);
zbg's headline is gated by zbgc's controls (GATES, and the runner's gate). zw: zw-c50 byte for
byte E977's kept z242-a-f0 (pinned); the rows per model within the tolerance over the mask.
A row whose job or reference did not complete, or kept no dump, cannot tell.

REQUIRED: the files each stage's scorer reads; read_files(STAGE, DIR) reads exactly what
verdicts() reads; producible(row) is the set of reading keys a row's job can produce."""
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

BASE = (".txt", "cases.tsv", "void.tsv", "readings.tsv", ".depth.1.bin")
REQUIRED = {"zst2": BASE + (".stencil.1.bin",), "zbgc": BASE, "zbg": BASE, "zw": BASE}
GATES = {"zbg": "zbgc"}     # {stage: the earlier stage whose controls gate it}


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


def changed(text, label):
    m = re.search(r"^%s #1: (\d+) dwords, (\d+) changed" % label, text or "", re.M)
    return int(m.group(2)) if m else None


def raw(d, name):
    b = K._read(os.path.join(d, name))
    return None if b is None or len(b) % 4 else b


def dwords(b):
    return None if b is None else list(struct.unpack("<%dI" % (len(b) // 4), b))


def _st(s):
    return "PASS" if s else "FAILED" if s is False else "cannot tell"


def _hv(s):
    return "held" if s else "FAILED" if s is False else "cannot tell"


def fbits(v):
    return struct.unpack("<f", struct.pack("<I", v))[0]


# ---- zst2 -----------------------------------------------------------------------------------
def v_zst2(stage, d, roots):
    import zst2 as Z
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    done = lambda n: n in cases and K.completed(cases[n])  # noqa: E731
    controls, per_model, lines = {}, {}, []
    depth = {}

    def dump(n):
        if n not in depth:
            depth[n] = raw(d, n + ".depth.1.bin") if done(n) else None
        return depth[n]

    for r in K.table(KP, stage):
        n = r["name"]
        want = preds.get(n, {})
        txt = K.text(d, n + ".txt") if done(n) else ""
        dc, sc = changed(txt, "depth"), changed(txt, "stencil store")
        if r["set"] == "control":
            parts, st = [], True
            for q, got in (("depth_changed", dc), ("sst_changed", sc)):
                if q in want:
                    fz = int(next(iter(want[q].values())))
                    parts.append(f"{q} {got} (frozen {fz})")
                    st = None if got is None or st is None else (st and got == fz)
            if "sst_changed" not in want:
                parts.append(f"sst_changed {sc} (a reading)")
            controls[n] = st
            lines.append(f"CONTROL {n}: " + ", ".join(parts) + f": {_st(st)}")
        sst = want.get("sst_changed", {}).get("H-E978")
        if sst is not None and r["set"] != "control":
            s = None if sc is None else sc == int(sst)
            per_model.setdefault("H-E978 (no stencil store)", []).append(s)
        if r["set"] == "control" and "bytes" not in want:
            continue
        w, h = Z.PLANES[Z.plane_of(n)][:2]
        fmt = Z.fmt_of(n)
        ref = dwords(dump(Z.ref_of(n)))
        mine = dump(n)
        sten = raw(d, n + ".stencil.1.bin") if done(n) else None
        if fmt == 7:
            f4 = dump(n.replace("-f7", "-f4"))
            ch = [k for k in range(len(mine) // 4) if mine[4 * k:4 * k + 4] != b"\xef\xbe\xad\xde"] \
                if mine else None
            same4 = None if not (mine and f4) else sum(
                1 for k in ch if f4[4 * k:4 * k + 4] == mine[4 * k:4 * k + 4])
            lines.append(f"READING {n}: changed dwords {None if ch is None else len(ch)}, equal to "
                         f"{n.replace('-f7', '-f4')}'s at the same offset {same4}; stencil store "
                         f"changed {sc}")
            continue
        res = {}
        for m in want.get("bytes", {}):
            if ref is None or mine is None or sten is None:
                res[m] = (None, "no dump")
                continue
            held, ok, npred, nch, whole = Z.check(Z.predict(fmt, m, ref, sten, w, h), mine)
            res[m] = (held, f"{ok}/{npred} bytes, {whole}/{nch} changed dwords whole")
        if r["set"] != "control":
            for m, (s, _) in res.items():
                per_model.setdefault(m, []).append(s)
        held = [m for m, (s, _) in res.items() if s]
        tag = "ROW" if r["set"] != "control" else "CONTROL-LAYOUT"
        lines.append(f"{tag} {n}: " + "; ".join(f"{m} {t}" for m, (_, t) in res.items())
                     + f"; stencil store changed {sc}: "
                     + (f"held {', '.join(held)}" if held else
                        "no frozen model" if all(s is False for s, _ in res.values()) else
                        "cannot tell"))
    for p in ("y", "d"):
        a, b = dump(f"z2{p}-f3"), dump(f"z2{p}-f5")
        lines.append(f"READING z2{p}: f3 and f5 byte-identical: "
                     f"{None if a is None or b is None else a == b}")
    if dump("z2x-f0") is not None:
        import pins
        e978 = pins.blob("data:" + E978_CTL)
        lines.append(f"READING z2x-f0: byte for byte E978's z120-ctl-s: {dump('z2x-f0') == e978}")
    return controls, per_model, lines


E978_CTL = "render/closing-r9-x/out/20261113-081821/zst/z120-ctl-s.depth.1.bin.gz"


# ---- zbgc, zbg --------------------------------------------------------------------------------
def v_bg(stage, d, roots):
    import zbg as B
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    done = lambda n: n in cases and K.completed(cases[n])  # noqa: E731
    controls, per_model, lines = {}, {}, []
    for r in K.table(KP, stage):
        n = r["name"]
        want = preds.get(n, {})
        fmt = (int(r["args"].split("--depth-ctl ")[1].split()[0], 16) >> 24) & 7
        dump = dwords(raw(d, n + ".depth.1.bin")) if done(n) else None
        mask = B.bg_dwords(fmt)
        got = None if dump is None else [dump[i] if i < len(dump) else None for i in mask]
        vals = {}
        for v in got or ():
            vals[v] = vals.get(v, 0) + 1
        top = ", ".join(f"{'-' if v is None else f'{v:#010x}'} x {c}"
                        for v, c in sorted(vals.items(), key=lambda t: -t[1])[:3])
        if r["set"] == "control":
            dc = changed(K.text(d, n + ".txt"), "depth") if done(n) else None
            fz = int(want["depth_changed"]["H-E831"])
            bg = int(want["bg"]["H-BGDEPTH"], 16)
            st = None if got is None or dc is None else (dc == fz and all(v == bg for v in got))
            controls[n] = st
            tri = {}
            if dump is not None:
                for y in range(B.H):
                    for x in range(B.W):
                        if B.is_tri(x, y):
                            v = dump[B.f0_index(x, y)]
                            tri[v] = tri.get(v, 0) + 1
            lines.append(f"CONTROL {n}: depth_changed {dc} (frozen {fz}); {len(mask)} background "
                         f"dwords: {top} (frozen {bg:#010x}): {_st(st)}")
            lines.append(f"READING {n}: triangle pixels: " + ", ".join(
                f"{v:#010x} x {c}" for v, c in sorted(tri.items(), key=lambda t: -t[1])[:3]))
            continue
        res = {}
        for m, v in want.get("bg", {}).items():
            s = None if got is None else all(x == int(v, 16) for x in got)
            res[m] = s
            per_model.setdefault(m, []).append(s)
        held = [m for m, s in res.items() if s]
        lines.append(f"ROW {n}: {len(mask)} background dwords: {top}: "
                     + (f"held {', '.join(held)}" if held else
                        "no frozen model" if got is not None else "cannot tell"))
    if stage == "zbg":
        controls = borrowed(roots or [os.path.dirname(d)])
        lines += [f"CONTROL {k} (of zbgc): {_st(v)}" for k, v in controls.items()]
    return controls, per_model, lines


def borrowed(roots):
    for root in roots:
        p = os.path.join(root, "zbgc")
        if os.path.isdir(p):
            return v_bg("zbgc", p, roots)[0]
    return {"zbgc": None}


# ---- zw ---------------------------------------------------------------------------------------
E977_REF = "render/closing-r9-x/out/20261113-081821/zls/z242-a-f0.depth.1.bin.gz"


def v_zw(stage, d, roots):
    import zbg as B
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    done = lambda n: n in cases and K.completed(cases[n])  # noqa: E731
    controls, per_model, lines = {}, {}, []
    pix = B.w10_pixels()
    for r in K.table(KP, stage):
        n = r["name"]
        want = preds.get(n, {})
        b = raw(d, n + ".depth.1.bin") if done(n) else None
        if r["set"] == "control":
            import pins
            ref = pins.blob("data:" + E977_REF)
            dc = changed(K.text(d, n + ".txt"), "depth") if done(n) else None
            fz = int(want["depth_changed"]["H-E831"])
            same = None if b is None else b == ref
            st = None if b is None or dc is None else (dc == fz and same)
            controls[n] = st
            lines.append(f"CONTROL {n}: depth_changed {dc} (frozen {fz}); byte for byte E977's "
                         f"z242-a-f0: {same}: {_st(st)}")
            continue
        w = fbits(int(r["args"].split("blk:10=")[1].split()[0], 16))
        z = dwords(b)
        res, fit = {}, None
        if z is not None:
            zs = [fbits(z[B.f0_index(x, y)]) for x, y in pix]
            ratios = sorted(v / ((x + 0.5) / 512) for v, (x, y) in zip(zs, pix))
            fit = ratios[len(ratios) // 2]
        for m in want.get("factor", {}):
            if z is None:
                res[m] = (None, "no dump")
                continue
            at = sum(1 for v, (x, y) in zip(zs, pix) if B.w10_at(v, B.w10_z(m, w, x)))
            res[m] = (at == len(pix), f"{at}/{len(pix)}")
            per_model.setdefault(m, []).append(res[m][0])
        held = [m for m, (s, _) in res.items() if s]
        lines.append(f"ROW {n} (w {w}): median z/t {fit}; " + "; ".join(
            f"{m} {t}" for m, (_, t) in res.items()) + ": "
            + (f"held {', '.join(held)}" if held else "no frozen model" if z is not None else
               "cannot tell"))
    return controls, per_model, lines


VERDICTS = {"zst2": v_zst2, "zbgc": v_bg, "zbg": v_bg, "zw": v_zw}


def verdicts(stage, d, roots=None):
    return VERDICTS[stage](stage, d, roots)


def read_files(stage, d):
    verdicts(stage, d, [])


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        dep = GATES.get(argv[2])
        if dep is None:
            return 0
        for root in argv[3:]:
            p = os.path.join(root, dep)
            if os.path.isdir(p):
                g = SK.gate(verdicts(dep, p, argv[3:])[0])
                print(f"gate {argv[2]} on {dep}: {'open' if g.ok else '; '.join(g.problems)}")
                return 0 if g.ok else 1
        print(f"gate {argv[2]}: {dep} has not run")
        return 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, per_model, lines = verdicts(argv[1], argv[2], argv[3:])
        print("\n".join(lines))
        for m, states in sorted(per_model.items()):
            print("SUMMARY: " + argv[1] + ": " + SK.headline(m, controls, states))
        if not per_model:       # zbgc: its two controls are its claim (zbg's premise)
            print("SUMMARY: " + argv[1] + ": " + SK.headline(
                "H-BGDEPTH (dword 16 is the background depth)", controls,
                [None if v is None else bool(v) for v in controls.values()]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
