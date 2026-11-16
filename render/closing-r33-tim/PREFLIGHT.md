# r33-tim preflight (the lead, before staging)

1. **Safe class**: no knob, no kreg, no register write, no planned fault or hang; regtimeline
   reads 0x012c, 0x0804 and 0x0acc through /dev/mem as root (E1115, E1120, E1122 read the first
   two this way; E246's census and every kit snapshot read 0x0acc).
2. The laptop runs module 7CE8E38EDB97FC5EA4F6C90 (N1), loaded = installed, booted. If another
   module is booted before the run, the srcversion is stale: re-scaffold, do not edit.
3. `~/sgxfive-test-t10` (sha256 9bedc2d6...) and `~/regtimeline` (sha256 079f6359...) on the
   laptop (the kit's stage checks both). Nothing is built; t30 is not used.
4. No build or other GPU session at the same time (the `ivl` controls, the rate fit). The laptop
   must not be idled (POWER IDLE zeroes 0x0acc until a reset, pds_isa; the kit resets before every
   job). `~/scratch/r33t` is this session's alone; at least 300 MB free on `~` (every sample is
   stored: about 1 to 2.5 MB of text a job).
5. Time: 15 jobs, about 4 minutes of jobs, 6 to 8 with staging [infer].
6. Order t1, t1d. A stop of either ends the session: report it, do not rerun blindly, do not
   reboot.
7. Record: E1131 (t1 and t1d). E1132 is not used by this session (t2 not built); E1133 spare.
8. After the run: `python3 score/score.py t1 out/ATT/t1` and the same for t1d.
