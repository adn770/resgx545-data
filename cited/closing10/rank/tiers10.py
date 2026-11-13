#!/usr/bin/env python3
"""Round 10 tiers: every open question (index.txt: main 58c4763 with r9-fold-k1 cf0a9dd staged, 158
open) placed once. The seeds are the other planner's (closing10/seeds); the rest is this ranking's."""
import pathlib
open_ids = [l.split("|")[0] for l in (pathlib.Path(__file__).parent / "index.txt").read_text().splitlines()]
T = {
 "SEEDS (closing10/seeds plans them)": "Q284 Q177 Q078 Q282 Q120 Q121 Q199 Q261 Q101 Q139 Q210 Q211 Q108 Q076 Q066 Q260",
 "O10 (offline now: records or notes in this round's package)": "Q030 Q242 Q019 Q202 Q205 Q046",
 "R10 (picked: session r10-x on B60AB0B4, t4)": "Q241 Q243 Q071",
 "R10c (conditional: design check or the coming t10 tool)": "Q288",
 "K10 (kernel-enabled or reload; not this round)": "Q109 Q068 Q064 Q193",
 "F10 (text: keep apart / merge)": "Q146 Q194",
 "O (offline narrowing, later)": "Q280 Q296 Q100 Q053 Q200 Q163 Q075 Q012 Q008 Q125 Q107 Q070 Q074 Q290 Q179 Q082 Q089 Q142 Q262 Q240",
 "H (safe hardware rows, later)": "Q001 Q010 Q011 Q013 Q016 Q017 Q020 Q023 Q024 Q026 Q027 Q032 Q039 Q040 Q042 Q043 Q044 Q050 Q051 Q052 Q054 Q055 Q057 Q058 Q060 Q062 Q065 Q069 Q073 Q080 Q092 Q098 Q104 Q112 Q114 Q115 Q116 Q123 Q126 Q127 Q129 Q130 Q132 Q133 Q134 Q135 Q136 Q137 Q143 Q158 Q159 Q160 Q161 Q162 Q164 Q181 Q183 Q195 Q196 Q201 Q206 Q207 Q230 Q231 Q276 Q111 Q086",
 "X (hangs, faults, held resets, new tooling)": "Q002 Q003 Q014 Q025 Q031 Q033 Q036 Q038 Q045 Q047 Q059 Q072 Q081 Q093 Q096 Q110 Q128 Q165 Q180 Q191 Q192 Q272 Q275 Q294",
 "Ph (hw, parked by the laptop rules or other hardware)": "Q048 Q063 Q099 Q154 Q168",
 "P (parked fw/kernel, the digest's 10)": "Q004 Q029 Q034 Q049 Q084 Q088 Q095 Q118 Q119 Q277",
}
placed = [q for v in T.values() for q in v.split()]
dup = sorted({q for q in placed if placed.count(q) > 1})
print("open", len(open_ids), "placed", len(placed), "missing", sorted(set(open_ids) - set(placed)),
      "extra", sorted(set(placed) - set(open_ids)), "dup", dup)
for k, v in T.items():
    print(f"{k}: {len(v.split())}: {v}")
