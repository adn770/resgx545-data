# R4-A: Q285 rerun with controls of the stage's own shape (decision 10, reruns): prepared, NOT run

Built 2026-11-11, offline. Nothing here touched the laptop, cachix or a git repository.
Read `PREFLIGHT.md` before running.

## What and why

Q285 asks why the image is empty when `CR_TE_AA` bit 29 is clear and bit 30 or 31 is set.
E728 found that dwords 11 to 26 of the parameter buffer are then displaced by one zero dword.
K2 (R3K-pixel, E825) built stage k-pb to poke that stretch between the TA and the 3D,
gated by three controls in k-pb0.
The controls were frozen from E728's one-render jobs, but the stage ran K2's two-render shape
(`-n 2 --geometry 1`), so they failed by construction, the gate closed and k-pb never ran.
R3K-regress (E827) then ran both shapes on the new module: 7 of 7 one-render rows reproduced
E728, and 3 of 3 two-render rows gave k-pb0's value.

This session reruns K2's 8 jobs (the same row count, the same commands byte for byte).
The only change is the controls: they are frozen from the R3K-regress kept output of jobs of
the same shape (`pb-n40-a/b/c` at TE 0x40, `pb-n60` at TE 0x60, `-n 2 --geometry 1`, dump).

## The module and the knob (a deliberate choice)

Fork a2788bd8 (srcversion 99CD90DA26E3AFF9C450517) refuses a job whose TE_AA sets bit 31 or 30
on a context made without `DRM_SGXFIVE_CTX_RENDER_AA_4X` when `render_rgn_arrays` is 0, the
new default. Every row here sets TE 0x40000000 or 0x60000000, so every row needs either
`render_rgn_arrays` 1 or `--aa4`.

- **Chosen: `rgn:1`.** After the job's reset, the runner writes `render_rgn_arrays` 1 and reads
  it back. After the job it writes 0 and reads it back. The exit trap writes 0 at every exit.
  A forced 1 is the one-array layout that E728, K2 and R3K-regress measured. The fork's KUnit
  pins it, and the 2026-11-11 rgn4 laptop check reproduced E827's `ctl-a1-256x160-tee0` at
  forced 1 with the rgn4 tool: its hash, TA data and parameter buffer sha256 were byte-identical.
- **Not chosen: `--aa4`.** It gives four region-header arrays, so the TA data is different and
  no two-render value exists to freeze.
- **The control showing the old values reproduce:** a-pb0's three controls. They are the
  R3K-regress two-render jobs, rerun at rgn:1 on the new module with the new tool. All three
  must equal every frozen quantity, including the sha256 of the 4.6 MB parameter buffer.

The tool is `~/sgxfive-test-rgn4` (sha256 e6951558..., built from resgx545 r3-rgn4 4623753,
source sha256 703cbcea..., `TOOLSRC.sha256`). R3K-regress used `~/sgxfive-test-r1`. The source
diff between them (0675ca0..4623753) changes the tri path only in three ways:
- the context flags field, which is 0 without `--aa4`;
- the `ba` check for `--tri` slots, which these rows do not use;
- the `--aa4` echo.

So the job words are the same [infer, from the source diff]. The a-pb0 controls test this.

## Stages and rows (8 jobs)

| stage | row | set | TE | what |
|---|---|---|---|---|
| a-pb0 | pb-d0-te40 | control | 0x40 | the dump run (E728's empty image, the stretch at 11-26) |
| a-pb0 | pb-p0-te60 | control | 0x60 | the twin (full image) |
| a-pb0 | pb-p1-te40 | control | 0x40 | d0 again; its parameter buffer must equal d0's |
| a-pb | pb-p2-own11 | control | 0x40 | poke dword 11 with its own value 0 |
| a-pb | pb-p3a-twin | **held out** | 0x40 | poke the twin's dwords 11-25 and 0 at 26 (16 pokes) |
| a-pb | pb-p3b-twin | replicate | 0x40 | as p3a |
| a-pb | pb-p4a-ffff | **held out** | 0x40 | poke dword 11 = 0xffffffff |
| a-pb | pb-p4b-ffff | replicate | 0x40 | as p4a |

Every row is `tri --tri-full --keep-going --wait-ms 20000` at 64 x 64,
`-n 2 --geometry 1 --poke cmd:1=TE --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002`
`--poke cmd:16=0xeaa26e26 --dump-render "$W/dump"`, plus the row's
`--kpoke-render 2:par:N=0xV`, with knobs `rgn:1 expectdiff`.

The pokes are armed before render 2. They land after render 1's geometry-only kick and before
render 2's own TA. So they change render 1's object (dwords 0-26), and render 2's TA then
appends its own object from dword 27 (the second stream header 04000004 at dword 27 in R3K-regress
pb-n40). [infer, from the fork's commit 8fc748b0 and the kept dumps]

## Controls and their frozen values (`predictions/a-pb0.tsv`, `a-pb.tsv`)

| control | frozen from (R3K-regress, E827) | target hash | diff | parameter buffer sha256 |
|---|---|---|---|---|
| pb-d0-te40 | pb-n40-a (= b = c) | 0x8ea26cdfee74a325 | 3969 of 4096, first (1, 1) 0xff000080 | b8ada427... |
| pb-p1-te40 | pb-n40-a, and = d0's in-session | 0x8ea26cdfee74a325 | as d0 | b8ada427... |
| pb-p0-te60 | pb-n60 | 0xd2bfb75560f4c325 | 0 of 4096 | 1f00f101... |
| pb-p2-own11 | pb-n40-a; = d0's in-session | 0x8ea26cdfee74a325 | as d0 | b8ada427... |

Each control also compares:
- the return code, the size echo and the geometry-only line;
- the render 2 line and the `renders ok` line;
- the TA data sha256 (8ec0ebc7...) and the dump sizes;
- dwords 0-63 of the parameter buffer;
- the kernel's `kpoke ... applied` lines: none for a-pb0, exactly `par:11=0x00000000` for p2;
- for p2, what debugfs `kpoke` still holds after the job, which must be nothing.

`tests/test_gen.py` checks that:
- every value is the kept file's;
- the three regress TE 0x40 replicates agree;
- no control hash is a one-render value.

## Hypotheses (K2's, kept) and the decision (`score/score_a.py`)

- **H-OLD**: the 3D reads the stretch in the old layout. p3 gives the twin's picture, and
  p4 draws nothing.
- **H-FIELD**: dword 11 is a field the 3D uses. p4 draws triangle pixels, and p3 is not the
  twin's picture.

Readings:
- **p3 "twin"** is diff 0 of 4096 with render 2 at `4096 triangle, 0 background, 0 other`.
  Any other completed reading with all 16 pokes applied is "not twin".
- **p4 "drawn"** is render 2 with more than 0 triangle pixels. "Empty" is 0 triangle and
  0 other. 0 triangle with other pixels is read and matches no hypothesis, and the scorer says
  so.

A row has no reading in these cases:
- a void job;
- class not ok;
- pokes not all applied;
- an overflow or tool failure message anywhere in the output;
- no render 2 line.

The decision, with the four controls (a-pb0's three and p2), uses scorekit (a byte-for-byte
copy of main 6421c1c's, last changed in eb84f54):
- **The controls gate every row.** Any control that is not PASS, whether FAIL or NODATA, gates
  every row: "controls FAILED" or "cannot tell: controls".
- **Replicates.** Each pair goes through `combine`. Replicates that disagree are mixed, never held.
- **Outcomes:**
  - p3 twin and p4 empty: H-OLD.
  - p3 not twin and p4 drawn: H-FIELD.
  - Both empty: cannot tell, park under Q030.
  - Twin and drawn: cannot tell, both effects.
  - Anything else: cannot tell, naming the mixed pairs, the rows with no reading, and the rows
    read that matched no hypothesis.
- **Headline.** A headline states how many of the 4 rows decided.

**Records that contradict K2's frozen k-pb values** (the hypotheses stay):
1. K2's p3 H-OLD froze target hash 0xd0530839d87ea325. That is the twin's one-render value, and
   K2's scorer required it for "twin". E825 and E827 give the twin's two-render hash as
   0xd2bfb75560f4c325. E825 also notes that the hash is not a function of the picture alone.
   Render 2's own object keeps the TE 0x40 layout even when p3 succeeds. So the hash is reported
   against 0xd2bfb75560f4c325 and never decides; the picture decides.
2. K2's p0 froze dword 26 = 0, which was also one-render. In two renders it is 0x04000004, the
   next object's header (E825). It is frozen from pb-n60 here.

If render 2's 3D did not draw render 1's object, p3 would read not twin and p4 empty: "cannot
tell, park under Q030". That is never a false H-FIELD or H-OLD.

## Stops

- **Fault limit 1.** The first fault, hang, timeout or unexplained failure ends the stage, then
  a reset and the health check (a fill and a triangle) run, and the runner exits 4.
- **Fatal kernel messages and freezes.** A fatal kernel message exits 3; a job that does not
  return exits 6. In both cases nothing runs but the knob restore.
- **A knob that does not read back** (1 before a job, 0 after it) exits 19.
- **The gate.** a-pb runs only if a-pb0's three controls pass. The gate is computed from the
  kept a-pb0, and a closed gate skips a-pb cleanly.
- **K2's warning:** a garbage dword 11 (p4) may hang the ISP. Then p4b does not run, and p4
  cannot tell.
- **What the lead decides.** After any stop the lead decides: no reboot, no unload, no register
  write.

## Layout and commands

`gen/agen.py` (extract, build) writes `gen/data/ctl_values.tsv`, `tables/`, `predictions/` and
`TABLES.md`. The scorer is `score/score_a.py` with `alib.py` and `scorekit.py`. The runner is
in `run/`:
- `run_stage.sh` and `lib_k.sh` run on the laptop;
- `k.sh` is the driver;
- `stage_k.sh` stages the files;
- `freeze_k.sh` freezes and verifies;
- `guard_k.sh` is the session's guard;
- `lib_check.sh` holds the shared checks.

`gen/frozen_commits.py` writes `FROZEN.commits` with resgx545's `tools/records/frozen.py`. The
tests are in `tests/`. Laptop directories: `~/r4a-run`, `~/r4a-out`.

```
export SGX_TARGET_HOST=jtorra@192.168.12.234
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
export PYTHONDONTWRITEBYTECODE=1
export PY=/Users/jtorra/src/resgx545/.venv/bin/python
cd /Users/jtorra/src/scratch/resgx545/closing3/r4-reruns/a-q285
bash tests/run_all.sh                 # offline: ALL TESTS: PASS
run/guard_k.sh && run/freeze_k.sh verify
SGX_DRY_RUN=1 run/stage_k.sh && SGX_DRY_RUN=1 run/k.sh
run/stage_k.sh                        # copies, compares, checks the tool hash
run/k.sh                              # the session (a-pb0, gate, a-pb)
$PY score/score_a.py verdict out/ATT  # the Q285 SUMMARY line
```

`run/k.sh --only a-pb0` (a new attempt directory) reruns one stage, and `run/k.sh --from a-pb`
continues after a stop.
