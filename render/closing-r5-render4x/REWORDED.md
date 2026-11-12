# Reworded after the run (2026-11-12, at the fold)

`tests/test_gen.py`, its check of `gen/data/sources.lst` (two lines): it named two paths of the
clean room's exclusion list as strings to look for, which the guard keeps out of public
repositories. The check now requires every listed source to exist and to sit in resgx545 or
resgx545-data (an allow list, stricter than the old deny list); it passes on the same 256 files.
The file is not in the freeze. The test as run is kept in resgx545-data-private,
`closing-pre-reword/r5-render4x/tests/test_gen.py`.
