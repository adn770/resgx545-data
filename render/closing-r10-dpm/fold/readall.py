#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/readall.py (r10-dpm fold, POST HOC, written after the frozen score was read): every row's
S_2..S_7, need and the replay beside it, with the spread per target and S_6 minus the replay at
every target of E962, E936 and this session.
  python3 fold/readall.py out/20261113-102513"""
import os, sys
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(KP, "score"), os.path.join(KP, "kit"), os.path.join(KP, "gen")]
import score as SC, plan as PL, kitscore as K  # noqa: E401,E402
h = lambda v: "-" if v is None else f"0x{v:x}"  # noqa: E731
att = sys.argv[1]
d = os.path.join(att, "s6rep")
rds = SC.readings("s6rep", d)
for r in K.table(KP, "s6rep"):
    rd = rds[r["name"]]
    w, hh = PL.target(r)
    S, A, U, _ = PL.model(w, hh)
    if rd is None:
        print(f"{r['name']:16s} unread"); continue
    cols = " ".join(f"s{k}={h(rd['S'].get(k))}" + ("" if rd['S'].get(k) == v else f"({rd['S'].get(k, 0) - v:+d})") for k, v in sorted(S.items()))
    print(f"{r['name']:16s} {w}x{hh} need {h(rd['need'])}/{h(U)} nparts {rd['nparts']} mono {int(rd['mono'])} | {cols} | steps {sorted(rd['S'])}")
