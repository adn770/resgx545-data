# r16-usse fold notes (2026-11-14, after the run)

Attempt `out/20261114-092913`, rc 0, 30 jobs, no stop, fault or hang (`run-r16u.log`,
`stage-r16u.log`: the lead's logs). The frozen scorer re-run on the kept files is byte-identical
(`reproduce.sh`, `reproduce.out`). Records E1061 (uadd, urpt; Q126) and E1062 (utest; Q137).

## Frozen verdicts

- uadd: both controls PASS; H-ZX 4 of 5 rows (u-imm1, u-imm127, u-c56, u-i0); **u-sa0 FAILED**
  (H-ZX 6/8 dwords, H-SX 0/8); H-SX 0 of 5.
- utest: both controls PASS; H-RULE 18 of 18, H-SIM's values 18 of 18; every rival 0 held.
- urpt: control PASS; H-ZX-ADV 2 of 2; H-NOREP, H-NOADV, H-SX 0 of 2.

## Post hoc (after the run, not frozen): u-sa0

`sa0_posthoc.py` (`sa0_posthoc.out`). Dwords 4 and 5 (pairs 4 and 5) read 0x8000fedc and 0x0001ffff,
the H-ZX values of pairs 6 and 7, written by the program's later instructions; dwords 0 to 3, 6
and 7 read their own pairs' H-ZX values. The pixels (o0 = the last `mov r3, sa0`) are mixed:
0x0001ffff (pair 7) 1406, 0x7fff8001 (pair 1) 182, 0x8000fedc (pair 6) 172, 0x00010000 (pair 0
or 4) 164, other 124. [infer] sa0 is one register shared by the fill's instances, which run the
program at different points: an instance reads another's write. Every value named is an H-ZX
value of some pair and none is an H-SX value of a pair where the two differ, but the row was
frozen per dword and FAILED: the sa0 destination clause of Q126 is not decided by it.

## Vectors

`make_vectors.py` (fold-local: closing_tables.py has no kit kind for probe scratch dwords, a
tooling item) writes `vectors/closing/r16-usse/usse/r16-usse-{uadd,utest,urpt}.vec.json`
(sgx545-vectors). u-sa0's o0 is mixed, so its vector has no o0 and the simulator does not compare
it (one instance cannot give the shared register's race). sgx-sim at the fold replays every other
vector (29 of 29 match).
