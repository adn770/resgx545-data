# SPDX-License-Identifier: MIT
"""gen/pde.py: the large-page directory entry of the linux fork's debugfs vm_pde_* (branch
r30-kernel 8bc0877e8603, drivers/gpu/drm/gma500/sgxfive/sgx_mmu_large.c and sgx_mmu.h), in
Python: the region's geometry, its table, the readings a session tells apart and the tags.
A line-by-line port of the fork's pure functions (sgx_mmu_large_geom, sgx_mmu_large_table,
sgx_mmu_large_phys, sgx_mmu_large_tag) with the region at physical 0, so an address is an offset
in the region (every region is naturally aligned, so the masks act on offsets as on addresses).
tests/test_gen.py holds it to the fork's KUnit values (sgx_mmu_large_test.c). Standard library."""

SZ_4K, SZ_8K, SZ_16K, SZ_32K, SZ_4M = 0x1000, 0x2000, 0x4000, 0x8000, 0x400000
CODES, NAMED = 8, 6
DENSE, PT4K, MISALIGN, PTOFF_L = 0, 1, 2, 3
LAYOUTS = ("dense", "pt4k", "misalign", "ptoff")
PTOFF_BYTES = 0x400
PT_ENTRIES = 1024
VALID = 1
# the readings (sgx_mmu.h): index va / S with the entry masked to S, the size field ignored,
# index va / S with the entry masked to 4 KiB, no table (the PDE names the data); RD_PTOFF: the
# table (or the section) starts at the PDE's bits 11:4
RD_DENSE, RD_4K, RD_MASK4K, RD_SECTION = 0, 1, 2, 3
RD_N = 4
RD_PTOFF = 0x10
READING_NAMES = {RD_DENSE: "dense", RD_4K: "4k", RD_MASK4K: "mask4k", RD_SECTION: "section"}
OUTSIDE, FAULT = "outside", "fault"


def page_size(code):
    """The page size a named code gives its table's entries, 0 for 6 and 7."""
    return SZ_4K << (2 * code) if code < NAMED else 0


def order_of(n):
    return n.bit_length() - 1


def geom(code, layout):
    """sgx_mmu_large_geom: the region of a code and layout, or None for a pair it refuses."""
    if code >= CODES or layout >= len(LAYOUTS):
        return None
    if code in (0, 5) and layout > PT4K:
        return None
    if code >= NAMED and layout != DENSE:
        return None
    s = page_size(code) if code < NAMED else SZ_4M
    g = dict(code=code, layout=layout, size=s, unit=s,
             pt_off=PTOFF_BYTES if layout == PTOFF_L else 0)
    if code == 0:
        g.update(region=8 * SZ_4K, nblocks=3, block_off=[(i + 1) * SZ_4K for i in range(3)],
                 trap_off=7 * SZ_4K)
    elif code < 5:
        nb = 2 if layout == MISALIGN else 3
        g.update(region=4 * s, nblocks=nb, block_off=[(i + 1) * s for i in range(nb)],
                 trap_off=3 * s)
    else:
        g.update(region=SZ_4M, nblocks=1, block_off=[0], trap_off=SZ_4M - SZ_4K)
    g["order"] = order_of(g["region"] // SZ_4K)
    return g


def pde(g, region=0):
    return region | g["pt_off"] | (g["code"] & 7) << 1 | VALID


def pte(addr):
    return addr | VALID


def table(g, region=0):
    """sgx_mmu_large_table: the 1024 entries of the table page."""
    trap = pte(region + g["trap_off"])
    pt = [trap] * PT_ENTRIES
    if g["code"] >= NAMED:
        return [pte(region + (i if i else 1) * SZ_4K) for i in range(PT_ENTRIES)]
    lay, nb, bo, size = g["layout"], g["nblocks"], g["block_off"], g["size"]
    if lay == PT4K:
        for i in range(PT_ENTRIES):
            k = i * SZ_4K // size
            if k < nb:
                pt[i] = pte(region + bo[k] + i * SZ_4K % size)
    elif lay == MISALIGN:
        for k in range(nb):
            pt[k] = pte(region + bo[k] + SZ_4K)
    elif lay == PTOFF_L:
        for k in range(nb):
            pt[g["pt_off"] // 4 + k] = pte(region + bo[k])
            pt[k] = pte(region + bo[(k + 1) % nb])          # the decoy: blocks rotated by one
    else:
        for k in range(nb):
            pt[k] = pte(region + bo[k])
    return pt


def phys(reading, size, pde_word, pt, va):
    """sgx_mmu_large_phys: the address VA offset va reaches under a reading assuming page size
    size (OUTSIDE: an index past the table page; FAULT: an entry without VALID)."""
    off = pde_word & 0xff0 if reading & RD_PTOFF else 0
    base = pde_word & 0xfffff000
    r = reading & ~RD_PTOFF
    if r == RD_SECTION:
        return base + off + va
    idx = va // SZ_4K if r == RD_4K else va // size
    idx += off // 4
    if idx >= PT_ENTRIES:
        return OUTSIDE
    e = pt[idx]
    if not e & VALID:
        return FAULT
    if r == RD_4K:
        return (e & 0xfffff000) + va % SZ_4K
    if r == RD_MASK4K:
        return (e & 0xfffff000) + va % size
    return (e & 0xfffff000 & ~(size - 1)) + va % size


def tag(slab, page, dword):
    """sgx_mmu_large_tag: dword `dword` of page `page` of slab `slab`."""
    return 0xa0000000 | (slab & 0xf) << 24 | (page & 0x3ff) << 12 | (dword & 0x3ff)


def token(g, off):
    """What a 4 KiB of the region at offset off reads as: `x` for the table page (no tags) or a
    4 KiB that straddles two pages (its dwords do not follow one page's tags), `S:P` for slab S
    page P (the tag's own fields, slab & 0xf), or the reading's failure."""
    if off in (OUTSIDE, FAULT):
        return off
    if off < SZ_4K or off % SZ_4K:
        return "x"
    return f"{(off // g['unit']) & 0xf}:{(off % g['unit']) // SZ_4K}"


def pages(g, reading, va0, va1, size=None):
    """The tokens of the VA pages [va0, va1) (offsets in the slot) under a reading."""
    size = size or g["size"]
    p, pt = pde(g), table(g)
    return [token(g, phys(reading, size, p, pt, va)) for va in range(va0, va1, SZ_4K)]


def every_reading(g):
    """(reading, size) of every reading the fork's safety case checks for a code: code 0 the 4 KiB
    one only, codes 6 and 7 at every named size."""
    out = []
    for rd in range(2 * RD_N):
        reading = rd % RD_N | (RD_PTOFF if rd >= RD_N else 0)
        if g["code"] == 0 and reading & ~RD_PTOFF != RD_4K:
            continue
        sizes = [g["size"]] if g["code"] < NAMED else [page_size(c) for c in range(NAMED)]
        out += [(reading, s) for s in sizes]
    return out


def union(g, va0, va1):
    """The region pages any reading of the safety case reaches over [va0, va1): a fill row's
    allowed changed pages (run/hooks.sh stops the stage on any other)."""
    out = set()
    p, pt = pde(g), table(g)
    for reading, s in every_reading(g):
        for va in range(va0, va1, SZ_4K):
            for a in (phys(reading, s, p, pt, va), phys(reading, s, p, pt, va + SZ_4K - 4)):
                if a not in (OUTSIDE, FAULT):
                    out.add(token(g, a - a % SZ_4K))
    return out


# the session's VA windows, as the fork's KUnit safety case holds them (sgx_mmu_large_test.c
# large_rows; HACKING.md "Known tool weaknesses"): code 0 [0, 16K) and [4M - 8K, 4M); codes 1-4
# [S - 8K, S + 8K) and [2S - 8K, 2S + 8K); code 5 [4M - 16K, 4M); codes 6, 7 [16K, 32K) read only
def windows(code):
    s = page_size(code)
    if code == 0:
        return [(0, SZ_16K, True), (SZ_4M - SZ_8K, SZ_4M, True)]
    if code <= 4:
        return [(s - SZ_8K, s + SZ_8K, True), (2 * s - SZ_8K, 2 * s + SZ_8K, True)]
    if code == 5:
        return [(SZ_4M - SZ_16K, SZ_4M, True)]
    return [(SZ_16K, SZ_32K, False)]


def inside(code, va0, va1, write):
    """Whether [va0, va1) lies in one of the code's windows (and a write in a writable one)."""
    return any(a <= va0 and va1 <= b and (w or not write) for a, b, w in windows(code))
