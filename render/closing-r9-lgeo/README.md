# r9-lgeo (round 9, session S9-lgeo: Q283, Q139)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 f32dfac and resgx545-data 2d666bfa. Plan:
`closing9/seeds/exp-seeds-r9.md` sections 5 and 6 (S-4 (a)); decisions `closing9/DECISIONS-R9.md`
(safe class only: no held reset, no planned fault, `#limit 0` in every table). zs3 (Q260) is not
in this session: it waits on the offline OZ gate, and if it passes it is built as a separate
session. Built offline; nothing here touched the laptop, cachix or a git repository. Records E958
(tx6) and E959 (q139b) are reserved for its fold (the builder folds it; notes in
fold/FOLD-NOTES.md).

## What runs, in order: 18 jobs, about 10 minutes

Laptop: module srcversion B60AB0B475DD1E8972419B5 (the test boot of fork 2a650d74, on the laptop
until the next reboot); tool t4 only, `~/sgxfive-test-rgn4` (sha256 e6951558..., built from
resgx545 4623753 `userspace/libsgxfive/tools/sgxfive-test.c` by `userspace/libsgxfive/Makefile`,
`TOOLSRC.sha256`; session.toml binds its source, so the kit's library mock replays every row);
files under `~/scratch/r9m/`.

| # | stage | jobs | what | frozen | label |
|---|---|---|---|---|---|
| 1 | tx6 | 14 | type 4 off multiples of 32; type 3 at a 16-bit format; type 1 at 24 and 40 wide | H-CEIL vs H-P2, H-PACK; H-DW8 vs H-TX8, RASTERW; RASTERW vs RASTERP2 | 2 controls, 11 held out (2 soft), 1 soft bridge |
| 2 | q139b | 4 | the 1280 x 720 and 768 x 640 baselines and m2-B3p1 residues, dumped | H-EVEN (= R7-BLK there) | 2 controls, 1 held out, 1 residue |

Time: tx6 about 2 minutes (the health fill and triangle after every job, `after`), q139b about 2
(1280 x 720 `--pixels` with dumps the longest; r8-lgeo's q139 ran 20 such jobs in about 3); with
staging, the per-stage health and the copy back about 10 minutes.

**Stops.** No fault is planned anywhere: any fault, hang or unexplained failure stops the stage
(rc 4) and the session (the Mac driver stops on any status but 0 and 24). A control without its
reading stops the session at its stage (rc 25, premise). The second soft failure in a row stops
tx6 (rc 24; the driver goes on to q139b); the second probe of tx6 without pixel rows (`needrows`)
or the second q139b row without a hash (`needhash`) stops that stage (rc 24). A file the scorer
reads that was not kept stops it (rc 23). `min_free_mb` 400; `job_timeout` 120 s.

## Hypotheses, controls, verdicts (frozen in predictions/, scored by score/score.py)

- **tx6 (Q283; E910, E940, E941).** E725's map-texture fill (64 x 32 pixels, the scratch's dword i
  is 0xD0000000 | i over t4's default 16 pages, 64 KiB; no rival reads past dword 7151).
  - Controls (kept images, `reads:rows`, both can fail): E910's type 4 64 x 32 program and image,
    E725's type 3 32 x 16 map program and image, byte for byte.
  - Type 4 off multiples of 32, seven 64 x 32 windows through the linear axis with offsets
    (texel ((x + xo) mod w, (y + yo) mod h); `lwin` of gen/lgen.py, at no offset `texcatalog.swin`
    bit for bit, the axis of E940's 24 and 40 wide rows): 48 x 64 at y 0 and 32, 96 x 32 at x 64,
    80 x 64 at x 0 and 64 by y 0 and 32. Frozen: H-CEIL (ceil(w / 32) blocks a block row, E941's
    rule as sgx-sim writes it) against H-P2 (the width rounded up to a power of two) and H-PACK
    (a partial block (w mod 32) columns wide). H-PACK parts on 5 rows, H-P2 on 2 (80 x 64 at y
    32); 96 x 32 at x 64 and 80 x 64 at x 0 part nothing (the axis at those widths). [infer] E910's
    type 4 at 4 x 16 (rows 32 dwords apart) already speaks against H-PACK below 32 wide; it stays
    a rival where a partial block follows whole ones.
  - Type 3's padding at a 16-bit format: format 5 (B5G6R5, two texels a dword) at 4 x 8 and 8 x 8
    through the map axis. Frozen: H-DW8 (rows max(8 dwords, w texels) apart, E940's max(8, w) in
    dwords) against H-TX8 (max(8 texels, w)) and RASTERW (w); all three part at 4 x 8, H-DW8 the
    other two at 8 x 8. The decision is on the 16-bit words read back from the pixels' top bits
    (`tx6model.word_of`), the low half of a dword first (sgx-sim `tex.rs` fetch), so it does not
    rest on the widening; the plan's [check] on the decoding: the scorer prints whether the pixels
    are also sgx-sim's widening of a rule (`colour_texel`, format 5) and whether the words match
    a rule with the high half first (readings, no verdict). No kept job ran a 16-bit format on
    type 3; E942 ran format 9 on type 5 without a fault.
  - Soft, last: type 1 at 24 x 8 and 40 x 8 through the linear axis, RASTERW against RASTERP2,
    with type 1 32 x 16 through the same axis as their bridge (set `bridge`, soft: unless it gives
    E725's 32 x 16 image the two rows cannot tell).
- **q139b (Q139; E944, E950's H-EVEN).** The datasets' own command (`ta/mtile-fields`, token for
  token) with `--keep-going --dump-render "$W"`; every row drew without a fault in its dataset.
  - Controls (`reads:hash,dump`, both can fail): the unpoked 1280 x 720 and 768 x 640 baselines,
    exact image and one header with a stream for every target tile (`lib_dump.baseline_layout`):
    the header base E944 lacked at these sizes.
  - Held out: the baselines' header slots (1800 and 960) and 768 x 640 m2-B3p1's wrong-tile set
    (its dataset's 24) and every header slot, against H-EVEN (a block row of the first macrotile
    takes 8 floor(fx / 2) slots). There fx is 12 and 8, so H-EVEN = R7-BLK = the round 8 orders:
    these rows test the slot rule at two new sizes, they do not part H-EVEN from R7-BLK (no
    safe-class row does: the plan's finding 4, R9-7).
  - Residue (a reading, scored nothing): 1280 x 720 m2-B3p1 (52 wrong tiles in its dataset, 40
    under every model; the last y bound 37), its wrong tiles and slots against each model; its
    y-side rule is fitted at the fold, in sample.

**Predicted outcomes.** H-CEIL held (7 of 7); H-DW8 held (2 of 2) [infer: the pad counts dwords,
as sgx-sim's 4 max(8, w) bytes]; RASTERW held for type 1 (2 of 2, as type 3 in E940); H-EVEN held
on the baselines and 768 x 640; the 1280 x 720 residue replicates its dataset's 52 wrong tiles.

## The mock's worlds (mock/world.py, kit/session.py mock)

model and rival (every stage 0; rival's images and slots fail the frozen rows, its controls
pass), norows (tx6 premise, 25), soft2 (tx6 stops 24, the driver goes on), txfault (a type 4 probe
faults: tx6 and the driver 4), ctlnohash (q139b premise, 25), nohash (q139b stops 24), fault (a
poked tri row faults: q139b and the driver 4), nodump (q139b's first row lacks its dump, 23).
The fake answers from the argv only: probes by their program's sha256 (`mock/progs.tsv`), tri
jobs by their geometry and pokes. Before the worlds, every row goes through the library mock
built from t4's bound source (4623753): none is refused.

## Replay vectors

The fold builds one `sgx545-tables` table a stage from the kept files alone (pinned:
`tools/usse-asm/closing_tables.py`, `closing_vectors.py`, `pbdump.py`, `region_tiles.py` and
`crates/sgx-sim/src/tex.rs` at f32dfac):

- tx6 → `closing_tables.py texture --session . --out fold/vectors tx6` →
  `fold/vectors/pixels/tx6.table.json` (per row the --pixels words, the job line, the input bin by
  sha256); replay: `crates/sgx-sim/src/tex.rs` texture layout tests for the layouts that hold
  (type 4's H-CEIL is already the sim's rule; the fold admits the new sizes in `measured_r4` with
  a test), `refused` for format 5 on type 3 (the sim admits types 1, 3, 4 at format 12 only)
  unless the fold adds it with a test.
- q139b → `closing_tables.py taslots --session . --out fold/vectors q139b` →
  `fold/vectors/ta-slots/q139b.table.json` (per row and tile the slots of every header naming it,
  the wrong tiles); replay: `refused` (the TA's region header placement at poked macrotile words
  is not modelled by sgx-sim or sgx-pipe).

## Layout

- gen/lgen.py writes `tables/`, `predictions/` (and `predictions/q139b/`), `bins/` and
  `mock/progs.tsv` from gen/tx6model.py and gen/q139even.py (new, standard library only) over the
  byte copies gen/texmodel.py, gen/texcatalog.py, gen/texbuild.py, gen/q139model.py,
  gen/q139_fit.py and `templates/tx_map.s` (r8-lgeo's published files, pinned), and the published
  records' kept files read at the pinned data commit (`gen/pins.txt`). score/lib_dump.py,
  score/pbdump_dump.py, score/region_tiles_dump.py and tests/kept.py are r8-lgeo's, byte for byte.
  The programs are assembled with usse-asm from `git archive` of f32dfac (`debug/asm`, which
  tests/run_all.sh builds; its sources are pinned).
- score/score.py, run/hooks.sh (readings rows, hash, dump; needhash, needrows), mock/world.py,
  `tests/` (`test_gen.py`, `test_models.py`, `test_twin.py`, `test_score.py`), PREFLIGHT.md,
  TOOLSRC.sha256; fold/FOLD-NOTES.md (the fold's notes; fold/ is outside the freeze).

Publishable: everything (our own programs and models; no firmware-derived file). **Nothing is
marked for data-private.** `debug/` is scratch.

## Commands

Every command is run through its interpreter, never by its mode bits (r7-geo's stage script
had mode 644: "permission denied", nothing staged, the first stage exited 127):

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (it has pytest and numpy), which
  the offline tests use unless `PY` names another; never a scratch venv of an older session.
- Offline: `bash tests/run_all.sh` (the assembler, the guard, own tests, the library mock and the
  mock of every world, the verify once frozen).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py).
- Score again on a kept attempt: `python3 score/score.py STAGE out/ATT/STAGE`.

## Deviations from the plan (the lead may object before staging)

1. Type 4's windows go through the linear axis with offsets, not the map axis's offset: the map
   axis normalizes to a power of two, so it cannot address 48, 80 or 96 columns. The seven
   windows are 48 x 64 (y 0, 32), 96 x 32 (x 64) and 80 x 64 (four); 96 x 32 has one block row,
   so it parts none of the three rivals there (a check of the axis at a third block).
2. Type 3's 16-bit rows are 4 x 8 and 8 x 8 at format 5 and are labelled held out, not explore:
   the verdict reads the 16-bit words back from the pixels, which needs no widening model.
3. q139b's controls are exact image and one header a tile; the baselines' slots are a held-out
   claim (no 1280 x 720 or 768 x 640 dump was read before), not a control premise. At these sizes
   fx is 12 and 8 (the plan said 12 for 768 x 640), so every order gives the same slots.
4. tx6 forbids `--scratch-pages` (every row at the default 64 KiB, the frozen size).
