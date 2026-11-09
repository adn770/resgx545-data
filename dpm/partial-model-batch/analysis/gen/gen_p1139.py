#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""11.39 generator: writes tables/*.txt (the run tables of run_table.sh), declared.tsv (case, table, set,
risk), predictions-declared.tsv (case, quantity, value, model) and hashes.txt (sha256 of everything
that is frozen before a run). Run from p1139:  python3 gen/gen_p1139.py [--hash]

The models (section 2 of plan.md) are functions here, so a prediction is computed, not typed:
  trig(P, U, v)  the partial-render count and the last abort's page status from the PB's ZLS threshold
                 thr0 = P - 0x22 (E201), variant R1 (raised once by 0x20 after the first partial render:
                 E310's seven dword-35 rows and E312's 0x21) or R3 (never raised, except from 1 to 0x21;
refuted for 4096x4096 by E310's row at 0x40, dword 35 = 0x3c, kept as the null at 1024x768 where E464's
lists at 0x28 look like several partial renders).
U is the pages a whole scene needs: 4096x4096 289 (fitted to E204's ten partial renders at 0x23 under R1;
the E310 page count 0x11f is 287), 1024x768 21 (0x13 + the same 2, a declared assumption).
"""
import hashlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
U4096, U1024 = 289, 21

def thr0(P):
    return P - 0x22

def trig(P, U, v="R1", t0=None):
    """(n_partial, last_abort_status); n 0: no overflow."""
    t0 = thr0(P) if t0 is None else t0
    if t0 >= U:
        return 0, 0
    t1 = t0 + 0x20 if (v == "R1" or t0 <= 1) else t0
    n = 1 + (U - t0) // (t1 - 1)
    return n, (t0 if n == 1 else t1)

def d35(P, U, v="R1", t0=None):
    n, last = trig(P, U, v, t0)
    return (last - 2) & 0xffff if n else 0

RT_TRIG = "0x0654-0x0660,0x0700-0x0710,0x0720-0x0724,0x0748"
RT_DEPTH = "0x0654-0x0660,0x0720-0x0724"
COMMON = "--keep-overflow --wait-ms 20000 --dump-render $W/dump --dump-each --words $W/words --regs 0x0700-0x074c"

def tri(w, h, n=1, extra=""):
    return f"tri --width {w} --height {h} -n {n} {COMMON} {extra}".strip()

_marker = [0]
def marker():
    """a fill of the job's own: no two jobs of the batch fill a buffer with the same dword (a stale
    buffer or a dump of another job cannot match; audit D7)."""
    _marker[0] += 1
    return "0xdead%04x" % _marker[0]

def depth_args(ctl, ctl_next=None, fill=None, extra="", store=False):
    """fill None: the job's marker; "index": dword i holds i (the load tests; with store=True the store
    goes to a second buffer, filled with the marker, so a loaded dword is told from an untouched one)."""
    fill = fill or marker()
    s = f"--depth --depth-ctl {ctl} --depth-fill {fill} --depth-dump $W/depth"
    if store:
        s += f" --depth-store --depth-store-fill {marker()}"
    if ctl_next:
        s += f" --depth-ctl-next {ctl_next}"
    return f"{s} {extra}".strip()

tables = {}      # name -> list of (name, set, risk, P, knobs, rt, args)
preds = []       # (case, quantity, value, model)
def add(table, name, set_, risk, P, knobs, rt, args):
    tables.setdefault(table, []).append((name, set_, risk, str(P), knobs or "", rt or "-", args))
def pred(case, q, v, model):
    preds.append((case, q, str(v), model))
def hx(P):
    return "0x%x" % P

# ---------------------------------------------------------------- free: page order across renders
# A1: whole buffer, three renders a context. A2: 1024x768 and 4096x4096 partial-render sweeps, two renders.
for (w, h, st) in [(64, 64, "fit"), (256, 256, "fit"), (128, 128, "heldout"), (192, 128, "heldout"),
                   (512, 384, "heldout"), (1024, 768, "heldout"), (64, 64, "control"), (1024, 768, "control")]:
    c = f"fr-whole-{w}x{h}" + ("-rep" if st == "control" else "")
    add("free", c, st, "safe", "0x422", "", "-", tri(w, h, 3))
    pred(c, "walk_ok", "yes", "H-walk")                 # E309: the walk covers all pages, every job
    pred(c, "job2_is_head_prefix", "yes", "H-head")       # E309 (two 64x64 renders: pages 3, 4)
    pred(c, "job3_is_head_prefix", "yes", "H-head")
    if (w, h) == (64, 64):
        pred(c, "job1_pages", "1-2", "H-first")           # E309: page 1 first, 2 pages
    if (w, h) == (256, 256):
        pred(c, "job1_pages", "1-5", "H-first")
    pred(c, "partials", 0, "R1")
for P in (0x23, 0x24, 0x26, 0x28, 0x2a, 0x2c, 0x30, 0x34, 0x36, 0x38):
    st = "fit" if P in (0x23, 0x24, 0x28, 0x30) else "heldout"
    c = f"fr-1024-{hx(P)}"
    add("free", c, st, "safe", hx(P), "", "-", tri(1024, 768, 2))
    n, last = trig(P, U1024)
    pred(c, "job1_status", "overflow" if n else "ok", "H-trig")
    pred(c, "walk_ok", "yes", "H-walk")
    pred(c, "job2_is_head_prefix", "yes", "H-head")
    if n:
        # H-free-O: the pages the 3D frees at the partial render are appended in macrotile order,
        # each list head to tail, the global list's page last (E312's tail sequence).
        pred(c, "tail_has_state_order", "yes", "H-free-O")
add("free", "fr-1024-0x30-rep", "control", "safe", "0x30", "noreset", "-", tri(1024, 768, 2))
add("free", "fr-1024-0x38-rep", "control", "safe", "0x38", "", "-", tri(1024, 768, 2))
for c, P in (("fr-1024-0x30-rep", 0x30), ("fr-1024-0x38-rep", 0x38)):       # the repeats carry their cases' claims
    n, _ = trig(P, U1024)
    pred(c, "job1_status", "overflow" if n else "ok", "H-trig")
    pred(c, "walk_ok", "yes", "H-walk")
    pred(c, "job2_is_head_prefix", "yes", "H-head")
for P in (0x23, 0x40, 0x60, 0x80, 0xc0, 0x100):
    st = "fit" if P in (0x23, 0x100) else "heldout"
    c = f"fr-4096-{hx(P)}"
    add("free", c, st, "safe", hx(P), "", "-", tri(4096, 4096, 1))
    pred(c, "job1_status", "overflow", "H-trig")
    pred(c, "walk_ok", "yes", "H-walk")

# ---------------------------------------------------------------- trig: counts and boundaries
def trig_case(name, st, P, w, h, U, extra="", t0=None, knobs=""):
    add("trig", name, st, "safe", hx(P), knobs, RT_TRIG, tri(w, h, 1, extra))
    n1, _ = trig(P, U, "R1", t0)
    n3, _ = trig(P, U, "R3", t0)
    pred(name, "job1_status", "overflow" if n1 else "ok", "H-trig")
    pred(name, "partials", n1, "R1")
    pred(name, "partials", n3, "R3")
    pred(name, "dword35", "0x%x" % d35(P, U, "R1", t0), "R1")
    pred(name, "dword35", "0x%x" % d35(P, U, "R3", t0), "R3")
for P in (0x33, 0x34, 0x35, 0x36, 0x37, 0x38):
    trig_case(f"tg-1024-bd-{hx(P)}", "heldout", P, 1024, 768, U1024)
for P in (0x13e, 0x13f, 0x140, 0x141, 0x142, 0x143, 0x144):
    trig_case(f"tg-4096-bd-{hx(P)}", "heldout", P, 4096, 4096, U4096)
for P in (0x23, 0x24, 0x28, 0x2c, 0x30):
    trig_case(f"tg-1024-n-{hx(P)}", "fit" if P in (0x23, 0x30) else "heldout", P, 1024, 768, U1024)
for P in (0x23, 0x40, 0x60, 0x80, 0xc0, 0x100):
    trig_case(f"tg-4096-n-{hx(P)}", "fit" if P in (0x23, 0x100) else "heldout", P, 4096, 4096, U4096)
for V in (0x20, 0x40, 0x80, 0x100, 0x400):     # the ZLS threshold poked (pb:11), P default 0x422
    name = f"tg-4096-poke-{hx(V)}"
    add("trig", name, "control" if V == 0x400 else "heldout", "safe" if V == 0x400 else "risky", "0x422", "", RT_TRIG,
        tri(4096, 4096, 1, f"--kpoke-render 1:pb:11={hx(V)}"))
    if V == 0x400:
        pred(name, "job1_status", "ok", "H-poke-null")        # the default value: nothing changes
    else:
        n1, _ = trig(0x422, U4096, "R1", V)
        pred(name, "job1_status", "overflow", "H-poke")
        pred(name, "partials", n1, "R1+poke")
        pred(name, "job1_status", "ok", "H-poke-null")         # the alternative: the poke is not honoured

# ---------------------------------------------------------------- state: lists, owner, final state
for (dx, dy) in [(0, 0), (256, 0), (0, 192), (-128, 96), (384, 288)]:
    for P in (0x30, 0x28):
        c = f"st-mv{dx}_{dy}-{hx(P)}"
        st = "fit" if (dx, dy, P) in ((0, 0, 0x30), (0, 0, 0x28)) else "heldout"
        add("state", c, st, "safe", hx(P), "", "-", tri(1024, 768, 1, "" if (dx, dy) == (0, 0) else f"--move 1:{dx},{dy}"))
        pred(c, "global_list", "1:page1", "H-global")
        pred(c, "lists_disjoint", "yes", "H-state")
        pred(c, "lists_in_triangle_macrotiles", "yes", "H-state")
        n, last = trig(P, U1024)
        pred(c, "state_sum", last - 1, "H-state-abort")
        if P == 0x28:                      # E464's 9 lists at 0x28 hold at least 12 pages, up to page 0x14
            pred(c, "state_sum_ge", 12, "H-state-end")
for P in (0x2a, 0x2c, 0x34, 0x36):
    c = f"st-sweep-{hx(P)}"
    add("state", c, "heldout", "safe", hx(P), "", "-", tri(1024, 768, 1))
    n, last = trig(P, U1024)
    pred(c, "state_sum", last - 1, "H-state-abort")
    pred(c, "state_sum_ge", max(U1024 - last - 4, 0), "H-state-end")
for P in (0x40, 0x23):                          # many partial renders: which partial's lists remain
    c = f"st-4096-{hx(P)}"
    add("state", c, "heldout", "safe", hx(P), "", RT_TRIG, tri(4096, 4096, 1))
    n, last = trig(P, U4096)
    pred(c, "state_sum", last - 1, "H-state-abort")
    pred(c, "state_sum_acc", "no", "H-state-last")
for (dx, P) in [(-96, 0x38), (96, 0x38), (-96, 0x3c), (96, 0x3c), (-96, 0x40), (96, 0x40), (-96, 0x48), (96, 0x48)]:
    c = f"st-two-{'f' if dx < 0 else 'n'}-{hx(P)}"
    add("state", c, "heldout", "safe", hx(P), "", "-",
        tri(1024, 768, 2, f"--geometry 1 --move 2:{dx},0"))
    pred(c, "job1_status", "overflow", "H-trig")
add("state", "st-repeat-0x30-a", "control", "safe", "0x30", "", "-", tri(1024, 768, 1))
add("state", "st-repeat-0x30-b", "control", "safe", "0x30", "noreset", "-", tri(1024, 768, 1))
for c in ("st-repeat-0x30-a", "st-repeat-0x30-b"):
    pred(c, "same_lists_as", "st-mv0_0-0x30", "H-repeat")          # pages a list, the same in every run
pred("st-repeat-0x30-a", "lists_pages_differ_from", "no@st-mv0_0-0x30", "H-head")      # after a reset: the same pages
pred("st-repeat-0x30-b", "lists_pages_differ_from", "yes@st-mv0_0-0x30", "H-head")      # no reset: the free list was permuted

# ---------------------------------------------------------------- depth
Z05 = "--poke blk:1=0x00400200"          # the default triangle at z 0.5, depth test less (E461)
RAMP = "--tri-full --tri-z 0.25,0.75,0.25"   # E465's ramp over x (the stored dword names its pixel)
# CR_ISP_ZLSCTL: 0x00171004 | G << 3 (bits 11:3 = G, E465): G = 1, 33 and 127 (no two tiles at one address)
G1, G33, G127 = "0x0017100c", "0x0017110c", "0x001713fc"
def sign_pred(P):
    return "yes" if P < 0x2c else "no"
for P in (0x30, 0x2c, 0x2a, 0x28, 0x26, 0x24, 0x23, 0x34, 0x38):
    for G, gn in ((G1, "g1"), (G33, "g33")):
        if gn == "g33" and P not in (0x30, 0x28, 0x23):
            continue
        for r in (1, 2):
            c = f"dp-z05-{gn}-{hx(P)}-r{r}"
            st = "fit" if (gn == "g1" and P in (0x30, 0x28, 0x23) and r == 1) else ("control" if r == 2 else "heldout")
            add("depth", c, st, "safe", hx(P), "", RT_DEPTH,
                tri(1024, 768, 1, f"{Z05} " + depth_args(G)))
            n, _ = trig(P, U1024)
            pred(c, "job1_status", "overflow" if n else "ok", "H-trig")
            pred(c, "window_dwords", 64512 if gn == "g1" else 786432, "E465")
            if n:
                pred(c, "sign", sign_pred(P), "H-sign-P")
                pred(c, "zero_dwords", 15104 if gn == "g1" else 184320, "H-zero-M1")
            else:
                pred(c, "sign", "no", "H-sign-P")
                pred(c, "zero_dwords", 0, "H-zero-M1")
for P in (0x30, 0x28, 0x23, 0x60, 0x100):
    for G, gn in ((G33, "g33"), (G1, "g1")):
        if gn == "g1" and P not in (0x30, 0x28):
            continue
        for r in (1, 2):
            c = f"dp-ramp-{gn}-{hx(P)}-r{r}"
            st = "fit" if (gn == "g33" and P in (0x30, 0x28, 0x23) and r == 1) else ("control" if r == 2 else "heldout")
            add("depth", c, st, "safe", hx(P), "", RT_DEPTH, tri(1024, 768, 1, f"{RAMP} " + depth_args(G)))
            if gn == "g33" and P in (0x30, 0x28, 0x23):
                pred(c, "sign", "yes", "E468")
                pred(c, "zero_dwords", 184320, "E468")
                pred(c, "zero_whole_tiles", 336, "E468")
            elif gn == "g1":
                pred(c, "zero_dwords", 15104, "H-zero-M1")
            else:
                pred(c, "sign", "?", "explore")
# index fill: is the partial renders' depth loaded by the final render, and what does the store hold
for P in (0x422, 0x28, 0x30):
    for ctl, cn in ((G33, "noload"), ("0x0017510e", "load")):
        for sc, sx in (("z05", Z05), ("ramp", RAMP)):
            c = f"dl-{sc}-{cn}-{hx(P)}"
            st = "fit" if P == 0x422 else "heldout"
            add("depth", c, st, "safe", hx(P), "", RT_DEPTH, tri(1024, 768, 1, f"{sx} " + depth_args(ctl, None, "index", store=True)))
            if P == 0x422 and cn == "noload":
                pred(c, "stored_index_based_rows_ge12", "no", "E467")      # no bit 1: the clear value is stored
            if P == 0x422 and cn == "load":
                pred(c, "stored_equals_index", "all_loaded_tiles", "E467")
            if P != 0x422 and cn == "load":
                pred(c, "stored_index_based_rows_ge12", "yes", "H-load-yes")
            if P != 0x422 and cn == "noload":
                pred(c, "stored_index_based_rows_ge12", "no", "H-load-yes")
# overlapping triangles: A (near or far) in the geometry kick, B in the final render, depth decides
for P in (0x422, 0x38, 0x3c, 0x40, 0x48):
    for dx in (-96, 96):
        for nx, nn in ((None, "same"), ("0x0017510e", "load")):
            if P == 0x422 and nx:
                continue
            c = f"ov-{'far' if dx < 0 else 'near'}-{nn}-{hx(P)}"
            add("depth", c, "heldout", "safe", hx(P), "", RT_DEPTH,
                tri(1024, 768, 2, f"--geometry 1 --move 2:{dx},0 --tri-z 0.25,0.75,0.25 {Z05} " + depth_args(G33, nx)))
            if dx > 0:
                pred(c, "overlap_value", "B", "H-min")    # B nearer: min(zA, zB) = zB whatever is loaded
            elif P == 0x422:
                pred(c, "overlap_value", "A", "H-min")    # whole buffer: the min, A
            else:
                pred(c, "overlap_value", "A" if nn == "load" else "mixed", "H-dload-yes" if nn == "load" else "H-dload-no")
# the 4096x4096 window: G = 1 and 0 (E465, E489), and 127 (no two tiles at one address)
for G, gn, st in ((G1, "g1", "fit"), ("0x0017100c", "g1b", "control"), ("0x00171004", "g0", "fit"), (G127, "g127", "heldout")):
    if gn == "g1b":
        continue
    for r in (1, 2):
        c = f"w4096-{gn}-r{r}"
        add("depth", c, st if r == 1 else "control", "safe", "0x2000", "", RT_DEPTH,
            tri(4096, 4096, 1, f"{RAMP} " + depth_args(G)))
        if gn == "g1":
            pred(c, "zero_dwords", 80640, "E465")
            pred(c, "window_dwords", 326656, "E465")
        elif gn == "g0":
            pred(c, "zero_dwords", 48000, "E465")
            pred(c, "window_dwords", 196096, "E465")
        else:
            pred(c, "window_dwords", 16777216, "rule")
            pred(c, "zero_dwords_between", "4000000-4200000", "H-zero-row")   # 64 rows x 128 tiles x 512 less halves
            pred(c, "zero_dwords_between", "900000-1100000", "H-zero-mt")      # 32 x 64 tiles x 512: the first macrotile

# ---------------------------------------------------------------- owner: Q191, Q192, Q045
for (w, h, n, P, nm) in [(64, 64, 1, 0x422, "a"), (64, 64, 2, 0x422, "b"), (64, 64, 3, 0x422, "c"),
                         (64, 32, 1, 0x422, "d"), (32, 32, 1, 0x422, "e"), (64, 64, 1, 0x300, "f"),
                         (64, 64, 1, 0x200, "g"), (64, 64, 1, 0x100, "h")]:
    c = f"ow-keep-{nm}"
    add("owner", c, "fit" if nm == "a" else "heldout", "safe", hx(P), "keep",
        "-", f"tri --width {w} --height {h} -n {n} --ctx2 --close-first-early --close-trace --words $W/words --dump-render $W/dump --kpoke-render 1:ta:7^=0xc")
    if nm == "a":
        pred(c, "kept_page1_w0", "0x00200047", "E591")
        pred(c, "kept_page2_w0", "0x04000417", "E591")
        pred(c, "kept_page3_w01", "0x00020001,2", "E591")
    pred(c, "kept_page3_w0_is_count_head", "yes", "H191-L")     # (pages used << 16) | first page, last page
    pred(c, "kept_page2_w0_high", "0x%04x" % (P - 0x22), "H191-P")
# Q192 and Q045 between kicks need the changed tool (knob new); they are skipped when it is not there
add("owner", "ow-part-solo", "control", "safe", "0x28", "new keep", "-",
    "tri --width 1024 --height 768 -n 1 --keep-overflow --words $W/words --dump-render $W/dump")
for (flag, nm) in (("0xc", "c"), ("0x4", "4")):
    for (kn, kk) in (("keep", "k"), ("", "n")):
        c = f"ow-part-{nm}-{kk}"
        add("owner", c, "heldout", "safe" if kk == "k" else "risky", "0x28", ("new " + kn).strip(), "-",
            f"tri --width 1024 --height 768 -n 1 --keep-overflow --ctx2 --close-first-early --words $W/words --dump-render $W/dump --kpoke-render 1:ta:7^={flag}")
        if kn:
            pred(c, "kept_state_replaced", "yes" if flag == "0xc" else "no", "H192-R")
for (v, nm) in (("0", "zero"), ("0xa5000000:ramp", "ramp")):
    for P in (0x30, 0x28):
        c = f"ow-fill-{nm}-{hx(P)}"
        add("owner", c, "heldout", "risky" if nm == "ramp" else "safe", hx(P), "new", "-",
            tri(1024, 768, 2, f"--geometry 1 --tadata-fill-render 2:6:{v}"))
        pred(c, "walk_same_as_control", "yes", "H45-R")
        pred(c, "walk_same_as_control", "no", "H45-L")
        pred(c, "image_same_as_control", "yes", "H45-R")
for (flag, nm) in (("0xc", "c"), ("0x4", "4")):          # T4: the kept pages before the second context is closed
    c = f"ow-kcopy-{nm}"
    add("owner", c, "heldout", "safe", "0x422", "new keep", "-",
        f"tri --width 64 --height 64 -n 1 --ctx2 --close-first-early --kept-copy $W/kept --words $W/words --kpoke-render 1:ta:7^={flag}")
    pred(c, "kept_at_render_end_has_store", "?", "explore")      # yes: stored by the job's end; no: at close
for c in ("ow-part-c-n", "ow-part-4-n"):
    pred(c, "job1_status", "?", "explore")      # no keep: E458 faulted a 64x64 owner's successor; a partial owner is new
add("owner", "ow-fill-control-0x30", "control", "safe", "0x30", "new", "-", tri(1024, 768, 2, "--geometry 1"))
add("owner", "ow-fill-control-0x28", "control", "safe", "0x28", "new", "-", tri(1024, 768, 2, "--geometry 1"))

# ---------------------------------------------------------------- wide: counters, bit 2, hangs
GREEN = "$S/p1139-green.bin"
def probe(w, h, nv, extra=""):
    return f"probe --tri pixel --width {w} --height {h} --vertices {nv} --dump-render $W/dump {extra} {GREEN}".strip()
for nv in (900, 1050, 1200, 1350, 1500):
    c = f"wd-glist-{nv}"
    add("wide", c, "fit" if nv in (900, 1500) else "heldout", "safe", "0x422", "", RT_TRIG, probe(4096, 4096, nv))
    pred(c, "global_list_pages", {900: 4, 1500: 5}.get(nv, "?"), "E438")
    pred(c, "dword36", {900: 2, 1500: 3}.get(nv, "?"), "E438")
    pred(c, "status2_high", 0, "H36-Z")
for r in range(1, 9):                    # repeatability of the 0x0748 bit 2 pulse: alternate reset / no reset
    for (nv, P) in ((300, 0x100), (450, 0x100)):
        c = f"wd-bit2-{nv}-{r}"
        add("wide", c, "control", "safe", hx(P), "" if r % 2 else "noreset", "0x0600-0x0750", probe(4096, 4096, nv))
        pred(c, "status2_high", 0, "H36-Z")
        pred(c, "bit2_cleared", "?", "explore")
for (nv, P, fl) in [(300, 0x40, "hold"), (300, 0x23, "hold"), (900, 0x100, "hold"), (600, 0x100, ""), (750, 0x100, ""),
                    (800, 0x100, ""), (850, 0x100, "")]:
    c = f"wd-hang-{nv}-{hx(P)}"
    add("wide", c, "heldout" if nv in (750, 800, 850) else "fit", "risky", hx(P), fl, RT_TRIG, probe(4096, 4096, nv))
    pred(c, "outcome", "hang" if (nv, P) in ((300, 0x40), (300, 0x23), (900, 0x100)) else "overflow", "E438")
    pred(c, "held_pages_exhausted", "?", "explore")

order = ["free", "trig", "state", "depth", "wide", "owner"]
def write_all():
    os.makedirs(os.path.join(ROOT, "tables"), exist_ok=True)
    rows = []
    for t in order:
        with open(os.path.join(ROOT, "tables", t + ".txt"), "w") as f:
            f.write("# name|set|risk|P|knobs|rt|args (run_table.sh); written by gen/gen_p1139.py\n")
            for r in tables[t]:
                f.write("|".join(r) + "\n")
                rows.append((r[0], t, r[1], r[2]))
    with open(os.path.join(ROOT, "declared.tsv"), "w") as f:
        f.write("case\ttable\tset\trisk\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    with open(os.path.join(ROOT, "predictions-declared.tsv"), "w") as f:
        f.write("case\tquantity\tvalue\tmodel\n")
        for r in preds:
            if r[0] in {x[0] for x in rows}:
                f.write("\t".join(r) + "\n")
    return rows

def hashes(paths):
    out = []
    for p in paths:
        h = hashlib.sha256(open(os.path.join(ROOT, p), "rb").read()).hexdigest()
        out.append(f"{h}  {p}")
    return out

if __name__ == "__main__":
    rows = write_all()
    print(len(rows), "cases,", len(preds), "predictions")
    if "--hash" in sys.argv:
        files = ["declared.tsv", "predictions-declared.tsv"] + [f"tables/{t}.txt" for t in order] + \
                ["gen/gen_p1139.py", "lib1139.sh", "run_table.sh", "run-all-1139.sh", "recompute/recompute_p1139.py"]
        with open(os.path.join(ROOT, "hashes.txt"), "w") as f:
            f.write("\n".join(hashes(files)) + "\n")
        print(open(os.path.join(ROOT, "hashes.txt")).read())
