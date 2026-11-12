#!/usr/bin/env python3
"""score_q086.py: r7-rp stage q086 (the axes of H-COV), scored from the kept files.

  score_q086.py q086 KEPT          per-row table, then exactly one `SUMMARY:` line (exit 0 even when cannot tell)
  score_q086.py gate q086 KEPT     exit 0 (q086 has no driver gate)
  score_q086.py verdict ATT_DIR    the SUMMARY line of ATT_DIR/q086 (or `not run`)

Per row (cases.tsv class, fault words, NAME.txt.gz): ok = job ok, `diff: 0 of W*H`, H pixel rows, every pixel 0xff00ff00; fault = class
fault with BIF_INT_STAT 256 (0x0100) and BIF_FAULT 0x100000xx (3D side); anything else (completed but wrong, other fault class,
missing output) is ok-wrong / fault-other / cannot tell.  Rows: control (R, must be ok), bridge (E886's U2 and FX on this module),
heldout (the predicted fault rows); a heldout row counts only when every row in its `needs` (its R control, the FX bridge) passed
(the R control ok with 0 wrong; the FX bridge as predicted).  Each model (H-COV, H-X, H-Y, H-AREA, H-ANY) holds when every counted
row's class is the model's.  Read files: cases.tsv, NAME.txt (REQUIRED).
"""
from __future__ import annotations

import gzip
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(KP, "gen")]
import scorekit as K  # noqa: E402

STAGE = "q086"
REQUIRED = {"q086": ("cases.tsv", ".txt")}
MODELS = ("H-COV", "H-X", "H-Y", "H-AREA", "H-ANY")
GREEN = "0xff00ff00"


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

    def out(self, n):
        p = os.path.join(self.d, n + ".txt.gz")
        if not os.path.exists(p):
            return None
        with gzip.open(p, "rb") as f:
            return f.read().decode("utf-8", "replace")


def load_preds(stage=STAGE, kp=KP):
    P = {}
    for ln in open(os.path.join(kp, "predictions", stage + ".tsv")).read().splitlines()[1:]:
        case, q, v, model, sset = ln.split("\t")
        P.setdefault(case, {"set": sset}).setdefault(q, {})[model] = v
    return P


def fmt_table(rows, head):
    w = [max(len(str(r[i])) for r in rows + [head]) for i in range(len(head))]
    return "\n".join("  ".join(str(c).ljust(w[i]) for i, c in enumerate(r)) for r in [head] + rows)


def observe(c, txt, w, h):
    """(obs, note): ok | ok-wrong | fault | fault-other | None (cannot tell)."""
    if c is None:
        return None, "not run"
    if txt is None:
        return None, "no output kept"
    cls = c.get("class")
    if cls == "ok":
        m = re.search(r"^diff: (\d+) of (\d+) pixels", txt, re.M)
        job = re.search(r"^job: (\S+)", txt, re.M)
        rows = re.findall(r"^row \d+: (.*)$", txt, re.M)
        words = [t for r in rows for t in r.split()]
        good = (job and job.group(1) == "ok" and m and int(m.group(1)) == 0 and int(m.group(2)) == w * h
                and len(rows) == h and len(words) == w * h and all(t == GREEN for t in words))
        return ("ok", "") if good else ("ok-wrong", "completed but diff/pixels are not 0 wrong of %d" % (w * h))
    if cls == "fault":
        fi, fw = c.get("fault_req", "unread"), c.get("fault_word", "unread")
        d3 = fi == "256" and fw.startswith("0x") and int(fw, 16) & 0xFFFFFF00 == 0x10000000
        return ("fault" if d3 else "fault-other"), "%s/%s" % (fi, fw)
    return None, "class " + str(cls)


def score(stage, kept_dir, P=None):
    k = Kept(kept_dir)
    P = P or load_preds(stage)
    obs, note = {}, {}
    for n, p in P.items():
        w, h = (int(x) for x in p["size"]["all"].split("x"))
        obs[n], note[n] = observe(k.cases.get(n), k.out(n) if n in k.cases else None, w, h)

    def need_state(n):
        o = obs.get(n)
        if o is None:
            return None
        return o == P[n]["class"]["H-COV"]

    st = {m: [] for m in MODELS}
    rows, skipped, bridges = [], [], []
    for n, p in P.items():
        o = obs[n]
        if o is None and note[n] == "not run":
            skipped.append(n)
        pred = p["class"]
        needs = [x for x in p.get("needs", {}).get("all", "-").split(",") if x != "-"]
        g = K.gate({x: need_state(x) for x in needs}) if needs else None
        sc = {}
        for m in MODELS:
            if o is None:
                sc[m] = None
            elif o in ("ok-wrong", "fault-other"):
                sc[m] = False
            else:
                sc[m] = o == pred[m]
        if p["set"] == "heldout":
            for m in MODELS:
                st[m].append(sc[m] if (g is None or g.ok) else None)
        elif p["set"] == "bridge":
            bridges.append("%s %s" % (n.split("-", 1)[1], o or "cannot tell"))
        rows.append((n, p["set"], p["size"]["all"], p["cover"]["H-COV"], pred["H-COV"], o or "-",
                     "/".join("y" if sc[m] else ("-" if sc[m] is None else "n") for m in MODELS),
                     note[n] or ("needs: " + ",".join(needs) if needs and not g.ok else "ok")))
    out = ["q086: class of each 4x job against " + ", ".join(MODELS) + " (y matches, n does not, - cannot tell)",
           fmt_table(rows, ["job", "set", "size", "cover (B3+B1 of tiles)", "H-COV", "observed", "COV/X/Y/AREA/ANY", "note"]), ""]
    t = {m: K.tally(st[m]) for m in MODELS}
    for m in MODELS:
        out.append("%s on the counted rows: %s" % (m, t[m]))
    ctl = [n for n, p in P.items() if p["set"] == "control"]
    ctl_ok = [n for n in ctl if obs[n] == "ok"]
    fx = [n for n, p in P.items() if p["set"] == "bridge" and p["class"]["H-COV"] == "fault"]
    fx_done = [n for n in fx if obs[n] == "ok"]
    if skipped:
        out.append("not run: %d rows (%s)" % (len(skipped), " ".join(skipped)))
    bl = "bridges: " + (", ".join(bridges) if bridges else "none")
    if fx_done:
        summ = "Q086: bridge %s completed: E886 depended on the old module, the new-size rows are unscored; %s" % (
            fx_done[0].split("-", 1)[1], bl)
    elif all(t[m].decided == 0 for m in MODELS):
        bad = [n for n in ctl if obs[n] != "ok"]
        summ = "Q086: cannot tell: no row decided" + ("; controls not passed: " + ", ".join(bad) if bad else "") + "; " + bl
    else:
        word = lambda m: ("held" if t[m].failed == 0 else "refuted")  # noqa: E731
        parts = ["%s %s (%d of %d rows%s)" % (m, word(m), t[m].held, t[m].decided,
                                              "; %d cannot tell" % t[m].cannot_tell if t[m].cannot_tell else "") for m in MODELS]
        summ = "Q086: %s; %s; controls pass %d of %d" % (", ".join(parts), bl, len(ctl_ok), len(ctl))
    if "q086-448x160-U2" in P:
        summ += "; 11 unrun E886 rows not pursued, by design"
    out.append("SUMMARY: " + summ)
    return summ, out


def gate(stage, kept_dir):
    return 0


def verdict(att_dir):
    d = os.path.join(att_dir, STAGE)
    if not os.path.isdir(d):
        return ["SUMMARY: Q086: not run"]
    return ["SUMMARY: " + score(STAGE, d)[0]]


def main(argv):
    if len(argv) == 4 and argv[1] == "gate" and argv[2] == STAGE:
        return gate(STAGE, argv[3])
    if len(argv) == 3 and argv[1] == "verdict":
        print("\n".join(verdict(argv[2])))
        return 0
    if len(argv) == 3 and argv[1] == STAGE:
        summ, out = score(STAGE, argv[2])
        print("\n".join(out))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
