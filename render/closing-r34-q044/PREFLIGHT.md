# r34-q044 preflight (the lead, before staging)

1. Safe class: no planned fault or hang, `#limit 0` in every stage, no knob, no kreg; mode 14
   never runs (E031: it faults). Modes 12 and 13 (pw, last) write past the target into the
   scratch, as E031's two runs did without a fault.
2. Module 7CE8E38EDB97FC5EA4F6C90 loaded = installed (the laptop was building a kernel module when
   this was built: check the module did not change); travel cable, HostKeyAlias cedar.
3. `~/sgxfive-test-t10` (sha256 9bedc2d6...) on the laptop.
4. `~/scratch/r34p` free; at least 300 MB free on `~`.
5. Order: s0, p1, p2, pw. 198 jobs, about 45 minutes, 55 at most. Do not reboot on any stop;
   report it.
6. After the run: `python3 score/score.py retire out/ATT` (README.md "Retire rule").
