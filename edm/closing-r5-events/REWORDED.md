# Reworded after the run (2026-11-12)

Before publishing this session in resgx545-data, the project's clean-room guard flagged one
sentence of our own notes (never the laptop's output), in one file: `README.md` named the closed
sources the preparation did not read. Under the user's decision of 2026-11-11 (the one R3k-events
and R4-events followed: reword the notes that name the closed sources), the sentence was reworded
to say that no closed source was read. Only wording changed. No logic, no prediction, no table,
no blob and no laptop data changed.

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `TOOL.sha256` and
  `LAPTOP.sha256` too.
- `out/` (everything the laptop produced and the scorer printed then) and `run-a1.log` are
  byte-identical.
- `README.md` is not in the freeze, so `FROZEN.sha256` is unchanged.
- The scorer, run on the kept stages after the rewording, prints output byte-identical to the
  kept `out/a1/score-STAGE.txt` in 3 of 3 stages (h1, h2, h3).
- The original bytes are kept in the private data repository
  (`closing-pre-reword/r5-events/README.md`).

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `README.md` | 06cbb0681da472f0 | 1ef0f43d274cc381 | no |
