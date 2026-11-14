# r19-k0 fold notes (for the builder's fold)

- Records: E1077 (stages k0 and kg: the module's knob-0 controls), E1078 (stage f0: the threshold
  update). `tools/records/new_record.py --session DIR`; appended corrections only.
- Scores: `score/score.py k0|kg|f0 KEPT/STAGE KEPT` (f0 needs kg of the same attempt for f0-geo).
  READING lines carry tl624 (0x0624's values in order), pb0-pb2, thr1-thr3, d35/d37/d38.
- E1078 text: H-UPD vs H-IGN vs H-LATE on thr2 and ovf2 (f0-down parts H-UPD from H-LATE);
  H-STORE is the EDM's store of dwords 10-13 into the descriptor ([infer] until read here); the
  module's dmesg line `render context: PB ..., final kicks' PB ..., list ... pages` (kept .dmesg)
  is the kernel premise (not scored: name it in the method).
- Builder's expectation: k0 and kg pass; H-UPD holds on every f0 row; f0-down's final overflows
  at 0x0624 0xe (or 0x2e after a raise).
- Deviations to state in the records: k0/kg split, k0-a0 a control (scene check, debug/scenecheck),
  f0-down N 0x30 (library-mock overflow rule), render_words has no TA command, f0 12 jobs.
- Kit gap to report (not fixed here): no `expect:` outcome for `tri --keep-overflow`'s overflow
  (rc 0 with a `job: failed: scene overflowed` line) in the library-mock replay.
- Vectors: `dpm/r19-k0-{k0,kg,f0}`, replay refused (README.md); E1077/E1078 to
  SIM_UNMODELLED.toml.
- Publish `lead/build_tool18b.sh` (t18b's recipe, first publication) with the session.
- Delete `.pytest_cache`, `__pycache__` and `debug/` build trees before publishing (debug/ is not
  frozen; `bash debug/scenecheck/run.sh`, `python3 debug/scenecheck/patch.py` and the out/*/scene
  hashes are the [check]'s
  evidence: cite their hashes, not the build trees).
