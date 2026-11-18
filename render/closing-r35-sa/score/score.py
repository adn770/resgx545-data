#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r35-sa's scorer, frozen before the run (closing29/plan/rank-round35.md sections 1,
3.2 and 3.4). Every verdict rule comes from kit/scorekit.py, the kept files are read through
kit/kitscore.py (byte copies of resgx545 eea6d2ab8f45, pinned in FROZEN.commits). Standard
library only.

  score.py a KEPT_DIR [ROOTS...]   CONTROL, FORM, READING, ROW, SUMMARY lines and the Q129 RULE
  score.py t KEPT_DIR [ROOTS...]   the same for stage t and the Q193 RULE
  score.py q129 ROOT               Q129's retire rule alone over the attempt ROOT (ROOT/a)
  score.py q193 ROOT               Q193's narrowing rule alone over ROOT (ROOT/t)
  score.py gate STAGE ROOTS...     exit 0 (no stage is gated)
  score.py premise STAGE KEPT_DIR  STOP lines and exit 1 when a control has no reading

Readings, from the kept texts only; every expected value is this session's own (a program's
constants, a marker its row wrote, the output of the row before in this attempt, the positions
of this attempt's fit rows):
  - a probe's pixels: the 32 `probe X: row Y: P0 .. P63` lines t30's --pixels prints, pixel
    index i = y * 64 + x; a row's pixels are read only when they agree with its o0 line (the one
    value 2048 times, or each of the up to four values `o0 mixed` names with its count and the
    `other` count the rest), else the row cannot tell;
  - the scratch dwords (`probe X: scratch +0xOFF 0xV`); controls: readings.tsv sa, top, rows.

D1 (form controls, gating every row of their form): c0 (K, every decoded pixel K3) and c1
(--coords, o0 = pa0: every pixel i decodes to (y << 16) | x) gate the position decode of every W
row; c2 (W_5, then R_5: R_5 reads the marker in 2048 of 2048) gates every R_5 reading; stage t's
c (T, then U: U reads T's marker in 2048 of 2048) gates every U reading. A failed form control
makes its rows cannot tell ("cannot tell: form control").

Stage a, a W row (fit f0, f1; held out h2..h15, h157) is read when its pixels are, its dwords 0..k-1
are its markers (the in-job readback, sa order) and its most frequent pixel is K1; its odd pixels
are those that are not K1. S0 = f0a's odd positions; d = the one shift (mod 2048) taking S0 onto
f1a's odd positions, if any.
  H-FOUR    held when the odd pixels are exactly 4 per sa written, each marker 4 times, no other
            value; H-OTHERN held when they are not (both on read rows only).
  H-FIXED4  held when the odd positions are S0; H-SHIFT when they are S0 + n d (mod 2048, n the sa
            written); FAILED otherwise (H-SHIFT also when no d exists).
  H-VAR     (second replicates of two-replicate n) held when the positions of each sa written
            differ from the first replicate's, FAILED when they are equal.
  H-UNION   (h157) held when the positions of each of its markers M_1, M_5, M_7 are those of the
            same replicate's W_1 (f1), W_5 (h5) and W_7 (h7) rows.
An R_5 row (p held out, q fit) reads M (its most frequent value is its group's W_5 marker), PREV
(every value is one the row before output, the most frequent the same) or XM (most frequent =
X_1's marker); a frozen M or PREV is held when the reading is in it, FAILED when it is in another
of the three, cannot tell otherwise. Every row is gated by its group's controls.

Q129 RULE, against the question line's two clauses:
  (a) "why do 12 pixels (4 each of three values) ... show those sa values": DECIDED iff c0, c1
      passed, every f and h row is read, H-FOUR holds on every one, S0 has 4 positions, one of
      H-FIXED4 or H-SHIFT holds on every held-out single-n h row, H-UNION holds on both h157
      rows and H-VAR fails on every second replicate; the answer is the positions rule.
  (b) "how long does an sa written by one job stay readable": DECIDED iff the c2, p and q
      controls passed, qa-r reads PREV (E484's form) and exactly one of H-ONEJOB and
      H-UNTILWRITE holds on both p rows.
RETIRE-CAPABLE iff both are DECIDED (R35-3a: the "why" is then the [infer] storage statement and
the mechanism moves to Q098's open "pa_n naming sa_n"); else NARROW, naming the clause(s) decided.

Stage t, a U row (held out t1..t4) with decoded multiset D, its group's T marker m and MK the T
markers written before it in the stage: M (D = {m: 2048}), SPLIT (two or more values, one of them
in MK), LASTJOB (no value in MK), TRI1536 (two values, 1536 and 512 pixels), OLDER (one value of MK,
not m). A frozen M, SPLIT, LASTJOB or TRI1536 is held when D is in it, FAILED otherwise; `!M` held
when D is not M.

Q193 RULE (narrowing, R35-5a): clause (a) per group: t1, t2, t4 DECIDED iff their controls and the
c form controls passed and exactly one of H-LASTWRITER, H-LASTJOB, H-SPLIT holds on every row of
the group; t3 DECIDED as kept (M on both rows) or cleared (H-RESETCLR on both). Clause (b): another
context by construction (every row is its own process, with its own VM and context: t30's
side_init); a power cycle and a module reload stay open. Q193 stays open: NARROW."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

REQUIRED = {s: (".txt", "cases.tsv", "void.tsv", "readings.tsv") for s in ("a", "t")}
GATES = {}
NPIX = 2048
W, H = 64, 32


def constants():
    out = {}
    for ln in open(os.path.join(KP, "gen", "constants.txt")).read().splitlines():
        k, _, v = ln.partition("=")
        out[k] = v
    return out


C = constants()
K1, K2, K3 = (int(C[k], 16) for k in ("K1", "K2", "K3"))
TRI = frozenset(int(v, 16) for v in C["TRI"].split(","))
A_POS = ("H-FIXED4", "H-SHIFT")
B_HYP = ("H-ONEJOB", "H-UNTILWRITE")
T_FULL = ("H-LASTWRITER", "H-LASTJOB", "H-SPLIT")
CLAIMS = {
    "H-FOUR": "exactly 4 pixels per sa written show its marker",
    "H-OTHERN": "another number of odd pixels than 4 per sa written",
    "H-FIXED4": "the same 4 positions for every sa",
    "H-SHIFT": "sa_n's positions are sa0's shifted by n d",
    "H-VAR": "the positions differ between replicates of one sa",
    "H-UNION": "W_157's 12 positions are the union of W_1's, W_5's and W_7's",
    "H-ONEJOB": "a job between that writes another sa replaces sa5 with its output",
    "H-UNTILWRITE": "a job between that writes another sa leaves sa5 as written",
    "H-LASTWRITER": "an unwritten r20 reads the last job that wrote r20, every pixel",
    "H-LASTJOB": "an unwritten r20 reads what the last job left, no r20 marker after a job between",
    "H-SPLIT": "an unwritten r20 reads a split of an r20 marker and other values after a job between",
    "H-TRI1536": "after the t10 triangle an unwritten r20 reads two values in 1536 and 512 pixels",
    "H-RESETCLR": "a debugfs reset replaces r20",
}


def producible(row):
    a = row["args"].split()
    if a[:1] != ["probe"]:
        return set()
    return {"sa", "top"} | ({"rows"} if "--pixels" in a else set())


def word(s):
    return "held" if s is True else "FAILED" if s is False else "cannot tell"


def cword(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n in cases:
        K.text(d, n + ".txt")


def group_of(name):
    return name.split("-")[0][:-1]


def rep_of(name):
    return name.split("-")[0][-1]


# ---- the kept texts ---------------------------------------------------------------------------
O0 = re.compile(r"^probe \S+: o0 (.*)$", re.M)
ROW = re.compile(r"^probe \S+: row (\d+):((?: [0-9a-f]{8}){64})$", re.M)
SCR = re.compile(r"^probe \S+: scratch \+0x([0-9a-f]{3}) 0x([0-9a-f]{8})$", re.M)


def o0_line(text):
    """(listed {value: count}, other count, single) of a probe's o0 line, or None."""
    m = O0.search(text)
    if not m:
        return None
    s = m.group(1)
    one = re.fullmatch(r"0x([0-9a-f]{8}) \((\d+) of (\d+)\)", s)
    if one:
        return {int(one.group(1), 16): int(one.group(2))}, 0, True
    if not s.startswith("mixed "):
        return None
    vals = {int(v, 16): int(c) for v, c in re.findall(r"0x([0-9a-f]{8}) x(\d+)", s)}
    oth = re.search(r"other x(\d+)", s)
    return vals, int(oth.group(1)) if oth else 0, False


def pixels(text):
    """The 2048 pixels (index y * 64 + x) of a --pixels probe, when its 32 rows are whole and
    agree with its o0 line; else None."""
    rows = {}
    for m in ROW.finditer(text):
        y = int(m.group(1))
        if y in rows:
            return None
        rows[y] = [int(v, 16) for v in m.group(2).split()]
    if sorted(rows) != list(range(H)):
        return None
    px = [v for y in range(H) for v in rows[y]]
    o = o0_line(text)
    if o is None:
        return None
    listed, other, single = o
    ms = multiset(px)
    if single:
        return px if ms == listed else None
    if any(ms.get(v) != c for v, c in listed.items()):
        return None
    if sum(c for v, c in ms.items() if v not in listed) != other:
        return None
    return px


def multiset(px):
    out = {}
    for v in px:
        out[v] = out.get(v, 0) + 1
    return out


def scratch(text):
    return {int(o, 16) // 4: int(v, 16) for o, v in SCR.findall(text)}


def top(ms):
    return max(ms.items(), key=lambda kv: (kv[1], -kv[0]))[0] if ms else None


def fmt(ms):
    if ms is None:
        return "no reading"
    items = sorted(ms.items(), key=lambda kv: (-kv[1], kv[0]))
    s = " ".join("0x%08x x%d" % kv for kv in items[:6])
    return s + (" (+%d more values)" % (len(items) - 6) if len(items) > 6 else "")


def where(px, v):
    """The pixel rows y a value occupies, as ranges."""
    ys = sorted({i // W for i, p in enumerate(px) if p == v})
    out, start = [], None
    for k, y in enumerate(ys):
        if start is None:
            start = y
        if k + 1 == len(ys) or ys[k + 1] != y + 1:
            out.append(f"{start}" if start == y else f"{start}-{y}")
            start = None
    return ",".join(out)


def ok_text(row, cases, d):
    c = cases.get(row["name"])
    if c is None or not K.completed(c):
        return None
    return K.text(d, row["name"] + ".txt")


def controls(stage, d):
    preds = K.predictions(KP, stage)
    cases, rds = K.rows(d, "cases.tsv"), K.readings(d)
    out, lines = {}, []
    for r in K.table(KP, stage):
        n = r["name"]
        if r["set"] != "control":
            continue
        want = {q: mv["H-REF"] for q, mv in preds[n].items()}
        c = cases.get(n)
        if c is None or not K.completed(c):
            out[n] = None
            lines.append(f"CONTROL {n}: did not complete ({c['class'] if c else 'not run'}): "
                         "cannot tell")
            continue
        got = rds.get(n, {})
        bad = {q: got.get(q) for q, v in want.items() if got.get(q) != v}
        out[n] = not bad
        lines.append(f"CONTROL {n}: " + (", ".join(f"{q} {got.get(q)}" for q in sorted(want))
                                         if not bad else "differs: " + ", ".join(
                                             f"{q} {v} (frozen {want[q]})"
                                             for q, v in sorted(bad.items())))
                     + f": {cword(out[n])}")
    return out, lines


def row_markers(row):
    """The markers a W, X or T row's program writes, from its file name (gen/make.py's names)."""
    m = re.search(r'/bins/(w|w157|x|t|t8)-([0-9a-f]{8})\.bin', row["args"])
    if not m:
        return None
    kind, base = m.group(1), int(m.group(2), 16)
    if kind == "w157":
        return {n: base | n for n in (1, 5, 7)}
    if kind in ("w", "x"):
        return {base & 0xFF: base}
    if kind == "t":
        return {20: base}
    return {k: base | k for k in range(6)}


# ---- stage a ---------------------------------------------------------------------------------
def form_a(tab, cases, d, ctl):
    """D1 for stage a: {c0..: state, c1..: state, c2..: state} and their lines."""
    out, lines = {}, []
    for r in tab:
        n, g = r["name"], group_of(r["name"])
        if g == "c0":
            t = ok_text(r, cases, d)
            px = pixels(t) if t else None
            st = None if px is None or ctl.get(n) is None else (
                ctl[n] is True and all(v == K3 for v in px))
            out[n] = st
            lines.append(f"FORM {n}: position decode on K3: {fmt(multiset(px)) if px else 'no pixels'}"
                         f": {cword(st)}")
        elif g == "c1":
            t = ok_text(r, cases, d)
            px = pixels(t) if t else None
            bad = None if px is None else sum(1 for i, v in enumerate(px)
                                              if v != ((i // W) << 16 | (i % W)))
            st = None if px is None or ctl.get(n) is None else (ctl[n] is True and bad == 0)
            out[n] = st
            lines.append(f"FORM {n}: position decode on (y << 16) | x: "
                         + ("no pixels" if px is None else f"{bad} of {NPIX} pixels differ")
                         + f": {cword(st)}")
        elif g == "c2" and n.endswith("-r"):
            i = tab.index(r)
            m = row_markers(tab[i - 1])[5]
            t = ok_text(r, cases, d)
            px = pixels(t) if t else None
            st = None if px is None or ctl.get(n) is None or ctl.get(tab[i - 1]["name"]) is None \
                else (ctl[n] is True and ctl[tab[i - 1]["name"]] is True
                      and multiset(px) == {m: NPIX})
            out[n] = st
            lines.append(f"FORM {n}: R_5 right after W_5 reads 0x{m:08x} x2048: "
                         f"{fmt(multiset(px)) if px else 'no pixels'}: {cword(st)}")
    return out, lines


def read_writer(r, cases, d):
    """A W row's {sa n: sorted odd positions}, its odd multiset and pixels; None when not read."""
    t = ok_text(r, cases, d)
    if t is None:
        return None
    px = pixels(t)
    ms = row_markers(r)
    if px is None or ms is None:
        return None
    sc = scratch(t)
    order = sorted(ms)
    if any(sc.get(k) != ms[n] for k, n in enumerate(order)):
        return None
    hist = multiset(px)
    if top(hist) != K1:
        return None
    odd = {i: v for i, v in enumerate(px) if v != K1}
    pos = {n: tuple(sorted(i for i, v in odd.items() if v == ms[n])) for n in order}
    return dict(odd=odd, pos=pos, ms=ms, hist=hist)


def fit_shift(s0, s1):
    if not s0 or len(s0) != len(s1):
        return None
    t1 = set(s1)
    for dd in range(NPIX):
        if {(i + dd) % NPIX for i in s0} == t1:
            return dd
    return None


def shifted(s0, n, dd):
    return tuple(sorted((i + n * dd) % NPIX for i in s0))


def r5_cats(tab, i, cases, d):
    """{'M', 'PREV', 'XM'} of an R_5 row (an empty set: none), or None when not read."""
    r = tab[i]
    t = ok_text(r, cases, d)
    px = pixels(t) if t else None
    if px is None:
        return None, None
    dm = multiset(px)
    sc = scratch(t)
    if sc.get(0) not in dm:
        return None, dm              # E1139's premise: dword 0 is one of the values read
    g = group_of(r["name"]) + rep_of(r["name"])
    wrow = next(x for x in tab if x["name"] == g + "-w")
    m5 = row_markers(wrow)[5]
    prev_t = ok_text(tab[i - 1], cases, d)
    prev = pixels(prev_t) if prev_t else None
    cats = set()
    if top(dm) == m5:
        cats.add("M")
    if prev is not None:
        q = multiset(prev)
        if set(dm) <= set(q) and top(dm) == top(q):
            cats.add("PREV")
    xm = row_markers(tab[i - 1])
    if xm and tab[i - 1]["args"].find("/bins/x-") >= 0 and top(dm) == xm[1]:
        cats.add("XM")
    return cats, dm


def cat_state(token, cats, rivals):
    if cats is None:
        return None
    if token.startswith("!"):
        return token[1:] not in cats
    if token in cats:
        return True
    return False if cats & rivals else None


def score_a(d):
    """(lines, per {model: {row: state}}, ctl, info)."""
    ctl, lines = controls("a", d)
    cases = K.rows(d, "cases.tsv")
    preds = K.predictions(KP, "a")
    tab = K.table(KP, "a")
    form, flines = form_a(tab, cases, d, ctl)
    lines += flines
    pos_ok = all(form.get(n) is True for n in form if group_of(n) in ("c0", "c1")) and \
        any(group_of(n) == "c1" for n in form) and any(group_of(n) == "c0" for n in form)
    rd_ok = all(form.get(n) is True for n in form if group_of(n) == "c2") and \
        sum(1 for n in form if group_of(n) == "c2") == 2
    wr = {}
    for r in tab:
        if r["set"] in ("fit", "heldout") and r["name"].endswith("-w"):
            wr[r["name"]] = read_writer(r, cases, d) if pos_ok else None
    f0a = wr.get("f0a-w")
    s0 = tuple(sorted(f0a["odd"])) if f0a else ()
    f1a = wr.get("f1a-w")
    dd = fit_shift(s0, tuple(sorted(f1a["odd"]))) if f1a else None
    lines.append(f"FIT: S0 (f0a's odd positions) = {list(s0) or 'none'}; d = "
                 + (f"{dd}" if dd is not None else "none (no shift takes S0 onto f1a's)"))
    per, info = {}, dict(s0=s0, d=dd, pos_ok=pos_ok, rd_ok=rd_ok, wr=wr, cats={})

    def put(m, n, st, tok, sset):
        per.setdefault(m, {})[n] = st
        lines.append(f"ROW {n} ({sset}) {m}: frozen {tok}: {word(st)}")

    for i, r in enumerate(tab):
        n, sset = r["name"], r["set"]
        if sset not in ("fit", "heldout"):
            continue
        if n.endswith("-w"):
            w = wr[n]
            if w is None:
                lines.append(f"READING {n}: " + ("cannot tell: form control" if not pos_ok
                                                  else "not read"))
            else:
                lines.append(f"READING {n}: odd {len(w['odd'])}: " + "; ".join(
                    f"sa{k} 0x{w['ms'][k]:08x} at {list(w['pos'][k])}" for k in sorted(w["pos"]))
                    + (f"; other {fmt(multiset(v for v in w['odd'].values() if v not in w['ms'].values()))}"
                       if any(v not in w["ms"].values() for v in w["odd"].values()) else ""))
            for m, tok in sorted(preds[n].get("count", {}).items()):
                k = int(tok.lstrip("!")) // 4
                four = None if w is None else (
                    len(w["odd"]) == 4 * k and all(len(p) == 4 for p in w["pos"].values()))
                put(m, n, None if four is None else (four if m == "H-FOUR" else not four), tok,
                    sset)
            for m, tok in sorted(preds[n].get("pos", {}).items()):
                if w is None:
                    st = None
                elif m == "H-UNION":
                    rp = rep_of(n)
                    src = {1: f"f1{rp}-w", 5: f"h5{rp}-w", 7: f"h7{rp}-w"}
                    parts = {k: wr.get(src[k]) for k in (1, 5, 7)}
                    st = None if any(p is None for p in parts.values()) else all(
                        w["pos"][k] == tuple(sorted(parts[k]["odd"])) for k in (1, 5, 7))
                elif m == "H-FIXED4":
                    st = None if not s0 else tuple(sorted(w["odd"])) == s0
                else:
                    nn = int(tok[3:-1])
                    st = False if dd is None and s0 else None if not s0 else \
                        tuple(sorted(w["odd"])) == shifted(s0, nn, dd)
                put(m, n, st, tok, sset)
            for m, tok in sorted(preds[n].get("rep", {}).items()):
                other = wr.get(n.replace("b-w", "a-w"))
                st = None if w is None or other is None else any(
                    w["pos"][k] != other["pos"][k] for k in w["pos"])
                put(m, n, st, tok, sset)
        elif n.endswith("-r"):
            cats, dm = r5_cats(tab, i, cases, d) if rd_ok else (None, None)
            info["cats"][n] = cats
            lines.append(f"READING {n}: {fmt(dm)}; the job before ({tab[i - 1]['name']}): "
                         + (fmt(multiset(pixels(ok_text(tab[i - 1], cases, d)) or []))
                            if ok_text(tab[i - 1], cases, d) else "no output") + ": "
                         + ("cannot tell: form control" if not rd_ok else
                            "/".join(sorted(cats)) if cats else "none of M, PREV, XM"))
            t = group_of(n) + rep_of(n)
            grp = {k: v for k, v in ctl.items() if k.split("-")[0] == t}
            g = SK.gate(grp) if grp else SK.Gate(ok=True)
            for m, tok in sorted(preds[n]["cat"].items()):
                put(m, n, SK.gated(g, cat_state(tok, cats, {"M", "PREV", "XM"})), tok, sset)
    held = {m: [v for n, v in rows.items() if next(r for r in tab if r["name"] == n)["set"]
                == "heldout"] for m, rows in per.items()}
    for m in sorted(per):
        if held[m]:
            lines.append(f"SUMMARY: a: {m}: " + SK.headline(CLAIMS[m], ctl, held[m]))
    return lines, per, ctl, info


def rule_q129(per, ctl, info):
    out = []
    tab = K.table(KP, "a")
    sets = {r["name"]: r["set"] for r in tab}
    wrows = [n for n in sets if n.endswith("-w") and sets[n] in ("fit", "heldout")]
    singles = [n for n in wrows if sets[n] == "heldout" and group_of(n) != "h157"]
    u157 = [n for n in wrows if group_of(n) == "h157"]
    var = sorted(per.get("H-VAR", {}))
    read = [n for n in wrows if info["wr"].get(n) is not None]
    four = all(per["H-FOUR"].get(n) is True for n in wrows)
    holds = [m for m in A_POS if all(per[m].get(n) is True for n in singles)]
    union = all(per["H-UNION"].get(n) is True for n in u157) and len(u157) == 2
    novar = all(per["H-VAR"].get(n) is False for n in var)
    a_ok = (info["pos_ok"] and len(read) == len(wrows) and four and len(info["s0"]) == 4
            and bool(holds) and union and novar)
    head = (f"Q129 RULE (a): form controls c0, c1 {'passed' if info['pos_ok'] else 'NOT passed'}; "
            f"W rows read {len(read)} of {len(wrows)}; S0 {list(info['s0'])}, d "
            f"{info['d'] if info['d'] is not None else 'none'}; "
            + "; ".join(f"{m} {SK.tally(per[m].get(n) for n in (singles if m in A_POS else u157 if m == 'H-UNION' else var if m == 'H-VAR' else wrows))}"
                        for m in ("H-FOUR", "H-OTHERN") + A_POS + ("H-UNION", "H-VAR")))
    if a_ok:
        out.append(head + f": DECIDED, {' = '.join(holds)}, H-UNION, H-FOUR")
    else:
        why = ("a form control did not pass" if not info["pos_ok"] else
               "a W row is not read" if len(read) != len(wrows) else
               "H-FOUR does not hold on every W row" if not four else
               "S0 is not 4 positions" if len(info["s0"]) != 4 else
               "neither H-FIXED4 nor H-SHIFT holds on every held-out sa" if not holds else
               "H-UNION does not hold on both h157 rows" if not union else
               "the positions vary between replicates (H-VAR)")
        out.append(head + f": not decided ({why})")
    p = sorted(n for n in per["H-ONEJOB"] if group_of(n) == "p")
    q = sorted(n for n in info["cats"] if group_of(n) == "q")
    ctl_b = {k: v for k, v in ctl.items() if group_of(k) in ("c2", "p", "q")}
    q_prev = bool(q) and all(info["cats"][n] is not None and "PREV" in info["cats"][n] for n in q)
    b_holds = [m for m in B_HYP if len(p) == 2 and all(per[m][n] is True for n in p)]
    b_ok = (all(v is True for v in ctl_b.values()) and info["rd_ok"] and q_prev
            and len(b_holds) == 1)
    head_b = (f"Q129 RULE (b): controls {sum(v is True for v in ctl_b.values())} of {len(ctl_b)} "
              f"passed; reader form (c2) {'passed' if info['rd_ok'] else 'NOT passed'}; q (E484's "
              f"form) reads PREV: {'yes' if q_prev else 'no'}; "
              + "; ".join(f"{m} {SK.tally(per[m][n] for n in p)}" for m in B_HYP) + " on p")
    out.append(head_b + (f": DECIDED, {b_holds[0]}" if b_ok else ": not decided"))
    if a_ok and b_ok:
        out.append("Q129 RULE: RETIRE-CAPABLE (both clauses decided; R35-3a)")
    elif a_ok or b_ok:
        out.append(f"Q129 RULE: NARROW: clause ({'a' if a_ok else 'b'}) decided, clause "
                   f"({'b' if a_ok else 'a'}) open")
    else:
        out.append("Q129 RULE: NARROW: neither clause decided")
    if a_ok:
        rule = ("the same 4 pixel positions for every sa" if holds == ["H-FIXED4"] or
                info["d"] == 0 else
                f"sa_n's 4 positions are sa0's shifted by {info['d']} n pixel indices (mod 2048)")
        out.append(f"Q129 ANSWER (a) [HW]: a 64 x 32 fill whose pixel task writes sa_n with "
                   f"iaddu32 (n = 0 to 15) outputs that value at exactly 4 pixels and K1 at "
                   f"the rest; sa0's are {list(info['s0'])} (index y * 64 + x) and {rule}, the "
                   f"same in both replicates; writing sa1, sa5 and sa7 in one job gives the "
                   f"union, 12 pixels (E484's 12)")
        out.append("Q129 WHY (R35-3a) [infer]: the sa write and o0 of those 4 instances name one "
                   "storage, the mirror of E1139's reader pairs; the mechanism moves to Q098's "
                   "open \"pa_n naming sa_n\"")
    if b_ok:
        ans = ("any job between replaces sa5 with that job's output, also a job that writes "
               "another sa (sa1): an sa lasts one job" if b_holds[0] == "H-ONEJOB" else
               "a job between that writes another sa (sa1) leaves sa5 as written, while a job "
               "writing no sa replaces it (E484): an sa lasts until a job that writes no sa")
        out.append(f"Q129 ANSWER (b) [HW]: {ans} (p: 2 of 2 held-out rows; q: E484's form "
                   "reproduced)")
    out.append("Q129 NOT THE LINE: sa written by fewer instances (the body's 1 to 16), other "
               "write forms (mov to sa, E484's), sizes other than 64 x 32; the lead confirms")
    return out


# ---- stage t ---------------------------------------------------------------------------------
def score_t(d):
    ctl, lines = controls("t", d)
    cases = K.rows(d, "cases.tsv")
    preds = K.predictions(KP, "t")
    tab = K.table(KP, "t")
    form, mk, per, info = {}, [], {}, dict(cats={}, groups={})
    for i, r in enumerate(tab):
        n = r["name"]
        if n.endswith("-t"):
            mk.append(row_markers(r)[20])
        if group_of(n) == "c" and n.endswith("-u"):
            m = row_markers(tab[i - 1])[20]
            t = ok_text(r, cases, d)
            px = pixels(t) if t else None
            st = None if px is None or ctl.get(n) is None or ctl.get(tab[i - 1]["name"]) is None \
                else (ctl[n] is True and ctl[tab[i - 1]["name"]] is True
                      and multiset(px) == {m: NPIX})
            form[n] = st
            lines.append(f"FORM {n}: U right after T reads 0x{m:08x} x2048: "
                         f"{fmt(multiset(px)) if px else 'no pixels'}: {cword(st)}")
    form_ok = len(form) == 2 and all(v is True for v in form.values())
    info["form_ok"] = form_ok
    seen = []
    for i, r in enumerate(tab):
        n, sset = r["name"], r["set"]
        if n.endswith("-t"):
            seen.append(row_markers(r)[20])
        if sset != "heldout":
            continue
        g = group_of(n) + rep_of(n)
        m = row_markers(next(x for x in tab if x["name"] == g + "-t"))[20]
        t = ok_text(r, cases, d)
        px = pixels(t) if t and form_ok else None
        cats = None
        if px is not None and scratch(t).get(0) in set(px):
            D = multiset(px)
            cats = set()
            mks = set(seen)
            if D == {m: NPIX}:
                cats.add("M")
            if len(D) >= 2 and set(D) & mks:
                cats.add("SPLIT")
            if not set(D) & mks:
                cats.add("LASTJOB")
            if sorted(D.values()) == [512, 1536]:
                cats.add("TRI1536")
            if len(D) == 1 and set(D) <= mks and D != {m: NPIX}:
                cats.add("OLDER")
        info["cats"][n] = cats
        lines.append(f"READING {n}: " + ("cannot tell: form control" if not form_ok else
                                          "not read" if cats is None else
                                          "; ".join(f"0x{v:08x} x{c} (rows {where(px, v)})"
                                                    for v, c in sorted(multiset(px).items(),
                                                                       key=lambda kv: -kv[1])[:6])
                                          + f": {'/'.join(sorted(cats))}"))
        grp = {k: v for k, v in ctl.items() if k.split("-")[0] == g}
        gt = SK.gate(grp) if grp else SK.Gate(ok=True)
        for mo, tok in sorted(preds[n]["cat"].items()):
            st = SK.gated(gt, cat_state(tok, cats, {"M", "SPLIT", "LASTJOB", "TRI1536", "OLDER"}))
            per.setdefault(mo, {})[n] = st
            lines.append(f"ROW {n} ({sset}) {mo}: frozen {tok}: {word(st)}")
    for mo in sorted(per):
        lines.append(f"SUMMARY: t: {mo}: " + SK.headline(CLAIMS[mo], ctl, list(per[mo].values())))
    return lines, per, ctl, info


def rule_q193(per, ctl, info):
    out = []
    groups = {}
    for n in per["H-LASTWRITER"]:
        groups.setdefault(group_of(n), []).append(n)
    form = info["form_ok"]
    decided = {}
    for g in ("t1", "t2", "t3", "t4"):
        rows = sorted(groups.get(g, []))
        cg = {k: v for k, v in ctl.items() if group_of(k) == g}
        cok = all(v is True for v in cg.values())
        tallies = "; ".join(f"{m} {SK.tally(per[m][n] for n in rows)}"
                            for m in T_FULL + (("H-TRI1536",) if g == "t2" else ())
                            + (("H-RESETCLR",) if g == "t3" else ()))
        if g == "t3":
            kept = rows and all(per["H-LASTWRITER"][n] is True for n in rows)
            clr = rows and all(per["H-RESETCLR"][n] is True for n in rows)
            res = "kept" if kept else "cleared (H-RESETCLR)" if clr else None
        else:
            hs = [m for m in T_FULL if rows and all(per[m][n] is True for n in rows)]
            res = hs[0] if len(hs) == 1 else None
        ok = form and cok and res is not None
        decided[g] = res if ok else None
        out.append(f"Q193 RULE (a) {g}: controls {sum(v is True for v in cg.values())} of "
                   f"{len(cg)} passed, form {'passed' if form else 'NOT passed'}; {tallies}: "
                   + (f"DECIDED, {res}" if ok else "not decided"))
    nd = [g for g, v in decided.items() if v is not None]
    out.append("Q193 RULE (b): another context: decided by construction (every row is its own "
               "process with its own VM and context, t30's side_init); a power cycle and a module "
               "reload: open (R35-5a)")
    out.append(f"Q193 RULE: NARROW: clause (a) decided for {', '.join(nd) or 'no group'} of t1, t2, "
               "t3, t4; the power cycle and module reload clauses stay open")
    return out


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        print(f"gate {argv[2]}: open (not gated)")
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) == 3 and argv[1] == "q129":
        _, per, ctl, info = score_a(os.path.join(argv[2], "a"))
        print("\n".join(rule_q129(per, ctl, info)))
        return 0
    if len(argv) == 3 and argv[1] == "q193":
        _, per, ctl, info = score_t(os.path.join(argv[2], "t"))
        print("\n".join(rule_q193(per, ctl, info)))
        return 0
    if len(argv) >= 3 and argv[1] == "a":
        lines, per, ctl, info = score_a(argv[2])
        print("\n".join(lines + rule_q129(per, ctl, info)))
        return 0
    if len(argv) >= 3 and argv[1] == "t":
        lines, per, ctl, info = score_t(argv[2])
        print("\n".join(lines + rule_q193(per, ctl, info)))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
