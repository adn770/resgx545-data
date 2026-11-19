# r40-s-pass fold notes (folder, 2026-11-19)

- One attempt, out/20261119-170734 (the lead, user present), on module 0CDFCDB73D76F39FE9E593C
  (fork f9453424bf71), Z's boot (uptime 5643 s at the arm), right after r40-s-s2's stop and
  reset, no rebuild. Row S-PASS (the design's row S): against Z only the pass changes, the first
  tick pass that sees cmd 1, no kick. Blob emitsb14 (resgx545 c3f9f67: emitsb with #14's word
  0xfb20b10800c08184 and nothing else; the module's verifier accepts it unchanged, KUnit on the
  Mac shim 34 of 34, closing29/r40-s-logs/shim-emitsb14.log). crumb3's U0 0x080401ef (R4's:
  emitsb's entry 1).
- The arm logged `own_code: 644 bytes accepted` and `own task armed: ... emit image 0x30011100
  ... pds=crumb3 pdsat=fw14 pds2=req form=fw14`; health ok (201, 230, 258).
- The frozen scorer (score-own.txt; fold/reproduce-own.out the same bytes): every control passed
  (PG, E0, T0, B), `Q128-SP RULE: SP-DONE: all ran`. X0 0x5a5a3303, T 0x005a3305 in snap9
  (snap0 0x01050794), S1 0x5a5a3304, M4 and run id 1, state 2; done after 0.6 ms; Δtick 9 from
  the command write (38.3 ms); alive false by design. Gate and post exact; the disarm reset
  brought the tick back (297, 326, 353).
- LANDING (printed, not scored): as Z's; pa0 and pa2 are not V0 and V2.
- Records: E1159 (this session).
