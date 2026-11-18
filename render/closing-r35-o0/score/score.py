#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r35-o0's scorer (Q073), frozen before the run. Every verdict rule comes from
kit/scorekit.py, the kept files are read through kit/kitscore.py (byte copies of resgx545
eea6d2ab8f45, pinned in FROZEN.commits). Standard library only.

  score.py o KEPT_DIR [ROOTS...]   CONTROL, READING, ROW, SUMMARY lines and the Q073 RULE (exit 0)
  score.py q073 ROOT               Q073's retire rule alone over the attempt ROOT (ROOT/o)
  score.py gate STAGE ROOTS...     exit 0 (one stage, not gated)
  score.py premise STAGE KEPT_DIR  STOP lines and exit 1 when a control has no reading

Images: a probe row's `row Y:` lines, H lines of W dwords (W = H = the row's --width), else no
image. BG (gen/constants.txt) is the probe triangle's background 0xff203040; a pixel is
"non-background" when it differs from BG. Every expected value of a hypothesis comes from this
session's own rows: the image of the P row's group's A' row (two rows before in h5, one before
elsewhere). Controls are fixed by construction:
  A' (bins/a.bin, size n)  PASS iff pixel (0, 0) is BG, at least one pixel is not, and every
      non-background pixel (x, y) is (pa0 & 0xffff0000) | (pa1 >> 16) with pa = (c + 0.5) * 2 /
      n - 1 as singles (E081); FAILED otherwise; cannot tell without an image. This is the
      decoder's known-value check (D1): a P pixel's value names the pixel it came from only
      through its group's A' image, and only when that A' control passed.
  K  (bins/k.bin)          the same with every non-background pixel 0xff00ff00.
  c1 P (after K, noreset)  PASS iff at least one pixel is not BG and every such pixel is K's
      constant (E417's form: the pass-through shows the previous colour on part of the
      triangle); FAILED iff one is something else; cannot tell with none (P's form untested).
Every h row is gated by c0's two A' controls, c1's four controls and its own group's A' control
(cannot tell when any of them did not pass).

Per P row of h1-h3 (A = its group's A' image, n_A its size; N = the P row's non-background
pixels; a row with no N is cannot tell for every model). For each model, the prediction of
pixel (x, y) is a value of A, and the model is held iff every pixel of N reads its prediction
(FAILED otherwise):
  H-SAMEPIX   A(x, y) (the same pixel, inside A's target)
  H-SLOTMAP   A(M(x, y)) with M fitted on h1a-p (the fit row): M(x, y) = the pixel of A whose
              value h1a-p reads at (x, y). With an alien value in the fit (not a value of h1a-a)
              or no pixel in it, no map: cannot tell everywhere. M the identity: H-SLOTMAP is
              H-SAMEPIX (not a rival): cannot tell everywhere. A pixel outside M's domain has no
              prediction (FAILED). On the fit row itself: held iff every N value is a value of
              A and M is not the identity.
  H-TILESLOT  (h2, h3) A at the pixel of the same tile index: tiles of 32 x 16 numbered row by
              row, n / 32 to a row; tile t of the P target -> tile t of A's (none: FAILED) [infer]
  H-OTHER     held iff none of the models above that apply (H-SLOTMAP only with a non-identity
              map) is held.
h4 (a reset between): H-RESETKEEP held iff N is not empty and every N value is a value of A;
H-RESETCLEAR held iff no N value is a value of A (N empty included); FAILED otherwise.
h5 (the t10 fill between): H-FILLREPLACE held iff every N value is the fill's colour, H-TRIONLY
iff every N value is a value of A; FAILED otherwise; cannot tell with N empty.
The count of N per row is printed against E417's (390 to 450 of 1062 at 64 x 64): a reading,
never a verdict.

Q073 RULE, frozen against the question line "what does o0 hold at the start of an opaque pass's
pixel shader?" and the body's "after a job ... of a different size":
  CONTROLS  every control of the stage passed (c0, c1 both replicates, every group's A').
  (a) SAME SIZE: DECIDED iff the held-out h1 rows (h1b-p, h1c-p) are both decided and the same
      one of H-SAMEPIX, H-SLOTMAP is held on both (the answer: what o0 holds).
  (b) OTHER SIZE: DECIDED iff at least one of h2a-p, h2b-p and one of h3a-p, h3b-p is decided
      and exactly one of H-SAMEPIX, H-TILESLOT, H-SLOTMAP is held on every decided h2/h3 row
      (two held on all of them: not separated, not decided).
  RETIRE-CAPABLE iff CONTROLS, (a) and (b); else NARROW, naming what was decided. The answer: at
  the start of the opaque pass, o0 holds the previous job's o0 at the pixel (a) names (and (b)
  across sizes) on the pixels that keep it, the background on the rest. h4 and h5 (the
  lifetime: a reset, a fill between) and the count (which pixels keep it: E417's 426) are
  printed with the answer, not part of the rule (R35-2 a: the count goes to the body)."""
import os
import re
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

STAGE = "o"
REQUIRED = {STAGE: (".txt", "cases.tsv", "void.tsv", "readings.tsv")}
GATES = {}
TILE_W, TILE_H = 32, 16
E417_64 = (390, 450)


def constants():
    out = {}
    for ln in open(os.path.join(KP, "gen", "constants.txt")).read().splitlines():
        k, _, v = ln.partition("=")
        out[k] = v
    return out


C = constants()
KCOL, BG, FILL = (int(C[k], 16) for k in ("K", "BG", "FILL"))
CLAIMS = {
    "H-SAMEPIX": "o0 at the start of the opaque pass holds the previous job's o0 at the same pixel",
    "H-SLOTMAP": "o0 holds the previous job's o0 of another pixel, by a map that repeats",
    "H-TILESLOT": "after a job of another size, o0 holds the previous job's o0 at the pixel of the "
                  "same tile index",
    "H-OTHER": "o0 holds neither the same pixel's, a repeating map's nor the tile slot's value",
    "H-RESETKEEP": "a debugfs reset between keeps the previous job's o0",
    "H-RESETCLEAR": "a debugfs reset between leaves none of the previous job's o0",
    "H-FILLREPLACE": "the t10 fill between replaces it with the fill's colour",
    "H-TRIONLY": "the previous triangle's o0 survives the t10 fill between",
}
ANSWER = {
    "H-SAMEPIX": "the o0 the previous job's shader wrote at the same pixel",
    "H-SLOTMAP": "the o0 the previous job's shader wrote at another pixel, by a map that repeats "
                 "between jobs (an instance slot reused [infer])",
    "H-TILESLOT": "the o0 the previous job wrote at the pixel of the same 32 x 16 tile index",
}


def producible(row):
    a = row["args"].split()
    return {"pixels"} if a[:1] == ["probe"] and "--pixels" in a else set()


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for r in K.table(KP, stage):
        if r["name"] in cases:
            K.text(d, r["name"] + ".txt")


def word(s):
    return "held" if s is True else "FAILED" if s is False else "cannot tell"


def cword(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


# ---- rows and images ------------------------------------------------------------------------
ROWL = re.compile(r"^probe \S+: row (\d+): ([0-9a-fA-F ]+)$", re.M)


def opt(row, name):
    a = row["args"].split()
    return int(a[a.index(name) + 1]) if name in a else None


def role(row):
    a = row["args"]
    if a == "fill":
        return "f"
    m = re.search(r'/bins/([akp])\.bin"?$', a)
    return m.group(1) if m else None


def group(name):
    return name.split("-")[0][:-1]


def image(text, n):
    """{(x, y): value} of n `row Y:` lines of n dwords, or None."""
    rows = {}
    for m in ROWL.finditer(text or ""):
        rows[int(m.group(1))] = [int(t, 16) for t in m.group(2).split()]
    if sorted(rows) != list(range(n)) or any(len(v) != n for v in rows.values()):
        return None
    return {(x, y): v for y in range(n) for x, v in enumerate(rows[y])}


def row_image(row, cases, d):
    c = cases.get(row["name"])
    if c is None or not K.completed(c):
        return None
    return image(K.text(d, row["name"] + ".txt"), opt(row, "--width"))


def fbits(f):
    return struct.unpack("<I", struct.pack("<f", f))[0]


def f_a(x, y, n):
    """A' at pixel (x, y) of an n x n target (gen/make.py, E081)."""
    return (fbits((x + 0.5) * 2.0 / n - 1.0) & 0xFFFF0000) | (fbits((y + 0.5) * 2.0 / n - 1.0) >> 16)


def nonbg(img):
    return {p: v for p, v in img.items() if v != BG}


# ---- controls -----------------------------------------------------------------------------
def control_state(row, img):
    if img is None:
        return None
    nb = nonbg(img)
    r, n = role(row), opt(row, "--width")
    if r == "p":
        if not nb:
            return None
        return all(v == KCOL for v in nb.values())
    if img[(0, 0)] != BG or not nb:
        return False
    if r == "a":
        return all(v == f_a(x, y, n) for (x, y), v in nb.items())
    return all(v == KCOL for v in nb.values())


def controls(tab, imgs):
    out, lines = {}, []
    for r in tab:
        if r["set"] != "control":
            continue
        n = r["name"]
        img = imgs.get(n)
        st = control_state(r, img)
        out[n] = st
        what = ("no image" if img is None else
                f"{len(nonbg(img))} non-background pixels" +
                ("" if role(r) != "a" else
                 f", {sum(1 for (x, y), v in nonbg(img).items() if v == f_a(x, y, opt(r, '--width')))}"
                 " of them A'(x, y)"))
        lines.append(f"CONTROL {n}: {what}: {cword(st)}")
    return out, lines


# ---- the models ---------------------------------------------------------------------------
def tile_map(x, y, n_p, n_a):
    """The pixel of A (n_a) with the tile index of (x, y) in the P target (n_p), or None."""
    t = (y // TILE_H) * (n_p // TILE_W) + x // TILE_W
    per = n_a // TILE_W
    ty, tx = divmod(t, per)
    if ty >= n_a // TILE_H:
        return None
    return tx * TILE_W + x % TILE_W, ty * TILE_H + y % TILE_H


def fit_map(p_img, a_img):
    """M fitted on the fit row: {(x, y): A's pixel}, or None (no pixel, or an alien value)."""
    if p_img is None or a_img is None:
        return None
    pos = {v: p for p, v in nonbg(a_img).items()}
    nb = nonbg(p_img)
    if not nb or any(v not in pos for v in nb.values()):
        return None
    return {p: pos[v] for p, v in nb.items()}


def identity(m):
    return m is not None and all(k == v for k, v in m.items())


def consistent(nb, a_img, pred):
    """Every pixel of nb reads A at pred(x, y) (a non-background value of A)."""
    for p, v in nb.items():
        q = pred(p)
        if q is None or a_img.get(q, BG) == BG or a_img[q] != v:
            return False
    return True


def cat_states(g, nb, a_img, n_p, n_a, fmap, fit_row):
    """{model: True/False/None} of an h1-h3 P row."""
    models = ["H-SAMEPIX", "H-SLOTMAP", "H-OTHER"] + (["H-TILESLOT"] if g in ("h2", "h3") else [])
    if not nb:
        return {m: None for m in models}
    out = {"H-SAMEPIX": consistent(nb, a_img, lambda p: p)}
    if fit_row:
        pos = {v for v in nonbg(a_img).values()}
        out["H-SLOTMAP"] = (all(v in pos for v in nb.values()) and fmap is not None
                            and not identity(fmap))
    elif fmap is None or identity(fmap):
        out["H-SLOTMAP"] = None
    else:
        out["H-SLOTMAP"] = consistent(nb, a_img, lambda p: fmap.get(p))
    if g in ("h2", "h3"):
        out["H-TILESLOT"] = consistent(nb, a_img, lambda p: tile_map(p[0], p[1], n_p, n_a))
    named = [v for k, v in out.items() if v is not None]
    out["H-OTHER"] = not any(named)
    return out


def life_states(g, nb, a_img):
    vals = set(nonbg(a_img).values())
    if g == "h4":
        return {"H-RESETKEEP": bool(nb) and all(v in vals for v in nb.values()),
                "H-RESETCLEAR": not any(v in vals for v in nb.values())}
    if not nb:
        return {"H-FILLREPLACE": None, "H-TRIONLY": None}
    return {"H-FILLREPLACE": all(v == FILL for v in nb.values()),
            "H-TRIONLY": all(v in vals for v in nb.values())}


def a_row_of(tab, i):
    """The A' row of the P row at index i: the nearest row before it in its group."""
    g = tab[i]["name"].split("-")[0]
    for j in range(i - 1, -1, -1):
        if tab[j]["name"].split("-")[0] == g and role(tab[j]) == "a":
            return tab[j]
    return None


def score(d):
    """(lines, per-model row states {model: {row: state}}, controls, counts {row: N})."""
    tab = K.table(KP, STAGE)
    cases = K.rows(d, "cases.tsv")
    preds = K.predictions(KP, STAGE)
    imgs = {r["name"]: row_image(r, cases, d) for r in tab if role(r) in ("a", "k", "p")}
    ctl, lines = controls(tab, imgs)
    base = {k: v for k, v in ctl.items() if group(k) in ("c0", "c1")}
    fit_name = next(r["name"] for r in tab if r["set"] == "fit")
    fit_a = a_row_of(tab, [r["name"] for r in tab].index(fit_name))
    fmap = fit_map(imgs.get(fit_name), imgs.get(fit_a["name"]))
    lines.append("FIT h1a-p: " + ("no map (no pixel, an alien value, or no image)" if fmap is None
                                  else f"the identity on {len(fmap)} pixels" if identity(fmap)
                                  else f"a map on {len(fmap)} pixels, "
                                       f"{sum(1 for k, v in fmap.items() if k != v)} moved"))
    per, counts = {}, {}
    for i, r in enumerate(tab):
        n = r["name"]
        if r["set"] not in ("fit", "heldout"):
            continue
        g = group(n)
        a = a_row_of(tab, i)
        p_img, a_img = imgs.get(n), imgs.get(a["name"])
        grp = dict(base)
        grp[a["name"]] = ctl.get(a["name"])
        gt = SK.gate(grp)
        if p_img is None or a_img is None:
            st = {m: None for m in preds[n][next(iter(preds[n]))]}
            lines.append(f"READING {n}: no image ({'P' if p_img is None else 'A'})")
        else:
            nb = nonbg(p_img)
            counts[n] = len(nb)
            vals = set(nonbg(a_img).values())
            same = sum(1 for p, v in nb.items() if a_img.get(p) == v)
            ina = sum(1 for v in nb.values() if v in vals)
            lines.append(f"READING {n}: {len(nb)} non-background pixels of {len(p_img)} (E417 at "
                         f"64 x 64: {E417_64[0]} to {E417_64[1]} of 1062); {same} read A'(x, y) "
                         f"of {a['name']}, {ina} a value of it, {len(nb) - ina} another value"
                         + (f"; fill colour {sum(1 for v in nb.values() if v == FILL)}"
                            if g == "h5" else ""))
            if g in ("h4", "h5"):
                st = life_states(g, nb, a_img)
            else:
                st = cat_states(g, nb, a_img, opt(r, "--width"), opt(a, "--width"), fmap,
                                r["set"] == "fit")
        for q in preds[n]:
            for m, tok in sorted(preds[n][q].items()):
                s = SK.gated(gt, st.get(m))
                per.setdefault(m, {})[n] = s
                lines.append(f"ROW {n} ({r['set']}) {m}: frozen {tok}: {word(s)}"
                             + ("" if gt.ok else "; gate: " + "; ".join(gt.problems)))
    for m in sorted(per):
        held = [v for n, v in per[m].items() if not n.startswith("h1a")]
        if held:
            lines.append(f"SUMMARY: {STAGE}: {m}: " + SK.headline(CLAIMS[m], ctl, held))
    return lines, per, ctl, counts


def rule(per, ctl, counts):
    """Q073 RULE (the docstring)."""
    out = []
    ctl_ok = bool(ctl) and all(v is True for v in ctl.values())
    out.append(f"Q073 RULE CONTROLS: {sum(v is True for v in ctl.values())} of {len(ctl)} passed"
               + ("" if ctl_ok else ": " + ", ".join(f"{k} {cword(v)}" for k, v in sorted(ctl.items())
                                                       if v is not True)))
    h1 = ["h1b-p", "h1c-p"]
    a_held = [m for m in ("H-SAMEPIX", "H-SLOTMAP")
              if all(per.get(m, {}).get(n) is True for n in h1)]
    a_dec = all(per.get("H-SAMEPIX", {}).get(n) is not None for n in h1)
    a_ok = a_dec and len(a_held) == 1
    out.append("Q073 RULE (a) same size: h1b-p, h1c-p "
               + "; ".join(f"{m} {SK.tally(per.get(m, {}).get(n) for n in h1)}"
                           for m in ("H-SAMEPIX", "H-SLOTMAP", "H-OTHER"))
               + (f": DECIDED, {a_held[0]}" if a_ok else
                  ": not decided (" + ("a held-out h1 row is not decided" if not a_dec else
                                       "neither H-SAMEPIX nor H-SLOTMAP holds on both"
                                       if not a_held else "both hold") + ")"))
    size = ["h2a-p", "h2b-p", "h3a-p", "h3b-p"]
    dec = [n for n in size if per.get("H-SAMEPIX", {}).get(n) is not None]
    b_cand = [m for m in ("H-SAMEPIX", "H-TILESLOT", "H-SLOTMAP")
              if dec and all(per.get(m, {}).get(n) is True for n in dec)]
    both_sides = any(n.startswith("h2") for n in dec) and any(n.startswith("h3") for n in dec)
    b_ok = both_sides and len(b_cand) == 1
    out.append(f"Q073 RULE (b) other size: decided {', '.join(dec) or 'none'}; "
               + "; ".join(f"{m} {SK.tally(per.get(m, {}).get(n) for n in size)}"
                           for m in ("H-SAMEPIX", "H-TILESLOT", "H-SLOTMAP", "H-OTHER"))
               + (f": DECIDED, {b_cand[0]}" if b_ok else
                  ": not decided (" + ("no decided row in h2 or in h3" if not both_sides else
                                       "no model holds on every decided row" if not b_cand else
                                       "not separated: " + ", ".join(b_cand)) + ")"))
    life = []
    for n, ms in (("h4a-p", ("H-RESETKEEP", "H-RESETCLEAR")), ("h4b-p", ("H-RESETKEEP", "H-RESETCLEAR")),
                  ("h5a-p", ("H-FILLREPLACE", "H-TRIONLY"))):
        held = [m for m in ms if per.get(m, {}).get(n) is True]
        life.append(f"{n} {', '.join(held) or 'none held'}")
    out.append("Q073 LIFETIME (printed, not the rule): " + "; ".join(life))
    out.append("Q073 COUNT (printed, not the rule; R35-2): " + ", ".join(
        f"{n} {c}" for n, c in sorted(counts.items())))
    if ctl_ok and a_ok and b_ok:
        out.append("Q073 RULE: RETIRE-CAPABLE (controls, (a) and (b) decided)")
        tail = ("" if b_cand[0] == a_held[0] else
                f"; after a job of another size {ANSWER[b_cand[0]]}")
        out.append(f"Q073 ANSWER [HW]: at the start of an opaque pass's pixel shader o0 holds "
                   f"{ANSWER[a_held[0]]}{tail}, on the pixels that keep it, and the background on "
                   "the rest (h1-h3, both replicates, every control)")
    else:
        why = [w for w, ok in (("controls", ctl_ok), ("(a)", a_ok), ("(b)", b_ok)) if not ok]
        got = [w for w, ok in (("(a)", a_ok), ("(b)", b_ok)) if ok]
        out.append(f"Q073 RULE: NARROW: {', '.join(got) or 'nothing'} decided; open: "
                   f"{', '.join(why)}")
    out.append("Q073 NOT THE LINE: which pixels keep it (the count, E417's 426; R35-2), the "
               "translucent pass, a previous job of another program form; the lead confirms")
    return out


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        print(f"gate {argv[2]}: open (not gated)")
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) == 3 and argv[1] == "q073":
        _, per, ctl, counts = score(os.path.join(argv[2], STAGE))
        print("\n".join(rule(per, ctl, counts)))
        return 0
    if len(argv) >= 3 and argv[1] == STAGE:
        lines, per, ctl, counts = score(argv[2])
        print("\n".join(lines + rule(per, ctl, counts)))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
