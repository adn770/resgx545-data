# r14-flag preflight (the lead, before staging)

1. **Flagged session**: run only after every safe session of the round and r14-bif (t14's first
   use), with the user present (R14-5 a). The user OK'd exactly f1's 3 and f2's 4 planned faults:
   no hang, no reboot, no clock-gate write.
2. The laptop runs module B60AB0B475DD1E8972419B5 (fork 2a650d74), loaded = installed. After a
   reboot to stock Arch this freeze cannot run: re-scaffold (a freeze is never rewritten).
3. `~/sgxfive-test-t14` sha256 aa550b94585aaf6eb5d9b7927d320ad31ea8d1e206b8c5e99e4435c7f0a83859
   (closing14/k14/TOOL14.built) and `~/sgxfive-test-t10` sha256 9bedc2d6... are on the laptop (the
   kit's stage checks both). Nothing is built for this session; `lead/build_tool14.sh` is the
   recipe t14 was built with (copied from closing14/k14).
4. No debugfs knob is written; `reset`, `regs`, `render_param` and `render_tadata` exist (the
   kit's preflight).
5. `~/scratch/r14f` is free on the laptop (prefix r14f, this session's only); at least 400 MB
   free on `~` (768 x 640 pixel text); python3 >= 3.10.
6. Time: 11 jobs, about 5 minutes; 8 at most if all 7 planned rows fault.
7. Stops (README.md "Stops"): any stop in f1 ends the session (on_stop = end); a failed recovery
   (`SGX recovery failed`) or a hang stops its stage (24): do not reboot, report to the user.
8. Order: f1, f2 (`python3 kit/session.py run .`).
9. Check before staging: README.md "Deviations" 1 (f2's rows are words predicted to draw; t10
   dumps nothing after a failed render), 3 (6 f2 jobs) and 6 (after f2, run
   `python3 score/score.py dumps f2 out/ATT/f2` for the slot and flag verdicts).
