# r30-evst2 preflight (the lead, before staging)

1. **Safe class**: no knob, no kreg, no register write, no planned fault or hang; regtimeline
   reads through /dev/mem as root.
2. The laptop runs module 7CE8E38EDB97FC5EA4F6C90 (N1), loaded = installed, booted. If another
   module is booted before the run, the srcversion is stale: re-scaffold, do not edit.
3. `~/sgxfive-test-t10` (sha256 9bedc2d6...) and `~/regtimeline` (sha256 079f6359...) on the
   laptop (the kit's stage checks both). Nothing is built.
4. No build or other GPU session at the same time (the `ivl` controls and the timing).
   `~/scratch/r30f` is this session's alone; at least 300 MB free on `~`.
5. Time: 41 jobs, about 7 to 8 minutes of jobs, 10 to 12 with staging [infer].
6. Order e1, e5, e2, e3, e4. A stop of e1 or e5 goes on; a stop of e2, e3 or e4 ends the
   session: report it, do not rerun blindly, do not reboot.
7. The laptop's clock was about 2 h 50 min behind in r30-evst; if not yet fixed, note it (the
   readings are regtimeline offsets, wall times are only labels).
8. After the run: `python3 score/score.py STAGE out/ATT/STAGE out/ATT` for e1, e5, e2, e3, e4.
