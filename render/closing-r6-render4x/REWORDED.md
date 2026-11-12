# Reworded after the run (2026-11-12, at the fold)

`tests/run_mock.sh`, one check (line 372, now 372 and 373): it compared the sha256 of
`FROZEN.sha256` with the hash set A ran with, 5fbd64f7.... `tools/closing/session_tests.sh` runs a
published session from a copy whose freeze has its absolute paths pointed at a fake home (and
`gen/data/sources.lst`, a frozen list of such paths, with them), so in that copy the file's hash
differs and the check failed while both freezes verified. The check now hashes the published
`FROZEN.sha256`, which session_tests.sh links beside the copy as `closing/r6-render4x/`, and the
session's own file where there is none (in the session directory, as run); it still requires both
sets to verify. The file is not in either freeze. The line as run:

```
[ "$(sha "$P/FROZEN.sha256")" = 5fbd64f7d2ea61052f4ca60aa996026c35768a49d5b179e6a8b1e5b3a1b031e8 ] && "$P/run/freeze_k.sh" verify A > /dev/null && "$P/run/freeze_k.sh" verify B > /dev/null \
```

`tests/test_gen.py`, its check of `gen/data/sources.lst` (lines 138 and 139, one import added):
as round 5's (render/closing-r5-render4x/REWORDED.md), it named paths of the clean room's
exclusion list as strings to look for, which the guard keeps out of public repositories. The
check now requires every listed source to exist and to sit in resgx545 or resgx545-data (an allow
list, stricter than the old deny list), round 5's wording. The file is not in either freeze. The
test as run is kept in resgx545-data-private, `closing-pre-reword/r6-render4x/tests/test_gen.py`.
