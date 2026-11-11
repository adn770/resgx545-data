# R4-events: laptop session r4-events of round 4 (stages kb2, kp, e3p)

Prepared 2026-11-11, NOT run. Nothing here touched the laptop, cachix or a git repo; nothing is
committed; the clean-room guard (tools/clean-room/guard.py) was not run; no closed source was
read. Read `PREFLIGHT.md` first.

Plan: `closing4/events/exp-events-r4.md` section 4, with the decisions taken as recommended (Q4 yes
x2 last in kb2; no `sa65` single-bit rows (split to Q294); no firmware `str` row at all (R4-7: only
0x0814 and 0x0a78 are allowed and none is needed)). The notes the plan wanted before the freeze (0a
to 0e) are read where they landed (E818 and E819 Correction sections, hw_spec 12.2 in the
integration tree, resgx545 5a13042) and the predictions start from them.

## What runs (one session, laptop prefix `~/r4e-`)

| stage | blob | jobs | what | stops |
|---|---|---|---|---|
| kb2 | `ring_hold` (S2b's bytes) | 10: G0P x2, Q2P x3, Q3P x3, Q4 x2 | Q290 with the ring over the kick: the writes (`kicker =0x42`, `kick_no_bump`) BEFORE the window opens, one `miscinfo` 1 ms after it; Q4 = Q3P, then a second window and one ordinary `miscinfo` (last) | 0 predicted, any tick stop ends the stage |
| kp | `ring_exit2` (new) | 4: E0, FK, KP x2 | Q152: a kick pass ended `idf, wdf, phas end, nop.end` (KP: one `miscinfo` into the pass); E0 and FK are the controls (one arm); each KP resets and arms | 0 or 1 (only KP may stop; budget 1; a stop of E0 or FK ends the stage) |
| e3p | `ring_skip3p` (new) | 4: B0, B1P x3 | Q166, Q111: the slot 3 end-of-render pass skipped once and ended with the phase end, `hold_recovery` Y in B1P, the host's CLEAR (`kregnow 0x0134`: bit 15, then bit 18), the watch from the slot 3 entry; each B1P ends with reset, gate, health. LAST | 0 predicted; its first stop ends the stage; 3 held jobs by design |

**18 jobs** (the plan's 16 to 18), **0 tick stops predicted, budget 2 in all** (kp 1, e3p 0 after
its first stop, which ends the stage), 3 held jobs (B1P). Order kb2, kp, e3p, each gated on the
previous stage's kept `stage.json` (exit 0, or 8 after the lead chose `--from`). If only one stage
can run: kb2.

Time: pure job time about 4 minutes (a reset and arm about 3 s a job; each unanswered `miscinfo`
0.5 s; each B1P about 25 s with its recovery); with the load step, three stage ends (reset, gate,
health, copy, score about 40 s each) and the staging: **about 12 minutes wall**, up to 20 with a
stop (each stop adds P3, the reset, the gate: about 35 s).

## Reboot

**No reboot is needed** if the laptop is in the state the handover left it (module 99CD90DA,
installed = loaded, the previous session finished with its health exact and its knobs restored).
The driver's load step (a health fill and triangle through `~/sgxfive-test-s1b`) loads the firmware
and prints the four knobs; every stage's preflight refuses unless srcversion loaded = installed =
99CD90DA26E3AFF9C450517, the debugfs files exist, the knobs read `hold_recovery N`,
`render_rgn_arrays 0x00000000`, `render_pb_pages 0x00000422`, `kick_no_bump N`, and the firmware is
running; each kb2 job and each KP and B1P job starts with a debugfs reset and an arm, the kicker
word at its boot value (K = 2 after the arm: E768). The lead asks the user for a reboot only after
a freeze, a watchdog line, a stage that ended with exit 5 or 6 (reset or gate not exact), or if
another session of this round left a knob or a context unrestored (the preflight says so).

## Run (the lead)

```
cd ~/src/scratch/resgx545/closing4/r4-events
export PYTHONDONTWRITEBYTECODE=1
export SGX_TARGET_HOST=jtorra@192.168.12.234        # direct cable: jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
export PY=../../closing/pixel-faults/.venv/bin/python PYTHON=$PY
export RESGX545=$HOME/src/scratch/resgx545/closing4/lead/wt   # the default (tree at 5a13042)
run/guard_r4e.sh && run/freeze_r4e.sh verify
SGX_DRY_RUN=1 run/r4e.sh ATTEMPT                    # prints the commands
run/stage_r4e.sh                                    # copy and check on the laptop (~/r4e-run)
run/r4e.sh ATTEMPT                                  # the session; stops at the first problem
run/r4e.sh ATTEMPT --from kp                    # resume after a stage a stop rule ended (8)
```

Results: `out/ATTEMPT/score-STAGE.txt` (one `SUMMARY:` line each; `out/ATTEMPT/STAGE/` has the kept
files, the stop dumps, the signature, marks and P3 inside the job records); on the laptop
`~/r4e-out/ATTEMPT/STAGE`. An attempt directory is never overwritten on either side.

## What is frozen, and what each stage predicts

`PREDICTIONS.sha256` (`predictions/*.tsv`, `case quantity value model set`; sets control, fit,
heldout, replicate), `FROZEN.sha256` (every generator, scorer, runner, script, table, blob, source,
prediction, test and the landed files of the tree by absolute path), `FROZEN.commits` (those pins
to resgx545 `5a13042`), `LAPTOP.sha256` (the files as laid out under `~/r4e-run`), `TOOL.sha256`.

- **kb2** (rows in `predictions/kb2.tsv`). Controls: G0P (one ordinary kick: one kick entry, K 2,
  the ticks before 2 and after 3, `pa2` 0x01061a70, answered, file `kicker 3 ccbctl 3 3 kicks 3`,
  at least 3 ticks after the kick entry: the timing control), and in every job the tick alive,
  `kick_no_bump` N. Q2P (W = 0x42): all readings: 1 kick entry, K 2, ticks before 2, answered, file
  `kicker 67 ccbctl 3 3 kicks 3`; ticks after: H-LATCH 67, H-CNT and H-HWC 3. Q3P and Q4
  (`kick_no_bump`): [fit, E819] not answered, file `kicker 2 ccbctl 3 2 kicks 3`; kick entries
  H-PEND 0, H-NOEVENT 0, H-LATE 1; ticks after K H-LATCH 2, H-CNT 2, H-HWC 3; `pa2` of the ticks
  after H-PEND 0x...74, H-NOEVENT 0x...70; `USE0_SERV_EVENT` bit 16 after the timeout (x2) H-PEND
  clear, H-NOEVENT set; Q4: second window kick entries H-PEND 2, H-NOEVENT 1, ccbctl `4 4` against
  `4 3`. "After the kick" is the kick entry (G0P, Q2P); in the `kick_no_bump` rows (a kick entry
  may not come) the call's start stamp + 8.0 ms, and "before" the stamp + 5.0 ms (the write comes
  6.7 ms after the stamp in E816).
  **Predicted (starting from the notes 0a and 0b) [infer]:** G0P holds; Q3P not answered, no kick
  entry, K stays 2 (H-HWC out), the ticks after the write read `...74` and bit 16 reads clear
  (H-PEND), Q4 two entries and `4 4`; Q2P's K after is the one open row (H-LATCH 67 against H-CNT
  3: the notes cannot separate them).
- **kp**. Controls E0 (12 to 16 entries on the grid) and FK (kept, flag 3, next entry +24994 or
  +24995 then the grid, read = write, dword 14 0). KP: H-PHAS-ANY (the tick is kept: at least 4
  ticks on the grid after the kick entry, signature idle, not answered, read = write - 1, dword 14
  0) against H-KICK-MORE (a stop: nothing after the kick entry, busy, P3 not answered). **Predicted
  [infer]:** H-PHAS-ANY (P2: the phase end is the program-shape rule; E813 B3's stop had none).
- **e3p**. Control B0 (E823 B0: the fill completes, one slot 3 end-of-render entry, bit 18 never
  read, tick alive). B1P: tick alive (H-PHAS-ANY) against stop (H-SLOT3-MORE); the fill held
  (both); bit 18 set in every watch read (H-LEVEL) against never (H-PULSE); after the host's CLEAR
  bit 15 still set, after bit 18 clear at 1, 3 and 20 ms (H-W; H-ALL clears at bit 15; H-NONE
  never). The first B1P is the fit for the clears (E823, 1 job), the replicates test them.
  **Predicted [infer]:** H-PHAS-ANY, H-LEVEL, H-W.

A row is held, FAILED or cannot tell (scorekit); a control that is not a pass makes every other row
of its job cannot tell, and G0P's (kb2), E0 and FK's (kp) and B0's (e3p) make the other rows of the
stage cannot tell. A family verdict (consistent, REFUTED, mixed, cannot tell) is printed per
hypothesis in the `SUMMARY:` line. Cannot tell: fewer than 3 ticks after the kick (kb2), the ring
full before the kick entry (kp), a watch of fewer than 5 reads or no slot 3 entry in the page
(e3p).

## Layout

- `asm/*.s`, `bins/*.blob`, `bins/blobs.json`: `ring_hold` (S2b's, byte for byte), `ring_exit2`,
  `ring_skip3p` (generated by `gen/r4blobs.py`, verified by the landed `tools/fwtask`, which also
  lints them: both end with `own_end`, the lint is clean; no row of this session ends otherwise)
- `tables/STAGE.json`, `TABLES.md`, `predictions/STAGE.tsv`, `stages.txt`: generated by
  `gen/gen_r4.py`
- `gen/r3layout.py` (R3k's, byte for byte), `gen/r4layout.py` (the one source: module, stages,
  rows, constants), `gen/r3blobs.py` (R3k's), `gen/r4blobs.py`, `gen/gen_r4.py`,
  `gen/laptop_files.py`
- `run/r4e_run.py` (laptop runner), `run/ops_kicker2.py` (kb2), `run/ops_e3p.py` (e3p),
  `run/r3common.py`, `run/health_remote.sh`, `run/r4e.sh` (Mac driver), `run/stage_r4e.sh`,
  `run/freeze_r4e.sh`, `run/guard_r4e.sh`, `run/guard_blobs.py`, `run/guard_py.py`,
  `run/guard_names.py`
- `score/score_r4e.py` (STAGE OUTDIR | gate STAGE ROOT | sig FILE), `sc_kb2.py`, `sc_kp.py`,
  `sc_e3p.py`, `r4common.py` (row engine, family verdicts), `scorelib.py` (R3k's readers with
  `r4layout`), `scorekit.py` (resgx545 5a13042 `tools/closing/scorekit.py`, byte for byte)
- `tests/`: `run_all.sh`, `test_gen_r4.py`, `sim_r4.py`, `test_scorer.py` (+ `fixtures/real/`: kept
  records of E813, E816, E817, E819, E823), `run_mock.py` (+ `mockfw/`, `shims/`, `fake_tool.py`)

Python: `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python` (the laptop needs only its
python3, 3.8 or later). Always `export PYTHONDONTWRITEBYTECODE=1`.

## Tests (all offline)

```
tests/run_all.sh              # guard, freeze verify, generator, sim, scorer, mock (about 6 minutes)
tests/run_all.sh --prefreeze  # before the freeze (the freeze check is the one allowed failure)
```

## Deviations from the plan (each for a reason the build found)

1. **KP writes KIND, ACT and COUNT before the window opens, `pre_ms` 0, and takes no stamp before
   the call.** The plan wants at least 4 ticks after the kick entry in the 16-rung ring; E817's
   `t_count_ms` shows the window open, a 3 ms sleep and the two page writes cost 10 ms, and the
   call's own write comes later. The task acts in window 2 only, so arming it first is safe. E0 and
   FK keep E817's order (`pre_ms` 3).
2. **Each KP job starts with a reset and an arm** (E0 and FK share the stage's one arm, as E830):
   the unread command KP leaves (read = write - 1) goes with the reset; the plan was silent.
3. **FK's next gap**: the gate window is 24950 to 25050 (control); the exact "24994 or 24995" of
   the plan is a fit row of FK (one unit of rounding must not shut the gate on KP).
4. **Stop budgets**: kb2 0, kp 1 (KP), e3p 0 (its first stop ends the stage: the plan's "ends at
   its first stop"); 2 in all as the plan. B1P no longer writes bit 29 and never CLEAR2: only CLEAR
   (`0x0134`) bits 15 and 18 are ever written (`kregnow`, by the host).
5. **Tool**: the plan pins `~/sgxfive-test-s1b` (E817, E823, E830 ran with it; the health fill and
   triangle and e3p's fill); the brief names `~/sgxfive-test-rgn4`. The session uses s1b (hash in
   `TOOL.sha256`); a one-line change of `TOOL.sha256`, `stage_r4e.sh`, `r4e.sh` and a refreeze
   moves it.
6. **G0P's timing control stops the stage in the runner** (exit 8 after the first G0P job without
   one kick entry and 3 ticks after it), not only in the scorer.
7. **Q4's first part is Q3P again**: its Q3P discriminating rows are scored as replicates (5
   Q3-shaped jobs), its `pa2` and bit 16 readings included.
8. **FROZEN.commits is written by `run/freeze_r4e.sh`**, not by `tools/records/frozen.py`: the
   integration tree sits under `scratch/resgx545/`, whose first `resgx545` path component the
   finder takes for the tree's root. Every pin is `git show
   5a13042a36972b37ae1e4c2338e0b7d0acd4da2c:<path>` checked; `usse-asm` is `untracked` (a build
   product). After the tree is merged the lead may re-pin by path with `frozen.py`.
