#!/usr/bin/env python3
"""The S1b review's scorer items (2026-11-10), tested first:
  4  p-c: the order-control criterion covers every config with a frozen ctl_min_frac; a missing one is cannot tell
  5  g-e1 ladder: exactly one raise -> no-raise flip per scene with usable cells on both sides, else cannot tell;
     HP1 checks the raised-threshold limit 0x2fe <= C < 0x3de
  6  S1 post-hoc fits run as `repeat`: every scorer prints repeat-only support apart from held-out support
Runs on S1's kept data (read only) with S1b's frozen predictions, and on synthetic ladders.  Prints ok/FAIL.
Run with PYTHONDONTWRITEBYTECODE=1 (the data repo's modules are imported: no __pycache__ there)."""
import sys

sys.dont_write_bytecode = True
import pathlib  # noqa: E402

S1B = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(S1B / "score"), str(S1B / "gen")]
import score_s1  # noqa: E402
import score_geo as G  # noqa: E402
import s1lib  # noqa: E402

OUT = pathlib.Path.home() / "src/scratch/resgx545/closing/s1/out"
ok = True


def check(name, fn):
    global ok
    try:
        r = fn()
        info = "" if r is None or r is True else str(r)[:200]
        good = r is not False
    except Exception as e:
        good, info = False, f"{type(e).__name__}: {str(e)[:200]}"
    print(("ok   " if good else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= good


def summ(stage, d):
    t = score_s1.run_stage(stage, OUT / d)
    return next(ln for ln in t.splitlines() if ln.startswith("SUMMARY:"))


def held_and_repeat(s):
    assert "held out:" in s and "repeat only:" in s, s
    h, r = s.split("repeat only:", 1)
    return h, r


def t4():
    s = summ("p-c", "p-c")             # S1 has c-u only; S1b freezes c-u, c-u-r2, c-u-r3
    assert "cannot tell" in s and "c-u-r2" in s, s


check("4 p-c: a frozen order control that did not run (c-u-r2, c-u-r3 on S1's data) is cannot tell", t4)


def lad(cells):
    return G.ladder_verdict({V: [(P, r) for P, r in c] for V, c in cells.items()})


P = [0x320, 0x340, 0x360, 0x380, 0x3a0, 0x3c0]
R, N, X = True, False, None          # raise, no raise, void cell


def t5a():
    v = lad({1350: list(zip(P, [R, R, R, N, N, N])), 1500: list(zip(P, [R, R, R, N, N, N]))})
    assert v.startswith("HP1") and "0x37e" in v and "0x3de" in v and "C" in v, v   # C in [0x35e, 0x37e)
    return v


def t5b():
    v = lad({1350: list(zip(P, [R] * 6)), 1500: list(zip(P, [R] * 6))})
    assert v.startswith("cannot tell") and "outside the ladder" in v, v


def t5c():
    v = lad({1350: list(zip(P, [R, R, X, N, N, N])), 1500: list(zip(P, [R, R, R, N, N, N]))})
    assert v.startswith("cannot tell") and "void" in v, v


def t5d():
    v = lad({1350: list(zip(P, [R, R, N, N, N, N])), 1500: list(zip(P, [R, R, R, R, N, N]))})
    assert v.startswith("HPS"), v


def t5e():
    v = lad({1350: list(zip(P, [R, N, R, N, N, N])), 1500: list(zip(P, [R, R, R, N, N, N]))})
    assert v.startswith("neither"), v


check("5 g-e1: one flip in both scenes at the same P is HP1, with C in [P_last - 2, P* - 2) inside the limit", t5a)
check("5 g-e1: no flip (every cell raises) is cannot tell (step outside the ladder)", t5b)
check("5 g-e1: the flip next to a void cell is cannot tell", t5c)
check("5 g-e1: one flip each, different P: HPS", t5d)
check("5 g-e1: two flips (not monotone) refutes both", t5e)


def t6_support():
    txt = s1lib.support([("HA", "heldout", True), ("HA", "repeat", True), ("HB", "repeat", True),
                         ("HC", "heldout", False), ("HC", "replicate", True)])
    h, r = held_and_repeat(txt)
    assert "HA" in h and "HB" not in h and "HB" in r and "HC" in h.split("refuted", 1)[1], txt


def t6_pc():
    import score_pix as Pm
    from s1lib import Kept, load_preds
    preds = load_preds(None, "p-c")
    for n in ("c-u-r2-x", "c-u-r2-y", "c-u-r3-x", "c-u-r3-y"):     # S1 ran c-u once: drop the two runs S1 lacks
        preds.pop(n, None)
    s = next(ln for ln in Pm.score_c(Kept(OUT / "p-c"), preds)[0].splitlines() if ln.startswith("SUMMARY"))
    h, r = held_and_repeat(s)
    assert "HQ" in r and "HQ" not in h, s


def t6_pd():
    s = summ("p-d", "p-d")
    h, r = held_and_repeat(s)
    assert "HB-A4" in r and "HB-A4" not in h.split("refuted", 1)[0], s


def t6_e5():
    s = summ("g-e5", "g-e5")
    h, r = held_and_repeat(s)
    assert "r-n8-a8:" in r and "r-n8-a8:" not in h, s


def t6_sets():
    pr = {st: s1lib.load_preds(None, st) for st in ("p-d", "p-c", "g-e5", "p-b2")}
    want = {"p-d": ["d-L2e2-64", "d-L3e3-64", "d-st-L3e2-64", "d-L2e2-21"], "p-c": ["c-k7-x", "c-k0-x", "c-k3-x"],
            "g-e5": ["r-n8-a8-r1", "r-n8-a8-r2", "r-n8-a8-r3"], "p-b2": ["d-shift", "d-tall"]}
    bad = []
    for st, ns in want.items():
        for n in ns:
            rows = [(q, m, s) for q, lst in pr[st][n].items() for v, m, s in lst]
            if any(s != "repeat" for q, m, s in rows) or not any("S1 post hoc" in m for q, m, s in rows):
                bad.append((st, n, sorted({s for q, m, s in rows})))
    assert not bad, bad


check("6 support(): repeat-only models apart from held-out ones", t6_support)
check("6 the S1 post-hoc fit jobs are frozen as `repeat`, their models named (S1 post hoc)", t6_sets)
check("6 p-c: HQ's support (k7, k0, k3: S1's fit) is repeat only", t6_pc)
check("6 p-d: HB-A4 at 64 and 21 pages (S1's fit) is repeat only", t6_pd)
check("6 g-e5: a8 with a reset (S1's fit) is repeat only", t6_e5)
sys.exit(0 if ok else 1)
