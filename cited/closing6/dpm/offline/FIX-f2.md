# F2 post-run fix (2026-11-12)

The frozen `f2_objpage.as-run.py` (sha256 in `FREEZE-f2.sha256`) read PB page 1 as the global
list's head in every dump. After a partial render the list's first pages are freed and its head
moves (the state words name it), so in overflowed dumps page 1 held stream blocks (period 32) and
the phase test read "NO" for pages it had not located; it then stopped on a job of R2-geo g-c3
whose timeline has no 0x0658 (KeyError). Its output up to the stop is `f2_objpage.as-run.out`.

`f2_objpage.py` takes the list's pages from the state words when the dump has them and page 1 when
they read empty, tests only pages that are global page k by F1's one-valued S_k and the first
run's peak, and skips (and prints) a job without 0x0658. The block head pair and L = 67 are the
fit dump's, as the as-run version read them there. The as-run output had already shown the phase
test passing on every complete calibration dump, so the fixed run's held-out lines are SEMI.
