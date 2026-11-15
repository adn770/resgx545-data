# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""scorekit.py: the shared verdict rules of a closing-session scorer (HACKING.md, "Closing-session
scorers"). Standard library only. A session copies this file byte for byte into its own
`score/scorekit.py`, so the session's freeze pins it, and states the commit it copied it from.

Row states: True (held), False (FAILED), None (cannot tell). A void job is a None row and never
a pass. Control states: True or "PASS" passes; False, "FAIL" or "FAILED" fails; None, "NODATA",
"VOID" or "cannot tell" cannot tell. Anything else is refused, so a tuple or a misspelt state
cannot pass a gate by being truthy.

- bracket(points): the (last clear, first set] bracket of a ladder of (N, state) points, N
  ascending or not. A void point (state None) never narrows it: one between the last clear and
  the first set point widens the bracket and is listed in `void_inside`. No point clear: the
  bracket is open below (lo None); no point set: open above (hi None).
- overlaps(bracket, window): the strict test of a predicted window [flo, fhi] against a bracket
  (lo, hi]. None is an open end, never zero or infinity; there is no slack.
- point_verdict(bracket, allowed): an exact-point hypothesis (the first set point is one of
  `allowed`). False only when every allowed point lies outside the bracket; True only when the
  bracket is closed, monotone and every point it could hold (its void points and hi) is allowed;
  None otherwise.
- gate(controls) / gated(gate, row): any control that is not a pass (FAILED, NODATA, cannot
  tell) shuts the gate, and a shut gate makes every dependent row cannot tell. No control at all
  shuts it too.
- tally(rows), combine(replicates): held, FAILED and cannot tell counted apart; replicates that
  disagree are "mixed", never "held".
- headline(claim, controls, rows): the claim only when every control passed and at least one
  row was decided, with the count of decided rows; otherwise what stopped it.
- control_read_problems(controls, producible) / refuse_unreadable(...): the generator side. A
  control declares the readings it needs; one whose row's job cannot produce one of them (r6-dpm:
  "grow" on a job with no partial render) or that declares none is refused before the freeze.
- premise_stops(controls, readings): the run side. A control with no reading of a key it
  declared (None, "" or "-"), or that did not run, STOPS the session at the premise stage; it
  never reaches a gate to shut it silently.
- missing_files(required, kept_dir, rows): the files a scorer reads (its REQUIRED: ".suffix"
  per row that ended ok, "CLASS:.suffix" per row that ended CLASS (ok, fault or hang) and
  "any:.suffix" per row, any other name once) that the kept directory lacks, kept plain or
  gzipped; rows a list of names (each ended ok) or {name: class} (the runner's cases.tsv).
"""
import os
from dataclasses import dataclass, field

PASS_STATES = {True, "PASS"}
FAIL_STATES = {False, "FAIL", "FAILED"}
OPEN_STATES = {None, "NODATA", "VOID", "cannot tell"}


# ---- brackets ------------------------------------------------------------------------------
@dataclass(frozen=True)
class Bracket:
    lo: float | None          # the last clear point below hi (exclusive); None: open below
    hi: float | None          # the first set point (inclusive); None: open above
    monotone: bool            # no clear point above hi
    void_inside: tuple = ()   # void points strictly between lo and hi (or past an open end)
    usable: int = 0           # points that were not void


def bracket(points):
    """The (last clear, first set] bracket of (N, state) points; state True set, False clear,
    None void."""
    pts = sorted(points, key=lambda p: p[0])
    used = [(n, s) for n, s in pts if s is not None]
    sets = [n for n, s in used if s is True]
    hi = sets[0] if sets else None
    clears = [n for n, s in used if s is False and (hi is None or n < hi)]
    lo = clears[-1] if clears else None
    monotone = hi is None or not any(s is False and n > hi for n, s in used)
    if not used:
        lo = hi = None
    inside = tuple(n for n, s in pts if s is None and (lo is None or n > lo)
                   and (hi is None or n < hi))
    return Bracket(lo, hi, monotone, inside, len(used))


def _ends(b):
    if isinstance(b, Bracket):
        return b.lo, b.hi
    lo, hi = b
    return lo, hi


def overlaps(b, window):
    """Whether a first set point in the bracket (lo, hi] can lie in the window [flo, fhi]."""
    lo, hi = _ends(b)
    flo, fhi = window
    if flo is not None and fhi is not None and flo > fhi:
        raise ValueError(f"window {window} is reversed")
    below_ok = hi is None or flo is None or flo <= hi
    above_ok = lo is None or fhi is None or fhi > lo
    return below_ok and above_ok


def contains(b, window):
    """Whether the whole bracket lies inside the window: NOT the test of a prediction (a bracket
    that only overlaps a window does not refute it); kept to name the difference."""
    lo, hi = _ends(b)
    flo, fhi = window
    lo_in = flo is None or (lo is not None and lo >= flo)
    hi_in = fhi is None or (hi is not None and hi <= fhi)
    return lo_in and hi_in


def point_verdict(b, allowed):
    """An exact-point hypothesis against a bracket: True, False or None (cannot tell)."""
    if b.usable == 0 or not b.monotone:
        return None
    allowed = set(allowed)
    inside = [p for p in allowed if (b.lo is None or p > b.lo) and (b.hi is None or p <= b.hi)]
    if not inside:
        return False
    if b.lo is None or b.hi is None:
        return None
    possible = set(b.void_inside) | {b.hi}
    return True if possible <= allowed else None


# ---- controls ------------------------------------------------------------------------------
def _state(v):
    if not isinstance(v, (bool, str, type(None))):
        raise TypeError(f"control state {v!r} is not True, False, None or a state word")
    if v in PASS_STATES:
        return "PASS"
    if v in FAIL_STATES:
        return "FAILED"
    if v in OPEN_STATES:
        return "cannot tell" if v is None else v
    raise ValueError(f"control state {v!r} is not a state word")


@dataclass
class Gate:
    ok: bool
    failed: list = field(default_factory=list)
    problems: list = field(default_factory=list)


def gate(controls):
    """Every control must pass; FAILED, NODATA and cannot tell all shut the gate."""
    g = Gate(ok=True)
    if not controls:
        return Gate(ok=False, problems=["no control"])
    for name, v in controls.items():
        s = _state(v)
        if s == "PASS":
            continue
        g.ok = False
        if s == "FAILED":
            g.failed.append(name)
        g.problems.append(f"{name}: {s}")
    return g


def gated(g, row):
    """A dependent row as the gate lets it through: unchanged, or cannot tell."""
    return row if g.ok else None


# ---- tallies -------------------------------------------------------------------------------
@dataclass(frozen=True)
class Tally:
    held: int
    failed: int
    cannot_tell: int

    @property
    def decided(self):
        return self.held + self.failed

    @property
    def total(self):
        return self.decided + self.cannot_tell

    def verdict(self):
        """None with no decided row, False with any FAILED row, True otherwise."""
        if self.decided == 0:
            return None
        return self.failed == 0

    def __str__(self):
        return (f"{self.held} held, {self.failed} FAILED, {self.cannot_tell} cannot tell"
                f" of {self.total}")


def tally(rows):
    rows = list(rows)
    for r in rows:
        if not isinstance(r, (bool, type(None))):
            raise TypeError(f"row state {r!r} is not True, False or None")
    return Tally(sum(1 for r in rows if r is True), sum(1 for r in rows if r is False),
                 sum(1 for r in rows if r is None))


def combine(reps):
    """Replicates of one row: held, refuted, mixed or cannot tell."""
    reps = list(reps)
    if not reps or any(r is None for r in reps):
        return "cannot tell"
    if all(r is True for r in reps):
        return "held"
    if all(r is False for r in reps):
        return "refuted"
    return "mixed"


# ---- headlines -----------------------------------------------------------------------------
def headline(claim, controls, rows):
    """The stage's headline: the claim with its count of decided rows, or why it cannot be
    printed (a FAILED control, no decided row, a control that cannot tell, a FAILED row)."""
    g = gate(controls)
    t = tally(rows)
    if g.failed:
        return "controls FAILED: " + "; ".join(g.problems)
    if t.decided == 0:
        return "cannot tell: no row decided" + ("; controls: " + "; ".join(g.problems)
                                               if g.problems else "")
    if not g.ok:
        return "cannot tell: controls: " + "; ".join(g.problems)
    if t.failed:
        return f"{claim} is not supported: {t}"
    return f"{claim} ({t.decided} of {t.total} rows decided)"


# ---- what a control reads --------------------------------------------------------------------
NO_READING = (None, "", "-")


class ControlReadError(ValueError):
    """A control that cannot produce the reading it is frozen on."""


def _keys(reads, name):
    if isinstance(reads, str):
        raise TypeError(f"control {name}: reads {reads!r} is a string, not a tuple of keys")
    return tuple(reads)


def control_read_problems(controls, producible):
    """controls: {name: (reads, row)}; producible(row): the reading keys the row's job can
    produce. A problem for every key a control reads that its row cannot produce, and for a
    control that reads nothing."""
    out = []
    for name, (reads, row) in controls.items():
        keys = _keys(reads, name)
        if not keys:
            out.append(f"control {name} declares no reading: it cannot fail")
            continue
        can = set(producible(row))
        out += [f"control {name} reads {k}, which its row cannot produce"
                for k in keys if k not in can]
    return out


def refuse_unreadable(controls, producible):
    """The generator's check: raise ControlReadError naming every unreadable control."""
    probs = control_read_problems(controls, producible)
    if probs:
        raise ControlReadError("; ".join(probs))


def premise_stops(controls, readings):
    """controls: {name: reads}; readings: {name: {key: value}} of the run. The STOP lines of the
    premise stage, empty when every control has every reading it declared."""
    out = []
    for name, reads in controls.items():
        keys = _keys(reads, name)
        if name not in readings:
            out.append(f"STOP: premise: control {name} did not run")
            continue
        r = readings[name]
        out += [f"STOP: premise: control {name} has no reading of {k}"
                for k in keys if k not in r or r[k] in NO_READING]
    return out


# ---- files a scorer reads --------------------------------------------------------------------
# the classes a REQUIRED entry "CLASS:.suffix" may name (the runner's ends of a row), and "any"
ROW_CLASSES = ("ok", "fault", "hang", "any")


def required_entry(entry):
    """(class, suffix) of a per-row REQUIRED entry (".suffix" is ok's), (None, name) of a stage
    file, or None for an entry of neither form (an unknown class, a suffix without its dot)."""
    cls, sep, rest = entry.partition(":")
    if not sep:
        return ("ok", entry) if entry.startswith(".") else (None, entry)
    return (cls, rest) if cls in ROW_CLASSES and rest.startswith(".") and len(rest) > 1 else None


def row_files(required, rows, every_class=False):
    """NAME.suffix of every per-row entry of `required` that applies to each row's class (all of
    them with every_class); rows a list of names (each ok) or {name: class}."""
    rows = rows if isinstance(rows, dict) else {n: "ok" for n in rows}
    per = [e for e in map(required_entry, required) if e and e[0]]
    return [n + s for n, c in rows.items() for k, s in per
            if every_class or k in ("any", c)]


def missing_files(required, kept_dir, rows):
    """The files of `required` (".suffix": NAME.suffix for every row that ended ok, "CLASS:.suffix"
    for every row that ended CLASS, "any:.suffix" for every row; any other name: that file) not
    in kept_dir, plain or with ".gz". Per-row files and no row: "(no row)"."""
    def kept(f):
        p = os.path.join(kept_dir, f)
        return os.path.exists(p) or os.path.exists(p + ".gz")
    rows = rows if isinstance(rows, dict) else list(rows)
    fixed = [f for f in required if (required_entry(f) or ("x",))[0] is None]
    per = [f for f in required if (required_entry(f) or (None,))[0]]
    out = [f for f in fixed if not kept(f)]
    if per and not rows:
        return out + ["(no row)"]
    return out + [f for f in row_files(required, rows) if not kept(f)]
