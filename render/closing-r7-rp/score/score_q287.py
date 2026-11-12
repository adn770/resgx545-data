#!/usr/bin/env python3
"""score_q287.py: r7-rp's scorer for stage s0 (the session gate) and stage q287 (Q287 odd widths at H 18).

  score_q287.py STAGE KEPT       detail, then exactly one `SUMMARY:` line (exit 0 even for cannot tell)
  score_q287.py gate STAGE KEPT  exit status = gate(STAGE, KEPT): 0 pass, 1 failed, 2 cannot tell (s0 only; 0 elsewhere)
  score_q287.py verdict ATT      the question's SUMMARY line(s) from ATT/q287

Reads only: cases.tsv, NAME.txt, NAME.depth.1.bin of the rows (REQUIRED), and s0's z-ctl row's dump.  The depth dump is
tile-major at the store's pitch G + 1 tiles (G = the ZLS control word's bits 11:3: 0x17100c is two tiles a row), the row's
frozen `pitch_tiles` prediction, never ceil(W / 32).  Rules (scorekit): a missing file, a skipped row, a row that did not
complete or a failed control is cannot tell, never a pass; replicates that disagree are "mixed", never held; the predictions
are read from predictions/STAGE.tsv (frozen).
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import gzip  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import struct  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(KP, "gen")]
import models_q287 as M  # noqa: E402
import scorekit as K  # noqa: E402

STAGES = ("s0", "q287")
REQUIRED = {"s0": ("cases.tsv", ".txt", "s0-z-ctl-34x18-y-t4.depth.1.bin"), "q287": ("cases.tsv", ".txt", ".depth.1.bin")}
S0_DEPTH_ROW = "s0-z-ctl-34x18-y-t4"


# ---- kept files ---------------------------------------------------------------------------------------------------------------
class Kept:
    def __init__(self, d):
        self.d = d
        self.cases, self.order = {}, []
        p = os.path.join(d, "cases.tsv")
        if os.path.exists(p):
            lines = open(p).read().splitlines()
            hdr = lines[0].split("\t")
            for ln in lines[1:]:
                c = dict(zip(hdr, ln.split("\t")))
                self.cases[c["name"]] = c
                self.order.append(c["name"])

    def _gz(self, name, suffix, binary=False):
        p = os.path.join(self.d, name + suffix + ".gz")
        if not os.path.exists(p):
            return None
        with gzip.open(p, "rb") as f:
            b = f.read()
        return b if binary else b.decode("utf-8", "replace")

    def out(self, n):
        return self._gz(n, ".txt")

    def depth(self, n):
        return self._gz(n, ".depth.1.bin", binary=True)


def load_preds(stage, kp=KP):
    P = {}
    for ln in open(os.path.join(kp, "predictions", stage + ".tsv")).read().splitlines()[1:]:
        case, q, v, model, sset = ln.split("\t")
        P.setdefault(case, {"set": sset}).setdefault(q, {})[model] = v
    return P


def fmt_table(rows, head):
    w = [max(len(str(r[i])) for r in rows + [head]) for i in range(len(head))]
    return "\n".join(["  ".join(str(h).ljust(w[i]) for i, h in enumerate(head))] +
                     ["  ".join(str(c).ljust(w[i]) for i, c in enumerate(r)) for r in rows])


def diff_line(txt):
    m = re.search(r"^diff: (\d+) of (\d+) pixels", txt or "", re.M)
    return (int(m.group(1)), int(m.group(2))) if m else None


def depth_row(k, n, p, need_diff=True):
    """(stored set or None, note): the row's job completed, its dump is long enough at the store's pitch, no tile-area dword
    still holds the pre-fill, and (need_diff) the colour image is exact."""
    c = k.cases.get(n)
    if c is None:
        return None, "not run"
    txt = k.out(n)
    if txt is None:
        return None, "no output kept"
    if c.get("class") != "ok":
        return None, "class " + c.get("class", "?")
    if not re.search(r"^job: ok", txt, re.M):
        return None, "no `job: ok`"
    w, h = (int(x) for x in p["size"]["all"].split("x"))
    raw = k.depth(n)
    if raw is None or len(raw) % 4:
        return None, "depth dump missing or unreadable"
    words = struct.unpack("<%dI" % (len(raw) // 4), raw)
    pt = int(p["pitch_tiles"]["all"])
    if len(words) < M.need_dwords(w, h, pt):
        return None, "dump has %d dwords, the tiles need %d" % (len(words), M.need_dwords(w, h, pt))
    st, dead = M.stored_set(words, w, h, pt)
    if dead:
        return None, "%d tile-area dwords still 0xdeadbeef" % dead
    if need_diff and diff_line(txt) != (0, w * h):
        return None, "no `diff: 0 of %d pixels`" % (w * h)
    return st, "ok"


# ---- s0 -----------------------------------------------------------------------------------------------------------------------
def s0_rows(k, P):
    """{row: True | False | None} for the four session-gate rows, with a note each."""
    res = {}
    for n, p in P.items():
        c = k.cases.get(n)
        txt = k.out(n) if c else None
        if c is None:
            res[n] = (None, "not run")
        elif txt is None:
            res[n] = (None, "no output kept")
        elif c.get("class") != "ok":
            res[n] = (False, "class " + c.get("class", "?"))
        elif "diff" in p:
            d = diff_line(txt)
            if d is None:
                res[n] = (None, "no diff line")
            else:
                res[n] = (d == (0, 4096), "diff %d of %d" % d)
        else:
            st, note = depth_row(k, n, p)
            if st is None:
                res[n] = (None, note)
            else:
                ok = len(st) == int(p["stored_count"]["E831"]) and M.set_sha(st) == p["stored_set_sha"]["A"]
                res[n] = (ok, "stored %d" % len(st))
    return res


def score_s0(k, P):
    res = s0_rows(k, P)
    rows = [(n, "PASS" if v is True else ("FAILED" if v is False else "cannot tell"), note) for n, (v, note) in res.items()]
    out = ["s0: the session gate", fmt_table(rows, ["job", "state", "note"]), ""]
    g = K.gate({n: v for n, (v, _) in res.items()})
    summ = "s0: gate passes (4 of 4)" if g.ok else ("s0: gate FAILED: " if g.failed else "s0: cannot tell: ") + "; ".join(g.problems)
    out.append("SUMMARY: " + summ)
    return "\n".join(out), summ


def gate_s0(k, P):
    res = s0_rows(k, P)
    if any(v is False for v, _ in res.values()):
        return 1
    return 0 if all(v is True for v, _ in res.values()) else 2


# ---- q287 ---------------------------------------------------------------------------------------------------------------------
def twin_reading(p, st):
    hit = [m for m in ("H-SCR", "H-VP") if M.set_sha(st) == p["stored_set_sha"][m]]
    if len(hit) == 2:
        return "both (same set)"
    return hit[0] if hit else "neither (extent %d)" % (max((x for x, _ in st), default=-1) + 1)


def score_q287(k, P):
    rows, ctl, res = [], {}, {}
    gate_row = [n for n, p in P.items() if p["set"] == "gate"]
    g0 = gate_row[0] if gate_row else None
    ptl = next(iter(P.values()))["pitch_tiles"]["all"]
    for n, p in P.items():
        st, note = depth_row(k, n, p, need_diff=p["set"] != "twin")
        res[n] = st
        w, h = (int(x) for x in p["size"]["all"].split("x"))
        if st is None:
            xs, hit = "-", []
        else:
            xs = max((x for x, _ in st), default=-1) + 1
            hit = [r for r in M.RULES if M.set_sha(st) == p["stored_set_sha"][r]] if p["set"] != "twin" else \
                [m for m in ("H-SCR", "H-VP") if M.set_sha(st) == p["stored_set_sha"][m]]
        if p["set"] in ("control", "gate"):
            ctl[n] = None if st is None else (len(st) == int(p["stored_count"].get("E831", p["stored_count"]["A"]))
                                              and M.set_sha(st) == p["stored_set_sha"]["A"])
        rows.append((n, p["set"], "%dx%d" % (w, h), "-" if st is None else len(st), xs, " ".join(hit) or "-",
                     p.get("separates", {}).get("A-vs-FLOOR", "-"), note))
    out = ["q287: stored (not 1.0f) tile-area dwords at the store's pitch (%s tiles a row) and the rules whose set equals them" %
           ptl,
           fmt_table(rows, ["job", "set", "size", "stored", "cols", "matched", "A!=FLOOR", "note"]), ""]
    twins = {n: p for n, p in P.items() if p["set"] == "twin"}
    tw = []
    for n, p in twins.items():
        tw.append("%s %s" % (n.replace("z-pk-20x18-", ""), "cannot tell" if res[n] is None else twin_reading(p, res[n])))
    twin_txt = "poke twins (W 20, gate nothing): " + ", ".join(tw)
    if twins:
        out.append(twin_txt)
    if g0 and (k.cases.get(g0, {}).get("class") == "fail" or "job: rejected" in (k.out(g0) or "")):
        summ = "Q287: odd widths refused by the module (gateodd: %s, class fail); %s" % (g0, twin_txt)
        out.append("SUMMARY: " + summ)
        return "\n".join(out), summ
    if g0 and g0 not in k.cases:
        summ = "Q287: cannot tell: the gate row %s did not run; %s" % (g0, twin_txt)
        out.append("SUMMARY: " + summ)
        return "\n".join(out), summ
    g = K.gate(ctl)
    cells = {}
    for n, p in P.items():
        if p["set"] in ("control", "gate", "twin"):
            continue
        cells.setdefault((re.sub(r"-r\d$", "", n), p["set"]), []).append(n)
    tallies, mixed = {}, []
    for r in M.RULES:
        for sset in ("fit", "heldout", "confirm"):
            states = []
            for (cell, s), names in sorted(cells.items()):
                if s != sset:
                    continue
                reps = [None if res[n] is None else M.set_sha(res[n]) == P[n]["stored_set_sha"][r] for n in names]
                cmb = K.combine(reps)
                if cmb == "mixed" and cell not in mixed:
                    mixed.append(cell)
                states.append(True if cmb == "held" else (False if cmb in ("refuted", "mixed") else None))
            tallies[(r, sset)] = K.tally(K.gated(g, x) for x in states)
        out.append("rule %-7s fit %s | held out %s | confirm %s" % (r, tallies[(r, "fit")], tallies[(r, "heldout")], tallies[(r, "confirm")]))
    if mixed:
        out.append("replicates disagree (mixed): " + ", ".join(mixed))
    unmatched = [n for n, st in res.items() if st is not None and P[n]["set"] in ("fit", "heldout", "confirm")
                 and not any(M.set_sha(st) == P[n]["stored_set_sha"][r] for r in M.RULES)]
    if unmatched:
        out.append("no rule's set matches: " + ", ".join(unmatched))
    if not g.ok:
        summ = "Q287: cannot tell: controls: " + "; ".join(g.problems)
    else:
        a, f = tallies[("A", "heldout")], tallies[("FLOOR", "heldout")]
        if a.decided == 0:
            summ = "Q287: cannot tell: no held-out cell decided"
        else:
            def word(t):
                return "held" if t.failed == 0 and t.cannot_tell == 0 else ("refuted" if t.failed else "held on the decided cells")
            fa, ff = tallies[("A", "fit")], tallies[("FLOOR", "fit")]
            summ = ("Q287 (odd widths, H 18): rule A %s on the held-out cells (%d of %d), FLOOR %s (%d of %d); fit cell 19: A %s, FLOOR %s; "
                    ".25 confirmations A %d of %d; %scontrols pass%s" % (
                        word(a), a.held, a.total, word(f), f.held, f.total,
                        word(fa) if fa.decided else "cannot tell", word(ff) if ff.decided else "cannot tell",
                        tallies[("A", "confirm")].held, tallies[("A", "confirm")].total,
                        "replicates mixed (%s); " % ", ".join(mixed) if mixed else "",
                        "; no rule matches: " + ", ".join(unmatched) if unmatched else ""))
        if twins:
            summ += "; " + twin_txt
    out.append("SUMMARY: " + summ)
    return "\n".join(out), summ


SCORERS = {"s0": score_s0, "q287": score_q287}


def score(stage, kept_dir, P=None):
    """(summary string, detail lines) of a stage's kept directory."""
    text, summ = SCORERS[stage](Kept(kept_dir), P or load_preds(stage))
    return summ, text.splitlines()


def gate(stage, kept_dir, P=None):
    """0 pass, 1 failed, 2 cannot tell; only s0 has a driver gate (q287's own gate row decides inside its verdict)."""
    if stage != "s0":
        return 0
    return gate_s0(Kept(kept_dir), P or load_preds("s0"))


def verdict(att_dir):
    d = os.path.join(att_dir, "q287")
    if not os.path.isdir(d):
        return ["SUMMARY: Q287: not run"]
    return ["SUMMARY: " + score("q287", d)[0]]


def main(argv):
    if len(argv) == 4 and argv[1] == "gate" and argv[2] in STAGES:
        return gate(argv[2], argv[3])
    if len(argv) == 3 and argv[1] == "verdict":
        print("\n".join(verdict(argv[2])))
        return 0
    if len(argv) == 3 and argv[1] in STAGES:
        summ, detail = score(argv[1], argv[2])
        print("\n".join(x for x in detail if not x.startswith("SUMMARY: ")))
        print("SUMMARY: " + summ)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
