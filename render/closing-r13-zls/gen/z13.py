# SPDX-License-Identifier: MIT
"""z13.py: r13-zls's rows and frozen rivals (round 13 plan closing13/plan/rank-round13.md sections
2 and 3, decisions R13-1 (a), R13-8 (a); tool t10, resgx545 a581c06 sgxfive-test.c).

Stage zbase (Q243, the moved load base; record E1029). Every row is E977's z243 form (64 x 32,
--tri-full at depth 0.5, the ZLS control 0x0017500e: depth loaded (bits 1, 14), stored, G 1) on
t10, with the depth test never (`--poke blk:1=0x00000200`, E467's form: the triangle changes no
depth, so the store holds what was loaded), the depth buffer filled with `index` (dword i holds i,
so a stored dword names the address it was loaded from), a store buffer of its own
(`--depth-store`, filled 0x3e800000) and `--depth-pages 20`. t10 arms depth_arm's pokes (rd:1 =
0x3e000000, rd:11, rd:12 = the depth buffer - base, rd:13 = the store buffer - base) before a row's
`--kpoke-render 1:` pokes (sgxfive-test.c depth_arm and the render loop), and the fork's
sgxfive_kpoke_take writes them in arm order, so `--kpoke-render 1:rd:12=V` replaces the load base.
Every kept t10/t4 depth job maps the depth buffer at 0x3e001000 and the next buffer right after it
(18 pages: store 0x3e013000; 20 pages: 0x3e015000), so with 20 pages depth_arm's own rd:12 is
0x1000 and rd:13 0x15000; hook_check stops the stage if the tool prints other addresses.
A move m sets rd:12 = 0x1000 + m. The load reads the target's 4 tiles (2048 dwords, E465's G 1
layout) from rd:12, so the store's dword k holds the loaded dword k + d of the depth buffer:
  H-MOVED      d = m / 4 (the load reads E465's layout from the new base)
  H-ALIGN4K    the base rounded down to 4 KiB;  H-ALIGNTILE  rounded down to 2 KiB (a tile)
  H-STOREBASE  rd:12 ignored, the load reads rd:13's buffer (its fill 0x3e800000)
  H-UNMOVED    the poke does not reach the load (identity, d = 0)
zb-mst moves the load base onto the store's own (rd:12 = rd:13 = 0x15000) with the fills swapped
(depth 0x3e800000, store `index`): every model that follows rd:12 or rd:13 stores the store
buffer's own index (read before written), H-UNMOVED 0x3e800000.
Controls (can fail): zb-c-ctl (E977's z243-ctl with rd:12 re-poked to its own 0x1000: drawn 2048,
the store byte for byte E977's kept dump), zb-c-eq0 (E995's eq-m0, compare never: drawn 0, store
byte for byte E995's), zb-c-id (this form, rd:12 its own: the identity, E467) and zb-c-off (a
+0x1000 move with the load bits 1 and 14 cleared, 0x0017100c: the clear value 1.0 at every
target dword, E467: nothing may follow the move).

Stage zbits (Q071, bits 12, 16, 20 alone and in pairs; record E1030). Stencil rows: E988's st1-b0
(64 x 32, the stencil loaded from `bytes`, EQUAL against mask 0x01, SOP3 invert, `--isp2
0x040501ff`, 1024 drawn) with the control word 0x0017300e's bits cleared; ramp rows: E977's
z242-c-f0 (80 x 40, G 2, 0x00171014) the same. E989: the three cleared together (with the set
half) make the stencil test read 0 (2048 drawn); E997: cleared together they store a linear image
(r10-x zb-clr-f0's kept dump). Rivals per clause c (Z: the test reads 0; L: the linear store):
c-BIT-k (k cleared), c-PAIR-a+b (both cleared), c-ALL (only the triple: no row here), c-ANY (any
one), and Z-SET (the set half 15, 21-23, 27-31 alone). Controls (can fail): zbs-base (E988's st1-b0,
1024), zbs-q071 (E989's q071-b0, 2048), zbr-ctl (E977's z242-c-f0, byte for byte its kept dump).

Stage zfmt (Q120, E1015's F7K and F6C held out; record E1031). zf-7k-3f, zf-7k-1f: format 7
under the constant stencil fills 0x3f and 0x1f (equal to the template's markers) on E986's x ramp:
F7K (c7_rule.f7k_block(S)) against F7K-FIX (S fixed at 0xa5). zf-y48-f6: format 6 on a y ramp of
another size (48 x 32) and origin (depths 0.375, 0.375, 0.875), its rows read from zf-y48-f0 (the
format-0 reference, a reading row); zf-flat-f6: format 6 on a flat 0.5 (every row of every tile
equal, v = 0x3f000000, E977/E995's stored 0.5): F6C (c7_rule.f6c_group) against F6RAW (E985's raw
layout). Control (can fail): zf-y6-ctl, E986's z2y-f6 rerun, byte for byte its kept dump."""
import struct

MAIN = "tri --keep-going --wait-ms 20000"
TILE_DW = 512
FILL_DEAD = 0xDEADBEEF

# ---- zbase -----------------------------------------------------------------------------------
ZB_CTL = 0x0017500E
ZB_CTL_OFF = ZB_CTL & ~0x4002              # bits 1 and 14 (the depth load) cleared: 0x0017100c
ZB_PAGES = 20
ZB_BASE = 0x3E000000
ZB_DEPTH = 0x3E001000
ZB_STORE = ZB_DEPTH + ZB_PAGES * 4096      # 0x3e015000
ZB_OWN = ZB_DEPTH - ZB_BASE                # 0x1000: depth_arm's rd:12
ZB_ST_OFF = ZB_STORE - ZB_BASE             # 0x15000: depth_arm's rd:13
ZB_N = 2048                                # 64 x 32: 4 tiles of 512 dwords (G 1)
ZB_SFILL = 0x3E800000
ZB_CLEAR = 0x3F800000
NEVER, LESS = 0x00000200, 0x00400200
ZB_MODELS = ("H-MOVED", "H-ALIGN4K", "H-ALIGNTILE", "H-STOREBASE", "H-UNMOVED")
# E977's z243-ctl (r9-x tables/zls.txt) and E995's eq-m0 (r10-x tables/dcmp.txt), as they ran on t4
Z243_CTL = ("tri --keep-going --wait-ms 20000 --width 64 --height 32 --max-width 64 --max-height 32"
            " --tri-full --tri-z 0.5,0.5,0.5 --depth --depth-ctl 0x0017500e --depth-fill 0x3f400000"
            ' --depth-store --depth-dump "$W" --poke blk:1=0x00400200 --pixels')
EQ_M0 = ("tri --keep-going --wait-ms 20000 --width 64 --height 32 --max-width 64 --max-height 32"
         " --tri-full --tri-z 0.5,0.5,0.5 --depth --depth-ctl 0x0017500e --depth-fill 0x3f000000"
         ' --depth-store --depth-dump "$W" --poke blk:1=0x00000200 --pixels')


def zb_args(rd12, ctl=ZB_CTL, dfill="index", sfill=f"{ZB_SFILL:#010x}"):
    return (f"{MAIN} --width 64 --height 32 --max-width 64 --max-height 32 --tri-full --tri-z "
            f"0.5,0.5,0.5 --depth --depth-ctl {ctl:#010x} --depth-fill {dfill} --depth-store "
            f"--depth-store-fill {sfill} --depth-pages {ZB_PAGES} --depth-dump \"$W\" --poke "
            f"blk:1={NEVER:#010x} --pixels --kpoke-render 1:rd:12={rd12:#x}")


# name: (set, rd:12 move m (None: the row's own args), args); in run order: the controls, the
# aligned moves, the store's own base, then the moves below a page (an unaligned base last)
ZB_MOVES = {"zb-m1000": 0x1000, "zb-m4000": 0x4000, "zb-m10000": 0x10000, "zb-mst": None,
            "zb-m800": 0x800, "zb-m40": 0x40, "zb-m4": 0x4}
ZBASE = {
    "zb-c-ctl": Z243_CTL + f" --kpoke-render 1:rd:12={ZB_OWN:#x}",
    "zb-c-eq0": EQ_M0,
    "zb-c-id": zb_args(ZB_OWN),
    "zb-c-off": zb_args(ZB_OWN + 0x1000, ctl=ZB_CTL_OFF),
}
for _n, _m in ZB_MOVES.items():
    ZBASE[_n] = (zb_args(ZB_ST_OFF, dfill=f"{ZB_SFILL:#010x}", sfill="index") if _m is None
                 else zb_args(ZB_OWN + _m))
ZB_CONTROL_READS = {"zb-c-ctl": "drawn,dst_changed", "zb-c-eq0": "drawn,dst_changed",
                    "zb-c-id": "dst_changed", "zb-c-off": "dst_changed"}
ZB_CONTROL_DRAWN = {"zb-c-ctl": 2048, "zb-c-eq0": 0}


def zb_offset(model, m):
    """the dword offset d of the load (store dword k = depth dword k + d), or None: no index"""
    base = ZB_OWN + m
    if model == "H-MOVED":
        return m // 4 if m % 4 == 0 else None
    if model == "H-ALIGN4K":
        return ((base & ~0xFFF) - ZB_OWN) // 4
    if model == "H-ALIGNTILE":
        return ((base & ~0x7FF) - ZB_OWN) // 4
    if model == "H-UNMOVED":
        return 0
    return None                             # H-STOREBASE: the store buffer's fill


def zb_predict(name, model):
    """the store's first ZB_N dwords under model (the rest keeps the store's fill)"""
    if name == "zb-mst":
        return ([ZB_SFILL] * ZB_N if model == "H-UNMOVED" else list(range(ZB_N)))
    m = ZB_MOVES[name]
    d = zb_offset(model, m)
    return [ZB_SFILL] * ZB_N if d is None else [k + d for k in range(ZB_N)]


def zb_store_fill(name):
    return None if name == "zb-mst" else ZB_SFILL    # zb-mst's store is `index`


# ---- zbits -----------------------------------------------------------------------------------
ST_CTL = 0x0017300E
RAMP_CTL = 0x00171014
SET_BITS = 0xF8E08000                      # 15, 21-23, 27-31 (r10-x gen/z.py)
TRIPLE = (12, 16, 20)
CLEARS = ((12,), (16,), (20,), (12, 16), (12, 20), (16, 20))
ISP2_B0 = 2 << 25 | 5 << 16 | 0x01 << 8 | 0xFF     # EQUAL, SOP3 invert, mask 0x01: 0x040501ff
Q071_CTL = (ST_CTL & ~0x00111000) | SET_BITS       # E989's 0xf8e6a00e
DRAWN_LOADED, DRAWN_ZERO = 1024, 2048


def st_args(ctl):
    return (f"{MAIN} --tri-full --width 64 --height 32 --max-width 64 --max-height 32 --depth "
            f"--depth-ctl {ctl:#010x} --depth-fill 0x3f800000 --stencil --stencil-fill bytes "
            f"--stencil-store --isp2 {ISP2_B0:#010x} --depth-dump \"$W\" --pixels")


def ramp_args(ctl):
    return (f"{MAIN} --width 80 --height 40 --max-width 80 --max-height 40 --tri-v "
            f"0,0,40960,0,0,20480 --tri-z 1,0,1 --depth --depth-ctl {ctl:#010x} --depth-fill "
            f"0xdeadbeef --depth-dump \"$W\" --poke blk:1={LESS:#010x}")


def cleared(ctl, bits):
    for b in bits:
        ctl &= ~(1 << b)
    return ctl


def tag(bits):
    return "c" + "-".join(str(b) for b in bits)


ZBITS = {"zbs-base": st_args(ST_CTL), "zbs-q071": st_args(Q071_CTL), "zbr-ctl": ramp_args(RAMP_CTL)}
ZBITS_BITS = {}                            # held-out row: the bits cleared (or "set")
for _b in CLEARS:
    ZBITS[f"zbs-{tag(_b)}"] = st_args(cleared(ST_CTL, _b))
    ZBITS_BITS[f"zbs-{tag(_b)}"] = _b
ZBITS["zbs-set"] = st_args(ST_CTL | SET_BITS)
ZBITS_BITS["zbs-set"] = "set"
for _b in CLEARS:
    ZBITS[f"zbr-{tag(_b)}"] = ramp_args(cleared(RAMP_CTL, _b))
    ZBITS_BITS[f"zbr-{tag(_b)}"] = _b
ZBITS_CONTROL = {"zbs-base": ("drawn", DRAWN_LOADED), "zbs-q071": ("drawn", DRAWN_ZERO),
                 "zbr-ctl": ("depth_changed", 4608)}


def clause_models(c):
    ms = [f"{c}-BIT-{k}" for k in TRIPLE] + [f"{c}-PAIR-{a}+{b}" for a, b in CLEARS[3:]]
    return ms + [f"{c}-ALL", f"{c}-ANY"] + (["Z-SET"] if c == "Z" else [])


def clause_on(model, bits):
    """does the clause's effect appear on a row whose control word has `bits` cleared ("set":
    the set half set instead) under model"""
    kind = model.split("-", 1)[1]
    if bits == "set":
        return kind == "SET"
    if kind.startswith("BIT-"):
        return int(kind[4:]) in bits
    if kind.startswith("PAIR-"):
        return set(map(int, kind[5:].split("+"))) <= set(bits)
    if kind == "ALL":
        return set(TRIPLE) <= set(bits)
    if kind == "ANY":
        return bool(bits)
    return False                            # SET on a clear row


def zbits_predict(name, model):
    """stencil rows (Z models): the drawn count; ramp rows (L models): "linear" or "tiled"."""
    on = clause_on(model, ZBITS_BITS[name])
    if name.startswith("zbs-"):
        return DRAWN_ZERO if on else DRAWN_LOADED
    return "linear" if on else "tiled"


# ---- zfmt ------------------------------------------------------------------------------------
F6_CTL, F7_CTL, F0_CTL = 0x0617300E, 0x0717300E, 0x0017300E
FLAT_V = 0x3F000000
ZF_MODELS_7 = ("F7K", "F7K-FIX")
ZF_MODELS_6 = ("F6C", "F6RAW")


def zf_args(w, ctl, z, sfill):
    return (f"{MAIN} --width {w} --height 32 --max-width {w} --max-height 32 --tri-full --tri-z "
            f"{z} --depth --depth-ctl {ctl:#010x} --depth-fill 0xdeadbeef --stencil "
            f"--stencil-fill {sfill} --stencil-store --depth-dump \"$W\" --poke blk:1={LESS:#010x}")


# name: (set, W, ramp, control word, stencil fill)
ZFMT_ROWS = {
    "zf-y6-ctl": ("control", 64, "0.25,0.25,0.75", F6_CTL, "index"),        # E986's z2y-f6
    "zf-7k-3f": ("heldout", 64, "0.25,0.75,0.25", F7_CTL, "0x3f3f3f3f"),
    "zf-7k-1f": ("heldout", 64, "0.25,0.75,0.25", F7_CTL, "0x1f1f1f1f"),
    "zf-y48-f0": ("reading", 48, "0.375,0.375,0.875", F0_CTL, "index"),
    "zf-y48-f6": ("heldout", 48, "0.375,0.375,0.875", F6_CTL, "index"),
    "zf-flat-f6": ("heldout", 64, "0.5,0.5,0.5", F6_CTL, "index"),
}
ZFMT = {n: zf_args(w, c, z, s) for n, (_, w, z, c, s) in ZFMT_ROWS.items()}
ZF_REF = {"zf-y48-f6": "zf-y48-f0"}        # F6C's row floats: that row's format-0 dump
ZF_Y6_CHANGED = 212                        # E986/E1015: z2y-f6's depth #1 changed dwords


def in_tile_index(x, y):
    """E465: the dword of pixel (x, y) in its 32 x 16 tile, y0 x0 y1 x1 y2 x2 y3 x3 x4"""
    x, y = x & 31, y & 15
    i = 0
    for b in range(4):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    return i | (x >> 4 & 1) << 8


def block_of(tx, ty, tw):
    """E985's block order of a compressed format's 512-dword tile blocks (c7-q120 score.py)"""
    return 2 * tw * (ty >> 1) + 2 * tx + (ty & 1)


def tiles(w, h):
    return -(-w // 32), -(-h // 16)


def row_values(ref, w, h):
    """{(tx, ty): 16 lists of the 32 reference dwords of each tile row} from a format-0 dump (G 1:
    tile (tx, ty) at 512 (2 ty + tx), E465)"""
    tw, th = tiles(w, h)
    out = {}
    for ty in range(th):
        for tx in range(tw):
            slot = ty * 2 + tx
            out[(tx, ty)] = [[ref[TILE_DW * slot + in_tile_index(x, y)] for x in range(32)]
                             for y in range(16)]
    return out


def flat_rows(w, h):
    tw, th = tiles(w, h)
    return {(tx, ty): [[FLAT_V] * 32 for _ in range(16)] for ty in range(th) for tx in range(tw)}


def f6_groups(rows, w, h, rule):
    """[(block, group q, predicted 12 dwords under F6C, the F6RAW rival's 12)] for every applicable
    group: the 4 rows of the group each one value and every earlier group of the block applicable
    (c7_rule.py RULE_F6C)"""
    tw, th = tiles(w, h)
    out = []
    for (tx, ty), rs in sorted(rows.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        blk = block_of(tx, ty, tw)
        for q in range(4):
            g = rs[4 * q:4 * q + 4]
            if not all(len(set(r)) == 1 for r in g):
                break
            raw = [rs[(12 * q + i) // 32][(12 * q + i) % 32] | rule.SIGN for i in range(12)]
            out.append((blk, q, rule.f6c_group([r[0] for r in g]), raw))
    return out


def f7_pred(fill_byte, rule, rival):
    """{dword: value} of format 7 under a constant stencil (4 blocks of 256 dwords at 64 x 32)"""
    return {256 * k + i: v for k in range(4) for i, v in enumerate(rule.f7k_block(fill_byte, rival))}


def dwords(b):
    return None if b is None else list(struct.unpack("<%dI" % (len(b) // 4), b[:len(b) // 4 * 4]))


def jobs():
    """[(stage, name, set, knobs, args, {quantity: {model: value}})] in run order"""
    out = []
    for n, a in ZBASE.items():
        if n in ZB_CONTROL_READS:
            q = {"store": {"H-E467": "rule"}}
            if n in ZB_CONTROL_DRAWN:
                q["drawn"] = {"H-E467": str(ZB_CONTROL_DRAWN[n])}
            out.append(("zbase", n, "control", f"expectdiff reads:{ZB_CONTROL_READS[n]}", a, q))
        else:
            out.append(("zbase", n, "heldout", "expectdiff", a,
                        {"store": {m: f"d={zb_offset(m, ZB_MOVES[n]) if n != 'zb-mst' else 'own'}"
                                   for m in ZB_MODELS}}))
    for n, a in ZBITS.items():
        if n in ZBITS_CONTROL:
            k, v = ZBITS_CONTROL[n]
            out.append(("zbits", n, "control", f"expectdiff reads:{k}", a, {k: {"H-E988": str(v)}}))
            continue
        c, quantity = ("Z", "drawn") if n.startswith("zbs-") else ("L", "layout")
        out.append(("zbits", n, "heldout", "expectdiff", a,
                    {quantity: {m: str(zbits_predict(n, m)) for m in clause_models(c)}}))
    for n, a in ZFMT.items():
        sset = ZFMT_ROWS[n][0]
        if sset == "control":
            out.append(("zfmt", n, "control", "expectdiff reads:depth_changed", a,
                        {"depth_changed": {"H-E986": str(ZF_Y6_CHANGED)}}))
        elif sset == "reading":
            out.append(("zfmt", n, "reading", "expectdiff", a, {}))
        elif n.startswith("zf-7k"):
            out.append(("zfmt", n, "heldout", "expectdiff", a,
                        {"dump": {m: "rule" for m in ZF_MODELS_7}}))
        else:
            out.append(("zfmt", n, "heldout", "expectdiff", a,
                        {"dump": {m: "rule" for m in ZF_MODELS_6}}))
    return out
