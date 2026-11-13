# r13-flag preflight (the lead, before staging)

1. **Flagged session**: run only after every safe session of the round (r13-tex, r13-zls, r13-dpm,
   r13-isp), with the user present (R13-3 a, R13-4 a). The user OK'd planned faults and hangs the
   kernel recovers only: no reboot, no clock-gate write, no held reset.
2. The laptop runs module B60AB0B475DD1E8972419B5 (fork 2a650d74), loaded = installed. After a
   reboot to stock Arch this freeze cannot run: re-scaffold (a freeze is never rewritten).
3. `~/sgxfive-test-t10` sha256 9bedc2d6... is present (t10 and t10p name it; the kit's stage
   checks it). Nothing is built for this session.
4. No debugfs knob is written; `reset` and `regs` exist (the kit's preflight).
5. `~/scratch/r13f` is free on the laptop (prefix r13f, this session's only); at least 300 MB free
   on `~`; python3 >= 3.10.
6. Time: 27 jobs, about 15 minutes (20 at most); f3 holds one 60 s idle.
7. Stops (README.md "Stops"): a failed recovery (`SGX recovery failed`) stops its stage (24) and
   the gates skip every later stage; a failed health stops the session (16, 5): do not reboot,
   report to the user.
8. Order: f1, f2, f3 (`python3 kit/session.py run .`). If f1 or f2 stops on its rule (24) without
   a failed recovery, f3 still runs: the lead may stop the driver there instead (Ctrl-C between
   stages) if the user wants F3 only after clean fault stages.
