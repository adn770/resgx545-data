# r32-kreg3 fold notes (builder)

- Built 2026-11-16 from resgx545 main bf0ba56, data 6b5c5112a; module 7CE8E38EDB97FC5EA4F6C90;
  tools t10 (as r29-kreg, r31-kreg2) and t30 (r30-pde's build). Nothing built for this session.
- Records: E1128 (s0, the calibration: every form's references, spread, the PICK) and E1129 (the
  picked k stage), assigned by the lead. With no pick, E1129 is not written (or E1128 says why).
- User decision 2026-11-16 (answer a): keep the question's load (t30 `probe --tri pixel --width
  64 --height 64 --vertices 1500`), more renders a job; safe calibration with a frozen pick rule
  (first form with references' IQR <= 0.8 percent; 64x64 at 10, 20, 40, then 1024x768 at 10, 20,
  40; none: stop before any flagged row); E1124's median and one-outlier rules kept; retire only
  on 64 of 64.
- Library-mock check before the build: debug/probe/run.sh (20 and 40 files at 64x64, 10 and 40 at
  1024x768: one timing line and one identical o0 line a file, rc 0).
- At the fold: score s0 (FORM, PICK lines into E1128), the picked k stage and
  `score.py q024 out/ATT`; Q024's question file: retire only on `Q024: RETIRE`, with the answer
  the README states (both loads: E1124 and E1129); FINDING narrows to the value; NOTHING leaves the
  question as it is with the readings recorded. No sim change (timing is unmodelled).
- If the pick is a 1024x768 form, say in E1129 that those triangles are not small (each about a
  quarter of the target [infer]): the clause is then answered for 500 triangles at 1024x768.
- Drop `debug/`, `__pycache__` and `.pytest_cache` from the published copy.
