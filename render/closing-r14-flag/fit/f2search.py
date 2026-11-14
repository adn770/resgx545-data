# SPDX-License-Identifier: MIT
"""f2search.py: the builder's search (before the freeze) for f2's words: CR_TE_MTILE1 with the
first macrotile fx tiles wide, fx 2 or 3 mod 4, at four target sizes; per word: H-EVEN's and
R7-BLK's wrong-tile counts and how many target slots differ, the flag's slot under H-LASTBLOCK
(LB) and H-HIGHSLOT (HS) and the image's wrong tiles under each, and whether those part. The
readers are gen/'s byte copies of r10-geo's. f2search.out is its output, filtered to fx at or past
the target's width in tiles (H-COVER's kind). Standard library only: `python3 fit/f2search.py`."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gen"))
sys.dont_write_bytecode = True
import q139_fit as F, q139model as Q, q139even as E
def info(w, h, args):
    tx, ty = F.cdiv(w, 32), F.cdiv(h, 16)
    pe = E.predict(w, h, args, "H-EVEN"); pr = E.predict(w, h, args, "blkrow")
    key = Q.KEYS["blkrow"]; n = E.geometry(w, h, args)[0]
    surv = [t for t, v in pe.items() if v is not None]
    if not surv: return None
    last = max(surv, key=lambda t: key(t[1], t[0], 0, 0, n))
    lb = pe[last]; hs = max(pe[t] for t in surv)
    wl = {t for t, v in pe.items() if v is None or v > lb}
    wh = {t for t, v in pe.items() if v is None or v > hs}
    return dict(tx=tx, ty=ty, geo=E.geometry(w, h, args), even_wrong=len(Q.wrong(pe)), blk_wrong=len(Q.wrong(pr)),
                slots_differ=sum(1 for t in pe if pe[t] != pr[t]), lastblock=lb, highslot=hs,
                wrong_lb=len(wl), wrong_hs=len(wh), wrong_sets_differ=wl != wh)
SIZES = [(640, 480), (768, 640), (1024, 768), (1280, 720)]
for w, h in SIZES:
    tx, ty, n, mx, my, m1, m2, s = F.rule(w, h)
    for fx in range(2, 64):
        if fx % 4 not in (2, 3): continue
        if n == 2:
            m1p = (m1 & ~(0xff << 12)) | fx << 12
        else:
            m1p = (m1 & ~(0xff << 22)) | fx << 22
        args = "--kpoke-render 1:ta:143=0x%08x" % m1p
        r = info(w, h, args)
        if r is None: continue
        cover = fx >= tx if n == 2 else False
        print(f"{w}x{h} n{n} rule m1=0x{m1:08x} s={s} fx={fx:2} m1p=0x{m1p:08x} cover={cover} geo={r['geo']} "
              f"wrong EVEN {r['even_wrong']} BLK {r['blk_wrong']} slotsdiff {r['slots_differ']} "
              f"flag LB {r['lastblock']} HS {r['highslot']} wrongLB {r['wrong_lb']} wrongHS {r['wrong_hs']} part={r['wrong_sets_differ']}")
