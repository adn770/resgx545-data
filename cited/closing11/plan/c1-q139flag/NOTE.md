# c1-q139flag: Q139 region header flag bit 7 on r7-rp's 21 q139 dumps

Verdict: H-LAST and H-FLAGSLOT hold on all 22 poked rows (21 scored + control m1-B1-5).
The rival H-HIGHEST parts from them on 17 of 21 poked rows in the "dump" and "model" forms, and
not at all in the "highest target-tile header" form. Frozen before any r7-rp dump was opened.

## Freeze
- Rule: `hflag_rule.json`, sha256 `291ef61dbabdfc46b13aea65c3b3989c3831af2a500b7dbc17ca48b9d9864d53`
  (`hflag_rule.sha256`); scorer `hflag_score.py` sha256 in `FREEZE.log` (13d60577...). Readers in
  `lib/` are byte copies of r10-geo's score/lib_dump.py, pbdump_dump.py, region_tiles_dump.py and
  gen/q139_fit.py, q139model.py, q139even.py.
- Read before the freeze: E907, E944 (size only), E959, E1007, r10-geo scorer code, the r10-geo
  q139c dumps (scorer test, already read by E1007), r7-rp cases.tsv and one r7-rp job text (rc and
  diff lines). No r7-rp `.tri.tadata.bin` or `.tri.param.bin` was opened before the freeze.
## Set
`resgx545-data/render/closing-r7-rp/out/20261112-205431/q139/` (E907's run, module srcversion
41E2...; r10-geo's was srcversion B60A...): 3 controls, 10 fit, 10 heldout, 1 replicate. rc 1 means
the diff line (expectdiff: image differs from the baseline); all 24 jobs say `job: ok`, whole
image, both dumps present, so all 24 are readable. The flag was never read there (E907 scored slots
and wrong tiles only). m2-B2-10 (fit) and part2-10_10_10 (heldout) were re-dumped by q139c:
replicate-class for E1007, new for the flag on this kernel build; m1-B2-8's r row is E907's own
replicate.
## Rules (frozen)
H-LAST: one bit-7 header; a target tile is drawn iff a stream header naming it lies at or before
it. H-FLAGSLOT: it sits at H-EVEN's slot of the last target tile in block order, and the implied
wrong-tile set is the image's. Rivals: H-HIGHEST (a) the highest nonzero header slot in the dump,
(b) the highest slot a predicted header takes, (c) the highest slot of a stream header naming a
target tile. Pass: strict, every decided row.
## Results [HW] (hflag_score.out)
| set | rows | one bit-7 hdr | H-LAST | H-FLAGSLOT | H-HIGHEST a / b / c |
|---|---|---|---|---|---|
| fit | 10 | 10 | 10 held | 10 held | 2 / 2 / 10 |
| heldout | 10 | 10 | 10 held | 10 held | 2 / 2 / 10 |
| replicate | 1 | 1 | 1 held | 1 held | 0 / 0 / 1 |
| m1-B1-5 (poked control) | 1 | 1 | 1 held | 1 held | 1 / 1 / 1 |
Unpoked baselines flag slot 127 (256 x 256) and 743 (640 x 480); m1-B1-5 127.
Tiles: H-LAST right on every tile (128 or 600 per row), no misses.
Flag slots seen: 43 to 127 (256 x 256), 343 to 743 (640 x 480); never at the highest slot written
except where nothing is written past it (strides 4, 8, 16, 24: 4 of 21 rows; m1-B1-5 too).
H-EVEN and R7-BLK slots: exact on 24 of 24 rows (all 128 or 600 tiles), including stride-4 (here
H-EVEN = blkrow; E907's original row-order R7-BLK failed it, the block order is E944's).
Where H-FLAGSLOT and H-HIGHEST part: the 17 rows with headers past the flag (dump highest 141 to
1183 against flag 95 to 743), e.g. m1-B1-28 flag 375 against highest 1183, m2-B1-20 flag 743
against 1119. This is the rows E1007 said did not part: its dumps' tail headers are non-target
tiles written past the target, which "highest slot written" (a) counts and (c) does not.
Form (c) never parts: the flagged header is also the highest target-tile stream header on all 24
rows. H-FLAGSLOT and (c) are not separated by these data [infer]: no row has the last tile in
block order below another target tile's slot.

## Refutation (rerun: python -I hflag_score.py DIR)
A readable dump with zero or two bit-7 headers, a drawn tile whose only header is past the flag,
an undrawn tile with a stream header at or before it, or a flag off H-EVEN's slot. None occurred.

## Records
E907, E944 (block order), E959 (post hoc flag), E1007 (q139c held out).
[infer] Nothing here needs a correction of E1007's claim; an appended note could say that
"the highest slot written" separates from the flag on 17 r7-rp rows when it counts non-target
headers written past the target, and only the form restricted to target tiles is not parted.
Not done: a dump where the last block-order tile is not the highest target slot.
Publishable: yes (published kept dumps, r10-geo code, no firmware content).
