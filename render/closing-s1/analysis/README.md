# S1 analysis (2026-11-09): verdicts, causes, questions, draft records, S1b

Read-only analysis of the laptop session S1 of the question-closing pass. Nothing was run on the
laptop, nothing committed, nothing outside `closing/s1/analysis/` written. Details:
`geometry.md` (g-e1 to g-e5), `pixel.md` (p-b1 to p-f). Helper scripts, all written after the run
and all **post hoc**: `scripts/geo_*.py`, `scripts/pixel_*.py` (run with
`../pixel-faults/.venv/bin/python -I`). Draft records: `records/<unit>/E???-*.md` (pass
`tools/records/evidence.py` checks in draft mode).

The frozen verdict of each stage is the result. Post-hoc readings are labelled as such; none is
held out or confirmed.

## Per stage

| stage | frozen verdict | failed control / cannot tell: cause |
|---|---|---|
| g-e1 | METHOD BROKEN | hardware: 1350 at P 0x3e0 does not raise; the design had used that held-out prediction as a method control (scorer followed the design) |
| g-e2a | U for 6 of 6 scenes (no hypothesis scored) | none; u-2f "DISAGREE" is by design (peak capped at thr0) |
| g-e2b | E625 overflow rule holds, 12 held out | 10 of 12 on the K-triangle scene, 2 on an earlier kick (scorer lacks the open-kick check); count jobs void by design (each kick overflowed alone) and their predictions never read by the scorer |
| g-e3 | cannot tell (e3k-ctl) | hardware: WCLAMP writes a sub-pixel object (1/w = 1/clamp), E194's image misread as "no object"; scorer gates all groups where the design gates per group (score_geo.py:280-284) |
| g-e4 | ix-24 HH 2/2; ix-25, ix-2425 HW signature (fault 0xd0008) 2/2 | control ok |
| g-e8 | cannot tell (o1-less-ctl) | design: depth-ctl 0x0017100e lacks bit 14, so no load (E664); also the tool shades every object of an open scene with the closing render's colour (render.c:400-404) |
| g-e8b | HD and HP both consistent, HL refuted | design: HD and HP predicted identically in all 6; translucent images equal opaque |
| g-e5 | a7 HD 3/3, a12 "HO" 0/3, a8 HI 2/3, a32 HD 3/3 | scorer label: a12 is 2582 x3, neither E702's 2028 (HD) nor base 2288 (HO) |
| p-b1 | cannot tell (all EMPTY) | scorer: cleared 1.0 counted as covered (score_pix.py:49); then design: a row-wide line does not fit at 1024 width |
| p-c | cannot tell (c-u 0.990) | hardware: 5 of 497 sources keep the first write; exact-1.0 criterion (score_pix.py:271) |
| p-g | cannot tell (no transition) | design: u, v constant, ladder 0.03 of a 1/64 step; output resolves about 1/16 |
| p-b2 | control reproduces dp-ax-b2; d-shift neither | scorer: same coverage bug (b2model.py:45) |
| p-d | cannot tell (mixed) | generator: A4 hashes copied from the 16-page model = all-sentinel image (s1pix.py:356) |
| p-f | control ok; 7 conditions exact 2/2; dc0 "split"; 1f fault | scorer regex (score_pix.py:394) for dc0; design: mask 0x1f includes buffer 0 |

## Per question

| question | now | why |
|---|---|---|
| Q273 | narrowed: knob clause only | knob lands at P 0x200 to 0x420 (frozen per-job proof, 21 jobs); raise clause void (METHOD BROKEN); post hoc: no raise at P >= 0x3e0 for 1350 or 1500, dword 36 steps between 1350 and 1380 |
| Q210 | unchanged | post hoc: R2 and E625's rule fail at thr0 0x3be; a limit 0x2fe <= C < 0x3de fits |
| Q211 | narrowed | frozen held out: E625's overflow rule on K-triangle scenes (12/12; 10 as K scenes); U measured for 6 scenes; formula and k open |
| Q230 | unchanged | frozen cannot tell; post hoc per group: HR-none, clipped polygons, HO-region, HF-round, x/w exact, WCLAMP replaces w |
| Q112 | narrowed | frozen: bit 24 hangs, bit 25 (and 24+25) faults 0xd0008, control ok; width needs the positive test |
| Q272 | narrowed: repeat clause closed for a7 and the a32 hang (frozen HD 3/3) | a12 repeats a change 3/3 but not E702's; a8 2/3 |
| Q164 | unchanged | post hoc: a8 loses vertex 70 in 2 of 3 (9, 9, 3 split) |
| Q073, Q241 | unchanged | HD vs HP not separable; translucent equals opaque |
| Q088 | unchanged | load absent as E664 predicts |
| Q288 | unchanged | controls failed |
| Q200 | narrowed (control only) | dp-ax-b2's region reproduces exactly on a new run (frozen control); HT/HV unanswered, post hoc both fail |
| Q276 | unchanged | control failed; post hoc per-lane (quad position) gating |
| Q280 | unchanged | design |
| Q281 | unchanged | post hoc A4 fits at 64 and 21 pages; fault follows the mapping |
| Q076 | narrowed | frozen held out, control passing: pairs {1,2} {1,3} {2,3} {4,5} {1,5} and 1-5 together not needed (2 renders), 6/7/8/10/11 not over 3 renders |
| Q286, Q003 | unchanged | E573's 0x91000 seen 4 more times |

Nothing is closed outright. The frozen held-out results with passing controls are: g-e2b (Q211's
overflow rule on K scenes), g-e4 (Q112's bits break the job), g-e5 a7 and a32 (Q272's repeat
clause), p-f (Q076's pairs), p-b2's control (Q200's region reproduces).

## Draft records (`records/`)

- dpm: `E???-s1-g-e1-...` (raise below 0x422, METHOD BROKEN), `E???-s1-g-e2-...` (U of K scenes,
  E625's rule held out)
- ta: `E???-s1-g-e3-...` (TA objects; WCLAMP control)
- vdm: `E???-s1-g-e4-...` (header bits 24/25), `E???-s1-g-e5-...` (E702's events repeated)
- isp: `E???-s1-g-e8-...` (no load; translucent = opaque), `E???-s1-p-b1-...`, `E???-s1-p-b2-...`
- pds: `E???-s1-p-c-...`
- texture: `E???-s1-p-d-...`, `E???-s1-p-g-...`
- bif: `E???-s1-p-f-...`

All cite the dataset `closing-s1:<stage>`, which does not exist yet: the kept `out/` tree must be
published as a dataset (datasets/closing-s1.toml) before the records land, and ids assigned.

## S1b: the next frozen run, smallest first

1. **p-f** (4 jobs): f-dpm with mask 0x1e (not 0x1f) x2 and 0xdc0 x2; scorer accepts `tri: 0 of N
   renders ok, N overflowed` with every `diff: 0` as exact (score_pix.py:394) and labels HJ only
   when the mask excludes buffer 0 (413-414).
2. **g-e4 positive test** (6 jobs, tool change): `--index-width 32` (index buffer as 32-bit words,
   about 20 lines in put_copies and the header), justified by the frozen fault signature of bit 25:
   bit 25 set over the 32-bit buffer must return E414's object (2 runs), bit 24+25 likewise (2), the
   unflipped header over the 32-bit buffer must break (2).
3. **g-e5** (8 jobs): a8 x3 with and x3 without a reset before it (state carry), a12 x2; HO frozen as
   the base histogram, the vertex fate (q164_fate functions) in the scorer.
4. **p-d** (7 jobs): A4 predictions rendered at each job's own page count; L2e2 at 17, 18, 19 pages;
   a dump past the scratch.
5. **p-b2** (8 jobs): coverage fix (b2model.py:45); HT, HV and the clipped-polygon candidate frozen;
   no-clip and target-size ladder with the PB dump.
6. **g-e8b** (6 jobs): a table where HD and HP differ (compare always on the translucent object,
   translucent farther), plus "pass type changes nothing" as a frozen hypothesis.
7. **g-e1** (14 jobs): 1350 and 1500 at P = 0x320, 0x340, 0x360, 0x380, 0x3a0, 0x3c0, plus 1350 and
   1380 at 0x3e0; controls c-1500-0x422 and p-1350-0x300 (raised in S1) only; frozen "one step P for
   both scenes" against "scene-dependent step".
8. **g-e3 subset** (about 15 jobs): per-group gate in the scorer, cut scored by vertex identity, 1/w
   on triangles that stay inside the guard band, WCLAMP control predicted as "replace" (1/w =
   1/clamp, object present), a clamp ladder between 1e-5 and 1e-3.
9. **p-c** (15 jobs): c-u x3 with a frozen criterion (>= 0.98 or the cluster named), the replicate
   compared (score_pix.py:241), g23's HP prediction refrozen or dropped.
10. **g-e8a** (8 jobs, tool change): `--depth-ctl` with bit 14 (0x0017500e), and per-object colour:
    keep each render's pixel programs in their own page while a scene is open (render.c:400-404)
    or build the pair with `probe --obj2` over a loaded depth.
11. **Redesigns, not S1b-ready:** g-e2 counts (an overflowed kick ends the open scene, so k needs a
    single-kick scene; HU1 must be computed offline from sgx-pipe's stream bytes and frozen against
    the six U now measured, which are fit data); p-b1 (per-pixel within-tile step on E731's 256 x
    128 target, coverage fix score_pix.py:49, WIDE threshold); p-g (ladders spanning a 1/16 level
    step first).

**Tool changes.** `--index-width 32` (item 2, earned by g-e4's frozen HW signature). `tri --move`
with `--tri-v`: the move is added to the 1/16-pixel vertices only (`tools/sgxfive-test.c:2921-2927`)
while a fine render uses the 1/256 ones (`src/render.c:407-410`), so a moved fine triangle is not
moved; needed for small or fine K-triangle scenes (E2) and moved fine planes (B2-type jobs). Per-
render pixel-program pages for open scenes (item 10).

**Scorer and generator fixes before freezing.** score_geo.py: e2b open-kick check and `nparts`
reading (185-192), e3 per-group gate (280-284) and cut by identity (246), e5 HO = base (374-386), e1
positive controls only from measured raises (69-72); score_pix.py:49 and gen/b2model.py:45 exclude
0x3f800000; score_pix.py:241, 271, 394, 413-414; gen/s1pix.py:356 (A4 at the job's pages).
