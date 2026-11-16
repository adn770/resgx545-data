# r34-sa0 fold (E1139)

- One attempt, out/20261117-001613: 60 jobs of stage s, 00:16:14 to 00:25:55 on 2026-11-17, rc 0,
  no stop, fault or lead decision. Every control passed: 18 writers (dword 0 = M, top K1) and
  6 colour jobs (K3). The frozen scorer, re-run at the fold, gives fold/reproduce.out, byte for
  byte the attempt's score-s.txt. The frozen rule is in fold/q136-rule.out: NARROW, neither
  clause decided.
- Why 18 readers and every pa0 row read cannot tell. This is a builder error: the frozen decode
  assumed each pixel is the value its own instance read, xored with the key. It is not. Every
  reader's pixels came in pairs {x, x ^ key}, about 1904 and 144 of 2048 (1812/236 in fla-r), so
  no decoded set matched M, PREV or TRI. The mock never had such a world, and no control ran the
  reader form on a known value. The H-RESET (2 of 2) and H-IDLE (6 of 6) "held" lines are
  artefacts: they say "not M", and a two-valued decode is never M. The two rows the scorer
  decided (rra-r2, rrb-r2) are the same two-valued pixels: "held" there is the scorer's
  category, not a reading.
- Post hoc (fold/posthoc.py, posthoc.out, labelled so). Model [infer]: what a reader reads
  aliases what earlier instances of the same job already wrote to o0. The first instances output
  v ^ key; later ones read that back and output v. So v, the value before the job's own writes,
  is the more frequent member of each pair. Dword 0 (the last store) is mostly v ^ key, which
  fits the model.
  - v = the group's marker M after a writer with no job between: no reset (nr), a debugfs reset
    (rs), and 10, 60 or 120 s idle. 14 of 14 rows: nr, rs, i10, i60, i120 and rr's first reader,
    both replicates.
  - v = the output of the job between: K3 after the colour fill, 0xff336699 after the t10 fill,
    0xff00ff00 and 0xff203040 after the t10 tri, and rr's first reader's keyed colour M ^ K2
    after it. 8 of 8.
  - That is H-ONEJOB's pattern on 20 of 20 R rows. H-PERSIST fails on k3, fl, tr and rr-r2;
    H-COLOUR fails on nr, rs, the idle rows and rr-r1.
  - pa0: v = the job before's colour on all 8 P rows, including both reset rows (pk3r). After the
    t10 tri, the pairs total 0xff00ff00 1536 and 0xff203040 512 in both replicates (1416 + 120,
    472 + 40; 1420 + 116, 472 + 40): E496's first-job mixture, count for count.
  None of this was frozen, so it decides nothing.
- A corrected rerun, r34-sa0b (record E1140), freezes these readings as the fit. Its readers
  output o0 = the value read (E496's form: the aliasing then has a fixed point), and it drops the
  rr group (its separation needed a keyed colour).
- Q136 is narrowed only: E1139 cited, the body carries the post hoc readings as such, and the
  line is unchanged.
