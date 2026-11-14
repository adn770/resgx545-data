# r16-mte (round 16: Q116, the MTE state's region clip, first run)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 b2b5288c82ed (kit/ is that commit's blobs) and
resgx545-data 62cb03b369ca. Plan `closing16/plan/rank-round16.md` sections 2 ("r16-mte") and 3;
decisions `closing16/DECISIONS-R16.md`: R16-4 (a), **SAFE CLASS**: the gate row first, the
empty-clip row last, `on_stop = "end"`, any fault or hang ends the session. Built offline; nothing
here touched the laptop, cachix or a git repository. Record E1060 is reserved for its fold (the
builder folds it).

## What runs: 15 jobs, one stage, about 5 minutes

Laptop: module B60AB0B475DD1E8972419B5 (fork 2a650d74) loaded = installed; no debugfs knob is
written (only `reset`). Files under `~/scratch/r16m/`.

- t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6..., already on the laptop), bound by source to
  resgx545 a581c06 `userspace/libsgxfive/tools/sgxfive-test.c` (sha256 23e1fa76...,
  `TOOLSRC.sha256`), recipe `data:render/closing-r10-st1/lead/build_tool10.sh` (byte copy in
  `lead/build_tool10.sh`). Nothing is built for this session.
- Every row: `probe --tri pixel --temps 32 --pixels --width W --height H [--tri-full]
  [--blk-add 7=C0,C1] "$S/bins/pix_green.bin"`. The program is r3k-regress's `pix_green.bin`
  (the same bytes as p1139-green.bin: 0xff00ff00), the background object writes 0xff203040, the
  target starts at the sentinel 0xdeadbeef. `--blk-add 7=C0,C1` grows the probe triangle's block
  from 0xdf43 (18 dwords) to 0xdfc3 (20), the closed driver's own triangle-with-clip block (E347),
  the two words after the pixel programs (tri_probe.c add_words). No record ran `--blk-add` before.

| # | stage | jobs | #limit | tool | what | controls |
|---|---|---|---|---|---|---|
| 1 | rclip | 15 | 0 | t10 | region clip at 64 x 64, 128 x 128, 256 x 256, 100 x 60 | g-clear-64 (gate, first), g-twin-64 |

Rows in run order (gen/model.py `ROWS`; clip words C0, C1):

| row | size | object | C0, C1 | for |
|---|---|---|---|---|
| g-clear-64 | 64 x 64 | full | 0x80000001, 0x00000003 | gate: E348's clear clip (its formula), = no clip |
| g-twin-64 | 64 x 64 | full | none | the gate's no-clip twin |
| vp64-e348 | 64 x 64 | full | 0x80010001, 0x00010003 | E348's viewport row's clip |
| p64-c0-r23 | 64 x 64 | full | 0x80000000, 0x00020003 | one column, rows 2-3 |
| p64-c01-r0 | 64 x 64 | full | 0x80000001, 0x00000000 | two columns, row 0 |
| p128-c12-r12 | 128 x 128 | full | 0x80010002, 0x00010002 | the plan's rows 1-2 of 8 |
| p128-c3-r04 | 128 x 128 | full | 0x80030003, 0x00000004 | the last column, rows 0-4 |
| e128-on-full | 128 x 128 | full | 0x80000003, 0x00000007 | enable set, whole target |
| e128-off | 128 x 128 | full | 0x00010002, 0x00020004 | enable clear, partial range |
| s128-tri | 128 x 128 | default | 0x80000001, 0x00010003 | the clip edge across the triangle |
| p256-c2-r39 | 256 x 256 | full | 0x80020002, 0x00030009 | one column, rows 3-9 |
| p256-c56-r1015 | 256 x 256 | full | 0x80050006, 0x000a000f | the last rows |
| m256-c34-r59 | 256 x 256 | full | 0x80030004, 0x00050009 | across all four macrotiles |
| e100x60-c23-r23 | 100 x 60 | full | 0x80020003, 0x00020003 | E348's size, the edge tiles |
| z128-empty | 128 x 128 | default | 0x80030003, 0x00040007 | LAST: no tile of the object kept |

### rclip (Q116, E1060): the frozen forms (gen/model.py)

The frame: a pixel (x, y) is the probe's `row y:` value x, y the memory row. The tool's viewport
has a positive y scale and its CPU reference puts window y at memory row y (r13-flag's
f3-shape-a: diff 0, "2709 if flipped"); E348's closed-driver words are y up with a positive scale
too, so its "rows counted from the bottom of the GL target" are window rows from y = 0, i.e. our
memory rows from 0 [infer]. See Deviation 1.

- Region forms: **H-TILECLIP** (E348: tiles of 32 x 16, first <= tile <= last in both, rows from
  memory row 0); H-EXCL (last bound exclusive); H-FLIP (tile rows from the target's last tile row);
  H-FLIPEXCL; H-PIXEL, H-PIXEXCL, H-PIXFLIP, H-PIXFLIPEXCL (the fields as pixel bounds); H-NOCLIP
  (the words read and ignored).
- Outside the kept region: **H-BG** (the background object writes it) against H-UNTOUCHED (left
  at the sentinel).
- Enable (C0 bit 31): **H-EN** (clear: no clip) against H-ALWAYS (the bounds apply anyway) and
  H-OFFDROP (clear: the object dropped).
- The object: `--tri-full` covers every pixel; the default triangle's coverage is render.c's
  `sgxfive_tri_expect` (gen/model.py `tri_expect`, line for line): pixels within a pixel of an
  edge may read either colour.

Every partial row (10: clip enabled, part of the target kept) parts H-TILECLIP from H-FLIP and from
H-EXCL on at least 256 pixels, and from every other form and H-UNTOUCHED too
(tests/test_twin.py); e128-off parts H-EN from H-ALWAYS (13312) and H-OFFDROP (16384); z128-empty
parts H-TILECLIP from H-NOCLIP (4026) and H-UNTOUCHED, from H-FLIP on 123 only. Predictions:
`predictions/rclip.tsv` (each row's frozen map sha256 and counts, every rival's map and parts).

Controls that can fail: g-clear-64 (all 0xff00ff00 and equal to g-twin-64's image), g-twin-64
(all 0xff00ff00, as r3k-regress's kept ctl-green rows read). Both gate every row's headline.

Retire Q116 (R16-6 a, the lead confirms) if one form, one outside form and one enable form are
left by every decided row with both controls passing (score.py's `RETIRE` line); "objects and
clears alike" then reads the full-target object with E348's clear clip and the background [infer].

## Stops

- Any fault or hang (`#limit 0`, no `expectfault` row): the stage stops (4) and the session with
  it.
- hook_check (24, and `on_stop = "end"` ends the session): a row without its W x H pixel values; a
  pixel none of 0xff00ff00, 0xff203040, 0xdeadbeef; a gate row (g-*) whose image is not
  0xff00ff00 over the whole target (the gate: if E348's clear clip does not reproduce the no-clip
  image, nothing after it runs).
- A control without its reading (25), after hook_check.
- Strict health after any fault (the kit's).

## The mock's worlds (mock/world.py, kit/session.py mock)

model (H-TILECLIP + H-BG + H-EN: 0, 0), flip (0, 0), untouched (0, 0), always (0, 0), gatebad
(H-EXCL: the gate reads half its target: 24, ends), nopix (24), stray (a stray value: 24), short
(255 rows at 256 x 256: 24), clipfault (every `--blk-add` row faults: the gate row, 4), emptyhang
(the last row hangs: 4). The kit's library-mock replay runs all 15 rows on t10's pinned source,
none refused; tests/test_blkadd.py runs 29 `--blk-add` forms through it and checks the world
refuses every one the tool refuses (bit 7: exactly two words).

## Replay vectors

rclip: `refused` until the fold. The kept images become a table `rclip` (`closing_tables.py`
format `sgx545-tables`, the `texture` kind's `--pixels` words, the clip words per row); sgx-pipe's
`mte.rs` places only presence 0xdf43 (`state()`, Q116 in `OPEN`), so the replay is refused with that
reason until the fold adds a region clip to sgx-pipe (test first) and names the test that replays
the table (`--replayed crates/sgx-pipe/tests/...::... --model TEXT`). Pinned: `mte.rs`,
`closing_tables.py`.

## Layout

gen/make.py writes tables/rclip.txt and predictions/rclip.tsv from gen/model.py and checks
bins/pix_green.bin against its pin; score/score.py; run/hooks.sh; mock/world.py; tests/
(test_twin.py, test_gen.py, test_score.py, test_blkadd.py, kept.py); lead/build_tool10.sh (t10's
recipe, a byte copy); PREFLIGHT.md; FOLD-NOTES.md. Publishable: everything (our own program,
tables, scorer and mock; no firmware-derived file). **Nothing is marked for data-private.**
`debug/` is scratch (the library-mock build and the mock runs).

## Commands

Every command is run through its interpreter, never by its mode bits:

- Offline: `bash tests/run_all.sh` (the guard, the session's tests, the library mock, the mock of
  every world, the verify once frozen); `python3 gen/make.py --check` (the generator current).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`, its log kept
  OUTSIDE this directory (`... run . 2>&1 | tee ../logs/r16-mte-run.log`).
- Score again on a kept attempt: `python3 score/score.py rclip out/ATT/rclip`.

## Deviations from the plan (the lead may object before staging)

1. **The row origin.** The plan writes H-TILECLIP as "rows counted from the bottom" in memory
   (rows 1 to 2 of 8 at 128 x 128 = y 80..111) and H-TOP as rows from the top. E348's words are
   GL window rows under a positive y scale, and the tool's window y is memory row y, so E348's
   reading is rows from memory row 0 [infer]. H-TILECLIP is frozen so; the plan's literal reading
   is the rival H-FLIP. Both are scored on every row (they part on 1024 to 12288 pixels a partial
   row), and either one holding alone retires the clause.
2. **100 x 60**: a partial clip touching the edge tiles (columns 2-3, rows 2-3), not E348's
   full-target clear clip at that size (which would read the no-clip image only).
3. **The empty-clip row** keeps tiles of the target that hold no pixel of the default triangle
   (column 3, rows 4-7 at 128 x 128), not a range outside the target or first > last (never-run
   index forms); it parts H-TILECLIP from H-EXCL on 0 pixels by construction, so the 256-pixel
   rule is held on the 10 partial rows, not on it.
4. **The gate stops the session** (hook_check) when g-clear-64's image is not the no-clip image,
   rather than only failing the control: an H-EXCL hardware is then measured on the gate row
   alone (its kept image still decides the bound form).
