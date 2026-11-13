# r13-tex fold notes (the builder folds after the run)

- Records (DECISIONS-R13.md): E1025 srgb3 (Q282), E1026 addr4 (Q177), E1027 t3c (Q078), E1028
  sb12 (Q046). Draft each method with `tools/records/new_record.py --session DIR`; appended
  corrections only; Q046's text fix (drop the modes 20/27 clause, E999; R13-11 a) in this fold.
- Rests on: E1016, E1004, E982, E723 (srgb3; c2's rule_b.py); E1000, E1017, E983, E565, E561
  (addr4; c2's rule_a.py, post_a.py); E564, E975, E1003, E722, E561 (t3c; c8's NOTE.md and
  q078_rule.py, post hoc); E383, E999 (sb12).
- What each verdict does: README.md "Predictions"; retirement only per R13-9 (a) (every open
  clause decided by held-out rows with passing controls; void clauses marked [infer]; the lead
  confirms): Q282 (FTZ-OUT on all six strided rows, threshold 2^-14; the trilinear row decides
  "other filters" or leaves it open), Q177 (H-MAX on the swept rows, one corner base, the type
  clause from E565's bd-st rows, README.md "Deviations" 3); Q078 and Q046 narrow only.
- Post hoc for the fold: addr4's printed "read less REPEAT" offsets per row (and the u16 row's
  reads if neither texel model holds: the 16-bit tile law is [infer]); t3c per-row levels read
  (decode the names with E561's tile law over the chain); sb12 the distinct-word counts and the
  per-pixel differences against E383's runs; srgb3 misses by weight (kx, ky) if FTZ-OUT misses.
- Kit need (shared tool, report only, never changed in a fold): the library-mock replay fails
  every `probe` of a program of ours (libsgxfive mock.c runs only its own copy shader and limm
  fills; any other program is "an unknown program", a fault), since 287031c made every bad end
  a refusal. Wanted: the replay counts the mock's own "unknown program" fault on a probe fill as
  "not modelled" (argv accepted, no usage line, no `job: rejected`), as tests/test_libmock.py
  does here, so a texture session needs no second tool name. r13-tex works around it with t10p
  (README.md "Deviations" 1).
- Tool weakness found (for HACKING "Known tool weaknesses"): resgx545-data
  `texture/p1141/support/texmodel.py` addresses a twiddled texture with plain Morton order over
  the whole side, not E561's 16 x 16 tiles: wrong above 16 a side (E564's an-t3b11 at pixel 16).
  gen/t3.py uses gen/addr.py's tile law instead (tests/test_gen.py checks E564's images).
- Sim in sync: sgx-sim tex.rs gets the flush's threshold and y stage (srgb3), the u-mode offset
  H-MAX and mode 5's regions (addr4, if decided), bits 12:11 (t3c, if decided); vectors
  `vectors/closing/r13-tex/*.table.json` (README.md "Replay vectors").
- Delete `.pytest_cache` and `__pycache__` before the fold publishes; `debug/` (the mocks and the
  library-mock build) is not published.
