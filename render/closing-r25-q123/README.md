# r25-q123

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 7f214e511d6a.

## What runs (rank-round24.md 2.3 and 5; DECISIONS-R24 R24-4 a, R24-6 a)

Tool t22 (`~/sgxfive-test-t22`, sha256 9b62d315..., built on the laptop from resgx545 3c68e8d,
`lead/build_tool22_laptop.sh`, `lead/TOOL22.built`); health fill and triangle with t10. Module
E0CC40275493F8AEAD8180B as loaded; no knob, no debugfs write of ours, no register write, no
`--kpoke`, no `--poke`. Safe class only; every stage `#limit 0`. Laptop prefix r25q. Record E1102
(rank-round24.md section 5). It can share one sitting with r25-csc (R24-6 a).

| stage | jobs | what | frozen | stop |
|---|---|---|---|---|
| q123s | 10 | E492's read and jump programs at E492's 0x300008 (2 controls, link 0x3), then at 0x0c3010, 0x2ca7f8, 0x3d0100, 0x1c8008 (8 held out) | H-STEP80000 (links 0x8604, 0x9501, 0xa022, 0x9003) against H-STEP20000, H-STEP40000, H-STEP100000, H-NOSTEP | control off its o0, placed words not as built (hook), any fault or hang; on_stop end |
| q123w | 11 | E1098's c-lapc (control, word 590), then ten 8192-word programs at 0x40000: lapc to 8191, 5712, 3958, 6608, 394, 6365; ba to 5072, 256, 5652, 3595 (seed 0x25123) | H-INDEX against H-WRAP256 | as q123s; on_stop end |

21 jobs, about 10 minutes with the runner's reset and health between jobs. Predictions are frozen
in `predictions/` (gen/make.py from gen/q123.py) before the run: the step was fitted on E476's and
E492's ten links (0x80000 is the only multiple of 8 up to 16 MiB that fits all ten, the generator
re-checks it), and the four new placements are held out: each of the rivals (every power of two
fitting five or more of the ten: 0x40000 seven, 0x20000 and 0x100000
five; and no step) predicts
another link at every one of them. The q123w targets are drawn by `random.Random(0x25123)` from
257 to 8190 (not 590) plus 256 and 8191, so no control row chose an index. Every placed word
outside the code is a pad naming itself (0xb0000000 | word), the heap base 256 pads (0xc0de0000 |
word): every landing a model allows is mapped. E492's programs are its bins byte for byte, followed
by pads to 32 words; c-lapc and q123-base are E1098's bins byte for byte.

Retires Q123 (R24-4 a) if both controls pass and every held-out row holds H-STEP80000 / H-INDEX;
any other result is a finding the fold records (FOLD-NOTES.md).

Firmware-derived files: none (every program is ours: E492's and E1098's published ones).

## Replay vectors

- q123s, q123w: `closing_tables.py` rows (offset, form, words, target, o0); replay: sgx-sim
  `usse.rs` (`a_placed_program_counts_from_its_code_base`, PCLINK_MASK 0x3ffff), as E1098's rows;
  the fold extends it with the new placements and the drawn landings. Everything the replay reads
  is in this session (bins/, tables/, predictions/) and the kept outputs.

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
