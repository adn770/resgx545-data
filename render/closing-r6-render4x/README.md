# r6-render4x stage A (H-TPM held out; Q293's four rows): prepared, NOT run

Built 2026-11-12, offline. Nothing here touched the laptop, cachix or a git repository. Frozen
against resgx545 main **d9b2969** (`FREEZE.txt`, `FROZEN.commits`). Read `PREFLIGHT.md` before
running. Plan: `/Users/jtorra/src/scratch/resgx545/closing6/render4x/exp-render4x-r6.md` section 2
(stage A) and section 5 (Q293), decisions `closing6/DECISIONS-R6.md` R6-2 (a) (stage A on the rgn4
boot as it stands, last of the four round 6 sessions before the reboot), R6-5 (a), R6-6 (a) and the
plan's decisions 1 (a), 5 (a), 7 (a). Stage B (the new kernel) is NOT built: it is a second freeze
added later (section "Stage B" below). Base: `closing5/r5-render4x` (published
`render/closing-r5-render4x`).

## What runs, in order (`stages.txt`)

| stage | jobs | what | predicted | fault limit |
|---|---|---|---|---|
| s0 | 3 | r5's controls (E827 ctl-u-1024-n1, E828 j1r, E824 h8; all PASS in r5) | pass | 1 |
| a | 13 (12 if a1 faults) | H-TPM held out: a4 premise; a1 (+ a1r), a12, a13, a8, a9; a2, a3, a5, a14; h1, h2 held | 6 faults (a2, a3, a5, a14, h1, h2) | 8 |
| t | 4 | Q293: t8 control (r5's t6); t5, t6 CR_TE_AA 0xc0000000 on the 11.31 line and point; t7 the 0x40 triangle with 0x00000001 poked into dword 11 | no fault | 1 |

**20 jobs** (the plan's 16 of stage A incl. a1's replicate, plus Q293's 4), plus the health pair at
each stage's begin and end and after each fault. Order: the main rows before Q293's rider (t7 is a
new poke value; a stop there must not cost stage a). **About 15 minutes on the laptop; plan 30.**

## Hypotheses and verdicts (`score/score_r.py`, frozen)

- **H-TPM (a)** [E870, a post hoc fit on E869's one dump]: a four-array 4x job faults iff
  4 x (Z(2tx - 1, 2ty - 1) + 1), Z the interleave with y on the even bits, passes the `td.rgn` of
  its context's maximum; a held fault loses exactly the stream offsets `rules.lost()` names. Held
  out on 11 rows: a1, a12, a13, a8, a9 complete where K-OR (and the other dead rules that fit
  E845) fault, a2, a3, a5, a14 fault, h1 and h2's lost sets compared AS SETS with the frozen
  `predictions/h.tsv` (h1: 43 headers 0x7000 to 0x7ab0, header 0 among them; h2: 511 headers
  0x7ffc to 0xc7f0, header 0 intact); verdict words `set equal (N)` or `both B, lost only L,
  predicted only P`. a4 is the premise (1024 x 768 on 2048 x 1024 completes at the limit): a
  fault there stops the stage. a1r replicates a1 only after a completion; disagreeing replicates
  are mixed (scorekit), never held. H-TPM's seven other variants (x on the even bits; the limit at
  the room's end, OTPM or state page) and r5's eleven dead rules are frozen beside it per row
  (`rule:*`, set `compare`): the verdict names those no decided row contradicts. Explore (reported,
  never scored): word-0 losses, bit 27, flags 0x04 and 0x10 in the held dumps, h1 against a9 (its
  completed twin on a larger maximum) header by header, the right pixels of the faulting rows.
- **Q293 (t)** (reworded Q293 on main): t5, t6 insert one zero dword right before the format word
  (dword 9 of the line, 11 of the point) and draw nothing (H-PAD; H-FIELD would be non-zero),
  compared with the frozen heads of the kept 11.31 dumps (r5's t3b, t4b equal them); t7: the
  kernel's `kpoke par:11=0x00000001 applied`, dword 11 the poked value, render 2 draws nothing
  (E829's p4 counts, H-OLD). t8 (r5's t6, E827's row) is the control.

## Round 4's and 5's slips: impossible by construction

- **The mock answers by argv** (`tests/worlds.py`): never a case name; held dumps are synthesized
  from the argv with the world's lost set and word-0 noise; t7's poke value is read from the argv.
- **The argv twin** (`tests/test_twin.py`): every row's command against its plan row typed from the
  plan (triangle, mode, size, maximum, TE word, render count, geometry, poke, knobs, held). It
  fails round 4's o2, a8 on its own size, t5 without rgn:1, t7 without its poke or as one render.
- **Replays before the freeze** (`tests/test_replay.py`): on E869's dump the set reader gives set
  equal (1023); it must fail and does on h2's set, the x-even set, m1's completed dump and r4's
  error-text dump; r5's 14 decided rows agree with H-TPM 14 of 14 and contradict K-OR; r5's t3c,
  t4c, t3, t4 hold as t5/t6; r5's t3b and t4c fail; E829's p4a holds as t7 with its own value,
  p3a fails; r5's t6 passes as t8 and E829's p2 fails.
- **Laptop files** (HACKING.md, round 6 brief): everything under `~/scratch/r6x/{run,stage,out}`;
  one `mktemp -d ~/scratch/tmp/r6x.XXXXXX` a stage (sudo drops TMPDIR), each job's work directory
  removed once its files are kept, the mktemp directory removed at every exit (an early trap too);
  `rm` only in those three forms (guard); at least 300 MiB free on ~ at the preflight and before
  each job, else rc 21. **r5-render4x's runner used a bare `mktemp -d` (laptop /tmp) and removed
  nothing: fixed here** (its leftovers are the lead's, PREFLIGHT 0).
- **No start-up timing in the mock**: the fake sudo's `regs` read during a held job waits until the
  fake tool has answered (a line in `answered` per case marker); `run_mock.sh` runs stage a with a
  fake that answers 3 s late and HOLD_READ 0.2 s and still reads both held faults and h1's set.

## Stops

- s0, t: the first fault, hang or unexplained failure ends the stage (rc 4) after strict health.
- a: a4 (no hypothesis knob) faulting stops at once (rc 4). Every other row's fault with E845's word
  is measured; after the 8th fault-class event with rows left the stage stops (rc 15). a1 faulting
  is the refutation, not a stop (a1r is then skipped).
- Any fault whose BIF_INT_STAT bits 15:0 are not 0x0100 or whose BIF_FAULT is not 0x10000011, or a
  "recovery failed: -110": rc 18. Strict health after every fault-class event (rc 16).
- Free space below 300 MiB on ~: rc 21 (before anything is touched or before the job).
- Knobs not reading back rc 19; the driver's rc 42 if a knob is not at its default after a stage.
- Any stop ends the session; after a stop: no reboot, no module unload, no register write. The
  lead decides (`run/k.sh --from STAGE` is a new attempt).

## Layout and commands

`gen/rgen.py` writes `tables/`, `predictions/` (s0, a, h: the lost sets, t), `TABLES.md`,
`stages.txt`, `bins/` (the line and point programs, equal to r5's published ones), `gen/data/`
(twins, the 26 recorded cells with each variant, the source list). `gen/rules.py` H-TPM, its
variants and the eleven dead rules; `gen/rlib.py` readers (dump names, header rule, lost offsets by
header position, probe image, kpoke lines); `score/score_r.py` the scorer (`score/scorekit.py`
byte for byte main's). `run/`: `run_stage.sh`, `lib_k.sh`, `k.env` run on the laptop; `k.sh` the
driver; `stage_k.sh` stages; `freeze_k.sh`, `guard_k.sh` the freeze and the session's own static
guard; `sets/A.env` this freeze set. `tests/run_all.sh` runs every offline test (exits 0).

```
export SGX_TARGET_HOST=jtorra@192.168.12.234
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
export PYTHONDONTWRITEBYTECODE=1
export PY=/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
cd /Users/jtorra/src/scratch/resgx545/closing6/r6-render4x
bash tests/run_all.sh                 # offline: ALL TESTS: PASS
run/guard_k.sh && run/freeze_k.sh verify
SGX_DRY_RUN=1 run/stage_k.sh && SGX_DRY_RUN=1 run/k.sh
run/stage_k.sh                        # copies to ~/scratch/r6x, compares, checks the tool hash
run/k.sh                              # the session, stage by stage (gates, scores, health)
$PY score/score_r.py verdict out/ATT  # the SUMMARY lines (several ATT after a --from)
```

## Stage B: a second freeze, added later without touching stage A

Stage B (plan section 4: the `render_tail_room` debugfs knob, 20 jobs, 3 predicted faults) runs on
the new kernel after the reboot. It is added as **freeze set B** and changes no file of set A:

- `sets/B.env` names its own stages file (`stages-B.txt`, stage names distinct from s0/a/t except a
  shared `s0` gate if wanted), freeze `FROZEN-B.sha256` + `PREDICTIONS-B.sha256`, tables
  (`tables/b*.txt`), predictions, scorer (`score/score_b.py`, importing `score_r` helpers),
  runner directory (`run-b/`: a copy of `run/lib_k.sh`, `run_stage.sh` with the `room:0xNNNN` knob
  writing `render_tail_room`, restored to 0 after each job and by the trap, and `k.env` with the new
  module's srcversion and the plan's preflight file `render_tail_room`) and guard
  (`run-b/guard_b.sh`, allowing that one write). Its generator is a new file (`gen/rgen_b.py`).
- `run/freeze_k.sh freeze B`, `run/stage_k.sh --set B`, `run/k.sh --set B` take it; set A's
  `freeze_k.sh` lists its files by name (`sets/A.env set_files`), never by glob, so B's files are
  outside A's freeze, and a set's freeze is never rewritten. Laptop: B's runner goes to
  `~/scratch/r6x/run/run-b/`, its freeze file beside A's; the same `out/`.
- `tests/run_mock.sh` section 7 does exactly this with a fake set B in a tree copy: B freezes,
  stages and runs (its gate reading A's s0), A's `FROZEN.sha256` and `PREDICTIONS.sha256` stay byte
  for byte and verify, a second `freeze A` is refused, B's table under A's freeze is refused.
- If stage A cannot run before the reboot, the plan's fallback (A's rows on the new kernel with
  `render_tail_room` set to the old room) needs set B's runner; A's frozen predictions stay valid.

## Deviations from the plan

1. **Order s0, a, t** (the plan does not fix where t5-t8 ride): the held-out rows first, the Q293
   rider last, so a stop on t7's new poke cannot cost stage a.
2. **t7's value is 0x00000001** (the plan says "a non-zero value"; E829 p4 had 0xffffffff).
   **t7 has no in-session own11 control** (the plan's four rows); t8 is the plan's control.
3. **t5 and t6 compare with the frozen heads of the kept 11.31 dumps** (no in-session baselines:
   the plan's four rows); r5's in-session baselines equalled them (E865), and t8 can fail.
4. **The a + h limit of 8** is one stage `a` with h1, h2 last, so the budget is shared as planned;
   a1 and a1r form their own hypothesis group (at most 1 event: a1r runs only after a completion).
5. **"All ten a rows"**: a4 is scored as the premise control, the other nine plus h1, h2 are the 11
   held-out rows of the headline; a1r is folded into a1 by scorekit's replicate rule.
6. **300 MiB** free-space floor (the plan's figure; the brief's minimum is 200).

## Publishable

Everything here is our own: generators, scorers, runners, tests, tables, the twins table and the
recorded-cells table (read from published datasets and the planner's offline scripts' formulas),
and the two programs (built from `probes/ta/p1131-progs.toml`). **No firmware-derived file**:
nothing goes to data-private. `debug/` is scratch (the mock tool build, test work directories) and
is not part of the session.

**Stage B is built**: see `README-B.md`, `PREFLIGHT-B.md`, `FREEZE-B.txt` (set B, frozen after stage A ran).
