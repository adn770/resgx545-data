# r40-s-sb fold notes (folder, 2026-11-19)

- One attempt, out/20261119-170536 (the lead, user present), on the r39-kernel module
  0CDFCDB73D76F39FE9E593C (fork f9453424bf71, closing29/kernel39c/deliver/f9453424bf71/manifest),
  Z's boot (kernel log uptime 5524 s at the arm), no rebuild. Row S-SB, one of the splits of Z
  (r39-n3d-z, E1156): against Z only `s2` changes, 0 instead of 0x00020000.
- The arm logged `own_code: 684 bytes accepted` and `own task armed: ... emit image 0x30011100
  ... pds=crumb3 pdsat=fw14 pds2=0 form=fw14`; health ok (201, 230, 257). Blob emitsk14 (Z's,
  word 0xfb20b10800c08184, sideband 0x843), the kick a GETMISCINFO read (answered after 206 us).
- The frozen scorer (score-own.txt; fold/reproduce-own.out the same bytes): every control passed
  (PG, K0, K1, T0, B), `Q128-SB RULE: SB-DONE: all ran`. X0 0x5a5a3303, T 0x005a3305 in snap9
  (snap0 0x01007265 running), S1 0x5a5a3304, M4 0x5a5a3302 and run id 1, state 2; done after
  10.6 ms; Δtick 7 from the kick; alive false as T1 stops the tick by design. The gate (tick
  stopped) and post (fold/reproduce-post.out) drew the triangle and the fill exactly; the disarm
  reset brought the tick back (290, 319, 347).
- LANDING (printed, not scored): pa0-pa3 and sa0-sa3 as Z's; pa0 and pa2 are not V0 and V2.
- Records: E1157 (this session); E1158 r40-s-s2, E1159 r40-s-pass, E1160 r40-s-sbt.
