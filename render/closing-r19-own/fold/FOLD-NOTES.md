# r19-own fold notes (builder, 2026-11-14)

- Records: E1084 (own2, Q192), E1085 (own1, Q191). Prefix r19o. Tool t18b (recipe published from
  this session's lead/, cited `data:render/closing-r19-own/lead/build_tool18b.sh`).
- Finding while building [infer, to confirm in the fold, a correction to E631 if it holds]:
  E631 (and Q191's 11.38 text) call pages 1 to 3 of the 1024x768 partial owner its control, OTPM
  and state pages. By the fork's layout (sgx_render_tadata_layout_in at 456404fcffe5, KUnit table)
  a 1024x768 context's tail pointers take pages 0 to 3 and the control, OTPM and state pages are
  4, 5 and 6 (E591 and E627 already read the state page at 0x6000). Read again in E631's kept
  records (data dpm/partial-model-batch/dumps, ow-part-*-k, fb-part-*-k-r2): with flag 0x4 the 5
  words 0x002000xx sit in page 4 = the control page, at dwords 0, 1, 4, 5, 8 (the family of the
  64x64 control word 0x00200047); with 0xc the control and OTPM pages hold nothing. So "the
  partial owner leaves no owner word in its control, OTPM or state pages" holds for the right
  pages too with 0xc, and the 0x4 words are in the control page, not "page 4 besides them". The
  fold appends the correction to E631 (and edits only its own clauses of Q191).
- Score: `python3 score/score.py own2 out/ATT/own2` and `own1`; FITS lines count each model.
- Vectors: own2/own1 tables refused (SIM_UNMODELLED E631's reason); E1084, E1085 to that list too.
