# Reworded after the run (2026-11-12)

`hwr_scan.py` and `stop_dumps.py`: the directory filter of each (lines 13 and 17) named two
paths of the clean room's exclusion list, which the guard keeps out of public repositories.
Both lines now keep only `firmware`, `clean-room` and `.git`: the scripts walk the top-level
directories of resgx545-data, which holds neither path, so the walk is the same. Re-run on
2026-11-12 over the same 22 directories, both outputs are byte-identical to the kept
`stop_dumps.out` and `hwr_scan.data.out`, as were the scripts as run. The scripts as run are
kept in resgx545-data-private, `closing-pre-reword/r5-events-offline/`.
