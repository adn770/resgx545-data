# r7-rp (round 7, area render/pixel: Q293, Q291, Q287, Q276, Q139, Q086): run once

Built 2026-11-12, offline, against resgx545 main **1c64f3a** and resgx545-data **830641e6** (not
moved; `FROZEN.commits`). Nothing here touched the laptop, cachix or a git repository. Plan:
`closing7/a/exp-pixel-r7.md`, every decision (a) (`closing7/DECISIONS-R7.md` R7-2, R7-3, R7-5;
the plan's own decisions 1 to 10 (a)). Offline records it starts from: **E897** (Q293: render 2's
own object in 13 kept dumps, post hoc) and **E898** (Q291: `probes/pds/templates/pix_posstore.s`,
sgx-sim 2048 of 2048). Read `PREFLIGHT.md` before staging: **the lead builds t7 on cachix first**.

## What runs, in order (`stages.txt`), 143 jobs

| # | stage | jobs | tool | question | frozen prediction | fault limit |
|---|---|---|---|---|---|---|
| 1 | s0 | 4 | t4, t6, t7 | session gate | default 64 x 64 triangle exact with each tool; E831's z-ctl-34x18-y (t4) stores 924 | 0 |
| 2 | q287 | 25 | t7 (t4, t6 controls) | Q287 odd widths, H 18 | rule A (x + 0.5 < 1.25 W) vs FLOOR, ROUND, CEIL, RSTRICT; W 20 poke twins H-SCR vs H-VP | 1 |
| 3 | q291g | 1 | t6 | Q291 gate row | 32 x 16, 512 slots: value = the slot's position, lane tag | 1 |
| 4 | q291 | 26 | t6 | Q291 attribute band | H-BAND (the depth band) vs H-TARGET, H-TILE; values H-LIN; twins rule A | 1 |
| 5 | p7-rdc | 14 | t4 | Q276 bridge (R6's controls) | R6's gate (c-e709 G-o4, c-u >= 0.98, c-ow, c-rd-0 >= 0.95, c-prd-0 lanes) | 1 |
| 6 | p7-rd | 34 | t4 | Q276 readback | H-MOD4: S S S A0 A4 A4 A4; x-rd-6/7 o2's/o3's word, n-rd-5 o1's; clean rows | 1 |
| 7 | q293 | 4 | t4 | Q293 render 2's object | u1 objects at 0, 27, 54 and 0 triangle; u2 = E888's t7; u3 4096; u4 0 | 1 |
| 8 | q139 | 24 | t4 | Q139 TA dumps | replication of the kept maps; H-MOVED vs H-INPLACE on the fit rows | 1 |
| 9 | q086 | 11 | t4 | Q086 axes, last | H-COV vs H-X, H-Y, H-AREA (four new rows, 2 vs 2 each); bridges | **6** |

**Faults predicted: 5, all in q086** (the FX bridge and the four new-size rows, 3D side,
budget 6); none elsewhere (a fault in any other stage stops the session). Expected time: **about
25 minutes of jobs** (q139's 640 x 480 rows and q086's 1024 x 768 the longest), **50 minutes
planned** with staging, health after each stage and the gates.

Driver gates (`run/r7.sh`, from the kept files): **s0** failing stops the session (exit 40);
**q291g** failing skips q291 (the plan's rc 24: Q291 cannot tell), the session goes on; **p7-rdc**
failing skips p7-rd, the session goes on. Runner clean end: **q287 rc 21** when the odd width is
refused (the gate row `z-dry-33x18`): its odd-width rows (`oddw`) are skipped, the even-width
controls and the three W 20 poke twins still run, the session goes on. **q086 rc 19** when the FX
bridge completes (E886 then depended on the old module; its four rows are not scored). Every other
non-zero runner status stops the session; the lead decides (no reboot, no unload, no register
write). Stop codes: `run/run_stage.sh` header, `PREFLIGHT.md` section 5.

## Hypotheses, controls, verdicts (frozen: `predictions/`, `score/`)

- **Q287** (`score/score_q287.py`): per row the stored set (count and sha) under A, FLOOR, ROUND,
  CEIL, RSTRICT; counts at H 18 as `closing7/a/q287/oddw_cells.out` (W 19 A 528 / FLOOR 506,
  W 35 968 / 946, W 7 198 / 176, W 11 308 / 286, W 23 638 / 616, W 43 1188 / 1166, W 51 1408 /
  1386). Verdict over 9 held-out cells (replicates combined; a disagreeing pair is mixed, never
  held). Controls that can fail: three 924s (t4, t6, t7 at 34 x 18; a t7 that changed an even
  width fails), the t7 y ramp, the gate row (902, A = FLOOR there), dead 0. Twins (W 20, no
  favourite, gate nothing): `cmd:9=0x00110012` (MTE screen 19 x 18) H-SCR 528 / H-VP 550; viewport
  `blk:6`, `blk:7` = 9.5 the reverse; both 528 under either. Replays: E831's g-z (A and FLOOR 10
  of 10, ROUND and CEIL refuted 10 of 10, RSTRICT 6 of 10) and E885 (A 7 of 7, the others 7 of 7
  refuted); a renamed dump is cannot tell.
- **Q291** (`score/score_q291.py`): valid set = slots whose dword 1 changed; exact set equality.
  H-BAND / H-TARGET / H-TILE: 20 x 12 375 / 240 / 512, cut-x 34 x 16 160 / 32 / 512 (table in
  `TABLES.md`); all 12 held-out P rows separate H-BAND from both rivals (tested). Values: P
  dword 1 = f32(x + 0.5), dword 2 = f32(y + 0.5); V clip x within 23 units of 2^-23 (E661), clip z
  within 4 (a weak check: the plan's V shape has no `--tri-z`, z = 0). Controls: the gate, the
  `pix_pa0` image, the cut-triangle controls (64 x 16, 32 x 32), V at 32 x 16, the in-target slots
  of every row. Depth twins (rule A at 20 x 12 .. 10 x 6: 375, 330, 300, 225, 84): a miss marks
  the size "no depth reference". Programs (`bins/`): `pix_posstore.bin` = E898's landed template
  assembled with the landed usse-asm (8a136e52...), `q291_pos.bin` E437's kept bin,
  `q291_vtx.bin` the landed `pds_iter_nofetch.s` with DOUTI0 0x20400800 (E606 kept no binary;
  the same route rebuilds E437's bin byte for byte), `vtx_attr_zx.bin`, `pix_pa0.bin`.
- **Q276** (`score/score_rd7.py`, `rd7model.py`; R6's modules copied as `rd_*.py`): own-source
  words, class L when L >= 0.85 of them in both jobs and every other class <= 0.02, fewer than 300
  own-source words is cannot tell; clean rows by R6's original rule (0.90 of all TRI), cl-p4 by
  R6's lane rule. A replicate whose top label differs from R6's is not replicated (void). Replay
  on R6's kept p6-rd: gate passes, vector S S S A0 A4 A4 A4, own-source counts equal
  `fold/posthoc_r6.txt` A (0.903 to 1.000, rivals 0); a doctored rd-5 must not read H-MOD4 and
  does not. H-STORE at any of o4..o7 reopens Q276 (E878's post hoc paragraph would need an
  appended correction).
- **Q293** (`score/score_dump.py`): u1 control first (`-n 3`, two geometry renders); u2 = E888's
  t7 byte for byte, frozen against its kept dump head (dwords 0 to 63), image and hash
  0x8ea26cdfee74a325; u3 16 kpokes `3:par:38..53` (E829's p3 words shifted by 27; KPR_MAX is 16,
  exactly at the limit) -> 4096 triangle pixels; u4 `3:par:38=0xffffffff` -> 0. u3, u4 are
  cannot tell unless every poke is applied and seen in the dump. Replay: E888's t7 (holds), t8
  (fails), E897's 13 dumps.
- **Q139** (`score/score_dump.py`): the datasets' commands token for token plus `--keep-going
  --dump-render` (deviation 2). Builder's picks: fit `m2-B2-24` (B2 at B3, exact, missed by E877),
  held out `m2-B2-28` (past B3, inside the 30 tile rows), bit 31 `640x480 m1-flag0` (0x02010018).
  `score q139` reads controls, replication and H-MOVED on the fit and replicate rows only; the
  held-out rows are read only by `score_dump.py q139-heldout KEPT MODEL_SHA` after the fold has
  fitted and hashed a placement model (`q139-fitdata` prints the fit rows' header slots).
- **Q086** (`score/score_q086.py`): bridges R 1024 x 768, U2 320 x 160 (completes), FX 320 x 160
  (faults: `expectfault`); then per size R control and its U2 row: 448 x 160, 320 x 224, 416 x 192,
  384 x 208 (`hypo:cov:4`: nothing skipped). A poked row counts only if its R completed with 0
  wrong and FX faulted on the 3D side. Replay on E886's 10 kept rows: H-COV 9 of 9 (and H-X, H-Y,
  H-AREA 9 of 9: why E886 could not separate them), H-ANY 6 of 9. Summary ends "11 unrun E886
  rows not pursued, by design".

## Offline check the lead asked for: depth buffer at odd widths

`tri --depth` sizes its buffer from `--depth-pages N` when given (else `depth_min_pages` = W x H
dwords + 16); the tool's only W-dependent check is N >= W x H dwords. The store is tile-major at
CR_ISP_ZLSCTL's pitch (0x17100c: G = 1, two tiles a row; `zls.rs` store_dword), independent of
W's parity and of the colour buffer's padded pitch (checked in the t4/t7 mocks: the buffer is N
pages, the kpokes ta:7, rd:1, rd:11, rd:12, rd:13 are the same at W 19, 51, 7). Every depth row
here passes **N = 18 at H 18** (2 tile rows x 2 tiles x 2 KiB + 16), the q291 twins N for their
tile extent + 16; `tests/test_q287.py` asserts N >= extent + 16, N >= the tool's minimum and
1.25 W <= 64 for every depth row, and the scorers index the dump at pitch G + 1, never ceil(W/32).
**So the rows do not depend on `depth_min_pages`; no tool fix is needed before the freeze.**
Finding [infer] for a later tool commit (tests first): `depth_min_pages` (W x H) is below the
store's extent whenever the tile rows x (G + 1) tiles exceed it (t7 accepts `--depth-pages 1` at
19 x 18, where the store reaches dword 1024+): a default or small N can let the store run past
the buffer at any width. Not used by any row.

## Round 4's and 6's slips: impossible by construction

- **The mock answers by argv**: `tests/worlds.py` dispatches on the fake binary's own path (t4,
  t6, t7) and the argv to the areas' `world_*.py`; no case name reaches them. t4 and t6 refuse
  odd widths as their builds do (seen in the real mocks).
- **The argv twins**: each area's test parses every row back against plan rows typed by hand
  (`tests/test_q287.py`, `test_q291.py`, `test_rd7.py`, `test_dump.py`, `test_q086.py`).
- **Real tools' mocks**: every row runs through its own tool's `--mock` build of the pinned source
  (`tests/realmock.py`: t4 4623753, t6 d9b2969, t7 1c64f3a).
- **Scorers replayed before the freeze** on the precedents' kept files under their real names, and
  on doctored copies that must fail (above).
- **Staged tree under env -i**: `tests/run_mock.sh` stages with `run/stage_r7.sh` onto a fake
  laptop; the ssh shim runs the laptop side under `env -i`; `sessioncheck.py staged` on the exact
  three files stage copies, `envi` of the staged runner, `kept` with each scorer's own reader on the
  mock output; `score_r7.py missing` per stage (every declared file kept).
- **Controls read something**: each area calls `scorekit.refuse_unreadable` in its generator; a
  control with no reading is cannot tell (premise), never a pass. Every scorer input is created
  (`$W/depth`, `$W/dump` made before every job) and kept (rc 23 otherwise).
- **No timing window**: no held flow; every sleep is 0 in the mock.

## Laptop files (round 7)

Everything under `~/scratch/r7r/`: `run/` (runner, tables, FROZEN.sha256, TOOL7.sha256), `bin/`
(`sgxfive-test-t6`, `sgxfive-test-t7`), `stage/` (the 55 programs of `bins/`), `out/ATT/STAGE`.
One `mktemp -d ~/scratch/tmp/r7r.XXXXXX` per stage run, each job's directory removed once kept,
the whole directory at exit; at least 200 MB free on `~` before each job (rc 22). Never `/tmp`.
Debugfs writes: `reset 1`, and `render_rgn_arrays 1` then `0` around each of q293's four rows
(read back; restored at every exit). The tool writes its own kpokes (q287/q291 depth recipe, q086
`ta:143/144/146`, q139 `ta:14x`, q293 `par:N`).

## Layout

- `tables/STAGE.txt` (`name|set|risk|knobs|tool|args`), `TABLES.md`, `predictions/STAGE.tsv`,
  `PREDICTIONS.sha256`, `FROZEN.sha256` (generators, models, scorers, runner, env, tables,
  predictions, programs, template, pin files, lead script, and by absolute path main's
  scorekit.py, sessioncheck.py, health.sh and every outside file a generator read:
  `gen/data/sources-*.lst`), `FROZEN.commits`, `TOOL.sha256` (t4), `TOOL6.sha256` (t6, round 6's),
  `TOOLSRC.sha256`, `TOOL6SRC.sha256`, `TOOL7SRC.sha256`, `TOOL7.sha256` (the slot), `stages.txt`.
- `gen/`: `r7gen.py` (all areas, TABLES.md, the invariants: 143 jobs, unique names, every `$S/`
  a `#need` and a file of `bins/`), `g_q287.py`, `g_q291.py`, `g_rd.py`, `g_dump.py`,
  `g_q086.py` and their helpers; `frozen_commits.py`.
- `score/`: `score_r7.py` (the entry point), the five area scorers and helpers, `scorekit.py` and
  `sessioncheck.py` (main's, byte for byte).
- `run/`: `stage_r7.sh`, `r7.sh` (Mac), `run_stage.sh` + `lib_r7.sh` + `r7.env` (laptop),
  `freeze_r7.sh`, `guard_r7.sh`, `lib_check.sh`. `lead/build_tool7.sh` (Mac and build host only).
- `templates/pix_posstore.s` (+ .lst): E898's landed template, the source of `bins/pix_posstore.bin`.
- `tests/`: `run_all.sh`, `run_mock.sh`, `worlds.py`, `fake_tool.sh`, `realmock.py`, `shims/`, the
  areas' tests and worlds; `debug-src/simcheck` (the plan's sim harness, for test_sim_q291.py).
  `debug/` is scratch.

## Publishing

Nothing here is firmware-derived (no disassembly reading, no script importing one; every program
is our own assembly): the whole directory may be published by the fold, **no file for
data-private**. `debug/` is scratch and is not published (it holds the tool mock builds, the
Mac copy of t6 and, once built, t7).

## Deviations from the plan

1. Stage split for the gates: q291's gate row is its own stage `q291g` and R6's 14 controls their
   own stage `p7-rdc`, so the driver can skip the rest (the plan's "stage ends, session goes on")
   from the kept files. The s0 gate stops the session with driver exit **40** (the plan's table
   said rc 30, which is the health's code here).
2. q139 rows add `--keep-going` to the datasets' commands: without it t4 skips the dump after an
   image that does not check (`if (!ret && o->dump_dir)`), so every wrong-image row would stop
   rc 23. With one render it changes only the tool's last line.
3. x-rd-7's tag: R6's formula gives 0x10 at j = 7 (tag 0 with bit 4, label 0:1), which no other
   output carries; kept as the plan's "tag 16" and readable. The lead may prefer another unused tag
   (a regeneration and a new freeze).
4. Q276 own-source floor: fewer than 300 own-source words in a job is cannot tell (an addition;
   it can only make a row cannot tell).
5. gateodd: a refused odd width skips only the `oddw` rows and the stage still runs its even-width
   rows (the plan: "the poke twins still run"), then exits 21. The refusal is recognised by
   `job: rejected` / `render: Invalid argument` with `FAILED after 0 renders` (the real output also
   prints a `diff:` line of the unrendered target).
6. q291 rows all use t6 (no row needs t7); the cut triangles reach 3.8 W / 3.6 H, past
   `--tri-full`'s 3 x and E606's +124 % (clip space; not expected to matter, flagged).
7. u2 (q293) is frozen against E888's kept dump and hash from the 99CD90DA boot: if 41E2F5C7
   changes them, u2 fails and the q293 headline reads controls FAILED (a finding, not a stop).
