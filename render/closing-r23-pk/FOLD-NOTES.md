# r23-pk fold notes (builder)

Built 2026-11-15 on resgx545 b2b6bc0, data 40abeab5a, t22 (3c68e8d, 9b62d315...), module
E0CC40275493F8AEAD8180B. Records E1096 to E1098 (round 22's plan, section 6: Q019, Q181, Q123);
if pk's echo result needs its own record (R22-4 a), ask the lead for a fourth number.

- pk: R22-4 a. If H-ECHO holds and H-E391 / H-E125 / H-NOLOAD hold, E125, E391 and E568 stand (no
  correction). If an echo shows a word other than the poked one, or a repeat differs from its
  record, append corrections to the record(s) it repeats.
- q019: H-E391 on sa0-sa31. t22 (and every earlier tool) prints at most 32 changed scratch dwords,
  so E391's "never sa32-sa63" was read from sa0-sa31 and the count of 32 more changed [infer].
  The fold should say so in E391's correction only if the fold confirms it from E391's raw
  output (pds/attribute-room/.../raw.txt: every case ends `scratch 32 more changed`). A tool that
  prints all 64 is a tooling need (report, do not change shared tools).
- q019 H-ROWS: the scorer prints the fit table's sha256 before scoring held-out rows; quote it.
- q181: copy control holds and fills black with the echo showing xfer:17 bit 0 set: the fill does
  not load the set (Q181 retires: the copy path loads it, E037). Fills match H-LOAD: E568's black
  was the dangling poke; E568 needs a correction.
- q123: H-CARRY18 on b16 rows plus q123h: Q123 retire-capable (bits 16 and 17 carry; indices to
  8100 in one placed program). x18-b16 reads EXE bit 16 in the exe18 form (E428 had bit 17).
- Clean-up before the fold publishes: `.pytest_cache`, `__pycache__` (none expected: tests run
  with -p no:cacheprovider and dont_write_bytecode).
