# Reworded after the run (2026-11-11)

Before publishing this session in resgx545-data, the project's clean-room guard flagged one
sentence of our own notes (never the laptop's output), in two files: `README.md` and
`PREFLIGHT.md` named the closed sources the preparation did not read. Under the user's decision of
2026-11-11 (the one R3k-events followed: reword the notes that name the closed sources), the
sentence was reworded to say that no closed source was read. Only wording changed. No logic, no
prediction, no assembled task and no laptop data changed.

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `TOOL.sha256` and
  `LAPTOP.sha256` too.
- `out/` (everything the laptop produced and the scorer printed then) and `run-a1.log` are
  byte-identical.
- Neither file is in the freeze, so `FROZEN.sha256` is unchanged.
- The scorer, run on the kept stages after the rewording, prints output byte-identical to the
  kept `out/a1/score-STAGE.txt` in 3 of 3 stages (kb2, kp, e3p).
- The original bytes stay in the session's scratch directory
  (`scratch/resgx545/closing4/r4-events/`), for the private data repository.

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `README.md` | 921baef796e22231 | 903a60416e3d5832 | no |
| `PREFLIGHT.md` | ba223ae31e008070 | 96679a9180670b75 | no |
