#!/usr/bin/env python3
"""Follow-up 1 (bg-words-f1), declared after the first bg-words run (161 jobs, all 161 images the control's, every poke of
words 3-16 seen in the object, the pokes of words 0-2 lost) and before its run. The single-word pokes could be masked by a
second copy or a fallback, so whole object at once: words 3-16 all 0xffffffff, all 0, and word N = 0xa5000000 + N, two jobs
each, with two controls. H66-Z: the ISP reads none of the words 3-16 in a render with no texture layer (E209's coordinate
reading is the transfer copy's layers): image = control and every poked word reads back in the object (14 of 14 a job).
python3 gen/gen_followup1.py -> gen/table-bg-words-f1.txt, declared-followup1.tsv, predictions-followup1.tsv"""
import pathlib
P = pathlib.Path(__file__).resolve().parent.parent
rows, decl, preds = [], [], []
def pokes(f): return " ".join("--kpoke-render 1:bg:%d=0x%08x" % (w, f(w)) for w in range(3, 17))
cases = [("b66f1-control-1", "control", ""), ("b66f1-ones-1", "heldout", pokes(lambda w: 0xffffffff)),
         ("b66f1-zero-1", "heldout", pokes(lambda w: 0)), ("b66f1-pat-1", "heldout", pokes(lambda w: 0xa5000000 + w)),
         ("b66f1-ones-2", "heldout", pokes(lambda w: 0xffffffff)), ("b66f1-zero-2", "heldout", pokes(lambda w: 0)),
         ("b66f1-pat-2", "heldout", pokes(lambda w: 0xa5000000 + w)), ("b66f1-control-2", "control", "")]
for n, sset, a in cases:
    rows.append("%s|%s|64|64|tri --pixels --dump-render \"$W/dump\" %s" % (n, sset, a))
    decl.append((n, "bg-words-f1", sset, "64x64"))
    preds.append((n, "image-vs-control", "same", "H66-Z" if a else "control"))
    if a:
        preds.append((n, "poke-in-object", "yes", "poke path"))
(P / "gen/table-bg-words-f1.txt").write_text("\n".join(rows) + "\n")
(P / "declared-followup1.tsv").write_text("case\tscript\tset\tsize\n" + "".join("\t".join(r) + "\n" for r in decl))
(P / "predictions-followup1.tsv").write_text("case\tquantity\tvalue\tmodel\n" + "".join("\t".join(r) + "\n" for r in preds))
print(len(rows), "jobs")
