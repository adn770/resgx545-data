# r17-tw preflight (the lead, before staging)

1. **SAFE CLASS, the round's second session** (R17-1 a): run after r17-zls. No planned fault: any
   fault or hang stops tw17 (4) and ends the session.
2. The laptop runs module B60AB0B475DD1E8972419B5 (fork 2a650d74), loaded = installed. After a
   reboot to stock Arch this freeze cannot run: re-scaffold (a freeze is never rewritten).
3. `~/sgxfive-test-t14` sha256 aa550b94585aaf6eb5d9b7927d320ad31ea8d1e206b8c5e99e4435c7f0a83859
   (closing14/k14/TOOL14.built) and `~/sgxfive-test-t10` sha256 9bedc2d6... are on the laptop (the
   kit's stage checks both). Nothing is built for this session.
4. No debugfs knob is written; `reset` and `regs` exist (the kit's preflight).
5. `~/scratch/r17w` is free on the laptop (prefix r17w, this session's only); at least 300 MB
   free on `~`; python3 >= 3.10.
6. Time: 14 jobs, about 5 minutes with staging and preflight.
7. Stops (README.md "Stops"): any fault, hang or hook stop ends the session, including a
   reference without its sentinel before its width's rows; a failed recovery: do not reboot,
   report it.
8. Check before staging: README.md "Deviations" 1 (the W 2048 pair, the plan's [check], last;
   drop it for the plan's 12 rows) and 3 (the left wrap rests on the LEFT-WRAP line, not on
   H-WIDE-G's within-1 SUMMARY).
