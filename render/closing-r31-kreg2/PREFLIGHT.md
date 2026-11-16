# r31-kreg2 preflight (the lead, before staging)

1. **Flagged session** (one register write of ours a row, `kreg:0x0a78=V`, values 0x00-0x3f, no
   planned fault or hang). The user's approval of the kit word is in closing29/DECISIONS-R29.md
   (round 29); this rerun is the round 31 "go" (plans/resgx545-question-closing.md, 2026-11-16).
   Run it while the user is present: an unrecoverable stall needs the user's power cycle.
2. The laptop runs module 7CE8E38EDB97FC5EA4F6C90 (fork 8bc0877e8603), loaded = installed, on
   the travel cable (`ssh -o HostKeyAlias=cedar jtorra@10.42.0.2`). Debugfs `kreg` exists and
   0x0a78 reads 0x2c before anything runs (the kit's preflight, read only).
3. Tools on the laptop, not rebuilt: `~/sgxfive-test-t10` (sha256 9bedc2d6...) and
   `~/sgxfive-test-t30` (sha256 b5ea288d...); the kit's stage checks both. t30's
   `probe --tri --vertices` prints `tri 64x64 #1: N us` (2cc9c5b).
4. Run alone (never interleaved with r31-cc: both use the GPU); `~/scratch/r31k` is this
   session's. At least 300 MB free on `~`; python3 >= 3.10.
5. Time: 307 jobs, about 35-40 minutes with staging [infer: r29-kreg's 5.6 s a job]; s0 about
   2 min, k1 about 14, k2 about 15 (L2 never timed on the laptop).
6. Order: s0, k1, k2 (`python3 kit/session.py run .`). k1 is gated on c0-tri and r1-r8, k2 on
   c0-tri and v1-v8; any stage's rc 24 ends the session.
7. Watch k1's and k2's first rows: a kreg write needs the firmware live and idle (-ENODEV,
   -EBUSY show as rc 19 before c01's job: a harmless stop to report, not to retry blindly).
   Watch v1: its `tri 64x64 #1` lines are L2's first timings on hardware.
8. Do not reboot on any stop; report to the user. After the run:
   `python3 score/score.py k1 out/ATT/k1 out/ATT`, the same for k2, and
   `python3 score/score.py q024 out/ATT` (the frozen retire rule: RETIRE, FINDING, NARROW or
   NOTHING).
