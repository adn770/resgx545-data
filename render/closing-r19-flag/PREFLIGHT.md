# r19-flag preflight (the lead, before staging)

1. **Flagged session**: run after every safe session of the round, with the user present
   (DECISIONS-R19 R19-3 a, the user's OK given). It plans 2 faults or hangs at most (the two junk
   rows; both are readings), allows no unplanned one, and ends on any stop. No kernel change, no
   boot, no clock-gate write, no held reset, no new tool.
2. Run it only after r19-k0's controls read (S1's f0-same and f0-up: the final's 0x0624 = N -
   0x22; if they failed the control here stops the stage at its first job, harmlessly) and after
   every safe stage. If a safe session left an `SGX recovery failed` line or a health failure,
   do not run this one.
3. The laptop runs module E0CC40275493F8AEAD8180B (fork 456404fcffe5), loaded = installed
   (`modinfo -F srcversion gma500_gfx` and `/sys/module/gma500_gfx/srcversion`). After a reboot
   to another kernel or module this freeze cannot run: re-scaffold (a freeze is never rewritten).
4. `~/sgxfive-test-t18b` sha256 58e79855... (built from ec50498, see lead/TOOL18b.built) and
   `~/sgxfive-test-t10` sha256 9bedc2d6... are on the laptop (the kit's stage checks both).
   Nothing is built for this session; no cachix.
5. debugfs: `reset`, `regs`, `render_pb_pages`, `render_final_pb_pages`, `render_param`,
   `render_tadata`, `render_words`, `buf09`, `tadata_fill` exist (the kit's preflight); the knobs
   read their defaults (render_pb_pages 0x422, render_final_pb_pages 0) before the session and are
   restored after every job.
6. `~/scratch/r19f` is free on the laptop (prefix r19f, this session's only); at least 300 MB free
   on `~` (TA dumps of a few tens of KiB a row); python3 >= 3.10.
7. Time: 3 jobs, about 4 minutes (7 if both planned rows fault or hang), plus about 3 for staging
   and the preflight.
8. Run: `python3 kit/session.py stage .` then `python3 kit/session.py run .` (log outside the
   session dir). Stops: rc 4 (an unplanned fault or hang, any other failure), 16 or 5 (health), 24
   (the control off, a failed recovery, a fault of the wrong kind), 25 (control without a reading).
   Do not reboot on any stop; report to the user.
9. Score: `python3 score/score.py fl out/ATT/fl` (H-NOLOAD expected [infer]).
