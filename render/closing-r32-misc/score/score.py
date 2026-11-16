#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r32-misc's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 80d9f2a1b3dc, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL, ROW and READ lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage gates another)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading
  score.py file NAME.txt               the readings of one job's text (a kept record's, offline)

A row's readings (analyse(), run/hooks.sh's rd_words is the twin of the control keys): diff (the
`diff:` lines summed), cache and cache9 (CR_CACHE_CTRL 0x0804 in the kit's snap0 and snap9),
mi and mius (the kit's kept NAME.miscinfo: served, and the answer's us; kitscore.miscinfo),
and under regtimeline ivl, ccfirst (0x0804 in the first sample), ccn (its changes), ccword (the
word after the first change), ccstart (ms from the tool's start to it). kicks (the served
GETMISCINFO answers before snap0) is a control reading only: readings.tsv.

The decisive reading of a row with pre:miscinfo, cache (and ccfirst), counts only where the row's
own premises hold: the read was served (mi) and the triangle after it still set bit 28 (cache9
0x1000ffff, H-CC-ONE: the word did not leave the core in another state); else cannot tell.

REQUIRED: the files each stage's scorer reads; read_files(STAGE, DIR) reads exactly what
verdicts() reads (NAME.miscinfo is the kit's word file: sessioncheck declares it); producible(row)
is the set of reading keys a row's job can produce."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

STAGES = ("m1", "m2")
REQUIRED = {s: (".txt", ".snap0.regs", ".snap9.regs", "cases.tsv", "void.tsv", "readings.tsv")
            for s in STAGES}
GATES = {}
WORD = "pre:miscinfo"
SET_BIT28 = 0x1000ffff
PREMISED = ("cache", "ccfirst")     # the readings that need the row's premises (mi, cache9)


def producible(row):
    keys = {"diff", "cache", "cache9", "kicks"}
    if WORD in row["knobs"]:
        keys.add("mi")
    if row["tool"] == "rt":
        keys.add("ivl")
    return keys


# ---- one job ----------------------------------------------------------------------------------
def timeline(text):
    """regtimeline's block: dict(regs, samples, seconds, start, end, rc, rows=[(t, [v])], cut)
    or None when the text has none."""
    tl = None
    for ln in text.splitlines():
        if ln.startswith("timeline: regs"):
            if tl is not None:
                break
            p = ln.split()
            i = p.index("samples")
            tl = dict(regs=[int(x, 16) for x in p[2:i]], samples=int(p[i + 1]),
                      seconds=float(p[i + 3]), start=int(p[i + 5]), end=int(p[i + 7]),
                      rc=int(p[i + 9]), rows=[], cut=False)
        elif ln.startswith("tl ") and tl is not None:
            p = ln.split()
            if len(p) != len(tl["regs"]) + 2:
                tl["cut"] = True
                break
            tl["rows"].append((int(p[1]), [int(x, 16) for x in p[2:]]))
    return tl


def diff_sum(text):
    s = [int(ln.split()[1]) for ln in text.splitlines() if ln.startswith("diff: ") and
         ln.split()[1].isdigit()]
    return sum(s) if s else None


def reg(regs_text, off):
    for ln in regs_text.splitlines():
        p = ln.split()
        if len(p) >= 3 and p[0] == "reg" and p[1] == off:
            return "0x%08x" % int(p[2], 16)
    return None


def analyse(text, snap0="", snap9="", mi=None):
    """Every reading of one job (None where the job cannot give it)."""
    r = dict(diff=diff_sum(text), cache=reg(snap0, "0x0804"), cache9=reg(snap9, "0x0804"))
    if mi is not None:
        r["mi"] = 1 if mi["served"] else 0
        r["mius"] = mi["us"]
    tl = timeline(text)
    if tl is None or not tl["rows"]:
        return r
    rows, regs = tl["rows"], tl["regs"]
    dur = max(tl["seconds"] * 1e9, tl["end"])
    r.update(cut=tl["cut"], rc=tl["rc"])
    r["ivl"] = int(dur / tl["samples"]) if tl["samples"] else None
    if 0x0804 in regs:
        c = regs.index(0x0804)
        v0 = rows[0][1][c]
        r["ccfirst"] = "0x%08x" % v0
        ch = [i for i, (_, v) in enumerate(rows) if v[c] != v0]
        r["ccn"] = sum(1 for a, b in zip(rows, rows[1:]) if a[1][c] != b[1][c])
        r["ccword"] = "0x%08x" % rows[ch[0]][1][c] if ch else None
        if ch:
            r["ccstart"] = round((rows[ch[0]][0] - tl["start"]) / 1e6, 2)
    return r


def kicks(dmesg, name, prefix="r32m", run=""):
    """The served GETMISCINFO answers after the last boot kick before NAME's snap0 mark (the
    hook's twin, for its tests)."""
    k = 0
    for ln in dmesg.splitlines():
        if "SGX boot: kicking the EDM" in ln:
            k = 0
        elif "SGX firmware: core" in ln and " answered after " in ln:
            k += 1
        elif f"resgx545 {prefix} snap {name} 0 " in ln and f" {run}" in ln:
            return k
    return None


# ---- verdicts -----------------------------------------------------------------------------
def inside(value, want):
    """A frozen value: exact (hex or decimal text) or a closed window lo..hi."""
    if value is None:
        return None
    if ".." in want:
        lo, hi = (float(x) for x in want.split(".."))
        return lo <= float(value) <= hi
    if want.startswith("0x") or str(value).startswith("0x"):
        try:
            return int(str(value), 16) == int(want, 16)
        except ValueError:
            return False
    return str(value) == want


def frozen(stage):
    """[(case, quantity, value, model, set)] of predictions/STAGE.tsv (kitscore drops the set)."""
    out = []
    lines = open(os.path.join(KP, "predictions", stage + ".tsv")).read().splitlines()
    for ln in lines[1:]:
        f = ln.split("\t")
        if len(f) >= 5:
            out.append(tuple(f[:5]))
    return out


class Kept:
    def __init__(self, stage, d):
        self.stage, self.d = stage, d
        self.cases = K.rows(d, "cases.tsv")
        self.void = K.rows(d, "void.tsv")
        self.readings = K.readings(d)
        self.read = {}
        self.words = {r["name"]: r["knobs"] for r in K.table(KP, stage)}

    def done(self, n):
        return n in self.cases and K.completed(self.cases[n])

    def get(self, n):
        if n not in self.read:
            if not self.done(n):
                self.read[n] = None
            else:
                mi = K.miscinfo(self.d, n) if WORD in self.words.get(n, ()) else None
                a = analyse(K.text(self.d, n + ".txt"), K.text(self.d, n + ".snap0.regs"),
                            K.text(self.d, n + ".snap9.regs"), mi)
                if WORD in self.words.get(n, ()) and mi is None:
                    a["mi"] = None
                k = self.readings.get(n, {}).get("kicks")
                a["kicks"] = int(k) if k not in (None, "") else None
                self.read[n] = a
        return self.read[n]


def premise_ok(a):
    """A word row's premises: the read served and the triangle after it set bit 28."""
    if a is None or a.get("mi") != 1 or a.get("cache9") is None:
        return None
    return int(a["cache9"], 16) == SET_BIT28


READ_KEYS = ("cache", "cache9", "mi", "mius", "ivl", "ccfirst", "ccn", "ccword", "ccstart")


def verdicts(stage, d):
    kp = Kept(stage, d)
    controls, per_model, lines = {}, {}, []
    preds = frozen(stage)
    for r in K.table(KP, stage):
        n = r["name"]
        a = kp.get(n)
        mine = [p for p in preds if p[0] == n]
        ctl = [p for p in mine if p[4] == "control"]
        if r["set"] == "control":
            res = {q: inside(None if a is None else a.get(q), v) for _, q, v, _, _ in ctl}
            state = None if a is None or any(v is None for v in res.values()) else \
                all(res.values())
            controls[n] = state
            lines.append(f"CONTROL {n}: " + " ".join(
                f"{q}={a.get(q) if a else None}" for _, q, _, _, _ in ctl) + ": " +
                ("PASS" if state else "FAILED" if state is False else "cannot tell"))
        for _, q, v, m, s in mine:
            if s == "control":
                continue
            got = None if a is None else a.get(q)
            st = inside(got, v)
            why = ""
            if q in PREMISED and WORD in r["knobs"]:
                p = premise_ok(a)
                if p is not True:
                    st, why = None, " (premise: the read not served or the triangle did not " \
                        "set bit 28)"
            per_model.setdefault(m, []).append(st)
            lines.append(f"ROW {n} [{s}] {m} {q}={got} (frozen {v}): "
                         + ("held" if st else "FAILED" if st is False else "cannot tell") + why)
        if a is not None:
            lines.append(f"READ {n}: " + " ".join(f"{k}={a.get(k)}" for k in READ_KEYS
                                                    if a.get(k) is not None))
    return controls, per_model, lines


CLAIMS = {
    "H-CC-FW": "CR_CACHE_CTRL stays 0x0000ffff after a served GETMISCINFO without INVAL_DATA "
               "(bit 28 is not set by any served kick)",
    "H-CC-HW": "a served GETMISCINFO without INVAL_DATA sets CR_CACHE_CTRL bit 28 (any served "
               "kick sets it)",
    "H-CC-ONE": "the triangle after the read still leaves CR_CACHE_CTRL 0x1000ffff (one change)",
    "H-CC-LAT": "the triangle's change comes 10 to 40 ms after the tool starts, as without the "
                "read",
    "H-MI-LAT": "the word's GETMISCINFO is answered in 100 to 400 us, as the boot's",
}


def read_files(stage, d):
    kp = Kept(stage, d)
    for r in K.table(KP, stage):
        kp.get(r["name"])


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0 if GATES.get(argv[2]) is None else 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) == 3 and argv[1] == "file":
        a = analyse(open(argv[2], errors="replace").read())
        print(" ".join(f"{k}={v}" for k, v in a.items()))
        return 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, per_model, lines = verdicts(argv[1], argv[2])
        print("\n".join(lines))
        for m, rows in sorted(per_model.items()):
            print(f"SUMMARY: {argv[1]} {m} [held]: " +
                  SK.headline(CLAIMS.get(m, m), controls, rows))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
