# r16-tw preflight (the lead, before staging)

1. **SAFE CLASS, the round's last session** (R16-1 a, R16-2 a): run after r16-zls, r16-usse,
   r16-tex and r16-mte. No planned fault: any fault or hang stops tw16 (4) and ends the session.
2. The laptop runs module B60AB0B475DD1E8972419B5 (fork 2a650d74), loaded = installed. After a
   reboot to stock Arch this freeze cannot run: re-scaffold (a freeze is never rewritten).
3. `~/sgxfive-test-t14` sha256 aa550b94585aaf6eb5d9b7927d320ad31ea8d1e206b8c5e99e4435c7f0a83859
   (closing14/k14/TOOL14.built) and `~/sgxfive-test-t10` sha256 9bedc2d6... are on the laptop (the
   kit's stage checks both). Nothing is built for this session.
4. No debugfs knob is written; `reset` and `regs` exist (the kit's preflight).
5. `~/scratch/r16w` is free on the laptop (prefix r16w, this session's only); at least 300 MB
   free on `~`; python3 >= 3.10.
6. Time: 17 jobs, about 5 minutes with staging and preflight.
7. Stops (README.md "Stops"): any fault, hang or hook stop ends the session, including the H 16
   sentinel stop before the bilinear and H 64 rows; a failed recovery: do not reboot, report it.
8. Check before staging: README.md "Deviations" 1 (edge rows at W 64 and 128, not 16 and 32) and 3
   (H-MOVEH added at H 8 and 16, guarded at H 64 by the sentinel stop).
