# sibling-src/: inputs the session read from scratch beside it

`sibling-src/render4x/c1.snap1.txt` and `c1.snap3.txt` are K2's register snapshots of its held
job c1 (the fault held, then after the reset), as the round 4 render planning kept them in
`closing4/render4x/` of the scratch tree. The generator `gen/rgen.py` names `c1.snap1.txt` as the
source of the reported 0x0724 reading (0x000b000b), and `tests/test_gen.py` reads
`../render4x/c1.snap1.txt` to check it.

They were added on 2026-11-11, after the run and after the freeze, so that the session's tests
can be re-run from the published data (`tools/closing/session_tests.sh` copies each
`sibling-src/<dir>/` to `closing3/<dir>` beside its copy of the session). They are copied byte
for byte from the scratch tree, are not in `FROZEN.sha256` and were not used on the laptop.
