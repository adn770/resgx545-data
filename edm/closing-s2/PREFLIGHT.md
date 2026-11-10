# S2 preflight (prepared 2026-11-09, not run)

Everything under `~/src/scratch/resgx545/closing/s2/`.  The laptop was not contacted, nothing is
committed, no landed tool was changed.  Offline checks that pass: `run/guard_s2.sh` (clean);
`tests/sim_s2.py` (37 checks: the four blobs in sgx-sim: window protocol, filter, ladders and
drop counters of all four slots, the hold's stamps, run id, n = 0 guard, three instructions an
iteration, busy flags, the E2a areas, the writer writing only sa67/sa68 and reaching its tail
call with p0..p3 = 0, 0, 1, 1); `tests/test_scorer.py` (33 checks: every hold shape, a 2^25
wrap, a down-counting timer, dispatch and filter rules, void rules, the reviewer's long-hold ALL
case, the E5 control comparison); `tests/run_mock.py` (28 tests, 102 checks, 0 failed: the whole
session through the real `stage_s2.sh`, `s2.sh`, runner and scorer against a mock laptop, each
gate closing, each stop rule, the predictions failing when the mock says so, the guard catching
injected lines, and one test per review item, section 6).  The freeze (`run/freeze_s2.sh
freeze`) was run after the last change; `run/freeze_s2.sh verify` passes.

## 1. Jobs and time

| stage | jobs | conditions | laptop s | blob (insns) |
|---|---|---|---|---|
| e1c | 10 | 4 | 12 | ring_e1 (640) |
| e1j | 14 | 5 | 30 | ring_e1 |
| e2r | 3 | 1 | 5 | pa_read (71) |
| e2w | 9 | 4 | 8 | pa_write (135) |
| e4c | 3 | 1 | 5 | ring_hold (747) |
| e4h | 8 | 3 | 8 | ring_hold |
| e4l | 2 | 1 | 5 | ring_hold |
| e5c | 5 | 2 | 8 | ring_hold |
| e5t | 5 | 2 | 10 | ring_hold |

59 jobs, 23 conditions (e1c gained `q50k` after S2 run 1, section 7).  Each stage adds an arm
(about 0.6 s: load, boot, three tick reads, a 300
ms rate window), a reset and gate at its end (about 2 s), and on the Mac one ssh, one copy, the
health script and the scorer (about 6 s).  Estimate: 2 to 3 minutes of laptop time, 4 to 6
minutes wall time without pauses, plus staging (under a minute, no build); allow 15 minutes with
reading the gates.  The mock session (no GPU) ran in 12 s.

## 2. Risk per stage (the runner stops at the first trigger; any stop ends S2)

- **e1c**: low.  Reads and stores to the page only, tail-calls every pass (E538's shape); new: a
  640-instruction blob (5240 bytes; the code page is 8 KiB), the window protocol.
- **e1j**: low to medium.  The first run of client jobs with our wrappers armed in slots 1-3:
  E538 had a kick only and E605 ticks only (E538: "Q033's Q2 needs a job and was not run").  The
  partial render (`render_pb_pages` 0x30, E547's recipe) is last; the knob is read back, marked,
  and put back to 0x422 in a `finally`.
- **e2r**: low.  As mem.s (E532): no sa, r-only writes; reads sa64..sa68 and sa0 (sa66..68 never
  read before: reads only).  Ends with p0 = p1 = 1 at the tail call, as mem.s did safely.
- **e2w**: medium.  Writes sa67 and sa68, unmeasured registers of the closed task.  The writer
  reaches its tail call with p0..p3 = 0, 0, 1, 1 (E536's safe writer), so its one difference from
  E536 is the register written (E537's stop came with sa63, sa65 and p0 = p1 = 1, cause not
  separated).  Stop rule: the tick not advancing over three reads (or no next pass): dump, reset,
  gate, no second attempt.  sa survived a reset in E536 (sa100, sa127), so the stage ends by
  writing sa67 and sa68 back to the values its own control read (`restore67`, `restore68`).
- **e4c**: low (no hold).  **e4h**: low to medium: holds of 0.7 to 20 ms, ticks only (E539 and
  E605 held 6.9 ms).  **e4l**: medium: 100 ms, never run; no job in flight; the kernel's job
  timeout is 500 ms (`sgxfive_sched.c`), its watchdog a 50 ms periodic check of job hangs and BIF
  faults (`sgxfive.c`), neither of which a hold with no job trips.
- **e5c**: medium: a GETMISCINFO kick during the 100 ms hold; the debugfs read waits at most 500 ms
  (`sgxfive_debug.c`: "no MISCINFO_READY after 500 ms") and is a result, not a stop.
- **e5t**: medium: a 64 x 64 triangle in flight during the 100 ms hold, `hold_recovery` Y for that
  job only (read back, marked, put back after the page read).  A triangle that does not complete
  ends the stage after the page read, the release, a reset and the gate.

Every job: a kernel-log marker before it (`resgx545 s2 case NAME RUN`), the knob read-backs
marked, the class marked after; its JSON (page, second page, timings, tool output, rc, class),
its kernel-log slice and a cases.tsv row are written in a `finally`, so a failing job keeps its
data.  The scorer reads only records of the stage's last run (run id), so a file left by an
earlier run is never scored.

## 3. Ready, and what is missing

Ready: four sources and blobs (landed verifier: accepted), nine tables, frozen predictions (10
files) and scorers with one SUMMARY line a stage, the runner with the gates and stop rules, the
driver, staging, the guard, the tests, `TABLES.md`, `README.md`.

Missing, in the order they matter:

1. The laptop is unknown here: `~/sgxfive-test-s1` (built by S1's staging) and
   `/home/jtorra/sgxfive-test` (the landed `cmd_gate` hardcodes it) must exist; the module must
   be branch `resgx545` with `own_code`, `own_arm`, `own_res`, `hold_recovery`,
   `render_pb_pages`, `miscinfo`.  `stage_s2.sh` checks, as root, the gate tool, the python that
   `sudo -n python3` runs (3.8 or newer) and an sgx debugfs directory found through `dri/*`; the
   runner's preflight checks the same and refuses otherwise.
2. The landed `fwtask_run.py` assumes `/sys/kernel/debug/dri/0/sgx`; the runner falls back to the
   first `dri/*/sgx` if that is missing.  `tools/bringup/health.sh`, which `s2.sh` runs between
   stages, also hardcodes `dri/0`: that directory is present on the laptop now (coordinator,
   2026-11-09), so S2 depends on it there and only there; if it moves, health fails and S2 stops.
3. No verdict rule is frozen for Q111's order (events 0d): e1j prints each job's merged order
   beside E547's first-rise orders (`predictions/e1-baseline-order.tsv`); the comparison is read
   by hand.  The HostCtl dword 12 delta of each E4 job is printed as a cross-check only (E605:
   its `regs` reads add about ten ticks).
4. E5 has no favoured outcome (QUEUED or LOST, both frozen as discriminants).
5. The mock cannot show that debugfs refuses an unprivileged reader; the guard checks statically
   that every debugfs access runs under `sudo -n` and the runner refuses to run as non-root.
6. `debugfs reset` (the landed `cmd_reset`, after every stage and every stop) makes the kernel
   run its boot sequence, which writes the clock-gate registers from the firmware's own data, as
   in every earlier batch (S1 PREFLIGHT 5.1).  No S2 code writes a clock-gate register.

## 4. Tool changes (none needed to run S2)

- None to the kernel: no `mov`-to-pa form, no CLEAR/CLEAR2 `str` rows, no skip of a closed handler
  (E2b, E3a, E3b are out).  No `str` at all in the four sources; `ldr` only of CR_TIMER (#81).
- Optional, `tools/fwtask/fwtask_run.py`: take the debugfs directory from `dri/*/sgx` (3 lines).
- Optional, `tools/fwtask/simrun.py`: `run()` loads only `asm/fwtask/<name>.s`; a `blob=`
  parameter (about 5 lines) would let `tests/sim_s2.py` drop its 40-line copy of `run()`.
- Before any result is recorded: land the four sources in `asm/fwtask/` with their
  `fwtask.map` rows (4 generated files, 1750 lines; `test_sources.py` checks them), the scorer as
  a landed tool (`tools/fwtask/score_events.py`, about 680 lines, already standard library), the
  page layout into `tools/fwtask/layout.py` (about 70 lines), and the runner if it is to be reused
  (about 460 lines).

## 5. Claims of exp-events.md that the source or the records contradict

1. 0a: "E536's safe writer touched none of sa64 to sa66".  E536's writer (state2.s cmd 1) wrote
   sa64 (the record's claim and `state2.s`), and the next event read sa64 = 2, not the marker.
   The plan and the brief ("E536 wrote other sa / sa64 safely") agree with the record.  sa64 = 2
   after a write fits 0a's alias (PDS #13 rewrites pa0 every event); the proposal does not use it.
2. "E537's sa65 write stopped the tick" (0a, plan decision 5): E537's stop is not established as
   the sa65 write.  E537 (1 run) assigns the stop to one of the sa63 write, the sa65 write, p0 =
   p1 = 1 at the tail call, or their combination.
3. E1 table, tri 256 x 256: under H1 status bit 10 (TPC_FLUSH) is pa1 bit 12, slot 0; the row
   lists only "+ s1: 9".
4. E1 table, "copy (SW_EVENT only)" and "fill (18)": E547's timelines show bit 26 in 1 of 5
   copies and bits 14, 26 and 31 in fills of the r7 set.  The scorer uses the union of E547's
   timelines and E548 per kind.
5. E1 "Deciding": the slot does not separate H1 from H2 on the fill: under H1 a word with SW_EVENT
   (pa1 bit 8) or pa0 not 0 goes to slot 0 (E146: bit 8 general, fast paths only with ir0 = 0).
   S2 decides on the witness bit (pa1 bit 4 against bit 18) and checks every entry's slot against
   E146's dispatch as an instrument control.
6. E1 "about 450 words": 640 (ring_e1) and 747 (ring_hold) instructions at 13 a rung, under 1024.
7. E1 row 2 "must fill 8 ticks": the count follows the host's open time (8 ms sleeps ran 10 to 12
   ms on the Mac); the frozen prediction is entries = open time x 0.997 +- 1.5.
8. E4: H-ONE and H-DELAYED both predict entries at the exit and then the original grid; they are
   not separable as written.  The frozen classifier names LOST, ONE, ALL, PARTIAL(q), OVERLAP and
   `/offgrid`, and says "cannot tell" when the exit falls within 50 us of the old grid (a pending
   tick and a natural one look alike; about one job in ten by chance).
9. E4 row 1 "hold n = 0": the slow loop of `slow.s` and `p1137_slow4.s` decrements before it
   tests, so n = 0 would run 2^32 iterations (about 4.6 minutes at 65 ns).  `ring_hold.s` tests n
   first, row 1 sends no command, and the runner refuses n above 1.6 million.
10. E5 "the tool launched at once after the command": the hold starts at the next event after the
    command (up to a tick later), so a kick issued at once can arrive before the hold (the mock
    showed it).  S2 waits 3 ms, reads STATE once, and voids the job unless it reads busy.
11. E5: job events delayed by the hold land after the exit whether they were queued or the job
    started after the hold, so the stamps alone cannot show overlap.  S2 shows it with the tool's
    own render time (`tri 64x64 #1: N us`) against the no-hold control.
12. E5 row 4 ("E1 row 6 again") runs in `ring_hold`, not E1's blob, and before row 3 (controls
    first); E5 rows 2-4 use the window with the slot filter, row 1 the window without it (E4 row 5's).
13. E2a "the next pass (the next tick, command 0)": a pass with command 0 does nothing in these
    tasks; S2 arms command 9 (state2.s's reader pattern) and proves the next pass by state 3.
14. CR_TIMER: E009 measured TIMER counting up at core / 16 (24.94 MHz).  The p1141 draft decoder
    (`ring_decode.py`) says CR_TIMER "counts down: a 25-bit watchdog per E155/E532"; neither record
    measures CR_TIMER's direction or width.  The scorer handles both directions and a 2^25 wrap and
    reports which it saw; the clock control fails unless it counts up 25001 a tick.
15. E1 Tooling: "the laptop side has `events` and `page`; a window write is one `res.w`".  The
    landed `events` command has no window protocol, and `one_cmd`, `cmd_tailpair` and
    `wait_state` poll the page until a deadline; S2's runner writes the window through the landed
    `Res` and calls none of the polling commands (the guard checks it).
16. E2a "command 1 three times, then 2 and 3 three times each" in one blob: S2 uses two blobs (the
    gated read pass cannot write sa at all) and restores sa67 and sa68 at the end (item 2.e2w).

## 6. Fixes after the independent review (2026-11-09)

Each item has a test that failed on the code before the fix (`tests/run_mock.py`
`t_review*`, `t_e5c_kick_lost`, `t_stop_arm`; `tests/test_scorer.py` "review 5", "review 6").

1. Stale gates: `s2.sh` writes `GATE STAGE NONE (running)` before a gated stage's ssh; the
   scorer writes `run=<id>` into every gate line; the runner opens the next stage only if that id
   is the one in its own `~/s2-out/<prev>/stage.json` with exit 0.  A stopped rerun of e2r no
   longer leaves an OPEN gate, and a gate of another run cannot arm `pa_write`.
2. A GETMISCINFO timeout reaches Python as `TimeoutError` (the kernel's seq_file text is lost):
   the runner catches `OSError` around the read and records the errno and "no MISCINFO_READY", so
   `kick-timeout` and E5's LOST are reachable and the runner no longer crashes with our task armed.
3. One cleanup for every stop after the arm began (the arm's own failure, a dirty page after it,
   a knob stop, any other exception): dump, reset, gate, exit 5 if they are not exact.  `job()`
   writes its JSON and cases.tsv row whatever fails; `main()` starts at exit 1.
4. A job's kernel-log slice starts at its own marker line (a line count is blind once the ring
   buffer is full); `s2.sh` also stops on a watchdog line (33) or an unreported hung, recovery or
   fault line (38) in the stage's whole `kernel.log` before scoring (a stuck triangle's expected
   recovery line excepted).
5. A long hold whose queued burst fills the ring no longer reads PARTIAL: with the ring full and
   nothing after the burst the shape is `ALL-or-PARTIAL(>=q, ring full)` (q is a lower bound; the
   drop counter also counts later natural ticks), ALL when q is within one of floor(H).
6. The E5 control compares shape classes (ONE and ONE/offgrid alike), drops cannot-tell on both
   sides, needs a told match and no told mismatch, and does not depend on set order.
7. e2w's restores are verified: a skipped restore, or a same-pass read-back that is not the value
   the control read, stops the stage (4); `s2.sh` prints a WARNING that sa67/sa68 may still hold
   the S2 marker whenever e2w stops; the e2w SUMMARY names the restores and whether both held.
8. The hash chain is closed at scoring: a stage whose `env.json` table or blob hash differs from
   the Mac's frozen files (or is of another run) scores `cannot tell`; `s2.sh` compares the
   laptop's `LAPTOP.sha256` with the local one before each stage (21).
9. Prerequisites checked as root at staging and in the preflight (section 3 item 1).
10. A failed instrument control makes the verdict `cannot tell (instrument control failed ...)`:
    e1j's dispatch rule, e2w's control read pass, e5t's no-hold controls (each valid, with a
    render time and at least one event entry).

Not changed: the gate after e4h and e4l stays a safety gate (valid, done, knob in band), not a
prediction gate, as before.

## 7. After S2 run 1 (e1c, run id 1794264422-17682): the kick rebuilt

Frozen verdict of run 1: `GATE e1c CLOSED` (quiet 3/3, ticks 2/2, kick 0/3).  Post hoc, fitted to
its three kick jobs (the analysis is in the report of 2026-11-09; `out/analysis-e1c.md` was not
written by the agent, the harness refused report files): the kick is one event with pa0 = 0 and
pa1 = (K << 24) | 0x100; pa1[31:24] is a count K that every event carries (2 after the arm, +1 a
kick); pa2 is EVENT_TIMER when the event is taken (the kick's pa2 phase agrees with the CR_TIMER
stamps within 3 units in 3 of 3; a tick reads 400000 - 16).  E538's "kick" words were the tick
after the kick.

Changed for the rerun (tests first: the mock now emits run 1's words, and the old code closes
e1c's gate on it; `tests/sim_s2.py` checks the new filter on the blobs):

- **Sources**: the window-1 filter masks pa1[31:24] (a plain tick is pa0 = 2 and pa1[23:0] = 0;
  run 1's masked bit 25 only, so every tick after a kick passed it).  `ring_e1.s` and
  `ring_hold.s` change in that one constant; new blob sha256 `0453863a...` and `fa0f79db...`.
- **e1c table**: the kick rows log every pass (window 2) so the ticks around the kick are seen;
  new control `q50k` x2 (window 1, 50 ms quiet after the kicks, K = 5) must log nothing: it fails
  on run 1's filter.
- **e1c predictions**: the kick (fit: S2 run 1, 3 jobs), held out for the rerun: exactly one entry
  that is not a plain tick, slot 0, pa0 0, pa1[23:0] 0x100 (gated); pa2[31:24] 0x01 and pa2[23:0]
  in 1..399999, not 0x061a70 (EVENT_TIMER's format and range, E009); (400000 - pa2[23:0]) / 16
  equal to the CR_TIMER time from the tick before (or to the tick after, from 25000) within 50
  units (run 1's residuals -1.6, -1.9, -2.8); ticks before the kick carry K, after K + 1; K = 2, 3,
  4 in job order; ticks unchanged (pa0 2, pa1[23:0] 0, pa2 0x01061a70, on the grid).  q50 and q8
  as they were.
- **Gate G1**: q50 3/3, q8 2/2, the kick's identity 3/3, q50k 2/2.  The pa2 range and phase, the
  count step and the count values are scored and reported as held-out predictions, not gated.

Later predictions and gates that rested on the old premise, all changed:

1. e1j and E5's window-1 rows (kick100, tri-nohold, tri100) through the filter (sources above).
2. e1j's scorer read pa1 bits 24 to 31 as event bits after masking only 24 and 25: now pa1[23:0]
   only; H2's allowed sets dropped status bits 26 and 31 (they would fall in the count byte); bit
   8 is allowed under H1 and H2 (a host kick raises it, so a job's own CCB kick may log it); the
   fill's witness (pa1 bit 4 against 18) ignores entries with the kick's words.
3. Withdrawn e1j rows: "bit8_entries_per_job 1 a fill, 2 a triangle (H1, SW_EVENT)" (bit 8 is
   confounded by the job's own kick) and "pa2 = 0x01061a70 on every job event (Q157 constant)",
   replaced by "pa2 in EVENT_TIMER's format and range" (held out).
4. e5c found the kick entry by pa1 bit 24: now by the kick's words.

Not affected: e2r/e2w (their passes are ticks, where pa2 is 0x01061a70, so the gate sa66 =
0x01061a70 stands; H-D's sa65 = pa1 includes the count byte on both sides), e4c/e4h/e4l (ticks
only), the hold shapes.

Offline note (to section 5), not a contradiction: pa2 = 0x01061a70 = 0x01000000 | 399984
(400000 - 16), the
format of EVENT_TIMER (bits 31:24 = 0x01, low 24 bits below HostCtl dword 6 = 400000, E009),
whose host reads never exceeded 0x615eb in E009 [infer: a latched EVENT_TIMER value; Q157].
