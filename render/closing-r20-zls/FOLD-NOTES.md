# r20-zls fold notes (builder, 2026-11-15)

## Deviations from the plan (rank-round20 section 3)

- zm's rival: the library writes its sentinel into the target before every kick (libsgxfive
  render.c, `sgxfive_render_tri_flags`, the fb fill loop), so the partial render's colour cannot
  reach the final's check and H-KEEP (wrong outside = |T1 \ T2| = 50162) cannot occur. zm reads
  H-REPAINT (wrong 0) vs H-HOLES (sentinel pixels left, `other` > 0). Q038's colour clause stays
  open (R20-3 b).
- zr passes `--depth-pages 0x340` (as r19's dzc): with the default 784 pages the G 33 store of a
  1024x768 target spills past its buffer (E1081's 19968 `other` pixels) and 30720 window dwords
  fall outside the dump. zc-geo keeps the default (E1081's row byte for byte).
- zc runs zc-geo first: its store after the final is a by-name REQUIRED file, so a stop on a later
  zc row still finds it kept.
- zc's controls gate zr, zm and zq (the plan: zc's store controls off, nothing else runs); a hook
  stop in zc ends the session (`on_stop = "end"`).
- zc-nl and zc-ld run on t18b under rt (r19 ran them on t10), so zregs reads their registers.
- t10 is bound for the kit's health fill and triangle only.
- zq's sign count is over the store window only (r19's zs counted the whole depth.2, whose marker
  fill 0xd019.... has bit 31 set: the 35840 "signed" dwords of E1082's H-PRSIGN rows were the
  fill [infer, to check at the fold: a correction to E1082 may be needed]).
- zq's raise: E625's 2 (P - 0x22) < U + 2 with U 49 (the ramp's peak on r19's kept zs rows)
  gives 0x44 and 0x4c not raised and still overflowing (thr0 34, 42 < 49); read per row.

## For the fold

- Score: `python3 score/score.py STAGE out/ATT/STAGE out/ATT` (zr reads zc's zregs from ROOT/zc).
- zr's READING lines carry the load buffer after the final (0.25 count in the window): if H-NOSTORE
  holds, that reading says whether the final wrote into the load buffer instead (dzo's single
  buffer kept depth with cleared signs, E1081).
