# Round 13 decisions (2026-11-13, user present)

Plan `plan/rank-round13.md`. User: routine decisions R13-1, 2, 5-11 all (a); R13-3 (a) F1 and
F2 planned faults in r13-flag after every safe session; R13-4 (a) tooling T13 (kit words
`noreset`, `idle:S`, tests first) and F3 (Q163 hangs) as the very last stage.

Sessions (tool t10 throughout, module B60AB0B4, kit at main 05b7039 unless noted):
- r13-tex (r13t): srgb3, addr4, t3c, sb12; E1025-E1028.
- r13-zls (r13z): zbase, zbits, zfmt; E1029-E1031.
- r13-dpm (r13d): pr2; E1032.
- r13-isp (r13i): q201, q261, far (last; stop at first non-ok); E1022-E1024.
- r13-flag (r13f): F1, F2, F3; E1033-E1035; built on the T13 kit commit; user OK given.
Order: tex, zls, dpm, isp, flag. Dropped: Q210, Q107, Q045. Deferred: Q139 fx 2/3, Q108 refill.
Folds may propose retirement (R13-9); the lead confirms. Q046 text fix in r13-tex's fold.
