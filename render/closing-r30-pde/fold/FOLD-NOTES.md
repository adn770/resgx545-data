# r30-pde fold notes (2026-11-16, after the run)

- Run: the lead built t30 on the laptop (`bash lead/finish_freeze.sh`: sha256 b5ea288d...,
  lead/TOOL30.built) and froze (FROZEN.sha256 9050a555..., fold/lead-freeze.log), then staged and
  ran on module 7CE8E38EDB97FC5EA4F6C90 (fork r30-kernel 8bc0877e8603, installed = loaded, the
  runner's preflight): attempt out/20261116-131809, rc 0, every stage complete, no fault, no hang,
  no `SGX recovery failed`, no stop. The KUnit gate of the module: the fork's series check on the
  laptop, 222 of 222 cases with the debug option, 132 of 132 without (closing29/kernel/deliver).
- Scores reproduced byte for byte (fold/reproduce.out). Frozen: s0 8 of 8 controls and s0-warm
  held; f1, f2, f45 H-4K on every row (9, 6, 8); f67 H-ALIAS 4 of 4; every other model refuted
  (H-4K-PTOFF held where it ties H-4K on c1-o and c2-o, refuted on c4-o). The frozen q109 rule
  prints RETIRE: every code 1 to 5 reads as 4 KiB entries, clause 2 moot, codes 6 and 7 taken as
  a size (their reading is the 4 KiB one too).
- Was the size field written? fold/posthoc.py (fold/posthoc.txt): every row's vm_large `pde`
  line is the region's address | the offset | code << 1 | VALID, the code field the row's knob,
  the listed table the fork's for that region, and every tag read or page changed is one of that
  row's region. The read-out prints the word the driver computed and stored with one 32-bit
  WRITE_ONCE into the uncached directory page (sgx_mmu_pd_override), not a read-back of the
  directory; the BIF walked the table that same word names (codes 1-3 each in a region of its
  own), so it fetched the word with the size field in it [infer from the source and the tags].
  Codes 4-7 share the pooled 4 MiB region 0x2f800000: there the word's address does not tell
  them apart, and a directory word cached from an earlier job is excluded only by the reset and
  the BIF invalidate before every job [infer]. Not a kit or fork mistake as far as the kept
  files show.
- Records: E1117 (clause 1: s0, f1, f45 dense rows), E1118 (clause 2: the index and bits 11:4,
  f2 and f45's misalign and ptoff rows), E1119 (clause 3: f67). BIF_INT_STAT 0x80000 and
  BIF_FAULT 0 after every job: the idle value the kit's reset prints.
- Kit note (report only): an all-voided stage's empty cases.tsv reads as not kept (43, mock world
  enomem45); not hit in the run.
