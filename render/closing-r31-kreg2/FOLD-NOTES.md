# r31-kreg2 fold notes (builder)

- Built 2026-11-16 from resgx545 main 2ffa9a9, data dc838e60f; module 7CE8E38EDB97FC5EA4F6C90;
  tools t10 (as r29-kreg) and t30 (r30-pde's build, recipe
  data:render/closing-r30-pde/lead/build_tool30_laptop.sh). Nothing built for this session.
- Records: E1124 (k1, L1) and E1125 (k2, L2) [builder's pick; r31-cc had claimed none, so
  E1122-E1123 are left to it; the lead renumbers if needed and the fold says so].
- The rule this rerun fixes: E1114's frozen control rule failed on one slow control job (c11, a
  mean of renders 2-6 at +3.04 percent). Fixed BEFORE this run: the median of renders 2-6, and
  at most one control a stage outside its band (named, excluded). The rule was chosen knowing
  E1114 (tests replay E1114 under it): say so in E1124, a calibration, not evidence.
- L2's form verified on t30's library mock first (debug/probe, not frozen): the timing line
  prints once a file, six files make six renders a job.
- At the fold: score s0, k1, k2 and `score.py q024 out/ATT`; k2's BOUND2 is s0's (print it in
  E1125's claim); Q024's question file: retire only on `Q024: RETIRE`, with the answer the README
  states; else narrow with the decided load's clause. No sim change (timing is unmodelled).
- Drop `debug/`, `__pycache__` and `.pytest_cache` from the published copy.
