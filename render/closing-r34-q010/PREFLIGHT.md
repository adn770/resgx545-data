# r34-q010 preflight (the lead, before staging)

1. **Safe class**: no expectfault, `#limit 0`, no knob, no kreg, no planned fault or hang.
2. The laptop runs module 7CE8E38EDB97FC5EA4F6C90, loaded = installed. The laptop was building a
   kernel module when this was built: if a new module is installed or booted before the run, the
   srcversion is stale: re-scaffold, do not edit.
3. No build or other GPU job at the same time (a foreign job between a load and its read would be
   an unplanned X). `~/scratch/r34q` is this session's alone; at least 300 MB free on `~`.
4. `~/sgxfive-test-t10` (9bedc2d6...) and `~/sgxfive-test-t30` (b5ea288d...) on the laptop (the
   kit's stage checks both). Nothing is built.
5. Time: 32 jobs, about 12 minutes (15 at most), 180 s of it idle waits (t4-rd, t5-rd).
6. One stage `c`; a stop ends the session: report it, do not rerun blindly, do not reboot.
7. Record: E1134.
8. After the run: `python3 score/score.py c out/ATT/c` and `python3 score/score.py q010 out/ATT`.
