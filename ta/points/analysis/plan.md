# Phase 11.31 laptop batch: TA object format, VDM state, hardware events

Scratch, gitignored, written 2026-11-08. Nothing staged or committed; nothing written under
`~/src/resgx545` (landed d994a37), `tools/rewrite/`, p1129, p1130. Questions: Q070 (high), Q047
(high), Q111 (high), Q117, Q092, Q094. Direction: facts a simulator needs. No kernel change.

## 0. Origin and scope

The cases come from the interrupted p1128 draft (`../p1128`, never run): its tables, programs and
shims were copied, renamed, and the pieces dropped that cannot run now. Dropped: `ta-tri-edges`
(24 jobs: vertices exactly on a tile line need a `--tri-v` tool option that does not exist in
`~/sgxfive-test-1126`; the five-copy boundary jobs stay, so the closed corner rule on the line itself
stays untested) and the irq matrix kinds other than tri64 and fill. The tool is the 11.26 binary,
`~/sgxfive-test-1126` (sha256 751f7223...600f82e on the laptop), unchanged: no new option.

Run counts planned (jobs): ta-object-format 47, ta-tri-boundary 27, vdm-vtask 28, vdm-state-units 36
(safe); event-timelines 6 idle + 30 r2 + 30 r7 (read-only, `regtimeline` of E435); event-irq-matrix
2 kinds (3 controls + 26 status bits, and 15 status2 bits a kind); risky, last, one script at a time:
ta-line-point 54 (E414: a line stream hangs the job), ta-risky 38, vdm-vtask-risky 9,
vdm-state-risky 78. Total 317 table jobs (declared.tsv) plus the event runs.

## 1. Declared before any run

`declared.tsv` (case, script, set, size) sha256 `bb0246746cabfdf9cc6b2fd7a24e79f072e39e56120e2d5b26f6315fa2c6823a`;
`predictions-declared.tsv` (529 rows: case, quantity, value, model) sha256
`c2b05ab114f62814a803223527b9585c58264f903c93d09079c2397fbd404a02`. The case tables are
`gen/table-*.txt`; the generator is `gen/gen_p1131.py` (`models.py` holds the models).
Sets: fit = cases whose names say `fit`/`ctl` (a model may be adjusted to them after the run);
heldout = never used to adjust; control = repeats whose outcome must equal the control's. A case
that an E-record already ran at the same settings is `fit` (E308 settings, E180 geometry, E181
points, E427 completions). Where a prediction is `?` the case is exploration (no outcome can fail
it) and is reported as such, not scored.

## 2. Hypotheses (models named as in predictions-declared.tsv)

- Q070 format. H70-F: stored dwords a vertex = 1 + sum over coordinate sets of (set dwords; half
  precision format bit halves, rounded up), iterated = 1 + N (format byte 15:8 [7:0 of the high
  byte]); H70-M: mask word j gets bit i+1 for set i by format bit (mask 0), size 1 (mask 1), sizes 3
  and 5 (mask 2), 4 and 5 (mask 3). Fit: five settings of E308 at N = 4. Held out: N = 2, 3, 5, 6, 8,
  9, 11 with six size/format patterns each (42).
- Q070 OUTSEL (H70-O): flipping OUTSEL bit k changes the format word only for bits 11 (to
  0x000c0101) and 12 (to 0x00000101); every other bit leaves 0x00040101.
- Q070 triangles (H70-T1): the tile is half-open on its high sides, bounding box then edge lines
  against the tile corners; fitted post hoc to E180's 472 regions, so the four fit cases are not a
  test; the 23 five-copy boundary cases are. H70-T0 (the landed record's rule) is scored too.
- Q070 lines (H70-L2): a line's regions are the 32x16 regions its exact segment touches (closed);
  one line: every stream form 0x90 (H70-L1). Points (H70-P0): the region and tile that hold the
  vertex, half-open at the low side. Both are predictions about streams only if the TA writes an
  object; E414 saw lines hang and points write nothing with a topology change alone, so these jobs
  also set ISP word 0 (0x8000 / 0x18000) as E181 did. If no object appears the outcome is `no
  object` and the region test for lines and points stays open.
- Q117 (H117-W): a point covers the pixels whose centre lies strictly inside a square of side
  (ISP word 1 bits 15:8)/16 around the vertex; fit placements at pixel centres with widths 0x10,
  0x20, 0x40; held out: corners (22.0), widths 0x00, 0x08, 0x80, 0xf0. H117-O0: a vertex output row
  carrying a size (1.0 and 8.0) changes nothing while OUTSEL is untouched.
- Q047 (H47-N+17, H47-P0): per case the three marks of a two-block stream (the viewport x offset,
  ISP word 1 = 0x..20f0 in the object, the block's own pixel shader) are all present (P) or all
  absent (A) or the job hangs (H); bits 11:9 = 0 give A, 2 to 5 give P, 1 and 6 hang, 7 alternates;
  bit 8 changes nothing. So the fields do not separate units: a marks mix (some P, some A) is the
  finding that would show they do.
- Q094 (H94-none): VDM_TASK0.MAX_VERTICES at 15, 13, 9, 7, 2, 3, 1 with 2, 4, 8, 11 coordinate outputs
  and 126 vertices: every vertex is found (ids found 126) at every value, i.e. the field is not a
  hardware limit our jobs reach. Q092 (H92-none): the first trailing word's top nibble (0xf, 0xd,
  0x7) with 1, 2, 4 attribute rows leaves the object equal to the control.
- Q111 (H111-fw, H111-ctl): see section 4; a bit's `Y` is predicted to be seen by a host interrupt
  when its enable is armed after a reset; `N` that it is not; `?` exploration. The 3 controls per
  kind (no enable) must give none.

## 3. Outcome rules and recomputation

A job is: completed (rc 0, `diff` or tool line printed) or failed (rc != 0, "failed", "faulted",
"hung"); a failed job is followed by a debugfs reset and the health tri (64x64 must draw exactly;
one retry after 5 s; three failed recoveries stop the script). Raw output of every job is kept
gzipped with its raw sha256 printed, with the render dumps. `recompute/recompute_p1131.py DIR`
reads only the kept files and `cases.tsv`, parses the parameter buffer and TA data itself (own
decoder of 3d.md 10.1 and 10.2, no import of the landed tools or the run scripts) and prints per
model the observed against the declared value by set. Faults to avoid (reviews r1122, r1124, r1126):
the scripts say exactly what ran (`cases.tsv` holds each argument line); no case is held out unless
it is in the declared set above and its value was not used to adjust; the declared pixel model
assumes centres and corners as written and a miss is reported as a miss.

## 4. Q111: what the host can read

Existing debugfs: `regs` (a fixed list of registers, read by `rd`: includes 0x012c CR_EVENT_STATUS,
0x0118 STATUS2, 0x0130, 0x0110 the enables), `kreg` (a write of one register: never used), `kregnow`
(a write now plus counters; only the two host enable offsets 0x0130 and 0x0110 are ever written by
the scripts, E444's method). `regtimeline` (E435) reads through /dev/mem. CR_EVENT_HOST_CLEAR
cannot be read; a write is not made. The firmware acknowledges the bits it handles, so a sample can
miss a pulse; the order of bits within one job and the firmware's own view of the word are the
firmware-task work of p1130 and are not repeated.

## 5. Order and risk

safe first: ta-object-format, ta-tri-boundary, vdm-vtask, vdm-state-units, event-timelines,
event-irq-matrix; then risky one at a time: ta-line-point, ta-risky, vdm-vtask-risky,
vdm-state-risky. Health before the first, after each and at the end. A freeze or watchdog reboot:
stop and report.

## 6. Follow-up cases, declared after the first run of the safe scripts and before their run

The first run (ta-object-format 47, ta-tri-boundary 27, vdm-vtask 28, vdm-state-units 36 jobs; the
numbers are in the records) showed three things the first models did not cover, so three follow-up
scripts were written (`gen/gen_followup.py`, 32 cases, 56 predictions) with models built from that
run. Their cases are held out of those models; their files are hashed here before they run:
`declared-followup.tsv` sha256 `3cdba06dd7b5882521b3a9cfff359cdbd6caceec322ba49c3eaf79d4a418ca25`; `predictions-followup.tsv` sha256 `26d23a5d95f8b1a35eff5285ec7b8e08806af3caf5576b8c42ed37bf4e0ae64c`.

- ta-object-format2 (12): H70-F2. A coordinate set of size code s has c(s) components (1:1, 2:2,
  3:3, 4:3, 5:4: x and y, z for codes 3 and 5, w for 4 and 5; built from the run's codes 1, 2 and 5,
  so 3 and 4 are untested); a set whose format bit is set stores ceil(c/2) dwords for its c components
  and the remaining outputs raw: stored = 1 + N - sum over flagged sets of (c - ceil(c/2)).
- vdm-vtask2 (12): Q094. The first run lost vertices at 3 rows with fields 15 and 13 and at 4 rows with
  15, 13 and 9, and kept all 126 at 2 rows at every field and at 3 rows from 9 down, 4 rows from 7
  down. H94-MD: a task's output dwords (4 + N) * V (V = field + 1) is safe up to 128 and loses from
  150; H94-MR: rows * V safe up to 32 and loses from 40; between them '?' (exploration). n5 field 13
  (MD safe, MR lost) and n6 field 13 and n5 field 15 (MR lost) separate them.
- ta-tri-corner (8): H70-T1 per tile and primitive, on 6-vertex jobs at 128 x 128 where the first
  triangle's edge passes exactly through a tile corner (16, 32, 48, 64 by 16, 32) and the second's
  misses it by 0.047 pixel.

## 7. Second follow-up (vdm-vtask3, 8 cases), declared after vdm-vtask2 and before it runs

vdm-vtask and vdm-vtask2 (39 jobs) lost or duplicated vertices only when R * V was 36 or more, with
R = ceil((4 + N) / 4) the output rows of N coordinate outputs and V = field + 1 the vertices of a
task, and kept all 126 up to 33: so a dword budget (H94-MD: 126 and 117 dwords lost, 132 kept) is
refuted, and H94-MR2 is declared: all 126 reach objects if R * V <= 33, not if R * V >= 36.
Eight cases of other N and fields, one repeat (v3-n8-f10-b). `declared-followup2.tsv` sha256
`43b34c2000f382d54fb51bd828bff5abd1cbfd860bc71d2f9aa0df8ca0a326b4`; `predictions-followup2.tsv` sha256 `9c14577d3aafceb84e7e47c74cd69e1959946a335fa9cf2bda4648375780c613`. The first model's miss and the refinement are
recorded as such: H94-MR2 is built from vdm-vtask and vdm-vtask2, so those 39 jobs are its fit.

## 8. Third and fourth follow-ups (ta-points 44 cases, ta-line-bisect 27 cases)

Declared after the risky scripts ta-risky and ta-line-point ran (so after OUTSEL bit 8 was seen to make
points draw: ps-outsel-b8-s1 and -s8 of ta-risky, 3 and 192 pixels; the one-line jobs of ta-line-point
fit a segment within 0.5 to 1.94 pixel of the region) and before they run.

- ta-points: H117-S1. With OUTSEL bit 8 set a point's size S is the first coordinate output dword (o4, a
  float in pixels, taken in sixteenths): the point covers the pixels whose centre lies in [v - S/2, v +
  S/2) in x and y. H70-P1: its tile list holds the 16 x 16 tiles [tx, tx + 16) x [ty, ty + 16) that
  [v - S/2, v + S/2] meets (hi closed on the footprint, the tile open on its high side). H117-R: o4, not
  o5, is the size. The two cases of ta-risky (S = 1 and 8 at pixel centres, 3 and 192 pixels) are the
  fit; the 44 cases are held out (centres, corners, fractional vertices, sizes 0.5 to 256, 1/16, 1/32, 0,
  the ISP word 1 width 0x80, two programs for the row, a negative size last).
  `declared-followup3.tsv` sha256 `56ebdce67212f5295c2ff96ebff67d0545fe784cb5fdafae827f0973aa3dcf64`; `predictions-followup3.tsv` sha256 `96ab63b7f4d095868db7151012c2a33cfc595242e84ee6074d2593d131102eff`.
- ta-line-bisect: H70-L3, a one-line object's regions are those within 0.5 pixel of the segment; vertical
  and horizontal lines at distances 0.3125 to 2.0 from the nearest region, plus 3 jobs with ISP word 1
  width 0x80. `declared-followup4.tsv` sha256 `13e4e7fb22872bb15729bf0ddaeb9a1e58b2cec86d3519f859962a9f8275b9bb`; `predictions-followup4.tsv` sha256 `820861e5799edb22b1e7c36b4309bf2cfc4b0b14eb7e5a385147f1bb2917c2a2`.

## 9. Fifth follow-up (vdm-state-grid, 19 cases), declared after vdm-state-risky and before it runs

The grid of vdm-state-risky (word 9 of the two-object stream set to the base with bits 11:9 = v and
bits 7:0 = rows, rows 1, 2, 3, 8, v 0 to 7, one run each): v = 0 removes the object, v = 1 hangs, 2 to 5
and 7 draw all marks at every rows, v = 6 hangs at every rows tried, while v = 6 with the base's rows (5,
the xor jobs) drew all marks in 4 of 4 runs. H47-G1: v = 6 completes only at rows = 5. H47-G2: completes
at 4 <= rows <= 7. H47-N: v = 1 hangs at every rows. `declared-followup5.tsv` sha256 `5f17985eea3112d5ca49b709daab7b472aa413bb358feef59f6877774cdea8bd`;
`predictions-followup5.tsv` sha256 `9c664deef43ddc649edbb2481fe833d94aa33c5ecba075f178a809c1ef70d647`.

## 10. Sixth follow-up (vdm-vtask4, 13 repeat jobs), declared after vdm-vtask3 and before it runs

vdm-vtask3 kept all 126 vertices by the total at (N, field) = (6, 10) but the objects were irregular
([15, 6, 15, 15, 6, 15, 15, 9, 9, 15, 6]), where (8, 10) and (5, 10) with the same R * V were regular: the
total is a weak measure, and one run a case cannot show whether the splitting is deterministic. H94-DET: the
list of object vertex counts of a case is the same on every run (the reference is the case's first run).
`declared-followup6.tsv` sha256 `db0726717c58460d2197b4b72125020a9b7bcbeeb6727af94aab48b420611c1d`; `predictions-followup6.tsv` sha256 `de228102c4d78634adfb0771e6c634a5ab2cfc8039a4ed944ec90ad533c60106`.

## 11. Seventh follow-up (ta-line-width, 30 jobs), declared after ta-line-bisect and ta-points

ta-line-bisect's w80 jobs listed regions up to 1.87 pixel from a line that its 0x10 jobs list only within
0.5, so the ISP word 1 width enters the region test. H70-L5: half-width hw = max(w / 32, 0.5) pixel (w the
byte of bits 15:8), a region listed iff the segment is nearer than hw (closed rectangle); 28 jobs (widths
0x20, 0x40, 0x80, 0xf0 at distances 1, 2, 3, 4, 5, 6, 8), regions within 0.2 pixel of hw predicted '?'. H117-C:
the two-output size program with OUTSEL untouched completes with no pixel; with bit 8 it hangs again (2 jobs).
`declared-followup7.tsv` sha256 `347d9fa60f243edc9080e3ca9cfd6aeb61bf26bd26ca6ed7ddbdb635fbda28f7`; `predictions-followup7.tsv` sha256 `ea9b23313cf2bdb9029a3c3158f291ec997e05b0ac85ac278cf5b5be11e1b484`.

## 12. Eighth follow-up (event-irq-repeat: 3 runs of 18 cases and 6 controls), declared after the first irq matrix

H111-rep: the extra host interrupt a bit's enable shows (one detection a run) is reproducible: each case's
value of the first matrix run (Y or N, in `predictions-followup8.tsv`, read from the kept first-run data)
is the value of every one of three repeats. Cases: tri64 and fill, CR_EVENT_STATUS bits 0, 6, 9, 12, 13, 18,
20, 26 and CR_EVENT_STATUS2 bit 1; each run with three unarmed controls a kind (which must show none). The
script is event-irq-matrix.sh with KINDS, STAT_BITS and STAT2_BITS set and KEEP to another directory.
`declared-followup8.tsv` sha256 `8528aeb7dcb7cce9664ebcbad15e71357f542e639ffcc379b02d9c302b95c8d5`; `predictions-followup8.tsv` sha256 `438854ff6b0654e2c6a61d52277216da9a103d11b6e140e3a80ed84f44601fdc`.

## 13. Ninth follow-up (ta-points-vertex, 4 jobs), declared after ta-points and before it runs

ta-points gave one size to every point of a job (a constant vertex output). H117-V: each point reads its own
vertex's size row: a vertex program writing 16 * C + 20 (C = clip x or y) gives sizes 8, 32, 14 (by x) and
8, 14, 32 (by y) at the three vertices; the pixels covered are the union of each vertex's own square (the
sizes and pixel counts are in `predictions-followup9.tsv`; the recompute takes its own union). Pixel-centre and
corner placements. `declared-followup9.tsv` sha256 `c80732f850ff039d3a8fe8ad46de79888dc9fbf1a87345286f64bab538246a35`; `predictions-followup9.tsv` sha256 `487fb01ec16db78707f1afbb7c9197e9ce2d903134438c6d1affee61dc016e04`.

## 14. What ran (written at the end; sections 1 to 13 above are as declared and are not edited)

Order and times (laptop clock, 2026-11-08): ta-object-format 23:03:00, ta-tri-boundary 23:04:21, vdm-vtask 23:04:56,
vdm-state-units 23:05:31, event-timelines 23:06:34, event-irq-matrix 23:12:19 to 23:20:55, ta-object-format2 23:21:18,
vdm-vtask2 23:21:41, ta-tri-corner 23:22:02, ta-line-point 23:22:19, ta-risky 23:23:20, vdm-vtask-risky 23:25:03,
vdm-state-risky 23:25:21 to 23:31:47, ta-points 23:32:31, ta-line-bisect and vdm-vtask3 (23:34), vdm-state-grid 23:35:17,
vdm-vtask4 23:37:26, ta-line-width 23:39:23, event-irq-repeat 1 to 3 23:40:14 to 23:47:45, ta-points-vertex 23:48:22. The
tool was ~/sgxfive-test-1126 (sha256 751f7223c8c731a08d75cfc3920a5d1050488ca3bdc426be45b7c431e600f82e on the laptop) in
every job. Health (job, fill, a 64 x 64 triangle exact, debug switches, journal) from the Mac over the cable before the
first script, between the first two chains and at the end; every script ran the health triangle before and after and after
each failed job (no "health:" line, so no failed recovery, no retry, no abort). Run counts: 732 jobs (720 before the tenth follow-up of section 15, which ran at 00:09:48); the table in
out/job-counts.txt. The kept raw outputs are in the dataset dumps (gzip, raw sha256 printed in the run output), the run
output of every script in output.txt, the journal in kernel.log.

Disclosures. (1) The recompute (recompute/recompute_p1131.py) is independent of the run scripts, the generator and the
landed tools (its own decoder of the parameter buffer and TA data); it was written during the runs, from the format of 3d.md, and
its decoder of the control stream was extended twice after reading data (form 0x88 as both tiles with a mask each; the single-tile
masks' low byte; bit 21 and its extra dword in stream_objects): the declared region strings of ta-tri-boundary (made by the generator's
class model) matched the observed ones in 5 of 27 jobs with the first decoder and in 27 of 27 with the final one, and the E542 numbers
are those of the final decoder. (2) `H70-T1` and `H70-L3` were fitted to earlier data (E180; the one-line jobs of ta-line-point)
before they were declared as predictions for the jobs after; the fit sets are named in sections 2, 6 and 8. (3) H94-MR2 and H70-L5
were built from the jobs of the scripts before them, which are their fit. (4) ta-line-point's multi-line geometry and point jobs
were declared with the vertices of copies at 1/16 pixel; the multi-line predictions were wrong in 5 of 5 and are not refitted.
(5) The two-output size program (psize2) hung in every job (4 of 4: 3 with OUTSEL bit 8, 1 without); its H117-R case is therefore not scored. (6) The irq repeats
and the matrix share their script (event-irq-matrix.sh with KINDS, STAT_BITS, STAT2_BITS and KEEP set); their raw outputs
have the same case names in different directories. (7) No question was retired except one: Q117, answered by E544.

## 15. Tenth follow-up (vdm-vtask5, 12 jobs), declared after vdm-vtask4 and before it runs (written after section 14)

The capacity of a vertex task was measured against the output rows only; Q094 also names the attribute rows
(VDM_TASK1 bits 14:7, word 7 of the stream, default 1). H94-ATTR: those rows do not change which vertices reach the
objects: the list of object vertex counts at rows 2, 4, 8 (and 16 for one case) equals the list of the same job at the
default rows (read from the first runs by gen/gen_followup10.py). Cases (N, field): (8, 11) at 2, 4, 8, 16, (8, 10) at 2,
4, 8, (11, 7) at 2, 4, 8, (2, 15) at 4, 8. `declared-followup10.tsv` sha256 `6247a017ab8616363f0f2f287418c2f967d8bcdf648bf22370d2c3679a710a87`; `predictions-followup10.tsv`
sha256 `dc02ed9b4a20f327393ceb7cd2e25f6d359abeaf443404707614d182cce8fb46`.
