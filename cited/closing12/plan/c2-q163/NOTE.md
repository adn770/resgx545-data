# C2 / Q163: E700's counter on the 11.31 state sweeps (vdm/state-units)
Verdict: the counter HOLDS for v in 3..7 (54 of 54 jobs, 13 hangs, 0 misses under M1 and M3);
the v < 2 clauses are NOT confirmed (SLO 14/20 M0 and M1, 17/20 M3, 20/20 M2 but M2 misses in S37).
## Rule and freeze
- `c2_rule.py`, sha256 1e6a9e12a97e55562cfc7b8b41d43ef1d3c16900d6ab34401231735b81156868
  (`c2_rule.sha256`, `FREEZE.log`, frozen 2026-11-13T12:21Z before the scoring run).
- Counter: c = 0 after a hang or a logged reset; g(v) = v - 2 (v >= 2); hang iff c + add > 8.
  Variants M0/M1/M2 as E701 states them, M3 = E701's post hoc variant (formed before this data).
  Rivals: NULL (stateless, T' = 9), NEVER, V16 (v in {1, 6} hangs). Excluded (E545 word causes):
  bits 15:13 = 0/5/6/7, bit 17, closed forms: 28 jobs, all 28 hung, all in vdm-state-risky.
- Pass criterion (frozen): HOLDS = 0 misses on S37 (v 3..7) plus TRIV (v1 = v2 = 2) and more
  right than NEVER and V16 on S; PARTLY 1-2 misses; REFUTED >= 3. SLO (v 0, 1) judged apart.
- Run order = cases.tsv order = marker order (kernel.log). Resets/hangs from kernel.log
  (`hung, recovering`, `SGX reset:`); hang totals 2/40/5 per script equal the survey's 47.
  Every script ends with a GPU reset (lib1131.sh trap), so c = 0 at each script start (assumed;
  the scripts between them, not kept, cannot change that). The two reset-without-hang jobs are the
  last jobs of units and risky (the exit reset), no effect. c is teacher-forced from outcomes.
## Held-out set and leaks
All 133 jobs (units 36, risky 78, grid 19); g and T were fitted on E413, tested on E700's 52 jobs;
no fit rows here. Read before the freeze: survey hang totals per script (as briefed), the E545
body (its per-word outcome statements), cases.tsv inputs, 2 control rc lines. LEAK of mine: the
first 28 outcome lines of state2-fields report.txt (cases 0-27) were read before the freeze.
## Results (scored jobs 105 of 133: 28 excluded; none void)
| set | M0 | M1 | M2 | M3 | NULL=NEVER | V16 |
| S37 (54, 13 hangs) | 53 | 54 | 53 | 54 | 41 | 37 |
| TRIV (31) | 31 | 31 | 31 | 31 | 31 | 31 |
| SLO (20) | 14 | 14 | 20 | 17 | 14 | 14 |
Per script S37 (M1): units 12/12, risky 28/28, grid 14/14. Every S37 hang needs history (own sum
<= 5), so NULL cannot reach them. T = 8 is the only threshold with 0 misses (T 7 and 9: 5 and 2,
`c2_sens_posthoc.out`, post hoc). Verdicts: M1 and M3 HOLDS, M0 and M2 PARTLY (1 miss each).
Misses: M0 grid `sg-v7-r4` (c = 4, v 1 adds 0 not -1: predicted hang, completed);
M2 units `st-b1-b119-4-r2` (block-1 v = 0 reset predicted c = 4, observed hang at c = 7: third
refutation of the v = 0 reset). Block-2 hangs by v: 3,4 0/6; 5 1/6; 6 7/16; 7 3/10.
## v < 2 (not confirmed)
Block-2 v = 1 hung in risky at all 6 jobs (`st-b2-b119-1-r1/r2` at c = 0; `st-grid-r1-v1` c = 0;
`st-grid-r2/r3/r8-v1` at c = 5 by M1/M3) and completed in grid `sg-v1-r4..r7` (c = 4..1). M3
misses the three c = 5 hangs; M0/M1 miss all six. M2 gets all of them only because a block-2 v = 0
job sits before each (reset to 0), which `st-b1-b119-4-r2` and E701 contradict.
[infer] grid rows (bits 7:0: 1,2,3,8 hang, 4..7 complete) explain it as well as c.
Block-1 v = 1 completed 2 of 2 (c = 0); v = 0 completed 4 of 4 (SLO).
## Not scored
state2-fields / state2-consts (E427/E545 earlier probes): STOPPED, not scored. raw.txt case order
alternates (0, 31, 1, 32 ...), kernel.log holds one campaign line and no per-case markers, the
words sit in binary `bins/`, so neither run order nor the reset events are recoverable.
No other shapes or time gaps in this data (one shape, jobs seconds apart).
## Refutes it
A v 3..7 job hanging with c + add <= 8 after completed jobs and no reset: none in 54. Falsified
variant: M3's block-2 v = 1 clause (3 misses), M2's v = 0 reset (1 miss in S37, E701 twice).
## Records
Rests on E413, E700, E701, E545 (exclusions). [infer] Appending to E700: the counter also holds on
54 jobs of E545's sweeps (new shape: none; same stream); to E701: M2's v = 0 reset and M3's
block-2 v = 1 hang at c = 0 do not hold on `st-b1-b119-4-r2` and the c = 5 jobs.
Publishable: all scripts and outputs derive from the kept 11.31 session only (no firmware content).
