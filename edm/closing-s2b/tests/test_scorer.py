#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""test_scorer.py: the S2 scorer's readers and classifiers on synthetic pages (every shape of E4, the E1 decision on
the fill, the dispatch rule, the void rules).  Exit 0 when every check holds.

    ../pixel-faults/.venv/bin/python tests/test_scorer.py
"""
import pathlib
import sys

S2 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(S2 / "gen"))
sys.path.insert(0, str(S2 / "score"))
import s2layout as L  # noqa: E402
import score_s2 as S  # noqa: E402

FAIL = []
T = S.T


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


def page_with(entries, E=None, X=None, drops=0):
    p = [0] * L.PAGE_DWORDS
    p[0] = L.MAGIC
    for j, (pa0, pa1, st) in enumerate(entries[:L.RUNGS[0]]):
        o = L.RING_BASE[0] + 8 * j
        p[o:o + 5] = [1, pa0, pa1, L.PA2_CONST, st & 0xFFFFFFFF]
    p[L.DROP] = drops
    p[L.HOLD_ENTRY] = E if E is not None else L.INITFILL
    p[L.HOLD_EXIT] = X if X is not None else L.INITFILL
    return {"page": p, "page2": list(p), "class": "ok", "rc": 0}


def tick(st):
    return (2, L.TICK_PA1, st)


def shape(entries, E, X, drops=0):
    return S.hold_shape(page_with(entries, E, X, drops))[0]


base = 0xFFFF0000            # stamps that wrap through 2^32 inside the job
H = 4 * T + 9000             # a hold of about four ticks and a third
E, X = base + 300, base + 300 + H
pre = [tick(base - T), tick(base)]
grid_after = [tick(base + k * T) for k in range(5, 9)]
check(shape(pre + grid_after, E, X) == "LOST", "LOST: nothing at the exit, the grid resumes (across a 2^32 wrap)")
check(shape(pre + [tick(X + 40)] + grid_after, E, X) == "ONE", "ONE: one entry at the exit, then the grid")
check(shape(pre + [tick(X + 40 + 300 * i) for i in range(4)] + grid_after, E, X) == "ALL", "ALL: floor(H) back to back")
check(shape(pre + [tick(X + 40 + 300 * i) for i in range(3)] + grid_after, E, X) == "ALL",
      "three of four at the exit: ALL by the frozen rule (|q - floorH| <= 1)")
Xg = base + 5 * T - 600                   # S2b: only a grid tick just AFTER the exit is ambiguous (one-sided guard)
check(shape(pre + [tick(Xg + 40)] + grid_after, E, Xg).startswith("cannot tell"),
      "cannot tell: a grid tick 600 units after the exit (a pending tick and a natural one look alike)")
long_X = base + 300 + 20 * T + 9000
check(shape(pre + [tick(long_X + 40 + 300 * i) for i in range(3)] + [tick(base + k * T) for k in range(22, 25)],
            E, long_X) == "PARTIAL(3)", "PARTIAL: 3 at the exit of a 20-tick hold")
check(shape(pre + [tick(E + T)] + grid_after, E, X) == "OVERLAP", "OVERLAP: a pass inside the hold")
check(shape(pre + [tick(X + 40)] + [tick(X + 40 + 7000 * k) for k in range(1, 4)], E, X).endswith("/offgrid"),
      "/offgrid: the grid after the exit is not the old phase")
check(shape([tick(X + 40)], E, X).startswith("cannot tell"), "cannot tell: no pass before the hold")
full = pre + [tick(base + 300 + i) for i in range(1, 15)]
check(shape(pre[:1] + [tick(base - T + 200 * i) for i in range(1, 16)], E, X).startswith("cannot tell"),
      "cannot tell: the ring full before the exit")
check(S.hold_shape(page_with(pre, E, None))[0] == "NODATA", "NODATA: no exit stamp")
# a down-counting CR_TIMER (the p1141 draft's assumption) and a 25-bit wrap (neither is recorded): the same shapes
M25 = 1 << 25
dn = lambda s: (0x1000000 - s) % M25          # time t -> a 25-bit down-counter that wraps during the job
tb = 0x1000000 - 600                         # so that the stamps cross 0 -> 2^25 - 1
check(S.rel(5, M25 - 5) == 10 and S.rel(M25 - 5, 5) == -10, "rel across a 2^25 wrap")
Ed, Xd = dn(tb + 300), dn(tb + 300 + H)
pre_d = [tick(dn(tb - T)), tick(dn(tb))]
after_d = [tick(dn(tb + k * T)) for k in range(5, 9)]
check(shape(pre_d + [tick(dn(tb + 300 + H + 40))] + after_d, Ed, Xd) == "ONE", "ONE with a 25-bit down-counter wrapping")
four = [(2, L.TICK_PA1, L.PA2_CONST, x[2]) for x in pre_d + after_d]
check(S.direction(four) == "down" and S.diffs(four)[0] == T, "direction down; diffs made positive")
# the filter and the dispatch rule (E146) as the scorer applies them
check(L.pds_slot(0, 0x10) == 3 and L.pds_slot(0, 0x110) == 0 and L.pds_slot(2, 0x10) == 0 and L.pds_slot(0, 0x200) == 1
      and L.pds_slot(0, 0x00300400) == 2 and L.pds_slot(0, 0x10 | 0x200) == 0 and L.pds_slot(0, 0x40000) == 0,
      "PDS #13 dispatch: groups, bit 8 general, pa0 not 0 general, a mix general")
check(L.is_plain_tick(2, 0x02000000) and L.is_plain_tick(2, 0) and L.is_plain_tick(2, 0x03000000)
      and L.is_plain_tick(2, 0xFF000000) and not L.is_plain_tick(2, 0x03000040)
      and not L.is_plain_tick(0, 0x02000000), "the window-1 filter masks the count byte pa1[31:24] (run 1)")
check(getattr(L, "is_kick", None) is not None and L.is_kick(0, 0x04000100) and not L.is_kick(2, 0x04000100)
      and not L.is_kick(0, 0x04000000) and not L.is_kick(0, 0x04000110), "run 1: the kick's words (pa0 0, low 24 = 0x100)")
# void rules
r = page_with(pre)
r["page2"][L.RING_BASE[0]] = 0
check(S.void_of(r, need_page2=True) is not None, "a ring that changed after the window closed is void")
r = page_with(pre)
r["page"][L.RING_BASE[0] + 8] = 7
try:
    S.ring(r["page"])
    check(False, "a rung flag of 7 is corrupt")
except ValueError:
    check(True, "a rung flag of 7 is corrupt")
r = page_with(pre)
r["class"] = "tickstop"
check(S.void_of(r) == "class tickstop", "a stop class is void")
r = page_with(pre)
r["page"][0] = 0
check(S.void_of(r) is not None, "a page without the kernel's header is void")
# review item 5: long holds whose queued burst fills the ring (the reviewer's synthetic case, allshape.py)
def review_page(n_ticks_hold, open_ticks, true_shape):
    pg = [0] * L.PAGE_DWORDS
    pg[0] = L.MAGIC
    t0 = 1_000_000
    Eh = t0 + 300
    hu = int(n_ticks_hold * T + 7000)
    Xh = Eh + hu
    pg[L.HOLD_ENTRY], pg[L.HOLD_EXIT] = Eh, Xh
    ent = [(2, L.TICK_PA1, L.PA2_CONST, t0)]
    if true_shape == "ALL":
        ent += [(2, L.TICK_PA1, L.PA2_CONST, Xh + 200 + 300 * i) for i in range(int(hu // T))]
    else:
        ent += [(2, L.TICK_PA1, L.PA2_CONST, Xh + 200)]
    g = (Xh - t0) // T + 1
    while g < open_ticks:
        ent.append((2, L.TICK_PA1, L.PA2_CONST, t0 + g * T))
        g += 1
    for j, e in enumerate(ent[:16]):
        o = L.RING_BASE[0] + 8 * j
        pg[o] = 1
        pg[o + 1:o + 5] = list(e)
    pg[L.DROP] = max(0, len(ent) - 16)
    return {"page": pg}


for nm, hold, open_t in (("h100k", 6.9, 34), ("h300k", 20.5, 52), ("h1500k", 100.5, 160)):
    s_one = S.hold_shape(review_page(hold, open_t, "ONE"))[0]
    s_all = S.hold_shape(review_page(hold, open_t, "ALL"))[0]
    check(s_one == "ONE", f"review 5, {nm}: a true ONE reads ONE ({s_one})")
    check(not s_all.startswith("PARTIAL") and (s_all == "ALL" or s_all.startswith("ALL-or-PARTIAL")),
          f"review 5, {nm}: a true ALL that fills the ring is not called PARTIAL ({s_all})")

# review item 6: the E5 control compares shape classes, drops cannot-tell, needs a told match and no told mismatch
cm = getattr(S, "control_match", None)
check(cm is not None, "review 6: control_match exists")
if cm:
    check(cm(["ONE", "ONE/offgrid"], ["ONE/offgrid", "ONE"])[0] is True, "review 6: ONE and ONE/offgrid are one class")
    check(cm(["ONE", "cannot tell (x)"], ["cannot tell (a)", "ONE", "cannot tell (b)"])[0] is True,
          "review 6: cannot-tell dropped from control and reference")
    check(cm(["LOST", "ONE"], ["ONE", "ONE"])[0] is False, "review 6: one told mismatch fails")
    check(cm(["cannot tell (x)", "cannot tell (y)"], ["ONE", "ONE"])[0] is False, "review 6: no told control fails")
    check(cm(["ONE"], ["cannot tell (a)"])[0] is False, "review 6: no told reference fails")
    check(all(cm(["ALL"], r)[0] is True for r in (["ALL", "ONE"], ["ONE", "ALL"])) and
          cm(["ALL"], ["ONE", "ONE", "ALL"])[0] is cm(["ALL"], ["ALL", "ONE", "ONE"])[0],
          "review 6: no dependence on order")
# ---- S2b: the classifier fixes, against S2 run 3's own pages (read-only fixtures) and synthetic holds ----------
import json  # noqa: E402

RUN3 = S2.parent / "s2" / "out"
check(S.T == 25000, f"S2b: the period is the measured 25000 (run 3's clock control), not E009's 25001 ({S.T})")
fixtures = 0
for st, names in (("e4h", ["h10k", "h10k-r2", "h100k", "h100k-r2", "h100k-r3", "h300k", "h300k-r2", "h300k-r3"]),
                  ("e4l", ["h1500k", "h1500k-r2"]), ("e5c", ["ctl100", "ctl100-r2"])):
    for nm in names:
        rec = S.record(RUN3 / st, nm)
        if rec is None:
            check(False, f"run 3 fixture {st}/{nm} readable")
            continue
        fixtures += 1
        got = S.hold_shape(rec)[0]
        want = "no tick held" if nm.startswith("h10k") else "PARTIAL(4)"
        check(got == want if want == "PARTIAL(4)" else got.startswith(want), f"run 3 {st}/{nm}: {got} (want {want})")
check(fixtures == 12, f"S2b: 12 run 3 pages used as fixtures ({fixtures})")
# the two new instruments reproduce run 3 (their fit): the pa2 signature and the window count
sigs, wins = [], []
for st, names in (("e4h", ["h10k", "h10k-r2", "h100k", "h100k-r2", "h100k-r3", "h300k", "h300k-r2", "h300k-r3"]),
                  ("e4l", ["h1500k", "h1500k-r2"]), ("e5c", ["ctl100", "ctl100-r2"])):
    for nm in names:
        rec = S.record(RUN3 / st, nm)
        if rec is None:
            continue
        shp, det = S.hold_shape(rec)
        H = det.get("floorH", 0)
        if H:
            sigs.append(S.pa2_signature(det, H))
        wins.append(S.window_count(rec, H)[2])
check(sigs == [True] * 10, f"S2b fit: the pa2 signature on run 3's 10 holds of 6, 18, 90 ticks ({sigs})")
check(wins == [True] * 12, f"S2b fit: the window count on run 3's 12 holds ({wins})")
d0 = S.hold_shape(S.record(RUN3 / "e4h", "h100k"))[1]
d0 = dict(d0, burst=[[0x01061A74, 103], [0x01061A70, 240], [0x01061A74, 380], [0x01060EA4, 531]])
check(S.pa2_signature(d0, 6) is False, "S2b: the pa2 signature can fail (a served tick's 0x01061a70 in the queue)")
# a tick 500 units after the exit is ambiguous; one 500 units BEFORE the exit was inside the hold and is not
b2 = 50_000_000
pre2 = [tick(b2 - T), tick(b2)]
E2 = b2 + 66
X_before = b2 + 3 * T - 500                 # the next grid tick 500 units after the exit
check(shape(pre2 + [tick(X_before + 100)] + [tick(b2 + k * T) for k in range(3, 7)], E2, X_before)
      .startswith("cannot tell"), "S2b: an exit 500 units before a grid tick: cannot tell")
X_after = b2 + 3 * T + 500                  # the last held tick 500 units before the exit: not ambiguous
s_after = shape(pre2 + [tick(X_after + 100), tick(X_after + 240)] + [tick(b2 + k * T) for k in range(4, 8)],
                E2, X_after)
check(s_after == "ALL", f"S2b: an exit 500 units after a grid tick is told (3 held, 2 after the exit: {s_after})")
X0 = b2 + 66 + 15015                        # n = 10000: no grid tick inside the hold
check(shape(pre2 + [tick(b2 + k * T) for k in range(1, 6)], E2, X0).startswith("no tick held"),
      "S2b: a hold with no grid tick inside reads 'no tick held' (LOST there is vacuous)")
# a 90-tick hold, exit at mid-phase, with the grid drifting 0.07 units a tick (run 3: griddev 5 to 6 at 90 ticks)
drift = lambda k: b2 + round(k * (T + 0.07))
X90 = b2 + 66 + round(1.5 * 1508279 + 15)    # n for H = 90 at mid-phase
burst90 = [tick(X90 + d) for d in (103, 240, 380, 530)]
after90 = [tick(drift(k)) for k in range(91, 95)]
s90 = shape(pre2 + burst90 + after90, E2, X90)
check(s90 == "PARTIAL(4)", f"S2b: a 90-tick hold with drift, four after the exit: PARTIAL(4) ({s90})")
print(f"{len(FAIL)} failed" if FAIL else "all scorer checks passed")
sys.exit(1 if FAIL else 0)
