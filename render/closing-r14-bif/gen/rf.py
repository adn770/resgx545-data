# SPDX-License-Identifier: MIT
"""rf.py: r14-bif's rows and frozen predictions (stage refill, Q108's stale-data clause, E1046).

The form is E1029's zb-c-id (r13-zls zbase, t10, kept and passed): a 64 x 32 target, the triangle
over all of it at depth 0.5 with the depth test never (`--poke blk:1=0x00000200`, E467: the store
holds what was loaded), ZLS control 0x0017500e (load and store), the depth buffer `index` (dword k
holds k) at 0x3e001000, a separate store buffer filled 0x3e800000 at 0x3e015000, 20 pages each.
Here it runs twice on one context (`tri -n 2 --keep-going`, t14 from c58f9f9). Without
--depth-ctl-next the tool fills every buffer again before render 2 (the same index and store
fill), then, for a refill row, `--refill 2:depth=V` writes V to every dword of the depth buffer
just before render 2's kick. The store of render 2 says what render 2 loaded:

  F      the first 2048 dwords k (the index render 1 loaded), the rest the store's fill
  V      the first 2048 dwords V, the rest the fill (the host's refill reached the load)
  clear  the first 2048 dwords 1.0 (no load: the control word's clear)

The knob rows put CACHECONSISTENT (PTE flag 0x8, debugfs vm_pte_flags) on the depth buffer's
mapping (vm_pte_addr 0x3e001000; the kernel logs `vm_map 0x3e001000 +0x14000: PTE flags 0x8`).

Frozen (per refill row, quantity store2):
  H-CC-COHERENT  flag set: render 2 reads V          H-CC-STALE  flag set: render 2 reads F
  H-NC-COHERENT  flag clear: render 2 reads V        H-NC-STALE  flag clear: render 2 reads F
  H-CC-NOOP      the flag without a refill: render 2 reads F (E945's "changed nothing", held out
                 on a depth load)
Favoured [infer]: H-CC-COHERENT and H-NC-COHERENT (the host maps a BO write-combined, fork
sgxfive_drv.c "mapped write-combined on the CPU", and nothing kept shows a ZLS load reused across
renders). Controls that can fail: rf-c-plain (E965's knob-free tri-c-depth twice: both renders
exact, each store 4096 dwords changed), rf-c-depth (no knob, no
refill: both stores byte for byte E1029's zb-c-id dump), rf-c-unread (flag set, render 1 with
the clearing control 0x0017100c that never loads, render 2 0x0017500e by --depth-ctl-next after
the refill: store 1 byte for byte E1029's zb-c-off dump, store 2 V)."""

W, H = 64, 32
N = W * H                      # the dwords the 64 x 32 ZLS store writes (E1029)
PAGES = 20
DEPTH, STORE, BASE = 0x3E001000, 0x3E015000, 0x3E000000
SFILL = 0x3E800000             # the store buffer's fill (E1029's zb-c-id)
V = 0x3F400000                 # the refill value, 0.75 (not the fill, the clear or an index)
CLEAR = 0x3F800000             # 1.0: the clearing control's store (E1029's zb-c-off)
CTL_LOAD, CTL_CLEAR = 0x0017500E, 0x0017100C
PTE_CC = 0x8
PLAIN_CHANGED = 4096           # E965's tri-c-depth (64 x 64, control 0x0017100c): store 1.0 x 4096
DWORDS = PAGES * 1024

COMMON = ("tri -n 2 --keep-going --wait-ms 20000 --width 64 --height 32 --max-width 64 "
          "--max-height 32 --tri-full --tri-z 0.5,0.5,0.5 --depth --depth-ctl {ctl} "
          "--depth-fill index --depth-store --depth-store-fill 0x3e800000 --depth-pages 20 "
          '--depth-dump "$W" --poke blk:1=0x00000200')
KNOB = f"dbg:vm_pte_addr={DEPTH:#010x} dbg:vm_pte_flags={PTE_CC:#x}"
REFILL = f" --refill 2:depth={V:#010x}"
R13Z = "render/closing-r13-zls/out/20261113-213117/zbase/"
KEPT = {"id": "data:" + R13Z + "zb-c-id.depth-store.1.bin.gz",     # E1029: store = identity
        "off": "data:" + R13Z + "zb-c-off.depth-store.1.bin.gz"}   # E1029: store = 1.0

# models of each held-out row: {model: the class of render 2's store}
MODELS = {
    "rf-cc-keep": {"H-CC-NOOP": "F"},
    "rf-cc-refill": {"H-CC-COHERENT": "V", "H-CC-STALE": "F"},
    "rf-nc-refill": {"H-NC-COHERENT": "V", "H-NC-STALE": "F"},
}
FAVOURED = ("H-CC-NOOP", "H-CC-COHERENT", "H-NC-COHERENT")
# what each control must read: (store 1's kept dump, the class of store 2)
CONTROL = {"rf-c-depth": ("id", "F"), "rf-c-unread": ("off", "V")}


def jobs():
    """(name, set, knobs, args, {quantity: {model: value}}) in run order."""
    load = COMMON.format(ctl=f"{CTL_LOAD:#010x}")
    unread = COMMON.format(ctl=f"{CTL_CLEAR:#010x}") + f" --depth-ctl-next {CTL_LOAD:#010x}"
    return [
        ("rf-c-plain", "control", "reads:job,renders,dst1,dst2",
         'tri -n 2 --depth --depth-store --depth-dump "$W"',
         {"renders": {"control": "2ok"}, "dst1": {"control": str(PLAIN_CHANGED)},
          "dst2": {"control": str(PLAIN_CHANGED)}}),
        ("rf-c-depth", "control", "expectdiff reads:job,dst1,dst2", load,
         {"store1": {"control": "F"}, "store2": {"control": "F"}}),
        ("rf-c-unread", "control", f"{KNOB} expectdiff reads:job,dst1,dst2,dep2",
         unread + REFILL, {"store1": {"control": "clear"}, "store2": {"control": "V"}}),
        ("rf-cc-keep", "heldout", f"{KNOB} expectdiff", load,
         {"store2": MODELS["rf-cc-keep"]}),
        ("rf-cc-refill", "heldout", f"{KNOB} expectdiff", load + REFILL,
         {"store2": MODELS["rf-cc-refill"]}),
        ("rf-nc-refill", "heldout", "expectdiff after", load + REFILL,
         {"store2": MODELS["rf-nc-refill"]}),
    ]


def dwords(b):
    import struct
    return None if b is None else list(struct.unpack("<%dI" % (len(b) // 4), b))


def store_class(d):
    """The class of a store dump (dwords): F, V, clear, or `mixed F a V b other c` / `other`,
    the rest of the buffer (past the 2048 the store writes) required to keep the fill."""
    if d is None or len(d) != DWORDS:
        return None
    rest = all(v == SFILL for v in d[N:])
    head = d[:N]
    nf = sum(1 for k, v in enumerate(head) if v == k)
    nv = sum(1 for v in head if v == V)
    nc = sum(1 for v in head if v == CLEAR)
    if rest and nf == N:
        return "F"
    if rest and nv == N:
        return "V"
    if rest and nc == N:
        return "clear"
    if nf or nv:
        return f"mixed F {nf} V {nv} other {N - nf - nv}" + ("" if rest else ", rest changed")
    return "other" + ("" if rest else ", rest changed")
