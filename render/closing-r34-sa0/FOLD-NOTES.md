# r34-sa0 fold notes (builder, 2026-11-17)

- Record reserved: E1139 (Q136; cite E484, E496, E1106; Q129 and Q193 only for what the readers
  show about sa0 and pa0, not their instance-slot clauses).
- Built on main fd916fe (kit with T1's `@snap0`/`@cal` forms; this session freezes no register
  value or interval, `session.py lint` clean), data 9a809796f. Deviation from the plan's sketch:
  R outputs sa0 ^ K2 (not a fixed K2) so its pixels give sa0 per instance and its colour still
  differs from every marker; W writes with iaddu32 in every instance (one value, so E1061's
  shared-register mixture cannot arise).
- Scoring: `score.py s out/ATT/s` (CONTROL, READING, ROW, SUMMARY, Q136 RULE lines) and `score.py
  q136 out/ATT`. Expected values are only this attempt's own (program constants, the job before).
- Q136 line edits at the fold: keep to Q136's own clauses; if (b) decides and (a) does not, the
  lead may split (a) or narrow; the rule's NOT THE LINE list goes to the lead.
- Replay: refused (carried state); a SIM_UNMODELLED entry is sim work for a later agent.
- debug/ holds the mock's kept worlds and the run_all logs: not frozen, not published.
