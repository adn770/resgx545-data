#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/posthoc.py: the fold's post-hoc readings of r30-pde (not frozen). Standard library.

  python3 fold/posthoc.py out/ATT > fold/posthoc.txt

1. The size field was in the directory word the BIF walked: for every row with vm_pde_addr set,
   vm_large's `pde` line must be the region's address | the table offset | code << 1 | VALID (the
   word sgx_mmu_pd_override stores, one WRITE_ONCE into the uncached directory page, fork
   8bc0877e8603 sgx_mmu.c), its listed table entries the fork's table for that region (gen/pde.py),
   and every tag the copy read (or page the fill changed) a page of that row's own region (the
   tags carry no address, so: the read-out's region, its pages named by slab and page). A region
   differs between codes 1-3 and the order-10 one; a stale directory word would walk another
   table. vm_large prints the word the driver computed, not a read-back of the directory page.
2. Every row's reading under the 4 KiB reading of that region (gen/pde.py), held or not.
3. CR_BIF_INT_STAT and CR_BIF_FAULT after every job (snap9), and the job times."""
import gzip
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import make as M  # noqa: E402
import pde as P  # noqa: E402
import score as S  # noqa: E402


def text(p):
    for q in (p + ".gz", p):
        if os.path.exists(q):
            return (gzip.open(q) if q.endswith(".gz") else open(q, "rb")).read().decode()
    return None


def pt_lines(g, region):
    """vm_large's `pt` lines as the fork prints them (runs of consecutive pages folded, the trap
    left out)."""
    pt, trap = P.table(g, region), P.pte(region + g["trap_off"])
    out, i = [], 0
    while i < len(pt):
        e, j = pt[i], i + 1
        while j < len(pt) and pt[j] == e + (j - i) * P.SZ_4K and e != trap:
            j += 1
        if e != trap:
            out.append(f"pt {i} {e:#010x}" if j - i == 1 else f"pt {i}-{j - 1} {e:#010x} step 0x1000")
        i = j
    return out


def main(att):
    rows = M.rows()
    bad = 0
    print("# r30-pde post hoc (fold/posthoc.py), attempt", os.path.basename(att.rstrip("/")))
    for st in M.STAGES:
        cases = S.K.rows(os.path.join(att, st), "cases.tsv")
        for r in rows[st]:
            n = r["name"]
            d = os.path.join(att, st)
            c = cases.get(n)
            rd = S.reading(cases, d, n)
            jt = re.search(r"^job time: (\d+) us", text(os.path.join(d, n + ".txt")) or "", re.M)
            line = f"{st} {n}: class {c['class'] if c else 'not run'} bif {rd.get('bif')} " \
                   f"job {jt.group(1) + ' us' if jt else '-'}"
            if r["g"] is None:
                print(line + f" large {rd.get('large')}")
                continue
            lg = text(os.path.join(d, n + ".vm_large.txt")) or ""
            m = re.search(r"^region (0x[0-9a-f]+) ", lg, re.M)
            pw = re.search(r"^pde (0x[0-9a-f]+)$", lg, re.M)
            if not (m and pw):
                print(line + " NO READ-OUT")
                bad += 1
                continue
            region, word = int(m.group(1), 16), int(pw.group(1), 16)
            g = r["g"]
            want = P.pde(g, region)
            ok_word = word == want and (word >> 1) & 7 == g["code"]
            got_pt = [ln for ln in lg.splitlines() if ln.startswith("pt ")]
            ok_pt = got_pt == pt_lines(g, region)
            a, b = max(r["va"][0], 0), min(r["va"][1], P.SZ_4M)
            if a < b:
                pred = P.pages(g, P.RD_4K, a, b)
                got = rd.get("tags") if r["kind"] == "copy" else rd.get("changed")
                exp = ",".join(pred) if r["kind"] == "copy" else M.changed(pred)
                rdg = f" reading {got} 4K-reading {exp} {'=' if got == exp else 'DIFFERS'}"
            else:
                rdg = " (the slot not touched)"
            print(line + f" region {region:#010x} pde {word:#010x} (code field {(word >> 1) & 7}, "
                  f"bits 11:4 {word >> 4 & 0xff:#x}) word {'ok' if ok_word else 'WRONG'}, table "
                  f"{'as built' if ok_pt else 'DIFFERS'}" + rdg)
            bad += not (ok_word and ok_pt)
    print(f"# rows whose directory word or table is not the fork's: {bad}")


if __name__ == "__main__":
    main(sys.argv[1])
