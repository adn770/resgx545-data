# r32-kreg3 preflight (the lead, before staging)

1. **Flagged session** (one register write of ours a row, `kreg:0x0a78=V`, values 0x00-0x3f, no
   planned fault or hang), only in the k stage s0 picks. The user's approval of the kit word is in
   closing29/DECISIONS-R29.md (round 29); this session's form rule is the user's decision of
   2026-11-16 (answer a). Run it while the user is present: an unrecoverable stall needs the
   user's power cycle.
2. The laptop runs module 7CE8E38EDB97FC5EA4F6C90, loaded = installed, on the travel cable
   (`ssh -o HostKeyAlias=cedar jtorra@10.42.0.2`). Debugfs `kreg` exists and 0x0a78 reads 0x2c
   before anything runs (the kit's preflight, read only).
3. Tools on the laptop, not rebuilt: `~/sgxfive-test-t10` (sha256 9bedc2d6...) and
   `~/sgxfive-test-t30` (sha256 b5ea288d...); the kit's stage checks both.
4. Run alone (never interleaved with another GPU session); `~/scratch/r32k` is this session's.
   At least 300 MB free on `~`; python3 >= 3.10.
5. Time: about 30-45 minutes with staging (194 jobs; 49 with no pick, about 12 minutes)
   [infer: E1125's 5.4 s a job plus the extra renders]. Budget 60 minutes.
6. Order: s0, then the six k stages in order; each k gate opens only on s0's PICK
   (`gate-k*.txt` names it), so at most one runs; the others print SKIPPED. Any stage's rc 24 ends
   the session.
7. Watch s0's first 1024x768 rows (vl*-1): the first 1024x768 renders of t30 on this module;
   watch the picked k stage's first row: a kreg write needs the firmware live and idle (-ENODEV,
   -EBUSY show as rc 19 before c01's job: a harmless stop to report, not to retry blindly).
8. Do not reboot on any stop; report to the user. After the run:
   `python3 score/score.py s0 out/ATT/s0 out/ATT` (FORM and PICK lines), the picked stage's
   `python3 score/score.py kNN out/ATT/kNN out/ATT`, and `python3 score/score.py q024 out/ATT`
   (the frozen retire rule: RETIRE, FINDING or NOTHING).
