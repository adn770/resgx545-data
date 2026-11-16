# Round 29 decisions (2026-11-16, user present: flagged round)

Plan `plan/rank-round29.md`. User approved R29-1 to R29-6 (a): session r29-flag (r29f), 39 jobs:
s0 safe references; f1 Q108, f2 Q139, f3 Q241 (only if O29-1 freezes a form), f4 Q112 (8
planned faults); h1 Q010, h2 Q163 (only if O29-2 freezes a form) (5 recovered hangs); #limits cap
14; stop on any unplanned fault or failed recovery; no kernel change, no boot. Records
E1108-E1113. Q010 retires on one consistent reading; the rest narrow.

Q024 kit word (user, 2026-11-16, answer (a) "Approve all three"): the kit's "no register write of
ours" rule is lifted for `kreg` writes to 0x0a78 in flagged stages only; r29-kreg merged (main
adca992); Q024's session r29-kreg approved as closing29/kreg/design.md proposes (run while the
user is present; an unrecoverable stall needs the user's power cycle). Built: 154 jobs (k2
dropped: no timed many-triangles form), record E1114, Q024 narrows only.
