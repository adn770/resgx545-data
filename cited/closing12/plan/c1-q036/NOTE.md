# c1-q036: STATUS2 high halves and 0x0748 bit 2 over all kept closing timelines (round 12, offline)

Rule: `q036_rule.json`, sha256 7be7002fb0e5045b48f06b59bb0e75af188fe31157c09d63568a02a323b38d02
(FREEZE.log; read before: a0-cal-2048 header and after-read head for the format, E873/E1013 text,
dpm_raise.py code). Scorer `q036_score.py` -> `q036_score.out` (rerun with python -I).
G = max of 0x072c bits 31:16 over a job's tl lines (global page count); 38 jobs lack 0x072c (no G).

## H0: STATUS2 high halves (all sessions are "held out"; no earlier record read these bits)
- 697 timeline jobs, 285824 tl lines (r1-pixgeo, r2-geo, r3-geo, r3-geo-c, r5/r6/r7-dpm,
  r8/r9-ldpm, r10-dpm, s1, s1b): non-zero 0x0710 high halves 0. 1594 after-reads: 0x071c high
  half non-zero 0. Per-session counts are in the .out.
- Jobs by G (0x0748 jobs): G<=5 464 (G 0..5), G>=6 195 (6:104, 7:79, 11:3, 13:5, 18:4), 38 none.
  So H0 holds on the 195 jobs whose global list passes 5 pages (up to 18). H-TAIL and H-ANY
  refuted (no non-zero sample). Refuting sample: none.
- Caveat: 0x071c is only in after-reads (end state), not in timelines; after-reads of r8/r9-ldpm
  and r10-dpm do not exist.

## Bit 2 (0x0748 bit 2 clear), held-out sessions r5..r10, s1, s1b (558 jobs, 197136 lines)
Fit rows: r1-pixgeo, r2-geo, r3-geo, r3-geo-c (139 jobs, 88688 lines, 96 clear lines, 61 jobs).
Fit: q=0.00108 per line, r=0.1708 clears per partial render, 0x100 jobs 0.75 vs others 0.43.
Held, jobs with any clear line / jobs: G<=5 130/334 (155 lines, 827 PR); G>=6 27/186 (27 lines,
126 PR); no G 12/38. Log-loss (lower better), Brier in .out:
- G<=5: R-PR 199.5, R-CONST 224.9, R-0x100 226.0, R-LEN 276.6
- G>=6: R-PR 67.5, R-LEN 88.9, R-0x100 112.1, R-CONST 114.1
R-PR (clears proportional to partial-render count) wins both splits; R-LEN is worse than the
constant at G<=5 (its q is a per-line constant and jobs differ much in length); R-0x100 does not
beat the constant. Clear lines are rare (1 per ~1000 lines), mostly one per job: a pulse, not
a level. r10-dpm (17 jobs, 1 PR) has none.
- [infer] bit 2 clearing goes with partial renders, not with global page count or length; G>=6
  jobs have fewer clears per job than G<=5 (0.15 vs 0.38 per job), PR per job 0.68 vs 2.5.
- Limits: the 0x100 class is read from the case args/name string only; sampling is ~8 us so a
  short pulse can be missed; PR counted as stretches of 0x0658 bit 0. Confound of PR with
  session/job type not removed [post hoc, none attempted].

## Would refute
H0: one non-zero high half of 0x0710/0x071c at any G. R-PR: a held job class with many PR and
no clear lines (r10-dpm has 1 PR only, consistent).

## Records and publishability
Rests on E358, E443, E626, E630, E631, E873/E1013 (G definition). No landed claim needs
correction; E443's "0 in every sample" extends to 697 jobs, G up to 18. All files here are derived
from published data only, publishable.
