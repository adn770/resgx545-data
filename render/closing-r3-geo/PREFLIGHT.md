# R3-geo preflight: jobs, time, controls, stops, risks, deviations

Prepared 2026-11-10 from `closing3/geometry/exp-geometry-r3.md` (design, offline fits, scripts) and the
binding decisions R3-G1 to R3-G9.  Nothing ran on the laptop.  Frozen: `FROZEN.sha256` (generators,
scorers, runner scripts and awk readers, tables, predictions, staged programs, templates, `TOOL.sha256`,
`TOOLSRC.sha256`, the read-only imports of the landed tree) and `PREDICTIONS.sha256`.  Refreeze
(`run/freeze_r3.sh freeze`) only if the tables are regenerated, never after the first job.
Laptop directories: `~/r3g` (runner, tables, pinned hash), `~/r3g-stage` (programs), `~/r3g-out` (kept
files and `state/`); never `~/r3p-*` or `~/r3xev`.

## 1. Jobs and time

| stage | jobs | what |
|---|---|---|
| g-da | 27 | depth threshold ladder: 6 controls, 21 held out (5 low, 4 high, 2 above half, 10 inside) |
| g-db | 16 | sign, sum rounding and q precision: 6 z>0, 6 q cells, 4 near w=1 |
| g-dc | 10 | viewport z words (`--blk 10/11`): 1 control, 3 at w=1, 6 at w!=1 |
| g-dd | 4 | made vertices at w!=1: two cuts on +w, two on -w |
| g-c4 | 10 | exact C at 2048x2048: 4 controls + 6 bisect cells picked by the runner (LT frozen: last raise 0xd4) |
| g-d36 | 6 | dword 36 (H-last) at 2048 and 4096, three or more aborts each |
| g-c6 | 5 | 2048x2048 target in a 4096x4096 context: calibration, g-c4's flip pair, thr0 0x100, 0x120 |
| g-c5 | 36 | 4096x2048, 2048x4096, 3072x3072: 12 each (calibration, 5 fixed cells, 6 bisect) |
| g-c7 | 11 | `--tri-full` at 2048x2048: calibration + gate, 6 cells at g-c4's flip, 4 bisect; LAST |
| **total** | **125** | 57 depth (R3-G1), 6 + 1 DPM side table (R3-G2/G3), 10, 36, 5, 11 |

H-last is a frozen side table (never gating except in g-d36) in every DPM job: all 68 DPM jobs list
`0x0720-0x072c` and carry the `dw36` prediction.  Time: depth jobs about 5 s (57: 5 min), DPM jobs 5 to
15 s with a reset each (g-c4 2.5 min, g-d36 3, g-c6 1.5, g-c5 8, g-c7 4; many g-c5 / g-c6 / g-c7 cells
are skipped by the fit gate and cost nothing), nine stage starts with health and copies 25 s each:
about 30 minutes of jobs, plan 45.  Staging is a copy (no build): 1 minute.  The 4096-class jobs keep a
4.6 MB dump each (about 25 jobs); preflight needs 600 MB free.

## 2. Frozen predictions and labels (full list in TABLES.md)

- **Depth** (all fits post hoc, E783's six words and E782's four vertices; 257 models tried, the fit rests
  on ONE word, t4-m2p6-3): candidate words of D1 D2 D5 T26 (t = 3/8) T27 (t = 7/16) K23 per cell;
  H-thr direction per cell (low and mid down, high and above half up, inside one flip along the
  fraction), `heldout`; measured words of the controls, `control`.  g-db: 21 labels (7 rules x 3 sums)
  on z>0 cells, 20 on the q cells, 8 rules on the near-1 cells.  g-dc: VF VT VZ VS.  g-dd: SH polygon,
  zigzag, prims, 1/w by HI-w, made depth 1.0 / 0.0 (HDP-made).
- **C**: LT = the last raise thr0 = floor(0x351 R / 32768): 0xd4 at 2048x2048 (stage-level `@g-c4`),
  0x1a8 / 0x1a8 / 0x1dd at the g-c5 targets; the affine laws (regions, side squared, macrotile area) are
  formulas over the MEASURED C(2048x2048) of g-c4, evaluated by the scorer.  H-target and H-context
  (g-c6), H-target and H-scene (g-c7): relative to g-c4's measured flip.
- **H-last**: dword 36 = max(count before the LAST abort - 2, 0); fit 73 of 73 kept jobs of R1 and R2,
  two separating (c3-2048-0xe2, k-1500-0x300), all label `heldout`.

## 3. Controls (each can fail) and what they gate

| stage | control | fails |
|---|---|---|
| g-da | da-ctl-z0-w3, da-ctl-zm05-w1 (0x3f000000, 0x3e800000), repeats of t4-m2p6-3 (0x3d88888c: the fit's own word) and t4-m6p1-7, w = 2 and 0.5 (exact product) | cannot tell; the m2p6-3 repeat reading another word stops the reading |
| g-db | none of its own: g-da's controls (scorer needs `out/g-da`) | cannot tell |
| g-dc | dc-ctl-default: blk 10 = blk 11 = 0.5 written explicitly, 0x3e800000 | cannot tell |
| g-dd | none of its own: the structure (set, order, prims, window positions) of each job | the job's made-vertex words are not tallied, "cannot tell for the failed jobs" |
| g-c4 | four controls `ctl:R/N`: 4096 0x372 raise / 0x374 none, 2048 0xe2 raise / 0x122 none | the RUNNER stops the session (rc 10), writes `state/CTLFAIL`; later DPM stages refuse to start (`CTL_OVERRIDE=1`) |
| g-d36, g-c6, g-c5, g-c7 | g-c4's four controls (scorer needs `out/g-c4`; same session, tool, day) | cannot tell |

## 4. Dynamic rows (new in R3: the runner decides from kept output)

State files in `~/r3g-out/state/G.obs` (thr0, class R/N/V) and `G.cal` (page need, partial renders).
Class from the job's own kept output: valid = the second TA run reaches the first abort's status and
there are 2 or more partial renders (R1's rule); R = dword 38 of buf09 is 0x20.  `B:G` = lo + (hi - lo)/2
(lo = the highest raise, hi = the lowest silent above); the bisect ends on a closed bracket, no raise,
no silent cell above, a silent cell below a raise, or a void cell inside the bracket.  `L:G` / `F:G` read
the last raise / first silent of g-c4.  `fit:G`: a cell whose 2 thr0 is not below the calibration's page need
is skipped (void by construction; in R2's data 0x162 with need 0x213 was void, 0x122 valid).  `gate:3` on
g-c7's calibration: more than 3 partial renders end the stage after one job.  Cells below thr0 0x60 or
above P 0x422 are never run.  The awk readers (`run/dpm_read.awk`, `run/bis.awk`) equal the scorer's
Python on the 73 kept jobs of R1/R2 and 3000 random observation sets; the bash runner's kept P columns
equal a Python twin of the runner on two synthetic worlds; the scorer re-derives every pick and flags one
off the rule.

## 5. Stops

Any `job hung` / fault line / unexplained failure stops the stage (rc 4, reset, health), searched in the
whole output; kernel watchdog or BUG rc 3; no return rc 6; health failure rc 5; a failed control rc 10;
the driver stops the session on any non-zero stage or a failed health.  rc 3 "scene overflowed" is the
normal class.  Preflight stops (rc 1): loaded srcversion != installed, != expected B21FDA82BD5E5CB5A627E3B
(`EXPECT_SRCV=any` to override), a missing debugfs file (reset, render_pb_pages, regs, buf09,
render_param, render_tadata), the tool hash differing from `TOOL.sha256` (STOP AND ASK, nothing is
rebuilt, R3-G8), no kmsg marker, less than 600 MB free.  The staging refuses a different tool the same way.

## 6. Risks

- g-d36 and g-c4's low cells make 3 to 8 partial renders a job (E630, E706 saw `job hung` in long
  partial-render sequences); the floor is thr0 0x60.  g-c7 is the hang-recovery class and runs last.
- g-c5 cells can all be void (page need too small): bounded by the fit gate; then the stage reports bounds
  only.  If a flip lies outside the fixed cells (5 cells span 0x19b..0x1c6 at 4096x2048), no bisect runs and the
  scorer reports an interval, not an exact limit.
- Nothing writes a clock-gate register, trc_hazard, kreg, kpoke, /dev/mem or a boot file; debugfs writes
  are `render_pb_pages` (allow-listed, restored) and the kernel's own `reset`, all through `sudo -n`.

## 7. DEVIATIONS from the design (and why)

1. **Controls of g-db, g-d36, g-c6, g-c5, g-c7 are other stages' (g-da's, g-c4's)**, not extra jobs, so
   the binding job counts (57 / 6 / 5 / 36 / 11) hold.  g-dd has no control job either: its structure
   predictions are the control.
2. **db-near2**: the design's w = 0x3f7fffff has RZ(1/w) = 1.0 exactly, so no rule can differ; replaced
   by w = 0x3f7ffffe (1 - 2^-23).  Pairs where z = -0.75 does not separate are moved to the nearest z that does.
3. **g-d36 "separating"**: defined as H-last's value differing from the peak reading's or the second-abort
   reading's (the design's "last differs from peak or second" also marks floor cases that separate nothing).
4. **g-c5 fixed cells** (5 a target) = the ends of the affine-in-regions bracket (last raise at C = 0x1bb and
   0x1e5 less 0x20) and LT's pair, so the design's 12 jobs a target = calibration + 5 + 6 bisect.
   g-c7's "4 around" = L-16, L-4, F+4, F+16, then 4 bisect.
5. **Expected srcversion** is enforced as a stop (design: "expected B21FDA..."): a different module needs the user.
6. **Stage-level pseudo-cases** (`@g-c4`, ...) hold the LT / law predictions that have no job row.
7. The inside bin 0.37-0.39 of g-da has explicit fractions 0.371 and 0.380 (so T26's 3/8 falls between them);
   cells within 0.004 of 3/8 or 7/16 are avoided (a tie would not read).
8. The depth model of g-dc rounds the product at w != 1 to nearest in every candidate (g-da decides that first).
