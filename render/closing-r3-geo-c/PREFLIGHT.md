# R3-geo-c preflight: jobs, time, controls, deviations, risks (laptop session L1b, add-on)

Prepared 2026-11-10 offline on the Mac, nothing touched the laptop, cachix or any repo.  Built from
`closing2/r2-geo/` (runner, driver, guard, freeze, scorer readers) and its tests.  Design:
`closing3/rank-round3.md` C1 and C2; decisions R3-R1 a, R3-R2 a, R3-R5 c.  Frozen: `FROZEN.sha256`
(23 files: generators, scorers, runner scripts, tables, predictions, TABLES.md, stages.txt, TOOL and
TOOLSRC pins) and `PREDICTIONS.sha256` (3 files).  Refreeze (`run/freeze_r3.sh freeze`) only if the
tables are regenerated, never after the first job.  Tests: `tests/run_all.sh` = ALL TESTS PASS
(25 + 19 + 30 python checks, 3 mock stages, 61 runner checks).

## 1. Jobs and time

| stage | jobs | what |
|---|---|---|
| g-z | 15 | C1 (Q287 + Q122): ZLS band, 3 E730 controls, 10 held-out sizes, 2 single triangles |
| g-qf | 22 | C2 fit (Q211): 3 controls (0xa0, 0xb0, 0xa3) + the 19 split cells at U = 287 |
| g-qh | 14 | C2 held out: 2 scene gates (P = 0x422) + 12 cells of the scenes U = 275 and 438 |
| **total** | **51** | order g-z, g-qf, g-qh (g-qh needs g-qf's kept data) |

Time (R1/R2 per-job times: about 8 s a depth job, 15 to 25 s a 4096x4096 job, a reset and a health
triangle between stages): g-z about 3 min, g-qf about 8, g-qh about 6, stage starts, health and
copies 3 x 25 s, staging 1 min: **about 18 minutes**, plan 30.  Laptop prefix `~/r3gc` (runner,
tables, FROZEN), `~/r3gc-stage`, `~/r3gc-out`; no collision with ~/r3g, ~/r3p-, ~/r3xev or ~/r2.
Pinned tool `~/sgxfive-test-r1` (sha256 `bf4f8be2d8a8fe50034559450928e05695dc96d396d4892f9b00ea6bc0d4f053`
in `TOOL.sha256`, copied from r2-geo; the staging and the runner stop on a mismatch: ask), and
`~/regtimeline`.  Preflight (every stage): srcversion loaded = installed = B21FDA82BD5E5CB5A627E3B
(`WANT_SRCV` pin), debugfs `reset render_pb_pages regs buf09 render_param render_tadata` present,
the kmsg marker arrives, the tool hash.  Tool messages are classified on the whole kept output and
the kernel slice; every gate is derived from the kept files by the scorer.

## 2. What is frozen (full list in TABLES.md and predictions/)

**g-z (C1).**  Rows are E730's isp-a-guard rows (`p1141/isp-a-guard.sh`: the same option string with
`$W/depth` for `@D@`, the depth pitch per width as E730, the 0xdeadbeef pre-fill, the host-side
`--poke blk:1=0x00400200`), tested token for token against E730's recorded options for the three
controls and by the same formula for the other 10 full rows.  Observable: a tile-area dword is stored
iff it is not 1.0f (E465's, as E730's post hoc reader, which the frozen scorer rewrites).  Frozen
rule A: x + 0.5 < 1.25 W (x < ceil(1.25 W - 0.5)), y likewise with H.  Alternatives: FLOOR, ROUND,
CEIL, RSTRICT (x + 1 < 1.25 W).  Gates (kept dump): no tile-area dword left at 0xdeadbeef, the
tool's `diff: 0 of W*H pixels`.

- Controls (E730's sizes, `control`): 34x18 ramp x, 34x18 ramp y (924 stored), 66x34 ramp x (3444);
  each must reproduce E730's count and rule A's set; ROUND and CEIL are refuted there (`repeat`).
  A miss voids the stage (`cannot tell`).
- Held out, full-screen triangle: widths 20, 36, 44, 76 at H 18 (ramp x); heights 20, 28, 36 at W 34
  (ramp y); the band past the tile area: widths 32 and 64, height 32.  Frozen per cell: extent,
  stored count and set hash for each of the five rules.
- Held out, single triangle by `--tri-v` (z-tri-in 34x18, wholly inside the band; z-tri-cross 36x20,
  crossing the band edge, whose corner it covers): pixel-centre raster model clipped by the band,
  edge pixels within 1/16 pixel ambiguous.  A raster miss refutes the raster model only; the band
  verdict is read from the full-screen cells.

**g-qf (C2 fit).**  The 20 (k, s) pairs of E625's family 1 + floor((U + k - thr0) / (thr0 + s)),
thr0 = P - 0x22, that fit E625's 10 and E779's 9 cells (`closing3/rank/q211_fit.out`, re-derived by
`gen/r3_geo.py`).  Rows: E779's command (4096x4096 default triangle, `-n 1 --keep-overflow`) at the
19 cells where the pairs split (0x24 .. 0xa2, descending P), controls 0xa0 = 2, 0xb0 = 1 (E625) and
0xa3 = 1 (E779).  Frozen: every pair's count at every cell, the knob proof 0x0624 = P - 0x22.  The 19
cells leave 13 classes (some pairs agree everywhere at U = 287): the fit cannot pin a unique pair.

**g-qh (C2 held out).**  Scenes of E773: s275 (`-n 1 --move 1:1024,0`) and s438 (`-n 2 --geometry 1
--move 2:0,1024`), `--keep-going` as E773.  Two scene gates (control rows, P = 0x422) read each
scene's U as the 0x0724 peak (275, 438) with no partial render; a scene that differs voids its cells.
Six cells a scene, chosen offline by a greedy that splits the 13 classes until every one of the 20
pairs is its own class (all 20 separated by the 12 cells), then the most divisive, and one cell
where all 20 pairs agree (s275 0x52 = 3, s438 0x7b = 3): s275 0x26 0x27 0x2a 0x2b 0x31 0x52; s438 0x38
0x39 0x48 0x79 0x7b 0xec; at most 9 predicted partial renders (E625 ran 10).  Frozen: all 20 pairs
at every cell, without a mid-session refreeze.  The scorer keeps the pairs the fit left (reads
g-qf's kept data) and scores the held-out cells against them: `pinned (k, s) = ...` when one pair
survives, the survivors listed otherwise, `REFUTED` when none, agree-cell misses listed.

## 3. Controls and stop conditions

| stage | control | passes | fails |
|---|---|---|---|
| g-z | z-ctl-34x18-x, -y, z-ctl-66x34-x | 924, 924, 3444 stored and rule A's set | `cannot tell` |
| g-qf | qf-0xa0, qf-0xb0, qf-0xa3 | counts 2, 1, 1 | `cannot tell` |
| g-qh | qc-s275, qc-s438 | U = 275 / 438, no partial render | the scene's cells void |

Stops: the runner stops on any hang, fault, unexpected failure, kernel watchdog or failed health
recovery (rc 3 "scene overflowed" is the normal class of the count rows).  The scorer, from the kept
files: a count that rises with P (monotone check per scene) = `cannot tell`; a job with a render
before the last overflowed (kick lines lost, E773's rule), a knob that did not land (0x0624), a
0xdeadbeef left in a tile area, a missing `diff:` line, a hang line in the kernel slice = NODATA for
that job, tested before any match.

## 4. DEVIATION from the proposal (needs the lead's eye)

The tool refuses odd sizes (`render.c`: `width % 2`, `height % 2` give EINVAL; the Mac mock prints
`render: Invalid argument` for widths 17, 19, 33, 35 and heights 17, 19, 21, which
`tests/mock_all.py` found first).  So 1.25 W has the fraction .0 or .5 only; the fractions .25 and
.75, where rule A (ceil(1.25 W - 0.5)) differs from FLOOR, cannot be run.  Nearest accepted shape:
sizes at the integer fraction (W or H = 0 mod 4) and new alignments of the band edge in the tile.
There A = FLOOR = ROUND = CEIL and only RSTRICT differs; RSTRICT agrees with A at E730's .5, so E730
did not refute it: the new cells do test a rule E730 could not (centre test x + 0.5 < 1.25 W against
x + 1 < 1.25 W), but **A against FLOOR stays untested**, so Q287's depth clause closes only as far as
A against RSTRICT/ROUND/CEIL at .0 and .5 (E730 and C1 together); the .25/.75 remainder would need
a tool that accepts odd targets.  Everything else the Mac mock refused: nothing (51 of 51 commands
accepted: g-z 15, g-qf 22, g-qh 14).

## 5. Changes from the design

- C2 fit stage runs all 19 split cells (R3-R2 a), not the ~10 of the sketch; 51 jobs in all, not
  ~33.  Fit cells are labelled `fit` (a new set label: scored apart from held out).
- Scene gates added (E773's U read again before the held-out cells), and the held-out cells are
  chosen to separate all 20 pairs rather than where the survivors agree, plus one agree cell a
  scene; the held-out jobs do not take `--dump-render`/`--dump-each` (4.6 MB dumps, not needed).
- C1 grew from ~12 to 15 jobs (heights 32 and the two single triangles).
- The runner is R2's with: no kpoke (a guard rule and a generator rule), the one allowed `--poke
  blk:1=0x00400200` only in g-z, the srcversion pin, no staged programs (no `bins/`).
- Not run: the iterated-attribute clause of Q287 (R3-R5 c, split off as its own question).

## 6. Risks

- Low.  C1 repeats E730's jobs with other sizes (E730: 12 of 12 rc 0).  C2 repeats E779's and E773's
  commands at other P; up to 9 partial renders a job (E625 ran 10 at P = 0x23, 0x24 is the lowest
  here).  The two `--tri-v` rows are new combinations (`--tri-v` with `--depth` and the poke): the
  mock accepts them, hardware not run; a fault stops the stage after the reset and health.  g-z runs first because it is cheap and
  independent of the count stages.
- g-qh's s438 scene (`-n 2`, first render geometry only) reads a count over the whole job; if its
  render #1 overflows the job is void by E773's rule and the held-out stage falls back on s275, which
  then separates fewer pairs (the scorer lists the survivors).

## 7. Commands the lead runs

```
export SGX_TARGET_HOST=jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
cd ~/src/scratch/resgx545/closing3/r3-geo-c
export PYTHONDONTWRITEBYTECODE=1
bash tests/run_all.sh                       # offline, all must pass
run/guard_r3.sh && run/freeze_r3.sh verify
SGX_DRY_RUN=1 run/stage_r3.sh               # prints the commands, builds nothing
run/stage_r3.sh                             # copies, checks the tool hash on the laptop
run/r3.sh                                   # stops at the first non-zero stage or health
PY=~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
$PY score/score_r3.py g-z out/g-z           # one SUMMARY a stage
$PY score/score_r3.py g-qf out/g-qf
$PY score/score_r3.py g-qh out/g-qh out/g-qf
```
