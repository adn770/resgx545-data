# r34-q044 fold notes

Attempt 20261116-232915 (fold/lead-run.log, fold/lead-stage.log): rc 0, 198 jobs in four stages,
no fault, no hang, no stop. s0 holds only controls: its seven PASS (E268's mode 0 at 0x80, bit 25
and bit 11; E031's mode 4; E385's mode 4 at 0x80 and bit 25, mode 8 at bit 25), so its SUMMARY
reads "cannot tell: no row decided" (no held-out row in it) and the gates of p1, p2 and pw opened.
Every stage control PASS (p1-ctl-m00, p2-m00-ref, p2-m04-ref, p2-m05-ref, p2-m08-ref,
pw-ctl-m00). The scores reproduce byte for byte (fold/reproduce.out). Records: **E1135** (p1,
pw), **E1136** (p2).

## Frozen verdicts

- p1: **H-E031** 55 of 55 (every reference is E031's kept image on 7CE8E38E); **H-REPEAT** (mode
  26) 1 of 1. **H-INV25** fit 3 of 3, held out not supported: 9 held, 43 FAILED; **H-SUBSET** fit
  3 of 3, held out 51 held, 1 FAILED. pw: H-E031 2 of 2, H-SUBSET 2 of 2, H-INV25 0 of 2.
- p2: **H-GE** 9 of 9 (H-GT refuted 9 of 9), **H-THR1** 26 of 26 (H-THRN refuted), **H-NULL**
  15 of 15 (H-ACT refuted), H-REPEAT (mode 26 under the ramp) 1 of 1.
- The retire rule (README.md, frozen): **RETIRE**.

## What bit 25 changed (fold/posthoc.txt)

- The one held-out mode that failed H-SUBSET is **mode 6** (A8 with RGB332): bit 25 inverts its
  alpha byte, xor 0xff00ff00 on all 2048 written dwords (0x80f1 -> 0x7ff1, 0xff25 -> 0x0025).
- Bit 25 changes the alpha field in exactly modes **0, 1, 2 (E268), 4, 5 (E385, again here) and
  6**, and nothing in 7 (A8 with R8, alpha and red), 8 (E385, again here), 9 to 13, 15 to 21, 23
  to 33 and 35 to 63 (among them the 40 ARGB8888-like modes other than 0).
- Mode 22: of the 4091 dwords its two references repeat, 3 differ in the bit-25 row
  (0x08800088 -> 0x08800000 at dwords 1008, 1016, 1017); mode 34: 0 of 4092. Not modelled
  (Q012); the 3 dwords are of the varying 0x88 constant Q012 names [infer: run-to-run variation,
  not bit 25].
- Mode 14 not run (E031: it faults).

## The low byte and bits 11:8

Mode 4's stored alpha bit is set at an alpha equal to the low byte at all nine values (2 to 40
pixels each: 0x02 29, 0x08 2, 0x3e 10, 0x42 9, 0x78 28, 0x84 32, 0xbc 40, 0xc4 39, 0xfc 30), so
alpha >= low byte. The low byte at 0x00, 0x40, 0xc0, 0xff changes nothing in modes 5 to 8 and at
0x40, 0xc0 nothing in 1, 2, 9, 10, 11; 0xf80 changes nothing in 1, 2, 3, 5 to 11, 15, 20, 24, 26,
27.

## The fold

sgx-pipe pbe.rs: `reg0400_known` admits the words that ran in the modes `pack_of` models (7 and 8
at bits 8:6 = 0: 0x80, bit 25, the low bytes 0x00, 0x40, 0xc0, 0xff and 0xf80; 15, 20, 24, 27:
0x80, bit 25, 0xf80; 18, 25, 28: 0x80, bit 25); `pack_pixel` leaves mode 7's alpha uninverted.
Tests first (pbe.rs unit test, tests/closing_r34_q044.rs on the kept rows).
