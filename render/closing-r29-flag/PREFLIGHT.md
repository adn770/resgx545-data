# r29-flag preflight (the lead, before staging)

1. **Flagged session**, with the user present (DECISIONS-R29: R29-1 to R29-6 (a)). The approval
   covers 8 planned faults and 5 recovered hangs with `#limit`s capped at 14; this build plans 4
   faults and 4 hangs and allows 9 events (README.md deviations 1, 2, 5). No kernel change, no
   boot, no clock-gate write, no held reset.
2. The laptop runs module E0CC40275493F8AEAD8180B (fork 456404fcffe5), loaded = installed, on the
   travel cable (`ssh -o HostKeyAlias=cedar jtorra@10.42.0.2`, plans/resgx545-travel-runbook.md).
   After a reboot into another kernel this freeze cannot run: re-scaffold (a freeze is never
   rewritten).
3. `~/sgxfive-test-t10` sha256 9bedc2d6..., `~/sgxfive-test-t14` sha256 aa550b94... and
   `~/sgxfive-test-t22` sha256 9b62d315... are on the laptop (the kit's stage checks all three).
   Nothing is built for this session.
4. debugfs: `reset`, `regs`, `vm_pte_addr`, `vm_pte_flags`, `render_param`, `render_tadata` exist
   (the kit's preflight); the knobs read 0 before the session and are restored after every job.
5. `~/scratch/r29f` is free on the laptop (prefix r29f, this session's only); at least 300 MB free
   on `~` (three 512 x 512 TA dumps and `--pixels` texts of about 3 MB a row); python3 >= 3.10.
6. Time: 28 jobs, about 16 minutes; about 20 if all 9 allowed events happen.
7. Order: s0, f1, f2, h1, h2 (`python3 kit/session.py run .`). Each flagged stage is gated on its
   s0 references (h2 on its own control) and on no `SGX recovery failed` line earlier; its rc 24
   ends the session.
8. Watch: f2's two 0x90004 TA faults at 512 x 512 (n = 2: E509's n = 2 faults and E1074's
   recovered at the first health try; its 640 x 480 ones did not). A strict-health stop (16) is a
   stop to report to the user, not to retry.
9. Do not reboot on any stop; report to the user. After the run, `python3 score/score.py q010
   out/ATT` prints Q010's retire rule (R29-3 a).
