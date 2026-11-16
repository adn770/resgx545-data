# SPDX-License-Identifier: MIT
"""fold/posthoc.py: the fold's post-hoc readings of attempt 20261116-232915 (not frozen): the
bit-25 action per mode (p1, pw), the dwords mode 22's and 34's bit-25 rows differ in on the
dwords their two references repeat, and the pixels at the equal alpha of each mode-4 row (p2).

  python3 fold/posthoc.py [ATTEMPT_DIR]"""
import collections
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path[:0] = [os.path.join(KP, "score"), os.path.join(KP, "kit"), os.path.join(KP, "gen")]
import kitscore as K  # noqa: E402
import q044 as Q  # noqa: E402
import score as SC  # noqa: E402

att = sys.argv[1] if len(sys.argv) > 1 else os.path.join(KP, "out", "20261116-232915")


def img(stage, name):
    return SC.pixels(K.text(os.path.join(att, stage), name + ".txt"))


acts, none_ = {}, []
for stage, modes in (("p1", Q.P1_MODES), ("pw", Q.PAST)):
    for m in modes:
        r, b = img(stage, f"{stage}-m{m:02d}-ref"), img(stage, f"{stage}-m{m:02d}-b25")
        r2 = img(stage, f"{stage}-m{m:02d}-ref2") if m in Q.REPEAT2 else None
        x, n = SC.xor_of(r, b, r2)
        if m in Q.Q012:
            st = [i for i in range(4096) if r[i] == r2[i]]
            diff = [(i, r[i], b[i]) for i in st if r[i] != b[i]]
            c = collections.Counter(r[i] ^ b[i] for i in st)
            print(f"mode {m}: {len(st)} dwords repeat across the two references; bit 25 row "
                  f"differs in {len(diff)}: " + ", ".join(f"[{i}] {a:#010x} -> {v:#010x}"
                                                          for i, a, v in diff[:6])
                  + f"; xor counts {dict(c.most_common(3))}")
            continue
        if x == "0x00000000":
            none_.append(m)
        else:
            acts[m] = x
print("bit 25 changes the stored image in: " + ", ".join(f"{m} ({x})" for m, x in sorted(acts.items())))
print("bit 25 changes nothing in: " + ", ".join(str(m) for m in none_))
with open(os.path.join(KP, "predictions", "p2", "alpha.txt")) as f:
    al = [None if t == "-" else int(t, 16) for t in f.read().split()]
cnt = collections.Counter(a for a in al if a is not None)
for low in Q.EQ:
    got = SC.thr_of(al, img("p2", f"p2-m04-e{low:02x}"))
    print(f"mode 4 low byte {low:#04x}: thr {got}; {cnt[low]} triangle pixels at alpha {low}, "
          f"stored set (H-GE)")
