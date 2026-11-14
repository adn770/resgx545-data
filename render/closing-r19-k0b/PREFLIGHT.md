# r19-k0b preflight (the lead, before staging)

1. The laptop runs module E0CC40275493F8AEAD8180B (fork 456404fcffe5), loaded = installed, booted
   on the road (travel runbook). With B60AB0B4 back this freeze cannot run (the kit refuses).
2. `~/sgxfive-test-t10` (9bedc2d6...), `~/sgxfive-test-t18b` (58e79855...) and `~/regtimeline`
   (079f6359...) are present; the kit's stage checks the three. Nothing is built.
3. debugfs `render_pb_pages` reads 0x422 and `render_final_pb_pages` reads 0 (the kit restores
   both after every job and by its exit trap; t18b writes the second itself). `render_param`,
   `render_tadata`, `render_words` and `buf09` exist (the preflight checks them).
4. `~/scratch/r19k2` is free on the laptop; at least 300 MB free on `~`; python3 >= 3.10.
5. Time: 22 jobs, about 10 min with staging. Three stages: k0, kg (gated on k0), f0 (gated on k0
   and kg); a stop in any ends the session.
6. The first row is k0-pr1-1 (t10 `probe` under regtimeline, P 0x2b6): it must read 1 partial
   render and knob 0x294; if not, the stage stops (24 or 25): report before anything else runs
   (R19-1 a).
7. After the run: S3 (r19-own) runs whatever f0 gives; S2 and S4 need f0's controls.
