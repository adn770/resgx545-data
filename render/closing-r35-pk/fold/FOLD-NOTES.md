# r35-pk fold notes

Attempt 20261118-090046 (fold/lead-run.log, fold/lead-stage.log): rc 0, 92 jobs in five stages,
no fault, no hang, no stop, on the laptop at home (192.168.12.234) with the test kernel's module
7CE8E38EDB97FC5EA4F6C90. Every control PASS: s0's nine (the ramp in mode 0, its image by
construction; the ramp in mode 4, split 127 clear, 128 set; E031's colour images of modes 3 to 7,
9 and 10), each stage's mode 0 reference (H-RAMP), pw's E031 images of modes 12 and 13. s0 holds
only controls, so its SUMMARY reads "cannot tell: no row decided"; every gate opened. The scores
reproduce byte for byte (fold/reproduce.out). Record: **E1146**.

## Frozen verdicts

- r1, modes 3 to 6: **H-RZ** 2 of 2 rows in each mode, every dword; H-RN, H-RNE, H-SCALE not
  supported (0 held, 2 FAILED each mode). Clause (d): RGB565 truncates.
- **H-AS0** 40 of 40 (r2) and 2 of 2 (r1, mode 11); H-AS0-PART refuted 42 of 42.
- **H-WHOLE** modes 9, 10 (r1), 12, 13 (pw, the scratch too), 2 of 2 each; H-NARROW refuted.
- r3: **H-1136** in modes 0, 5 and 6 (4 of 4 each); in mode 4 **H-LOWDEP** 4 of 4 (H-1136 0 of 4).
- The narrow rule (frozen): NARROW; (b) readings only, (c) not run.

## Post hoc (fold/posthoc.py, posthoc.txt; not frozen)

- Mode 4 with bit 25: the low 15 bits are the 0x80 reference's on every pixel; the alpha bit is
  set for alpha 0 to 191 at 0x02000040 and 0 to 63 at 0x020000c0, so the threshold takes the
  inverted alpha (255 - a >= low byte) rather than inverting the thresholded bit. At the low byte
  0x80 the two orders give the same image, which is why E385 and E1135 could not tell them apart.
- Every replicate pair equal dword for dword (r1, r3, pw).
- Modes 9, 10, 12, 13 layout (each dword's colour names its pixel): 9 holds 120 triangle colours
  in 1024 dwords, 10 714 in 2048, 12 714 at a step of 2 dwords and 152 more in 1536 scratch
  dwords at an 8-byte stride (pixel rows 40 to 54), 13 120 at a step of 4 and 792 in 2816 scratch
  dwords at 16 bytes (rows 20 to 54). No simple raster map fits (fold/posthoc.txt): left open.

## The fold

- sgx-pipe `pbe.rs`, tests first: RGB565 truncates every channel (the `rgb565_known` refusal is
  gone), modes 4, 5, 6 at bits 8:6 = 0 modelled (ARGB1555 with the low byte's threshold, ARGB4444,
  A8 over RGB332, all truncating), bit 25 inverting the alpha before packing (mode 4's threshold
  then reads the inverted alpha), the 40 ARGB8888-like modes as mode 0 with bit 25 changing
  nothing; `reg0400_known` admits the words that ran there; 9, 10, 12, 13 refuse naming their
  layout (Q302). `tests/closing_r35_pk.rs` replays every modelled row of the session; r34-q044's
  replay now models its mode 4 to 6 and ARGB8888-like rows too.
- Q302 narrows to (b) the layouts of 9, 10, 12, 13, (c) mode 14 and the fields 1 to 7 of modes 4
  to 6 and the ARGB8888-like modes.
