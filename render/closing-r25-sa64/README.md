# r25-sa64

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 134103452432.

## What runs (rank-round24.md 2.1 and 5; DECISIONS-R24 R24-1 a, R24-3 a)

Tool t24 (`~/sgxfive-test-t24`, sha256 fd15fce4..., built on the laptop from resgx545 1341034,
`lead/build_tool24_laptop.sh`, `lead/TOOL24.built`): t22 plus `probe --scratch-show N` (1 to 64,
default 32). Health fill and triangle with t10. Module E0CC40275493F8AEAD8180B as loaded; no knob,
no debugfs write of ours, no register write, no `--kpoke`. Safe class only; every stage `#limit
0`. Laptop prefix r25s. Record E1104.

| stage | jobs | what | frozen | stop |
|---|---|---|---|---|
| pk64 | 2 | E1096's pk-e391 (E391 case 0) and pk-e125 (E125 case 0) with `--scratch-show 64` | H-ECHO, H-E391/H-E125 (sa0-sa15), H-SHOW (64/0, 16/0) | echo count, print capped below 64 (hook); on_stop end |
| q019 | 56 | E391's 40 jobs byte for byte with `--scratch-show 64`, then 16 held out at 3 and 6 rows (gate: pk64) | H-E391 (sa0-sa31, in-row control), H-ALL64, H-NONE, H-ROWS (fit 0/1/4, held out 2/3/6/8) | echo count, print capped (hook) |

58 jobs, about 25 to 30 minutes with the runner's reset and health between jobs (E1096: 44 jobs in
about 20 minutes). Any fault, hang or unexplained failure stops the stage (kit). Every poke row
reads its `probe NAME: poked ...` echo as a premise; every row's print must take
`--scratch-show 64` (64 lines, no `more changed` line) or it is cannot tell.

The 16 held-out programs (`q019-R-r3-*`, `q019-R-r6-*`) are E391's table at sizes it did not
run: `douta_words.s` rendered by `tools/usse-asm/probe.py` with the markers
`0xa<run><rows:02x><attribute:04x>` and C words `attribute << 8`; the same renderer reproduces
E391's 40 programs byte for byte (tests/test_plan.py). bg:1 = 0x30000 | rows << 18 (3 rows
0xf0000, 6 rows 0x1b0000).

Predictions [infer: the planner gives none of the three as expected]: H-NONE extends E391's
"never sa32-sa63"; H-ALL64 would need the appended correction to E391 at the fold; H-ROWS retires
Q019 only with a fit table that is not flat (score line `H-ROWS fit table flat: no`) and R24-3 a.

Firmware-derived files: none (every program is ours or E391's and E125's published ones).

## Mock worlds (mock/world.py)

none, all64, rows (all run); noecho and capped (pk64 stops, the session ends); e1096off (pk64's
control fails in the scorer, q019's gate shuts).

## Replay vectors

- pk64, q019: `closing_tables.py` rows of sa0-sa63 per job (format `sgx545-tables`); replay:
  sgx-sim's fill `douta` path (`crates/sgx-sim/src/vectors.rs`, secondary attributes within the
  PDS state's size), as E1096's fold; rows past sa31 the model does not hold are the fold's finding
  (SIM_UNMODELLED.toml entry if refused), not a silent refusal.

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
