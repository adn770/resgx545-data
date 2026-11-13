# Round 13 ranking: laptop sessions from the round 10 to 12 row lists (Opus, 2026-11-13)

Basis: resgx545 `main` 05b7039 (records to E1021, 154 open), resgx545-data 75d01ee20, fork resgx545
2a650d74 (read only), laptop on module B60AB0B4 (one-shot boot; a reboot returns to stock Arch).
Inputs: section 4 of `closing11/plan/rank-round11.md` (rows R11-L1..L10) and of
`closing12/plan/rank-round12.md` (R12-L1..L5), round 10's leftovers (far2 for Q199, E1008 unused;
Q108's `--refill`, `closing10/seeds/exp-seeds-r10.md` sections 8 and 13). Nothing staged, built
or run; no laptop, SSH or cachix. No scratch scripts were needed: this file is the only output.

Checks done for this plan (read only):
- `userspace/` has no commit after a581c06 (`git log a581c06..05b7039 -- userspace/` is empty):
  **t10 (9bedc2d6, built from a581c06) is main's sgxfive-test**, so every row binds t10
  (`--tool-src
  t10=a581c06:userspace/libsgxfive/tools/sgxfive-test.c@closing10/k10/build_tool10.sh`).
- Q243's moved load base (round 10's open [check]): `tri` arms `depth_arm`'s pokes (rd:1, 11, 12,
  13; sgxfive-test.c line 3188) before a row's `--kpoke-render N:` pokes (line 3205), and the
  fork's `sgxfive_kpoke_take` (`sgxfive_kpoke.c` lines 135-157) writes the armed pokes in arm
  order, so **`--kpoke-render 1:rd:12=V` overrides the load base** with no tool change.
- The kit resets the GPU before every row (`run_stage.sh` line 124). Q163's counter is cleared
  by a reset (E700), so **a Q163 sequence cannot run in the kit as it is**: see T13.

## 1. Every listed row, ranked (retire first)

"Retire" = every open clause of the question line is decided by held-out rows if the frozen
hypothesis holds and the controls pass. "Narrow" = at least one clause stays open whatever happens.

| # | Row (source) | Question | Outcome if it holds | Jobs | Stage | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | R12-L1 position and coordinate set under byte 0 | Q201 | **retire** | 12 | r13-isp q201 | safe |
| 2 | Q243 moved load base (R11-L8) | Q243 | **retire** | 10 | r13-zls zbase | safe |
| 3 | R11-L3 sRGB flush threshold, y stage, channels | Q282 | **retire** | 9 | r13-tex srgb3 | safe |
| 4 | R11-L1 + far2: clip on held-out far vertices | Q261, Q199 | **retire both** | 16 + 8 | r13-isp q261, far | safe (far: untested range) |
| 5 | R11-L4 non-square twiddled u modes | Q177 | retire-capable | 12 | r13-tex addr4 | safe |
| 6 | R11-L5 T3 bits 11/12 LOD mode, bit 14 filtered | Q078 | narrow (retire with F1) | 16 | r13-tex t3c | safe |
| 7 | R11-L9 sideband bit 12 words | Q046 | narrow (bit 11 open) | 16 | r13-tex sb12 | safe |
| 8 | R11-L2 ZLS bits 12/16/20 alone and in pairs | Q071 | narrow | 15 | r13-zls zbits | safe |
| 9 | R11-L6 F7K fills, second y-ramp size | Q120 | narrow | 5 | r13-zls zfmt | safe |
| 10 | R12-L3 0x0748 bit 2 against the partial-render count | Q036 | narrow | 8 | r13-dpm pr2 | safe |
| 11 | Q078 bit 14 on a twiddled texture | Q078 | retire with row 6 | 4 | r13-flag F1 | **planned fault** |
| 12 | Q046 bit 11 | Q046 | narrow (explore) | 4 | r13-flag F2 | **planned fault** |
| 13 | R12-L4 Q163 counter, other shape, idle, job between | Q163 | narrow (retire-capable) | 18 | r13-flag F3 | **hangs**; waits for T13 |
| - | R11-L10 Q139 fx 2/3 mod 4 | Q139 | narrow | (4) | not planned (R13-5) | faults |
| - | R11-L7 Q210 new targets | Q210 | narrow | - | dropped | - |
| - | R12-L2 Q107 index-filled overflow | Q107 | nothing new | - | dropped | - |
| - | R12-L5 Q045 raised 4096 jobs | Q045 | offline first | - | dropped | - |
| - | R10 Q108 `--refill` | Q108 | narrow | (6) | not planned (R13-6) | needs a t13 |

### Rows the kept data already decide (dropped, or cut down)

- **Q107 (R12-L2)**: E628 already ran overflowed 1024x768 jobs over a load buffer of ascending
  indices (8 of 8 jobs, 0x28 and 0x30 pages): outside the zero region the store **is** the load
  buffer, dword for dword. So an index fill names no tile order, and the row as listed repeats
  E628. E1020 shows the plain-store overlay fails on the jobs without a load. Q107 needs a new idea,
  not this row. Offline (fold or later round): set E628's zero-region extent against E1020's
  15104-dword prefix.
- **Q210 (R11-L7)**: E1013 holds the per-target class at 22 targets with no rule of w and h. New
  targets only add rows to that table. Q210 keeps four other clauses (band 6's end, S3 offsets,
  band 4's raise, large objects). The jobs are long, and they narrow at best.
- **Q045 (R12-L5)**: E627's layouts can fix the state-page locator offline (round 12 finding 5:
  62 of 87 misses were reads of the wrong place). Do that before any row.
- **Q046, modes 20 and 27**: E999 answered it (bits 8:6 ignored, mode 15's image, 16 of 16).
  The question line still asks it, so it needs a text fix (R13-11). Only bit 12's words and bit
  11 stay.
- **Q243, integer load, NaN, equal depths**: answered by E977 and E995. Only the moved load base
  is left, so row 2 is all Q243 needs.
- **Q201, coverage and the position source at 0x26**: answered by E1018 (256 of 256) and E1010.
  Row 1 runs only byte 0 values other than 0x88 and 0x26, plus those two as controls.
- **Q071, the triple cleared together**: answered by E989 and E1014. Only the single bits and the
  pairs are left.
- **Q139's flag clause**: answered by E1011 (21 of 21). The highest target slot clause needs a
  dump at fx 2/3 mod 4, and every such kept job faulted. The stride and E509 clauses stay open
  whatever runs, so Q139 is not planned (R13-5).

## 2. Rows in detail (frozen hypotheses, rivals, split, controls, stops)

Every stage: `#limit 0` unless flagged; any unexpected fault or hang stops it (kit rc 4);
controls are `reads:` rows of the stage's own shape, not the default triangle; expectdiff rows
need `job: ok`; predictions frozen before staging (kit freeze). [infer] marks inferences.

**q201 (Q201, 12 jobs, probe --tri, t10).** Byte 0 of `--cmd 16` at 0x3c, 0x0f, 0xf0, 0x5a. Each
value runs with two programs:
- a coordinate set equal to the window position (vtxuse `--vtx-coords`, E606's attribute-plane
  form);
- E437's source-0 douti (E1010's identity form).

Frozen hypotheses:
- H-SAMPLE0: both read (x + lo/16, y + hi/16), lo the low nibble.
- Rivals: H-CENTRE (x + 0.5 always), H-SWAP (nibbles swapped), H-SPLIT (the position source
  moves and the coordinate set stays at the centre).

Coverage per row from sgx-pipe's E1018 model, values compared on drawn pixels only. All 8 rows
are held out (no kept job iterates under these bytes). Controls that can fail:
- 0x88 coordinate set (E606's x + 0.5 plane);
- 0x26 source 0 (E1010's x + 0.375, y + 0.125);
- 0x26 coordinate set (held out too, but it is the bridge);
- an end replicate.

Retire if H-SAMPLE0 holds 8 of 8. Replay: sgx-pipe isp (sample point), table `q201`.

**q261 (Q261, 16 jobs, tri --tri-unit 5, t10).** c6's frozen engine (`closing11/plan/c6-q261/`
`q261_rule3.py`, 5424683...), rerun only to print predictions. The rows:
- 4 pos-x far vertices (7 distinct images over G 16 to 22);
- 3 neg-x (lower bound 8 to 32, 6 images);
- 4 far-y (y bound, assumed symmetric);
- 3 on a 128 x 128 target (the guard relative to the target, 128 + G, or absolute, 80 to 86).

Frozen hypotheses:
- H-CLIP(G): one integer G in all pos-x rows; the lower and y bounds as their own integers.
- Rivals: H-EXACT (exact coverage) and H-PIVOT (E1005's displaced vertex, interval per
  distance).

All 14 rows are held out (the vertices were chosen after E1012 and never ran). Controls that can
fail: a replicate of E1005's far-x24p d = 0, and E979's far-ctl (E684's far21d0). Retire Q261 if
one G fits every row, and the bounds and the 128 rows decide relative versus absolute. Replay:
sgx-pipe isp (the clip, refused today), table `q261`.

**far (Q199, 8 jobs, tri --tri-unit 0 or 5, t10; last stage of r13-isp).** Seeds' far2: one
vertex at +-2^26, 2^28 and 2^30 pixels in x and y, ascending distance, plus a 2^25 replicate of
E979's x25n and far-ctl.

Frozen hypotheses:
- H-CLIP at the G that q261 reads (both are frozen before staging, so far's prediction is the
  survivor set G 16 to 22, scored per G).
- Rivals: H-SAT (saturation at a 2^31-unit word), H-WRAP, H-F32 (float32 window coordinate with
  1/256 rounding).

All held out. Risk: no fault up to 2^25 (E979); beyond that the range is untested (E684: "they
may hang the TA") [infer: the clip comes first]. The stage stops at the first non-ok. Retire Q199
with Q261 if H-CLIP holds to 2^30 (answer: the vertex reaches the format only inside the guard).
If the clip reading fails, Q199 narrows.

**srgb3 (Q282, 9 probe fills, t10, r10-tex srgb2's form).**
- x stage alone: corners (0, 1, 0, 1) at ky 0, kx 11 to 14 (5.2e-5 and 5.7e-5 predicted flushed,
  6.16e-5 and 6.6e-5 kept: pins 2^-14).
- y stage alone: (0, 0, 1, 1) at kx 0.
- The same pattern in channels 1 and 2 and in alpha.
- A trilinear row (two levels, LOD between).

Frozen hypotheses (c2's `next_row_b.out`):
- FTZ-OUT (every stage output below 2^-14 to +0, E1016).
- Rivals: FTZ-IN (x results flushed entering y only), BF11 unflushed, and H-ALPHALIN (alpha is not
  sRGB-decoded: E982's stage on linear alpha).

All held out. Controls that can fail: a replicate of srgb2-ctl (g-bl-st-a) and of an-t0b27.
Retire if FTZ-OUT holds on all rows (the "negative values" clause is void: sRGB bytes decode
non-negative and bilinear weights are non-negative [infer], stated in the record). Replay:
sgx-sim tex.rs (the flush is modelled since E1016), table `srgb3`.

**addr4 (Q177, 12 probe fills, t10, r10-tex addr3's form).** Shapes never run:
- 32 x 64, 8 x 64 and 128 x 32 in modes 4 and 6 (max(W, H) against W and H);
- mode 5 at 64 x 16 and 16 x 64 (corner base (W + H)/2 = 40 against 12 + M/4 = 28, side constants
  7M + 52 + s and 4M + 52 + s);
- mode 7 at 32 x 64;
- a 16-bit format at 32 x 64 mode 4.

Frozen hypotheses:
- H-MAX: 8 max(W, H) + 52, from E1000.
- E1017's post hoc mode-5 forms, with both corner bases as rivals.
- Rivals H-W and H-H (E1000's).

Controls that can fail: a replicate of E1000's 16 x 64 mode 4, and bd-uv5 16 x 16. Scratch: page
12 of 32, every rival's farthest read inside it (128 x 32: 8 x 128 + 52 = 1076 dwords).
Retire-capable. The "type" clause is [check]: the builder reads E910/E940 for whether any other
TEXTYPE takes u modes 4 to 7. If none does, the clause is answered as "twiddled 2D only".

**t3c (Q078 bits 11, 12, 14 filtered; 16 probe fills, t10).** From c8's list (`c8-q078/NOTE.md`):
- bit 11 clear at forced LOD 0 to 6 (smp2dreplace, 7 rows);
- bit 12 with T0's max level 3 and 5 (2);
- bits 12:11 = 10 (1);
- a 32 x 32 chain with bits 11 and 12 (2);
- bit 11 clear with mips off (1);
- bit 14 under a bilinear sample on a strided texture (2: does the floor(4096 u) move, E1003,
  apply per tap or to the footprint?).

Frozen hypotheses:
- H-LODMODE: bits 12:11 are a LOD-mode field, 00 level 0, 01 the gradient, 11 the last level
  [infer from c8]; 10 is predicted as each rival's reading.
- Rivals: a LOD bias (-3.5 or less, +2.5 or more), a constant dword 5460 (address, not level).
- For bit 14: per tap against per footprint.

All held out (c8 was fitted post hoc on E564's two jobs). Control that can fail: an-t3b11's
replicate (E564). Narrow alone. With F1 Q078 can retire.

**sb12 (Q046 bit 12, 16 jobs, probe --tri --sideband, t10, r10-x sb's form).** Modes 0 to 6,
each with two colours whose bytes all differ, plus one row at a moved triangle. Frozen
hypotheses: H-FIXED (the words do not depend on colour or position: E383's kept bit-12 words)
against H-O0 (a function of o0). Controls that can fail: E383's mode 8 row, and a bit-12 row
replicating E383. Narrow (bit 11 stays): retire only together with F2 and a rule there.

**zbase (Q243, 10 jobs, tri --depth --depth-store, t10).** `--kpoke-render 1:rd:12=V` moves the
load base by +4 bytes, +0x40, +0x1000, +0x4000, +0x10000 and to the store's own offset (rd:13).
`--depth-fill index`, so every loaded dword names its address. `--depth-pages` covers the
store's extent plus the largest move (HACKING weakness: depth_min_pages).

Frozen hypotheses:
- H-MOVED: the load reads E465's layout from the new base.
- Rivals: H-STOREBASE (rd:12 ignored, the load reads rd:13's), H-ALIGN4K (the base rounded down
  to 4 KiB), H-ALIGNTILE.

All held out. Controls that can fail:
- rd:12 re-poked to depth_arm's own value (must equal E977's z243 control);
- a +0x1000 move with the load bits off (nothing may change);
- E995's dcmp control.

Retire if H-MOVED holds on every move.

**zbits (Q071, 15 jobs, tri --depth --stencil --isp2, t10, r10-st1's form).** Starting from E988's
0x0017300e:
- bits 12, 16 and 20 cleared alone and in pairs, under E988's stencil test (6 rows) and on E977's
  ramp store (6);
- the set half (15, 21 to 23, 27 to 31) alone under the stencil test (1).

Frozen hypotheses: H-BIT-k for each k (one bit carries the zero stencil read and one the linear
store) against H-ALL (the triple only) and H-ANY. Controls that can fail: E988's base row (1024
drawn) and a q071-b0 replicate (2048). Narrow: bit 0 with other controls and the bits' meaning
stay open.

**zfmt (Q120, 5 jobs, t10).**
- F7K at constant stencil fills 0x3f and 0x1f (markers equal to the fill);
- F6C on a y-ramp of another size (48 x 32) and origin;
- F6C on a plane with equal rows in another tile.

Frozen: F7K and F6C (E1015) against the fixed-byte rival. Control: a z2y-f6 replicate (E986).
Narrow: formats 5 and 7 under the index stencil and the variable runs stay.

**pr2 (Q036 bit 2, 8 jobs, regtimeline over t10, r8-ldpm's knob form).** One scene at controlled
partial-render counts 0, 1, 2, 4 (`dbg:render_pb_pages=` per row, two replicates at 0 and 2).
Frozen: R-PR (E1019: bit 2 clears go with partial renders; predicted at least one clear line
per partial render and none at 0) against R-LEN and the constant. The same timelines also give
0x0700 to 0x0728 and CR_DPM_3D_PAGE_COUNTS' high half, as readings. The 0-PR rows are the
control that can fail. Narrow: CR_DMS_CTRL, the signature registers and the builder fault stay
open.

**F1 (Q078 bit 14 on a twiddled texture, 4 probe fills; planned faults).** E566's bit-14 twiddled
job faulted.

Frozen hypothesis: H-TWMOVE, E1003's move (floor(4096 clamp(u, 0, 1)) texels) taken in the
twiddled index. It predicts:
- a fault at the page of the first read past the mapping, with `--scratch-pages` below the reach;
- the image, without a fault, with the mapping covering the reach.

Rival: H-FAULTANY (bit 14 faults any twiddled read). Rows: one predicted fault, one predicted
no-fault, each followed by its bit-clear reference (the references are the controls). `#limit 2`
counts only the planned fault rows; if the no-fault row faults, that is a reading (E946's
lesson: the limit never counts a control's fault). With t3c, Q078 can retire.

**F2 (Q046 bit 11, 4 jobs; planned faults).** Bit 11 in modes 0, 4 and 8 (3 planned faults),
plus a bit-12 control. Readings: BIF_INT_STAT, the fault address and SB, as `hook_fault` keys.
This is exploration (no rule is frozen beyond "faults in modes 0 to 8"), so Q046 narrows, unless
the three addresses follow the target's base with one offset [infer, post hoc].

**F3 (Q163, about 18 jobs, about 6 expected hangs; waits for T13).** Sequences under E700's frozen
counter rule (M1; E1021's held-out form), each opened by a normal (reset) row:
- block-2 v = 1 at c = 0, 2 and 5 with grid bits 7:0 held at a completing value (c against the
  grid bits);
- another shape (a one-block stream, v = 7 twice: predicted hang on the second);
- the same pair with `idle:60` before the second;
- the same pair with a fill row between;
- the same pair with an ordinary reset row between (the kit's reset, no hang).

The health fill and triangle (v = 2 [infer], g = 0) add nothing under E700. That premise is
checked by one `noreset` health-only sequence. `#limit 8`. Stop at the first failed recovery
(a -110 reset has happened once, handover 2026-11-11): no reboot, the user decides. Narrow, and
retire-capable if every clause row holds and the lead accepts one other shape as "other shapes".

## 3. Sessions (safe first; one sitting on B60AB0B4; tool t10 throughout)

| Session | Stages (jobs) | Jobs | Wall | Prefix | Records | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| r13-tex | srgb3 (9), addr4 (12), t3c (16), sb12 (16) | 53 | ~9 min | r13t | E1025 srgb3, E1026 addr4, E1027 t3c, E1028 sb12 | safe |
| r13-zls | zbase (10), zbits (15), zfmt (5) | 30 | ~7 min | r13z | E1029 zbase, E1030 zbits, E1031 zfmt | safe |
| r13-dpm | pr2 (8) | 8 | ~5 min | r13d | E1032 pr2 | safe |
| r13-isp | q201 (12), q261 (16), far (8, last) | 36 | ~8 min | r13i | E1022 q201, E1023 q261, E1024 far | safe; far untested range |
| r13-flag | F1 (4), F2 (4), then F3 (~18, after T13) | ~26 | ~16 min | r13f | E1033 F1, E1034 F2, E1035 F3 | **flagged**: user OK |

Wall: about 6 s a job (r10-tex 48 jobs in 5.5 min, r10-x 91 in 9.5 min), plus about 3 min of
staging and preflight a session. Faults and hangs cost about 40 s each (reset and strict health),
and F3 has two 60 s idles. **Total about 45 min of laptop time** (safe about 29, flagged about 16).
Builders run offline in parallel first (about 1 to 1.5 h).

Order: r13-tex, r13-zls, r13-dpm, r13-isp (its far stage is the only safe row in untested range,
so it comes after every zero-risk stage), then r13-flag F1, F2 and finally F3. A failed recovery
in F3 ends the round, but everything else has already run.

Kit fit:
- r13-tex: fits (r10-tex/r10-x forms; probe programs from those sessions' `gen/`).
- r13-zls: fits. The mock must accept `rd:12` in `--kpoke-render`; the library-mock replay has
  had a kpoke file since 287031c.
- r13-dpm: fits (regtimeline `wraps = true`, `dbg:render_pb_pages`).
- r13-isp: fits (`--tri-unit`, int32 `--tri-v`, `--cmd 16=`).
- r13-flag F1 and F2: fit (`expectfault`, `#limit` without controls, `hook_fault`).
- **F3 does not fit**: the runner resets before every row (`run_stage.sh` line 124) and has no
  idle word.

Per-session premise checks (in each builder's tests, besides the library-mock replay):
- r13-isp: q201 rows have `--cmd 16=` and the vtx-coords program; q261 and far rows have
  `--tri-unit` and coordinates in int32.
- r13-zls: zbase has `--depth-store`, the kpoke after depth_arm, and `--depth-pages` at least
  the extent plus the move; zbits has `--isp2` only with `--depth --stencil --stencil-store`.
- r13-tex: scratch pages cover every rival's farthest read; every bit-14 row is followed by its
  reference.
- r13-flag: `#limit` counts only the planned rows; `hook_fault` reads the keys the scorer needs.

Replay vectors (each README names its table):
- `q201`, `q261`, `far`: sgx-pipe isp.rs, or refused under Q261/Q199 until the fold models the
  clip.
- `srgb3`: sgx-sim tex.rs.
- `addr4`, `t3c`: sgx-sim tex address (the u-mode offset refused under Q177 if not retired).
- `zbase`, `zbits`, `zfmt`: sgx-pipe zls.rs.
- `sb12`: sgx-pipe pbe.rs.
- `pr2`: refused (register timelines).
- F1 to F3: refused (faults and hangs).

## 4. Tooling package T13 (kit only; no new sgxfive-test binary)

One tooling agent on a branch off 05b7039, test first, before F3's build. Not needed by any safe
session.
- `run_stage.sh`/`lib_kit.sh`: knob word `noreset`. The runner skips the reset before that row,
  and only if the previous row ended `ok` or as an expected hang that the runner already reset
  (the guard refuses `noreset` on a stage's first row).
- Knob word `idle:S` (1 to 120 s, one fixed sleep before the job; the mock sets it to 0 as it
  does today's sleeps).
- Both words in the header list, `sessioncheck`, the guard and the library-mock replay.

Tests: a fake-laptop table with a `noreset` row (no `reset 1` write logged before it), a refused
`noreset` first row (rc 7), `idle:` out of range (rc 7), and the mock's world with no clock.
About 45 min on the Mac; nothing to build on cachix. F3 waits for it.

Not in T13 (R13-6): `tri --refill N:BUF`, a host fill between two renders, for Q108's
CACHECONSISTENT stale-data clause. It is a sgxfive-test change and would need t13 built on
cachix. It only narrows Q108 (its texture, depth-load, TA and EDM clauses need planned faults).

## 5. Offline parts (no laptop)

- Builders' predictions (all frozen offline): q261 and far from c6's engine, srgb3 from c2's
  `next_row_b`, addr4 from E1000/E1017's forms, q201 from sgx-pipe's E1018 model.
- Text fix: Q046's line drops the modes 20/27 clause (E999), in r13-tex's fold.
- Q107 (no row): E628's extent against E1020's prefix, in a later offline round. Q045: the state
  page locator from E627's layouts, the same.
- Unused numbers: E1036 (F4/Q139 if R13-5 b), E1037 (r13-bif if R13-6 b). E993, E994 and E1008
  (round 10) stay unused.

## 6. User decisions

1. **R13-1 Safe sessions.** a) r13-tex, r13-zls, r13-dpm, r13-isp in that order: 127 jobs, about
   29 min, records E1022 to E1032 (recommended); b) the same without r13-dpm (Q036 is narrow-only),
   119 jobs; c) only the retire-capable stages (q201, q261, far, srgb3, addr4, zbase): 67 jobs,
   about 16 min.
2. **R13-2 far (Q199 past 2^25 px).** a) Safe class, last stage of r13-isp, ascending distance,
   stop at the first non-ok (recommended); b) move it into r13-flag (user OK, after F2); c) skip
   it (Q199 stays at 2^25 and Q261 cannot retire on the format clause).
3. **R13-3 Planned faults F1 (Q078 bit 14 twiddled, 2 planned) and F2 (Q046 bit 11, 3 planned).**
   a) Both, after every safe session, with the user present (recommended: F1 lets Q078 retire);
   b) F1 only; c) neither.
4. **R13-4 Q163 hangs (F3) and T13.** a) The tooling agent adds the kit words `noreset` and
   `idle:S` (tests first). F3 runs last, about 6 hangs, `#limit 8`, and stops at the first failed
   recovery with no reboot (recommended); b) skip F3 and T13 this round (Q163 keeps its line).
5. **R13-5 Q139 at fx 2/3 mod 4.** a) Not this round: narrow only, every kept such job faulted,
   and the stride and E509 clauses stay open (recommended); b) a 4-row F4 in r13-flag (E1036).
6. **R13-6 Q108 `--refill`.** a) Defer: it narrows one clause and needs a t13 build on cachix
   (recommended); b) a sgxfive-test change (`tri --refill N:BUF`, test first, t13 on cachix) and a
   6-job r13-bif after r13-flag (E1037).
7. **R13-7 Dropped rows.** a) Drop Q210 (E1013), Q107 (E628 decides the index-fill row) and Q045
   (offline locator first) (recommended); b) keep 6 Q210 calibrations in r13-dpm (about +3 min,
   narrow).
8. **R13-8 Tool.** a) t10 for every row: main's sgxfive-test since a581c06, one binding
   (recommended); b) t4 in stages that replicate t4-era records (two bindings, a tool-equivalence
   control each).
9. **R13-9 Retirement in the folds.** a) A fold proposes retiring a question when every open
   clause is decided by held-out rows with passing controls. Void clauses are marked [infer]
   (Q282's negative values), and the lead confirms. This covers Q201, Q243, Q282, Q261 with Q199,
   Q177, and Q078 only with F1 (recommended); b) folds only narrow, and retirement waits for an
   offline round.
10. **R13-10 Record numbers.** a) As in section 3: E1022 to E1035, with E1036 and E1037
    conditional (recommended); b) the lead renumbers after the builds.
11. **R13-11 Q046 text.** a) Drop the modes 20/27 clause (E999) in r13-tex's fold (recommended);
    b) leave it for the next edit.
