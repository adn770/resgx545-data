# r29-flag fold notes (after the run, outside the freeze)

Attempt out/20261116-055520 (driver rc 5): s0 8 of 8 references passed (GATE f1, f2, h1 open);
f1 ran both rows, both faulted as planned; f2 ran both rows, both faulted as planned, and the
kit's strict health after f2-y512 failed twice, so the stage aborted (5) and h1, h2 never ran
(they run in r29-flag2, unchanged).

- f1 (E1108): `q108-both-load` BIF fault 0x80200 at 0x3e001001, `q108-both-tex` 0x80002 at
  0x3e003001, each after the kernel's `vm_map ... PTE flags 0x12` line: H-WO-READ 2 of 2,
  H-EDM-TYPE and H-PASS 0 of 2 (score-f1.txt, reproduced byte for byte, reproduce.out).
- f2 (E1109): both rows 0x90004 (H-KIND 2 of 2) at page 0x20008 (`0x20008021` for x,
  `0x20008061` for y, the low bits the directory list): H-AXIS held on x and FAILED on y (0x20010
  predicted), H-SIZE FAILED on both (0x2000a, 0x20012 predicted). score-f2.txt is the frozen
  scorer run at the fold (the stage kept no score file). [post hoc] At 512 x 512 the TA data ends
  at 0x20008000 (c-512 read 32768 bytes), so both writes faulted at the first page past it; at 384
  x 256 (E1074) the end is 0x20006000 and the write faulted at 0x20008 as well.
- The strict health after f2-x512 drew (fill and triangle). After f2-y512 the fill drew (fill3,
  fill4: `diff: 0`) and the 64 x 64 health triangle faulted twice, each with the kernel's `BIF
  fault 0x90004 at 0x20008062` (jobs 714, 716), the reset clean after each and no `SGX recovery
  failed` line: a plain triangle in a new context faulted the TA's header write at the same page
  after the y-side word. [infer] Some TA state the y-side word left survived the kit's debugfs
  reset and a fill job; the lead's later triangle drew (outside the kept files).
