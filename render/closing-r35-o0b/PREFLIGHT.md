# r35-o0b preflight (the lead, before staging)

1. Safe class: no planned fault or hang, `#limit 0`, no knob, no kreg.
2. The laptop at home: `SGX_TARGET_HOST=jtorra@192.168.12.234` (HostKeyAlias cedar), the test
   kernel booted, module 7CE8E38EDB97FC5EA4F6C90 loaded = installed.
3. `~/sgxfive-test-t10` (sha256 9bedc2d6...) on the laptop.
4. `~/scratch/r35q` free; at least 300 MB free on `~`.
5. One stage `o`, 32 jobs, about 7 minutes. Do not reboot on any stop; report it.
6. After the run: `python3 score/score.py q073 out/ATT` (README.md "Retire rule").
