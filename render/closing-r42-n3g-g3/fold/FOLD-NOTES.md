# r42-n3g-g3 fold notes (folder, 2026-11-23)

- One attempt, out/20261122-163956, on module 079DD0D13F231EEAC52FE0F (fork r42-kernel
  ec6511d5de87, the one-shot boot of 2026-11-22), after session G2 (closing29/r42-n3g-logs/
  runone-G3.out). Session G3 of closing29/n3g/design.md (section 3.5): stage lv (row LV, blob
  emitsb_sbc43s, `form=sbc43`, sideband 0xc43, image landv: land with V0 and V2 to attributes 0
  and 2), one row of three jobs: command 1 (the emit), command 6 on the next tick pass and command
  6 again after `sleep_ms` 2000. Kit and blobs: resgx545 c0e2dc36.
- The stage stopped at its one row (class hang, rc 4), so the driver did not score it; the frozen
  scorer was run by hand on the kept directory (fold/reproduce-lv-20261122-163956.out).
- Verdict: `Q128-N3G-LV RULE: LV-EARLY, LV-V`. PG, E0, T0 and J1 passed; B FAILED (BIF_FAULT
  0x0440000f) and J2 FAILED (job 2 never served). LV-V held as predicted. LV-EARLY held against
  its prediction (failed, the design's weak [infer]); LV-EARLY0 failed as predicted. LV-REBASE,
  LV-FILL and LV-HEAL were not reached and LV-FILLOK cannot tell.
- Readings: job 1 done (run id 1, 8 ticks), post sa0 = V0 0x32004000, sa2 = V2 0x32002000, sa1
  0x04400000, sa13 = pa1 = M13 0x005d3000 (G1's marker still there), pa12 and pa14 landv's markers
  0x5a5a3a18 and 0x5a5a3a1a.
- K5 (printed): job 1 BIF_FAULT 0 before and after; job 2's pre already BIF_INT_STAT 0x000d0400,
  BIF_FAULT 0x0440000f (list 15, page 0x04400000 = the post sa1), so the fault came on a stock pass
  between job 1's end and job 2's post. The tick stopped (the runner's alive check failed), job 2
  never served (cmd_after 6, dwords 224-255 0xdeadc0de), no gate ran; the kit's reset and health
  recovered it (closing29/r42-n3g-logs/health-r42-n3g-g3.log).
- [post hoc, infer] LC (E1176, E1178) stopped early at page 0 with post sa0 0; LV, with sa0 = V0
  and sa2 = V2, stopped early at the page in sa1. Restoring sa0 and sa2 does not prevent the early
  stop; the stop may follow a pointer through the first secondaries (the first unmapped one met).
- Records: E1183.
