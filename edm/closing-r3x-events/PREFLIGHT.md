# R3x-events preflight (prepared 2026-11-10, not run)

Everything is under `~/src/scratch/resgx545/closing3/r3x-events/`, a copy of
`closing2/r3-events/` (which was not edited). The landed tree, the data, the linux fork and the past
session directories were read, not changed. The laptop, cachix and every git repo were not
touched; nothing is committed; the clean-room guard was not run; no closed source was read.
Frozen: `FROZEN.sha256` (every generator, scorer, runner, script,
table, blob, source, prediction and what they import from the landed tree), `PREDICTIONS.sha256`
(4 files), `LAPTOP.sha256` (the files as laid out on the laptop under `~/r3xev`).

Checks that pass (the dated run is at the end of this file): `tests/run_all.sh` = `run/guard_r3.sh`,
`run/freeze_r3.sh verify`, `tests/sim_r3.py`, `tests/test_scorer.py`, `tests/test_guard.py`,
`tests/run_mock.py`; both new blobs also build and verify through the landed CLI
`tools/fwtask/fwtask.py OUTDIR source.s...` to the same sha256 as `bins/` (alias2 `c41bd078...`,
ring_end `0dd75bc9...`, ring_hold `fa0f79db...`).

## 1. What runs (the binding decisions R3-E1 to R3-E9)

One session, laptop directory `~/r3xev` (results `~/r3xev-out`), pinned tool `~/sgxfive-test-s1b`,
stages h, c, e, d in that order. Stage f and the Q290 rows are not here. Each stage's gate is the
previous stage's kept `stage.json` (exit 0, or 8 with `--from`).

| stage | blob | jobs | what | reset + arm |
|---|---|---|---|---|
| h | ring_hold.blob | 6 | H0 x3 (no hold: two signatures at 20 and 60 ms, 20 `status` reads), H1 x3 (the same inside a 90.5 ms hold, one `status` at 40 ms) | each job |
| c | alias2.s | 13 | C0 x2, C1 x3 (= A7), C2 x2, C3 x2, C4 x2, C5 x2 | stage start, after a stop |
| e | ring_end.s | 5 to 7 (4 if X1 stops) | E0 x2, X1 x2 (slot 2), X20 x2 (only if X1 kept 2 of 2), B3 x1 LAST | stage start, after a stop |
| d | alias2.s | 4 to 7 | D0, D1 (+2 only if kept), D2, D3 (= A8), D4 (only if D3 kept the tick) | each job |

Jobs run: **expected 32** (H-NOTENDED, H-EXIT, H-CCB worlds: 6 + 13 + 7 + 6; the mock's default
session runs exactly 32), minimum 27, **maximum 33** (the H-ONCE world: D1 x3 and D4 run). See
DEVIATION 2.

Rows, parameters and frozen predictions are in `TABLES.md`, `predictions/*.tsv`; the single source
is `gen/r3layout.py` (`ROW_SPEC`, `E537`, `TESTED_PA1_MASK`), checked by the generator, the runner,
the guard and the scorer against each other.

- h: H0 x3 control (clock status 0x20 or 0x78, EMPTY set, D0 = page pass count minus HostCtl
  dword 12 one modal value); H1 held out, hold band 2262434 +- 0.2 % + 50 units (S2b); H-NOTENDED:
  all four signature elements and clock 0x000ccfa0 as a running task, D = D0 or D0 + 1; H-REARM:
  some element differs.
- c: C0 fit (E791's A0: pclink 0x98, p1 1, sa64 2, sa65 K<<24, sa63 0). C1 sa65 = K<<24 | 1<<23;
  C2 sa65 = 0xb0000000; C3 sa65 = K<<24 | 0x1c04c (bits 2, 3, 6, 14, 15, 16: all outside the tested
  pa1 mask 0x780790, R-4); C4 sa65 = K<<24 | 1<<19; all kept, next entry pclink 0x98 and sa65
  K<<24, C1 also read = write and dword 14 = 0. C5 cmd 12: sa64 = pa0 & ~2 on 50 consecutive
  passes, kept, pclink 6 after the last, dword 12 - passes = -50 +- 8, D = D0 + 50 +- 1.
- e: E0 control (14 +- 2 entries on the 25000 grid, nothing acted). X1 = a plain tick handed to the
  closed task of slot 2 at 0xace (R-2: 17 + 5 instructions, no group bit, no state word): H-EXIT
  and H-TICKONLY keep the tick (next gap 25000 +- 50, a flag-4 entry), H-BODY stops it (busy, read
  = write, dword 14 = 0). X20: 20 such passes, kept, dword 12 - passes = -20 +- 8. B3 = one
  `miscinfo` whose kick pass ends with our own `idf, wdf, nop.end`: H-EXIT and H-BODY stop (busy,
  `miscinfo` not answered, read = write - 1, one kick entry flag 3, nothing after), H-TICKONLY keeps
  the tick (grid kept, read = write - 1, not answered).
- d: D0 control; D1 sa65 = 0xb009c4dc (E537's, bit 8 clear), D2 sa65 = K<<24 | 0x100, D3 sa65 =
  0xb009c5dc (E537's, the fit row), D4 = E537's sa63 0xd7c5f5ae, sa64 0xb0150d9d, sa65, r20
  0xf8a4ac80, r21 0xfcf393c8, i0 0xa958e53c, i1 0xd90c0733, p0 = p1 = 1 (R2-1 b's set, nothing
  more; sa63 put back afterwards). H-CCB: D1 kept, D2 and D3 stop with read = write + 1, dword 14
  = 0xad002600, busy; H-HANDLER: D1 and D3 stop, D2 kept, dword 14 = 0; H-ONCE: everything kept.

## 2. The runner, what is new (copy of closing2's `r3_run.py`)

- Preflight: srcversion loaded = installed = **B21FDA82BD5E5CB5A627E3B** (any other: exit 1), the
  debugfs files own_code, own_arm, own_res, load, boot, reset, regs, status, miscinfo, the pinned
  tool, the frozen files, the whole table against `ROW_SPEC` (job names and order, words, counts,
  triggers; any value outside: exit 7), the previous stage's kept `stage.json`.
- `captured()` keeps every line of a tool command's WHOLE output that names a failure (`FAIL`,
  `Traceback`, `"error"`, `BUG`, `Oops`); an arm, reset or gate with such a line is not ok.
- Every job: D0 baseline (20 triples page pass / dword 12 / page pass), the row, the tick bracket,
  the CCB offsets and dword 14 after it (`marks_post`).
- A stop is signed BEFORE anything else: P1 the signature twice 30 ms apart with HostCtl dword 14,
  the CCB offsets and the pass count (so D against the row's D0 is P2), the landed dumps, then P3
  (one `miscinfo` into the stopped EDM, the window open in the ring stages so that a kick entry
  would show; the registers again). Not in B3. Then reset + gate + health (`end()`), recorded.
- A stopped row is never replicated (its later jobs are `skipped`); `run_if` rows (X20, D1
  replicates, D4) are gated on kept output (`all_kept:ROW:N`).
- Budgets: stages c, e, d take one stop and go on, the second ends the stage (exit 8, reset and
  gate exact); stage h takes none (DEVIATION 1). A freeze (exit 6) or a watchdog line (exit 3) stops
  all laptop work.
- The only debugfs writes are own_code, own_arm, own_res (the page), load, boot, reset; the only
  kick is `miscinfo` (the kernel's own command and kick together: a bare kick with no command is
  never built: the guard refuses a trigger other than `none` or `miscinfo`, any `kicker`,
  `kick_no_bump`, `xfer_sync` word, and a `cont4`).

## 3. Controls that can fail, void and cannot-tell states

Controls: H0 (idle, D0 modal) and H1's hold band; C0 (A0 as E791 read it) and the writer's
read-back (void if the sa65 written is not what the row says, or if the task's own record of sa65
at entry has a count byte other than K); C5's own pass counter (void under 50 passes); E0 (14 +- 2
entries on the grid, nothing acted) and ACTED = the design (void otherwise); D0.
Cannot tell: a signature sample outside the hold (STATE not busy around it), the reader not run
but the tick kept, the KIND of pass never came (ACTED 0), the acted pass not logged first, a ring
full before the acted pass, an unreadable signature. Void: no record, a stale record, a class that
is not a result, no page, a ring that changed after the close, a corrupt flag. Void and cannot-tell
rows never count as a pass. Fit rows (C0, D3, E537's dump) are kept apart from held-out rows and
replicates in every tally; 0x012c is dropped from the stop-signature match (0b) and kept as a value.

## 4. Time

Pure job time under 2 minutes (about 3 s a reset-and-arm job in h and d, 0.2 to 0.5 s a job in c
and e; B3 and each P3 wait up to 0.5 s for the kernel's timeout). Each stop adds P3, the
reset, the gate and, in c and e, a re-arm: about 35 s. Each stage end: reset, gate, health, copy,
score: about 40 s. Expected about 15 minutes wall (3 stops), 20 with every stop budgeted. The mock
session (real sleeps, no hardware) takes about 30 s.

## 5. Risks

- Stage h: none beyond S2b's (the same blob, the same hold). Two samples read inside a 90.5 ms hold
  each time; if one falls outside, the row is cannot tell, not wrong.
- Stage c: low (every word carries only bits with no handler, except C4's bit 19 which posts
  nothing and C5's sa64 write, E792's A4 repeated 50 times).
- Stage e: medium. X1 runs closed code on an event it was not started for (slot 2's fast path: 12
  instructions then the shared exit; no memory, sa or state read, R-2). B3 ends a kick pass without
  the closed task and stops the tick if H-EXIT or H-BODY hold; the reset recovers it (E793: 2 of 2).
  **The kernel's overlay of a second continue patch (`cont2`) in entry 0 is not provable offline**
  (the landed `fwtask.apply_patches` is the model; the fork's test file is the reference). If the
  kernel refuses the blob the arm is not ok and the stage ends (exit 4) before any job.
- Stage d: the expected-stop stage, last. D2 and D3 make the closed task consume a never-written
  zeroed CCB slot and (0a, [infer]) branch to address 0, where the routine at 0x0-0x5 stores
  0xad002600 and goes to a poll on CR_EVENT_STATUS bit 6; E537 recovered by the debugfs reset
  (1 of 1), E793 2 of 2. D3's replication of E537 can also hang nothing (H-ONCE).
- P3 sends one `miscinfo` into a stopped EDM: the kernel times out after 500 ms and prints its dump,
  no automatic reset (read of `sgxfive_miscinfo`); the next thing the runner does is the reset.
- Laptop limits held: no clock-gate register write, firmware `str` none at all, no trc_hazard, no
  reboot, GRUB or build, debugfs via `sudo -n`, kmsg via `os.open(O_WRONLY | O_APPEND)`.

## 6. DEVIATION entries (from the design or the decisions as written)

1. **Stage h takes no stop (budget 0: the first stop ends it).** The design table says "0 stops
   expected, cap 1"; R3-E2 says "the second stop ends the stage (cap 2 per stage)". Both are kept
   as written for c, e, d; h follows its own table row. Total stop cap is then 1 + 2 + 2 + 2 = 7,
   not 6 (the 6 counts c, e, d). One line in `gen/r3layout.py` (`STOP_BUDGET`) changes it.
2. **Job counts.** The design says 28 to 32; the arithmetic is 27 to 33 (expected 32). The 33rd is
   D4 after three D1 reps; the low end is X1 stopping (4 jobs in e) with D1 stopping (4 in d).
3. **C2's word is the literal 0xb0000000** (count byte 0xb0, not K), as the design writes it; C1,
   C3, C4 and D2 use K << 24. D1 and D3 are E537's literal words (count byte 0xb0).
4. **If D1 and D2 both stop, stage d ends before D3** (the cap rule). R3-E3 says D3 runs even if
   D2 alone already shows E537's marks, which it does; D3 is lost only in the two-stops-before-D3
   case, as exp-events-r3.md section 2 already said.
5. **`alias2.s` keeps alias.s's commands 1-7 and 9 unchanged** (command 7 restores sa63 after a stop
   and after D4); the tables reach only 0 (the host's reader), 10, 11, 12 and, in the runner's
   baseline, 7. The guard checks every command's sa set by decoding the words, so the unreached
   code is bound by the same limits. `ring_skip.s` is gone: `ring_end.s` replaces it, so B0 to B2
   and the skip of stage b are not in this session.
6. **cmd 12's counter is held in r8** (the landed verifier's `ima32` row accepts only that form);
   no effect on the experiment.
7. **H1's signatures are two samples 10 ms apart** (a stop's signature keeps the 30 ms of R3) so
   that both signatures fit inside the 90.5 ms hold; the page's STATE is read around each and a
   sample outside the hold is cannot tell.
8. **P3 sees the ring only in stages h and e** (alias2 has no ring); in c and d P3 is judged on
   answered / not answered and on the CCB offsets after it.
9. **D4 puts sa63 back afterwards** (cmd 7, then the reader), and after a D4 stop re-arms and
   restores before the stage's final reset. sa63 is inside R2-1 b's set; nothing else is written.
10. **A one-off addition:** a stage-h stop scenario, `X20` ring-full (16 rungs, 4 drops) and the
    D baseline are new instruments with no precedent run; their predictions are what the design
    states, not fitted.

## 7. Dated run (2026-11-10, Mac, offline)

`tests/run_all.sh` after the freeze: RUN_ALL PASSED (about 3 minutes).

| check | result |
|---|---|
| `run/guard_r3.sh` | clean (3 blobs, 4 tables, scripts, runner) |
| `run/freeze_r3.sh verify` | files verified (37 frozen files, 4 prediction files) |
| `tests/sim_r3.py` | 91 checks, 0 failed (every command path of alias2.s incl. 10, 11, 12; ring_end.s KIND, ACT, COUNT, flags 3 and 4, tail to slot 2, window rules, X20 ring full) |
| `tests/test_scorer.py` | 132 checks, 0 failed (E537 and E793 dumps, R3's real A0 and B0, S2b's hold page; a world each for H-NOTENDED, H-REARM, H-EXIT, H-BODY, H-TICKONLY, H-CCB, H-HANDLER, H-ONCE, each winning in its own and losing in the others; void, cannot-tell, stale, gates) |
| `tests/test_guard.py` | 53 checks, 0 failed (every limit broken in a copy) |
| `tests/run_mock.py` | 17 tests, 127 checks, 0 failed (the default session h, c, e, d with 32 jobs and d's two stops; the H-ONCE session with all 33; one scenario for H-REARM, an h stop, one and two c stops, P3 answered, H-BODY, H-TICKONLY, H-HANDLER; gates, preflight refusals, fatal, arm, tool-message, gate-fail and exception paths; the debugfs trace) |

Freeze hashes (sha256 of the files, first 16 hex): `FROZEN.sha256` 27de581c54c552f0, `PREDICTIONS.sha256` d8a1cbccda63b121,
`LAPTOP.sha256` e87eeb52da52b710. Blobs: alias2 `c41bd078cd42eb33...`, ring_end `0dd75bc9102981ed...`, ring_hold
`fa0f79dbb5864187...` (S2b's, byte for byte).

## Refreeze 2026-11-10 (lead, before the first job)

Main moved to 7aaa017 (r3-kernel landed) after this session was frozen, changing
`tools/fwtask/fwtask.py` and `regs.toml`. alias2, ring_end and ring_hold were rebuilt with the
verifier at 927bea4 (the laptop's running kernel's rows) and at 7aaa017: all three are byte
identical to the frozen blobs (c41bd078..., 0dd75bc9..., fa0f79db...). Only FROZEN.sha256 was
regenerated (old kept as FROZEN.pre-l3-refreeze.sha256); PREDICTIONS.sha256 is unchanged.
