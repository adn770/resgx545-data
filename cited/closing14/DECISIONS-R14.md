# Round 14 decisions (2026-11-14, user present)

Plan `plan/rank-round14.md`. User: routine decisions R14-1, 2, 3, 6, 7, 8, 9, 10 all (a);
R14-4 (a) tooling T14 (`tri --refill K:BUF=V`, `--scratch-pages` up to 256) and a t14 build;
R14-5 (a) r14-flag with F1 (Q078, t14, 3 planned faults) and F2 (Q139, 4 planned faults); no F3.

Sessions (kit at main dddadbd unless noted; t10 except where t14 is named):
- r14-tex (r14t): srgb4, addr5; E1038, E1039.
- r14-zls (r14z): zgran, zodd, zbits2, zflat; E1040-E1043.
- r14-dpm (r14d): pr3; E1044.
- r14-isp (r14i): wind, g14 (poked-viewport rows last, stop at first non-ok), clipr (int32 ends
  last); E1045, E1036, E1037.
- r14-bif (r14b): refill on t14; E1046. Built after T14.
- r14-flag (r14f): F1 (t14), F2 (t10); E1047, E1048. Built after T14; user OK given. E1049 unused.
Order: tex, zls, dpm, isp, bif, flag. Folds may propose retirement and reword unmeasurable clauses
([infer], lead confirms); Q199 and Q243 text fixes in their folds.
