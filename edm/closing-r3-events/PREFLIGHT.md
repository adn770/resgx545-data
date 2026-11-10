# R3-events preflight (prepared 2026-11-10, not run)

Everything is under `~/src/scratch/resgx545/closing2/r3-events/`. The landed tree, the data, the
linux fork and the past session directories were read, not changed. The laptop was not
contacted. Nothing is committed. Frozen: `FROZEN.sha256` (every generator, scorer, runner,
script, table, blob, source, prediction and what they import from the landed tree),
`PREDICTIONS.sha256` (3 files), `LAPTOP.sha256` (the files as laid out on the laptop).

Checks that pass (see the end of this file for the dated run): `run/guard_r3.sh`;
`run/freeze_r3.sh verify`; `tests/sim_r3.py`; `tests/test_scorer.py`; `tests/test_guard.py`;
`tests/run_mock.py`.

## 1. Offline readings behind the rows

- **The tick is the experiment's instrument.** HostCtl dword 12 (the closed task's tick
  count) advances over three reads 20 ms apart and the rate is 900 to 1100 Hz: kept. Not
  advancing: a stop (E537 read 0x9db in it in both dumps).
- **The stop signature** (E537, `p1130-b2-variants/tailpair-stop1-regs.txt`): reg 0x0008
  0x000ccfa0 (busy, idle 0x20), 0x0b14 (USE0_SERV_EVENT) 0x9e0 with bit 16 EMPTY clear and the
  count frozen, 0x0acc (EVENT_TIMER) 0x01038ec3 counting, 0x012c (EVENT_STATUS) 0x20000000.
  The runner reads these (and 0x0118, 0x0c04, 0x0c08, 0x0b20) TWICE, 30 ms apart, the moment a
  tick stop is seen and BEFORE the landed dumps and the reset; the scorer classes busy /
  idle-pending / idle-empty and says which elements match E537 (all four: "matches E537").
- **Persistence.** E536's sa100, sa127, i0 and i1 survived a debugfs reset and a reload, so sa63
  may too: after every stop's reset and re-arm stage a reads sa63 and puts it back (command 7,
  an sa63 write allowed in A1-A6) before the next row; A1 restores it itself.
- **A4's "pclink 6, p1 ours"** is E536's reading (sa64 markers with bit 1 clear, next entry
  pclink 6, p1 as left); `dword 12 delta = passes - 1` needs a pass count: alias.s and ring_skip.s
  count every pass in dword 20, the runner brackets the pass count and HostCtl dword 12 (page,
  register, page) before and after, and the scorer works with the interval that gives
  (`d12 - passes` is exactly -N, outside -N, or cannot tell).
- **K7 and the kernel's lock** (fork, branch resgx545, `sgxfive.c`): every debugfs command takes
  `sgx->lock` and waits for its answer under it (`sgxfive_miscinfo_show`, `sgxfive_xfer_*_show`).
  Two `miscinfo` reads therefore cannot both be inside a 90 ms hold: the second would be issued
  after the first one's answer, after the hold. The landed `xfer_sync` file submits a TRANSFER
  (kick 1), sleeps 50 ms under the lock, submits PROCESS_QUEUES (kick 2) and waits for the SW
  event: two real kicks 50 ms apart, both inside a hold that began a few ms before. K7 uses it.

## 2. What I changed from the proposal, and why

1. **K7 uses `xfer_sync`, not two miscinfo reads** (above). Rows: `k7-ctl` (no kick; fit: S2b's
   ctl90), `k7-one` (one miscinfo kick 3 ms in; S2b's kick90, a replicate: 3 of 3 queued), then
   `k7`, `k7-r2`, `k7-r3` (xfer_sync, window 2). Each job resets and arms first (K starts at 2
   after the arm: the K identity is then read against ccbctl[0], the free instrument). The one
   new thing the laptop is asked to do is the landed test file `xfer_sync` under our armed
   ring_hold (its TRANSFER and PROCESS_QUEUES go to the closed task, which runs after our hold
   as it does after any pass); it has run under the stock firmware (E018). Risk medium, last
   in the session, reset after.
2. **A6 writes no sa register at all.** The proposal's "E536's list" has sa100, sa127, sa20, sa24
   and sa64; the laptop limit allows sa63/sa64/sa65 only, and sa64 would confound H-P11 with A4.
   A6 writes r20, r21, i0, i1 (E536's r and i values), leaves p2/p3 as at entry and calls the
   closed task with p0 = p1 = 1 from the dispatch (as E537's cmd 4 did). H-P11 (p0 = p1 = 1 with
   r and i written) is still what it tests; it is not E536's list minus sa63/sa65 exactly.
3. **A0 is host-driven, the other rows are writer plus reader.** A0 sets cmd 9 itself; A1-A6
   write, arm the reader (cmd 9, runs at the next event) and call the closed task; A1 also reads
   1200 ms later, then restores sa63.
4. **A stop leaves the remaining reps of the row to run** (a repeat of the stop is the second
   stop, which ends the stage: exit 8, reset and gate done, the lead decides about the next
   stage). Stage b is the same; B2 runs only if every B1 rep kept the tick.
5. **ring_skip skips only plain ticks and only in window 2** (pa0 = 2, no bit of pa1[23:0],
   SKIP > 0). A kick pass is never skipped: B3 cannot be run with this blob. A skipped pass is
   logged with flag 3, so the ring shows exactly which pass it was.
6. **The writer's flag is a word that stays** (`WR_DONE`), because cmd 9 lasts one tick and a
   2 ms host poll misses it.
7. **Rows' counts**: A0 x2, A1-A5 x3, A6 x2 (19 jobs); B0 x3, B1 x3, B2 x2 (8); K7 5 jobs.

## 3. Rows, labels and controls

Fit rows are only what past data fitted (A0: E536/E537's controls; k7-ctl and k7-one: S2b's
ctl90 and kick90); everything else is held out or a replicate; B0 and the k7 knob band are
controls. Void: no record, a class that is not a result, no page, a ring that changed after the
close, a writer whose flag was not set, a read-back that is not what the writer wrote (A3: sa65
not restored), a SKIPPED count that is not the design's, a hold that was not busy at the kick.
Cannot tell: reader not run but tick kept, A0 differs (pclink claims), the signature dump
unreadable, a ring full before the burst ended, a hold outside its knob band, a kick count
(one entry, both reads answered) that merge and queue capacity do not separate.

## 4. Risks and limits

No kernel change, no reboot, no build on the laptop; the only writes are debugfs own_code,
own_arm, own_res (the page), load, boot and reset (an allow-list; no knob is written), /dev/kmsg
(`os.open(path, os.O_WRONLY | os.O_APPEND)`) and the results page. No register write, no kreg,
kpoke or clock register, no trc_hazard, no firmware-task `str` (the guard refuses any), ldr of
CR_TIMER only. The task's sa writes: alias.s command 1 and 7 sa63, 2 and 3 sa65, 4 and 5 sa64,
nothing in 6 and 9; ring_skip.s and ring_hold.blob none. A freeze or a watchdog stops all laptop
work (exit 6, exit 3).

- stage a: the E537 stop is the expected outcome of one hypothesis; A3 writes a marker to sa65
  and restores it inside one pass (the closed task does not run in between).
- stage b: B1 is H-STOP's test; the first stop is budgeted.
- stage k7: see 2.1.

## 5. Time

About 4 minutes of laptop work: a under 1 minute of jobs (19 jobs of about 0.25 s, A1's 1.2 s
wait three times; a stop adds two resets, a re-arm and the baseline, about 15 s), b about 10 s
of jobs, k7 about 10 s of jobs (5 jobs, a reset and arm each, 90 ms holds); plus each stage's
preflight, final reset and gate (about 10 s) and the health script (about 20 s). About 10
minutes wall with staging, copies and scoring. The mock session (real sleeps, no hardware)
takes 18 s.

## 6. Not closed by R3

Why the closed task hangs on a corrupt word; what the exit routine at 0x1974 does if B1 stops
idle-pending; A7 (sa65 | 1 << 23) and A8 (E537's cmd 4 markers) and B3 (a skip on a kick pass),
which the user has not approved; H-KW against H-HWC (needs a kernel change).
