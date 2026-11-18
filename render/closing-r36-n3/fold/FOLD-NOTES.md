# r36-n3 fold notes (builder, 2026-11-18)

- Attempt out/20261118-152130 (the lead, user present): stage own stopped at its first row e1-a,
  runner rc 1 ("no done within 200 ms"), class fail, stage rc 4; the session ended there and post
  did not run. The frozen scorer (fold/reproduce-own.out, scored by hand: the driver scores only
  stages that end 0 or 24) prints H-NONE held on 1 of 1 kept row, H-PA and H-SA "controls FAILED"
  (E1 failed), `N3 RULE: NONE` and `Q128 RULE: NARROW`.
- Entry 0 ran this command: slot 1 = 0x5a5a3301 and run id 1, cmd cleared to 0. Entry 1 left no
  write: slots 2-4 hold the host's fill 0xdeadc0de, state 0, echo 0. The arm was ok (the kernel
  logged the emit image at 0x30022000, ticks advancing at 996 Hz, health ok).
- Post hoc (fold/posthoc.py, fold/posthoc.out; not frozen): the EDM's tick (HostCtl dword 12)
  read 1943 at snap0 and 2467 both in fwtask_run.py's stop dump after the 200 ms window and in
  snap9 about 0.3 s later (kernel marks 4528.52 for the run, 4529.02 for snap9); USE0_SERV_EVENT
  also stayed at 0x000109a8. So the tick had stopped by the end of the window: the EDM stopped
  without a BIF fault (BIF_INT_STAT 0x00080000, BIF_FAULT 0, bif_faults 0 throughout). The kit's
  reset after the stop recovered it, and its health pair (t30 fill and triangle) drew exactly.
  The kit classified the job `fail`, not `hang`: neither fwtask_run.py's stop nor the runner reads
  the tick after an owntask stop (a kit need, reported to the lead).
- Harmless kit message: `lib_kit.sh: line 78: !v: unbound variable` after the arm, from
  run_stage.sh calling `tool_path` for the tool `owntask` (no TOOL_owntask_PATH); owntask rows
  never use $TT, nothing in the data changed. The lead fixes it in the kit.
- Records: E1148 only (E1149-E1155 unused).
