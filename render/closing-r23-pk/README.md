# r23-pk

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 b2b6bc0d44fc.

## What runs (rank-round22.md 2.1, 2.2 and 6; DECISIONS-R22 all (a), R22-2 a, R22-4 a)

Tool t22 (`~/sgxfive-test-t22`, sha256 9b62d315..., built on the laptop from resgx545 3c68e8d,
`lead/build_tool22_laptop.sh`, `lead/TOOL22.built`); health fill and triangle with t10. Module
E0CC40275493F8AEAD8180B as loaded; no knob, no debugfs write of ours, no register write, no
`--kpoke`. Safe class only; every stage `#limit 0`. Laptop prefix r23p. Records E1096 to E1098
(round 22's plan, section 6).

| stage | jobs | what | frozen | stop |
|---|---|---|---|---|
| pk | 4 | E391 case 0, E125 case 0, E568 fy-28-p0-csc, E391 unpoked: controls on t22's echo | H-ECHO; H-E391, H-E125, H-NOLOAD/H-LOAD | echo count != poke count (hook), on_stop end |
| q019 | 40 | E391's 40 jobs, same programs and pokes (gate: pk) | H-E391; H-ROWS fitted 0/1/4, held out 2/8 | echo count (hook) |
| q181 | 8 | E037 copy controls (set 0 loaded, not loaded), E568's fy fills csc/nocsc (gate: pk) | H-NOLOAD vs H-LOAD | echo count (hook) |
| q123 | 7 | in-step run and lapc controls (0x40000), exe18 start at 0x80040, bit-16 crossings (0x7fe00, 0x78000 x 8192 words) | H-CARRY18 vs H-WRAP; H-EXE18 vs H-EXE16 | control off its o0, placed words not as built (hook), on_stop end |
| q123h | 3 | bit-17 crossings, exe18 at 0xffe00 (gate: q123 controls, bit-16 carried, exe18 honoured) | H-CARRY18 vs H-WRAP17 | any fault or hang |

62 jobs, about 25 to 30 minutes with the runner's reset and health between jobs. Any fault, hang
or unexplained failure stops the stage (kit). Predictions: the model world of `mock/world.py`
(every echo as t22 prints it, E391's and E125's markers, E568's black, E037's copy hashes,
H-CARRY18 and H-EXE18) is the planner's expectation [infer]; the scorer decides.

Every landing a q123 model allows is mapped: the placed program's words are pads that end the task
with `o0 = 0xb0000000 | word`, the probe's own program at the heap base 256 pads `0xc0de0000 |
word` (a wrap or a truncated target lands there). q123h runs only when the bit-16 crossings
carried and the exe18 start at bit 16 was honoured, so a 16-bit wrap (to the unmapped 0x80000) is
excluded before bit 17 is tried (gen/q123.py, tests/test_plan.py).

Known limit: t22's fill probe prints the first 32 changed scratch dwords (sa0-sa31), as the tool
of E391 did; sa32-sa63 of sa64_dump.s are counted (`scratch 32 more changed`), not shown. H-E391
is scored on sa0-sa31 only (E391's own reading had the same limit [infer]: see FOLD-NOTES.md).

Firmware-derived files: none (every program is ours or E391's, E125's and E568's published ones).

## Replay vectors

- pk, q019: `closing_tables.py` rows of sa0-sa31 per job; replay: sgx-sim's fill `douta` path
  (`crates/sgx-sim/src/vectors.rs`, secondary attributes within the PDS state's size, pds_isa
  3.4); a row the model's size rule disagrees with is the fold's finding, not a silent refusal.
- q181: rows of the fy fills' pixel sha256 and the copies' hashes; replay: sgx-sim `tex.rs`
  (`the_yuv_texel_model_is_opaque_black_for_an_unloaded_set`) for the black rows; a row whose
  set is loaded is `refused` (the sim stops on colour-space load jobs, E568's note).
- q123, q123h: rows of (offset, form, words, target, o0); replay: sgx-sim `usse.rs`
  (`a_placed_program_counts_from_its_code_base`, PCLINK_MASK 0x3ffff), extended by the fold
  with the crossing rows.

## Commands


Every command is run through its interpreter, never by its mode bits (r7-geo's stage script
had mode 644: "permission denied", nothing staged, the first stage exited 127):

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (it has pytest and numpy), which
  the offline tests use unless `PY` names another; never a scratch venv of an older session.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py). The driver keeps its own logs, `out/stage.log` and
  `out/ATTEMPT/run.log`; tee nothing into this directory's top (verify reports a new file there).
