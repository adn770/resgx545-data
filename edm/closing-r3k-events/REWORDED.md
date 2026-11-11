# Reworded after the run (2026-11-11)

Before publishing this session in resgx545-data, the project's clean-room guard flagged one
sentence of our own notes (never the laptop's output), in two files: `README.md` and
`PREFLIGHT.md` named the closed sources the preparation did not read. Under the user's decision of
2026-11-11 (the same as L3's of 2026-11-10: reword the notes that name the closed sources), the
sentence was reworded to say that no closed source was read. Only wording changed. No logic, no
prediction, no assembled task and no laptop data changed.

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `TOOL.sha256`,
  `TOOLR1.sha256`, `LAPTOP-k0.sha256` and `LAPTOP-kev.sha256` too.
- `out/` (everything the laptop produced and the scorer printed then) is byte-identical.
- Neither file is in the freeze, so `FROZEN.sha256` is unchanged; `FROZEN.pre-reword.sha256` is
  a copy of the freeze the run used, byte-identical to `FROZEN.sha256`.
- The scorer, run on the kept stages after the rewording, prints output byte-identical to the
  kept `out/score-STAGE.txt` in 11 of 11 stages (k0f, k0t, k0c, k0h, f, t, kb, e2b, e3h, e3a,
  e3b).
- The original bytes are kept in the private data repository.

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `README.md` | 722e7c8071867e65 | 0fdccfb3c09efbda | no |
| `PREFLIGHT.md` | a35d9e60cbe512ca | 247539970509d47b | no |
