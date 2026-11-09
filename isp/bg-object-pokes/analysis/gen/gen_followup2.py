#!/usr/bin/env python3
"""Follow-up 2 (keep-partial), declared after the keep-closed run and before its run. keep-closed showed (64x64 contexts,
15 jobs): with render flag bit 3 and the first context's memory kept the second context's render is exact (7 of 7) and the
first's control page (page 1), OTPM page (page 2) and state page (page 3, 34 dwords) are written (store) after the second's
render, none of them with bit 2 alone or no flag. H45-P: the same store happens for a context that rendered partially (its
state page, page 6 of the TA data of a 1024x768 context, holds the lists of its partial renders, E464), and it replaces them:
after the second context's render the kept pages 4-6 of a flag-0xc first context differ from those of the same first context
rendered alone and closed with keep (kp-solo-c), those of a flag-0x4 first do not (kp-solo-4 against kp-ctx2-4).
python3 gen/gen_followup2.py -> gen/table-keep-partial.txt, declared-followup2.tsv, predictions-followup2.tsv"""
import pathlib
P = pathlib.Path(__file__).resolve().parent.parent
rows, decl, preds = [], [], []
K = [("kp-solo-4", "heldout", 0, "0x4", 2), ("kp-solo-c", "heldout", 0, "0xc", 2),
     ("kp-ctx2-4", "heldout", 1, "0x4", 2), ("kp-ctx2-c", "heldout", 1, "0xc", 2)]
for tag, sset, ctx2, flag, n in K:
    for i in range(1, n + 1):
        name = "%s-%d" % (tag, i)
        rows.append("%s|%s|1|%s|%d" % (name, sset, flag, ctx2))
        decl.append((name, "keep-partial", sset, "1024x768"))
        preds.append((name, "kept-readable", "yes", "render_kept"))
        if ctx2 and flag == "0xc":
            preds.append((name, "pages4-6-vs-solo", "changed", "H45-P"))
        elif ctx2:
            preds.append((name, "pages4-6-vs-solo", "equal", "H45-P"))
        if ctx2:
            preds.append((name, "second-render", "completes", "H45-K"))
(P / "gen/table-keep-partial.txt").write_text("\n".join(rows) + "\n")
(P / "declared-followup2.tsv").write_text("case\tscript\tset\tsize\n" + "".join("\t".join(r) + "\n" for r in decl))
(P / "predictions-followup2.tsv").write_text("case\tquantity\tvalue\tmodel\n" + "".join("\t".join(r) + "\n" for r in preds))
print(len(rows), "jobs")
