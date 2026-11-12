# Round 6 decisions (2026-11-12)

Merged from the ranking (`rank/rank-round6.md`, 9 decisions) and three plans
(`{render4x,pixel,dpm}/exp-*-r6.md`, 7 + 8 + 8). Recommendation (a) first. Kernel work approved by
the user (2026-11-12) where it helps close questions. The laptop is on rgn4 (99CD90DA) today.

R6-1 Offline first: one fold package before any freeze.
  (a) Records/notes for what the kept data decides, each labelled post hoc/SEMI/held as it is:
      render4x H-TPM (the 4x tail pointers in Z-order; 1023 of 1023 lost offsets on E869's dump,
      26 of 26 recorded outcomes); pixel Q276 (o4..o7 reach no pixel; E081 correction) and Q230
      (no table-plus-Newton model fits; H-FRAC frozen, then 13 of 13 held out); dpm (A2b's S2 is
      0x97 by bracket; the burst/slow-page phase reading; the page-by-page Q211 replay, 54 of
      56) via its offline stage F1-F9; ranking (Q289's half-tile rule, post hoc; Q139's whole-tile
      errors and the offline macrotile test) and housekeeping (merges Q274->Q183, Q244->Q071,
      sideband clause->Q046, Q136's pa0->Q098; narrow Q178, Q271; reword Q291, Q293).
  (b) Each with its session's fold.

R6-2 Sessions on the rgn4 boot as it stands (before any reboot), files under ~/scratch/<prefix>/.
  (a) Four sessions in this order: r6-pixel (p6-rd 58, g6-rwa+g6-rw 114, L3 8, S 22 last with
      kpoke rd:9 and a restore check; ~18 min), r6-dpm (~97 jobs incl. oomring2, ~35 min),
      r6-misc from the ranking (Q289 held-out row 23, Q287+Q291 odd heights with a userspace tool
      rebuilt on cachix from main, Q086's 20 skipped 4x cases + 1; ~70 jobs, ~45 min, fault budget
      3), r6-render4x stage A (16 jobs, 6 predicted faults; last before the reboot).
  (b) The same without the optional sets (pixel L3 and S; ranking Q086).

R6-3 Kernel series (one cachix build, one one-shot boot after the rgn4 sessions are folded).
  (a) Three test-first fork commits: the 4x tail room (`sgx_render_tail_room()`, 4 x the bytes
      for a 4x context, debugfs `render_tail_room` knob, four KUnit tests incl. the 26 cells);
      K1, a debugfs peek of 0x0694 (CR_DPM_TASK_STATE); K2, a bus-interface flush before a held
      reset.
  (b) The tail room only. (c) No kernel work this round.

R6-4 Sessions on the new kernel.
  (a) r6-render4x stage B (20 jobs, 3 predicted faults: own-maximum cells, knob one page under
      and over, 4096 x 960) and r6-held (Q003 replay through the directory list, Q294 + Q111's
      0x0694 rows; ~28 jobs, ~40 min, medium risk: E848 saw -110 boot timeouts after held resets).
  (b) Stage B only.

R6-5 Stop rules and budgets as each plan freezes them (fault limits per stage, strict health,
  exit on any unexplained stop; the lead decides after a stop).
  (a) As planned. (b) First fault ends a stage.

R6-6 Question outcomes after the sessions.
  (a) Retire Q276's o4-predicate clause if o4 does not read back; Q293 reworded to its bounded
      items with its four rows; Q289 retired if the held-out row picks OR or ADD; Q287 by the odd
      heights; the merges of R6-1.
  (b) Narrow only, no retirements this round.

R6-7 Sim and vectors in the folds (tests first).
  (a) sgx-pipe: xfer half-tile stores (Q289, ~1534 scenes) after the held-out row; 1/w H-FRAC
      only after g6-rw holds; the dpm page replay as a rule for one-triangle scenes; the 4x tail
      layout after stage B.
  (b) Vectors only. (c) Later.
