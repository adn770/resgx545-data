# r31-cc preflight (the lead, before staging)

1. **Safe class**: no knob, no kreg, no register write, no planned fault or hang; regtimeline
   reads through /dev/mem as root (0x0804, 0x0b14, 0x0c00, 0x0a74, 0x012c; E258 read all but
   0x0b14, which every kit snapshot reads).
2. The laptop runs module 7CE8E38EDB97FC5EA4F6C90 (N1), loaded = installed, booted. If another
   module is booted before the run, the srcversion is stale: re-scaffold, do not edit.
3. `~/sgxfive-test-t10` (sha256 9bedc2d6...) and `~/regtimeline` (sha256 079f6359...) on the
   laptop (the kit's stage checks both). Nothing is built; t30 is not used.
4. No build or other GPU session at the same time (the `ivl` controls and the timing; r31-kreg2
   must not run alongside). `~/scratch/r31c` is this session's alone; at least 300 MB free on `~`.
5. Time: 52 jobs, about 9 to 10 minutes of jobs, 12 to 15 with staging [infer].
6. Order c1, c2, c3, c4, c5. A stop of any stage ends the session: report it, do not rerun
   blindly, do not reboot.
7. Record: E1122 provisional (README); settle it against r31-kreg2 before the fold.
8. After the run: `python3 score/score.py STAGE out/ATT/STAGE` for c1 to c5.
