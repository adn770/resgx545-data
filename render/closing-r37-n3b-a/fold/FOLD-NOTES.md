# r37-n3b-a fold notes (folder, 2026-11-19)

- Three attempt directories under out/, all kept:
  - out/20261118-212839: the driver's verify refused the session before staging (`FROZEN FILES
    CHANGED: run-a.log: not frozen`, a lead log then at the session's top); nothing reached the
    laptop, no stage ran.
  - out/20261118-212845: **void attempt**. Stage own exited 13 at the stage's first debugfs reset
    (`tee: .../sgx/reset: No such device`, kernel `SGX recovery failed: -19`): the firmware was not
    yet loaded after the boot. No arm, no row (cases.tsv and readings.tsv hold their headers only),
    nothing armed; no reading of it is used. Recorded in E1149's method, as earlier folds name a
    first attempt that ran nothing.
  - out/20261118-212949: the lead attempt (user present). The arm logged `emit image 0x30022000
    ... pds=v1`, health ok, ticks advancing at 995 Hz. c1-a: no done within 200 ms, runner rc 1,
    the kit classed it `hang` (`firmware hung: the tick stopped`), stage rc 4; post did not run.
- The frozen scorer, run on the kept directory (fold/reproduce-own.out): every control passed,
  `N3b-A RULE: A-PAST`; X0 0x5a5a3303, S1 and M4 the host's fill, state 0; Δtick 10 in a 237.1 ms
  window.
- Read from the kept files (not frozen): HostCtl dword 12 read 0x7a2 at snap0 and 0x9b9 in both
  the stop dump and snap9 (alive_at_stop: 2489 three times, serv_event 68030 three times);
  `CR_CLKGATESTATUS` 0x20 -> 0x000ccfa0; 0x0acc running in every read (0x010295f9 at snap0,
  0x01038295 in the stop dump, 0x01017336 in snap9); BIF_FAULT 0 throughout; the reset after the
  stop recovered (t30 fill `diff: 0 of 2048`, triangle `diff: 0 of 4096`).
- The SIGNATURE line (USE0_SERV_EVENT bit 16, count minus tick) is printed, not scored: bit 16 was
  already set at snap0 here (0x000107a7), in r37-n3b-b and in E1148 (0x0001079c at snap0), and the
  count minus tick is 5 in every read, so neither marks the stop.
- Records: E1149 (this session), E1150 (r37-n3b-b).
