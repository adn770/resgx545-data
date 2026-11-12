# R5-pixel preflight: jobs, time, controls, stops, risks, deviations

Prepared 2026-11-12 from `closing5/pixel/exp-pixel-r5.md` (sections 2, 4, 6, 7) and
`closing5/DECISIONS-R5.md` (all (a)), offline. Nothing ran on the laptop. Frozen: `FROZEN.sha256`,
`PREDICTIONS.sha256`, `FROZEN.commits` (resgx545 main f0d5b39: E850 and E851 are on it, and the
predictions cite them). Refreeze (`gen/r5gen.py`, `run/freeze_r5.sh freeze`,
`gen/frozen_commits.py`) only before the first job.

## 1. Jobs and time

| table | jobs | sets | time |
|---|---|---|---|
| p5-o4 (Q276) | 58 | 8 control, 48 HELD OUT (16 walk, 8 independent, 24 predicate), 2 replicate | about 5 min |
| g5-rwa (Q230) | 12 | 6 control, 6 HELD OUT (q) | about 1 min |
| g5-rw (Q230) | 36 | 14 HELD OUT (m), 2 replicate, 20 table | about 3.5 min |

106 jobs; R4 ran 5.3 s a job: about 10 minutes of jobs, plus about 30 s a table for ssh, health
and copy, and 1 to 4 minutes of staging: plan 20 minutes. Bounds: 900 s a table, 300 s a copy,
150 s health, 120 s a job (`timeout -k 10`). No reboot: the session needs the rgn4 boot
(7.3.0-resgx545, module srcversion 99CD90DA26E3AFF9C450517, checked loaded = installed = expected by
the preflight). If the laptop is back on stock Arch, the preflight stops (rc 1): do not run.

## 2. Tool

`~/sgxfive-test-rgn4`, sha256 e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a (R4's
pin, `TOOL.sha256`, `run/r5.env`); `stage_r5.sh` and the runner's preflight refuse another hash.
No regtimeline (no row needs it). `tests/mock_all.py`: 106 of 106 commands accepted by the landed
tool's `--mock`.

## 3. Controls and frozen predictions

**p5-o4 (Q276).** R4's p4-o4 command byte for byte (C_BASE) and decode (R4's `score_o4.py`, pinned);
word = marker << 6 | bits 5:4 << 4 | tag. Model family: the nine of E850 (OR(o0,o3), AND(o4,o6),
XOR(o0,o2,o6), XOR(o3,o5,o6), MUX(o4; o0, o2, o3, o5, o6)); `score/o5model.py`.
- Controls (8, first): c-e709 (E709's o4g-3, G-o4 structural as R4; bits 5:4 = 3 reported),
  c-u (R4's own program, G-o1 tag-2 fraction >= 0.98), c-all4 (every output with bit 4: 5:1 in
  all nine; any other reading voids the stage, not the session), c-v-a4 (R4's own program: 5:0,
  E838). Bridge (the driver's gate): c-e709, c-u, c-v-a4.
- Walk w-0..w-7 (HELD OUT): bits 5:4 at the tag-5 words, the plan's table 2.1 (nine different
  vectors). Positive control (gates the walk): >= 95% of w-0's own-pixel tag-1 words and of w-1's
  tag-2 words carry bit 4. The bits of every tag are reported per walk row.
- Independent rows z-o3, l-o4, l-o6, n-o4: the plan's table 2.2 (labels 5:0, 4:0, d1 = 10 to 100
  displaced tag-1 pairs; 0 in all 17 of R4's configurations; "none frozen" = cannot tell by design).
- Predicate sets (k = 0, 3, 7, both orders): P4 scored only if the walk's model reads o4, P3 only
  if it reads o3; gated vs ignored survivors.
- Verdict: "the tag-5 word is MODEL" iff controls and positive controls pass, the 8 walk entries
  equal one frozen vector, z-o3, l-o4, l-o6 read its cells and the replicate of w-3 agrees; a
  decided walk matching none: "family refuted, vector recorded"; else cannot tell.

**g5-rw (Q230).** R4's command (CMD) byte for byte. New template `vtx_zws.s` (o0 = S x, o1 = S y):
every vertex of every row is inside the viewport (asserted by the generator; the same check flags
exactly rw-15..rw-20 on R4's design). Frozen per job: object, 3 vertices at 32 + 32 S x / w, depth
0x3f000000, every word RZ or RZ + 1.
- Controls (part a): rw-k0..k3 (R4's programs, known words as E842), rw-k4 (w 0.3, S 1/4: RZ),
  rw-k5 (w 0.7, S 1/2: 0x3fb6db6e, RZ + 1, E795).
- q-15..q-20 (R4's quarter jobs at S 1/4): shape, RZ / RZ + 1, H-MANT on the 4 words whose
  mantissa was read (all RZ).
- m-01..m-14 (R4's rw-01..14 at scale 1/2 and 16): H-MANT (E851) = R4's delta, 42 words, 11 RZ + 1.
  Held iff 42 of 42; one miss refutes unless a replicate (rw-07, rw-10: R4's six words) differs
  (then not deterministic, cannot tell).
- d-01..d-20: 60 new mantissas (none read before), scales 1/4 to 4; FIT / HELD OUT split frozen by
  sha256 (`@split`) for a later fit; three FAILED shapes void the table.

## 4. Fit vs held out

- FIT (inputs): E850's eight kept configurations (the family), E851's 65 known words (H-MANT and
  its table), the control words.
- HELD OUT: the walk, independent and predicate rows; the q and m words; the dense table (half
  FIT, half HELD OUT for the later fit only).

## 5. Gates, stops, what the lead decides

Runner (`run/run_stage.sh`): 1 preflight (a file that is not the frozen one, a laptop
FROZEN.sha256 that is not the Mac's, another tool or module, a debugfs file missing: reset,
hold_recovery, regs, render_param, render_tadata, render_pb_pages, alias_skip; hold_recovery not
N, render_pb_pages not 0x422, alias_skip not 0), 3 watchdog/BUG (touch nothing), 4 unexpected
hang, fault or failure, 5 failed health recovery, 6 a job did not return, 7 unknown knob, 8
missing program, 12 registers unreadable, 13 reset failed, 14 fault latched before a job, 16
STATUS2 not 0x400 after the reset. Driver (`run/r5.sh`): 20 frozen files changed, 30 to 37
health after a table, 38 no SUMMARY, 39 the attempt exists, 42 a gate did not pass (exit 1 a
control FAILED, 2 cannot tell): p5-o4's bridge controls; g5-rwa's controls and the q shape stop.
The only debugfs write is `reset`; markers go to /dev/kmsg via `sudo -n tee -a`.

## 6. Risks

Low: userspace only, the shapes of 97 and 24 kept jobs with no fault and no hang, no debugfs
write but reset, no firmware `str`, no clock-gate write, no kernel or tool build, no reboot.

## 7. Deviations from the plan

1. g5-rw runs as two job tables, g5-rwa (6 controls + 6 q) and g5-rw (36), so that the plan's
   stops ("a control word off stops the stage", "three FAILED shapes stop the stage") act before
   the 36 jobs: the laptop cannot decode a dump (no Python there), the Mac scorer's gate can. The
   three-FAILED-shapes stop counts the q jobs (R4's slip); in the dense table it voids the table
   post hoc. Same 48 jobs.
2. Dense table: the tool's triangle forces w3 = 0.75 w1 + 0.25 w2, so 60 new mantissas are 40
   designed (the 32 odd k of 1 + k/64 exact, 8 hashed, nudged <= 6 ulps for exactness) and 20
   derived; the plan's "28 hashed" read as 8 hashed + 20 derived.
3. Knob `s2` on every row (the plan's STATUS2 stop; R4's two stages did not read it).
4. c-u is R4's program byte for byte (as c-v-a4 and c-e709), so three bridges, not two.
5. "Each o4 program is disassembled": the tree has no USSE disassembler; each of the 48 new
   programs is run in sgx-sim (lanes 0 and 3) and its eight output words compared with the table.
6. The walk's positive control gates the walk (the plan reports it beside the controls).

## 8. Offline tests (`tests/run_all.sh`, all pass)

`test_sim` (the sgx-sim harness builds), `test_gen` (counts; argv twin: every row is its table's
template with only the program changed, and the program its plan row needs; determinism),
`test_replay` (R4's kept files: c-v-a4 5:0, c-e709-x bits 5:4 = 3 at 39 of 39, G-o4 and G-o1
pass, d1 = 0 in R4; a wrong-file-name reader is void; R4's 1/w table reproduced byte for byte, the
six FAILED shapes rw-15..20, the viewport check flags exactly them), `test_o5` (plan tables 2.1 and
2.2, 48 programs in sgx-sim, nine models x gating named, a tenth refuted, c-all4 voiding, the
bridge failing, void, replicate, positive control), `test_rw5` (exactness, viewport, 48 programs in
sgx-sim with o0 to o3 exact, R4's programs rebuilt, mock worlds through REAL rewritten dumps: hidden
mantissa rule held, exponent rule refuted, pure RZ fails the controls, R4's unscaled design clips
the q jobs to 7 vertices: FAILED shape and the gate), `mock_all` (106 of 106), `run_mock` (the
runner, every stop rule, the guard, staging and the whole driver against the ARGV-driven fake
tool: it runs the staged program each command names in sgx-sim; a control of another shape, R4's o2
slip, fails the bridge gate), `guard_r5`.

## 9. The lead must check before staging

- The laptop is still on the rgn4 boot (srcversion 99CD90DA...) and `~/sgxfive-test-rgn4` hashes
  e6951558...; `~/r5p-*` do not exist yet.
- [infer, for the fold, not a plan change] E709's o4g-3 writes o4 only under p1 = (g25 == 3), and
  every tag-5 pair source is lane 0; if the predicate gates (E808: o1, 29 of 29), the six
  o4-reading models (AND(o4,o6), the five MUX) give no tag-5 word in c-e709, yet E838's c-e709 read
  39. E850's family check assumed o4 = 0xcf5 written there. The walk decides; the mock copies the
  lane-3 o4 word into lane 0 for E709's program so its G-o4 control passes in every model world.
