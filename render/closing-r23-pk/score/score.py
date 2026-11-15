#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r23-pk's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 b2b6bc0d44fc, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when the gate of STAGE is open (GATES)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

What each stage reads (t22's probe and copy output, kept as NAME.txt):
  `probe NAME: poked SPACE:N 0xOLD -> 0xNEW`   the echo: one a poke, in the pokes' order; a poke
      `S:N=V` holds when NEW = V, `S:N^=V` when NEW = OLD ^ V; a row with no poke holds with no
      echo line. A poke row whose echo does not hold is cannot tell in every model (its premise).
  `probe NAME: scratch +0xOFF 0xV`            sa(OFF / 4) of sa64_dump.s / sa_dump.s (the tool
      prints the first 32 changed dwords: sa0-sa31)
  `probe NAME: row Y: ...`                     the 2048 pixels: their sha256 as E568's
      (tx-formats.sh: 8 hex digits a pixel, raster order, comma joined)
  `probe NAME: o0 0xV (2048 of 2048)`          a uniform o0; `o0 mixed` is no single value
  `probe NAME: placed words read back: K of N`  the placed program as built (premise)
  `target: WxH hash 0xH`                       the copy's target hash (E037)

Models (predictions/STAGE.tsv): H-ECHO (pk's controls), H-E391 / H-E125 / H-NOLOAD / H-LOAD
(the repeats against their records), H-E391 and H-ROWS (q019: H-ROWS is fitted here on the fit
rows, 0, 1 and 4 rows, its table's sha256 printed before any held-out row is read, and holds on a
held-out row when the arriving count at 2 rows lies between those at 1 and 4 rows of the same run
and attribute set, and at 8 rows is at least that at 4), H-NOLOAD / H-LOAD (q181), H-CARRY18,
H-WRAP, H-WRAP17, H-EXE18, H-EXE16 (q123, q123h).

REQUIRED: the files each stage's scorer reads; read_files(STAGE, DIR) reads exactly what
verdicts() reads; producible(row) is the set of reading keys a row's job can produce."""
import hashlib
import os
import re
import shlex
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {s: (".txt",) + FIXED for s in ("pk", "q019", "q181", "q123", "q123h")}
GATES = {"q019": "pk", "q181": "pk", "q123h": "q123"}
Q123H_NEEDS = {"b16-run": "H-CARRY18", "b16-ba": "H-CARRY18", "b16-lapc": "H-CARRY18",
               "b16-long": "H-CARRY18", "x18-b16": "H-EXE18"}


def producible(row):
    a = row["args"].split()
    if a[:1] == ["copy"]:
        return {"hash"}
    if a[:1] == ["probe"]:
        return {"echo", "o0"} | ({"placed"} if "--place" in a else set())
    return set()


# ---- readers ----------------------------------------------------------------------------------
_POKED = re.compile(r"^probe \S+: poked (\w+):(\d+) 0x([0-9a-f]{8}) -> 0x([0-9a-f]{8})$")
_SCR = re.compile(r"^probe \S+: scratch \+0x([0-9a-f]+) 0x([0-9a-f]{8})$")
_ROW = re.compile(r"^probe \S+: row (\d+): ([0-9a-f ]+)$")
_O0 = re.compile(r"^probe \S+: o0 0x([0-9a-f]{8}) \((\d+) of (\d+)\)$")
_PLACED = re.compile(r"^probe \S+: placed words read back: (\d+) of (\d+) as built")
_HASH = re.compile(r"^target: \d+x\d+ hash (0x[0-9a-f]{16})$")
_SPEC = re.compile(r"^(\w+):(\d+)(\^?)=(0x[0-9a-fA-F]+|\d+)$")


def pokes(args):
    a = shlex.split(args.replace("$S", "/s").replace("$W", "/w"))
    return [a[i + 1] for i, x in enumerate(a) if x == "--poke"]


def echo(text):
    """[(space, index, old, new)] of the echo lines."""
    return [(m[1], int(m[2]), int(m[3], 16), int(m[4], 16))
            for m in map(_POKED.match, text.splitlines()) if m]


def echo_state(args, text):
    """(True, False or None, reading): every poke echoed with the word it sent."""
    want, got = pokes(args), echo(text)
    if not text:
        return None, "no output"
    if len(got) != len(want):
        return False, f"{len(got)} of {len(want)} pokes echoed"
    for spec, (sp, ix, old, new) in zip(want, got):
        m = _SPEC.match(spec)
        if not m or (m[1], int(m[2])) != (sp, ix):
            return False, f"echo {sp}:{ix} for poke {spec}"
        v = int(m[4], 0)
        if new != ((old ^ v) if m[3] else v):
            return False, f"{spec}: 0x{old:08x} -> 0x{new:08x}"
    return True, ",".join(f"{sp}:{ix}=0x{new:08x}" for sp, ix, _, new in got) or "-"


def scratch(text):
    return {int(m[1], 16) // 4: int(m[2], 16) for m in map(_SCR.match, text.splitlines()) if m}


def pixsha(text):
    vals = []
    for m in map(_ROW.match, text.splitlines()):
        if m:
            vals += [v.rjust(8, "0") for v in m[2].split()]
    if len(vals) != 2048:
        return None
    return hashlib.sha256(",".join(vals).encode()).hexdigest()


def o0(text):
    for m in map(_O0.match, text.splitlines()):
        if m and m[2] == m[3]:
            return int(m[1], 16)
    return None


def placed(text):
    for m in map(_PLACED.match, text.splitlines()):
        if m:
            return f"{m[1]}/{m[2]}"
    return None


def copy_hash(text):
    for m in map(_HASH.match, text.splitlines()):
        if m:
            return m[1]
    return None


def arrive(sa, markers, lo):
    """(own, stray): markers at their own sa (attribute lo + k), markers anywhere else in the
    shown sa0-sa31."""
    own = stray = 0
    for k, mk in enumerate(markers):
        at = [i for i, v in sa.items() if v == mk]
        own += (lo + k) in at
        stray += sum(1 for i in at if i != lo + k)
    return own, stray


# ---- the stage's kept files -------------------------------------------------------------------
class Run:
    def __init__(self, stage, d):
        self.stage, self.d = stage, d
        self.cases = K.rows(d, "cases.tsv")
        K.rows(d, "void.tsv")
        self.table = K.table(KP, stage)
        self.preds = K.predictions(KP, stage)

    def text(self, n):
        r = self.cases.get(n)
        if r is None or not K.completed(r):
            return ""
        return K.text(self.d, n + ".txt")


def _st(v):
    return "held" if v is True else "FAILED" if v is False else "cannot tell"


def _models(preds, n, q):
    return {m: v for m, v in preds.get(n, {}).get(q, {}).items()}


def _row(lines, per_model, n, res):
    for m, (v, why) in sorted(res.items()):
        per_model.setdefault(m, []).append(v)
        lines.append(f"ROW {n} {m}: {_st(v)} ({why})")


def markers_of(r, n):
    v = _models(r.preds, n, "own")
    for m in ("H-E391", "H-E125"):
        if m in v and "," in v[m]:
            return [int(x, 16) for x in v[m].split(",")]
    return None


# ---- stages -------------------------------------------------------------------------------------
def _pk(r, controls, per_model, lines):
    for row in r.table:
        n, t = row["name"], r.text(row["name"])
        ok, why = echo_state(row["args"], t)
        controls[n] = ok
        lines.append(f"CONTROL {n}: echo {why}: {'PASS' if ok else _st(ok)}")
        if not t:
            continue
        mk = markers_of(r, n)
        if mk is not None:
            own, stray = arrive(scratch(t), mk, 0)
            m = "H-E391" if n == "pk-e391" else "H-E125"
            v = (own == 16 and stray == 0) if ok else None
            _row(lines, per_model, n, {m: (v, f"own {own} of 16, stray {stray}")})
        if n == "pk-e568":
            sha = pixsha(t)
            res = {m: ((sha == want) if ok and sha else None, f"pixels {sha}")
                   for m, want in _models(r.preds, n, "pixsha").items()}
            _row(lines, per_model, n, res)


def q019_reading(r, row):
    """(echo ok, own, stray, first attribute, run, rows) of a q019 row; own None unread."""
    n = row["name"]
    m = re.match(r"q019-(\d)-r(\d)-a(\d\d)$", n)
    run, rows, lo = int(m[1]), int(m[2]), int(m[3])
    t = r.text(n)
    if not t:
        return None, None, None, lo, run, rows
    ok, _ = echo_state(row["args"], t)
    own, stray = arrive(scratch(t), q019_markers(lo, run, rows), lo)
    return ok, own, stray, lo, run, rows


def q019_markers(lo, run, rows):
    """attribute-room's markers: 0xa<run><rows:x>0000 + attribute (probes/pds/attribute-room.toml)."""
    return [0xA0000000 | run << 24 | rows << 16 | (lo + k) for k in range(16)]


def _q019(r, controls, per_model, lines):
    got = {}
    for row in r.table:
        ok, own, stray, lo, run, rows = q019_reading(r, row)
        got[(run, rows, lo)] = own if ok else None
        n = row["name"]
        if ok is not True:
            why = "not run" if own is None else "echo does not hold (premise)"
            _row(lines, per_model, n, {"H-E391": (None, why)})
            continue
        want = 16 if lo < 32 else 0
        _row(lines, per_model, n, {"H-E391": (own == want and stray == 0,
                                              f"own {own} (frozen {want}), stray {stray}")})
    fit = sorted((k, v) for k, v in got.items() if k[1] in (0, 1, 4))
    lines.append("H-ROWS fit (0, 1, 4 rows): sha256 " +
                 hashlib.sha256(repr(fit).encode()).hexdigest() + " " +
                 " ".join(f"{run}/{rows}/{lo}={v}" for (run, rows, lo), v in fit))
    for row in r.table:
        n = row["name"]
        m = re.match(r"q019-(\d)-r(\d)-a(\d\d)$", n)
        run, rows, lo = int(m[1]), int(m[2]), int(m[3])
        if rows not in (2, 8):
            continue
        v = got.get((run, rows, lo))
        a1, a4 = got.get((run, 1, lo)), got.get((run, 4, lo))
        if v is None or a4 is None or (rows == 2 and a1 is None):
            _row(lines, per_model, n, {"H-ROWS": (None, "a fit or held-out count unread")})
            continue
        ok = (min(a1, a4) <= v <= max(a1, a4)) if rows == 2 else v >= a4
        _row(lines, per_model, n, {"H-ROWS": (ok, f"own {v}; fit 1 rows {a1}, 4 rows {a4}")})


def _q181(r, controls, per_model, lines):
    for row in r.table:
        n, t = row["name"], r.text(row["name"])
        if row["set"] == "control":
            h = copy_hash(t)
            want = _models(r.preds, n, "hash").get("H-E037")
            controls[n] = None if h is None else h == want
            lines.append(f"CONTROL {n}: hash {h} (frozen {want}): "
                         f"{'PASS' if controls[n] else _st(controls[n])}")
            continue
        ok, why = echo_state(row["args"], t) if t else (None, "not run")
        sha = pixsha(t) if ok else None
        res = {m: (None if sha is None else sha == want, f"pixels {sha}; echo {why}")
               for m, want in _models(r.preds, n, "pixsha").items()}
        _row(lines, per_model, n, res)


def q123_reading(r, row):
    t = r.text(row["name"])
    return (o0(t), placed(t)) if t else (None, None)


def _q123(r, controls, per_model, lines):
    for row in r.table:
        n = row["name"]
        v, pl = q123_reading(r, row)
        want_pl = _models(r.preds, n, "placed").get("H-PLACED")
        models = _models(r.preds, n, "o0")
        ok_pl = pl == want_pl
        if row["set"] == "control":
            want = models["H-CARRY18"]
            controls[n] = None if v is None or pl is None else (ok_pl and f"0x{v:08x}" == want)
            lines.append(f"CONTROL {n}: o0 {v if v is None else hex(v)} (frozen {want}), placed "
                         f"{pl}: {'PASS' if controls[n] else _st(controls[n])}")
            continue
        why = f"o0 {v if v is None else f'0x{v:08x}'}, placed {pl}"
        _row(lines, per_model, n, {m: (None if v is None or not ok_pl else f"0x{v:08x}" == want,
                                       why) for m, want in models.items()})


SCORERS = {"pk": _pk, "q019": _q019, "q181": _q181, "q123": _q123, "q123h": _q123}


def verdicts(stage, d):
    r = Run(stage, d)
    controls, per_model, lines = {}, {}, []
    SCORERS[stage](r, controls, per_model, lines)
    return controls, per_model, lines


def read_files(stage, d):
    verdicts(stage, d)


def gate_q123h(d):
    """q123h's gate: q123's controls passed, and every bit-16 crossing and the exe18 start read
    the model that leaves only mapped landings at bit 17."""
    controls, _, lines = verdicts("q123", d)
    g = SK.gate(controls)
    problems = list(g.problems)
    for n, m in Q123H_NEEDS.items():
        hit = [ln for ln in lines if ln.startswith(f"ROW {n} {m}: ")]
        if not hit or not hit[0].split(": ", 1)[1].startswith("held"):
            problems.append(f"{n}: {m} not held")
    return not problems, problems


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        dep = GATES.get(argv[2])
        if dep is None:
            return 0
        for root in argv[3:]:
            d = os.path.join(root, dep)
            if os.path.isdir(d):
                if argv[2] == "q123h":
                    ok, problems = gate_q123h(d)
                else:
                    g = SK.gate(verdicts(dep, d)[0])
                    ok, problems = g.ok, g.problems
                print(f"gate {argv[2]} on {dep}: {'open' if ok else '; '.join(problems)}")
                return 0 if ok else 1
        print(f"gate {argv[2]}: {dep} has not run")
        return 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, per_model, lines = verdicts(argv[1], argv[2])
        print("\n".join(lines))
        g = SK.gate(controls) if controls else None
        print("SUMMARY: " + argv[1] + ": controls " + ("none in this stage" if g is None else
                                                         "all passed" if g.ok else
                                                         "; ".join(g.problems)))
        for m, states in sorted(per_model.items()):
            h = SK.headline(m, controls or {"(gate)": True}, states)
            print("SUMMARY: " + argv[1] + ": " + (h if h.startswith(m) else f"{m}: {h}"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
