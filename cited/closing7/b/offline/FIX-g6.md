# G6 post-run fix (2026-11-12)

The frozen `g6_s3miss.as-run.py` (sha256 in `FREEZE-g6.sha256`) stopped on its second dump
(R3-geo g-c5 c5b-f1): `f3_streams.chain` raised on a stream link outside the dump, which in an
overflowed dump is a block on a page the partial render freed and the TA reused. Its output up
to the stop is `g6_s3miss.as-run.out`.

`g6_s3miss.py` reports such a dump ("stream not read") and goes on; nothing else changed. G6
is exploratory and has no verdict.
