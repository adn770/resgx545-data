# Round 5 decisions (2026-11-12)

Merged from the four plans' 34 decisions: `closing5/{render4x,events,pixel,dpm}/exp-*-r5.md`
(render4x D1-D10, events D1-D9, pixel D1-D7, dpm D1-D8). Recommendation first in each.
Laptop checked 2026-11-12 00:34: 7.3.0-resgx545, module 99CD90DA (rgn4) loaded, up 4:28.

R5-1 Land the offline results before any freeze (events D1, pixel D1 and D4, dpm D1).
  (a) One fold package first: Q295's lockup marks (new record, corrections E836, E353), Q276's
      "clears 5:3" refuted (E838 correction, Q276 note), Q230's g4-rw fit dead offline (0 of
      225), Q210's step table and c4-b3 candidate, R-5 held on g-qf/s275, Q211's count rule
      (fit). Predictions then cite landed text.
  (b) Each with its session's fold.

R5-2 Offline firmware work for Q295 (events D2, D3).
  (a) Reading R-6 (three items, notes to data-private) before the freeze, then the pysgx oracle
      run S0 (2 h box).
  (b) R-6 only. (c) Neither; after the hardware if needed.

R5-3 Sessions, scope and order (render4x D1/D3/D4/D5, events D4-D6, pixel D2/D3/D5/D6/D7, dpm
  D2/D4/D5/D6; laptop render4x D10, dpm D7, events D9, render4x D8).
  (a) Four sessions on the rgn4 boot as it stands, no reboot, full scope as recommended:
      r5-events 14 jobs (first, health check; ends with timer_clock 0 verified), r5-pixel 106,
      r5-dpm 82 (16-register list with 0x0734 swapped in), r5-render4x 37 (faults; last).
      Not this round: E406's four-output setup, v-stock-4096 (dropped), closed-driver captures.
  (b) The same minus the exploratory rows (render4x x/d, dpm T/A2b, pixel P3 and dense table).
  (c) Reruns and seeds only (render4x t/o/m, events h1, pixel core, dpm A0/A1/A3).

R5-4 Stop rules (events D4, render4x D6).
  (a) Events: a b1p stop is the predicted outcome, the stage continues after each exactly
      recovered stop; render4x: per-stage fault limits (m 4, l 5, x 3, d 1, o 1, t 1), strict
      health after each.
  (b) Round 4's rule: the first stop ends the stage.

R5-5 Own firmware task oomring reading sa8/sa9 (dpm D3).
  (a) Build it, run it last in r5-dpm; if the rgn4 verifier refuses it, stop and ask before any
      kernel build.
  (b) Only if A2 says H-BLOCK or mixed. (c) Skip.

R5-6 What render4x freezes (render4x D2).
  (a) H-TPC's four variants against the seven size rules (stage m separates them in one row).
  (b) Q292's neutral ladder only.

R5-7 Retirements after the sessions (events D7, D8).
  (a) Q166 retired if H-W holds 3 of 3 (other bits to Q111); Q295 retired if h1 and h2 hold and
      R-6 names the state, else narrowed.
  (b) Keep both open.

R5-8 Follow-on (render4x D7, D9; dpm D8).
  (a) If H-TPC holds, plan the kernel tail-room change for the next boot (no kernel work this
      round); sim/vectors in the folds (dpm H-CNT for one-triangle scenes, guard decisions as
      vectors); 11.32 tables left as run.
  (b) Build the kernel change now (cachix, one-shot boot with OK). (c) Text only.
