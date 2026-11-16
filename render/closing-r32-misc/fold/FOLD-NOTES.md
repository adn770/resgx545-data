# r32-misc fold notes

Attempt 20261116-185655 (fold/lead-run.log, fold/lead-stage.log): rc 0, 11 jobs in two stages,
every job drew exactly, no fault, no hang, no stop; every control PASS (m1-c1, m1-c3: cache
0x0000ffff, cache9 0x1000ffff, kicks 1; m1-c2: mi 1, kicks 2; m2-c1: ivl 856 ns, mi 1, kicks 2).
The scores reproduce byte for byte (fold/reproduce.out against the run's score-STAGE.txt).
Records: **E1126** (m1) and **E1127** (m2), as the frozen README reserves them.

**Kit base.** The session's kit is a byte copy of resgx545 80d9f2a (branch r32-miscinfo, since
merged into main: 4f30d5b holds 45bbaaa, f09c011 and 80d9f2a). Data pinned 6b5c5112a, data main
at the fold.

## Frozen verdicts (all non-control rows held out)

- m1: **H-CC-FW** held 7 of 7 (m1-01..06 and m1-c2's held clause: snap0 0x0000ffff after the
  word's served GETMISCINFO), **H-CC-HW** refuted 7 of 7, **H-CC-ONE** held 7 of 7 (snap9
  0x1000ffff after the triangle), **H-MI-LAT** held 6 of 6 (154 to 161 us).
- m2: H-CC-FW held 3 of 3 (snap0 of both rows and m2-01's first timeline sample; m2-c1's
  `ccfirst` clause too: 0x0000ffff), H-CC-HW refuted 3 of 3, **H-CC-LAT** held 2 of 2 (24.41 and
  25.15 ms, inside E1122's 18.3 to 25.2 and the frozen 10 to 40), H-CC-ONE held 3 of 3 (one
  change, to 0x1000ffff), H-MI-LAT 1 of 1 (148 us).

## Post hoc (fold/posthoc.py, posthoc.txt; not frozen)

- The kernel logged 26 GETMISCINFO answers over the two stages: one after each of the 17 boot
  kicks (`sgxfive_ident_ask`, 125 to 252 us) and one for each of the 9 word reads (148 to 161
  us, the same as NAME.miscinfo's). Every row's count before its snap0, the held rows too, is
  the frozen one: 1 without the word, 2 with it.
- So before every snap0 of a word row two served GETMISCINFO commands ran after the reset: the
  boot's, with the firmware file's cache control (meta word 30; doc/specs/boot_sequence.md), and
  the word's, with none (`sgxfive_command` clears it once sent, fork 8bc0877e8603). Neither
  carries INVAL_DATA (bit 3). All 11 snap0 read 0x0000ffff, 3 s after the last answer.

## What it decides, what it does not

- Decided [HW]: a served kick whose command carries no INVAL_DATA does not set CR_CACHE_CTRL
  bit 28; the word stays the reset word 0x0000ffff (9 of 9 word rows, 2 controls, and r31-cc's
  52 snap0 after the boot's own kick, post hoc). A triangle's kick after it sets bit 28 as
  without it, 24.4 and 25.2 ms after t10 starts. With E1123 (the bit follows the kick pass's
  BIF write) bit 28 is tied to the command's INVAL_DATA, not to the kick.
- Not decided: whether bit 28 is the firmware's literal `| 0x10000000` (E013) or the hardware's
  response to the firmware's INVAL_DATA work (both need bit 3; the kit has no kick with
  INVAL_DATA alone); what the firmware's own read after a TA kick returns (inside one sample,
  E1123); whether a kick with only BIF bits other than INVAL_BIF_PD differs; anything about the
  other CR_EVENT_STATUS bits Q111 names.

## sgx-sim, fwsim

sgx-sim already answers a CR_CACHE_CTRL read after a served kick with the reset word until the
run writes the register (E1122's rule, crates/sgx-sim/src/hw.rs): a run that never writes it
(a GETMISCINFO pass, no INVAL_DATA) reads 0x0000ffff, which E1126 now measures. The fold adds a
test that pins that answer and cites E1126 in the rule's notes and tools/fwsim/seeds.toml; no
answer changes. No vectors table: snapshots and a timeline, no closing_tables kind.
