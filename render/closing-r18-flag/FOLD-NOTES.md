# r18-flag fold notes (builder, before the run)

- Records: E1070 f1 (Q299), E1071 f2 (Q108), E1072 f4 (Q241 bit 18), E1073 O18-1 (Q139 offline,
  `fit/o18_1.py`, `fit/o18_1.out`), E1074 f3 (Q139), E1075 h1 (Q112), E1076 h2 (Q163). Draft each
  method with `tools/records/new_record.py --session DIR`; appended corrections only.
- f1: the plan's premise failed (README.md deviation 1); E1070 says so and cites the kept
  `layout: fb` lines. Q299 retires (R18-6 a, the lead confirming) when both rows read as one end
  hypothesis with zv-c-g3 and zv-g5-24 passing. If G 3 completes, its colour image (diff) says
  whether the ZLS store or the PBE wrote pages 16 and 18 last (a reading, not frozen). sgx-pipe's
  `zls` refusal of a store past its buffer becomes the measured outcome.
- f2: run `score.py dumps f2` on the kept dir; an edm-load row that completed with E1046's store
  holds H-EDM-READ's load clause byte for byte. Q108 narrows.
- f3: E1073 is the offline fit (post hoc, 162 of 162; its rival 155 of 162). E1074 the held-out
  kind; the page (H-PAGE-END) is a separate reading. If f3-k4 faults 0x90004, note whether its
  health passed at the first try (E509's 640 x 480 rows did not).
- f4: the fault word names the requestor (hw_spec 5.5's table gets a row if it is new).
- h1, h2: hangs; h2's M1 counts the add per job; the fold states each shape's rows.
- Kit needs (report, do not change shared tools): REQUIRED per class (r14-flag's), again for f2's
  stores; the library mock refuses `probe --tri --dump-render` (no debugfs render files in the
  mock), so E756's form ran without it.
