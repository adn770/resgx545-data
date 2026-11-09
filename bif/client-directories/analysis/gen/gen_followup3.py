#!/usr/bin/env python3
"""Follow-up 3 (keep-pages), declared after keep-closed and the keep-partial runs and before its run. keep-closed: with render
flag bit 3 and the first context's memory kept the second context's render is exact (7 of 7) and the first context's TA data
pages 1 (control), 2 (OTPM) and 3 (state) hold, after it, words the DPM stored (page 1 word 0 0x00200047, page 2 word 0
0x04000417, page 3 words 0-1 0x00020001, 2 and the other 32 words 0, which replaced a ramp: 34 of 34 dwords, 3 of 3 jobs); a
ramp in page 3 did not break the render. H45-W: the slot step only writes these pages (it does not read them): with a ramp
(word i = 0xa5000000 + i) in page 1 or in page 2 instead of page 3, the second context's render is still exact and the
page then differs from the ramp. python3 gen/gen_followup3.py -> gen/table-keep-pages.txt, declared-followup3.tsv,
predictions-followup3.tsv"""
import pathlib
P = pathlib.Path(__file__).resolve().parent.parent
rows, decl, preds = [], [], []
for page in (1, 2):
    for i in (1, 2, 3):
        name = "k45f3-p%d-%d" % (page, i)
        rows.append("%s|heldout|1|0xc|%d" % (name, page))
        decl.append((name, "keep-pages", "heldout", "64x64"))
        preds.append((name, "second-render", "exact", "H45-W"))
        preds.append((name, "page-vs-ramp", "changed", "H45-W"))
        preds.append((name, "changed-dwords", "?", "H45-W"))
(P / "gen/table-keep-pages.txt").write_text("\n".join(rows) + "\n")
(P / "declared-followup3.tsv").write_text("case\tscript\tset\tsize\n" + "".join("\t".join(r) + "\n" for r in decl))
(P / "predictions-followup3.tsv").write_text("case\tquantity\tvalue\tmodel\n" + "".join("\t".join(r) + "\n" for r in preds))
print(len(rows), "jobs")
