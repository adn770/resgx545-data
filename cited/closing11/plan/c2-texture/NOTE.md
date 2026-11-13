# c2-texture: Q177 / E1000 (check A) and Q282 / E1004 (check B), offline

Rules (frozen before scoring, FREEZE.log): A `rule_a.py` sha256
1dc239182dd4e2b975e958ea4f23df70fd49c6e0fdc4b6c7b18c401e1b203208; B `rule_b.py` sha256
84bd426400514091ae58c75c4fac6f6f3fca1d12dd3d4b30660e1af6551a2237. Rerun: `python -I score_a.py`,
`score_b.py`, `post_a.py`, `probe_uv5.py`, `detail_b.py` (outputs `.out`).

## A. 8 max(W,H) + 52 (H-MAX) against H-W, H-H: NOTHING KEPT DISCRIMINATES MAX FROM W
Searched: every kept twiddled job with T0 u mode 4-7: p1132 tx-border (16 jobs; the other 21 are
u modes 0-3, v-only or strided), r8-geo addr (u4-u7), r9-geo addr2 (11 jobs). specs.json
and cases.json (p1132 + p1141) hold no other u 4-7 job; E033's older 16 x 16 is square.
- 27 of 31 jobs are squares (8, 16, 32): H-MAX = H-W = H-H pixel for pixel (differ 0): no test.
- 4 jobs are 32 x 8 (bd-hb-ns-uv4..uv7, u and v in the same mode): max = W = 32, so MAX/W differ 0
  pixels; MAX/H differ on all 2048. H-MAX and H-W held 2048/2048 (uv4, uv6, uv7), H-H 0.
  These are E565's jobs that E983 read (W vs H fitted there): not held out; they refute only H-H.
- Only addr3's 8 x 32 and 16 x 64 (H > W) part max from W; 64 x 16 parts max from H. All are the
  post hoc rule's fit set. Held-out jobs discriminating max from W: 0 (from H: 4, all E983-read).
- So E1000's "8 max(W,H)+52" stays [fitted]; H > W exists only at those two addr3 jobs.
- Mode 5 (frozen H-MAX): s inside 128/128 and s outside with t inside 384/384 on both mode 5
  uv jobs (16 x 16, 32 x 8); single-axis u5 jobs 2048/2048 (squares, no discrimination).
- Mode 5 with v outside (E983's dwords 20-23): bd-uv5 (16 x 16) is the only other kept job.
  C-CONST (20..23): 1152/1152 on 32 x 8 (its source), 0/1152 on 16 x 16, which reads 16, 17, 18, 19
  (+0 above-left, +1 above-right, +2 below-left, +3 below-right). The dwords are shape dependent.
  s inside with t outside, unforeseen by the frozen rule (it predicted +offset): 384/896 fail on
  both uv5 jobs; they read a per-side constant plus s.
- [post hoc, post_a.py, fitted on those two jobs, no held-out job exists]: s inside, t < 0:
  7 M + 52 + s; t >= H: 4 M + 52 + s (384/384 on both; H-form 108 at 32 x 8 is excluded, W vs M
  not parted, W = M in both). Corner base c = 16 (16 x 16), 20 (32 x 8): (W+H)/2 and 12 + M/4 fit
  both, undecidable with two shapes. A hardware row at 16 x 64 (or 64 x 16) parts them (40 vs 28).
- Landed records: E1000/E983 need no correction as written (E983 says "one size"); an appended
  note would help: dwords 20-23 are 32 x 8's, 16 x 16 reads 16-19 (bd-uv5, E565's kept data).

## B. R10-BF11 with stage outputs below 2^-14 flushed (FTZ-OUT)
Kept bilinear sRGB (T0 bit 27, filter bits 12-13 / 10-11 set) jobs: g-bl-st-a, g-bl-st-b (E723),
reruns srgb2-ctl (r10-tex) and srgb-ctl (r9-x) of g-bl-st-a, srgb-eq (equal corners), and
an-t0b27 (p1132 tx-lod, 64 x 64 twiddled, grad input; footprint by texmodel.py, not by the
strided form). ab-t43, s64x32-t0b27, ind-t0b27 are point sampled. Fit set (not scored here):
srgb2's five rows and r9-x's six (post_srgb_ftz.py).
| job | pixels exact BF11 / OUT / IN / INOUT | halves SUB | halves PART |
| g-bl-st-a, g-bl-st-b, srgb2-ctl, srgb-ctl, srgb-eq | 2048 all four | 0 | 0 |
| an-t0b27 | 2036 / 2048 / 2047 / 2048 | 12 | 12 |
- Five jobs never reach a subnormal stage (all corner bytes decode normal or the bilinear
  weights are large): they cannot decide the flush; they only keep BF11 intact (2048 each).
- an-t0b27 decides 12 halves (detail_b.out): pixel x = 4, rows 0-11, channel 0, two corner quads
  (21, 23, 0, 2) and (0, 2, 1, 3), kx 4, ky 4..60. Unflushed BF11 is wrong on all 12 (by 0x0a to
  0x3ba half bits), FTZ-OUT 12/12 (HW equals it, 4096/4096 halves, 2048/2048 pixels). Input-only
  flush (FTZ-IN: operands flushed, final not) fails 1 (4,4): HW 0, FTZ-IN 0x0166; FTZ-INOUT = OUT.
- So the stage-output flush is held out on one job, two corner quads, 12 weights: a thin,
  correlated sample (same x column), not 12 independent ones; the final-output flush rests on
  one half, (4,4), final 5.7e-5 unflushed (hardware 0), and on E1004's fit rows.
- Input flush vs output flush: decoded corner bytes are never subnormal (byte 1 = 3.04e-4), so
  operands of the x stage can not be subnormal; "input flush" is only the flush of x-stage results
  entering the y stage, which is what FTZ-IN is. Its only separator from FTZ-OUT: y-stage final
  subnormal. A later row: bytes (0, 1, 0, 1) at ky 0, kx 11..14 (x stage alone: 5.2e-5, 5.7e-5
  flushed, 6.16e-5, 6.6e-5 kept predicted) and (0, 0, 1, 1) at kx 0 for the y stage alone
  (next_row_b.out); the threshold lies between 5.7e-5 and 6.4e-5 in the kept data.
- Record: E1004 may take an appended line: an-t0b27 (p1132) holds the flush out on 12 halves, one
  pixel column (E982's "subnormal halves never ran" meant its own fit; an-t0b27 ran in 11.32).
[infer] an-t0b27's footprint is the 11.32 model's; its 2048/2048 under FTZ-OUT supports it.
All files are derived from published kept data and our own scripts; no firmware-derived content.
