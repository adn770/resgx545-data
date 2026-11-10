# S1 of the resgx545 question-closing pass: prepared, NOT run

Plan: `~/src/plans/resgx545-question-closing.md`, decision 7 (S1 = geometry E1-E4, E8, E5, then
pixel B1, C, G, B2, D, F).  Proposals: `closing/exp-dpm-geometry.md`,
`closing/exp-pixel-faults.md`.  Nothing here touched the laptop; nothing is committed.  Read
`PREFLIGHT.md` first (totals, time, risks, inconsistencies) and `OPTIONS.md` (every tool option,
checked against the source).

## Layout

- **`tables/STAGE.txt`**: one job table a stage: `name|set|risk|P|knobs|rt|command`, exact tool
  commands; `TABLES.md` is the readable view
- **`predictions/STAGE.tsv`**: frozen predictions `case quantity value model set`; `*.bits` the B2
  region sets
- **`score/score_s1.py`**: the scorers (written before the run): `score_s1.py STAGE out/STAGE
  [--emit-u U.json]`
- **`gen/s1gen.py`**: regenerates tables, predictions, staged programs (`bins/`), `TABLES.md`
- **`gen/gen_e2_boundary.py`**: the generator of the E2 boundary table `g-e2b`, from the measured
  U (the PAUSE)
- **`run/run_stage.sh`, `run/lib_s1.sh`**: the laptop-side stage runner
- **`run/s1.sh`**: the Mac-side session driver: verify frozen files, stage over ssh, copy results,
  health between stages
- **`run/stage_s1.sh`**: copies runner, tables and programs to the laptop, builds the tool
  (userspace) and regtimeline
- **`run/freeze_s1.sh`, `FROZEN.sha256`, `PREDICTIONS.sha256`**: the freeze (sha256 of
  predictions, scorers, tables, runner, programs)
- **`run/guard_s1.sh`**: static check of the forbidden list (reboot, GRUB, kernel build,
  trc_hazard, clock-gate, kreg, loops)
- **`tests/`**: `run_mock.sh` (every table through the runner against a fake tool and a
  plain-directory debugfs, and the stop rules), `mock_all.py` (every command against the tool's
  mock), `emit_checks.py`, `test_scorers.py` (the readers on landed data)

Python: `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python` (numpy; scorers and
generators only).

## Order and the pause

`g-e1`, `g-e2a`, **PAUSE**, `g-e2b`, `g-e3`, `g-e4`, `g-e8`, `g-e8b`, `g-e5`, `p-b1`, `p-c`,
`p-g`, `p-b2`, `p-d`, `p-f` (`stages.txt`).  Each table starts with its controls; the controls
that fault by design (`d-L2e2-16`, `f-ctl0`) are last.

```
run/stage_s1.sh                       # once: tables, programs, tool, regtimeline (userspace only)
run/s1.sh                             # runs until the PAUSE: exits 10 after g-e2a
python score/score_s1.py g-e2a out/g-e2a --emit-u U.json   # refuses if the 0x13 control failed
python gen/gen_e2_boundary.py U.json  # writes tables/g-e2b.txt and predictions/g-e2b.tsv
run/freeze_s1.sh e2b                  # freeze them BEFORE they run
run/stage_s1.sh --tables-only
run/s1.sh --from g-e2b                # the rest
```

`score_s1.py` refuses to run unless `run/freeze_s1.sh verify STAGE` passes.  `SGX_DRY_RUN=1`
prints the commands of `s1.sh` and `stage_s1.sh`.  Stop codes of the stage runner: 1 preflight
(also a table or program that is not the frozen one), 3 kernel watchdog/lockup/BUG (nothing but
the knob restore touches the machine), 4 unexpected hang, fault or failure (hangs and faults that
are stated hypotheses are measured instead: `hypo:GROUP:MAX`), 5 the first failed health recovery,
6 a job did not return (freeze), 7 forbidden knob, 8 missing program, 9 a knob read-back differs;
`s1.sh` adds 20 (frozen files changed), 30-37 (health after a stage: no answer or a failed
triangle or fill, FAIL, watchdog in the dmesg tail, knobs not back; 37 scp failed), and kills a
stage after `STAGE_ALARM` seconds (default 1800).  Any of them stops the session.  Every scorer
ends with one `SUMMARY:` line, a verdict or `cannot tell`, and treats empty or missing data, an rc
that is not a result and a failed control as void.

## Per stage: control, knob proof, scorer, fit / held out

"Conditions" count identical jobs once (replicates are named `-r2`, `-rep`).  A control that
reproduces an earlier result is the first row of its table.  Set column of the tables and of
`predictions/*.tsv`: `control`, `heldout`, `replicate`; `fit` is used only where a job of S1 is
itself a fit job (none is).

- **g-e1**: jobs / conditions: 22 / 21; control that can fail (first): `c-1500-0x422`: E704's
  words, must not raise; `p-*` positive controls must raise; knob proof: the job's own 0x0624
  (first row after the tool's start with 0x0724 non-zero; the first sample is the previous job's)
  = P - 0x22 (void otherwise); FIT (earlier data): R2 (E625/E630, 109 of 110 jobs); HELD OUT (this
  run): every P < 0x422 job: HC, HA, HS
- **g-e2a**: jobs / conditions: 10 / 8; control that can fail (first): `u-1-0x422` must read 0x13;
  `u-2f-0x38` = E627's st-two-f; knob proof: the job's own 0x0624; `tri ... #k: geometry only`
  lines = K - 1; FIT (earlier data): the U model: 10 known (scene, U) points; HELD OUT (this run):
  the six 2-4 triangle scenes (an empirical coverage proxy, extrapolated: the scorer reports the
  residual, no pass; see PREFLIGHT)
- **g-e2b**: jobs / conditions: 12 to 14, generated; control that can fail (first): overflow at U
  + 0x21, none at U + 0x22; knob proof: the job's own 0x0624; FIT (earlier data): E625's overflow
  rule (post hoc there); HELD OUT (this run): all
- **g-e3**: jobs / conditions: 35 / 31; control that can fail (first): one control a group (E651
  object, E194 removal, E182 1000 px); knob proof: the `emit_checks` word checks and the controls;
  FIT (earlier data): stored 1/w = RZ32(1/w) on the 9 vertices of mte/rhw; HELD OUT (this run):
  every job
- **g-e4**: jobs / conditions: 7 / 4; control that can fail (first): `ix-c`: E414's five-copy
  object; knob proof: `emit_checks`: the flip changes bit 24 of one dword; FIT (earlier data):
  none; HELD OUT (this run): all
- **g-e8**: jobs / conditions: 8 / 6; control that can fail (first): one-object jobs must equal
  E664/E665; knob proof: the compare pair (never/less) differ; echo of `--tri-z`; FIT (earlier
  data): E660's ISP rule (earlier fit); HELD OUT (this run): all two-object jobs
- **g-e8b**: jobs / conditions: 6 / 6; control that can fail (first): both-opaque jobs: the nearer
  colour wins; knob proof: `emit_checks` (blocks 1 and 10); FIT (earlier data): none; HELD OUT
  (this run): the four translucent jobs
- **g-e5**: jobs / conditions: 14 / 6; control that can fail (first): `r-n8-a1` (x2288), `r-n2-a9`
  (x2821) reproduce E702; knob proof: the echoed `VDM words ^6 ^7`; FIT (earlier data): none; HELD
  OUT (this run): the four events
- **p-b1**: jobs / conditions: 11 / 10; control that can fail (first): `g-ctl` (0x3923d700),
  `g-dyadic` (every rule = f32(A)): the control that can fail; knob proof: the echoed `tri:
  vertices256`; FIT (earlier data): the nine rules agree on E731's dp-bx-b0; HELD OUT (this run):
  the eight ramps
- **p-c**: jobs / conditions: 13 / 12; control that can fail (first): `c-e709` (17 to 29 tag-5
  pairs), `c-u` (tag 2 wins); knob proof: the pairs; `c-u`; FIT (earlier data): none; HELD OUT
  (this run): `c-k7`, `c-k0`, `c-k3`, `c-g23`
- **p-g**: jobs / conditions: 9 / 5; control that can fail (first): `g-ctl-lf-r8`: E721's image
  sha256; knob proof: at least one transition per ladder; FIT (earlier data): none; HELD OUT (this
  run): the four ladders
- **p-b2**: jobs / conditions: 5 / 5; control that can fail (first): `d-ctl` reproduces 7680 at -1
  and 1536 at -2; knob proof: echoed vertices; FIT (earlier data): the boundary line x + 2y >= 319
  fitted on dp-ax-b2; HELD OUT (this run): `d-shift`, `d-tall`, `d-b3`, `d-ygrad`
- **p-d**: jobs / conditions: 7 / 7; control that can fail (first): `d-ok-64` (A4 exact);
  `d-L2e2-16` reproduces E722's fault and is the last job; knob proof: the probe's `scratch ... (N
  KiB)` line; FIT (earlier data): the A4 model (E722, 13 of 16); HELD OUT (this run): the 64-page
  and boundary jobs
- **p-f**: jobs / conditions: 20 / 10; control that can fail (last, nothing depends on it):
  `f-ctl0` reproduces E573: fault 0x91000; knob proof: `alias_skip` read-back marker in the kernel
  log; FIT (earlier data): none; HELD OUT (this run): pairs, all, 3 renders, DPM

The frozen predictions with their hashes: `PREDICTIONS.sha256`; files that define a case, a run or
a score: `FROZEN.sha256` (`run/freeze_s1.sh verify` checks both; `s1.sh` does it before every
stage; the freeze is attested by file times and hashes only, as in the earlier batches).
