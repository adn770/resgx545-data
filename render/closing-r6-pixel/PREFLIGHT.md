# R6-pixel preflight: jobs, time, controls, stops, risks, deviations

Prepared 2026-11-12 from `closing6/pixel/exp-pixel-r6.md` (sections 2, 4, 5, 6) and
`closing6/DECISIONS-R6.md` (all (a); R6-2 a), offline. Nothing ran on the laptop. Frozen:
`FROZEN.sha256`, `PREDICTIONS.sha256`, `FROZEN.commits` (resgx545 main d9b2969: E871 and E872 are on
it, and the predictions cite them). Refreeze (`gen/r6gen.py`, `run/freeze_r6.sh freeze`,
`gen/frozen_commits.py`) only before the first job.

## 1. Jobs and time

| table | jobs | sets | time |
|---|---|---|---|
| p6-rd (Q276) | 58 | 14 control, 42 HELD OUT (14 rd, 8 independent, 20 predicate), 2 replicate | about 5 min |
| p6-l3 (Q276, L3) | 8 | 4 control (R5's programs), 4 HELD OUT | about 45 s |
| g6-rwa (Q230) | 8 | 8 control | about 45 s |
| g6-rw (Q230) | 106 | 104 HELD OUT (72 L, 8 B, 24 E), 2 replicate | about 9.5 min |
| p6-s (Q023, S) | 22 | 4 control (c-s-all4, r-u), 18 HELD OUT | about 2 min |

202 jobs; R5 ran 5.3 s a job: about 18 minutes of jobs, plus about 30 s a table for ssh, health and
copy, and 1 to 4 minutes of staging: plan 30 minutes. Bounds: 1500 s a table, 300 s a copy, 150 s
health, 120 s a job (`timeout -k 10`). No reboot: the session needs the rgn4 boot (7.3.0-resgx545,
module srcversion 99CD90DA26E3AFF9C450517, checked loaded = installed = expected by the preflight). If
the laptop is back on stock Arch, the preflight stops (rc 1): do not run. Without the optional sets
(R6-2 b): `run/r6.sh --only p6-rd g6-rwa g6-rw`, 172 jobs.

## 2. Tool

`~/sgxfive-test-rgn4`, sha256 e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a
(`TOOL.sha256`, `run/r6.env`); `stage_r6.sh` and the runner's preflight refuse another hash. No new
userspace tool is needed. No regtimeline. `tests/mock_all.py`: 202 of 202 commands accepted by the
landed tool's `--mock` (`--kpoke rd:9=1` included).

## 3. Controls and frozen predictions

**p6-rd (Q276).** R5's command byte for byte (C_BASE) and word layout (marker << 6 | bits 5:4 << 4
| tag). rd-j = R5's walk row w-j plus `mov.skipinv r10, oJ; mov.skipinv.end o0, r10` last: the own
pixel shows what oJ held (E373). Premise (E871): o4..o7's own words reach no pixel, so readback is
the only window left. TRI = the own pixels of c-rd-0 in both jobs (>= 300). Classes at TRI (>= 90
percent in both jobs): S (oJ's word), A0 (o0's, 1:2), A4 (o_(j-4)'s, j >= 5; at j = 4 it is A0), X
(< 5 percent carry the job's marker), O:T.B (>= 90 percent one other marker), W:T.B.
- Controls: c-e709 (G-o4), c-u (G-o1 >= 0.98), c-all4 (5:1, else the stage is void), c-ow (bits 1 at
  >= 95 percent: the last o0 write is the pixel), c-rd-0 (W_A at >= 95 percent: readback through r10
  works), c-prd-0 k1 / k7 (lane labels at >= 95 percent: gates the predicate rows). Bridge (the
  driver's gate): c-e709, c-u, c-ow, c-rd-0.
- Models: H-STORE S S S S S S S; H-FOUR S S S !S !S !S !S; H-O0 A0 x 7; H-MOD4 S S S A0 A4 A4 A4
  (H-MOD4 implies H-FOUR; both named). n-rd-1/4 not S; x-rd-4/5 S with tag 13/14 (if rd-j is S);
  rd-4's replicate the same class.
- Predicate prd-j-k (j 3, 4; k 0, 1, 2, 3, 7): per lane (x & 1) | (y & 1) << 1, gated (bit 4 at lane
  k only), ignored (bit 4 everywhere), never (bits 0 everywhere); "the predicate gates the o_j write"
  iff gated alone survives the five k.

**p6-l3.** R5's p3-pa-k0 (x 5:0, y 5:1) and p3-pa-k3 (5:1, 5:1) byte for byte: the determinism
control; new k1, k2: x 5:1; y H-Y1 / H-Y2 / H-YN. A job's label: >= 10 tag-5 words of one label, no
other above 2.

**g6-rw (Q230).** R5's command (CMD) and template `vtx_zws.s`; every job exact and inside the viewport
(asserted). Premise (E872): no table-plus-Newton model fits; H-FRAC held 13 of 13.
- Controls (g6-rwa): rw-k0..k5 (the known words) and d-01, d-02 (R5's six words, two RZ + 1; four of
  them are words of E859's HELD OUT half, used as replicate controls, never for a fit).
- L: windows of 36 mantissas Bw + o s (o in 0..41) at strides 1, 2^8, 2^16, two bases each (sha256 of
  `r6-rw-win-<n>`, disjoint from all 130 read mantissas). Separable iff min frac(RZ + 1) > max
  frac(RZ); scored with >= 30 read, >= 4 RZ + 1 and >= 4 RZ above 0.5. H-SMOOTH(s): both windows
  separable = held, both inverted = refuted, else mixed. None predicted to hold.
- B: 8 jobs, all 24 mantissas with frac in [0.42, 0.62) (frozen search, sha256 of `r6-rw-b-<n>`).
- H-FRAC on L and B: held iff no word with frac < 0.5 stores RZ + 1 (>= 20 such words read; 117
  expected).
- E: R4's rw-10, rw-12, rw-01, rw-02 (most RZ + 1 words) at exponents -12, -6, -3, 5, 8, 12; H-MANT
  held iff 12 of 12 per exponent; FAILED shape = "no object at this exponent".
- Replicates rl-1a-00, rl-16a-00: their L job's words.

**p6-s.** c-s-all4 must show E406's pattern (tags 2..4 <= 2 a job, tag 5 >= 10), else the set is
void; H-OR vs H-OWN4 by s-0..s-7 and s-n4; r-u (c-u with `--kpoke rd:9=0`) must pass G-o1.

## 4. Fit vs held out

- FIT (inputs): E858's walk and E850's family (the word layout, R5's readings of c-all4 and P3),
  E842 / E851 / E859 (the known words, R4's deltas), E872's FIT half and H-FRAC (frozen there).
- HELD OUT: rd, independent and predicate rows; L3's k1 and k2; every L, B and E word; S's walk.
- E859's dense HELD OUT half stays unread for fits (only d-01 and d-02 run again, as controls).

## 5. Gates, stops, what the lead decides

Runner (`run/run_stage.sh`): 1 preflight (a file that is not the frozen one, a laptop FROZEN.sha256
that is not the Mac's, another tool or module, a debugfs file missing: reset, hold_recovery, regs,
render_param, render_tadata, render_pb_pages, alias_skip, and kpoke for p6-s; hold_recovery not N,
render_pb_pages not 0x422, alias_skip not 0, kpoke armed at the start, less than 200 MB free), 3
watchdog/BUG (touch nothing but the kpoke clear), 4 unexpected hang, fault or failure, 5 failed health
recovery, 6 a job did not return, 7 unknown knob or a kpoke outside the rule, 8 missing program, 12
registers unreadable, 13 reset failed, 14 fault latched before a job, 16 STATUS2 not 0x400 after the
reset, 19 kpoke armed before or after a kpoke row (cleared), 21 free space under 200 MB before a job.
Driver (`run/r6.sh`): 20 frozen files changed, 30 to 37 health after a table, 38 no SUMMARY, 39 the
attempt exists, 42 a gate did not pass (exit 1 a control FAILED, 2 cannot tell). debugfs writes:
`reset` and `kpoke` `clear` only; markers go to /dev/kmsg via `sudo -n tee -a`.

## 6. Risks

Low. Userspace only; no firmware `str`, no clock-gate write, no kernel or tool build, no reboot. New
forms: `mov` from an output register (run in E373) and E406's setup (27 clean jobs at one data row;
hangs only at 5 to 7 rows), last in the session; one `kpoke` of render details dword 9 a job (E406's;
the kernel leaves dword 9 at 0, so `rd:9=0` is the default).

## 7. Deviations from the plan

1. c-prd-0 ends with an unpredicated `or.skipinv.end o7` (tag 8), not `p1 or.skipinv.end o0`: no task
   of the session ends on a predicated instruction (a form no kept job ran; the simulator ends there
   whatever the predicate, unmeasured). Its o0 reading is unchanged.
2. g6-rw is one table (106 jobs) with E last; "three FAILED shapes among L and B" voids L and B in the
   scorer (post hoc), not a runtime stop: the laptop cannot decode a dump, and the jobs are safe.
3. The restore rows run c-u with `--kpoke rd:9=0`, and the runner also checks debugfs kpoke empty
   after each kpoke row and clears it in the exit trap.
4. p6-l3's controls void the set only; the set does not stop the session.
5. At j = 4, H-MOD4's A4 (o0's word) is the class A0; X and O:T.B are frozen as written in section 3.
6. Pins at main d9b2969 (the plan wrote d3de0b1; E871 and E872 landed since).

## 8. Offline tests (`tests/run_all.sh`, all pass)

`test_sim` (the sgx-sim harness builds; `--list`), `test_gen` (counts 202; argv twin: every row is its
plan row's template WRITTEN IN THE TEST with only the program changed, p6-s's by the two options;
reused programs are the published bytes; markers; determinism), `test_replay` (R5's kept files: the
readback reader reads A0, never S, on R5's walk; G-o4, G-o1, c-all4 5:1 hold; L3's reader gives R5's
k0 / k3 labels; the setup pattern FAILS on R5's plain c-all4; R5's 126-word table byte for byte; the
g6-rwa controls pass on R5's dumps and fail with one word changed; a wrong file name is void),
`test_rd` (plan tables; every new program read back from its bytes through the simulator's decode
and run at four lanes; mock worlds H-STORE, H-FOUR, H-O0, H-MOD4, a fifth vector, gated / ignored /
never, a dead readback, first-write-wins, no tag-5 word, R4's o2 slip; L3 lanes 1, 2, 0; S H-OR,
H-OWN4, plain), `test_rw6` (windows disjoint from the 130 read mantissas, B's fracs, E's exponents;
worlds e smooth, e hashed, RZ + 1 below 0.5, exponent-dependent delta, clipped at 2^12, RZ always, R4's
unscaled design, off-window jobs), `mock_all` (202 of 202), `run_mock` (the runner, every stop rule
incl. kpoke not dropped, kpoke armed at the start, no debugfs kpoke, low free space at the start and
during a stage; work directories removed; laptop files under ~/scratch only with TMPDIR unusable;
the guard, staging and the whole driver against the ARGV-driven fake tool), `guard_r6`. The fakes
read no clock and sleep nowhere; run_all passed with a busy loop on every core (section 9).

## 9. The lead must check before staging

- The laptop is still on the rgn4 boot (srcversion 99CD90DA...), `~/sgxfive-test-rgn4` hashes
  e6951558..., debugfs `dri/0/sgx/kpoke` exists and reads empty, `~/scratch/r6p` does not exist yet,
  and `~/scratch` has well over 200 MB free (the kept files are about 6 MB).
- p6-s is the only kpoke: if the lead prefers, `run/r6.sh --only p6-rd p6-l3 g6-rwa g6-rw` and p6-s
  later.
