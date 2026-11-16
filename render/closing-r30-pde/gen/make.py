#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r30-pde's tables (tables/STAGE.txt), frozen predictions (predictions/STAGE.tsv)
and the fill rows' allowed changed pages (gen/allowed.tsv, read by run/hooks.sh on the laptop),
from gen/pde.py's port of the linux fork's large-page functions (branch r30-kernel 8bc0877e8603).
`python3 gen/make.py` writes them; `--check` exits 1 when a written file differs.

Every row aims one copy (--src-addr) or one fill (--dst-addr) at the 4 MiB slot SLOT, which
debugfs vm_pde_addr names in the rows that set it (dbg: words), 64 pixels wide at the tool's
default stride of 256 bytes (16 rows a 4 KiB page), each row's VA window inside the fork's KUnit
safety case (pde.inside; tests/test_gen.py holds every row to it). Standard library only."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pde as P  # noqa: E402

SLOT = 0x60000000                  # vm_pde_addr: a 4 MiB slot of the general heap, >= 0x60000000
ROW_BYTES = 256                    # the tool's default stride (copy --src-stride, fill --stride)
ROWS_PAGE = P.SZ_4K // ROW_BYTES   # 16 rows a page
STAGES = ("s0", "f1", "f2", "f45", "f67")
LIMIT = {"s0": 0, "f1": 6, "f2": 4, "f45": 6, "f67": 4}
SRC = "closing29/kernel/plan-kernel.md 2.3; fork r30-kernel 8bc0877e8603 sgx_mmu_large.c (gen/pde.py)"


def knobs(code, layout):
    return f"dbg:vm_pde_addr={SLOT:#x} dbg:vm_pde_size={code} dbg:vm_pde_layout={layout}"


def job(kind, va0, va1):
    """(args, the VA window [va0, va1) the job touches, as offsets from SLOT)."""
    h = (va1 - va0) // ROW_BYTES
    if kind == "copy":
        return f'copy --src-addr {SLOT + va0:#x} --height {h} --large-copy "$W"'
    return f'fill --dst-addr {SLOT + va0:#x} --height {h} --large-copy "$W"'


def toks(lst):
    return ",".join(lst) if lst else "none"


def changed(lst):
    """A fill's changed pages: the distinct tokens, sorted (the read-out lists each page once)."""
    s = sorted(set(lst), key=lambda t: tuple(int(x) for x in t.split(":")) if ":" in t else (99, 0))
    return toks(s)


# ---- the rows -------------------------------------------------------------------------------
def s0_rows():
    """The safe references: the knobs off (a plain buffer at SLOT, exact) and vm_pde_size 0
    (4 KiB entries over the tagged region: the tags read as the 4 KiB reading predicts), a copy at
    the slot's start and a fill across its end into the next, 4 KiB-mapped slot; twice. First,
    the warm row: vm_pde_size 5 maps the slot over a 4 MiB region (order 10) right after the
    boot, while the copy reads only the page before the slot; the region goes to the module's
    pool for every later order-10 row."""
    g0, g5 = P.geom(0, 0), P.geom(5, 0)
    rows = [dict(name="s0-warm", set="fit", knobs="soft " + knobs(5, 0), kind="copy",
                 va=(-P.SZ_4K, 0), g=g5,
                 pred={"H-WARM": dict(end="ok", job="ok", diff="0", large="c5.l0.o10",
                                      table="intact", changed="none")})]
    for k in (1, 2):
        rows += [
            dict(name=f"s0-pcopy-{k}", set="control", knobs="reads:job,diff,large", kind="copy",
                 va=(0, P.SZ_16K), g=None,
                 pred={"H-REF": dict(end="ok", job="ok", diff="0", large="none")}),
            dict(name=f"s0-kcopy-{k}", set="control",
                 knobs="expectdiff reads:job,diff,large,tags,table,changed " + knobs(0, 0),
                 kind="copy", va=(0, P.SZ_16K), g=g0,
                 pred={"H-REF": dict(end="ok", job="ok", diff="4096", large="c0.l0.o3",
                                     tags=toks(P.pages(g0, P.RD_4K, 0, P.SZ_16K)), table="intact",
                                     changed="none")}),
            dict(name=f"s0-pfill-{k}", set="control", knobs="reads:job,diff,large", kind="fill",
                 va=(P.SZ_4M - P.SZ_8K, P.SZ_4M + P.SZ_8K), g=None,
                 pred={"H-REF": dict(end="ok", job="ok", diff="0", large="none")}),
            dict(name=f"s0-kfill-{k}", set="control",
                 knobs="expectdiff reads:job,diff,large,table,changed " + knobs(0, 0), kind="fill",
                 va=(P.SZ_4M - P.SZ_8K, P.SZ_4M + P.SZ_8K), g=g0,
                 pred={"H-REF": dict(end="ok", job="ok", diff="2048", large="c0.l0.o3",
                                     table="intact",
                                     changed=changed(P.pages(g0, P.RD_4K, P.SZ_4M - P.SZ_8K,
                                                             P.SZ_4M)))}),
        ]
    return rows


def quant(kind, lst):
    return dict(tags=toks(lst)) if kind == "copy" else dict(changed=changed(lst))


def models(g, kind, va0, va1):
    """{model: frozen quantities} of a flagged row of a named code 1-5 (layout as g's)."""
    rd = lambda r: dict(end="ok", **quant(kind, P.pages(g, r, va0, va1)))  # noqa: E731
    out = {"H-FAULT": dict(end="fault")}
    if g["layout"] == P.DENSE:
        out.update({"H-DENSE": rd(P.RD_DENSE), "H-4K": rd(P.RD_4K), "H-SECTION": rd(P.RD_SECTION)})
    elif g["layout"] == P.MISALIGN:
        out.update({"H-MASK-S": rd(P.RD_DENSE), "H-MASK4K": rd(P.RD_MASK4K), "H-4K": rd(P.RD_4K),
                    "H-SECTION": rd(P.RD_SECTION)})
    else:
        out.update({"H-PTOFF-IGN": rd(P.RD_DENSE), "H-PTOFF-USE": rd(P.RD_DENSE | P.RD_PTOFF),
                    "H-4K": rd(P.RD_4K), "H-4K-PTOFF": rd(P.RD_4K | P.RD_PTOFF),
                    "H-SECTION": rd(P.RD_SECTION)})
    return out


def dense_rows(code, soft=""):
    """Copy a over large page 0's end into page 1 (fit), copy b over page 1's end into page 2
    (held out), the fill over page 0's end (held out); code 5: [4M - 16K, 4M - 8K), [4M - 8K,
    4M) and the fill over both."""
    g, s = P.geom(code, P.DENSE), P.page_size(code)
    if code == 5:
        spans = (("a", "fit", "copy", P.SZ_4M - P.SZ_16K, P.SZ_4M - P.SZ_8K),
                 ("b", "heldout", "copy", P.SZ_4M - P.SZ_8K, P.SZ_4M),
                 ("f", "heldout", "fill", P.SZ_4M - P.SZ_16K, P.SZ_4M))
    else:
        spans = (("a", "fit", "copy", s - P.SZ_8K, s + P.SZ_8K),
                 ("b", "heldout", "copy", 2 * s - P.SZ_8K, 2 * s + P.SZ_8K),
                 ("f", "heldout", "fill", s - P.SZ_8K, s + P.SZ_8K))
    return [dict(name=f"c{code}-{t}", set=st, knobs=f"{soft}expectfault expectdiff " +
                 knobs(code, P.DENSE), kind=kind, va=(a, b), g=g, pred=models(g, kind, a, b))
            for t, st, kind, a, b in spans]


def layout_rows(code, soft=""):
    """The misalign copy and the ptoff copy over large page 0's end into page 1 (held out)."""
    s = P.page_size(code)
    out = []
    for t, lay in (("m", P.MISALIGN), ("o", P.PTOFF_L)):
        g = P.geom(code, lay)
        out.append(dict(name=f"c{code}-{t}", set="heldout",
                        knobs=f"{soft}expectfault expectdiff " + knobs(code, lay), kind="copy",
                        va=(s - P.SZ_8K, s + P.SZ_8K), g=g,
                        pred=models(g, "copy", s - P.SZ_8K, s + P.SZ_8K)))
    return out


def unnamed_rows():
    """Codes 6 and 7: one copy each over [16K, 32K), then each again. H-FAULT the frozen one;
    H-ALIAS (the entry taken as any size but 16 KiB, or as 4 KiB entries: region pages 4-7) and
    H-ALIAS16 (as 16 KiB: pages 0-3, the table page first) the rivals."""
    out = []
    for rep in (1, 2):
        for code in (6, 7):
            g = P.geom(code, P.DENSE)
            out.append(dict(
                name=f"c{code}-u{rep}", set="fit" if rep == 1 else "heldout",
                knobs="soft expectfault expectdiff " + knobs(code, P.DENSE), kind="copy",
                va=(P.SZ_16K, P.SZ_32K), g=g,
                pred={"H-FAULT": dict(end="fault"),
                      "H-ALIAS": dict(end="ok", tags=toks(P.pages(g, P.RD_4K, P.SZ_16K, P.SZ_32K))),
                      "H-ALIAS16": dict(end="ok", tags=toks(P.pages(g, P.RD_DENSE, P.SZ_16K,
                                                                     P.SZ_32K, P.SZ_16K)))}))
    return out


def rows():
    """{stage: [row]} in run order. Order-10 rows (codes 4-7: a 4 MiB region) are `soft`: an
    -ENOMEM refusal at the map voids the row, a second in a row stops the stage."""
    return {
        "s0": s0_rows(),
        "f1": [r for c in (1, 2, 3) for r in dense_rows(c)],
        "f2": [r for c in (1, 2, 3) for r in layout_rows(c)],
        "f45": dense_rows(4, "soft ") + dense_rows(5, "soft ") + layout_rows(4, "soft "),
        "f67": unnamed_rows(),
    }


HEAD = {
    "s0": "s0: safe references (Q109, r30-pde). The warm row maps the slot with vm_pde_size 5 "
          "(a 4 MiB region, order 10, right after the boot) while its copy reads the page before "
          "the slot only. The controls: the knobs off (a plain buffer at the slot: exact, vm_large "
          "none) and vm_pde_size 0 (4 KiB entries over the tagged region: the copy's tags and the "
          "fill's changed page are H-4K's, the table intact), each twice. They gate every flagged "
          "stage. Safe class: no expectfault, #limit 0; any fault or hang stops the session.",
    "f1": "f1 (FLAGGED, planned faults): codes 1-3 (16K, 64K, 256K), dense table: copy a over "
          "large page 0's end into page 1 (fit), copy b over page 1's end into page 2 (held out), "
          "the fill over page 0's end (held out). Frozen H-DENSE (index va / S, entry masked to S) "
          "against H-4K (the size field ignored), H-SECTION (no table) and H-FAULT. #limit 6 of 9 "
          "rows; hook_fault ends the session on a hang, a fault without its BIF line or a failed "
          "recovery; hook_check on a changed page outside the readings or a changed table.",
    "f2": "f2 (FLAGGED, planned faults): codes 1-3, the table's address bits: the misalign copy "
          "(entry k = block k + 4 KiB: H-MASK-S, the entry masked to S, against H-MASK4K) and the "
          "ptoff copy (the table at + 0x400 named by the PDE's bits 11:4, a rotated decoy at + 0: "
          "H-PTOFF-IGN against H-PTOFF-USE), over page 0's end into page 1, held out. #limit 4 of 6.",
    "f45": "f45 (FLAGGED, planned faults): the 4 MiB regions (order 10): code 4 (1M) as f1 and f2, "
           "code 5 (4M) dense: copy a [4M - 16K, 4M - 8K) fit, copy b [4M - 8K, 4M) and the fill "
           "[4M - 16K, 4M) held out. Rows soft (an -ENOMEM voids one; two in a row stop). Gated "
           "also on s0-warm's 4 MiB region. #limit 6 of 8.",
    "f67": "f67 (FLAGGED, planned faults, last): the unnamed codes 6 and 7, copies only over "
           "[16K, 32K), each twice. Frozen H-FAULT (the BIF does not take the code: a fault, or a "
           "hang the kernel recovers, with the kernel's BIF line and registers) against H-ALIAS "
           "and H-ALIAS16 (taken as a size). Soft (order 10). #limit 4 of 4.",
}


def table_text(st, rs):
    lines = [f"#stage {st}", f"#limit {LIMIT[st]}", "# " + HEAD[st]]
    for r in rs:
        risk = "safe" if st == "s0" else "risky"
        lines.append(f"{r['name']}|{r['set']}|{risk}|{r['knobs']}|t30|{job(r['kind'], *r['va'])}")
    return "\n".join(lines) + "\n"


def pred_text(rs):
    out = ["case\tquantity\tvalue\tmodel\tset\tsource"]
    for r in rs:
        for m, qs in r["pred"].items():
            for q, v in qs.items():
                out.append(f"{r['name']}\t{q}\t{v}\t{m}\t{r['set']}\t{SRC}")
    return "\n".join(out) + "\n"


def allowed_text(all_rows):
    """name, then the region pages a fill row may change (pde.union over its slot window)."""
    out = ["# gen/allowed.tsv (gen/make.py): a fill row's allowed changed pages, S:P, comma "
           "separated (pde.union: every reading of the fork's safety case over the row's window)"]
    for st in STAGES:
        for r in all_rows[st]:
            if r["kind"] != "fill" or r["g"] is None:
                continue
            a, b = max(r["va"][0], 0), min(r["va"][1], P.SZ_4M)
            u = sorted(P.union(r["g"], a, b) - {"x"},
                       key=lambda t: tuple(int(x) for x in t.split(":")))
            out.append(f"{r['name']}\t{','.join(u)}")
    return "\n".join(out) + "\n"


def files():
    rs = rows()
    out = {}
    for st in STAGES:
        out[f"tables/{st}.txt"] = table_text(st, rs[st])
        out[f"predictions/{st}.tsv"] = pred_text(rs[st])
    out["gen/allowed.tsv"] = allowed_text(rs)
    return out


def main(argv):
    check = "--check" in argv
    bad = 0
    for rel, text in files().items():
        p = os.path.join(KP, rel)
        if check:
            cur = open(p).read() if os.path.exists(p) else None
            if cur != text:
                print(f"{rel}: not what gen/make.py writes")
                bad = 1
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
