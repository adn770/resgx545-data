#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r25-sa64's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 134103452432, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when the gate of STAGE is open (GATES)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

What each stage reads (t24's probe output, kept as NAME.txt):
  `probe NAME: poked SPACE:N 0xOLD -> 0xNEW`   the echo: one a poke, in the pokes' order; a poke
      `S:N=V` holds when NEW = V, `S:N^=V` when NEW = OLD ^ V. A poke row whose echo does not hold
      is cannot tell in every model (its premise).
  `probe NAME: scratch +0xOFF 0xV`            sa(OFF / 4) of sa64_dump.s / sa_dump.s: with
      --scratch-show 64 the first 64 changed dwords (sa0-sa63 when all changed)
  `probe NAME: scratch K more changed`         more than 64 changed (none expected: sa64_dump.s
      stores 64 dwords); a row whose print stops below 64 lines with this line did not take
      --scratch-show 64 (premise, H-SHOW)

Models (predictions/STAGE.tsv): pk64: H-ECHO, H-E391 / H-E125 (sa0-sa15 their markers, stray 0),
H-SHOW (lines shown / more): the control of each row is all of them. q019: H-E391 (the markers in
sa0-sa31 as E1096 read them: own_lo 16 for attributes 0-31, 0 for 32-63, no stray in sa0-sa31),
H-ALL64 (own 16 over sa0-sa63 for every set, no stray), H-NONE (own 16 for 0-31, 0 for 32-63, no
stray), H-ROWS (fitted here on 0, 1 and 4 rows, its table's sha256 printed before any held-out row
is read; holds on a held-out row when its count at 2 or 3 rows lies between those at 1 and 4 rows
of the same run and set, at 6 or 8 rows is at least that at 4 rows).

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
REQUIRED = {s: (".txt",) + FIXED for s in ("pk64", "q019")}
GATES = {"q019": "pk64"}
FIT, LOW, HIGH = (0, 1, 4), (2, 3), (6, 8)
SHOW = 64


def producible(row):
    a = row["args"].split()
    if a[:1] == ["probe"]:
        return {"echo", "shown"}
    return set()


# ---- readers ----------------------------------------------------------------------------------
_POKED = re.compile(r"^probe \S+: poked (\w+):(\d+) 0x([0-9a-f]{8}) -> 0x([0-9a-f]{8})$")
_SCR = re.compile(r"^probe \S+: scratch \+0x([0-9a-f]+) 0x([0-9a-f]{8})$")
_MORE = re.compile(r"^probe \S+: scratch (\d+) more changed$")
_SPEC = re.compile(r"^(\w+):(\d+)(\^?)=(0x[0-9a-fA-F]+|\d+)$")
_NAME = re.compile(r"q019-(\d)-r(\d)-a(\d\d)$")


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


def shown(text):
    """(scratch lines, the `more changed` count or 0)."""
    n = sum(1 for ln in text.splitlines() if _SCR.match(ln))
    more = [int(m[1]) for m in map(_MORE.match, text.splitlines()) if m]
    return n, (more[0] if more else 0)


def show_ok(text):
    """The print took --scratch-show 64: no `more changed` line unless 64 lines were shown."""
    n, more = shown(text)
    return not more or n == SHOW


def arrive(sa, markers, lo, upto=SHOW):
    """(own, stray): markers at their own sa (attribute lo + k), markers at any other shown sa
    below upto."""
    own = stray = 0
    for k, mk in enumerate(markers):
        at = [i for i, v in sa.items() if v == mk and i < upto]
        own += (lo + k) in at
        stray += sum(1 for i in at if i != lo + k)
    return own, stray


def q019_markers(lo, run, rows):
    """attribute-room's markers: 0xa<run><rows:02x>0000 + attribute (gen/make.py markers)."""
    return [0xA0000000 | run << 24 | rows << 16 | (lo + k) for k in range(16)]


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
    return dict(preds.get(n, {}).get(q, {}))


def _row(lines, per_model, n, res):
    for m, (v, why) in sorted(res.items()):
        per_model.setdefault(m, []).append(v)
        lines.append(f"ROW {n} {m}: {_st(v)} ({why})")


# ---- stages -------------------------------------------------------------------------------------
def _pk64(r, controls, per_model, lines):
    for row in r.table:
        n, t = row["name"], r.text(row["name"])
        ok, why = echo_state(row["args"], t)
        m = "H-E391" if n == "pk-e391" else "H-E125"
        mk = [int(x, 16) for x in _models(r.preds, n, "own")[m].split(",")]
        own, stray = arrive(scratch(t), mk, 0) if t else (None, None)
        sh, more = shown(t)
        want_sh = _models(r.preds, n, "shown")["H-SHOW"]
        sh_ok = f"{sh}/{more}" == want_sh
        mk_ok = own == 16 and stray == 0
        controls[n] = None if not t else bool(ok and sh_ok and mk_ok)
        lines.append(f"CONTROL {n}: echo {why}; sa0-sa15 own {own} of 16, stray {stray}; shown "
                     f"{sh}/{more} (frozen {want_sh}): "
                     f"{'PASS' if controls[n] else _st(controls[n])}")
        if t:
            _row(lines, per_model, n, {m: (mk_ok if ok else None, f"own {own}, stray {stray}"),
                                       "H-SHOW": (sh_ok, f"shown {sh}/{more}")})


def q019_reading(r, row):
    """(premise ok, own_lo, stray_lo, own, stray, lo, run, rows); counts None when unread."""
    m = _NAME.match(row["name"])
    run, rows, lo = int(m[1]), int(m[2]), int(m[3])
    t = r.text(row["name"])
    if not t:
        return None, None, None, None, None, lo, run, rows
    ok = echo_state(row["args"], t)[0] is True and show_ok(t)
    sa, mk = scratch(t), q019_markers(lo, run, rows)
    own_lo, stray_lo = arrive(sa, mk, lo, 32)
    own, stray = arrive(sa, mk, lo)
    return ok, own_lo, stray_lo, own, stray, lo, run, rows


def _q019(r, controls, per_model, lines):
    got = {}
    for row in r.table:
        n = row["name"]
        ok, own_lo, stray_lo, own, stray, lo, run, rows = q019_reading(r, row)
        got[(run, rows, lo)] = own if ok else None
        if ok is not True:
            why = "not run" if ok is None else "echo or print does not hold (premise)"
            _row(lines, per_model, n, {m: (None, why) for m in ("H-E391", "H-ALL64", "H-NONE")})
            continue
        lo16 = 16 if lo < 32 else 0
        _row(lines, per_model, n, {
            "H-E391": (own_lo == lo16 and stray_lo == 0,
                       f"sa0-sa31 own {own_lo} (frozen {lo16}), stray {stray_lo}"),
            "H-ALL64": (own == 16 and stray == 0, f"sa0-sa63 own {own} (frozen 16), stray {stray}"),
            "H-NONE": (own == lo16 and stray == 0,
                       f"sa0-sa63 own {own} (frozen {lo16}), stray {stray}")})
    fit = sorted((k, v) for k, v in got.items() if k[1] in FIT)
    flat = all(len({got.get((run, x, lo)) for x in FIT}) == 1
               for run in (1, 2) for lo in (0, 16, 32, 48))
    lines.append("H-ROWS fit (0, 1, 4 rows): sha256 " +
                 hashlib.sha256(repr(fit).encode()).hexdigest() + " " +
                 " ".join(f"{run}/{rows}/{lo}={v}" for (run, rows, lo), v in fit))
    lines.append(f"H-ROWS fit table flat: {'yes' if flat else 'no'}")
    for row in r.table:
        n = row["name"]
        m = _NAME.match(n)
        run, rows, lo = int(m[1]), int(m[2]), int(m[3])
        if rows in FIT:
            continue
        v = got.get((run, rows, lo))
        a1, a4 = got.get((run, 1, lo)), got.get((run, 4, lo))
        if v is None or a4 is None or (rows in LOW and a1 is None):
            _row(lines, per_model, n, {"H-ROWS": (None, "a fit or held-out count unread")})
            continue
        ok = (min(a1, a4) <= v <= max(a1, a4)) if rows in LOW else v >= a4
        _row(lines, per_model, n, {"H-ROWS": (ok, f"own {v}; fit 1 rows {a1}, 4 rows {a4}")})


SCORERS = {"pk64": _pk64, "q019": _q019}


def verdicts(stage, d):
    r = Run(stage, d)
    controls, per_model, lines = {}, {}, []
    SCORERS[stage](r, controls, per_model, lines)
    return controls, per_model, lines


def read_files(stage, d):
    verdicts(stage, d)


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        dep = GATES.get(argv[2])
        if dep is None:
            return 0
        for root in argv[3:]:
            d = os.path.join(root, dep)
            if os.path.isdir(d):
                g = SK.gate(verdicts(dep, d)[0])
                print(f"gate {argv[2]} on {dep}: {'open' if g.ok else '; '.join(g.problems)}")
                return 0 if g.ok else 1
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
