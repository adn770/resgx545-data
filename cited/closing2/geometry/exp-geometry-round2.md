# Proposal round 2: Q210/Q273 (C, dword 36), Q211 (U), Q230 (TA/MTE clip, clamp, off-target)

2026-11-10. Offline work only; nothing ran on the laptop, no repo edited. Scripts (read-only on the
published data): `~/src/scratch/resgx545/closing2/geometry/{dw36_glist,dw36_tri,u_model,e3_decode,
clip_rules,clamp_rcp,designs}.py`. Every offline result below is a FIT on data measured before the
script was written unless marked otherwise; the frozen predictions are what the runs hold out.

## 0. Offline results (what decided before any job)

**Q273 dword 36 (dw36_glist.py, dw36_tri.py).** Across 150 jobs with a control block and a TA-data
dump (S1 g-e1 22, S1b g-e1 16, E630 wd-glist 5, E704 dpm-oom 8, E625's tri jobs 99 at 1024x768 and
4096x4096): in every UNRAISED job dword 36 = max(global-list page count - 2, 0): g = 1 -> 0 (54), g = 2
-> 0 (3), g = 4 -> 2 (E630's 4 + S1/S1b's 1350 cells), g = 5 -> 3 (the 1380-1500 cells), 99 of 99.
Every job where dword 36 differs from the page's g - 2 is a RAISED job (9 of 9 in S1/S1b, 77 in
E625's data), which E627 explains: after a raise the state page holds the lists the TA built after the
last partial render, not the first abort's. So dword 36 is the global list's page count at the first
abort, less 2, saturating at 0 (E310's firmware reading, `CR_DPM_GLOBAL_PAGE_STATUS` count - 2, with a
floor). The global list's pages hold the OBJECTS: the walked pages of c-1500-0x422's list (0x241,
0x35c, 0xb8) carry packed vertices (depth 0x3f000000, 1/w 0x3f800000, ISP 0x1d00200/0x10f0), while
macrotile pages carry streams (0x5c8c7fff.., 0xc0000000 fills). Hence E753's "1, 1, 3, 2, 3, 3 over
P" is the number of object pages the TA had taken when the threshold hit (it depends on how far the
scene had got, not on the vertex count alone), and the "step between 1350 and 1380" is one more
object page at that thr0. `CR_DPM_GLOBAL_PAGE_STATUS` is 0x072c (glossary G0828): NOT in any kept
timeline (0x0720-0x0724 only). Held-out test: sample it (see D below).

**Q211 page need (u_model.py).** HU1 = sgx-pipe's TA model applied as it stands (ta.rs: `tiling`,
`tile_lists` per 16x16 half-region, `walk`, 128 bytes a stream, a page per macrotile that has streams,
pages = ceil(streams/32)) + 1 global page gives EVERY measured U exactly, residual 0 in 16 of 16:
the default triangle at 64x64 (2), 128x128 (3), 192x128 (5), 256x256 (5), 512x384 (8), 1024x768 (19),
4096x4096 (287); the four positions (19, 20, 17, 12); E735's six K-scenes (29, 35, 37; 19, 22, 22);
E627's two-triangle scene (24, inside 23..26). Only 128 B/stream with G = 1 does it (64/96/160/192/256
B and G = 0/2 miss by 16 to 479 pages in total). E310's 3-page macrotiles 5 and 9 at 1024x768 are the
model's 96-stream macrotiles. This is a fit on all 16 (two constants picked from a small grid; the
structure is E650's). E625's k stays a separate unknown (U = 287 is HU1's; k is the partial path's).
The model refuses nothing here: it needs `ta.rs` only for the tiling and region test (the n = 4
refusal of `write` concerns the header layout, not the page count).

**Q230 (e3_decode.py, clip_rules.py, clamp_rcp.py, designs.py).** Read from all 41 objects of S1 and
S1b g-e3:
1. The primitive list is a triangle STRIP: entries (0,1,2), (2,1,3), (2,3,4) over the stored
   vertices, each 5-bit field = (bit 4: the edge from this vertex to the next vertex of the triangle
   is a boundary edge of the polygon, 0 for an internal diagonal) | (bits 3:0: stored vertex index).
   41 of 41 objects (3, 4 and 5 vertices). This re-reads E546/Q070's "vertex numbers 16 to 31": a
   4-bit index with the flag set on every edge of a lone triangle.
2. The stored vertex order is the strip zigzag p1, p2, p0, p3, p(n-1), p4 ... of the clipped
   polygon's boundary (41 of 41 are a zigzag of their convex hull), and for the two z cuts the
   polygon is Sutherland-Hodgman over the input edges A->B, B->C, C->A (the end vertex when inside,
   the intersection when crossing): SH gives [(32,14),(32,44),(20,56),(8,8)] and the zigzag of it is
   exactly the stored [(32,44),(20,56),(32,14),(8,8)]; same for cut-m (2 of 2 each, repeats included).
3. Depth: stored = 0.5 + 0.5 z_ndc (viewport z offset/scale) exactly, including the clip-made
   vertices (z = +-w gives 1.0 / 0.0 exactly). Every w-scan and clamp job has z_clip = 0, hence depth
   0x3f000000 whatever w: that is why E754 could not score depth at w != 1 (nothing to score).
4. Off-target: the viewport word 6 is an ABSOLUTE x offset (default 32.0): window x = X + 32 x_clip.
   So e3o-x64 put the triangle at x 40..88 (straddling the edge; streams only in target column 1) and
   e3o-x128 at 104..152: inside macrotile 0's 128-wide region grid, yet no object. The
   "macrotile grid" reading is therefore refuted on existing data; HO-region (E542's tile rule on
   target regions only) fits all five. Open interval: min x in (64, 104].
5. Guard band: clip planes at +-1.5 in clip units (w = 0.5 reaches -16/80 unclipped with 3
   vertices; 1e-3 is clipped to a 4-vertex square at -16/80).
6. WCLAMP position rule: x_stored = (x clipped to the +-1.5 band in TRUE w) / max(w, clamp). It gives
   E736's e3k-ctl square exactly: 1.5 * 32 * (1e-5 / 1e-3) = 0.48 (stored 0.4805 = 123/256) and
   E754's four shrunk triangles. One rule for both programs (E754's "position clause" puzzle).
7. 1/w under the clamp: within +-0.55 ulp of the exact reciprocal; RZ 5 of 6, RN 5 of 6, no
   truncated/rounded-mantissa or reduced-precision rule fits all six (23 down to 8 bits tried). In
   band: RZ 7 of 7 (E754 held out). The clamp path is not a rounding rule; it is boundable only.

## 1. Ranking by value for cost

| rank | experiment | questions | jobs | tooling | closes |
|---|---|---|---|---|---|
| 1 | U1 held-out page need: 16 new scenes at 0x422 + 2 boundary pairs | Q211 U clause | 22 | generator from u_model.py (~120 lines), none on the laptop | Q211's U formula (dpm.rs can compute U) |
| 2 | C1 fine ladder + C2 kpoke decoupling (+ 0x072c in every timeline) | Q210 C, Q273 dword 36 | 22 + 7 | regtimeline range; `--kpoke pb:11=V` exists | C exactly; absolute vs P-tied; dword 36 rule held out |
| 3 | T1 off-target boundary + T7 fine grid | Q230 off-target, 1/256 clauses | 11 + 3 | none | two clauses |
| 4 | T2 clipped polygons (new cuts, slab, y-cut) | Q230 vertex rules | 7 | 1-line template variant | the vertex-rule clause |
| 5 | U2 k ladder (+3 spacing cells after a pause) | Q211 k, spacing | 7 + 3 | none | k to +-1 coupled to s |
| 6 | T5 sub-pixel cull + T6 clamp ladder | Q230 clamp clause | 9 + 7 | none | cull threshold; clamp 1/w as a bound |
| 7 | T4 depth at w != 1 + T3 1/w of clip-made vertices | Q230 depth, clip 1/w | 8 + 4 | two templates (~15 lines each) | depth formula; interpolation rule |
| 8 | C3 second target 2048x2048 | Q210 "does C move" | 6 | state-page offset only for dword 36 | the target clause |
| 9 | U3 `--vertices` ladder (stream block capacity) | Q211 wide scenes, Q070 | 6 | none | measurement only |

About 110 jobs, ~25 min of jobs; three pauses (C1 -> C3 and the 1350 cells; U2 -> spacing cells;
none for the rest). Safest first within each stage; the kpoke stage last of its session.

## 2. Q210 / Q273: the limit C and dword 36

Hypotheses (frozen):
- H-abs: the raise happens iff thr0 + 0x20 <= C, C a constant of the core/firmware in [0x35e, 0x37e)
  (E753), the same whatever sets thr0 and whatever the target.
- H-rel: the limit is tied to P (C = P - 2 - d, d in (0, 0x20]): a threshold set by the descriptor
  poke at P = 0x422 raises up to V = 0x3de.
- H-target: C differs at 2048x2048 (the flip moves by more than one 0x20 step).
- D36: dword 36 = max(0x072c's page count at the first abort - 2, 0) in EVERY job, raised ones
  included (offline fit above, 99 unraised; the raised jobs are the held-out part).

Observables per job: the job's own 0x0624 rows (knob proof: P - 0x22; under a poke, the first
abort's status read from the 0x0658 stretch and 0x0724 = V, and dword 35 = V - 2 or V + 0x1e),
0x0658 stretches (partial renders), run peaks, TA3DCtl dwords 35-39, and 0x072c sampled with the
timeline (range 0x0720-0x072c, read-only). The raise = dwords 37/38 non-zero and the second abort at
thr0 + 0x20.

**C1, fine ladder (safe, no tooling).** `probe --tri pixel --width 4096 --height 4096 --vertices 1500
--dump-render` with p1139-green, render_pb_pages written/read back/marked, a reset before each job,
regtimeline 0x0624-0x0628, 0x0654-0x0660, 0x0700-0x0710, 0x0720-0x072c, 0x0748.

| id | V | P | role | H-abs |
|---|---|---|---|---|
| c-1500-0x360 | 1500 | 0x360 | control (E753: raise) | raise |
| c-1500-0x380 | 1500 | 0x380 | control (E753: none) | none |
| f-1500-P, P = 0x362, 0x364 ... 0x37e (15) | 1500 | step 2 | held out | raise for P - 2 <= C, none above: exactly one flip |
| f-1350-P, P = 0x366, 0x36e, 0x372, 0x376, 0x37a | 1350 | 5 cells | held out (HP1: same flip) | same outcome as 1500 at that P |
| after the pause: f-1500-(P* - 1) | 1500 | step 1 | fixes C exactly | by the flip |

Decision: one flip -> C = P* - 3 (P* the first silent cell); the step-1 job fixes it. Two flips or a
reversed one refute H-abs's monotone form (recorded as such). 1350 differing from 1500 at any cell
refutes HP1 (one step for both scenes). Void: a cell whose second run does not reach thr0 or whose
0x0624 is not P - 0x22. Cannot tell: a control fails. 22 jobs, ~3 min.

**C2, decoupling by the descriptor poke (E625's `pb:11=V`, a debugfs kpoke; E625 ran 5 with no
incident; user decision 1).** P = 0x422 throughout.

| id | command | role | H-abs | H-rel |
|---|---|---|---|---|
| k-tri-0x80 | `tri --width 4096 --height 4096 -n 1 --keep-overflow --dump-each --words --regs 0x0700-0x074c --kpoke-render 1:pb:11=0x80` | control (E625: raise, dw35 0x9e) | raise | raise |
| k-tri-0x100 | same, V = 0x100 | control (E625: none, dw35 0xfe) | none | none |
| k-1500-0x300 | `probe --tri pixel ... --vertices 1500 --kpoke pb:11=0x300` | held out | raise | raise |
| k-1500-0x33e | V = 0x33e (raised 0x35e, E753's P = 0x360 twin) | held out | raise | raise |
| k-1500-0x35e | V = 0x35e (raised 0x37e, E753's P = 0x380 twin) | held out | none | raise |
| k-1500-0x3a0 | V = 0x3a0 | held out | none | raise |
| k-1500-0x3de | V = 0x3de (raised 0x3fe) | held out | none | raise |

Knob proof per job: the first abort's status = V (0x0658/0x0724) and dword 35 = V - 2 or V + 0x1e;
0x0624's reading is recorded (V or P - 0x22: a measurement, not a gate). The 1500 scene's second
run reaches V for every V <= 0x3de (E704: it reached 0x400 at P = 0x422). Decision: raises at 0x300
and 0x33e and none from 0x35e up = H-abs (C is a value the poked threshold is compared with, the
same as the knob's); raises at all five = H-rel (the limit follows P, not the threshold: the knob
ladder and the poke ladder then disagree, which is itself the mechanism's first handle). Mixed =
cannot tell, repeat once. 7 jobs, ~2 min. Risk: a poke of the PB descriptor; E625's 5 were clean;
stop the stage on any `job hung`/fault line.

**C3, second target (after C1).** `probe --tri pixel --width 2048 --height 2048 --vertices 1500` at
P = P* - 2, P*, P* - 0x20, P* + 0x20 (4 jobs) with the 4096 pair P* - 2 / P* re-run in the stage as
controls (2 jobs). H-abs + "C the same": identical outcomes at P* - 2 (raise) and P* (none); H-target:
both raise or both silent, the +-0x20 cells bracket the new flip. Void: the second run does not reach
thr0 at 2048 (then try 2048x1536, same prediction). The raise verdict needs buf09 and the timeline
only; the dword-36 check at 2048 needs the TA data's state-page offset for that context (from the
fork's layout, read-only; not needed for the verdict). Risk: a context size never run; the tool
accepts it iff `--mock` does (check first). 6 jobs.

**D, dword 36 in every job of C1-C3**: with 0x072c sampled, score D36 in every job: the register's
count at the first 0x0658 rising edge (the sample just before it) less 2, floored at 0, equals dword
36. Raised jobs are the held-out part (9 of 9 differ from the page today, as E627 says they must).
If 0x072c does not change over the job (not a live count), the clause stays at the 99-job fit.

What will not close: what the DPM compares C with and why 0x20 (no observable names them; C2 names
only whether the limit follows the threshold or P); whether C is the hardware's or the firmware's
(if C2 gives H-abs and C1 a round value, a `kind = fw` note is the most that can be said).

## 3. Q211: the page need U

**U1, held-out formula run (safe, no laptop tooling).** `tri --width W --height H -n K --geometry
1..K-1 --move k:DX,DY --keep-going --keep-overflow --dump-render --dump-each --words --regs
0x0700-0x074c`, P = 0x422, regtimeline 0x0624-0x0628, 0x0654-0x0660, 0x0720-0x072c. U read as e2a's
scorer does (peak of 0x0724 and the free-list walk; disagreement = cannot tell for that cell; a
kick line other than "geometry only, the scene left open" voids a K-scene cell). Frozen HU1
predictions (designs.py; HU2 "coverage + c", c = 8 from the default triangle, in brackets):

| id | scene | U (HU1) | HU2 |
|---|---|---|---|
| u-ctl-1 | 1024x768 default | 19 (control, E705/E735) | 19 |
| u-ctl-2a | 2 apart (0,288) | 29 (control, E735) | 23 |
| u-m32 | 1024x768 moved (32,0) | 21 | 19 |
| u-m0-96 | moved (0,96) | 22 | 19 |
| u-m-128-96 | moved (-128,96) (E627 overflowed it at 0x30) | 22 | 17 |
| u-m384-288 | moved (384,288) (E627: completes at 0x30 = thr0 14) | 13 | 12 |
| u-2-m96 | two: base + (-96,0) (E627: 23..26) | 24 | 20 |
| u-2-256-192 | two: base + (256,192) | 30 | 22 |
| u-3-stk | three: base + (16,0) + (0,16) | 21 | 19 |
| u-4-corners | four: (0,0) (512,0) (0,384) (512,384) | 35 | 24 |
| u-640 | 640x480 default | 11 | - |
| u-1280 | 1280x1024 default | 31 | - |
| u-2048 | 2048x2048 default | 79 | - |
| u-2048-1536 | 2048x1536 default | 60 | - |
| u-512-m128 | 512x384 moved (128,0) | 7 | - |
| u-4096-m1024 | 4096x4096 moved (1024,0) | 275 | - |
| u-4096-2 | 4096x4096 two: base + (0,1024) | 438 | - |
| b-2-m96-lo/hi | two (-96,0) at P = 0x45 / 0x46 | overflow / complete (E625's rule with U = 24) | |
| b-m32-lo/hi | moved (32,0) at P = 0x36 / 0x37 | overflow / complete | |

Decision: HU1 holds iff every usable cell is exact (a miss of 1 page refutes it for that scene and
the record says which macrotile); 16 held-out scenes at five grids (n = 2 and n = 4, 64x64 to 4096)
is what "closed" means for the U clause. Non-library sizes (640x480, 1280x1024, 2048x1536) run only
if `--mock` accepts them (E174: 222 sizes). Risk low; the 4096 two-triangle scene is 438 pages, fine
at 0x422. 22 jobs, ~4 min. Tooling: the generator computes the predictions with u_model.py's code
(~120 lines moved into gen/), the scorer compares U to the prediction (~30 lines).

**U2, k and the spacing (safe).** The count formula 1 + floor((U + k - thr0) / (thr0 + s)) with
U = 287 (HU1 = E625's measure) at 4096x4096, `tri -n 1 --keep-overflow` default triangle: count 2 iff
k >= 2 thr0 - 256 (s = 0x1f) or 2 thr0 - 257 (s = 0x1e). Ladder P = 0xa3 .. 0xa9 (thr0 129..135: k
thresholds 2, 4, 6, 8, 10, 12, 14), controls P = 0xa0 (E625: count 2) and 0xb0 (count 1). The first
cell with count 1 gives k to within 2 (coupled to s by one). After a pause, three cells where count 3
iff k >= 3 thr0 + 2 s - 287 straddle the found k (P about 0x83..0x88; E625's 0x60 (3) and 0x80 (2) as
controls) to separate s = 0x1e from 0x1f where the two families do not alias. Void: a count not
readable from 0x0658. 10 jobs. Will not close if (k, 0x1f) and (k - 1, 0x1e) predict the same count at
every reachable cell (then the pair is recorded as the answer).

**U3, stream-block capacity (measurement).** `probe --tri pixel --width 1024 --height 768 --vertices
N`, N = 6, 15, 30, 60, 150, 300 at 0x422: HU1 predicts 19 for N = 6 and 15 (one object, 2 to 3 stream
dwords per region, one 128-byte block; held out); the first N whose U exceeds 19 places the block's
capacity in objects (the chaining rule is Q070's and not predicted). 6 jobs, data for the wide-scene
clause (E630's 9 pages a vertex).

## 4. Q230: the TA for clipped, perspective and off-target triangles

Each group gated by its own control (S1b's scorer convention); `probe --tri ... --width 64 --height
64 --dump-render`, the object decoded by pbdump (vertices, prim list, depth, 1/w, regions).

**T1, off-target limit (HO-region: E542's tile rule, low side closed, high side open, on target
regions only; no tooling).** Viewport word 6 (x offset) and word 8 (y offset), min x = X - 24, max x
= X + 24.

| id | word | value | HO-region | HO-band(B > 0) |
|---|---|---|---|---|
| o-x64 | 6 | 64.0 | present (control, E736) | present |
| o-x1000 | 6 | 1000.0 | none (control, E650/E736) | none |
| o-x87.5 | 6 | 87.5 (min x 63.5) | present | present |
| o-x88 | 6 | 88.0 (min x 64.0) | none | present |
| o-x88.5, o-x96, o-x104 | 6 | 88.5, 96, 104 | none | present up to 88 + B |
| o-xm24 | 6 | -24.0 (max x 0.0) | present | present |
| o-xm24.5 | 6 | -24.5 | none | present |
| o-y87.5, o-y88 | 8 | 87.5, 88.0 | present, none | present, present |

Decision: 88.0 none and 87.5 present (and -24.0 present, -24.5 none, y alike) = HO-region with E542's
conventions held out at the target's edge; 88.0 present = a band, its width read from the ladder.
Cannot tell: a control fails, or a dump is unreadable. 11 jobs.

**T2, clipped polygons (SH order, zigzag, edge flags, made-vertex depth; vtx_zab.s).**

| id | program | predicted object |
|---|---|---|
| z-flat099 | A = 0, B = 0.99 | control: E651's object, depth 0x3f7eb852 |
| z-cut-p | z = 2x + 1 | control (repeat): 4 vertices [(32,44),(20,56),(32,14),(8,8)], prims [(16,1,18),(2,17,19)] |
| z-cut-p05 | z = 2x + 0.5 | 4 vertices [(40,36),(20,56),(40,16),(8,8)], depths [1.0, 0.375, 1.0, 0.0], prims [(16,1,18),(2,17,19)] |
| z-slab | z = 4x (both planes) | 4 vertices, none original: [(24,52),(24,12),(40,36),(40,16)] depths [0,0,1,1] if the +w plane is applied first, [(40,36),(24,52),(40,16),(24,12)] depths [1,0,1,0] if -w first (either is a finding) |
| z-cut-ym | z = 2y - 1 (template with pa1: one line) | computed by the generator from SH + zigzag |
| z-cut-m-slope | z = 4x - 1 (cut at x = 0 again, B kept) | 3 vertices [(56,20),(32,44),(32,14)] depths [1.0, 0, 0] |
| z-cut-p-r2 | repeat of z-cut-p05 | same |

Decision: a group counts only if both controls hold; each row's vertex SET, ORDER, prim words and
depth words are scored separately (set right but order wrong refutes the zigzag, not SH). 7 jobs.
Tooling: `vtx_zab.s` variant reading pa1 (1 line), mock-assembled.

**T3, 1/w of clip-made vertices (template vtx_zw.s: z = A x + B, w = C x + D, ~15 lines).** w = 0.5 x
+ 1.25 (A: 0.875, B: 1.625, C: 1.0625), z = 2x + 1: cut at x = 1/6. HI-w: made 1/w = RZ(1/w_made),
w_made = 1.3333 -> 0.75; HI-rhw: lerp of 1/w along the edge -> 0.8205 (A->B). Stored x, y = x/w per
vertex, depth 1.0 at the made vertices. Second slope w = -0.5 x + 1.25. Control: z-cut-p (w = 1).
4 jobs. The +-1 ulp of the made 1/w (today 0x3f800001 on one made vertex of two) is not predicted.

**T4, depth at w != 1 (template vtx_wzclip.s: vtx_wclip + `mov o2, #{Z}`, ~2 lines).** Pairs with
z/w in (-1, -0.5], where depth = 0.5 - 0.5|z/w| is exact (Sterbenz) and the candidates differ:
(Z, W) = (-2.1, 3), (-2.6, 3), (-5.3, 7), (-0.0027, 0.003), (-0.83, 1.1), (-6.1, 7); frozen words per
candidate D1 (0.5 + 0.5 (Z * RZ(1/W))), D2 (0.5 + 0.5 RZ(Z/W)), D3 (RN(Z/W)), D5 (RZ(Z * RZ(1/W))),
D7 (Z * RN(1/W)), D6 ((Z + W)/(2W)) from designs.py (3 to 4 distinct words a pair). Controls: Z = 0,
W = 3 (0x3f000000, E754's e3i-w3) and Z = -0.5, W = 1 (0x3e800000, cut-p's A). 8 jobs. Decision: the
one candidate right in 6 of 6; none -> the words are recorded and the clause narrows to +-1 ulp.

**T5, sub-pixel cull (in band, w = 1, `--tri-v ... --tri-unit 10`, no tooling).** Triangles centred
on the pixel corner (32,32), covering no pixel centre, extent e = 0.3, 0.5, 0.6, 0.75, 0.9, 0.98 px;
controls e3k-ctl (0.96-px square present) and e3k-i-c1e3 (0.48-px triangle none), repeated. HS-ext:
object iff the extent >= T, T in (0.48, 0.96]; HS-area as the alternative (an elongated 0.3 x 0.98
triangle separates them). 9 jobs. Cannot tell: a control fails.

**T6, clamp ladder (vtx_wclip, x and y scaled by w; no tooling).** Clamps where RZ and RN of
1/clamp differ: 6e-5 and 1.5e-4 over w = 1e-5; 6e-4, 7e-4 and 1.2e-3 over w = 1e-4 (so the object
stays above T5's size); 2e-4 over 1e-5 as the cell where RZ = RN (a miss there means an error beyond
1 ulp). Frozen per job: the RZ word, the RN word, and the position x_in / clamp (HREP-xy' held out
again). Control: e3k-i-c3e5 (0x47023555). 7 jobs. Decision: all RZ or all RN closes the rounding
clause; mixed closes it as "within 1 ulp, not a rounding rule" (the simulator accepts either
neighbour and reports fitted).

**T7, fine grid (no tooling).** Three more odd-numerator triangles at unit 10 (values 1 and 3 mod 4,
no ties): HF-round predicts the packed 1/256 value rounded to nearest; HF-trunc truncated. Control:
e3f-ctl. 4 jobs.

What will not close: the clamp 1/w as a rule (bound only); the ulp of a clip-made 1/w; the z-cut
plane order beyond what T2's slab shows; the band's exact edge for y and for w other than 0.5/1e-3
(T1 tests the viewport side, not the clip side; a w = 0.4 job would clip at 4 vertices if the band is
exactly 1.5: optional 1 job).

## 5. Scorer outline (all stages)

Per job: void before any match (no output, rc not a tool result, missing dump, knob proof failing,
second run not reaching thr0 where the raise is scored). Per group: the controls' frozen values
must hold or the group is "cannot tell"; held-out rows tallied apart from repeats (S1b's `support`).
Verdicts name the hypothesis and the count ("H-abs 5 of 5", "HU1 16 of 16 exact"), never a
summary of the fit data. Dword-36 (D) is scored in every DPM job as a side table, never gating.

## 6. Risk and stop rules

All 4096 jobs are 2-4 partial renders (rc 3 "scene overflowed" is the normal class). Stop a stage on
any `job hung` or fault line; a context lost after a reset is logged and the next job runs. C2's
descriptor poke: E625 ran five without incident; it stays last in its session. C3's 2048 target and
U1's non-library sizes run only if `--mock` accepts the size. Nothing writes a clock-gate register,
trc_hazard, kreg, /dev/mem beyond `--regs` reads, GRUB or a kernel. The laptop builds the tool only
if a template is added (T2-T4); otherwise the S1b binary runs as is.

## 7. Tooling (sizes)

| item | size | needed by |
|---|---|---|
| regtimeline range 0x0720-0x072c | argument | C1-C3, U1 (dword 36) |
| U generator from u_model.py + scorer compare | ~150 lines Python, offline | U1 |
| `--kpoke pb:11=V` on probe | exists (README); check the spec with `--mock` | C2 |
| vtx_zab.s pa1 variant; vtx_wzclip.s; vtx_zw.s | 1, 2, ~15 lines; mock-assembled | T2, T4, T3 |
| state-page offset at 2048x2048 | read from the fork's layout | C3 (dword 36 only) |
| sgx-pipe after the runs: dpm.rs U = HU1 (tiling + tile_lists, ~80 lines), the raise rule with C, dword 36; ta.rs prim list as index + edge flag, strip order, SH clip; mte.rs clamp rule, guard band 1.5 | sub-phase | records |

## 8. User decisions needed

1. C2: allow the descriptor poke `pb:11=V` (debugfs kpoke, E625's "risky script" class, no kernel
   change) in this batch. Without it C stays "absolute or P-tied: not separated".
2. Sample 0x072c (CR_DPM_GLOBAL_PAGE_STATUS, read-only) in the timelines of every DPM job.
3. C3: run a 2048x2048 context (never run; raise verdict needs no layout knowledge) or skip.
4. Build the three vertex templates now (T2-T4, laptop tool rebuild) or defer T3/T4 to a later batch.
5. Record now, as post-hoc readings on existing data: dword 36 = object pages at the first abort
   less 2 (Q273/E753 correction), the prim list as index + edge flag and the strip order (Q070/E546
   note), HU1 as a fit (Q211), the viewport-offset reading of E736's off-target cells (Q230) — or
   only after the held-out runs.
6. Order: U1, C1, T1, T2, T7, U2, T5, T6, then C2 (last in its session), then C3 and the pause cells.
