# r36-n3 fold notes (builder)

- Built 2026-11-18 from resgx545 main b9098a4, data 6b2938440, module C01FB320 (fork c78059370315),
  t30 as health tool (r35-sa's binding).
- Records: E1148-E1155 only. Likely: one record for own's landing (DECIDED-PA / NOT-PA / NONE /
  OPEN), one for post if it carries anything beyond health.
- Fold: if DECIDED-PA, fwsim/sgx-sim's emitted `douta` goes to pa (test first, E1133's sa landing
  refuted, cite the kept pages); if NOT-PA, record "not pa, sa unchanged" only; Q128 narrows by its
  own clause, never retires.
- Decided while building: H-NONE ends the session at its first row (a job whose entry 1 never runs
  is never done: runner rc 4), so the rule reads it on the first kept row, not on held-out rows; the
  hooks stop on sa1/sa3 too (conservative, beside the design's sa0/sa2); the host fills slots 2-4
  (A/B) through params so an unwritten slot shows; V0-V3 per row from snap0's ta3dctl lines (hooks
  fall back to r35-sa's values only for a snap0 without them).
