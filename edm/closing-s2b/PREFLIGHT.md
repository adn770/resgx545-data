# S2b preflight (prepared 2026-11-10, not run)

Everything is under `~/src/scratch/resgx545/closing/s2b/`, a copy of S2's framework.  `../s2/` and
its `out/` were read, not changed.  The laptop was not contacted, nothing is committed, and no
landed tool was changed.

Checks that pass:
- `run/guard_s2.sh` is clean.
- `run/freeze_s2.sh verify` passes (31 files, 5 predictions files).
- `tests/test_scorer.py`: every check passes, including run 3's 12 hold pages.
- `tests/sim_s2.py`: ring_hold in sgx-sim, 18 checks.
- `tests/run_mock.py`: 17 tests, 0 failed.

## 1. The independent analysis, checked against S2 run 3's data

Checked on the kept pages (`../s2/out/e4h`, `e4l`, `e5c`):

- **Hold length.** It is 1.5 n + 15 units within 1 in 12 of 12 holds: 15015 at n = 10000 (x2),
  150015 to 150016 at 100000 (x3), 450015 at 300000 (x3), and 2250015 at 1500000 (x4, with e5c's
  two controls).
- **Hold start.** The hold starts 64 to 70 units after the tick whose pass runs it.  So the exit
  lands 1.5 n + 79 to 85 units after that tick: 79 to 86 units past an old-grid tick for every n
  that is a multiple of 50000.  That is the design fault.
- **After the exit.** Every hold of 6, 18 and 90 ticks is followed by four entries 102 to 552 units
  after its exit (10 of 10), and then the grid.  The first three read pa2 0x01061a74; the fourth
  reads an EVENT_TIMER sample whose (400000 - pa2[23:0]) / 16 = 182.9 to 189.8 units matches the
  first entry's time after the last held tick (181 to 188).
- **Window counts** (entries logged plus drops) are 26, 32, 38 and 74.  They equal open time x
  0.99746 - H + min(H, 4) within 0.5 in 12 of 12.
- **The fixed classifier** (`fixed_shape.py`, now in the scorer) gives "no tick held" for both n =
  10000 holds and PARTIAL(4) for the other ten.

Nothing in the data contradicts the analysis.  One addition: run 3's frozen n = 10000 verdict of
LOST is vacuous, because no tick fell inside those holds and every hypothesis predicts nothing.

## 2. Scorer fixes (tests first)

The new `test_scorer.py` rows failed on the copied S2 scorer (15 failures) before these changes:

1. **One-sided guard.** Only a grid tick within 1250 units AFTER the exit is ambiguous.  A tick just
   before the exit was inside the hold and cannot appear after it.
2. **Burst.** The burst is the entries after the exit and before the next grid tick minus 1250.
   One addition, so that the earlier review's long-drain case still reads ALL or ALL-or-PARTIAL and
   not PARTIAL: entries that continue the chain past that point (under 5000 units apart) stay in the
   burst, and one of them may then be the natural tick.  The count is then q or q - 1, and the
   classifier answers only if both give the same class; otherwise "cannot tell".
3. **Period.** The period is 25000 units, as run 3's clock control measured, not E009's 25001.  The
   25001 period put run 3's 90-tick exits 5 and 10 units on the wrong side.
4. **No tick held.** floorH = 0 reads "no tick held (nothing to tell)" and is not told.
5. **New instruments.**
   - `pa2_signature`: the first min(H, 3) burst entries read 0x01061a74.  With H >= 4, the fourth
     reads an EVENT_TIMER sample within 25 units of the first entry's time after the last held tick.
   - `window_count`: entries logged plus drops = open_ms x 0.99746 - H + min(H, 4) within 1.5.  It
     does not use the stamps.
   - Both reproduce run 3 (their fit: 10 of 10 and 12 of 12); a test shows the signature failing.
6. **Shape classes.** "no tick held" is not a told class in the E5 control comparison.

Fixtures: run 3's twelve pages (h10k reads "no tick held", the rest PARTIAL(4)); a synthetic exit
500 units before a grid tick (cannot tell); one 500 units after a grid tick (told, ALL); a hold with
no tick inside (no tick held); and a 90-tick mid-phase hold with the grid drifting 0.07 units a tick
(PARTIAL(4)).

## 3. Stages, jobs, predictions

n for H held ticks = ((H + 0.5) x 25000 - 82) / 1.5, rounded, so each exit lands mid-period (about
12500 units from both grid ticks):

| H | 1 | 2 | 3 | 4 | 6 | 90 |
|---|---|---|---|---|---|---|
| n | 24945 | 41612 | 58279 | 74945 | 108279 | 1508279 |

| stage | jobs | what | gate after |
|---|---|---|---|
| e4c | 3 | no hold, window 2, 20 ms (control: 16 ticks on the grid) | G: control 3/3 |
| e4m | 10 | H = 1, 2, 3, 4, 6, x2, window 2 | G: every hold valid, knob in band |
| e4l | 2 | H = 90 (about 90.5 ms), window 2 | G: the same |
| e5c | 5 | ctl90 x2, kick90 x3 (window 2, kick 3 ms in) | G: class = e4l's, kicks valid |
| e5t | 5 | tri-nohold x2, tri90 x3 (window 1, hold_recovery Y) | end |

That is 25 jobs.  Estimate: about 1.5 minutes of laptop time (holds up to 91 ms, a 160 ms window
for the long rows), 3 to 4 minutes wall time with staging, health and scoring.

Predictions, frozen in `predictions/*.tsv`, per hold job:

- **Knob band (control).** The hold lasts 1.5 n + 15 within 0.2 % + 50 units (fit: S2 run 3).
- **Held ticks (design control).** floorH = H.  A hold whose exit is not where it was designed is
  scored "cannot tell" on the prediction.
- **Burst size q (held out).** q = min(H, 4), labelled "fit: S2 run 3".  The fit is the queue that
  run 3 saw after 6, 18 and 90 ticks, so H = 1 to 4 are new conditions.  The alternatives, frozen as
  rows, are LOST (q = 0), ONE (q = 1) and ALL (q = H).  At H = 1, ONE, ALL and the cap coincide, so
  only LOST is tested there; H = 2 to 4 separate the cap from ONE, and H = 6 and 90 separate it
  from ALL.
- **pa2 signature (held out).** The first min(H, 3) entries read 0x01061a74.  For H >= 4, the
  fourth reads an EVENT_TIMER sample whose age equals the first entry's time after the last held
  tick (at mid-phase this predicts about 12600 units, far from run 3's 185).
- **Window count (held out).** A second instrument, as above.
- **e5c.** The controls must match e4l's shape class (gated).  The kicks have two frozen outcomes,
  QUEUED (S2 run 3: 3 of 3, in window 1) or LOST, and no favourite.  New in S2b: the kick's place in
  the drain, which window 2 makes visible, is reported.
- **e5t.** As frozen in S2, at the 90-tick n.

## 4. Risks

These are the same as S2 run 3, which ran e4c, e4h, e4l and e5c with no stop, no busy flag and no
bad log line.  Holds of 1 to 6 ticks are shorter than run 3's.  The 90.5-tick hold is 0.5 ms longer
than run 3's, still with no job in flight; the kernel's job timeout is 500 ms.

e5t has never run (a triangle in flight during a 90.5 ms hold): risk medium.  A stuck triangle is
read, released, reset, and ends the stage.

All gates, stop rules, run-id gate lines, hash checks, kernel-log checks and the
unprivileged-access guard are as in S2.  No sa write exists in S2b: the guard refuses any source
but `ring_hold.s` and any table with a `pa` task, and the runner refuses a `pa` op.

## 5. Not changed, or open

- e4c's control and the e5t design are as in S2.
- The mock models run 3's queue.  How a kick shares the queue with ticks is the mock's guess and is
  not used by any prediction.
- The landed `health.sh` still reads `dri/0` (present on the laptop).
- The laptop's `~/sgxfive-test-s1` and `/home/jtorra/sgxfive-test` must exist (staging checks
  both).
- Restaging is the coordinator's.
