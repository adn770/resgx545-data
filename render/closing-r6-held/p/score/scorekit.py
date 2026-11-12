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
"""
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
