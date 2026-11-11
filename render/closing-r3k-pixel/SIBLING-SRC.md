# sibling-src/: inputs the session read from scratch beside it

`sibling-src/kernel/layout_f4.py` and `layout_f4.out` are the kernel batch's layout check
(`closing3/kernel/` in the scratch tree, 2026-11-10 14:14): the formula of the kernel's TA data
layout, transcribed from the linux fork, against every 4x size on record, and its output. The
generator `gen/kgen.py` names it as the post-hoc fit (19 of 19 rows on record) that the frozen
layout sizes of the held-out rows come from, and `tests/test_gen.py` reads
`../kernel/layout_f4.out` to check them. Running `python3 layout_f4.py` reproduces
`layout_f4.out` byte for byte.

They were added on 2026-11-11, after the run and after the freeze, so that the session's tests
can be re-run from the published data (`tools/closing/session_tests.sh` copies each
`sibling-src/<dir>/` to `closing3/<dir>` beside its copy of the session). They are copied byte
for byte from the scratch tree, are not in `FROZEN.sha256` and were not used on the laptop.

`README.md` is a pre-run document and is left as it was.
