# r35-o0 preflight (the lead, before staging)

1. Safe class: no planned fault or hang, `#limit 0`, no knob, no kreg.
2. Boot the test kernel first: module 7CE8E38EDB97FC5EA4F6C90 loaded = installed (the laptop
   was on stock Arch on 2026-11-17); travel cable, HostKeyAlias cedar.
3. `~/sgxfive-test-t10` (sha256 9bedc2d6...) on the laptop.
4. `~/scratch/r35o` free; at least 300 MB free on `~`.
5. One stage `o`, 27 jobs, about 6 minutes. Do not reboot on any stop; report it.
6. After the run: `python3 score/score.py q073 out/ATT` (README.md "Retire rule").
