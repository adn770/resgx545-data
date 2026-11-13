# r9-faults fold notes (the builder's, for the fold after the run)

- Records: E964 (xf2, Q108), E965 (tri2, Q108), E980 (bif, Q076). Draft each method with
  `tools/records/new_record.py --session DIR` once landed.
- Build: scaffolded from resgx545 f32dfac, data 2d666bfa, srcversion B60AB0B475DD1E8972419B5,
  t4 bound by `--tool-src
  t4=4623753:userspace/libsgxfive/tools/sgxfive-test.c@userspace/libsgxfive/Makefile`.
  4623753 is on no branch of resgx545 (r3-rgn4's commit); session_tests.sh may warn, as for round
  4 and 5's sessions.
- E946's slip checked: the kit at f32dfac does not count a control's expected fault against
  `#limit` (tools/closing/test_kit.py,
  `test_a_control_that_expects_its_fault_does_not_count_against_the_limit`); this session's
  `#limit` is expectfault non-control rows + 1 (xf2 8, tri2 5, bif 10), so the count never stops
  a stage inside its rows.
- Kit gap (report to the round's tooling agent, not fixed here): the runner calls no hook after a
  fault or hang row, so the plan's "stop on two -110 in a row" is read only at the next row that
  reads ok (hook_check counts `SGX recovery failed: -110` since the stage's begin marker) and by
  strict health. A kit rule (a fault row whose slice or the following health has a -110, counted
  in a row) would make it exact.
- Post hoc only: E946's xf-wo-fill page (0x3e002000) is the fit of H-LASTROW; the summaries of
  the S9-k2 hypotheses count held-out rows only. tri-edm-dld is a reading (no load at 0x0017100c).
- [infer] to check at the fold: the buffer layout of B60AB0B4 equals E573's (a bif fault outside
  the left-out buffers reads `fault-elsewhere`: read the debugfs layout then); the new fill
  sizes' laptop hashes equal the library mock's (else their exact rows read `other`); the 64 x 64
  depth store changes 4096 dwords (tri-c-depth's frozen dstore, from E465's window rule).
- Replay: xf2/tri2 -> `pte` table, sgx-pipe bif.rs `pte_access` (extend test first for what
  holds); bif -> refused (no alias kind, Q076 OPEN in bif.rs).
- Deviations from the plans: README "Deviations" (bif's rows, xf2's limit 8, tri-c-depth second,
  the -110 rule).

## The run and the fold (2026-11-13)

- One attempt, out/20261113-084720 (xf2 08:47, tri2 08:50, bif 08:51 to about 08:54 Mac time),
  33 of 33 jobs, every stage rc 0, every control PASS, no stop, no lead decision, no -110, health
  drawn at its first try after every fault; the lead's log is out/run-r9f.log. fold/reproduce.sh
  (output fold/reproduce.out): the freeze verifies, the frozen scorer's output is byte-identical
  to the kept one for the three stages, 253 kept files match the laptop's raw sha256.
- Faults: isolation's three (control), xf2 5 (0x80020 x 3 at the last pixel's page SB 31, 0xa0020,
  0x80002), tri2 3 (0xa0020 at 0x3e001001 for WO|EDMPROT, 0xa0200 at the store's first page,
  0x80200 at 0x3e018001, the store window's last page), bif 2 (the controls' 0x90400 and 0x91000).
  New FAULT_REQ bit 9 (0x200): the ZLS store [infer: from the access].
- Read post hoc (not scored): tri-wo-dst's store landed whole (4096 dwords changed, the 64 x 64
  window) and its colour image holds 512 of 4096 pixels (first wrong pixel (32, 0): the first 32 x
  16 tile) [infer]; tri-edm-dst stored nothing and wrote no pixel.
- Replay: vectors/closing/r9-faults/pte/{xf2,tri2}.table.json, replayed by
  crates/sgx-pipe/tests/pte_table.rs (17 rows modelled, 2 refused: isolation, the depth buffer).
  bif: no table (closing_tables.py has no alias kind; Q076 stays OPEN in bif.rs).
