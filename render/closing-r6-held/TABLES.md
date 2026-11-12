# r6-held part H tables (written by gen/hgen.py; do not edit)

Stage s0 (controls) then stage q (6 cells).  Each q cell: E848's job held, the fault read at 2.8 s and 1 s later,
[flush: `echo 1 > bif_flush` while held, the registers read], the debugfs reset, the follow-up, then triangles until one
draws (three at most), then the health pair.

| cell | size | follow-up | flush | job word | first triangle: H-LIST / H-WORD | H-FLUSH / H-PEND |
|---|---|---|---|---|---|---|
| a0-640-health | 640 x 480 | health | no | 0x2000a061 | fault at 0x2000a061 (both) | - |
| b0-640-flush-health | 640 x 480 | health | yes | 0x2000a061 | - | ok / fault at 0x2000a061 |
| a1-640-fill | 640 x 480 | fill | no | 0x2000a061 | fault at 0x2000a062 / 0x2000a061 | - |
| b1-640-flush-fill | 640 x 480 | fill | yes | 0x2000a061 | - | ok / fault at 0x2000a062 |
| a2-288-fill | 288 x 144 | fill | no | 0x20006061 | fault at 0x20006062 / 0x20006061 | - |
| b2-288-flush-health | 288 x 144 | health | yes | 0x20006061 | - | ok / fault at 0x20006061 |

Rows by model: predictions/q.tsv and predictions/s0.tsv (case, quantity, value, model, set, source).
