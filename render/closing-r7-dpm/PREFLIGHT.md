# R7-dpm preflight: jobs, time, controls, stops, risks, deviations

Prepared 2026-11-12 offline from `closing7/b/exp-dpm-r7.md` (all decisions (a); DECISIONS-R7.md R7-2, R7-4, R7-6 (a)). Nothing ran
on the laptop. Two freezes against resgx545 main 1c64f3a and resgx545-data 830641e6: set A (`FROZEN.sha256`,
`PREDICTIONS.sha256`, `FROZEN.commits`) and set B (`FROZEN-B.sha256`, `PREDICTIONS-B.sha256`, `FROZEN-B.commits`, which also pins
the fork's verifier files at 664fd0d0, `sgx_own_regs.h` at 3f0b3e74 and `regs.toml` before 7d0ee7f). Refreeze
(`run/freeze_r7.sh freeze A|B`) only if the tables are regenerated, never after the set's first job; both sets share the generator and
the runner, so a refreeze of one is followed by `verify AB`.

## 1. Laptop

- Set A: module 41E2F5C756F96D20F7109A4 (fork 3f0b3e74) loaded = installed, checked before every stage; set B: module
  37EC97AB0CB37213C42FCCC (fork 664fd0d0) after the one-shot boot (`closing7/kernel/deliver/664fd0d00765/gma500_gfx.ko`, sha256
  cfae29f8...). Another module STOPS (ask).
- Tool `~/sgxfive-test-rgn4` sha256 e6951558..., `~/regtimeline` 079f6359..., python3 >= 3.10 (the staged landed `scorekit.py` needs
  it; staging and the preflight refuse an older one). A mismatch STOPS; nothing is built.
- Every session file under `~/scratch/r7d/`: `run/` (runner, tables, both freezes), `stage/` (p1139-green.bin, oomring2.blob),
  `out/ATTEMPT/` (a1 for set A, b1 for set B; kept files, `state/`). One work directory a job, `mktemp -d ~/scratch/tmp/r7d.XXXXXX`,
  removed once its files are kept (and by the trap on a stop). Nothing in `/tmp`. 600 MB free at each preflight, 200 MB before every
  job (else rc 13, the job not run). Every directory a job writes into is made by the runner and checked before the tool runs
  (`sessioncheck.py outdirs`, rc 13).
- Debugfs: reset, render_pb_pages, regs, buf09, render_param, render_tadata; s-k also own_code, own_arm, own_res, load, boot,
  status, miscinfo. All through `sudo -n`; markers by `sudo -n tee -a`.

## 2. Jobs and time

97 jobs: set A 87 (s-a0 6, s-m 50, s-b 29, s-v 2), set B 10 (s-k). 2048-class jobs about 9 s, 3072-class about 12 s, 4096-class tri
jobs 15 to 25 s, 1024-class about 6 s, s-k about 13 s (arm and page read), five stage starts with health and copies 25 s each:
set A about 25 minutes (plan 45; the driver's stage alarm is 2400 s, s-m), set B about 3 minutes plus the boot.

## 3. Controls (each declares what it reads; each can fail)

| stage | control (reads) | fails |
|---|---|---|
| s-a0 | a0-cal-2048 (S2..S5, knob, mono, gps_left = 2, model), a0-cal-2048f (S2..S7, knob, mono, need 0x213, nparts 0: no grow, no pages left), c4-b5 (cls R, gps_left 2), c4-b6 (cls N, gps_left 1), t-s3m6 (gps_left 1), g-qf 0xa2 (nparts 2, runpeaks 0x80 0xa0 0x2, gmax 1) | runner STOPS rc 10 on a value off, a key WITHOUT A READING (sessioncheck.py premise), a knob proof or a calibration off the model; later stages of set A refused |
| s-m | each calibration (knob, mono) and `model:` | off the model: its cells re-picked as its own S_k + (cell - model S_k), scored for H-SPAN only |
| s-b | each scene calibration: need = HU1's U, no partial render, 1 global page | its cells void |
| s-k | k-b6 first (ring_counts 1: every OOM rung's 0x0724 / 0x072c non-zero and inside the host samples; dec_sa8_380 0), k-b5 (0x180, R) | k-b6's premise: rc 10, s-k stops; the scorer gates s-k's headlines |

Proven at build (tests/test_controls.py): R6-dpm's kept jobs of the same six rows hold all 29 s-a0 controls; planted copies fail
(swap, scene, knob) or read NO READING with a premise STOP (missing control block, missing output); R6's kept k-b5 / k-b6 hold the bits
and FAIL the ring premise (oomring has no page-count words); G8: R6-dpm's a2 through this gate STOPS at a0-cal-2048f grow, and without
it equals `postrun/ungated.out`. Gate scope: s-m by the five 1500-vertex s-a0 rows and its target's calibration; s-b by g-qf and its
scene's calibration; s-k by its own controls (another module, another freeze). Labels: controls `control`; s-m replicates, k-b3,
k-creep2 `repeat`; s-v and F9 counts `explore`; the rest `heldout`.

## 4. Stops

Runner: hang (incl. -110), fault, unexpected failure (rc 4); watchdog/BUG (rc 3); no return (rc 6); failed health (rc 5); capture not
whole, a missing s-v or tri dump, a missing output directory, short of space (rc 13); knob read-back (rc 9); a control or premise
(rc 10); second EDM stall (rc 11); arm or clear failed (rc 12); preflight (rc 1: module not the set's, tool, regtimeline, python).
Driver: any non-zero stage, a file the scorer reads not kept (rc 23, `sessioncheck.py kept`), health not exact, render_pb_pages not
0x422, hold_recovery not N, alias_skip not 0. The lead decides after any stop.

## 5. Risks

- Never-run targets 3072x3072, 3072x2048, 2048x3072, 2560x2560, 1024x1024 (probe) and 4096x2048, 1024x768 moved (tri): the tool's own
  mock accepts all 99 commands with the right echo (`tests/mock_all.py`), so no spare size was used. 3072-class captures are larger
  (up to 0x400 samples of the first run); the 200 MB check covers them.
- s-k needs the boot of a new module (R7-4 (a)): low risk by the plan (two `ldr`, no `str`); the loaded module's verifier (3f0b3e74)
  refuses oomring2, so set B cannot run by mistake on 41E2F5C7 (preflight and verifier both refuse).
- s-k's band 5 cells 0x177 and 0x178 take one partial render by F9: their decision-entry bits will likely read "cannot tell"; their
  abort counts (H-PASS) are readable.

## 6. Deviations from the plan

1. s-v: no rule was frozen (E900), so per decision 5 (a) two exploratory calibrations (2 jobs, not 6), no verdict.
2. s-b 1024x768: calibration + 4 cells (the plan says 5 cells): each scene's U control needs its calibration.
3. s-k order: k-b6 first (the plan's premise job), then k-b5; s-k's fixed cells (S3, S4 + 1) use the 2048 model's steps (s-a0 checks
   them on the same day, set A) instead of calibration-derived cells, since set B runs after a reboot.
4. Scene rule: moves >= 0 only (every kept move is), U kept 10 pages from the kept U at 4096x4096 only; at the other targets a move
   other than (0, 0) is enough (the first pick at 1024x768, U 8, was replaced by this rule before the freeze).
5. The runner needs python3 >= 3.10 on the laptop (landed scorekit.py); the lead checks it at staging.
