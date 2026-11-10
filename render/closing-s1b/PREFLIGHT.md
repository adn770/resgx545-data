# S1b preflight: jobs, time, controls, fit vs held out, risks, inconsistencies

Prepared 2026-11-09 from `closing/s1/analysis/{README,geometry,pixel}.md` and the S1 session.
Nothing ran on the laptop.  Frozen: `FROZEN.sha256` (89 files: generators, scorers, runner,
tables, predictions, programs, TOOLSRC.sha256, and the read-only imports pbdump.py, probe.py,
q164_fate.py, recompute_p1131.py, tex2.py, texmodel.py), `PREDICTIONS.sha256` (13 files).  Refreeze (`run/freeze_s1.sh freeze`)
only if the tables are regenerated, and never after the first job.

## 0. Review changes (2026-11-10; these override the sections below where they differ)

- **Order:** p-b2, g-e8b, g-e1, g-e3, p-c, g-e5, then p-d, p-f, g-e4w.  g-e4w rows: ix-c, then
  ix32-n, ix32-25, ix32-2425, ix-25.
- **Hypothesis gates that trip:** every group's limit is below its row count (2-run groups 1,
  p-d hx 3 of 4, hm 3 of 4; one-row groups 1), and the runner skips every remaining hypothesis
  row of a stage after 3 hang/fault events.  A skipped row is recorded in cases.tsv (rc `-`,
  class `skipped`) and is void for the scorers; a condition whose replicate was skipped after a
  fault is reported on its one run.  Consequence: a control that faults by design and runs last
  (f-ctl0, ix-25, d-L2e2-16) is skipped if three events came before it, and that stage is then
  cannot tell.
- **Tool source frozen:** `TOOLSRC.sha256` (51 files, in FROZEN.sha256) is the sha256 of the
  deploy inputs in the worktree; `stage_s1.sh --src` refuses any checkout that differs, before
  copying anything (today it refuses `~/src/resgx545`: the change is not committed; the file set
  is the same, so the committed main will match).
- **p-c control:** every config with a frozen `ctl_min_frac` (c-u, c-u-r2, c-u-r3) must have
  run and pass, else cannot tell.
- **g-e1 ladder:** exactly one raise -> no-raise flip per scene between neighbouring usable
  cells, else cannot tell (step outside the ladder or next to a void cell); two flips or a
  reversed flip refute both models; HP1 also requires its bound P_r - 2 <= C < P_s - 2 inside
  0x2fe <= C < 0x3de.
- **Repeats:** S1's post-hoc fits run again are set `repeat` (not held out), fitted models
  renamed "(S1 post hoc ...)": p-d d-L2e2-64, d-L3e3-64, d-st-L3e2-64, d-L2e2-21; p-c c-k7,
  c-k0, c-k3; g-e5 a8 r1-r3; p-b2 d-shift, d-tall; and, by the same rule, p-f f-dpm-dc0, p-c
  c-g23, g-e5 a12, g-e3 e3z-cut-p/-m.  Every scorer prints `held out: ...; repeat only: ...`.
- **Preflight:** writes a kmsg marker and exits 1 unless `sudo -n dmesg` shows it.
- **Bytecode:** every entry point sets `sys.dont_write_bytecode`; run tests with
  `PYTHONDONTWRITEBYTECODE=1` (no new `__pycache__` in resgx545-data; existing caches untouched).
- **Host:** export `SGX_TARGET_HOST=jtorra@10.42.0.2` and
  `SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"` (no local.env).

## 1. Tool changes (worktree, uncommitted)

`~/src/resgx545/.claude/worktrees/agent-aed0242cfe8ab4e23/userspace/libsgxfive`, tests first
(the C test failed to compile without the field, the CLI tests failed on the old tool):

- `probe --tri ... --index-width 16|32` (`sgxfive_tri_probe.index_width`, `put_copies`): 32
  writes the index list 0..n-1 as 32-bit words where the 16-bit list goes and sets VDM word 2
  bit 25 (`SGXFIVE_TRI_PROBE_VDM_INDEX32`, documented as the bit under test, not a field);
  refused with `--obj2` and above 126 vertices (no room at W_IDX); the probe line echoes
  `32-bit indices`.  Justified by S1's g-e4 frozen HW signature (bit 25 faults 0xd0008).
- `tri --move N:DX,DY` with `--tri-v`: the fine vertices (`v256`, in the job's unit) move too
  (`tools/sgxfive-test.c`, the move loop), so a moved fine render is moved.
- Not done (listed): per-render pixel-program pages for open scenes (`src/render.c:400-404`),
  which g-e8a (item 10) needs.

`make -C userspace/libsgxfive check` (main repo .venv on PATH): every C suite passes
(test_tri_probe 2620), pytest 378 passed, 2 skipped; `tools/usse-asm/test_tri_probe.py` and
`tools/bringup/test_scripts.py` 86 passed.  Source sha256 of `sgxfive-test.c`:
4250ca3639b4c32f91421b792b6f240c2a6e4d7e0d4e922d8f8444a4b2d02e70 (the staging checks the laptop
built exactly this source).

## 2. Jobs and time

| stage | jobs | conditions | expected hang/fault rows (hypo, last) | S1 analysis said |
|---|---|---|---|---|
| p-f | 6 | 4 | f-dpm-1e x2, f-dpm-dc0 x2 (HJ), f-ctl0 (E573) | 4 |
| g-e4w | 8 | 5 | ix32-* x6, ix-25 (S1's fault) | 6 |
| g-e5 | 10 | 5 | none (stophang everywhere) | 8 |
| p-d | 10 | 10 | 64/21/20..17-page jobs, d-L2e2-16 (E722) | 7 |
| p-b2 | 8 | 7 | none | 8 |
| g-e8b | 7 | 5 | none | 6 |
| g-e1 | 16 | 16 | none (rc 3 + "scene overflowed" is ok) | 14 |
| g-e3 | 14 | 14 | none | about 15 |
| p-c | 17 | 16 | none | 15 |
| **total** | **96** | | | |

The extra jobs are controls (p-f f-dpm-0 and f-ctl0, g-e4w ix-c and ix-25, g-e5 the two E702
bases, p-d d-ok-64 and d-L2e2-16, g-e8b o-2-alw-far, g-e1 the two measured controls) and p-c's
g23 pair (refrozen rather than dropped).  Time, from S1's per-stage times (about 5 s a plain
job, 10 to 15 s a hang or fault with its reset and health): p-f 1 min, g-e4w 2, g-e5 1.5, p-d
1.5, p-b2 1 (4.6 MB PB dumps), g-e8b 1, g-e1 2.5, g-e3 1.5, p-c 1.5; with health between
stages about **15 minutes**, plus staging (tool build on the laptop) about 3.

## 3. Every control row: how it passes, how it fails

| stage | control | passes | fails (scorer) | fails (runner) |
|---|---|---|---|---|
| p-f | f-dpm-0 (mask 0, P 0x23) | both renders overflow, every diff 0, `tri: 0 of 2 renders ok, 2 overflowed` (or K + M = 2) | `controls failed` unless exact | plain row: a fault stops (4); rc 1 without "scene overflowed" stops (S1: rc 0) |
| p-f | f-ctl0 (mask 0x1) | `BIF fault 0x91000` | not that word: cannot tell | hypo row, last: measured |
| g-e4w | ix-c | 15-vertex object (its words are the reference) | void/not 15: cannot tell | plain: a hang/fault stops |
| g-e4w | ix-25 (bit 25, 16-bit) | `fault 0xd0008` (S1 2 of 2) | anything else: cannot tell | hypo, last |
| g-e5 | r-n8-a1, r-n2-a9 | o0 counts 2288, 2821 (E702, S1) | other count: cannot tell | stophang |
| p-d | d-ok-64 | complete, A4 at 64 pages pixel for pixel (checked on S1's image) | other: cannot tell | plain: fault stops |
| p-d | d-L2e2-16 | `BIF fault 0x90002` | other: cannot tell | hypo, last |
| p-b2 | d-ctl, d-ctl-r2 | deviation set = E731's dp-ax-b2 set (S1 frozen) | cannot tell | no expectdiff: rc 1 stops (S1 rc 0) |
| g-e8b | t-opq-near, t-opq-far, o-2-alw-far | red, green, red (more pixels) | cannot tell | probe, rc 0 in S1 |
| g-e1 | c-1500-0x422 (no raise), p-1350-0x300 (raise) | dword 38 = 0 / 0x20 with the second run reaching thr0 | raised / void: cannot tell; positive not raising: METHOD BROKEN | rc 3 with "scene overflowed" = ok |
| g-e3 | e3i-ctl, e3z-flat099 (E651 object), e3k-ctl (S1's measured replace) | every control prediction holds | only its own group cannot tell | probe |
| p-c | c-e709 (17..29 tag-5 pairs), c-u x3 (tag-2 fraction >= 0.98 each) | criterion holds in all | cannot tell | probe |

Knob proofs: p-f the `alias_skip` read-back marker per job (kernel.log); g-e1 the job's own
0x0624 rows (`knob_value`, never the first sample); g-e4w the `32-bit indices` echo (and
`tests/emit_checks.py` for the words); g-e5 the echoed VDM words; p-d the probe's
`scratch at ... (N KiB)` line; p-b2 the echoed `vertices256`.

## 4. Fit vs held out

Everything S1's analysis read post hoc is FIT data for S1b; it enters only as a frozen
hypothesis (model names end in `(S1 post hoc)`) or a control reproducing an S1 value
(`(S1 frozen)`); `tests/test_s1b_scorers.py` shows the scorers read S1's data as the analysis
did, which is a reader check, not evidence.

- p-f: HI/HJ held out; f-dpm-dc0 is a repeat of a job S1 scored wrongly (post hoc exact).
- g-e4w: all held out (no 32-bit job ever ran).
- g-e5: HL70 (vertex 70 lost, count 2156) and HS1 (a12 = 2582) are S1 post hoc; the reset
  vs no-reset comparison (HC) is new.
- p-d: A4 at 64 and 21 pages fit S1's images post hoc (4 of 4): a frozen repeat, not held out
  in the strong sense.  HM ("the fault follows the mapping") is S1 post hoc; 17, 18, 19 pages
  are new.
- p-b2: HT and HV failed post hoc on S1; HCLIP is S1's post hoc candidate; all frozen here,
  new targets (192, 256) and triangles (448, 384) held out.
- g-e8b: the always table is new; HN is S1 post hoc.
- g-e1: HP1 matches S1's post hoc limit; the P = 0x320..0x3c0 cells are new.
- g-e3: HREP is S1 post hoc (e3k-ctl, e3k-above); the in-band w jobs and the clamp ladder new.
- p-c: HQ and the c-u cluster are S1 post hoc; g23's 0.25 is refrozen from S1's 0.253 (fit).

## 5. Risks

- New words on hardware: VDM bit 25 over a 32-bit list (if HX, a fault like S1's: hypo rows,
  at most two a group); translucent + always ISP0 0x03c00200 and opaque always 0x01c00200 on
  a second object; vtx_wclip with block word 14 (in-band clamp); 17 to 19 scratch pages.
- g-e5's noreset rows run right after an a8 job with no reset; S1's a8 jobs completed (no
  hang).  A hang there stops the stage (stophang).
- p-b2 keeps eight 4.6 MB PB dumps (gzip on the laptop, about 40 s).
- The laptop build uses the landed `tools/bringup/deploy-tool.sh` of the --src checkout, which
  replaces `~/libsgxfive-s1b` there (as S1's staging did with -s1).
- Nothing writes a clock-gate register, trc_hazard, kreg/kpoke, /dev/mem, GRUB, a kernel, or a
  firmware-task str; the guard checks the runner and tables (and refuses debugfs without sudo).

## 6. Inconsistencies

1. **Location.** The Write tool refused `~/src/scratch/resgx545/closing/s1b/` for this agent
   (worktree isolation); the session was built in the worktree's `debug/s1b/` instead.  Before
   that refusal, a shell copy had already created `closing/s1b/` with S1's unmodified framework
   files (run/, gen/, score/, tests/ and empty dirs).  That partial copy is stale: replace it
   with this directory (same file names) before staging.  Nothing was deleted.
2. **Job counts** differ from the analysis's (section 2): controls were added, g23 kept.
3. **p-d at 17 to 20 pages:** the A4 model reads only 80 to 83 KiB, past every one of these
   scratches, so every pixel is OOB in the model: HM's "A4 exact on the in-scratch pixels" is
   vacuous and only the outcome separates HM from HB-end.  "A dump past the scratch" is
   d-L2e2-20's pixel words (the tool has no dump of memory past the scratch).
4. **g-e4w:** `--index-width 32` sets bit 25 itself, i.e. the hypothesis under test is built
   into the option (documented in the header and README).  ix32-n predicts "not same" under
   both HW32 and HX, so it does not separate them; ix32-25 does.
5. **g-e8b:** "always" is DCMP 7 from `isp_words.py` (ISP0 bits 24:22; the landed job default
   0x01d00200 is always with depth writes off); always with writes on, and translucent always,
   have no landed run.  The control o-2-alw-far checks always on an opaque second object first.
6. **g-e3 HREP's position clause:** "x and y divided by the clamp" does not give S1's e3k-ctl
   square (vtx_w leaves x at -0.75 .. 0.75, so x/clamp lands far outside the guard band, yet
   S1 stored a 0.96-pixel square at the centre).  The position clause is therefore a separate
   model (HREP-xy) from the 1/w clause (HREP RZ / RN), and e3k-ctl's control prediction is S1's
   measurement (an object, 1/w 0x4479ffff, inside 31.5..32.5), not the rule.
7. **g-e1:** p-900-0x200 also qualifies as a positive control (it raised in S1) but is left out
   (3 partial renders, slow); one positive control raised once in S1 is the only one.
8. **p-c:** S1's c-u passed 0.990 against the old 1.0; the new 0.98 is set from that one run.
9. S1's `f-ctl0-r2` ran before `f-ctl0-r1` (the old ordering put the replicate in the middle);
   S1b orders plain rows (controls first), then hypothesis rows with their controls last.

## 7. What is missing

- Item 10 (g-e8a): needs the per-render pixel-program pages (tool change not done) or a
  probe with a loaded depth (probe has no --depth).
- Item 11 redesigns (g-e2 counts with HU1 from sgx-pipe, p-b1 per-pixel within-tile step,
  p-g ladders over a 1/16 step): not prepared.  Their scorer fixes (e2b open-kick and nparts,
  row_ranges' clear depth) are applied and tested on S1 data.
- Unit tests of the g-e1 ladder and g-e4w/p-b2 decision logic on synthetic data: those scorers
  are exercised on fake data (cannot tell) and, where names overlap, on S1's data only.
