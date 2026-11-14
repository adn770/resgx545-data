# r18-flag, read at the fold (2026-11-14, after the run; outside the freeze)

Attempt out/20261114-133536 (run.log), rc 0, every stage ran, no stop, no failed
recovery, strict health passed after all 10 events. The frozen scorer re-run on the kept files
is byte for byte (fold/reproduce.out); f2's stores: fold/score-f2-dumps.txt.

Post hoc readings (not frozen, [infer] where marked):

- f1: q299-g3 completed with the 20-page control's hash (0xd0530839d87ea325) and diff 0, its depth
  buffer holding pages 12 and 14 only (2048 dwords): the stores to buffer pages 16 and 18 went
  into the colour buffer and the PBE's colour reached those pages after them [infer].
- f3: f3-k4's 0x90004 is at TA data page 0x20008 (0x20008021), not H-PAGE-END's 0x20006, the page
  of E509's 256 x 256 x-side faults on another module: the TA's first faulting header write is
  not the first page past the kernel's TA data, and the page did not move with the layout
  [infer]. Health passed at the first try after both f3 faults.
- f4: both bit-18 rows faulted 0xd0400 at 0x1 (page 0, CID 1): FAULT_REQ bit 10 with FAULT_TYPE
  5, hw_spec 5.5's word of the background program's fetch (E764), on the library triangle and on
  E977's ramp alike.
- h2: the counter's step and threshold did not move with 24 or 48 vertices, one or two objects,
  8 or 16 temporaries, 64 x 64 or 128 x 64 (4 of 4 rows of M1).

Kit needs (FOLD-NOTES.md lists both; not changed here): REQUIRED per row class (f2's stores are
read by `score.py dumps`), and `probe --tri --dump-render` in the library mock.
