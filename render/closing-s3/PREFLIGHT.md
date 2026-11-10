# S3 preflight (prepared 2026-11-09, NOT run)

S3 of the question-closing pass: the held faults, pixel E1 (Q003) and pixel A (Q286 sufficiency).
Plan: `~/src/plans/resgx545-question-closing.md`, decision 7 (S3 last, riskiest state). Proposal:
`closing/exp-pixel-faults.md` sections 1 and 5. Pixel E2 (kreg writes to CR_BIF_CTRL /
CR_BIF_INT_STAT) is not approved and is not here. The laptop was not contacted, nothing is
committed, no landed tool was changed. Everything is under `~/src/scratch/resgx545/closing/s3/`.

## 1. How to run (after S2 has finished and been analysed; one session on the laptop at a time)

```
run/guard_s3.sh && run/freeze_s3.sh verify     # static rules; frozen files unchanged
run/stage_s3.sh                                # runner, tables, hashes, one program; no compile
run/s3.sh                                      # the five stages, gates, scoring, health between
$PY score/score_s3.py verdict out/ATT           # Q286 and Q003 SUMMARY lines
```

Each run of `s3.sh` is an attempt `ATT` (`S3_ATT`, default the clock): output in `out/ATT/STAGE` on
the Mac and `~/s3-out/ATT/STAGE` on the laptop, never written twice (driver 39, runner 1); a rerun
after a stop is a new attempt (`--from STAGE`, with `S3_PRIOR_ROOTS=out/OLD` so the gates and the
verdict read the earlier stages). The driver passes the runner the sha256 of the Mac's
`FROZEN.sha256` and the attempt; the runner refuses a laptop copy that differs, before it touches
anything. The runner ignores SIGPIPE and SIGHUP and writes all its output also to
`STAGE/runner.log` (a dropped ssh does not stop a stage half way; the copy has the whole log).

`PY` is `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python` (numpy, scorers only).
`SGX_DRY_RUN=1` prints the commands of `stage_s3.sh` and `s3.sh`. S3 reuses S1's laptop binaries
`~/sgxfive-test-s1` (sha256 d776afbc...) and `~/regtimeline` (079f6359...): `run/s3.env` holds both
hashes and the runner refuses others; the tool source is unchanged since (sha256 42540a78...).
Any change to a frozen file needs `run/freeze_s3.sh freeze` again (the driver, the runner and the
scorer refuse otherwise).

Files: `tables/STAGE.txt` (`name|set|risk|knobs|rt|args`), `predictions/s3-a.tsv`, `s3-e1.tsv`
(frozen, `PREDICTIONS.sha256`), `score/score_s3.py` + `s3lib.py`, `run/run_stage.sh` +
`lib_s3.sh` + `s3.env` (laptop), `run/s3.sh` (Mac driver), `run/stage_s3.sh`, `run/freeze_s3.sh`,
`run/guard_s3.sh`, `bins/s1d-tw64x64-l2e2__0.bin` (byte-identical to S1's frozen copy, which
faulted 0x90002 on the laptop as d-L2e2-16), `tests/`, `work/reset_status_scan.py` (offline scan,
section 6).

## 2. Jobs, in order (10 jobs, 5 stages)

| stage | job | set | mode | frozen prediction |
|---|---|---|---|---|
| s3-a-safe | a4-ctl-320x400-te20 | control | plain | completes, diff 0, 544x400, 0xa000, 1 array |
| s3-a-safe | a1-256x160-dump | heldout | plain | completes, 0x6000, slot 4 zero H4 / written H5 |
| s3-a-safe | a2-320x128-dump | heldout | plain | as a1 |
| s3-a-safe | a3-256x160-rep | replicate | plain | TA data sha256 = a1's |
| s3-e1-ctl | e1-ta-read | control | held | E444: 0x20000000, 0x480, 0x90008, 0x3e000001 |
| s3-e1-ctl | e1-bg-fetch | control | held | E444: 0x20000000, 0x440, 0xd0400, 0x0001f061 |
| s3-e1 | e1-tex | heldout | held | 0x90002 at page 0x3e017; HE 0x440; HF an extra bit |
| s3-a-fault | a5-320x400-max544 | heldout | held | H4 completes, 0xa000, 4 arrays; H5 0x2000a |
| s3-a-fault | a6-320x400-max320 | control | held | 0x90004 at 0x20008; HE 0x480, HF extra bit |
| s3-xfer | e1-xfer-ro | heldout | xferro | 0x80020, 0 written; HE 0x440, HE-edm 0x400; HF |

e1-xfer-ro is alone in the last stage: if debugfs `xfer_ro` is gone or fails (-ENOENT, -EINVAL,
-ENODEV: rc 1 and no fault, stop 4) nothing after it is lost.

Commands are E729's q140 form (`tri --tri-full --keep-going --wait-ms 20000 --width W --height H
--max-width MW --max-height MH --poke cmd:1=TE --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002
--poke cmd:16=0xeaa26e26 --dump-render "$W/dump"`), E444's `tri --fault` and `tri --pixels --poke
cmd:23^=0x08000000`, S1's texture probe, and a read of debugfs `xfer_ro`. All 9 tool commands are
accepted by the landed tool's own mock (`tests/mock_tool.py`).

Held mode (`held`): hold_recovery Y (read back), the job in the background under regtimeline
(0x0118, 0x012c, 0x0c00-0x0c08, read-only), debugfs regs read before the job (snap 0), 2.8 s after
the launch (snap 1, = E444's 2.5 s after the tool's start), 1 s later (snap 2); then the kernel's
own debugfs reset WITH THE HOLD STILL Y (it becomes the held recovery and blames the held job:
`sgxfive_recovery_hold`; writing N first would let the 50 ms watchdog recover on its own and make
the debugfs reset a second halt); then hold_recovery N (read back); snap 3; one `wait` for the job
(bounded by `timeout -k 10 60`). Before every job: the reset must succeed (13) and snap 0 must show
no fault bit (14). `xferro`: the same without the hold (xfer_ro is the kernel's EDM transfer path;
no render job, so no watchdog; the fault stays latched until the reset). Classes of held jobs come
from snap 1
(fault = CR_BIF_INT_STAT bits 15:0 set; hang = the kernel's hold message, no fault bit), not from
the kernel log, which under a hold says "hung" for a fault too and prints no fault line.

### Control walk: how each control passes and how it fails

- **a4** passes: rc 0, class ok, `diff: 0 of 128000`, the tool's echo `targets up to 544x400`, the
  TA data dump 0xa000 bytes (the knob proof: the kernel laid the TA data out for the maximum), one
  array written, nothing below rgn. Fails: any of these (tested: TA data 0x8000, another echo, a
  wrong image, two arrays, a fault, no output). A fault or wrong image also stops the stage (no
  `expectdiff`, no hypothesis group). A failed a4 closes the gate of s3-a-fault (status 40).
- **a1, a2** (held out, not controls) are NODATA unless rc 0, diff 0, TA data 0x6000 and at least 4
  arrays written (the 4x proof); NODATA gives "cannot tell".
- **a3** passes when its dump's sha256 equals a1's; without it neither H4 nor H5 is closed.
- **e1-ta-read, e1-bg-fetch** pass when class fault, the hold message present (the hold took
  effect), snap 0 clear, snap 1 equal to E444's four words, no extra bit at snap 1, and snap 3
  clear. Bits seen only in the timeline are reported, not part of the pass rule. Fails: any of
  these (tested: status2 0x400, no hold message, snap 1 missing, status bit 18 extra, not cleared,
  no fault, a fault latched before the job). Either failing gives "METHOD BROKEN" and closes the
  gates of s3-e1, s3-a-fault and s3-xfer.
- **a6** passes when class fault, the hold message, echo 320x400, CR_BIF_INT_STAT 0x90004 and the
  fault page 0x20008 or above (a later page is accepted and reported). Fails: completes (the layout
  model is wrong, a5 says nothing), another word, a page below 0x20008, no echo. Its failure makes
  Q286 "cannot tell".
- No row is designed to draw nothing or to differ, so none needs `expectdiff` for its pass. a5 and
  a6 carry it so that a completion with a wrong image is recorded and scored (a5: "cannot tell";
  a6: the control fails) instead of stopping the session before the scoring.

Decision (frozen in `score_s3.py verdict`): Q286 closed H4 when slot 4 is zero in a1 and a2, a3
equals a1, a5 completes with 4 arrays in 0xa000 and a6 passes; closed H5 when a1 or a2 shows a
fifth array AND a3 equals a1; slot 4 lies in the ZLS area at 256x160 and 320x128 (zls 0x5000), so a
written slot 4 counts as an array only if it looks like one (non-zero dwords at positions slot 0
also writes, and at least as many as the sparsest of slots 1-3: true of every array in E728's
dumps, tested); a slot 4 that does not, or a gap (a later slot written after an empty one), is
"cannot tell". Also "cannot tell" when a5 and a6 both fault (H5 or slack: Q140's kernel layout
needed), when a control failed or data are void; a fifth array with a completing a5 is reported as
inconsistent. Q003 E1: HE for every held kind (no status bit of its own, set at snap 1 and not at
snap 0, or rising at the fault in the timeline before snap 2, beyond CR_EVENT_STATUS bit 29 and
CR_EVENT_STATUS2 bits 10, 7, 6; bits 14 SW_EVENT and 31 MASTER always masked; timeline rows at or
after HOLD_READ + HOLD_GAP = 3.8 s are the reset's and not read), HF if any kind shows one, "cannot
tell" if the E444 controls failed. A job with a fault latched at snap 0 is NODATA.

## 3. Time

| part | estimate |
|---|---|
| staging (copies, sha check) | under 1 min |
| s3-a-safe (4 jobs: reset 3 s, job under 1 s each) | about 30 s |
| s3-e1-ctl, s3-e1 (2 held jobs each: reset, 3.8 s held, reset, health) | about 40 s each |
| s3-a-fault (2 held jobs; health retries likely, E729: two faulting triangles) | 40 s to 2 min |
| per stage: ssh, preflight, start reset, health, copy, score, health.sh | about 30 s each |

About 5 minutes of laptop time, 10 with every health retry. Bounds: 900 s a stage, 300 s a copy,
150 s the health, 60 s a held job, 120 s a plain job.

## 4. Stop rules (runner exit status; `s3.sh` passes it on and stops)

1 preflight (driver srcversion installed = loaded, debugfs files, tool and regtimeline sha256,
hold_recovery N, render_pb_pages 0x422, alias_skip 0 at the start, tables, runner and program
frozen); 3 a watchdog, lockup or BUG line; 4 an unexpected hang, fault or failure (a fault in a
job outside a hypothesis group, rc 1 without a diff line, a wrong image without `expectdiff`); 5
the plain triangle fails after a reset and a retry; 6 a job did not return (rc 124); 7 an unknown
or forbidden knob; 8 a staged program missing; 9 hold_recovery did not read back Y (the job is not
started); 10 a held fault still latched after the reset and one more reset; 11 hold_recovery did
not read back N; 12 the registers could not be read; 13 the reset before a job failed; 14 a fault
latched before a job. The runner also stops with 1 when the laptop's FROZEN.sha256 is not the
Mac's, the attempt is missing or its directory is not empty. Driver: 20 frozen files changed, 30
to 37 health.sh checks (no answer, fill and triangle not both diff 0, FAIL, watchdog,
render_pb_pages, hold_recovery not N, alias_skip, copy failed), 38 no scorer SUMMARY, 39 the
attempt's stage directory exists, 40 a gate closed, 142 a bound reached (a freeze). Every laptop
`timeout` is `timeout -k 10` (guard checks). Before the preflight passes, the runner's exit
touches nothing (another
session may hold a fault); after it, the exit sets hold_recovery N first, then resets unless the
stop was 3, 6 or 10.

Lessons of S1 applied: debugfs only through `sudo -n` (the mock's debugfs directory is mode 000 and
a bare `[ -e "$D/..." ]` fails it; `guard_s3.sh` greps every code line naming `$D` or
`/sys/kernel/debug` for `sudo -n`); `--keep-going` on every render; the first regtimeline row is
the previous state (the scorer uses rows from the command's `start` on; tested with a stale fault
row); missing or empty data are NODATA; rc and class on every row; controls can fail (tested, each);
knob proofs per job (tool echo, TA data size, the 64 KiB line, the hold message, the read-backs);
the scorer verifies the freeze before scoring (tested: refuses after a prediction changes);
every ssh and scp bounded (guard checks); no `| tail` or `|| true` (guard checks); no wait loop;
per-job kernel-log markers (knobs, read-backs, snaps, resets, health tries, class), the job's
kernel-log slice taken before its health triangles, which have their own markers and kept outputs;
expected-fault jobs in hypothesis groups and last.

## 5. Risks

- **a5, a6 (4x faults)**: E729's unheld 4x faults were followed by 5 faulting health triangles at
  the same TA data pages and 3 recoveries with "no INIT_COMPLETE after 500 ms" (-110), each
  recovered by the cleanup's second reset. Held, the same kernel reset path runs (sgxfive_reset);
  whether the hold makes it better or worse is unknown. The health allows two failing triangles.
- **a5 never ran**: the largest 4x completion is 320x128 (E729). In the 544x400 layout the ZLS
  area starts at 0x7000, inside the target's arrays 2 and 3; E729's 256x160 completion had the same
  overlap (zls 0x5000, arrays to 0x5800) and drew exactly, and E728's dumps show nothing past the
  arrays, so no ZLS store is expected without `--depth`. A completion with a wrong image is
  recorded, not a stop.
- **e1-xfer-ro**: debugfs `xfer_ro` last ran on the phase-4 kernel (E021, 2026-10-31). It holds
  the device lock for its 500 ms wait (snap 1 comes 2.8 s later); it leaves the EDM unable to
  power off until the reset (the reset halts without asking). Last of its stage.
- **e1-tex**: the probe waits 5 s (WAIT_NS; `--wait-ms` is tri/dummy only); the reset comes at
  about 4 s after the launch. If the probe gives up first, its context's cleanup fails while held
  and is dropped (E355); the reset then cancels it. Either order ends the hold.
- **held jobs under regtimeline**: a tight read-only loop on the Atom while the job is held (about
  4 s); S1 ran regtimeline on many jobs.
- **E444's reading may not repeat**: then the gate stops S3 before anything new runs.

## 6. Offline result found while preparing (no hardware): the kernel already logs status at reset

`sgxfive_clear_faults` prints `SGX reset: BIF_FAULT x EVENT_STATUS a/b` on every recovery, after
the halt and before it clears anything. `work/reset_status_scan.py` pairs each "BIF fault W at A"
line in the kernel logs of resgx545-data and S1's out/ with the next reset line
(`work/reset_status_scan.out`; 1101 pairs in 72 dataset directories, some counted twice through
per-job slices and journals):

| word | reset's EVENT_STATUS / EVENT_STATUS2 (after the halt) |
|---|---|
| 0x90002 (texture) | 0x20000000/0x440: 50 of 50 |
| 0x90004 (TA write) | 0x480: 129; 0x400: 28 (kept-owner, reg-074c, kept-state jobs); 0x440: 1 |
| 0x90008 (TA read) | 0x480: 33; 0xc80: 1 |
| 0x90080, 0x90100, 0x90200 | 0x440: 10; 0x440: 75, 0x400: 129; 0x440: 11, 0x400: 3 |
| 0xd0002, 0xd0008, 0xd0080 | 0x440: 2; 0x480: 24; 0x440: 5 |
| 0x80400 (EDM write) | 0x400: 11 (bit 31 set in 3) |

So e1-tex's and a6's HE status2 values are already seen after the halt (they are "fit" for those
rows; the held-out part is the reading during the hold and the timeline). BIF_FAULT reads 0x0 after
the halt in all 1101 resets: the halt (deinit script and SOFT_RESET_ALL) leaves CR_BIF_FAULT
reading zero before the kernel writes CR_BIF_CTRL's clear bit, a lead for E2's "what clears it"
(a register of a block held in reset may read zero whatever it holds) [infer].

## 7. Recovery plan

- **A held fault does not clear** (stop 10): the runner has already written debugfs reset (with
  the hold Y), set hold_recovery N, reset once more and read the registers after each; it then does
  nothing more (no third reset, no health triangle) and keeps the snapshots. On the Mac: copy
  `s3-out/ATT/STAGE` (bounded),
  then stop. Do not reboot, unload the module, write any register or retry jobs: the user decides
  (a reboot is the user's call). Record CR_BIF_INT_STAT, CR_BIF_FAULT, CR_BIF_CTRL from snaps 3
  and 4 and the kernel log: that a fault survives the kernel's halt and boot is itself a Q003 fact.
- **The debugfs reset returns -110** (no INIT_COMPLETE): recorded as reset_rc; the context's
  cleanup then resets again (E729's pattern); the health decides (stop 5 after a reset and a retry).
- **No answer over ssh** (142 or 255): stop; no further ssh commands beyond one bounded copy
  attempt; the user checks the laptop.
- **hold_recovery stuck at Y** (11): the exit tries N once more; S3 stops; nothing else runs
  (every later fault would be held).
- **A failed preflight** (1): nothing is touched (no reset, no knob write).

## 8. Proposal claims contradicted by source or records

1. "confirm `--max-width` takes effect, by reading the layout in debugfs `layout`": debugfs `layout`
   (`sgxfive.c:266`) prints the firmware buffers' addresses, heap bases and the PD, not a render's
   TA data. The knob proof used here is the TA data dump's size (0xa000) and the tool's echo.
2. "a1 and a2 completed in E729; their dumps separate 4 from 5": E729's q140 jobs had no
   `--dump-render`; there are no dumps of those sizes. S3 runs them with the dump.
3. E1 "the two enables written with kregnow (E444's method)": not in S3 (no register writes beyond
   the tool's knobs). E444 already showed bits 6 and 7 of CR_EVENT_STATUS2 raise the host interrupt
   once enabled; the enable step would matter only for a new bit (HF), as a follow-up.
4. E1's prediction "transfer 0x80020: STATUS2 0x440": no record has a status for that fault; the
   EDM's own write fault reads 0x400 (E444). Both are frozen (HE 0x440, HE-edm 0x400).
5. E1 and Q003 say bits 0, 4, 6 to 9, 11, 14, 15 of FAULT_REQ were never seen and "the ZLS has not
   faulted in any record": the published kernel logs hold 0x90080 (E317's run, ta/points,
   usse/output-room-rd), 0x90100 (E511, ta/mtile-fields, te-words), 0x90200 (zls/control-bits, the
   data of E411, whose bits 5 to 11 faulted the job) and type-5 forms 0xd0002, 0xd0008 (E737),
   0xd0080. Q003's 2026-11-09 requestor table misses them (bits 7, 8, 9 are seen).
6. E1's held-fault list says "a background-program fetch (E363's)" and its table "repeat of E444's
   TA read fault"; Q003 labels 0xd0400 "a fetch at a low address (E363)", E444 "pixel PDS heap".
   S3 runs both E444 kinds as controls.
7. Section 1's risk note: "two failed health recoveries end the run"; S1's stricter rule is kept
   (the first failed recovery stops).
8. Section 1's title includes "Q285's size check": no job of the proposal measures it; S3 has none.
9. The fault page of a held job cannot come from the kernel log: under a hold the watchdog prints
   no "BIF fault" line (`sgxfive_watchdog`), only "job N hung, recovery held"; the scorer reads
   CR_BIF_FAULT from snap 1 (E729's job-id fix is not needed here).

## 9. Ready, missing, and changes to landed tools (none made)

Ready: 5 tables, 2 frozen prediction files, the scorers (per stage, gate, verdict; one SUMMARY
line each), the runner, the driver, staging, freeze, guard, the mocks and tests. Tests run here:
`tests/run_mock.sh` 67 of 67 (five stages end to end with default HE/H4 fakes through to the
verdict; a fake kernel watchdog that recovers a latched fault once hold_recovery is N, so the
reset-before-N order is tested; every stop rule including 9 to 14, the start-time hands-off, the
frozen-sha256 check, a closed output pipe, attempt directories, a hypothesis group's skip, the
bare-debugfs failure, seven guard injections, the driver's dry run and the alarm);
`tests/test_scorers.py` 81 of 81 (each control's failure, void data, each verdict, the hold-window
cut and the masked bits, the array-like rule on E728's dumps, the layout against E729's pages,
S1's regs and dmesg, E729's journal, the freeze refusal); `tests/mock_tool.py` 9 of 9 commands.
Frozen: `FROZEN.sha256` (19 files), `PREDICTIONS.sha256`.

The eight findings of the independent review (2026-11-09) are fixed, each with a test that failed
on the code before the fix (shown by running the new tests on the old code: 16 scorer and 33 mock
checks failed): the timeline window and masked bits (1), the reset written before N (2), the
pre-job reset and snap 0 (3), xfer_ro last and a6 scored (4), the Mac's freeze on the laptop (5),
PIPE/HUP ignored, runner.log, `timeout -k` (6), one directory an attempt (7), the H5 closure
(8).

Missing or unverifiable here:

1. The laptop's state: that `~/sgxfive-test-s1` and `~/regtimeline` are still S1's (the preflight
   checks), that the driver still has `hold_recovery` and `xfer_ro` (checked), that S2 left nothing
   armed (the start reset disarms the debug switches; hold, render_pb_pages and alias_skip are
   checked).
2. Whether debugfs `xfer_ro` still works on branch resgx545 (code read, not run since E021).
3. The scorers are scratch (numpy). A record of Q286 or Q003 from S3 needs them as landed tools.

Changes to landed tools that would help (sizes; none needed to run S3):

- `tools/bringup/health.sh`: no timeout of its own, statuses hidden behind `| head` / `| tail`,
  `dri/0` hard-coded, no `alias_skip` in its knob line: about 5 lines (S3 wraps it in a 150 s bound
  and checks its text).
- `sgxfive-test.c`: `--wait-ms` for `probe` (the texture hold races WAIT_NS = 5 s): about 3 lines.
- kernel (user decision, not S3): print CR_BIF_INT_STAT and CR_BIF_FAULT before the halt in the
  "SGX reset" line (today BIF_FAULT is read after it and is always 0): about 3 lines; the
  devcoredump already captures both before the halt.
- a landed, numpy-free `tools/` version of `work/reset_status_scan.py` if section 6 is to be
  recorded: about 70 lines; and a dated correction of Q003's requestor table (section 8, item 5).
