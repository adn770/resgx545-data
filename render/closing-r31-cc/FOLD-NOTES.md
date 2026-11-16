# r31-cc fold notes

- Record: E1122 (provisional; checked 2026-11-16: main 2ffa9a9 ends at E1121, no closing29 dir
  reserves E1122; r31-kreg2 is built in parallel and names none yet). One record, c1 to c5.
- Verdict to read first: c3 and c4's H-BIF-FIRST against H-BIF-LATER and the stage's
  H-BIF-HIDDEN. Before taking a "pre" BIF word as the firmware's, compare its word with the
  gma500 host flush (bit 3 alone, `mmu.c`) and the job's dmesg; a word with bit 2 is not the
  host's [infer].
- sgx-sim / fwsim: only if H-BIF-FIRST holds, the CR_CACHE_CTRL read after a kick before the
  run's write may answer the reset word (cite E1122) and the run's write after it; else the
  refusal stays and names the order read (H-CNT-*, H-CC-26, H-DMS). Test first.
- Premise the fold should check in the fwsim facts it may read (not this builder): the value the
  boot path wrote to CR_CACHE_CTRL in the sim. If it was | 0x10000000, the kit's post-reset
  0x0000ffff (E1120) already argues that a firmware write of bit 28 does not stay [infer], which
  H-CC-FW must then explain.
- If H-BIF-HIDDEN holds: report the kit row word for a debugfs `miscinfo` read before snap0
  (README, "The decisive form") as the tooling need; do not hand-roll it.
- Delete `debug/`, `.pytest_cache` and `__pycache__` before the fold publishes.
