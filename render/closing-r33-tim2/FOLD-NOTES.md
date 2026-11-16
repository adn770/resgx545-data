# r33-tim2 fold notes

- Built 2026-11-16 on resgx545 main 7dba6bd (kit as merged), data 052c0a8bf. Record E1133 (t1 and
  t1d). The rerun of r33-tim (E1131, controls failed on ivl; its fold on branches r33-fold-tim and
  r33-fold-tim-data, not merged at build time).
- Corrections against r33-tim's scorer (README "Why"): `ten`/`tover` take bits 23:0 up to 400000;
  the window is read against the pre-change line (`lcc`, `rcc`, `wmed`, `as20`, `as120`), not the
  change sample. E1131's kept rows give, with this scorer: nline 70 to 202, rcc -103 to +137 but
  t1-08 -29478, wmed 27.5 to 633.4, as120 7.3 to 346.7 (post hoc, while building).
- The fwsim rule to state if H-TIM-LINE, H-TIM-ASYNC and H-TIM-399 hold [infer]: `tim` =
  0x01000000 | ((lcc - 399.0 t) mod 400000), t us after the CR_CACHE_CTRL write; report the
  window's span and the count across it per row (READ lines: lcc, l26, d26, w26).
- Replay the frozen scorer on E1131's kept rows at the fold as a post-hoc comparison (not pinned).
- No vectors table; sgx-sim/fwsim changes test first on the kept `.txt` files.
