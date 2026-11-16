# r29-kreg preflight (the lead, before staging)

1. **Flagged session** (one register write of ours a row, no planned fault or hang). The user's
   approval was relayed by the lead in round 29: the kit rule lifted for `kreg` to 0x0a78 in
   flagged stages (main adca992), Q024's session as `closing29/kreg/design.md` proposes. Confirm
   with the user before the first k1 row runs if that approval is not in DECISIONS-R29.md.
2. The laptop runs module E0CC40275493F8AEAD8180B (fork 456404fcffe5), loaded = installed, on the
   travel cable (`ssh -o HostKeyAlias=cedar jtorra@10.42.0.2`). Its debugfs has `kreg` (created
   beside `reset` and `regs` in sgxfive_debug.c); the preflight checks it and that 0x0a78 reads
   0x2c before anything runs (read only).
3. `~/sgxfive-test-t10` sha256 9bedc2d6... is on the laptop (the kit's stage checks it). Nothing is
   built for this session.
4. Run r29-kreg after r29-flag, never interleaved with it: both use the GPU; `~/scratch/r29k` is
   this session's alone. At least 300 MB free on `~`; python3 >= 3.10.
5. Time: 154 jobs, about 65 minutes [infer]; s0 about 4 minutes.
6. Order: s0 then k1 (`python3 kit/session.py run .`). k1 is gated on s0's controls; either
   stage's rc 24 ends the session.
7. Watch k1's first rows: a kreg write right after the runner's reset needs the firmware live and
   idle (the kernel's -ENODEV, -EBUSY); a refusal shows as rc 19 before c01's job, a harmless
   stop to report, not to retry blindly.
8. Do not reboot on any stop; report to the user. After the run: `python3 score/score.py k1
   out/ATT/k1 out/ATT` prints the per-value table and the headline.
