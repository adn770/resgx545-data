# r18-flag preflight (the lead, before staging)

1. **Flagged session**: run after every safe session of the round, with the user present
   (DECISIONS-R18). The approval covers 8 planned faults and 3 recovered hangs; this build plans
   7 faults and 3 hangs and allows 15 events (README.md deviation 1). No kernel change, no boot,
   no clock-gate write, no held reset.
2. The laptop runs module B60AB0B475DD1E8972419B5 (fork 2a650d74), loaded = installed. After a
   reboot to stock Arch this freeze cannot run: re-scaffold (a freeze is never rewritten).
3. `~/sgxfive-test-t10` sha256 9bedc2d6... and `~/sgxfive-test-t14` sha256 aa550b94... are on the
   laptop (the kit's stage checks both). Nothing is built for this session.
4. debugfs: `reset`, `regs`, `vm_pte_addr`, `vm_pte_flags`, `render_param`, `render_tadata` exist
   (the kit's preflight); the knobs read 0 before the session and are restored after every job.
5. `~/scratch/r18f` is free on the laptop (prefix r18f, this session's only); at least 300 MB free
   on `~` (two TA dumps of 4.6 MB a row); python3 >= 3.10.
6. Time: 26 jobs, about 15 minutes; about 20 if all 15 allowed events happen.
7. Order: s0, f1, f2, f3, f4, h1, h2 (`python3 kit/session.py run .`). Each flagged stage is gated
   on its s0 references and on no `SGX recovery failed` line earlier; its rc 24 ends the session.
8. Watch: f3-k4 (a 0x90004 TA fault). E509's 0x90004 faults at 640 x 480 each needed two health
   retries; at 256 x 256 none did, and f3 runs at 384 x 256 (n = 2). A strict-health stop (16)
   after f3 is a stop to report to the user, not to retry.
9. Do not reboot on any stop; report to the user. After f2, `python3 score/score.py dumps f2
   out/ATT/f2` reads the load rows' stores (README.md deviation 5).
