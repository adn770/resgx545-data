# c6-q261: set-up arithmetic for the far-vertex band (Q261 / E1005), offline, post hoc
Verdict: round 1 (all declared set-up arithmetics) fits no row set; round 2 (clip) fits all 48
rows with ONE integer parameter [post hoc]: fits post hoc, needs a held-out row.
## Rules (frozen before scoring, FREEZE.log)
- Round 1 `q261_rule.py` sha256 4a0eaaf19c9a9c64851658c6dd9b694c558183aaf736e79c8adb186781e2d844:
  float coefficients a,b,c (exact ints rounded to m bits, m = 24..8, RN or RZ) in 9 forms (c from
  exact or rounded products, c-first order, 32/16 tile-relative, edge-start origin, near-vertex
  origin, slope forms), fixed-point LSB truncation of c (2^16..2^32), far vertex floored to a 2^k
  grid (k=4..10), 32-bit wrap and saturation of the 1/256 vertex. 236 candidates.
- Round 2 `q261_rule2.py` 0997a099a36388c1465abe7d26af7403b5422af75bd3ff919c596800b233da93,
  written after round 1 and the D_eff diagnostic: clip against a guard rectangle ([-G,64+G] or
  [-G,G]), each new vertex rounded to 1/256 (half up / truncated / float32 interpolation), exact
  polygon edge test. 51 candidates.
- Round 3 `q261_rule3.py` 5424683440b720249c4ed9a5f1cbd31d8fbe7c3f7c4b5b349ab24b3b8985cdda:
  scan of the clip guard (G=1..48, asymmetric pairs) after round 2 had one fit.
- Criterion: all 48 rows pixel-exact (all 4096 pixels). Rows: E1005's 36 (far-x23p/x24p/x25n,
  d=0..-544), E1005 control, E979's 10 far rows, E979 control (plan said 47; there are 48).
  Fit rows = every row; there is NO held-out row (the data that suggested the rule is all of it).
- Outside the 0.05 px near sets the exact image equals hardware on all 48 rows.
## Results (q261_score.out, q261_score2.out, q261_score3.out; rerun: python -I q261_scoreN.py)
- Round 1: 0 of 236 fit. Best: 46 of 48 rows, all 318 band pixels right (abs-cX m=12..14 RN,
  tile32, slope-near, near m=10/11 RZ): only far-x24p d=-416, -544 fail (band drawn, hardware
  not). q261_deff.out: they snap the far edge to slope 1/4, so the lattice pixels are exact ties
  drawn by the tie rule (D_eff = t* - d, grows with |d|). Float32 (m=24), fixed-point and vertex
  candidates: 11 of 48 or worse (the exact image: 11 of 48, 0 of 318 band pixels).
- Round 2: 1 of 51 fits, `clip[-16,64+16]/exact-halfup`: 48 of 48 rows, 318 of 318 band pixels.
  G=2..8 miss only far-x24p d=-416; float32 interpolation, truncation, origin guards do not fit.
- Round 3 (the free parameter): symmetric G fits for G = 16..22 (hi bound x <= 80..86); G <= 15
  fails far-x24p d=-416, G >= 23 fails far-x23p d=-544. The lo bound is unconstrained in 8..32
  (far-x25n fits for all). The y bounds are untested (no far-y row has a band pixel).
## Reading [infer]
- The band pixels are rounding of a clipped vertex: the ISP/TA clips the far vertex to a guard
  around the target, rounds the new vertex to 1/256, and the edge from the near vertex turns by
  (rounding error)/(distance to it). That predicts per-triangle "displacements" of different size
  without D proportional to |F|, and the exact image outside the band (E979). It does not need a
  coefficient format. Chance level: 1 of 51 declared fits, but 7 of 48 scanned G fit and the
  fitting G are contiguous, which the miss pattern of G=2..8 and 23..48 supports.
- Everything is [post hoc]: E1005's intervals were read first.
## Held-out vertices for a later hardware row (q261_heldout.out, q261_proposals.json)
64 x 64, t4 --tri-unit 5, near vertices of E979's far-x24p (pos-x), far-x25n (neg-x), far-y22n:
- pos-x, survivors G=16..22: far vertex (11085359.125, 4582008.71875), (12650724.125,
  -1220066.84375), (15420021.78125, 1514664.1875), (6442454.25, 1792305.65625): 7 distinct
  predicted images (1-pixel differences, e.g. pixel (62,32) drawn only for G=18,19).
- neg-x, lo guard 8..32: (-30099096.9375, -134643.59375), (-8909363.90625, -501189.3125),
  (-10999817.75, 8040414.59375): 6 distinct images.
- far-y, guard 8..32 (assumed symmetric): 4 vertices in the .out, weaker (y bound untested).
- A 128 x 128 target would tell a guard relative to the target (64+G) from an absolute 80..86.
Predictions differ from the exact image by 0 to 2 pixels: single band pixels decide.
A held-out row whose band pixels contradict every G in 16..22 refutes the clip reading.
## Records and publishability
Rests on E607, E684, E979, E984, E1005 (Q199, Q260, Q261). E1005's "[infer] rounding of a slope
or an edge coefficient" would need an appended note only if a held-out row confirms the clip
reading; E984's note that 11 to 19 bit coefficient variants break E683 stands (round 1 here
reproduces its tie-based near fits). All files are scripts and text from published data; no
firmware-derived content.
