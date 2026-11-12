# r7-faults tables (written by gen/fgen.py; do not edit)

Order: s0, l, d, m (one driver call; `run/f.sh`).  Rows by model: predictions/*.tsv (case, quantity, value, model, set,
source).

## l: `lock #0` twice (E088's counter probe; count = quads that added)

| row | program | set | H-SELF | H-REFLAG | H-RECOUNT |
|---|---|---|---|---|---|
| l0-lock-release | lock #0, add, release #0 | control | ok 512 | ok 512 | ok 512 |
| l1-lock0-lock1 | lock #0, lock #1, add, release #1, release #0 | control | ok 512 | ok 512 | ok 512 |
| l2-lock-lock-rel-rel | lock #0, lock #0, add, release #0, release #0 | heldout | hang 0 | ok 512 | ok 512 |
| l3-lock-lock-rel | lock #0, lock #0, add, release #0 | heldout | hang 0 | ok 512 | hang 1 |
| l4-lock-norel | lock #0, add | replicate | hang 1 | hang 1 | hang 1 |

## d: the fault-page dose (E848's held job, one array; the boot after the held reset)

| cell | size | fault page (layout) | set | H-PAGE (E901 R-PAGE) | H-SIZE (E892 literal) |
|---|---|---|---|---|---|
| d0-640x480 | 640 x 480 | 0x2000a | control | up | up |
| d1-288x144 | 288 x 144 | 0x20006 | control | timeout | timeout |
| d2-320x400 | 320 x 400 | 0x20008 | heldout | timeout | up |
| d3-256x288 | 256 x 288 | 0x20006 | heldout | timeout | up |
| d4-128x528 | 128 x 528 | 0x20009 | heldout | up | up |
| d5-384x384 | 384 x 384 | 0x20008 | heldout | timeout | up |
| d6-320x400 | 320 x 400 | 0x20008 | heldout | timeout | up |

## m: manipulations at 288 x 144 (page 0x20006)

| cell | before the reset | set | prediction |
|---|---|---|---|
| m0a-none | nothing | control | timeout (control) |
| m1a-clr | kregnow 0x0c00^=0x10 twice (CLEAR_FAULT set, cleared) | heldout | H-CLR up / H-NULL timeout |
| m2a-long | a 9 s hold | heldout | H-TIME up / H-NULL timeout |
| m2b-long | a 9 s hold | heldout | H-TIME up / H-NULL timeout |
| m1b-clr | kregnow 0x0c00^=0x10 twice (CLEAR_FAULT set, cleared) | heldout | H-CLR up / H-NULL timeout |
| m0b-none | nothing | control | timeout (control) |
