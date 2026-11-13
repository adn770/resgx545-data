# r8-geo fold notes (the builder's, frozen with the session)

The builder folds this session (round process, 2026-11-12). What the fold needs to know:

- Scores: `out/<attempt>/score-<stage>.txt` from score/score.py; SUMMARY lines per hypothesis.
  The cube READ lines (face ties, texel ties up/down per |ma|, edge in/out counts) and the addr
  READ lines (index per position, base page 12 = dword 12288 subtracted) are the reading tables.
- Records to draft (tools/records/new_record.py --session DIR): one per stage with a decided row.
  cube: Q284 (s, t) held out on (a), sizes on (b), ties and edge readings; decision R8-4 (a) retires
  Q284 if (c)/(d) decide ties and edges. seam: Q141 retires if every held-out set is exact
  (decision R8-3 (a)). addr: Q177 retires if one rival holds on u and v, else the reads tabled.
  vdm: Q271 retires or narrows to the layout if the forced = natural controls are exact.
- Inputs not in a repository at the freeze: gen/q284_rule.json (closing8/rank, sha256 52162471...;
  O2 publishes the scripts), gen/o8/ (closing8/offline/r8-1, O1's R8-1 table). Both are session
  files, frozen here; cite them through this session's published directory.
- The vdm render memory (`*.param.bin`) is kept for the p1131 decoder (E703's reading under a
  layout assumption); vdm-r2-n8-v8 decides nothing by design.
- Things a fold must not do: change kit/, tools/closing, tools/records (report them instead).
- Kit pinned at resgx545 d97c473 (r7-merge's tip at scaffold time; r7-merge moved on afterwards).
