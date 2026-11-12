#!/usr/bin/env python3
"""score_m.py STAGE KEPTDIR TOOL6_SHA | verdict ROOT TOOL6_SHA: score r6-misc's stages from their kept files.

  STAGE    q289  q287  q086
  KEPTDIR  out/ATT/STAGE (copied from the laptop's ~/scratch/r6m/out/ATT/STAGE): cases.tsv (rc, class, fault words), NAME.txt.gz
           (the tool's stdout), NAME.err.gz, NAME.dmesg.gz, NAME.depth.1.bin.gz (q287)
  verdict  one SUMMARY line a stage found under ROOT (or `not run`)
Refuses to run unless `run/freeze_m.sh verify TOOL6_SHA` passes.  Prints the per-job table and one `SUMMARY:` line a stage.
Tests call score_q289 / score_q287 / score_q086 (kept directory, predictions) directly.

Rules (HACKING.md "Closing-session scorers", tools/closing/scorekit.py): a job with no output, a missing dump, a skipped row, a
fault where the observable needs a completed job, or a gate that did not pass is cannot tell (None), never a pass; a failing
control shuts the stage's gate; replicates are combined (disagreeing replicates are "mixed", never held); fit, held-out and
confirmation rows are tallied apart; the predictions are read from predictions/STAGE.tsv (frozen) only.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import gzip  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import struct  # noqa: E402
import subprocess  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(KP, "gen")]
import models as M  # noqa: E402
import scorekit as K  # noqa: E402

STAGES = ("q289", "q287", "q086")


# ---- kept files ------------------------------------------------------------------------------------------------------------
class Kept:
    def __init__(self, d):
        self.d = d
        self.cases = {}
        self.order = []
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

    def err(self, n):
        return self._gz(n, ".err") or ""

    def dmesg(self, n):
        return self._gz(n, ".dmesg") or ""

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
    out = ["  ".join(str(h).ljust(w[i]) for i, h in enumerate(head))]
    out += ["  ".join(str(c).ljust(w[i]) for i, c in enumerate(r)) for r in rows]
    return "\n".join(out)


def tool_lines(txt):
    """job result, hash, diff count, diff total, outside count of one tool output (None where absent)."""
    g = lambda rx: (re.search(rx, txt or "", re.M) or [None, None])  # noqa: E731
    job = g(r"^job: (\S+)")[1]
    h = g(r"^target: \d+x\d+ hash (0x[0-9a-f]+)")[1]
    m = re.search(r"^diff: (\d+) of (\d+) pixels", txt or "", re.M)
    o = g(r"^outside: (\d+) dwords")[1]
    return job, (int(h, 16) if h else None), (int(m.group(1)) if m else None), (int(m.group(2)) if m else None), \
        (int(o) if o is not None else None)


# ---- q289 ------------------------------------------------------------------------------------------------------------------
def score_q289(k: Kept, P):
    rows, ctl, held = [], {}, {"M-OR": [], "M-ADD": [], "M-XOR": []}
    sep = {"M-OR": [], "M-ADD": []}
    offboth, outside = [], []
    for n, p in P.items():
        sset = p["set"]
        c = k.cases.get(n)
        txt = k.out(n) if c else None
        job, h, diff, tot, outs = tool_lines(txt)
        void = None
        if c is None:
            void = "not run"
        elif txt is None:
            void = "no output kept"
        elif c.get("class") != "ok" or job != "ok":
            void = "class %s, job %s" % (c.get("class"), job)
        elif h is None:
            void = "no hash line"
        elif "%dx%d" % tuple(int(x) for x in re.search(r"^target: (\d+)x(\d+)", txt, re.M).groups()) != p["size"]["all"]:
            void = "target size is not the row's"
        st = {}
        for model in ("M-OR", "M-ADD", "M-XOR"):
            st[model] = None if void else (h == int(p["hash"][model], 16))
        if not void and outs:
            outside.append("%s (%d)" % (n, outs))
        if not void and not st["M-OR"] and not st["M-ADD"]:
            offboth.append("%s (0x%016x)" % (n, h))
        if sset == "control":
            want = int(p["hash"].get("E876", p["hash"]["M-OR"]), 16)
            ctl[n] = None if void else (h == want and outs == 0)
        else:
            for model in held:
                held[model].append(st[model])
            if p["separates"]["OR-vs-ADD"] == "yes":
                for model in sep:
                    sep[model].append(st[model])
        rows.append((n, sset, p["size"]["all"], "-" if h is None else "0x%016x" % h, "-" if diff is None else diff,
                     "-" if outs is None else outs, "/".join("y" if st[m] else ("-" if st[m] is None else "n") for m in st),
                     void or "ok"))
    out = ["q289: the fill's hash against M-OR / M-ADD / M-XOR (y matches, n does not, - cannot tell)",
           fmt_table(rows, ["job", "set", "size", "hash", "diff", "outside", "OR/ADD/XOR", "note"]), ""]
    g = K.gate(ctl)
    res = {}
    for model in ("M-OR", "M-ADD", "M-XOR"):
        t = K.tally(K.gated(g, r) for r in held[model])
        res[model] = t
        out.append("%s on the held-out rows: %s" % (model, t))
    ts = {m: K.tally(K.gated(g, r) for r in sep[m]) for m in sep}
    out.append("separating rows (OR != ADD): OR %s; ADD %s" % (ts["M-OR"], ts["M-ADD"]))
    if offboth:
        out.append("hashes on neither M-OR nor M-ADD: " + ", ".join(offboth))
    if outside:
        out.append("dwords written outside the target: " + ", ".join(outside))
    if outside:
        summ = "Q289: a store outside the target (%s): the half-tile rule (nothing stored outside) is refuted" % ", ".join(outside)
    elif not g.ok:
        summ = "Q289: cannot tell: controls: " + "; ".join(g.problems)
    elif ts["M-OR"].decided == 0:
        summ = "Q289: cannot tell: no separating row decided"
    else:
        parts = []
        for m in ("M-OR", "M-ADD"):
            t, s = res[m], ts[m]
            parts.append("%s %s (%d of %d held-out rows, %d of %d separating)" % (
                m, "held" if t.failed == 0 and s.failed == 0 else "refuted", t.held, t.decided, s.held, s.decided))
        summ = "Q289: " + "; ".join(parts) + "; controls pass" + ("; off both models: %d" % len(offboth) if offboth else "")
    out.append("SUMMARY: " + summ)
    return "\n".join(out), summ


# ---- q287 ------------------------------------------------------------------------------------------------------------------
def q287_row(k: Kept, n, p):
    """(state dict, stored set or None, note)."""
    c = k.cases.get(n)
    if c is None:
        return None, "not run"
    txt = k.out(n)
    if txt is None:
        return None, "no output kept"
    if c.get("class") != "ok":
        return None, "class " + c.get("class", "?")
    w, h = (int(x) for x in p["size"]["all"].split("x"))
    raw = k.depth(n)
    if raw is None or len(raw) % 4:
        return None, "depth dump missing or unreadable"
    words = struct.unpack("<%dI" % (len(raw) // 4), raw)
    tw, th = M.G.tiles(w, h)
    need = 512 * ((th - 1) * (M.G.pitch_g(w) + 1) + tw)
    if len(words) < need:
        return None, "dump has %d dwords, the tiles need %d" % (len(words), need)
    st, dead = M.G.stored_set(words, w, h)
    if dead:
        return None, "%d tile-area dwords still 0xdeadbeef" % dead
    if not re.search(r"^diff: 0 of %d pixels" % (w * h), txt, re.M):
        return None, "no `diff: 0 of %d pixels`" % (w * h)
    return st, "ok"


def score_q287(k: Kept, P):
    rows, ctl, res = [], {}, {}
    gate_row = [n for n, p in P.items() if p["set"] == "gate"]
    for n, p in P.items():
        st, note = q287_row(k, n, p)
        res[n] = st
        w, h = (int(x) for x in p["size"]["all"].split("x"))
        if st is not None:
            xs = max((x for x, _ in st), default=-1) + 1
            ys = max((y for _, y in st), default=-1) + 1
            hit = [r for r in M.G.RULES if M.set_sha(st) == p["stored_set_sha"][r]]
        else:
            xs = ys = "-"
            hit = []
        if p["set"] == "control":
            ctl[n] = None if st is None else (len(st) == int(p["stored_count"]["E831"]) and M.set_sha(st) == p["stored_set_sha"]["A"])
        rows.append((n, p["set"], "%dx%d" % (w, h), "-" if st is None else len(st), "%s,%s" % (xs, ys),
                     " ".join(hit) or "-", p["separates"]["A-vs-FLOOR"], note))
    out = ["q287: stored (not 1.0f) tile-area dwords and the rules whose set equals them",
           fmt_table(rows, ["job", "set", "size", "stored", "extent", "rules matched", "A!=FLOOR", "note"]), ""]
    g0 = gate_row[0] if gate_row else None
    if g0 and k.cases.get(g0, {}).get("class") == "fail":
        summ = "Q287: odd heights refused (gateodd: %s, class fail): not run" % g0
        out.append("SUMMARY: " + summ)
        return "\n".join(out), summ
    if g0 and g0 not in k.cases:
        summ = "Q287: cannot tell: the gate row %s did not run" % g0
        out.append("SUMMARY: " + summ)
        return "\n".join(out), summ
    g = K.gate(ctl)
    # replicates: rows that differ only by -rN are one cell; a cell's state per rule is combine() of its runs
    cells = {}
    for n, p in P.items():
        if p["set"] in ("control", "gate"):
            continue
        cells.setdefault((re.sub(r"-r\d$", "", n), p["set"]), []).append(n)
    tallies = {}
    lines = []
    for r in ("A", "FLOOR", "ROUND", "CEIL", "RSTRICT"):
        for sset in ("fit", "heldout", "confirm"):
            states = []
            for (cell, s), names in sorted(cells.items()):
                if s != sset:
                    continue
                reps = [None if res[n] is None else M.set_sha(res[n]) == P[n]["stored_set_sha"][r] for n in names]
                cmb = K.combine(reps)
                states.append(True if cmb == "held" else (False if cmb in ("refuted", "mixed") else None))
            tallies[(r, sset)] = K.tally(K.gated(g, s) for s in states)
        lines.append("rule %-7s fit %s | held out %s | confirm %s" % (r, tallies[(r, "fit")], tallies[(r, "heldout")],
                                                                   tallies[(r, "confirm")]))
    out += lines
    unmatched = [n for n, st in res.items() if st is not None and P[n]["set"] not in ("control",)
                 and not any(M.set_sha(st) == P[n]["stored_set_sha"][r] for r in M.G.RULES)]
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
                return "held" if t.failed == 0 else "refuted"
            summ = ("Q287 (odd heights, W 34): rule A %s on the held-out cells (%d of %d), FLOOR %s (%d of %d); fit cell 19: A %s, "
                    "FLOOR %s; .25 confirmations A %d of %d; controls pass%s" % (
                        word(a), a.held, a.decided, word(f), f.held, f.decided,
                        word(tallies[("A", "fit")]) if tallies[("A", "fit")].decided else "cannot tell",
                        word(tallies[("FLOOR", "fit")]) if tallies[("FLOOR", "fit")].decided else "cannot tell",
                        tallies[("A", "confirm")].held, tallies[("A", "confirm")].decided,
                        "; no rule matches: " + ", ".join(unmatched) if unmatched else ""))
    out.append("SUMMARY: " + summ)
    return "\n".join(out), summ


# ---- q086 ------------------------------------------------------------------------------------------------------------------
def score_q086(k: Kept, P):
    rows, ctl = [], {}
    st = {"H-COV": [], "H-ANY": []}
    skipped, words = [], []
    for n, p in P.items():
        c = k.cases.get(n)
        w, h = (int(x) for x in p["size"]["all"].split("x"))
        obs, note = None, ""
        if c is None:
            note = "not run (its group reached its count, or the stage stopped)"
            skipped.append(n)
        else:
            txt = k.out(n)
            job, hsh, diff, tot, outs = tool_lines(txt)
            if c.get("class") == "ok":
                nrow = len(re.findall(r"^row \d+: ", txt or "", re.M))
                if diff == 0 and tot == w * h and nrow == h:
                    obs = "ok"
                else:
                    note = "completed but diff %s of %s, %d pixel rows" % (diff, tot, nrow)
                    obs = "ok-wrong"
            elif c.get("class") == "fault":
                fi, fw = c.get("fault_req", "unread"), c.get("fault_word", "unread")
                is3d = fi == "256" and fw.startswith("0x") and int(fw, 16) & 0xFFFFFF00 == 0x10000000
                obs = "fault" if is3d else "fault-other"
                words.append("%s %s/%s" % (n, fi, fw))
            else:
                note = "class " + c.get("class", "?")
        pred = p["class"]
        sc = {}
        for model in st:
            if obs is None:
                sc[model] = None
            elif obs in ("ok-wrong", "fault-other"):
                sc[model] = False
            else:
                sc[model] = obs == pred[model]
        if p["set"] == "control":
            ctl[n] = None if obs is None else obs == "ok"
        else:
            for model in st:
                st[model].append(sc[model])
        rows.append((n, p["set"], "%dx%d" % (w, h), p["cover"]["H-COV"], pred["H-COV"], obs or "-",
                     "/".join("y" if sc[m] else ("-" if sc[m] is None else "n") for m in st), note or "ok"))
    out = ["q086: class of each 4x job against H-COV (complete iff the words' grid covers the target) and H-ANY (all complete)",
           fmt_table(rows, ["job", "set", "size", "cover (B3+B1 of tiles)", "H-COV", "observed", "COV/ANY", "note"]), ""]
    g = K.gate(ctl)
    t = {m: K.tally(K.gated(g, r) for r in st[m]) for m in st}
    for m in st:
        out.append("%s on the held-out rows: %s" % (m, t[m]))
    if words:
        out.append("fault words: " + ", ".join(words))
    if skipped:
        out.append("not run: %d rows (%s)" % (len(skipped), " ".join(skipped)))
    if not g.ok:
        summ = "Q086: cannot tell: controls: " + "; ".join(g.problems)
    elif t["H-COV"].decided == 0:
        summ = "Q086: cannot tell: no held-out row decided"
    else:
        summ = "Q086: H-COV %s (%d of %d held-out rows), H-ANY %s (%d of %d); %d rows not run; control R passes" % (
            "held" if t["H-COV"].failed == 0 else "refuted", t["H-COV"].held, t["H-COV"].decided,
            "held" if t["H-ANY"].failed == 0 else "refuted", t["H-ANY"].held, t["H-ANY"].decided, len(skipped))
    out.append("SUMMARY: " + summ)
    return "\n".join(out), summ


# every file each scorer reads, per kept row (tests/run_mock.sh checks the kept output of every stage against it)
REQUIRED = {"q289": (".txt",), "q287": (".txt", ".depth.1.bin"), "q086": (".txt",)}


def missing_files(stage, d):
    """The files the stage's scorer reads that are not in the kept directory d (cases.tsv first)."""
    if not os.path.exists(os.path.join(d, "cases.tsv")):
        return ["cases.tsv"]
    k = Kept(d)
    return [n + s + ".gz" for n in k.order for s in REQUIRED[stage] if not os.path.exists(os.path.join(d, n + s + ".gz"))]


SCORERS = {"q289": score_q289, "q287": score_q287, "q086": score_q086}


def frozen_ok(s6):
    r = subprocess.run([os.path.join(KP, "run", "freeze_m.sh"), "verify", s6], capture_output=True, text=True)
    return r.returncode == 0, r.stdout + r.stderr


def main(argv):
    if len(argv) != 4 or argv[1] not in STAGES + ("verdict",):
        print(__doc__)
        return 2
    ok, msg = frozen_ok(argv[3])
    if not ok:
        print(msg.strip())
        print("SUMMARY: refused: the frozen files do not verify")
        return 1
    if argv[1] == "verdict":
        for s in STAGES:
            d = os.path.join(argv[2], s)
            if not os.path.isdir(d):
                print("SUMMARY: %s: not run" % s)
                continue
            _, summ = SCORERS[s](Kept(d), load_preds(s))
            print("SUMMARY: " + summ)
        return 0
    text, _ = SCORERS[argv[1]](Kept(argv[2]), load_preds(argv[1]))
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
