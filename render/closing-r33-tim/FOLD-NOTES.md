# r33-tim fold notes

- Built 2026-11-16 on resgx545 main f888bb7 (kit as merged), data 052c0a8bf. Record E1131 (t1 and
  t1d). E1132 not built: t2 has no safe form (README "t2"); E1133 spare.
- The fwsim rule to state if H-TIM-FREE, H-TIM-ASYNC and H-TIM-399 hold [infer]: at a read t us
  after the CR_CACHE_CTRL write, `tim` = 0x01000000 | ((tcc - 399.0 t) mod 400000), tcc the kept
  row's count at the change; or 400000 less the clocks since the last tick reload (E532: a tick
  served at once samples 0x01061a70). Report the window's measured span (d26 + w26) and the
  count drop across it per row: the bound fwsim needs for PDS #14's read.
- Read per row from the READ lines: tcc, t26 (the count at bit 26's rise), d26, w26, rpre, wres,
  wtail, wmax; t1d's rate and period at the densest interval.
- Post hoc (stated while building, not frozen): 208 of 208 kit snapshots in r30-evst2, r31-cc and
  r32-misc read 0x0acc with bit 24 set and bits 23:0 below 400000 (77 to 398501).
- sgx-sim/fwsim changes go test first (tools/fwsim seeds or replay rules, hw.rs's EVENT_TIMER read),
  on the kept `.txt` files only; no vectors table (closing_tables.py has no timeline kind).
- t2's needs for the lead (README): a flagged client-emit stage on t10/t30 (one planned fault a
  row, E488/E520) or a module change allowing one `emitpds` form in own tasks plus a kit job kind
  for own-task arms.
- Score: `python3 score/score.py t1 out/ATT/t1`, same for t1d; the driver writes
  out/ATT/score-STAGE.txt.
