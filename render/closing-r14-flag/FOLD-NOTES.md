# r14-flag fold notes (builder, before the run)

- Records: E1047 (f1, Q078), E1048 (f2, Q139); E1049 unused (no F3). Draft each method with
  `tools/records/new_record.py --session DIR`; appended corrections only.
- f1: if the bit-14 rows draw, every pixel names its dword: decode the full map (READING lines,
  then a look.py over predictions/f1 and the kept images) whatever form holds. If one frozen form
  gives all three images, Q078's twiddled clause can retire (R14-6: the lead confirms); f1's
  images then become a `tex` table for sgx-sim's texture address. If a form holds on f1-small and
  f1-zero but not f1-tw32, the u past 1 (wrap or clamp of the 4096 term) is the open part. If the
  rows fault inside the 1 MiB scratch (fwhere "inside the scratch"), the mapping premise failed
  (t14's heap): report, do not read it as bit 14. E1033 takes a note (its pages read).
- f2: H-COVER vs H-FAULT23 on every row; H-EVEN vs R7-BLK on the rows that drew; H-LASTBLOCK vs
  H-HIGHSLOT on the 768 x 640 rows. Q139's line: H-EVEN held out (if it holds) narrows the first
  clause to "why"; the flag clause answered or narrowed; the stride's relation and E509's faults
  stay. If H-EVEN holds, a `ta` table for sgx-pipe's `ta::macrotile_slots` (poked words).
- Plan premise to correct in the fold's text: E950's residue dumps came from jobs that drew, not
  faulted (rank-round14.md "Checks done"); t10's tri dumps nothing after a failed render.
- Kit needs (report, do not change shared tools): none found. Tool note: a TA dump after a failed
  tri render would need the kernel to keep the TA data across recovery (dump_render's comment).
