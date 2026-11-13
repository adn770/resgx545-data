# Round 10 decisions (2026-11-13, lead; the user is away: "do another round")

Lead's rule without the user: each plan's recommended option, safe class only (no planned
faults), no kernel change or boot, no push.

Ranking `rank/rank-round10.md` (X-): R10-1..R10-8 all (a). R10-5 (retire Q030) only after
win0's verdict. R10-4 (Q071's stencil rows) goes into the seeds' Q121 stage on the new tool.
Offline O10: E990-E994. Session r10-x: E995-E999 (dcmp, zov, zbits, isp0x, win0; sb and grad
only if their offline checks pass).
Seeds `seeds/exp-seeds-r10.md` (S-): pending; records from E982 (to E989), more after E999 if
needed.

Seeds `seeds/exp-seeds-r10.md` (S-): R10-1..R10-10 all (a). Records: offline E982-E985
(Q282 retires on E982); S10-zls E986-E989 (zst2, zbg, st1 on t10); S10-tex E1000-E1004 (addr3,
cube3, t3b, srgb2); S10-geo E1005-E1008 (pivot, q139c, bgw, far2 on t10); S10-dpm E1009
(s6rep). Records above E999 need tooling item 8 (r10-tooling2) before their folds.
Tooling r10-tooling merged (main 9849dab, IGT sgxfive 2786f55fa); r10-tooling2: E1000+,
--tri-unit 0..20 / --tri-v int32, --stencil-fill bytes; then t10 is built once from it.
