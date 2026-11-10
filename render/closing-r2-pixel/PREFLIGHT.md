# R2-pixel preflight: jobs, time, controls, decision rule, risks, changes

Prepared 2026-11-10 from `closing2/exp-pixel.md` sections 2 and 3 and decisions R2-7 to R2-9,
R2-17.  Nothing ran on the laptop.  Frozen: `FROZEN.sha256` (every generator, scorer, runner
script, table, prediction, staged program, template, the data the generator reads and the landed
files it imports: probe.py, tx_map.s, sgxfive-test.c, p1141-addr.toml), `PREDICTIONS.sha256`.
Refreeze (`run/freeze_r2.sh freeze`) only after regenerating, and never after the first job.

## 1. Jobs and time

| stage | jobs | what |
|---|---|---|
| r2-d-safe | 5 | d-ok-64, d-L2e2-19, d-L2e2-19x, d-L2e2-18x, d-L2e2-18 (no fault expected) |
| r2-d-fault | 2 | d-L2e2-17 (held out, fault expected), d-L2e2-16 (control, last) |
| r2-a-safe | 4 | a4 (control), a1, a2, a3 (replicate) |
| r2-a-fault | 2 | a5 (held out, HELD), a6 (control, HELD, last) |
| r2-a-slack | 3 | conditional: sa4, sa5 (HELD), sa6 (HELD, last) |

Time (from S1b/S3/R1 per-job times: a probe job 1 s, a tri job 0.2 s plus 3 s to keep a 4.6 MB
PB dump, reset 3 s before every job, a held job 3.8 s hold plus two resets, a fault plus its
health triangle 12 s, per stage ssh, preflight, start health, copy, score, health 30 s): D2 about
3 minutes, A2 about 4 minutes, slack about 2 minutes, staging 1 minute: **about 10 minutes** (12
with the slack pair); plan 20 (health retries after the 4x faults: S3 saw two failing triangles
after E729's unheld 4x faults).  Bounds: 900 s a stage, 300 s a copy, 150 s health, 60 s a held
job, 120 s a plain job.

## 2. Tool

R1's build `~/sgxfive-test-r1` (sha256 bf4f8be2...) and `~/regtimeline` (079f6359...) are reused:
the source in the main checkout is still the one R1 built (sgxfive-test.c sha256 4250ca36...), and
every option used exists in it (`probe --scratch-pages 16..64 --coords --pixels`, `tri --tri-full
--keep-going --width --height --max-width --max-height --poke cmd:N= --dump-render --wait-ms`).
`tests/mock_all.py` runs all 16 table commands through the landed tool's `--mock`: 16 of 16
accepted, the `targets up to WxH` and `scratch at ... (N KiB)` echoes match.  **No rebuild.**  The
mock does not render, so it proves acceptance, not behaviour; 544x656 (the slack pair's maximum)
has never run on hardware (a refusal stops the stage, rc 4).  The runner's preflight refuses any
other tool or regtimeline hash.

## 3. Controls: how each passes and fails (scorer states: PASS, FAIL, NODATA, cannot tell)

| row | passes | fails (what the scorer says) |
|---|---|---|
| d-ok-64 | complete, image = S1b's A4 hash 1074d49c... | everything cannot tell; the stage's other rows are not read |
| d-L2e2-19 (FIT) | complete, 2048 words byte-identical to S1b's measured image | 19x, 18x, 18, 17 cannot tell ("not byte-identical") |
| d-L2e2-19x | complete, every word = S1b's image XOR 1 | 18x cannot tell (the variant is not trusted) |
| d-L2e2-16 | fault 0x90002 at 0x3e017001 (E722) | d-L2e2-17 cannot tell ("the 16-page control did not fault") |
| a4 | rc 1/0 with diff, 28 of 128000, first (304, 128), echo 544x400, TA data 0xa000, one array at 0x4000, nothing below 0x4000 or from 0x5800 | cannot tell for A2; closes the r2-a-fault gate |
| a6 | held fault 0x90004, page 0x20008 (later accepted and reported), hold message, echo 320x400 | cannot tell for Q286 ("the layout model is wrong" if it completes) |
| sa4, sa6 | as a4 (605 of 188928, first (272, 208), TA data 0x11000, rgn 0x7000, stride 0x2400) and a6 (page 0x2000d) | the slack verdict cannot tell |

NODATA (never a verdict): no `cases.tsv` row (not run), no output, rc not a tool result (2, 124,
127, 128+), class missing, a fault latched before the job (snap 0), the probe's scratch line not
`0x3e003000 (N KiB)` for the row's N (another base voids the row), not 2048 pixels, a dump
missing, a1/a2 with fewer than 4 arrays.  The tool's messages are searched in the WHOLE output
(R1-events lost "scene overflowed" in a 4000-character tail): tested with 6000 and 12000
characters around the message.  Every tri row has `expectdiff`, every probe row of the safe D
stage but d-ok-64 has `expectnopix` (below), so a wrong control result is recorded and scored,
never a stage stop before the scoring.

## 4. Fit vs held out (tallied apart in every SUMMARY)

- HL (probe layout) rows 21, 20, 19 are FIT (S1b measured 2048 of 2048; the model has no free
  parameter): d-L2e2-19 carries it as a control.  d-L2e2-18 is a **repeat** (retrodiction: S1b
  measured rc 3 before the model existed).  HELD OUT: d-L2e2-18x (0xdeadbeee everywhere, rc 0)
  and d-L2e2-17 (fault 0x90002 at 0x3e017001).  Controls: d-ok-64, 19, 19x, 16.
- A2: a4 and a6 controls, a1, a2, a5 HELD OUT, a3 replicate.  S3 already measured a4 (28 of
  128000 first (304, 128), echo 544x400, TA data 0xa000, one array): refrozen, so it is a repeat
  by data but still the control; sa5 is held out; sa4, sa6 controls.

## 5. Decision rules (frozen in `score_r2.py`)

Q281 (`verdict`): HL when d-ok-64 and d-L2e2-19 pass and every held-out row agrees; "HL
REFUTED" if 18x gives rc 3 or another image (HS) or 17 completes or faults elsewhere; "partly"
if a held-out row cannot tell (control failed or void).

Q286 (as S3's verdict): closed H4 when slot 4 is zero in a1 and a2, a3 equals a1, a5 completes
with 4 arrays in 0xa000 (diff 0 of 128000) and a6 passes; closed H5 when a1 or a2 shows an
array-like fifth slot and a3 equals a1; cannot tell when a control fails or data are void.

**Slack-pair rule.**  a5 "cannot tell" when it faults (at 0x2000a: H5 or slack of the kernel
layout; or another page) or completes with a wrong image, while a4 and a6 passed.  Then
`score_r2.py gate r2-a-slack` opens (exit 0); exit 3 "not needed" if a5 completed in four arrays;
exit 1 closed if a4 or a6 failed, a5 is void (rerun r2-a-fault) or r2-a-fault did not run.  The
pair 288x656 in a context made for 544x656 (rgn 0x7000, rgn_size 0x2400, size 0x11000: four
arrays end at 0x10000, one page of slack, five would end at 0x12400): sa4 control (TE 0x20, 605
wrong pixels, first (272, 208), one array), sa5 held (TE 0xe0: H4 completes, diff 0, TA data
0x11000, 4 arrays; H5 held 0x90004 at page 0x20011), sa6 held control (max 288x656, TA data
0xd000: fault 0x90004 at 0x2000d).  With a5 cannot tell and slot 4 zero in the dumps: sa5
completes = "H4 holds with slack" (a5 faulted only because 320x400/544x400 is boundary-exact:
kernel layout fix, Q140); sa5 faults = "more than four arrays plus a page needed", NOT H4, H5
not shown by a dump: cannot close; a slack control failing = cannot tell.

## 6. Stop rules (runner exit status; `r2.sh` passes it on and stops)

Runner: 1 preflight (module srcversion installed = loaded, the 7 debugfs files exist, tool and
regtimeline hash, hold_recovery N, render_pb_pages 0x422, alias_skip 0, the table, runner and
programs frozen, laptop FROZEN.sha256 = the Mac's, attempt directory empty, a tri row without
expectdiff or --keep-going); 3 watchdog, lockup or BUG; 4 an unexpected fault, **any hang**
(hypothesis row or not), or failure; 5 the plain triangle fails after a reset and two tries; 6 a
job did not return; 7 unknown knob; 8 staged program missing; 9/11 hold_recovery read-back;
10 a held fault still latched after two resets; 12 registers unreadable; 13 the reset before a
job failed; 14 a fault latched before a job; **15 the 5th fault-class event of the session**
(fault or hang, expected or not, counted across stages: the driver passes `R2_FAULTS_PRIOR`;
stop comes after that event's reset and health).  Driver: 20 frozen files changed, 30 to 37
health checks, 38 no scorer SUMMARY, 39 attempt directory exists, 40 a gate is closed (the
SUMMARY says which stage to rerun), 41 the slack pair does not fit the budget.  Expected events:
d-17, d-16, a5 (if H5 or slack), a6 = up to 4; the slack pair adds 2, so with four used it needs
`R2_FAULT_LIMIT=6` (the driver stops with rc 41 and prints the command: the lead's call).

Recovery (S3's plan): a held fault that does not clear (10): nothing more is done, the snapshots
are kept; no reboot, no module unload, no register write, no retry: the user decides.  No answer
over ssh (142/255): stop, one bounded copy, the user checks the laptop.

## 7. Risks

- **a5/a6 (4x faults)**: E729's unheld 4x faults were followed by faulting health triangles and
  recoveries needing the second reset; held, the same kernel reset path runs.  Health allows a
  reset and two tries.  The slack pair adds two more such faults.
- **d-L2e2-17/16**: two 0x90002 faults at 0x3e017001, E722/E743/S1/S3 measured the 16-page one
  many times (plain and held) without a hang.  17 pages is expected identical.
- **a5 never ran**; the largest 4x completion is 320x128.  A completion with a wrong image is
  recorded (expectdiff) and scored "cannot tell".
- **18x / 19x**: a new program (one instruction); it assembles, differs from S1b's in exactly the
  last word (tested).  If the sample unit returns nothing the output is 0xA0A1A2A2 (reported as
  HS: another image).
- Nothing writes a clock-gate register, trc_hazard, kreg/kpoke, /dev/mem beyond `regtimeline`'s
  reads, a boot-loader file or a kernel; the only debugfs writes are `hold_recovery` (Y for held
  jobs, always back to N and read back) and the kernel's own `reset`; every debugfs access goes
  through `sudo -n` (guard-checked, `[ -e ]` and globs too).  The debugfs directory is dri/0/sgx
  or else the first `dri/*/sgx` (three names exist: dri/0, dri/0000:00:02.0, dri/128).

## 8. What changed from the proposal, and why

1. **d-L2e2-18 is a `repeat`, not held out**: the proposal calls it a retrodiction; S1b already
   measured rc 3 and the model was built knowing it.  The held-out row is 18x.
2. **`expectnopix` knob** (new in the runner): S1b's d-L2e2-18 (rc 3 "no pixel written") was
   class `fail` and stopped p-d.  Now rc 3 with that message is class ok and scored; 19, 19x and
   18x carry it too, so a wrong control or an HS result is recorded, not a stop.
3. **A hang always stops**, even in a hypothesis group (S3's runner recorded and continued).
4. **5th-fault stop and the slack gate** are implemented (count across stages, `R2_FAULTS_PRIOR`
   and `R2_FAULT_LIMIT`; gate exit codes 0/1/3).  The slack stage cannot run inside the budget
   unless the lead raises it (section 6).
5. **No `set -f`**: the runner walks the table by line number; a test counts the kept dumps.
6. **a4 refrozen** to E727's model (S3's 0 was wrong: it stopped S3).  Every tri row has
   `expectdiff` (S3's a4 had none).
7. **xor immediate**: `xor.skipinv.end o0, r10, #1` assembles with the immediate directly (no
   register, no extra control row needed).
8. **Gates are computed, not stored** (no gate file to reset on restaging); the driver says
   exactly what to rerun.
9. a6's E1 row (Q003 TA write, HE/HF) rides along as in S3; no kernel-log slice is needed (held
   registers).  Q276 and Q003 PBE are not in this session (other batches).
