# r7-geo (round 7, session r7-geo of the ranking): prepared offline, NOT run

Built 2026-11-12, offline, frozen against resgx545 main **1c64f3a** and resgx545-data **830641e6** (neither moved; nothing here
touched the laptop, cachix or a git repository).  Plan: the ranking's proposed session in
`closing7/rank/rank-round7.md` (R7-2 to R7-5), user decisions `closing7/DECISIONS-R7.md` R7-2 (a) and R7-7 (a), with decision 4 (a)
(Q260's rivals) and the planner's recommendations for the smaller choices.  Offline records it starts from (main): E893 (Q142,
H-GRID, offline), E894 (TEXTYPE 5 stores no texel tag in E567's three jobs: the H-STEP image this session freezes), the Q260 note of
2026-11-12 (the tile-relative reading refuted offline: the sweeps below are the route it names).  Read `PREFLIGHT.md` before staging.

## What runs, in order (`stages.txt`), 628 jobs

| stage | jobs | tool | what | frozen | stop |
|---|---|---|---|---|---|
| xf | 10 | t4 | Q206's both-fields clause: 8 fills at 128 x 64 with the end-of-tile DOUTU1 x and y fields XORed together | H-INDEP vs H-XFIRST vs H-YFIRST (hash) | any fault |
| tx | 18 | t4 | Q283: types 1, 3, 4 at 4 x 16, 64 x 8, 128 x 8, type 4 at 64 x 32, 128 x 32; Q178: type 5 at 8, 16, 32, 64 and two memory controls | RASTERW (1, 3); S32 vs SMAXW, S2WCAP, RASTERW, RASTER2W (4); H-STEP vs H-FIX16 (5); H-STEP vs H-MEM | any fault; health after each job |
| zd | 102 | t4 | Q262 depth: E606's D jobs, 12 small + 12 medium at 512 x 256, 640 x 480, 1024 x 768, 2048 x 1024, 4 at 4096 x 4096 | H-E606, H-ZLS, H-DEPTH (3 U) | any fault; 2 soft failures in a row |
| zi | 26 | t4 | Q262 iteration: E606's I0 probe, 6 medium at each of the four sizes | H-E606, H-ITER (4 U) | as zd |
| zf | 242 | t4, t6 | Q240: D jobs on 64 x 128, 128 x 64, 256 x 64, 128 x 96, 128 x 144, 32 x 16, 16 x 8, 4096 x 16, 64 x 33, 96 x 47 (t6) | H-E606, H-ZLS, H-DEPTH | any fault; a gate refusal skips its size |
| zs | 230 | t4 | Q260: 17-step sweeps of 1/4096 across the tie at -0.5, -3.5, -64.5, +0.5, +64.5 and the far side (x and y), 24 non-tie cases | HU, HA, FAR, SETUP(c) fitted on the -0.5 x sweep | any fault |

Controls that can fail, each its record's own command and kept answer: xf E884's 128 x 64 x ^ 0x10 fill and baseline (kept hashes);
tx E725's ty3-32x16 program byte for byte (kept image) and type 5 at 16 x 16 (E567's image, E894); zd E606 cases 412 (64 x 64) and
1206 (256 x 128) (kept hash, triangle count, dump sha256); zi E606's I0 case 1016 (kept rows) and E680's 1024 x 768 case 1400246
(kept hash); zf E606 cases 262 (64 x 64) and 926 (128 x 128); zs E681's 1400606 and E683's 1401234 at 512 x 256 (kept hashes) and the
+0.5 x sweep (HU, E681).  Each control declares the readings it needs (`gen/data/controls.tsv`, checked by
`scorekit.refuse_unreadable`); on the laptop a control without them STOPS the stage (rc 25, `sessioncheck.py premise`).

**Predicted outcomes** (frozen in `predictions/`): xf H-INDEP; tx RASTERW for 1 and 3, S32 for 4 (E725 fitted it), H-STEP for 5 with
the memory controls unchanged; zd/zi/zf E606's coverage, the whole tile area written, depth within 3 U and pa0 within 4 U on every
size; zs: HU is predicted exact on the positive mirror and the controls; on the negative sweeps the rivals are open (E683 refuted HU
and left HA 101 pixels short): no rival is favoured, the fit picks c.  No fault is predicted anywhere (0 in E606/E680's 3700 jobs;
1556 fills of xf's poke; E725's 12 and E567's 15 risky texture jobs ran clean).

**Time**: about 60 minutes of jobs at E680's pace (about 5 s a job; tx's health after each job adds 3 minutes; the 4096 x 4096
depth jobs about 30 s each), about 75 minutes with staging and the health after each stage.  Stop budget: 0 faults (the first
stops the stage), 2 soft failures in a row, 2 rows without a hash.

## Retire / narrow on the verdicts (R7-7 a)

Q262 retires if every zd/zi size holds; Q240 narrows per decision 3 (odd widths, past 4096); Q283 retires if the held-out strides
hold at 4, 64 and 128; Q178 retires as "type 5 is not a texel layout" if H-STEP holds and the memory controls show no read
(decision 5 a); Q206's both-fields clause closes (Q206 stays: an umbrella); Q260: a rival exact on the held-out sweeps settles the
rounding; otherwise the STEP table (`score_g.py zs`) is the per-step table the simulator needs (a narrowing).

## Layout

- `tables/STAGE.txt` (`name|set|risk|knobs|tool|args`), `predictions/STAGE.tsv`, `TABLES.md`, `stages.txt`, `gen/data/controls.tsv`:
  written by `gen/g7gen.py` from `gen/models.py` (models), `gen/model1140.py` (byte copy of resgx545-data
  isp/coverage-envelope/recompute/model1140.py), `gen/r3_geo.py` (byte copy of round 3's), `gen/texbuild.py` and `gen/texcatalog.py`
  (byte copies of resgx545 tools/texture/p1132/gen/build.py and catalog.py), and the records it reads (`gen/data/sources.lst`)
- `bins/`: the probe programs (`bins/SHA256SUMS`), assembled with resgx545 1c64f3a's usse-asm (git archive in `debug/asm`); the
  three iteration programs equal E606's manifest, the texture control equals E725's stage-bin; `templates/` their sources
- `score/score_g.py` (the scorers), `score/scorekit.py` and `score/sessioncheck.py` (byte copies of resgx545 1c64f3a's)
- `run/g.sh` (Mac driver), `run/stage_g.sh`, `run/run_stage.sh` + `run/lib_g.sh` + `run/g.env` (the laptop runner),
  `run/freeze_g.sh`, `run/guard_g.sh`, `run/lib_check.sh`
- `bin/t6/sgxfive-test`: round 6's t6 (resgx545 d9b2969, sha256 97df5c0e..., the binary the lead built on cachix for r6-misc),
  for zf's 48 odd-height rows only.  Our own build, nothing firmware-derived; the fold may leave the binary out of the published
  copy (its hash is TOOL6.sha256 and r6-misc's)
- `tests/`: `run_all.sh` (all must pass), `test_gen.py`, `test_twin.py`, `test_scorers.py`, `test_replay.py`, `mock_all.py`,
  `run_mock.sh`, `worlds.py` (the argv-driven fake), `shims/`

Publishable: everything here (no firmware-derived file, no disassembly of closed code; the programs are our own sources).
**Nothing is marked for data-private.**  `debug/` is scratch (the archived assembler, mock builds, test outputs).

## Commands the lead runs

```
export SGX_TARGET_HOST=jtorra@10.42.0.2 SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"   # or local.env
cd ~/src/scratch/resgx545/closing7/r7-geo
bash tests/run_all.sh                       # offline, ALL TESTS: PASS
run/guard_g.sh && run/freeze_g.sh verify
SGX_DRY_RUN=1 run/stage_g.sh; run/stage_g.sh
SGX_DRY_RUN=1 run/g.sh; run/g.sh            # all six stages; after a stop: run/g.sh --from STAGE (a new attempt)
PY=~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
$PY score/score_g.py verdict out/ATT
```

## Deviations from the plan (all small; the lead may object before staging)

1. **Tool**: every row runs on `~/sgxfive-test-rgn4` (e6951558) but zf's 48 odd-height rows (64 x 33, 96 x 47), which the rgn4
   build refuses (`render: Invalid argument`); they run on round 6's t6 (97df5c0e), staged by `stage_g.sh` from `bin/t6/`, as
   r6-misc's q287 did.  No row needs odd widths.  The rgn4 tool has no `--pixels-rle`: zd prints `--pixels` up to 512 x 256 only,
   above which the hash, the triangle count and the depth dump decide.
2. **Q283**: Q283's widths 24 and 40 are not run (the map window maps power-of-two sizes only); its "128 x 64 fill for type 4 at
   32" cannot run (the probe fill is fixed at 64 x 32): type 4 at 64 x 32 and 128 x 32 instead.
3. **Q178 memory controls**: the program zeroes (sets) the texture's first 112 dwords before its sample, not the whole texture: the
   tool takes at most 256 USSE words a probe.
4. **Q260**: at 1/4096 the threshold 7/16 (H-T7) is half away from zero (HA): not a separate rival.  Each sweep aims through one
   pixel centre: 1 pixel from -0.5, +0.5 and the far side, 4 from -3.5, 100 from -64.5 and +64.5; target 512 x 256.
5. **4096 x 4096**: the 64 MB depth buffer is dumped and kept whole (gzip), not a window; the runner asks for 200 MB + 8 KiB a page
   free before such a row.
6. E606's I0 probes and E680's colour control are their own stage (zi): each stage's scorer reads one kind of file.
