# r35-pk preflight (the lead, before staging)

1. Safe class: no planned fault or hang, `#limit 0` in every stage, no knob, no kreg; pack modes
   14, 22, 26, 34 never run. Modes 12 and 13 (pw, last) write past the target into the scratch,
   as E031's two runs and r34-q044's pw did without a fault.
2. Module 7CE8E38EDB97FC5EA4F6C90 loaded = installed: the laptop rebooted into stock Arch after
   this was built, so boot the test kernel first; travel cable, HostKeyAlias cedar.
3. `~/sgxfive-test-t10` (sha256 9bedc2d6...) on the laptop.
4. `~/scratch/r35p` free; at least 300 MB free on `~`.
5. Check tests/test_score.py exists and passes (D2: every frozen name held and FAILED).
6. Order: s0, r1, r2, r3, pw. 92 jobs, about 20 minutes, 30 at most. Do not reboot on any stop;
   report it.
7. After the run: `python3 score/score.py narrow out/ATT` (README.md "Narrow rule").
