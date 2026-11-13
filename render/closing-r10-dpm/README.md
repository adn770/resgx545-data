# r10-dpm: round 10's DPM session S10-dpm (Q210)

Round 10, session S10-dpm of `closing10/seeds/exp-seeds-r10.md` section 10 (DECISIONS-R10.md:
R10-5 (a), safe class only: no held reset, no planned fault, no `expectfault` row, `#limit 0`).
Built offline 2026-11-13 on the session kit, scaffolded by `tools/closing/new_session.py` from
resgx545 main 9849dab and resgx545-data 1324301be. Nothing here touched the laptop, cachix or a git
repository. Record number reserved for the fold: E1009 (tooling is adding 4-digit E-number support
before folds). Built from r9-ldpm (`closing9/r9-ldpm`, read in full: session.toml, gen, score,
mock, tests); score/read.py, `gen/r9_tables.json` and `bins/p1139-green.bin` are byte copies of
the published `render/closing-r9-ldpm` files (pinned, tests/test_plan.py).

## The question

Q210: at the sixth global page (S_6) E874's step replay is low at some targets. E962 read S_6 one
or two pages above the replay at each of the four wide targets (one calibration each); E936 and
r9-ldpm's m6b read two values at 1536x1536, 1792x1792, 2304x1792 and 4096x2048, and 0x1dd to 0x1e1
at 2304x2304 (`seeds/q210/s_spread.out`). Either the S_6 step is noisy between runs of one target
(the replay is right on average) or the replay is biased low (a deterministic offset). Replicates
decide it; no new rule is proposed.

## What runs

Laptop prefix `~/scratch/r10d/`, module B60AB0B475DD1E8972419B5 (fork 2a650d74, loaded). Tool t4
`~/sgxfive-test-rgn4` (e6951558..., source resgx545 4623753 `userspace/libsgxfive/tools/
sgxfive-test.c`, sha256 703cbcea..., replayed row by row on its library mock) run under
`~/regtimeline` (079f6359..., `wraps = true`) with R5-dpm's 16 registers; both are on the laptop
and bound by their sha256, nothing is built or shipped. The program binary is
`bins/p1139-green.bin`.

One stage, **s6rep, 17 jobs** (about 5 minutes with the preflight; ~7 s a job under regtimeline):

| rows | what | set |
|---|---|---|
| a0-cal-2048, a0-cal-2048f | r9-ldpm's a0 premise pair (E935), token for token | control |
| s6r-TAG-1 to -3 | three calibration replicates (P 0x422, thr0 0x400, above every need) at 4096x1024 (c1604), 4096x1536 (c1606), 3584x1024 (c1404), 2048x512 (c0802), 2048x2304 (c0809) | heldout |

The replicates run round-robin (replicate 1 of the five targets, then 2, then 3), so a replicate
never follows a job of its own target. Every row is `expect:rc3-overflow` (a calibration that
completes ends rc 0, also an expected end) with `dbg:render_pb_pages` = thr0 + 0x22.

Stops: the a0 pair first; a control off (`ctl:` value) stops the stage (rc 24), an unread one
stops the session (rc 25). Any fault, hang, -110, failed health, or an rc 3 without "scene
overflowed the parameter buffer" stops the stage (rc 4). `min_free_mb` 300, `job_timeout` 120 s.
The replicates never stop a stage; the scorer decides.

## Frozen before the run (`predictions/s6rep.tsv`, gen/plan.py, score/score.py)

Per target T: R = E874's replay S_6 (`gen/r9_tables.json`: 0x17c, 0x229, 0x14d, 0x6e, 0x1ac),
v1 v2 v3 = the three replicates' S_6 reads (S_6 = max(pp, p - 1) as E962 read it, `rd["S"][6]`),
K = the kept read (0x17e, 0x22b, 0x14f, 0x6f, 0x1ad: R + 2, + 2, + 2, + 1, + 1).

| rival | says | prediction at T |
|---|---|---|
| H-NOISE | the replay's S_6 is the centre of a spread | R in [min v, max v] and max v - min v <= 2 |
| H-BIAS | the replay is low by a constant | every v is R + 1 or R + 2 (E962's reading) |
| H-BIAS-SAME (tally) | the offset is the kept one | every v = K |
| H-REPLAY6 (tally) | the replay is exact | every v = R |
| H-REPLAY (tally) | E874's need | need = U (0x20f, 0x302, 0x1d0, 0x9a, 0x24f), nparts 0 |

The two rivals cannot both hold at a target (H-NOISE needs a read at or below R, H-BIAS none).
Per target a class: NOISE, BIAS or NEITHER (any other set of reads: a read below R with the rest
above, a span over 2, a read above R + 2); a missing S_6 makes the target "cannot tell".

**Decision rule** (over the 5 targets, only with both a0 controls passed; else "cannot tell"):
- NOISE decided: at least 4 targets NOISE and at most 1 BIAS. Q210 narrows to noise: the replay
  is right within the step's spread, and E962's misses were one draw each.
- BIAS decided: at least 4 targets BIAS and at most 1 NOISE. Q210 narrows to a bias that is the
  same at every replicate of a target (offset 1 or 2 pages at S_6).
- MIXED: anything else; the per-target classes are recorded, no verdict on the cause.
Not frozen as a verdict, noted for the fold [infer]: an exact replay (v = R at every replicate)
counts as NOISE under the rule above (span 0 contains R) although it says E962's reads were
outliers; a target with a spread but R outside the range (all of R + 1 to R + 3) is NEITHER.
Calibration reads in this stage are all at thr0 0x400 (a completed job); r9-ldpm's 2304x2304
calibration read 0x1e1 where its partial-render cells read 0x1dd, so a calibration-versus-cell
offset (run mode, not noise) is not excluded by these rows [infer; Q210 stays open on it].

**Builder's expectation (not a verdict)** [infer]: 2048x2304 read 0x1ad in all seven kept runs, so
H-BIAS is the stronger there; the four wide targets have one read each, so either rival is open.
The controls can fail: the a0 pair would read otherwise if the module state moved (E935: S_2 to
S_7 and the need 0x213 at 2048x2048).

## Layout

- gen/plan.py (table and predictions; `--check`), `gen/r9_tables.json`.
- score/score.py (scorekit and kitscore; `classify` and `decision` are the frozen rule),
  score/read.py (r9-ldpm's reader).
- run/hooks.sh: `rd_words` (the same reading in awk; tests/test_read.py holds the twin),
  `hook_reading`, `hook_check` (a `ctl:KEY=VALUE` word off stops the stage), `hook_fault` (none).
- `mock/world.py`: six worlds (model, ctloff, noread, fault, rc3other, needoff).
- `tests/`: test_plan.py (generator, rows, safe class, session.toml, the a0 pair the argv twin of
  r9-ldpm's published a0, the strict fake takes every row, the frozen rivals in the predictions, the
  copies are the published blobs), test_read.py, test_score.py (holds on r9-ldpm's kept a0 pair and
  kept calibrations of the five targets as replicates; fails on another target's calibration in
  the a0 place and on a moved knob; classes and decision rule on synthetic reads).

## Commands

- Offline: `bash tests/run_all.sh` (guard, own tests, library mock of every row, mock of every
  world, verify).
- Freeze: `python3 kit/session.py freeze .` (never rewritten).
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .` (stop codes:
  kit/session.py), with `SGX_TARGET_HOST` set; afterwards move `~/scratch/r10d` to
  `~/scratch/archive/`.

## Replay vectors

s6rep: the replicates' S_2 to S_7 and need become the `sgx545-tables` table `dpm/r10-dpm-s6rep`
(`tools/usse-asm/closing_tables.py`) when the fold lands it. Replay: `refused` as a vector (a
spread reading, not a step rule); if NOISE is decided, the sgx-pipe `dpm.rs` step test
(`tool_triangle_steps`) gets S_6's tolerance of 2 pages [infer], and if BIAS is decided its S_6
offset per target is a candidate for the next replay. The fold reads only the kept `out/` files,
`gen/r9_tables.json` and score/score.py.

## Publication

No file reads a firmware image, listing or closed binary: nothing is marked for data-private.
`debug/` is scratch (delete any `.pytest_cache` before the fold publishes).
