#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r35-o0b's scorer (Q073), the corrected rerun of r35-o0 (E1143), frozen before the
run. Every verdict rule comes from kit/scorekit.py, the kept files are read through
kit/kitscore.py (byte copies of resgx545 204501aac415, pinned in FROZEN.commits). Standard
library only.

  score.py o KEPT_DIR [ROOTS...]   CONTROL, READING, ROW, SUMMARY lines and the Q073 RULE (exit 0)
  score.py q073 ROOT               Q073's retire rule alone over the attempt ROOT (ROOT/o)
  score.py gate STAGE ROOTS...     exit 0 (one stage, not gated)
  score.py premise STAGE KEPT_DIR  STOP lines and exit 1 when a control has no reading

Images: a probe row's `row Y:` lines, H lines of W dwords (W = H = the row's --width), else no
image. BG (gen/constants.txt) is the background 0xff203040; a pixel is "kept" (non-background)
when it differs from BG. Every expected value comes from this session's own rows: the image of
the P row's group's A' row (A), and the images of every row before that A' row (EARLIER).

Controls (fixed by construction):
  A' 64 x 64 (bins/a.bin)  PASS iff pixel (0, 0) is BG, some pixel is not, and every kept pixel
      (x, y) is (pa0 & 0xffff0000) | (pa1 >> 16), pa = (c + 0.5) * 2 / 64 - 1 (E081).
  A' 128 x 128             the same with at least 98 % of the kept pixels A'(x, y): E1143 found
      1 to 30 of 4284 pixels (4 x 4 blocks) holding another pixel's value, a hardware reading.
  K                        every kept pixel 0xff00ff00 (and (0, 0) BG, some pixel kept).
  c1 P (after K)           PASS iff some pixel is kept and every kept pixel is 0xff00ff00.
A P row is gated by c1's four controls, c0's A' control of its A's size and its own group's A'
control (r35-o0 gated every row on c0a-a128: E1143's void).

Models (fit: E1143's post hoc readings, data:render/closing-r35-o0/fold/posthoc.out; every P row
here is held out). Per kept pixel p = (x, y) with value v: "A at d" when v = A(p + d) for an
offset d (A's pixel holding v, minus p; A injective, so d is unique); "EARLIER" when v is not a
value of A but a kept value of a row before the group's A' row; "NEW" otherwise.
  h1 H-OFFSETS   held iff some pixel is kept, at least one reads A, every A offset is in
                 OFFSETS64 and no pixel is NEW; else FAILED.
     H-SAMEPIX   held iff some pixel is kept and every pixel is A at (0, 0); else FAILED.
     H-OTHER     held iff both above are FAILED.
  h2 H-SIZENONE  held iff no pixel is kept (a 64 x 64 pass-through after a 128 x 128 job);
     H-SIZEKEEP  held iff some pixel is kept.
  h3 H-OFFSETS128 held iff some pixel reads A and every A offset is in OFFSETS128; FAILED iff an
                 A offset is outside it; cannot tell when no pixel reads A (NEW and EARLIER
                 pixels are counted, not judged: E1143's h3a had 240 NEW).
     H-SAMEPIX   the same with the offsets {(0, 0)}.
  h4 H-RESETKEEP held iff some pixel is kept and every kept value is a value of A;
     H-RESETCLEAR held iff no kept value is a value of A.
  h5 H-FILLREPLACE held iff some pixel is kept and every kept pixel is the fill's colour;
     H-TRIONLY   held iff some pixel is kept and every kept value is a value of A; cannot tell
                 for both with no kept pixel.
A row with no kept pixel is cannot tell for h1 and h3's models.

Q073 RULE, frozen against the line "what does o0 hold at the start of an opaque pass's pixel
shader?" and the body's "after a job ... of a different size":
  (a) SAME SIZE: DECIDED iff c1 and every h1 group's A' control passed, at least three of the
      four h1 rows (h1a-d) are decided, and H-OFFSETS is held on every decided one
      (H-SAMEPIX then FAILED on at least one: else the answer is H-SAMEPIX's).
  (b) OTHER SIZE: DECIDED iff both h2 rows are decided under H-SIZENONE / H-SIZEKEEP the same
      way, and H-OFFSETS128 is held on every decided h3 row (at least one).
  RETIRE-CAPABLE iff (a) and (b); else NARROW, naming what was decided. h4, h5 (the lifetime)
  and the counts (which pixels keep it, R35-2 a) are printed, not part of the rule."""
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
E417_64 = (390, 450)
A128_SHARE = 0.98


def constants():
    out = {}
    for ln in open(os.path.join(KP, "gen", "constants.txt")).read().splitlines():
        k, _, v = ln.partition("=")
        out[k] = v
    return out


def offsets(s):
    return frozenset(tuple(int(t) for t in p.split(",")) for p in s.split(";"))


C = constants()
KCOL, BG, FILL = (int(C[k], 16) for k in ("K", "BG", "FILL"))
OFF64, OFF128 = offsets(C["OFFSETS64"]), offsets(C["OFFSETS128"])
CLAIMS = {
    "H-OFFSETS": "o0 at the start of the opaque pass holds an earlier job's o0 at the same pixel or "
                 "at a fixed offset (E1143's set), or a value of a job further back",
    "H-SAMEPIX": "o0 holds the previous job's o0 at the same pixel",
    "H-OTHER": "o0 holds neither",
    "H-SIZENONE": "a 64 x 64 pass-through after a 128 x 128 job keeps no pixel",
    "H-SIZEKEEP": "a 64 x 64 pass-through after a 128 x 128 job keeps some pixel",
    "H-OFFSETS128": "a 128 x 128 pass-through after a 64 x 64 job reads it at E1143's offsets",
    "H-RESETKEEP": "a debugfs reset between keeps the previous job's o0",
    "H-RESETCLEAR": "a debugfs reset between leaves none of the previous job's o0",
    "H-FILLREPLACE": "the t10 fill between replaces it with the fill's colour",
    "H-TRIONLY": "the previous triangle's o0 survives the t10 fill between",
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
        good = sum(1 for (x, y), v in nb.items() if v == f_a(x, y, n))
        return good == len(nb) if n == 64 else good >= A128_SHARE * len(nb)
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
def a_row_of(tab, i):
    """The A' row of the P row at index i: the nearest row before it in its group."""
    g = tab[i]["name"].split("-")[0]
    for j in range(i - 1, -1, -1):
        if tab[j]["name"].split("-")[0] == g and role(tab[j]) == "a":
            return tab[j]
    return None


def classify(nb, a_img, earlier):
    """{pixel: ("A", d) | ("EARLIER", None) | ("NEW", None)}."""
    pos = {}
    for p, v in nonbg(a_img).items():
        pos.setdefault(v, p)
    out = {}
    for p, v in nb.items():
        if v in pos:
            q = pos[v]
            out[p] = ("A", (q[0] - p[0], q[1] - p[1]))
        elif v in earlier:
            out[p] = ("EARLIER", None)
        else:
            out[p] = ("NEW", None)
    return out


def states(g, nb, cls, a_img):
    a_offs = [d for k, d in cls.values() if k == "A"]
    new = any(k == "NEW" for k, _ in cls.values())
    vals = set(nonbg(a_img).values())
    if g == "h1":
        if not nb:
            return {"H-OFFSETS": None, "H-SAMEPIX": None, "H-OTHER": None}
        off = bool(a_offs) and all(d in OFF64 for d in a_offs) and not new
        same = len(a_offs) == len(nb) and all(d == (0, 0) for d in a_offs)
        return {"H-OFFSETS": off, "H-SAMEPIX": same, "H-OTHER": not off and not same}
    if g == "h2":
        return {"H-SIZENONE": not nb, "H-SIZEKEEP": bool(nb)}
    if g == "h3":
        if not a_offs:
            return {"H-OFFSETS128": None, "H-SAMEPIX": None}
        return {"H-OFFSETS128": all(d in OFF128 for d in a_offs),
                "H-SAMEPIX": all(d == (0, 0) for d in a_offs)}
    if g == "h4":
        return {"H-RESETKEEP": bool(nb) and all(v in vals for v in nb.values()),
                "H-RESETCLEAR": not any(v in vals for v in nb.values())}
    if not nb:
        return {"H-FILLREPLACE": None, "H-TRIONLY": None}
    return {"H-FILLREPLACE": all(v == FILL for v in nb.values()),
            "H-TRIONLY": all(v in vals for v in nb.values())}


def score(d):
    """(lines, per-model row states {model: {row: state}}, controls, counts {row: N})."""
    tab = K.table(KP, STAGE)
    cases = K.rows(d, "cases.tsv")
    preds = K.predictions(KP, STAGE)
    names = [r["name"] for r in tab]
    imgs = {r["name"]: row_image(r, cases, d) for r in tab if role(r) in ("a", "k", "p")}
    ctl, lines = controls(tab, imgs)
    c1 = {k: v for k, v in ctl.items() if group(k) == "c1"}
    per, counts = {}, {}
    for i, r in enumerate(tab):
        n = r["name"]
        if r["set"] != "heldout":
            continue
        g = group(n)
        a = a_row_of(tab, i)
        size_a = opt(a, "--width")
        grp = dict(c1)
        grp["c0a-a%d" % size_a] = ctl.get("c0a-a%d" % size_a)
        grp[a["name"]] = ctl.get(a["name"])
        gt = SK.gate(grp)
        p_img, a_img = imgs.get(n), imgs.get(a["name"])
        if p_img is None or a_img is None:
            st = {m: None for m in preds[n][next(iter(preds[n]))]}
            lines.append(f"READING {n}: no image ({'P' if p_img is None else 'A'})")
        else:
            earlier = set()
            for j in range(names.index(a["name"])):
                im = imgs.get(names[j])
                if im is not None:
                    earlier |= set(nonbg(im).values())
            nb = nonbg(p_img)
            counts[n] = len(nb)
            cls = classify(nb, a_img, earlier)
            offs = {}
            for k, dd in cls.values():
                key = f"A{dd}" if k == "A" else k
                offs[key] = offs.get(key, 0) + 1
            lines.append(f"READING {n}: {len(nb)} kept pixels of {len(p_img)} (E417 at 64 x 64: "
                         f"{E417_64[0]} to {E417_64[1]} of 1062); after {a['name']}: "
                         + (", ".join(f"{k} {c}" for k, c in sorted(offs.items(), key=lambda kv: -kv[1]))
                            or "none")
                         + (f"; fill colour {sum(1 for v in nb.values() if v == FILL)}"
                            if g == "h5" else ""))
            st = states(g, nb, cls, a_img)
        for q in preds[n]:
            for m, tok in sorted(preds[n][q].items()):
                s = SK.gated(gt, st.get(m))
                per.setdefault(m, {})[n] = s
                lines.append(f"ROW {n} ({r['set']}) {m}: frozen {tok}: {word(s)}"
                             + ("" if gt.ok else "; gate: " + "; ".join(gt.problems)))
    for m in sorted(per):
        lines.append(f"SUMMARY: {STAGE}: {m}: " + SK.headline(CLAIMS[m], ctl, list(per[m].values())))
    return lines, per, ctl, counts


def rule(per, ctl, counts):
    """Q073 RULE (the docstring)."""
    out = []
    h1 = sorted(n for n in per.get("H-OFFSETS", {}))
    h1_ctl = {k: v for k, v in ctl.items() if group(k) in ("c1", "h1") or k == "c0a-a64"}
    ctl_a = all(v is True for v in h1_ctl.values())
    dec = [n for n in h1 if per["H-OFFSETS"][n] is not None]
    off_all = bool(dec) and all(per["H-OFFSETS"][n] is True for n in dec)
    same_all = bool(dec) and all(per["H-SAMEPIX"][n] is True for n in dec)
    a_ok = ctl_a and len(h1) == 4 and len(dec) >= 3 and (off_all or same_all)
    a_which = "H-SAMEPIX" if same_all else "H-OFFSETS"
    out.append(f"Q073 RULE (a) same size: controls {'passed' if ctl_a else 'not all passed'}; "
               f"h1 rows decided {len(dec)} of {len(h1)}; "
               + "; ".join(f"{m} {SK.tally(per[m].values())}"
                           for m in ("H-OFFSETS", "H-SAMEPIX", "H-OTHER"))
               + (f": DECIDED, {a_which}" if a_ok else ": not decided"))
    h2 = sorted(per.get("H-SIZENONE", {}))
    none2 = [per["H-SIZENONE"][n] for n in h2]
    b2 = len(h2) == 2 and none2[0] is not None and none2[0] == none2[1]
    h3 = sorted(per.get("H-OFFSETS128", {}))
    d3 = [n for n in h3 if per["H-OFFSETS128"][n] is not None]
    b3 = bool(d3) and all(per["H-OFFSETS128"][n] is True for n in d3)
    b_ok = b2 and b3
    out.append(f"Q073 RULE (b) other size: h2 H-SIZENONE {SK.tally(none2)}; h3 decided "
               f"{len(d3)} of {len(h3)}, H-OFFSETS128 {SK.tally(per['H-OFFSETS128'][n] for n in h3)}"
               f", H-SAMEPIX {SK.tally(per['H-SAMEPIX'][n] for n in h3)}"
               + (f": DECIDED, {'H-SIZENONE' if none2[0] else 'H-SIZEKEEP'} and H-OFFSETS128"
                  if b_ok else ": not decided"))
    life = []
    for m in ("H-RESETKEEP", "H-RESETCLEAR", "H-FILLREPLACE", "H-TRIONLY"):
        life.append(f"{m} {SK.tally(per.get(m, {}).values())}")
    out.append("Q073 LIFETIME (printed, not the rule): " + "; ".join(life))
    out.append("Q073 COUNT (printed, not the rule; R35-2): " + ", ".join(
        f"{n} {c}" for n, c in sorted(counts.items())))
    if a_ok and b_ok:
        out.append("Q073 RULE: RETIRE-CAPABLE ((a) and (b) decided)")
        what = ("the o0 the previous job's shader wrote at the same pixel" if a_which == "H-SAMEPIX"
                else "the o0 an earlier job's shader wrote, at the same pixel or at one of the "
                     "offsets (dx, dy) " + ", ".join(str(d) for d in sorted(OFF64))
                     + " of the previous job, or a value of a job further back")
        size = ("after a 128 x 128 job a 64 x 64 pass-through keeps nothing" if none2[0] else
                "after a 128 x 128 job a 64 x 64 pass-through keeps some pixels")
        out.append(f"Q073 ANSWER [HW]: at the start of an opaque pass's pixel shader o0 holds {what}"
                   f", on the pixels that keep one, and the background on the rest; {size}, and "
                   "a 128 x 128 pass-through after a 64 x 64 job reads it at the offsets "
                   + ", ".join(str(d) for d in sorted(OFF128)))
    else:
        got = [w for w, ok in (("(a)", a_ok), ("(b)", b_ok)) if ok]
        why = [w for w, ok in (("(a)", a_ok), ("(b)", b_ok)) if not ok]
        out.append(f"Q073 RULE: NARROW: {', '.join(got) or 'nothing'} decided; open: "
                   f"{', '.join(why)}")
    out.append("Q073 NOT THE LINE: which pixels keep it (the count; R35-2), why these offsets "
               "(slots, tiles), the translucent pass; the lead confirms")
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
