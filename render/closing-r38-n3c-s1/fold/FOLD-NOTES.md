# r38-n3c-s1 fold notes (folder, 2026-11-19)

- One attempt, out/20261119-092626 (the lead, user present), rc 0, on the r37-kernel module
  77917296568EB311B89B0DA (fork 4f35fc20ffa9), no build and no boot. Stages own, tim and post
  each ended with every control passed; the driver scored them (out/score-*.txt) and the frozen
  scorer, rerun on the kept directories, prints the same lines (fold/reproduce-own.out,
  fold/reproduce-tim.out, fold/reproduce-post.out).
- own (R1 `n0`, E1151): the arm logged `own task armed: slots 0x1 ... emit image 0x0 (0: none)
  pds=v1` (emitsn has no emit; the `pds=v1` word is the module's default, unused) and was healthy
  (ticks 209, 238, 265). n0: done, X0 0x5a5a3303, M4 0x5a5a3302 and run id 1, state 2, echo 1,
  Δtick 40 in a 38.1 ms window (37.9 expected), gate ok (fill and triangle exact); after the job
  the tick still advanced (2121, 2148, 2175). `N3c-R1 RULE: N0-OK: the stop needs the emit`.
  Snap0 0x0acc 0x010110d3, snap9 0x0105f638: running. The SIGNATURE line (printed, not scored):
  USE0_SERV_EVENT bit 16 set at snap0 and snap9 here too, with no stop, as in E1148-E1150.
- tim (R2 `th`, E1152): the stock firmware (own_arm off after own's disarm), regtimeline 0.06
  0.005 0x0acc around t30's probe of the recorded `pds-timer-tim-host` program (`--temps 32 --pds
  36`, the recorded harness; the design said `--pds 4`, README "Deviations"). 18199 samples, 8532
  stored (a sample is stored when it differs), interval 3296 ns; 8531 stored samples running
  (0x0104xxxx down to 0x01038477 at 13126201 ns), then 0x00abcde0 at 13132015 ns and no stored
  sample after it, so constant to the timeline's end; snap9 (after the job, before any reset)
  0x0acc 0x00abcde0; the probe's scratch stores of `tim` at +0x008-+0x014 and +0x028-+0x034 all
  0x00abcde0 (+0x000 too, as in the recorded run's raw.txt). Job time 1013 us.
  `N3c-R2 RULE: V0-HOLDS: the host sees the PDS write`.
- So the host's read of 0x0acc is the register a client PDS `movs tim` writes: E1150's inference
  is measured for a client program. Still inferred: that a program started by an `emitpds` from
  an EDM task would do the same (no emitted program's `movs tim` has been seen to run).
- post: p1-tri and p2-fill on t30 after tim's last reset, both `diff: 0`; the kit's resets after
  tim restarted the counter (post p1-tri snap0 0x0acc 0x01053594, p2-fill snap9 0x0101ed1f:
  running; th's own snap0, before the job, read 0x010352eb).
- No vectors table: own is an owntask row and th a timeline, neither a table kind
  (README "Replay vectors"). sgx-sim already writes a PDS `movs tim` into EVENT_TIMER as the
  host's register; its test cites E1152 now, and the own-task emit refusal's test runs the
  same task without the emit, citing E1151.
- Records: E1151 (stage own), E1152 (stage tim); E1150 gets a dated correction; Q128 narrowed.
