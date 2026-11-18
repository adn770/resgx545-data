# r37-n3b-b fold notes (folder, 2026-11-19)

- One attempt, out/20261118-213042 (the lead, user present), on the same boot and module as
  r37-n3b-a. The arm logged `emit image 0x30022000 ... pds=crumb` and `own_arm` read
  `... pds=crumb blob=644`, health ok, ticks advancing at 963 Hz. c1-a: no done within 200 ms,
  runner rc 1, the kit classed it `hang` (`firmware hung: the tick stopped`), stage rc 4; post did
  not run.
- The frozen scorer, run on the kept directory (fold/reproduce-own.out): every control passed,
  `N3b-B RULE: B-1: (1) the program never ran`; X0 0x5a5a3303, S1 and M4 the host's fill, state 0;
  T (0x0acc) 0x0101fc6d in snap9 and 0x010585dc in the stop dump, bit 24 set and counting;
  Δtick 10 in a 237.7 ms window.
- The rule rests on an inference the session does not measure: that a `movs tim` of a PDS program
  started by an `emitpds` from an EDM task writes the same CR_EVENT_TIMER (0x0acc) the host reads.
  `movs tim` was measured only from client PDS programs (the fill's secondary program of the
  probes pds-timer-tim-*, read back through the PDS: doc/isa/content/pds/probe/inputs.md), and the
  host's reads of 0x0acc are of the firmware's own running timer (E1131, E1133). If the
  inference is false, B-1 cannot be told from B-1p, B-2a or B-2b.
- Read from the kept files (not frozen): HostCtl dword 12 read 0x615 at snap0 and 0x82b in the stop
  dump and snap9 (alive_at_stop: 2091 three times, serv_event 67632 three times);
  `CR_CLKGATESTATUS` 0x20 -> 0x000ccfa0; BIF_FAULT 0 throughout; the reset after the stop
  recovered (t30 fill `diff: 0 of 2048`, triangle `diff: 0 of 4096`).
- The SIGNATURE line is printed, not scored: USE0_SERV_EVENT bit 16 was already set at snap0
  (0x0001061a), as in r37-n3b-a and E1148, and the count minus tick is 5 in every read.
- Records: E1150 (this session); E1149 is r37-n3b-a.
