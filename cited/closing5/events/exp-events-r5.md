# Round 5 plan, area events (Q295, Q166's B1P replicates)

Planned 2026-11-12. Nothing here touched the laptop, cachix or a repo; no firmware image, closed
binary or `ukernel.dis` was opened; the clean-room guard was not run. Scripts and outputs of the
offline part are in `closing5/events/offline/` (they read published sessions of `resgx545-data`
only, so they are publishable as they are).

## 0. Result in short

The kept data of round 4 already answers most of Q295. The tick stop of E836's b1p is the
microkernel's own lockup detection (the routine of E353, "not yet seen on the hardware"):

- b1p's stop dump holds HostCtl dword 3 (`ui32uKernelDetectedLockups`) = 1 and dword 8
  (`ui32InterruptFlags`) = 1 (HWR), `sw_events 1` with no fill completion, and TA3DCtl dword 58
  = 0xaac267c2 (dword 57 = 0). Nobody read these words in round 4.
- The stop came after exactly 20 slot 0 passes after the fill's kick, not "about 20 ms": 10 ticks
  in the ring plus page dword 16 (the task's "ring full" counter) = 10. 20 = 2 x
  `ui32HWRecoverySampleRate` (10, HostCtl dword 5).
- The 20 other kept stops with the busy signature (missing phase end, phantom kick, E823's b1
  among them) all read dword 3 = 0, dword 8 = 0, dword 58 = 0, `sw_events 0`.

So seed 1 becomes: confirm held out (the B1P replicates of seed 2 do it, with a scorer that reads
the dump), a dose test (ticks, not time), and two things the data cannot say: which state the
skipped handler leaves that keeps the detector armed, and why the EDM is busy after it flags the
lockup. One laptop session, 14 jobs, about 15 minutes, no reboot if the laptop is as left.

## 1. What was read

- Handovers 2026-11-12 and 2026-11-11; Q295, Q166; E823, E836, E837, E353, E084; hw_spec 12.2,
  `doc/specs/boot_sequence.md` section 2 and the MISR text, `doc/specs/edm_dataflow.md` (lines
  301-314, 909-931: the routine 0x1c4-0x599).
- Our reading notes `cited/closing3/events/readings/readings-r3.md` (R-1 to R-4) and
  `cited/closing4/p7/reading-r5.md` (R-5) in data-private. Neither covers the tick routine's
  3D check nor the body of slot 3's bit 4 handler (R-2 lists only the no-group-bit path).
- Kept timelines: `resgx545-data/edm/closing-r4-events/out/a1/e3p/` (b0, b1p, stop dumps),
  `edm/closing-r3k-events/out/e3b/` (E823), and every dump of the published sessions (scan below).
- r4-events session (`closing4/r4-events/`: README, `asm/ring_skip3p.s`, `run/ops_e3p.py`,
  `predictions/e3p.tsv`, `score/`), `crates/sgx-sim/src/edm_pass.rs`, `crates/pysgx/tests/`.
- Kernel fork branch resgx545 (a2788bd8, read only): debugfs knobs; the boot writes HostCtl dword
  5 = 10 (`HC_HWR_SAMPLE_RATE`, a constant) and dword 6 from the `timer_clock` knob; no code reads
  dword 8, so nothing on the host acknowledges an HWR request.

## 2. Offline results (run now, in `offline/`)

### O1. The stop came after exactly 20 slot 0 passes [HW, post hoc]

`offline/ticks_after.py` (output `ticks_after.out`) reads the kept page of a job: the slot 0 ring,
the "ring full" counters (dwords 16 to 19, `asm/ring_skip3p.s` lines 258-263: counted only with
the window open) and the pass counter (dword 20).

| job | ticks before the kick | ticks after it in the ring | dword 16 | passes after the kick |
|---|---|---|---|---|
| r4 b1p (`b1p.json` and `stop-b1p-own_res.json`, window still open at the stop) | 5 | 10 | 10 | **20** |
| r4 b0 (control, window closed by the host) | 5 | 10 | 292 | 302 (alive) |
| E823 b1 (`idf, wdf, nop.end`) | 5 | 0 | 0 | **0** |
| E823 b0 | 5 | 10 | 279 | 289 (alive) |

Slots 1 to 3 counted 0 and logged nothing but the one slot 3 entry (37 us after the kick entry),
so no event other than 20 slot 0 passes entered our task between the skipped pass and the stop.
The gaps are 7623 units (kick to first tick), 24990, 25000 x7, 25005: the last pass entered about
19.3 ms after the kick. E836's "about 20 passes [infer]" becomes a count read from the page.

Rests on: E836's kept files. Refuted by: a B1P replicate with another count. Needs a held-out
check: yes (h1 below); b1p is the fit.

### O2. b1p's stop dump carries the lockup marks [HW, post hoc]

`stop-b1p-status.txt` (taken at the stop's signature, before the host's clears):
`hostctl[0]` dword 3 = 1, dword 5 = 10, `hostctl[8]` dword 8 = 1, dword 9 = 0, dword 12 = 1051,
dword 14 = 0; `loaded 1 live 1 sw_events 1`; `ta3dctl[56]` = 0, 0, 0xaac267c2 (dwords 56, 57, 58).
Landed text names them: dword 3 `ui32uKernelDetectedLockups`, dword 8 `ui32InterruptFlags` (the
EDM sets HWR = 1), and E353 [RE]: one routine (0x1c4-0x599) increments the lockup count, sets
`InterruptFlags` bit 0 and writes `SW_EVENT`; the dataflow shows in the same routine a counter at
TA3DCtl +0xe4 (dword 57) compared with `hw_recovery_sample_rate`, and a saved word at +0xe8 (dword
58) whose equality leads to the call that counts the lockup (`edm_dataflow.md` 926-931).

Reading [infer]: after a 3D kick the closed tick routine counts ticks; every 10th it samples a
progress word; first sample (tick 10) differs from the saved 0 and is stored (0xaac267c2); the
second (tick 20) is equal, so it counts a lockup, requests recovery from the host (dword 8,
`SW_EVENT`: the kernel counted the interrupt, `sw_events 1`, and does nothing with it) and the
pass never ends (busy signature). The closed end-of-render handler, skipped, is what would have
ended the check.

### O3. No other stop has the marks [HW, post hoc, a control that could have failed]

`offline/stop_dumps.py` (`stop_dumps.out`) over the published sessions (19 unit directories of
`resgx545-data`, `firmware/` not entered): 6797 dumps, 95 of a firmware past its boot (dword 12
above 20), 21 of them with `CR_CLKGATESTATUS` 0x000ccfa0. Of those 21, b1p alone reads dword 3 = 1
and dword 8 = 1; the other 20 (the stop dumps of closing-r3-events b, r3k e3b, f, t, r3x d and
e, r4-q152 fr, the in-window reads of r3k k0h and r3x h, the fixtures of E537, E813 and E817; some
are copies of one stop) read 0, 0, dword 58 = 0, `sw_events 0`; the list is in `stop_dumps.out`.
`offline/hwr_scan.py` (`hwr_scan.data.out`): over all 6797 dumps the only other non-zero dwords
56 to 58 are in r1's d1 (E771: 4096x4096 jobs with 1500 vertices): 0x720b23e4, 0, 0x3c8c9a29 with
dword 3 = 0: [infer] jobs longer than 10 ticks, samples taken, progress seen, no lockup. The
`.out` files print absolute paths; the fold regenerates them with paths relative to the data repo
before publishing.

E823's b1 was read after the hypothesis was formed and came out as it says (0 passes, no marks),
but no prediction file was frozen first: an offline check, not a held-out row.

### O4. What offline cannot decide

1. Replication (one job).
2. Ticks or time: at the stock clock 20 ticks and 20 ms are the same thing.
3. Which state keeps the check armed (what the skipped handler would have cleared), and what the
   sampled word is. The dataflow lists the words, not the conditions; notes R-1 to R-5 do not
   cover this code.
4. Why the EDM is busy after flagging (the DDK's host answers HWR with a full reset, so the
   firmware may simply wait; not read, not measured).
5. Whether an acknowledgement of bit 18 before the stop changes anything (Q295's candidate 1).

The sim cannot test any of this today: `edm_pass.rs` is a table of measured rows and refuses the
slot 3 pass (its header says E836 is not taken). pysgx boots the firmware image and serves ticks
(`test_sgx_ccb.py`), which is the offline route for items 3 and 4 (step S0 below).

## 3. Hypotheses and frozen predictions

| name | says | separates on |
|---|---|---|
| H-HWR | the stop is the firmware's 3D lockup detection | dump marks: dword 3 +1, dword 8 = 1, `sw_events` +1, dword 58 not 0, dword 57 = 0 |
| H-NOMARK | another cause; b1p's marks were incidental | a B1P stop with dword 3 = 0, dword 8 = 0 |
| H-TICKS | the stop comes on the 20th tick after the fill's kick (2 x dword 5) | 20 ticks at every `timer_clock` |
| H-TIME | the stop comes about 19 ms after the kick, whatever the tick | 10 ticks at 800000, 5 at 1600000 |
| H-STATE | the check is armed by firmware state, not by status bit 18 | early host clear of bit 18: still stops at 20, marks set |
| H-ACK18 | the unacknowledged bit 18 is what a later pass waits for | early host clear of bit 18: tick alive, dword 3 = 0 |
| H-LEVEL, H-W | as frozen in r4 (bit 18 a level; CLEAR clears the bits written) | as `predictions/e3p.tsv` |

Predicted [infer]: H-HWR, H-TICKS, H-STATE, H-LEVEL, H-W. Labels: r4's b1p is the **fit** for the
marks and the count (the hypothesis came from it) and stays the fit for the clears with E823;
every B1P row of round 5 is **held out**; the clears on a running EDM (h3) are held out.

Quantity definitions the build must freeze: `ticks_after_kick` = slot 0 rungs with `pa0` 2 after
the fill's kick entry + dword 16, read from the stop's `own_res` dump; cannot tell if the fill's
kick entry is not in the ring or a second kick entry precedes the stop (h3's P3 excepted, see
there). `lockups` = dword 3 at the stop minus dword 3 at the arm dump. `tick_gap` = median gap of
the ring's ticks in `CR_TIMER` units.

## 4. Offline steps before any hardware

- **F0, fold what section 2 found** (half a session, no hardware). A new record (tiers HW, infer;
  data `edm-closing-r4-events:out/a1/e3p/`, cites `cited/closing5/events/offline/` published with
  `scratch_cites.py --publish`): O1, O2, O3. Appended corrections: E836 ("about 20 ms", "the
  stop's time is an estimate" -> 20 passes from dword 16; "something of the skipped handler is
  needed later" -> the lockup check), E353 and `boot_sequence.md` ("not yet seen on the hardware"
  -> seen once, E836's job), hw_spec 12.2 ("within about 20 ms"; the stop signature has two
  kinds: with and without the marks). Q295 narrowed to items 1 to 5 of O4. E837 unchanged.
- **R-6, a reading of our disassembly** by the lead with the method of E154/E155 and R-1 to R-5
  (I did not open the listing). Three items only: (i) the 3D branch of 0x1c4-0x599: what arms
  it, what resets dword 57, which word is sampled into dword 58; (ii) what the code does after
  the `SW_EVENT` write of the lockup path (does it reach the exit's `phas`, loop, or poll);
  (iii) which of those states the bit 4 handler of slot 3 (0xe21 on) writes. Frozen before the
  reading [infer]: (i) armed by a mark the 3D kick sets and the end-of-render handler clears,
  dword 57 zeroed at the kick and at each sample; (ii) no exit: a wait; (iii) the handler clears
  the mark of (i). Notes to data-private (`cited/closing5/events/reading-r6.md`). If (i) names a
  state our verifier lets a task write, a later round can test "skip and clear": not planned here.
- **S0, pysgx as the firmware's oracle** (time box 2 hours, after R-6, scratch test in
  `closing5/events/sim/`, `CARGO_TARGET_DIR` inside it). Control that can fail: 40 idle ticks
  leave dword 3 = 0 and dword 57 = 0. Then the state of R-6 (i) set by hand, labelled as an
  assumption, a constant register bus, ticks served: frozen prediction dword 58 written on tick
  10, dword 3 = 1 and dword 8 = 1 on tick 20, no `phas` executed after. Stop: the sim refuses a
  form or a register in the routine (record where; do not extend the sim in this step).
- **Sim in sync** after the hardware: `edm_pass.rs` gains the measured row (a fill whose slot 3
  end-of-render pass is ended by `OwnEnd { phas: true }`: kept for 19 ticks, stalled on the 20th
  closed tick pass after the kick, dword 3 +1, dword 8 = 1) and keeps refusing other clocks unless
  h2 measured them; a closing-pass vector from the replicates.

## 5. Hardware: one session, `r5-events` (reuse r4-events, three stages)

Reuse byte for byte: the blob `ring_skip3p` (sha256 3b35d3af...; no new blob, no `str` at all),
`run/r3common.py`, `ops_e3p.py`'s job, the scorer's readers, the tool `~/sgxfive-test-s1b`, the
module 99CD90DA (laptop as left: **no reboot**; if it was rebooted to stock Arch, the session
needs the one-shot test boot the other areas ask for, with the user's OK). New: `r5layout.py`
(stages, rows), the runner's `timer_clock` handling and a status dump in every job, an early-clear
variant of the job, `sc_h.py` (marks, count, gap), predictions. Only `CR_EVENT_HOST_CLEAR` (0x0134)
bits 15 and 18 are written, by the host (`kregnow`); `timer_clock` is HostCtl memory written by
the kernel at the firmware boot (E084), not a register. No clock-gate write, no `trc_hazard`.

Changed rule: in r4 a B1P stop ended the stage. Here a B1P stop is the **prediction**; each is
signed (signature twice, the status dump, `own_res`), then reset, gate, health. The stage ends on:
a recovery not exact (exit 5 or 6: ask the user for a reboot), a control (B0) that stops, or a
stop without both the marks and the count (one unexplained stop ends the session).

| stage | `timer_clock` | jobs | what | predicted stops |
|---|---|---|---|---|
| h1 | 0 (400000) | B0, B1P x3 | r4's e3p again: marks, count 20, bit 18 level, clears after the stop | 3 |
| h2 | 800000, 1600000 | per clock: B0, B1P x2 (6 jobs) | dose: ticks or time; no host write before the stop | 4 |
| h3 | 1600000 | B0, B1E x3 | clears of bit 15 then 18 started at the slot 3 entry (EDM running), one `miscinfo` after them, watch 150 ms | 3 |

14 jobs, 10 predicted stops. Order h1, h2, h3, each gated on the previous `stage.json`. If only
one stage can run: h1 (it settles seed 2 and the held-out half of Q295).

**h1 rows (per B1P, held out).** Controls: `skipped` 1, slot 3 logged with flag 3, `tick_gap`
25000 +-10, `hold_recovery` back to N, dword 3 = 0 and dword 8 = 0 at the arm dump. H-HWR:
`lockups` 1, dword 8 = 1, dword 9 = 0, `sw_events` 1, dword 57 = 0, dword 58 not 0, dword 14 = 0,
CCB 3 and 3 (H-NOMARK: 0, 0, 0). H-TICKS: `ticks_after_kick` 20. H-LEVEL, H-W and H-ALL, H-NONE
as r4's file, set heldout. B0: fill ok, tick alive, bit 18 never, and (new, can fail) dword 3 = 0,
dword 8 = 0 in a status dump taken after the watch.

**h2 rows.** Control per clock (B0, can fail): HostCtl dword 6 in the arm dump = the knob,
`tick_gap` 50000 +-20 (800000) or 100000 +-40 (1600000; a value E084 did not measure, so B0 at
1600000 is its measurement and a failed B0 voids the clock), fill ok, tick alive, no marks. Every
B1P job carries its own `tick_gap` row as a control: a job whose gap is not its clock's is void.
H-TICKS: `ticks_after_kick` 20 at both clocks; H-TIME: 10 +-1 at 800000 and 5 +-1 at 1600000.
Marks as h1. The watch is 100 ms at 800000 and 150 ms at 1600000 (the stop is predicted at 39 and
78 ms). Stage end: knob 0, reset, `tick_gap` 25000 in a 20 ms window, health; the session's last
line prints the knob (other sessions' preflights do not read `timer_clock`).

**h3 rows.** B1E = B1P with the clears moved: at the slot 3 entry seen, `kregnow` bit 15, reads
at 1 and 3 ms, bit 18, reads at 1 and 3 ms (about 40 ms in all at the debugfs's pace, against a
stop predicted at 78 ms), then one `miscinfo`. Controls that can fail: the `miscinfo` answered
and its kick entry in the ring with ticks after it (the EDM was running at the clears; not
answered: the job's clear rows are "stopped EDM" rows and go to h1's family). H-W on a running
EDM: bit 18 set after bit 15, clear after bit 18. H-STATE: stop, `ticks_after_kick` 20 counted
from the fill's kick, marks set, signature status 0x20000000; H-ACK18: tick alive at 150 ms,
`lockups` 0. One assumption rides on it [infer, from the dataflow: dword 57 is zeroed only in the
3D kick routines and at a sample]: the `miscinfo` kick does not restart the count; a stop with
marks at another count is scored "mixed" for H-TICKS and does not touch H-STATE.

**Verdict rules.** H-HWR consistent only with 3 of 3 in h1; any B1P stop without marks refutes it
and ends the session. A count other than 20 in any h1 or h2 job refutes H-TICKS as stated (the
record then gives the counts). Cannot tell: the fill's kick entry not in the ring, fewer than 3
ticks before the stop, no slot 3 entry, a watch of fewer than 5 reads.

**Dry runs that would have caught round 4's slips, per stage.**

- Wrong file name in a scorer (t's slip): `sc_h.py` is run, before the freeze, on r4's kept
  `out/a1/e3p` as produced by the real runner (must print marks held, count 20), on E823's
  `out/e3b` (must print H-HWR FAILED on b1: shows the rows can fail) and on b0 (control pass). A
  missing dump is "cannot tell" with the path printed, never a pass; `test_scorer.py` asserts the
  three outcomes.
- A control that ran with the default (o2's slip): every job's record echoes what was applied and
  the scorer gates on it: knob read back, dword 6 from the arm dump, `tick_gap` from the job's own
  ring, `skipped`, the slot 3 flag, and for h3 the clears' time stamps before the stop. The mock
  (`tests/run_mock.py`, `mockfw/kmock.py` extended: `timer_clock` at boot, a lockup after 20
  ticks of a skipped render with the marks) runs all three stages; three negative mocks must
  score REFUTED or void: a mock that ignores `timer_clock` (h2 void by the gap gate), one that
  stops by time (H-TICKS refuted), one without marks (H-NOMARK).
- `SGX_DRY_RUN=1` prints the laptop commands; the generator test checks that only 0x0134 and the
  knobs `hold_recovery`, `timer_clock` are ever written.

**Cost and risk.** About 7 minutes of jobs (a stop job 30 to 35 s), 15 minutes wall with staging
and three stage ends, 25 with trouble. 10 predicted stops: 21 kept stops of this signature all
recovered by one debugfs reset, the one with the marks (b1p) too (reset, gate, health exact), so
the marked kind has one recovery on record: h1's first B1P is the test of that, and its rule ends
the session if it fails. No kernel change, no build. Risk of a leftover: `timer_clock` (restored
and read back at each stage end and in the driver's `finally`).

## 6. What the results would change

- h1 3 of 3: Q166's round 4 rule is met (H-W on `CR_EVENT_HOST_CLEAR` bits 15 and 18, 4 jobs
  with r4's); Q295's "why" is the lockup check, held out. New records: one for h1 (marks, count,
  clears), one for h2 (dose), one for h3 (running EDM). Corrections as F0 if not folded before.
- Specs: hw_spec 12.2 (the skipped slot 3 pass; two kinds of stop), `boot_sequence.md` (HWR seen;
  the sampling in ticks), `usse_isa.md` 3.6 (a task that takes over slot 3's end of render must
  end the firmware's 3D check or own the tick), model-tasks.
- Left open whatever h runs: the state of O4 item 3 (R-6, then perhaps a "skip and clear" task in
  a later round), `CR_EVENT_HOST_CLEAR` on bits other than 15 and 18 (Q111), the TA side of the
  same check (dword 55 and 56; not planned).

## 7. User decisions

1. **Fold the offline finding (F0) before the hardware?**
   (a) Yes, now: new record, appended corrections on E836 and E353, Q295 narrowed, the
   predictions of h1 start from landed text. (recommended)
   (b) Wait and fold it with h1's results in one record.
2. **Reading R-6 of our disassembly (three items, notes to data-private)?**
   (a) Yes, before the freeze, by the lead with the E154 method; its three predictions frozen
   first. (recommended: it is the only route to "which state", and costs no laptop time)
   (b) After the hardware, only if h3 leaves H-STATE standing.
   (c) No reading; Q295 is retired on the mechanism alone.
3. **S0, the pysgx oracle run (2 hours, time boxed)?**
   (a) Yes, after R-6. (recommended)
   (b) Skip; sim in sync only from the hardware rows.
4. **h1, the B1P replicates, with a stop now the predicted outcome?**
   (a) B0 + B1P x3, the stage continuing after each recovered stop. (recommended)
   (b) B0 + B1P x2 (r4's two unrun jobs only).
   (c) Keep r4's rule (first stop ends the stage): one job a session.
5. **h2, the dose test through `timer_clock`?**
   (a) 800000 and 1600000, B0 + B1P x2 each (6 jobs, 4 stops). (recommended)
   (b) 800000 only (3 jobs; E084 measured that clock).
   (c) Instead, a `hwr_sample_rate` debugfs knob in the fork (dword 5 = 20: predicted 40 ticks):
   a kernel change, cachix build and a one-shot boot with your OK.
   (d) Skip: H-TICKS rests on the count 20 alone.
6. **h3, the clears on a running EDM (Q166's open clause, Q295's candidate 1)?**
   (a) B0 + B1E x3 at 1600000 (needs 5 (a); 3 stops). (recommended)
   (b) Skip; Q166 says "stopped EDM only".
7. **Q166 after h1 (and h3)?**
   (a) Retire it if H-W holds 3 of 3, other bits left to Q111. (recommended)
   (b) Keep it open for bits other than 15 and 18.
8. **Q295 after the session?**
   (a) Retire it if h1 and h2 hold and R-6 names the state; otherwise narrow it to what is left.
   (recommended)
   (b) Keep it open until a task of ours skips the handler and keeps the tick.
9. **Place in round 5's laptop order?**
   (a) Any slot; it needs no reboot and no kernel change, but must not overlap another session
   and must end with `timer_clock` 0 verified. (recommended: first, 15 minutes, as a health check
   of the laptop state)
   (b) Last, as in round 4.
