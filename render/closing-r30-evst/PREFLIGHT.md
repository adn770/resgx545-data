# r30-evst preflight (the lead, before staging)

1. **Safe class**: no knob, no kreg, no register write, no planned fault or hang. regtimeline
   reads through /dev/mem as root (as r20-own, r23-dpm and E547 did).
2. The laptop runs module E0CC40275493F8AEAD8180B, loaded = installed, on the travel cable
   (`ssh -o HostKeyAlias=cedar jtorra@10.42.0.2`). **Do not stage or run while the laptop builds a
   kernel** (round 30: it is building one now): a build's CPU load slows the sampler (the `ivl`
   controls would fail) and the reset-then-job rhythm. Stage only after the build ends and the
   lead's kernel session no longer needs the GPU; if a new module is installed or booted, the
   srcversion here is stale: re-scaffold, do not edit.
3. `~/sgxfive-test-t10` (sha256 9bedc2d6...) and `~/regtimeline` (sha256 079f6359...) on the
   laptop (the kit's stage checks both). Nothing is built for this session.
4. Never interleaved with another GPU session; `~/scratch/r30e` is this session's alone. At least
   300 MB free on `~`; python3 >= 3.10.
5. Time: 47 jobs, 8 to 10 minutes of jobs, 12 to 15 with staging [infer].
6. Order: e1, e5, e2, e3, e4 (`python3 kit/session.py run .`). A stop of e1 or e5 goes on; a stop
   of e2, e3 or e4 (a tick stop, a hang latch, a bad draw) ends the session: report it, do not
   rerun blindly. Do not reboot on any stop.
7. Premise of 0x0b14 (CR_USE0_SERV_EVENT): read before through the regs file in every kit job
   (E009's 200 reads, the runner's snapshots) but never sampled densely by regtimeline. If e2's
   first rows stop on the tick rule, the dense read is the suspect [infer]: report, keep e3/e4
   unrun.
8. After the run: `python3 score/score.py e1 out/ATT/e1 out/ATT` and the same for e5, e2, e3
   (it reads e1 from the attempt), e4.
