# R3k preflight (prepared 2026-11-10, not run)

Everything is under `~/src/scratch/resgx545/closing3/r3k-events/`, a copy of the framework of
`closing3/r3x-events/` (L3; not edited). The landed tree (resgx545 main `7aaa017`, `tools/fwtask`,
`tools/usse-asm`, `crates/sgx-sim`), the fork (`/Volumes/linux/linux-sgx-r3`, read only), the data
and the past session directories were read, not changed. The laptop, cachix and every git repo
were not touched; nothing is committed; the clean-room guard (tools/clean-room/guard.py) was not
run; no closed source was read. The only firmware reading used is the
lead's `closing3/events/readings/` (our own disassembly, facts only: the exit's five words, the
fast paths, the tick handler's EVENT_TIMER store). Frozen: `FROZEN.sha256` (every generator, scorer,
runner, script, table, blob, source, prediction, the tool programs and what they import from the
landed tree), `PREDICTIONS.sha256` (11 files), `LAPTOP-k0.sha256` and `LAPTOP-kev.sha256` (the files
as laid out on the laptop under `~/r3k0` and `~/r3kev`).

Checks that pass (the dated run is at the end): `tests/run_all.sh` = `run/guard_r3.sh`,
`run/freeze_r3.sh verify`, `tests/sim_r3.py`, `tests/test_scorer.py`, `tests/test_guard.py`,
`tests/run_mock.py`. Every new blob also builds and verifies through the landed CLI path
(`fwtask.build_blob_text`, `verify_blob`, run inside the guard and the sim test). `alias2.blob` and
`ring_hold.blob` are L3's frozen bytes (`c41bd078...`, `fa0f79db...`).

## 0. Preconditions the lead checks (not automated, all in the order they happen)

- The new module is installed and the laptop rebooted into `linux-resgx545`; `stage_r3.sh` then
  checks srcversion loaded = installed = **230E0EF50FFFD606C53AE3C** (any other, including
  `B21FDA82...`: refused) and that `kicker`, `kick_no_bump`, `kregnow`, `hold_recovery`,
  `render_rgn_arrays`, `render_pb_pages` exist. The installed file's sha256 (`06bf58db...`) is
  recorded, not a condition (the file may be compressed on the laptop): compare by hand.
- `~/sgxfive-test-s1b` (health, loop fills, e3b's fill; sha256 `46a2d063...` in `TOOL.sha256`) and
  `~/sgxfive-test-r1` (K0's k0t only; sha256 `bf4f8be2...` in `TOOLR1.sha256`, L1's and L2's pin).
- `/lib/firmware/sgx545_ukernel.fw` digest = `6a00268e...` (the cut `cont4` is tied to): checked in the
  runner's preflight for `ring_exit` (exit 1 otherwise) and again from the kernel's own arm line
  (`exit 0x... (0: unknown)`: a zero index stops the stage at the first arm, exit 4, before any job).
- K0 first. K1's first gate is K0's `k0h` kept `stage.json`; a failed K0 closes it.

## 1. What runs

| stage | blob | jobs (min / expected / max) | what | reset + arm |
|---|---|---|---|---|
| k0f | none | 1 | F0: reset, 15 files exist, 4 knobs at their defaults, `kicker` in the kernel's format with W = ccbctl[0], `kregnow` lists 6 rows and neither clear register | once |
| k0t | none | 2 | GD (dd-p1: L1's g-dd job, 64x64, made vertices) and PX (t-ctl-green-16x16, L2's q-t control) through `~/sgxfive-test-r1` with the arguments L1 and L2 used | each job (reset) |
| k0c | alias2 | 2 | C0 (reader: E791's A0), C1 (= A7: sa65 | 1<<23, kept 3 of 3 in L3) | stage start |
| k0h | ring_hold | 3 | H0 (idle), H1 (one signature pair inside the 90.5 ms hold), G0 (ring, one miscinfo: K = 2, 3) | each job |
| f | ring_exit | 4 / 8 / 9 | E0; FC4 x2 (cont4 control, FIRST); FB x2 (run only if FC4 kept); FCF x2, FPH x2 (only if FB kept) | stage start, after a stop |
| t | ring_timer | 3 / 4 / 5 | E0; T1 x2 (str, then the closed task); T2 x2 (str, then our own end; only if T1 kept) | stage start, after a stop |
| kb | ring_hold | 12 | Q0 x3, Q1 x3, Q2 x3, Q3 x3 | each job |
| e2b | pa_write2 | 15 | R x3, S, C4 x3, C5 x3, C6 x3, Z67, Z68 | stage start |
| e3h | none | 3 | 3 rounds of the 5 steps, CLEAR2 by `kregnow` | each job |
| e3a | strclr | 3 | the same 3 rounds, CLEAR2 by `str #69` | each job |
| e3b | ring_skip3 | 4 / 4 / 5 | B0 x3 (hold_recovery N), B1 once (Y, skip once), B2 (str #77, only if B1 kept) | each job |

Jobs: K0 8. K1 minimum 4 + 3 + 12 + 15 + 3 + 3 + 4 = 44, expected (H-BOTH, H-NOTIMER, H-STOP3) 8 + 4 + 12 + 15
+ 3 + 3 + 4 = 49, maximum 9 + 5 + 12 + 15 + 3 + 3 + 5 = 52; with K0 the session set is 52 to 60
jobs. Rows, parameters and frozen predictions are in `TABLES.md` and `predictions/*.tsv`; the
single source is `gen/r3layout.py` (`ROW_SPEC` and the constants), checked by the generator, the
runner, the guard and the scorer against each other.

### Stage f (the decisions of L3 folded in)

L3 showed X1 (a tick pass handed to the closed slot 2) keeps the tick and B3 (own end on a kick
pass) stops it, and D2 (bit 8) reproduced E537's assert marks: H-EXIT is supported. The exit of the
closed tasks is cfi.global, idf, wdf, phas ... end, nop.end (R-1; the verifier now accepts exactly
those two words). Each row is a plain tick pass, COUNT 1:

| row | the pass ends with | H-BOTH | H-CFI | H-PHAS | H-ANY | H-PLACE | H-BEFORE |
|---|---|---|---|---|---|---|---|
| FC4 (control, first, x2) | the real exit by `cont4` (tail call to 0x1974) | keep | keep | keep | keep | keep | STOP |
| FB (x2) | cfi, idf, wdf, phas, nop.end in our page (the exact replica) | keep | keep | keep | keep | STOP | not run |
| FCF (x2) | cfi, idf, wdf, nop.end | STOP | keep | STOP | keep | not run | not run |
| FPH (x2) | idf, wdf, phas, nop.end | STOP | STOP | keep | keep | not run | not run |

Gates (`run_if`): FB only if FC4 kept (else the replicas say nothing), FCF and FPH only if FB kept
(a stopping replica makes the singles uninformative). A stopped row is never replicated; the
second stop ends the stage (cap 2). Worst cases: H-BOTH (FCF, FPH stop: exit 8 after the second);
H-CFI or H-PHAS (1 stop); H-ANY (0). Each stop adds P3, the reset, the gate and a re-arm (about 35 s).

### Stage t (R3-K10)

The closed tick handler stores `0x01000000 | HostCtl dword 6` (= 0x01061a80) to CR_EVENT_TIMER and
`mov pa2` (E155; the instruction run in `ukernel.dis`). T1: `str #691` of that word, then the closed
task as ever (control: the write is harmless, next gap 25000 +- 50, flag 4). T2: the same str, then our
own end (idf, wdf, nop.end: E793's shape): H-TIMER keeps the tick, H-NOTIMER stops it. T2 runs only if
T1 kept. Budget 1 stop (the second ends the stage).

### Stage kb (Q290, R3-K5)

`reset + arm ring_hold` per job (K = 2 after the arm, E768), window 2, then (a) Q0 nothing, (b) Q1
`kicker =0x42`, (c) Q2 Q1 then one `miscinfo`, (d) Q3 `kick_no_bump` then one `miscinfo`. Frozen K of the
ticks after the action: H-KW (the word read at each event) 0x42 / 0x43 / 2; H-LATCH (the word as it was at
the last kick) 2 / 0x43 / 2; H-HWC (the count of EVENT_KICK writes) 2 / 3 / 3 (Q1 / Q2 / Q3). Controls in
every world (rows labelled control): the file reads what was written, `ccbctl[0]` 2 after Q1, 3 after Q2
and Q3, the `kicks` counter +1 for a kick and 0 for none, `kick_no_bump` read N after Q3, every miscinfo
answered. Slot 0's ring has 16 rungs: the job is 1 + 5 + 5 ms, about 12 entries (a ring full before the
interval is cannot tell). Budget 0 (a tick stop ends the stage). No bare kick exists anywhere: the only
kick is `miscinfo`, which the kernel sends with its command.

### Stage e2b (Q098, R3-K3), E3 rows (Q166, Q111; R3-K1, R3-K2), K0

As the design (`exp-kernel-r3.md` 2.1) with the rows named in section 1. e2b: markers `0x5a67...` per
row (never the old words), pa0 and pa1 never written (the verifier refuses them too), Z rows put sa67 and
sa68 back to E748's words. E3a/E3h: the loop `loop-b16-i56` (our own source, E431/E769) through the pinned
tool latches STATUS2 bit 6; step 3 writes bit 15 (a zero bit), step 4 bit 6. E3b: the fill's end-of-render
event is slot 3, pa0 0, pa1[23:0] 0x10 (E747); B1 skips its first such pass once (flag 3, nop.end),
STATUS and STATUS2 are read as fast as the debugfs reads for 50 ms, the tick is checked (a stop is signed
FIRST), then CLEAR (0x0134) by the host with bit 15, then bit 18, and after a stop bit 29 (TIMER), each read
1 and 3 ms later, then P3 (one miscinfo) and the reset; hold_recovery is Y for the whole of B1 and B2 and
read back N before the tool is collected.

## 2. The runner (copy of L3's `r3_run.py`; what is new)

- Preflight: srcversion loaded = installed = 230E0EF5...; the files of `NEED_FILES`; the pinned tools;
  every frozen file (hash by hash from `LAPTOP.sha256`); the whole table against `ROW_SPEC` (names and
  order, words, counts, acts, kicker word, CLEAR values, hold_recovery per row; any value outside: exit 7);
  the blob's `str` set, pa/sa write sets (`blobs.json`) and the cont4 digest rule; the previous stage's
  kept `stage.json` (K0's `k0h` for `f`, found in `~/r3k0-out`).
- Op families (mixins in `run/ops_*.py`): `alias2`, `holdsig`, `act` (core), `kicker`, `pawrite`,
  `clear_host`, `clear_fw`, `skip3`, `defaults`, `tooljob`. Debugfs writes, by name: own_code, own_arm,
  load, boot, reset, `kicker` (only `=0x42`), `kick_no_bump` (Y), `hold_recovery` (Y / N through `knob`,
  read back), `kregnow` (only `0x0114=` with bits 15 or 6 and `0x0134=` with bits 15, 18, 29). Never a
  BIF register, an enable, CLKGATECTL2, kreg or kpoke.
- Stops as L3: the signature twice 30 ms apart with HostCtl dword 14 and the CCB offsets BEFORE the reset
  (in e3b before the writes), P3 (one miscinfo; in e3b after the writes), the landed dumps, then reset +
  gate + health (`end()`), recorded. Every op calls `check_tick` at its end, so any stop is signed first.
  A stopped row is not replicated (e3b's B1 replicates: its budget is the stage's). Budgets (stops the
  stage takes and goes on; the next ends it, exit 8): f 1, t 1, kb 0, e2b 0, e3h 0, e3a 0, e3b 2 (3 stops),
  K0 0. A freeze (exit 6) or a watchdog line (exit 3) stops all laptop work.
- Tool messages are searched in the WHOLE output (`captured`), health after each stop and stage, gates
  from kept output, `kernel.log` of every stage checked (e3b expects hung / recovery lines: only BIF-fault
  and page-fault lines stop it).

## 3. Controls that can fail, void and cannot-tell states

Controls (rows labelled control or fit): k0f's eleven (files, srcversion, defaults, kicker format, W =
ccbctl[0], kregnow rows) and, where the kernel's own format is not known, one held-out [infer] row
(`kicks` = ccbctl[0]); k0t: rc, class, the picture lines (sha256 of the `o0` line and the 64 rows),
STATUS2 0x400 before and after (the L1 and L2 outputs, kept); the render buffers' sha256 are held-out
[infer] rows (they may depend on addresses); k0c: C0 (E791's A0) and C1 (L3's kept); k0h: H0 idle, H1's hold
band and a running task's signature (L3: 3 of 3), G0 (K 2 then 3, one kick entry, answered, grid); f: E0 (14 +-
2 entries on the grid, nothing acted) and FC4 (the control, which can fail and then ends the replicas);
t: E0 and T1; kb: Q0 and the file/ccbctl/kicks/answered rows of every row; e2b: R (E748's ten words and the
next pass) and S, Z67, Z68 (E748's writes); e3h / e3a: steps 1 and 2 (latch set, holds), STATUS2 0x400
after the reset, bit 10 throughout, and for e3a that the task took the commands; e3b: B0 (the fill without the
skip: completes, one entry, tick alive, SKIPPED 0). **A failed control of a K0 stage makes the scorer exit 9
and the driver stop (K0 failing stops everything)**; in K1 a failed control is FAILED in the SUMMARY and the
tally keeps fit, held-out, replicate and control rows apart.
Cannot tell: a signature outside the hold, the acted KIND never came, the ring full before the interval, no tick
after a write (kb), step 1 not 0x440 (the held-out steps of that round), bit 18 not held (the CLEAR readings of
that job), no bit-29 read. Void: no record, a stale record (another run's stage.json), a class that is not a
result, a corrupt flag, no page or a changed ring after the close, ACTED not the design's, a kicker write that
was refused, a task that did not answer. Void and cannot-tell rows never count as a pass.

## 4. Time

Pure job time under 5 minutes. About 3 s a reset-and-arm job; each stop adds P3, the reset, the gate, a re-arm
(about 35 s); each stage end: reset, gate, health, copy, score (about 40 s). K0: about 6 minutes wall (4 stages).
K1: f 2 to 3, t 2, kb 1.5, e2b 1, e3h 1.5, e3a 1.5, e3b 4 minutes: about 15 minutes with the expected stops
(f 2, t 1, e3b 1), 20 with every stop budgeted. The mock sessions (real sleeps, no hardware) take about 1 minute
for K0 and 1 to 2 for K1.

## 5. Stop budget and risks

| stage | stops expected | cap | risk |
|---|---|---|---|
| k0f, k0t, k0c, k0h | 0 | the first ends everything | none beyond L1, L2 and L3's own (their rows repeated) |
| f | H-BOTH 2, H-CFI / H-PHAS 1, H-ANY 0 | 2 | medium: the first runs of our own cfi and phas words and of a tail call into the exit (`cont4`); a stop is recovered by the debugfs reset (E793 2 of 2, L3 3 of 3) |
| t | 1 (T2) | 2 | medium: a `str` to the EDM timer by a task of ours; reset recovers |
| kb | 0 | 1 | low |
| e2b | 0 | 1 | low; C6 medium (sa66 is rewritten by PDS #13 each event) and last of the three; a stop ends the stage before Z67 and Z68 (sa67 and sa68 may then hold a marker until the next boot: the end reset is exact, E536 saw sa registers survive a reset) |
| e3h, e3a | 0 | 1 | low (a latch the firmware ignores, bits 6 and 15 only) |
| e3b | 1 (B1 under H-STOP3) | cap 3 (not a licence to repeat) | medium: the only stage that skips a closed handler; hold_recovery Y with a stuck fill; the tool is collected only after the knob is back to N; the reset is the recovery |

Risks that cannot be proved offline: (1) the kernel's overlay of `cont4` and of the two tail triples in
entry 0 (the landed `fwtask.apply_patches` is the model; the arm line's exit index is checked at the first arm);
(2) what the fill does while an end-of-render event is skipped (the fake tool and the mock invent it; the
runner bounds the tool with a 6 s timeout, kills it and resets); (3) slot 0's ring (16 rungs) holds the kb
interval only if the kicker and kick calls are quick; (4) `sgx-sim` does not model a pa write (it reads
the old value back) nor the new `str` registers: the sim tests prove encodings, control flow, patching and
the stores (including that every acted pass makes exactly one `str #691` with the pinned word), not any
hardware result; (5) the loop fills of e3 depend on E431/E769 (56 iterations latch STATUS2 bit 6: step 1 is the
control of every round); (6) K0's pinned `~/sgxfive-test-r1` must run unchanged on the new module (that is
what k0t tests).
Laptop limits held: no clock-gate register write, no kreg, no trc_hazard, no reboot, GRUB or build, debugfs via
`sudo -n`, kmsg via `os.open(O_WRONLY | O_APPEND)`; firmware `str` only to 0x0114, 0x0134, 0x0acc and each only in
its own blob (the guard decodes it from the word); the BIF registers are never written.

## 6. DEVIATION entries (from the design or the decisions as written)

1. **EVENT_TIMER word.** The brief says pin the stored word to pa2 = 0x01061a70 (E746). The closed
   tick handler stores `0x01000000 | HostCtl dword 6` = **0x01061a80** (the reload word, instructions
   505-509 of the readings' listing: `or`, `str #691`, `mov pa2`), and pa2 reads 0x01061a70 sixteen
   units later. `ring_timer` stores 0x01061a80 (the handler's own word; the guard pins the `mov r12`
   before each `str` to it). One constant (`r3layout.TIMER_STR_WORD`) changes it.
2. **Stage f gating.** The brief lists four rows; here FB runs only if FC4 kept and FCF/FPH only if FB kept
   (a stop of the control or of the exact replica makes the later rows uninformative and would spend the
   2-stop cap for nothing). If the lead wants every row to run anyway, remove the `run_if` of FB, FCF, FPH in
   `ROW_SPEC["f"]`.
3. **Stage t's two rows** (T1, T2) are my reading of R3-K10 (the exp-kernel text names only the str row and the
   word); the decision text fixes "after the stage f rows" and "K1 after A7/A8", nothing more.
4. **e3b P3 order.** The writes (bit 15, 18, 29) are made AFTER the signature and BEFORE P3 (P3 sends a
   miscinfo into the stopped EDM, which would change what the clears act on); the reset is still last.
5. **e3b replicates (FIXED by the lead, R3-E2 a).** B1 runs once; if it stops: signature, host writes, P3, reset, next row. A stopped row is never replicated; the 3-stop budget is a cap. B2 runs only if B1 kept the tick. Changed: `ROW_SPEC["e3b"]` B1 reps 3 -> 1 (jobs b1-r2, b1-r3 gone, 7 -> 5 jobs), `rep_after_stop` removed from B1, B2's `run_if` all_kept:B1:3 -> all_kept:B1:1; predictions/e3b.tsv lost exactly the b1-r2 and b1-r3 rows; tables/e3b.json, TABLES.md, the e3b tests follow. No other prediction file changed.
6. **Stage order.** f, t, kb, e2b, e3h, e3a, e3b (the brief fixes f then t, host then firmware for E3, e3b
   last); kb and e2b sit between because they are the low-risk rows.
7. **k0t's two render-buffer hashes** are held-out [infer] rows, not controls (they may include addresses);
   the controls are rc, class, the picture lines, STATUS2.
8. **L3's stage-h "D0 one modal value" control is dropped** (it failed in L3); H1's hold band and signature
   are the controls.
9. **kb timing**: 1 + 5 + 5 ms instead of the design's 20 ms of ticks (slot 0's ring holds 16 entries).
10. **Gate across sessions**: f's runner looks for `~/r3k0-out/k0h/stage.json` (the other session's
    directory); the driver gates on `out/k0h`.
11. **cont4 is checked twice** (firmware digest at preflight, the kernel's exit index at the first arm): not in
    the design.

## 7. Dated run (2026-11-10, Mac, offline)

`tests/run_all.sh` after the freeze: RUN_ALL PASSED (about 4 minutes), then `run/freeze_r3.sh freeze` and
`verify`: files verified. resgx545 main `tools/fwtask` and `tools/usse-asm` are unchanged since `7aaa017`
(`git diff 7aaa017 HEAD` empty), so the frozen landed hashes are those of the landed tree.

| check | result |
|---|---|
| `run/guard_r3.sh` | clean (7 blobs, 11 tables, scripts, runner and op modules) |
| `run/freeze_r3.sh verify` | files verified (77 frozen files, 11 prediction files) |
| `tests/sim_r3.py` | 136 checks, 0 failed (alias2's commands as L3; ring_exit ACT 3 to 6, flags 3 and 4, ACT_SEEN, only the wanted pass, window 2 only; ring_timer: one `str #691` of 0x01061a80 per acted pass, flag 4 / 3; pa_write2: cmd 1, 9, 2, 3, 4, 5, 6 and the p flags; strclr; ring_skip3's skip-once and slot 0 command) |
| `tests/test_scorer.py` | 91 checks, 0 failed (E537 and L3's D2 and B3 dumps; a world each for H-BOTH, H-CFI, H-PHAS, H-ANY, H-PLACE, H-BEFORE, H-TIMER, H-NOTIMER, H-TIMERW-STOPS, H-KW, H-LATCH, H-HWC, H-D, H-B, H-P, H-W, H-ALL, H-NONE, H-STOP3, H-FREE3, H-LEVEL, H-PULSE, each winning in its own and losing in the others; void, cannot-tell, stale, gates; k0f and k0t on L1's kept dd-p1 output) |
| `tests/test_guard.py` | 79 checks, 0 failed (every limit broken in a copy of a source or a table) |
| `tests/run_mock.py` | 12 tests, 133 checks, 0 failed (K0 default and a failed control per file; K1 default session through f exit 8, t, kb, e2b, e3h, e3a, e3b exit 8; every f and t world; kb, e2b, e3 and e3b worlds; preflight refusals; fatal, arm, tool-message, gate-fail and exception paths; the debugfs write trace) |

Freeze hashes (sha256 of the files, first 16 hex): `FROZEN.sha256` b59727a474a68223, `PREDICTIONS.sha256`
9241faca510ef02a, `LAPTOP-k0.sha256` 8eaf535723e0accb, `LAPTOP-kev.sha256` cbfb7e96f9b626e2. Blobs: alias2
`c41bd078...` (L3's), ring_hold `fa0f79db...` (S2b's), ring_exit `3c031d99...`, ring_timer `8f1536f1...`,
pa_write2 `0374a24e...`, strclr `7259a198...`, ring_skip3 `d0671a5f...`.
