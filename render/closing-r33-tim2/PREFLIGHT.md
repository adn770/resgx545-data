# r33-tim2 preflight (the lead, before staging)

1. **Safe class**: no knob, no kreg, no register write, no planned fault or hang; regtimeline
   reads 0x012c, 0x0804 and 0x0acc through /dev/mem as root, as r33-tim did (E1131).
2. The laptop runs module 7CE8E38EDB97FC5EA4F6C90 (N1), loaded = installed, booted. If another
   module is booted before the run, the srcversion is stale: re-scaffold, do not edit.
3. `~/sgxfive-test-t10` (sha256 9bedc2d6...) and `~/regtimeline` (sha256 079f6359...) on the
   laptop (the kit's stage checks both). Nothing is built; t30 is not used.
4. No build or other GPU session at the same time: the `ivl` controls and H-SPACING are frozen
   from E1131's quiet laptop. The laptop must not be idled (POWER IDLE zeroes 0x0acc until a
   reset). `~/scratch/r33u` is this session's alone; at least 300 MB free on `~`.
5. Time: 15 jobs, about 2.5 minutes of stages as E1131, 5 to 7 with staging.
6. Order t1, t1d. A stop of either ends the session: report it, do not rerun blindly, do not
   reboot.
7. Record: E1133 (t1 and t1d).
8. After the run: `python3 score/score.py t1 out/ATT/t1` and the same for t1d.
