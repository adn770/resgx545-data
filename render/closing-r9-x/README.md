# r9-x

Round 9's session r9-x (decision R9-2 (a), `closing9/rank/rank-round9.md` section 2, records
E975-E979), built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 f32dfacc8db8, data 2d666bfafa21. Laptop prefix `r9x`,
module B60AB0B475DD1E8972419B5 (fork 2a650d74, as it runs since 03:11), tool t4 =
`~/sgxfive-test-rgn4` (sha256 e6951558..., built from resgx545 4623753
`userspace/libsgxfive/tools/sgxfive-test.c`, sha256 703cbcea..., `TOOLSRC.sha256`; its rows are
replayed on that source's library mock by the kit). No knob, no kernel change, safe class only.

## What runs, in order (66 jobs, about 10 minutes of jobs, 30 to 35 with staging and health)

| Stage | Plan | Questions | Jobs | Controls (can fail) | Frozen | Record |
| --- | --- | --- | --- | --- | --- | --- |
| t3 | R9-A | Q078 | 19 | E566 s64x32-ctl, s64x32-t3b14; E564 an-ctl (kept images) | bit 14 per pixel: H-UCOL, H-U01, H-URAW on 6 held-out geometries, each with its bit-14-clear reference (H-TEXMODEL); bits 11/12 E566/E564 replicates | E975 |
| srgb | R9-B | Q282 | 8 | E723 g-bl-st-a (kept image); eq (equal corners) | per pixel H-HALF2, H-BF11 (a, b fit; c held out) | E976 |
| zls | R9-C | Q242, Q243 | 16 | the 3 format-0 jobs (E831 count); E467's load | per dword H-ROUND/H-FLOOR, H-E490/H-SLOT512; drawn counts H-INT/H-RAW, IEEE/NaN-pass/inf-zero | E977 |
| zst | R9-D | Q120 | 12 | format 0 at both sizes (depth and E467's stencil copy counts) | formats 4, 7 H-SCALE vs H-NONE; 3, 5, 6 a reading table | E978 |
| far | R9-E | Q199, Q261 | 11 | E684's far21d0 (exact there) | per pixel H-EXACT, H-SAT, H-WRAP, H-CULL | E979 |

Each stage's header (`tables/STAGE.txt`) and generator (gen/STAGE.py, gen/zls.py for zls and
zst) say what each row tests; `predictions/STAGE.tsv` and `predictions/STAGE/NAME.MODEL.txt` are
frozen with the session. The scorer prints one SUMMARY line per frozen model per stage.

Stops: any fault or hang in any stage (no row is `expectfault`; `#limit 0`); a control without its
reading (premise, 25); a probe row without its 32 pixel rows or a tri row without `job: ok`
(hook_check, 24: the stage stops, the next stage runs); free space under 300 MiB (22). far runs
last: E684 stopped at 2^21 pixels, so far's rows are a new range [infer: a vertex the TA cannot
hold is clipped or culled, not a fault]; its first fault stops the session (4).

## Deviations from the plan, from its three dry-run checks (lead/dryrun_checks.out)

1. **R9-D, Q121 dropped (check 1).** Its rows need ISP word 2 (a stencil operation) together with
   the ZLS stencil buffers. Tool t4 sets ISP word 2 only in `probe --tri` (`--isp2`), which has no
   `--stencil` buffers, and `tri` has the buffers but refuses `--isp2` (`bad option --isp2`). A
   `--poke blk:` emulation would have to move the state block's words 3 to 11, two of them GPU
   addresses: not done. zst runs Q120 only (12 jobs in place of 16); the stencil pattern Q120
   needs comes from E467's load (bits 1 and 13) of a stencil buffer filled with each dword's
   index. Q121 needs a tool change (`tri --isp2`, test first) in a later round.
2. **R9-E, `--tri-unit 0` refused (check 2).** t4 takes `--tri-unit` 5 to 20 and `--tri-v` values
   in [-2^30, 2^30). The rows use unit 5 (1/32 pixel): +-2^22, +-2^23 and +-2^24 pixels both ways
   and -2^25; the plan's 2^26 (and +2^25) are out of reach. The plan's two tie rows (a far vertex
   at 2^20 + 1/512) are dropped: a 1/256 move of a vertex 2^20 pixels away moves the edges inside
   the target by about 2.4e-7 pixel, far inside E684's 1e-3 band [infer]. The far vertices carry
   a large second coordinate where the 24.8 clamp and wrap would change an edge's direction, so
   H-SAT and H-WRAP are separable (tests/test_gen.py). far has 11 jobs, not 13.
3. **Check 3 (R9-A scratch extents)** holds: every rival's highest dword is below the pages the row
   maps (16, b14-w32s128 19; tests/test_gen.py). t3 has 13 jobs (the plan's 12 plus E564's an-ctl
   as the twiddled rows' control).
4. zls has 16 jobs (the plan's 17): Q243's integer-format loads are one job each (a constant fill
   that separates H-INT from H-RAW under less), NaN and infinity under less and greater, plus
   E467's load as a control; Q242's controls are the three format-0 jobs (E490's 1024 x 768 job
   not rerun).

## Replay vectors (HACKING.md "Replay vectors")

| Stage | Vectors table (closing_tables.py, `sgx545-tables`) | replay |
| --- | --- | --- |
| t3 | `t3-bit14` (pixel, model dword per rival, kept dword) | sgx-sim texture sampler: refused until the fold lands the bit-14 rule (no sampler path models T3 bit 14) |
| srgb | `srgb-bilinear` (corners, weights, kept halves) | refused: Q282's arithmetic is the fold's fit; the table feeds its sgx-pipe test |
| zls | `zls-int-formats` (dword, format-0 float, kept 24/16-bit) | sgx-pipe `zls::encode_depth` / `dword_sets` test once the fold widens RAMP_DEPTH and the G = 33 refusal |
| zst | none (reading table; Q120 layouts undecoded) | refused |
| far | `isp-far-vertex` (vertices, kept coverage) | sgx-pipe `isp` coverage test (the fold sets what it refuses past 2^21, E684) |

The freeze pins every input those replays read (session.toml `[freeze] pins`).

## Commands

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (it has pytest and numpy), which
  the offline tests use unless `PY` names another; never a scratch venv of an older session.
- Generator: `python3 gen/make.py` (`--check`: current or not).
- Dry-run checks: `bash lead/dryrun_checks.sh` (library mock only).
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py).
- Score: `python3 score/score.py STAGE KEPT_DIR`.

Mock worlds (`mock/world.py`): model (all 0), nopix (t3 and srgb stop 24, the rest run), nodepth
(premise 25 at zls), rejected (`job: rejected` with a diff line: 4 at zls), farfault (4 at far).

Nothing here is firmware-derived; every file may go to resgx545-data.
