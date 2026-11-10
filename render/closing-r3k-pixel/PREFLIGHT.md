# R3K-pixel preflight: jobs, time, controls, fault budget, risks, deviations

Prepared 2026-11-10 from `closing3/kernel/exp-kernel-r3.md` (K-pixel rows), `series-r3.md`
(what was built; fork `resgx545` at 8fc748b0, read only) and decisions R3-K4, R3-K6, R3-K7.
Nothing ran on the laptop.  Frozen: `FROZEN.sha256` (generators, scorers, runner scripts, env,
tables, predictions, staged program, the data the generator reads, the tool pins and the landed
tool source), `PREDICTIONS.sha256`.  Refreeze (`run/freeze_k.sh freeze`) only after regenerating,
and never after the first job.  Tests: `tests/run_all.sh` = PASS (test_gen 33, test_scorers_k 49,
mock_all 23, run_mock 130, guard clean); scorer tests were written before the scorer and seen
failing first, the mock suite failed on the missing pieces before they existed.

## 1. Jobs, time, fault budget

| stage | jobs | what | expected fault-class events |
|---|---|---|---|
| k-f4 | 11 | c3, c2, h1-h8 (plain), c1 (held, last) | 1 (c1); an h row that faults is a refutation |
| k-pb0 | 3 | dump run (TE 0x40), p0 (TE 0x60 twin), p1 (TE 0x40) | 0 |
| k-pb | 5 | p2, p3a, p3b, p4a, p4b (pokes into the parameter buffer) | 0 (a hang = stop) |
| k-bif | 5 | n0 (idle), f1, f1r, f2, f3 (held, f3 last) | 4 |

Time (per-job figures of r2-pixel and S3: reset 3 s before every job, a plain tri 0.2 s plus 3 s
to keep a dump, a held job 2.8 s + gap + reset + health about 25 s, a bif row adds its writes and
the 2.5 s watch; per stage ssh, preflight, copy, score, health 30 s): k-f4 about 3 minutes,
k-pb0 1, k-pb 1.5, k-bif 3, staging 1: **about 10 minutes**; plan 20 (health retries after 4x
faults).  The design budgeted 35 for K-pixel.

Fault budget: the limit is **5 fault-class events per stage** (r2-pixel's limit, now counted per
stage: the driver passes `K_FAULTS_PRIOR=0`).  Expected in the whole session: 5 (c1 and the four
held BIF rows), never more than 4 in one stage.  Hypothesis groups bound what is measured: `h4:2`
(two faulting h rows end the h rows), `c1:1`, `bif:4`.  A fault in a row without a group, any hang
and any unexplained failure stop the stage (rc 4) after a reset and a health check.  The runner's
health runs after every fault and every stage; the driver's after every stage.

## 2. Tool, module, pins

- Tool `~/sgxfive-test-r1` sha256 bf4f8be2... and `~/regtimeline` 079f6359... are the pins of
  `closing3/r3-pixel` (`TOOL.sha256`, `TOOLSRC.sha256` copied; the freeze compares the landed tool
  source with `TOOLSRC.sha256`).  A mismatch of either on the laptop: **stop and ask**, nothing is
  rebuilt.  No design row needs a new tool option: `--kpoke-render 2:par:INDEX=VALUE`,
  `-n 2 --geometry 1`, `--keep-overflow`, `--dump-render`, `tri --fault` all exist in the pinned
  build (`tests/mock_all.py`: 23 of 23 commands accepted by the landed tool's mock, the
  `targets up to WxH` echo and the `scratch at ... (N KiB)` line match, the par pokes are echoed
  as `kpoke before render 2`).  The mock does not render: it proves acceptance, not behaviour.
- Preflight (`lib_k.sh`): kernel and firmware printed; `modinfo -F srcversion` = loaded =
  **230E0EF50FFFD606C53AE3C** (`k.env`); the debugfs files `reset hold_recovery regs render_param
  render_tadata render_pb_pages alias_skip render_rgn_arrays kregnow kpoke kicker` exist;
  defaults: hold_recovery N, render_pb_pages 0x422, alias_skip 0, **render_rgn_arrays 1**; the
  `kregnow` file lists the `0x0c00` and `0x0c04` rows (the old module has none); tool and
  regtimeline hashes.  Any failure: rc 1, nothing touched (no knob write, no reset).
- Knob: `render_rgn_arrays` is a row knob (`rgn:1` or `rgn:4`): written after the job's reset,
  read back numerically (rc 19 if it does not read back 4), logged as `resgx545 r3k rgn NAME N`.
  A row without it runs at 1.  The runner's exit trap writes **1 back at every exit** (a stop,
  a freeze, a fatal message included; a bounded write) and prints it; the driver reads it after
  every stage and after a stop and stops with rc 42 if a stage leaves another value.

## 3. Controls: how each passes and fails

| row | passes | fails (what the scorer says) |
|---|---|---|
| c3 (knob 1, 64x64) | complete, diff 0 of 4096, TA data 0x6000, 4 arrays, nothing below rgn | FAIL; h rows cannot tell |
| c2 (knob 4, 64x64) | as c3, and TA data sha256 and target hash equal c3's | FAIL; h rows cannot tell |
| c1 (knob 1, 288x144, held) | held fault 0x90004 at page 0x20006 (E729) | FAIL if it completes ("the knob leaks"); h rows cannot tell |
| knob proof of each h row | TA data size = the four-array layout's (0x8000 ... 0x1e000) | the size of the knob-1 layout = "the knob did not apply": cannot tell, not a refutation |
| pb-d0 (dump run) | stream words 04000004 00030001 04000000 at dwords 0-2, dwords 11-26 = E728's own, diff 3969 of 4096, hash 0xfc5ff15e0434a325 | FAIL: par's index is not the dword index; gate closed |
| p0 (TE 0x60) | diff 0 of 4096, hash 0xd0530839d87ea325, 4096 triangle pixels, dwords 11-26 = the twin's | FAIL: the split flow is not the twin; gate closed |
| p1 (TE 0x40) | E728's empty image (as pb-d0) and a parameter buffer sha256 equal to the dump run's | FAIL; gate closed |
| p2 (own value) | the poke applied once (kernel log), image empty, dwords 0-26 unchanged, sha = dump run's when k-pb0 is kept | FAIL: p3/p4 cannot tell |
| n0 (idle) | four writes status 0, four log lines and six snapshots all INT_STAT 0x80000 / FAULT 0, BIF_CTRL restored | FAIL: Q003 cannot tell |
| each fault row | frozen fault word and page (f1/f1r 0x90008 at 0x3e000, f2 0x90004 at 0x20008, f3 0x90002 at 0x3e017); `0x0c04=0x1` changes nothing; BIF_CTRL back at its first value | cannot tell for the row |

Never a verdict (NODATA): no `cases.tsv` row, no output, rc 2/124/125-127/128+, a class that is not
a result, a fault latched before the job, a missing dump or snapshot, pokes the kernel log does
not show as applied, a kregnow write that returned non-zero (EBUSY) or fewer than four kernel
log lines.  The tool's and the kernel's messages are searched in the WHOLE output (a parameter-
buffer overflow message, tested with 12000 characters around it, makes an h row cannot tell).

## 4. Fit vs held out (tallied apart)

- Q140: the layout model (`klib.layout(w, h, f)`, the kernel's formula) fits 19 of 19 rows on
  record **post hoc** (`closing3/kernel/layout_f4.out`); the frozen predictions come from it, the
  eight h rows are the held-out part (h8 1024x768 is the largest 4x context ever run); c1-c3 are
  controls.  Refuted: any h row faulting, wrong pixels or a number of arrays other than 4.
- Q285: p0, p1, p2, the dump run are controls (frozen from E728 and the landed twin);
  **held out**: p3 (H-OLD: the twin's image; H-FIELD: not), p4 (H-FIELD: pixels drawn; H-OLD: none);
  p3b and p4b are replicates.
- Q003: n0 and the controls above; **held out**: f1, f2, f3 (H-W1C, H-CLR, H-RST frozen per
  row); f1r replicate.  E767's lead (the halt makes both registers read clear) is frozen as data
  for the reset's two new log lines.

## 5. Decision rules (frozen in `score_k.py`)

- Q140: all controls PASS and 8 of 8 h rows AGREE: "four arrays suffice at the 8 held-out
  sizes"; an h row REFUTED names its fault page; a failed control or a knob that did not apply is
  cannot tell for the h rows.  The health-triangle clause of Q140 is not closed here.
- Q285: needs p2 PASS and a consistent p3 and p4: twin + empty = H-OLD; not twin + drawn =
  H-FIELD; not twin + empty = cannot tell, park under Q030; twin + drawn = cannot tell, both.
- Q003: n0 PASS, then per row: after the write of the set bits (value = the fault word without
  bit 19) the state is cleared = H-W1C (and stays cleared); unchanged then cleared by the
  `0x0c00^=0x10` flip = H-CLR; unchanged throughout = H-RST; anything else = OTHER.  All rows the
  same = that hypothesis; rows disagreeing = MIXED with the rows named.  After the writes a 2.5 s
  watch (does the job complete, does the fault return) is reported, not scored.
- Gate: k-pb runs only if k-pb0's dump run, p0 and p1 passed.  A closed gate skips k-pb cleanly
  (message, `SKIPPED`), the session goes on with k-bif, exit 0, and the SUMMARY names the rerun.

## 6. Stops and recovery

Runner exit codes (`run_stage.sh` header): 1 preflight or frozen mismatch, 3 fatal kernel message,
4 unexpected hang/fault/failure, 5 failed health recovery, 6 a job did not return, 7 forbidden
knob or value, 8 missing program, 9/11 hold_recovery read-back, 10 a held fault still latched
after two resets (no further reset), 12 registers unreadable, 13 reset failed, 14 fault latched
before a job, 15 the 5th fault event of a stage, **18 no answer within 10 s after a BIF write
(E317's stall: nothing but the knob restore touches the machine, no reset)**, **19 the knob did
not read back**.  Driver: 20 frozen files changed, 30-36 health after a stage, 37 copy, 38 no
SUMMARY, 39 attempt directory exists, **42 render_rgn_arrays not 1 after a stage**.  After any stop
the driver prints the knobs it can read.  Recovery: no reboot, no module unload, no register write
beyond the two kregnow forms; a held fault that does not clear (10) or a stall (18): the user
decides.  No answer over ssh (142/255): one bounded copy, the user checks the laptop.

## 7. Risks

- **k-bif (medium to high, last)**: a `CR_BIF_CTRL` write on a held fault; E317 stalled a laptop
  once.  Mitigations: held faults and one idle row only (the module refuses with -EBUSY while a
  job is unfinished and nothing is held), exactly two write forms (`0x0c04=VALUE` without bit 19,
  `0x0c00^=0x10`, enforced in `bif_write` and by the guard), every write and the regs read after it
  bounded by `timeout -k` (10 s), f3 (the texture fault) last.
- **k-f4**: 4x faults leave state (E729: faulting health triangles, failed recoveries); reset and
  two health tries after every fault, stop at the first failed recovery.  h8 (1024x768 at 4x) may
  overflow the 0x422-page parameter buffer: `--keep-overflow`, the message is cannot tell.
- **k-pb (medium)**: a garbage dword 11 may hang the ISP (p4): hang = stop, reset, health.
  p0/p1 are cheap and gate the pokes.
- Nothing writes a clock-gate register, trc_hazard, kreg, a clear or enable register, kpoke by
  the runner (the tool writes the par pokes), /dev/mem, a boot-loader file or a kernel; the only
  debugfs writes are `hold_recovery`, `reset`, `render_rgn_arrays` (1 or 4) and the two kregnow
  forms, always through `sudo -n`, all enforced by `run/guard_k.sh` and tested (13 injections).

## 8. DEVIATIONS from the design and the decisions

1. **c1 runs last in k-f4** (the design lists it first): fault rows run last in their stages
   (binding); c3 and c2 run first, c1's job is the same.
2. **Pixel E2 set bits**: the write is the fault word with bit 19 (the idle bit) left out
   (0x10008, 0x10004, 0x10002); the design says "the set bits" and gives 0x80000 as H-W1C's
   result, which is the idle bit staying set [infer].  The runner computes it from the fault read
   just before; the guard and `bif_write` refuse any value with bit 19.
3. **The dump run of Q285**: the pinned tool's `--dump-render` writes the parameter buffer once,
   after the last render; there is no dump between the TA and the 3D.  The dump run is the TE 0x40
   job of the same shape (stage k-pb0, first); the index of the poke is checked against it (the
   stream words at dwords 0-2, E728's words at 11-26).  Whether the 3D rewrites the buffer is
   unmeasured: the p3/p4 dump reads are reported as data, the kernel log is the gate for "applied".
4. **k-pb0 and k-pb are two stages** (the design has one stage pb): the gate needs the controls
   kept before the pokes run; 3 + 5 = the design's 8 jobs.
5. **Fault limit per stage** (5), not cumulative as the r2 driver counted.
6. **n0 is an idle row with no tool**: the four writes alone with a regs read after each; "health
   passes" is the driver's and runner's health after the stage.
7. h8 only carries `--keep-overflow` (an existing option, not a new one).
8. The kernel log lines of the new module (`kregnow 0x0c04: OLD -> NEW, reads R, BIF_INT_STAT I
   BIF_FAULT F`, the two `SGX reset:` BIF lines, `kpoke par:I=0xV applied`) are read from the fork
   source, not from a run: a format that differs makes the rows NODATA, not wrong.
9. No tool option was needed that the pinned build lacks, so no row was dropped.
