"""S1 pixel stages: B1 (p-b1), C (p-c), G (p-g), B2 (p-b2), D (p-d), F (p-f).  Proposals: exp-pixel-faults.md."""
from __future__ import annotations

import gzip
import json
import math
import re
import struct
import tomllib

import numpy as np

from s1common import BINS, DATA, REPO, Row, f32, probe

TEXD = DATA / "texture/p1141"
DEPTH_CTL = 0x0017100C


def f32r(x: float) -> float:
    return float(np.float32(x))


def bits(x: float) -> int:
    return struct.unpack("<I", struct.pack("<f", x))[0]


def fbits(b: int) -> float:
    return struct.unpack("<f", struct.pack("<I", b))[0]


def depth_args(w, h, pages=None):
    """tri1141.py depth_args generalised: the depth tile pitch g = tiles across - 1 goes into the control."""
    g = max(1, (w + 31) // 32 - 1)
    tw, th = (w + 31) // 32, (h + 15) // 16
    tiles = (th - 1) * (g + 1) + tw
    pages = pages or max((w * h * 4 + 4095) // 4096, tiles // 2) + 16
    ctl = (DEPTH_CTL & ~(0x1FF << 3)) | g << 3
    return (f'--depth --depth-ctl {hex(ctl)} --depth-fill 0xdeadbeef --depth-dump "$W/depth" '
            f'--depth-pages {pages} --poke blk:1=0x00400200')


def tri_depth_cmd(w, h, V, Z, pages=None):
    v256 = ",".join(str(int(c * 256)) for p in V for c in p)
    zs = ",".join(repr(float(z)) for z in Z)
    return (f'tri --keep-overflow --wait-ms 20000 --width {w} --height {h} --tri-v {v256} --tri-z {zs} '
            f'{depth_args(w, h, pages)} --pixels')


# ------------------------------------------------------------------------------------------ B1
def mant_trunc(a, k):
    b = bits(f32r(a))
    return fbits(b & ~((1 << (24 - k)) - 1))


def mant_rn(a, k):
    b = bits(f32r(a))
    q = 1 << (24 - k)
    return fbits(((b + (q >> 1)) // q) * q)


def fx_trunc(a, m):
    q = 2.0 ** -m
    return math.floor(a / q) * q


def fx_rn(a, m):
    q = 2.0 ** -m
    return math.floor(a / q + 0.5) * q


def recip_k(x, k):
    e = math.floor(math.log2(1 / x))
    q = 2.0 ** (e - (k - 1))
    return math.floor((1 / x) / q) * q


def rules(A, dz, dx):
    r = {"T16": mant_trunc(A, 16), "T17": mant_trunc(A, 17), "T18": mant_trunc(A, 18), "T20": mant_trunc(A, 20),
         "RN16": mant_rn(A, 16), "RN20": mant_rn(A, 20), "FX30": fx_trunc(A, 30), "FX31": fx_trunc(A, 31),
         "FX32": fx_trunc(A, 32), "FXRN30": fx_rn(A, 30), "f32": f32r(A)}
    for k in range(16, 21):
        r[f"RD{k}"] = f32r(dz * recip_k(dx, k))          # dz x recip_k(dx), the reciprocal-of-dx form
    return {k: bits(f32r(v)) for k, v in r.items()}


B1_RAMPS = [("g-r2", 1 / 16, 700), ("g-r4", 1 / 2, 400), ("g-r6", 1 / 128, 400), ("g-r7", 1 / 128, 700),
            ("g-r9", 1 / 4, 900), ("g-r11", 1 / 8, 1700), ("g-r12", 9 / 128, 400), ("g-r13", 0.03, 700)]


def p_b1():
    rows, preds = [], []
    Z0 = 0.5

    def job(nm, dz, dx, st, role, cond=None):
        z1 = repr(float(f32r(Z0 + dz)))
        rows.append(Row(nm, st, "safe", "-", "stophang", "-", tri_depth_cmd(1024, 32, ((0, 0), (dx, 0), (0, dx)),
                                                                        (Z0, float(z1), Z0)), role, cond or nm))
        A = (f32r(Z0 + dz) - f32r(Z0)) / dx
        for rn, w in rules(A, f32r(Z0 + dz) - f32r(Z0), dx).items():
            preds.append((nm, "rule_word", f"0x{w:08x}", rn, st))
        preds.append((nm, "A_exact", repr(A), "plane", st))

    job("g-ctl", 1 / 16, 400, "control", "control: dp-bx-b0's geometry (A = 1/6400) at 1024 x 32; "
        "the range must hold 0x3923d700 (E731's fit), not f32(A) = 0x3923d70a")
    job("g-dyadic", 1 / 16, 512, "control", "control that can fail: A = 2^-13 exactly, every rule agrees on f32(A)")
    for nm, dz, dx in B1_RAMPS:
        job(nm, dz, dx, "heldout", f"ramp dz = {dz:g}, dx = {dx}: separates the nine rules")
        if nm == "g-r2":
            job("g-r2-rep", dz, dx, "replicate", "replicate of g-r2: identical dump sha256", cond="g-r2")
    head = """B1 (pixel): Q288, which rule gives the effective depth gradient (binade 0, B = 0).
Jobs: tri --tri-v --tri-z --depth --depth-dump on 1024 x 32 (two tile rows, 32 tile columns), z0 = 0.5.
The depth control word's pitch field g = 31 and the buffer pages (48) follow tri1141.py's depth_args
for this width (the proposal says --depth-pages 40, fine too).  Frozen: the float32 word of the
gradient under each rule per ramp; scorer score/score_s1.py p-b1 (row fit as depth_drift.py grad_bounds).
FIT: E731's dp-bx-b0 (A = 1/6400 -> 0x3923d700), which nine rules agree with.  HELD OUT: g-r2..g-r13.
g-dyadic is the control that can fail.  The proposal's 'dx > 1024' does not hold for its own ramps
(dx 400..900): the triangle covers about dx pixels of a 1024-pixel row (PREFLIGHT.md)."""
    return rows, preds, [], head


# ------------------------------------------------------------------------------------------ C
C_BASE = ('probe --tri pixel --temps 32 --pixels --dump-render "$W/dump" --width 64 --height 64 --vtx-coords 2 '
          '--blk 4=0x00030001 --slot pixpds="$S/pds_iter_xy.bin:12" --slot vtxuse="$S/vtx_coords.bin" '
          '"$S/{prog}.bin"')


def c_program(cfg, ax, m):
    """E709's shader with o1 guarded by complementary predicates (the second written is tag 2 = p1 true)."""
    pa = "pa0" if ax == "x" else "pa1"
    t = lambda j: f"#0x{m * 16 + j:x}"
    ops = ["phas #0, #0, pixel, end, parallel", f"or.skipinv o0, {pa}, {t(1)}"]
    test = {"k0": "xor.testtaz.chan0 !c0, p1, g25, #0", "k3": "xor.testtaz.chan0 !c0, p1, g25, #3",
            "k7": "xor.testtaz.chan0 !c0, p1, g25, #7", "g23": "and.testtanz.chan0 !c0, p1, g23, #16"}.get(cfg)
    if test:
        ops += [test, f"!p1 or.skipinv o1, {pa}, {t(12)}", f"p1 or.skipinv o1, {pa}, {t(2)}"]
    else:                                                       # unpredicated: the second write wins
        ops += [f"or.skipinv o1, {pa}, {t(12)}", f"or.skipinv o1, {pa}, {t(2)}"]
    ops += [f"or.skipinv o2, {pa}, {t(3)}", f"or.skipinv o3, {pa}, {t(4)}"]
    ops += [f"p1 or.skipinv o4, {pa}, {t(5)}" if test else f"or.skipinv o4, {pa}, {t(5)}"]
    ops += [f"or.skipinv o5, {pa}, {t(6)}", f"or.skipinv o6, {pa}, {t(7)}", f"or.skipinv.end o7, {pa}, {t(8)}"]
    return "\n".join(ops) + "\n"


def p_c():
    rows, preds, needs = [], [], []
    markers = {}

    def build(name, text):
        out = BINS / f"{name}.bin"
        probe._assemble(text, out)
        needs.append(f"$S/{name}.bin")

    # pds_iter_xy / vtx_coords: the usse template pair E570 used (the p1134 stage's copy is not checkable)
    probe._assemble((REPO / "probes/usse/templates/pds_iter_xy.s").read_text(), BINS / "pds_iter_xy.bin", "pds")
    probe._assemble((REPO / "probes/usse/templates/vtx_coords.s").read_text(), BINS / "vtx_coords.bin")
    needs += ["$S/pds_iter_xy.bin", "$S/vtx_coords.bin"]
    # c-e709: E709's own programs (a copy from the verification dataset, byte for byte)
    PD = DATA / "vdm/verification-1141ta/programs"
    for ax in "xy":
        src = (PD / f"o4g-3-{ax}.s").read_text()
        probe._assemble(src, BINS / f"s1c-e709-{ax}.bin")
        needs.append(f"$S/s1c-e709-{ax}.bin")
    plan = [("c-e709", "e709", "control", "control: E709's o4g-3 unchanged (17 to 29 tag-5 pairs)"),
            ("c-u", "u", "control", "control for order: both writes unpredicated, the second (tag 2) wins"),
            ("c-k7", "k7", "heldout", "guard that cannot hold: g25 is a lane id 0..3, never 7"),
            ("c-k0", "k0", "heldout", "g25 == 0"), ("c-k3", "k3", "heldout", "g25 == 3"),
            ("c-g23", "g23", "heldout", "and.testtanz g23 & 0x10")]
    m = 0x210
    for nm, cfg, st, role in plan:
        for ax in "xy":
            m += 1
            jn = f"{nm}-{ax}"
            if cfg == "e709":
                prog = f"s1c-e709-{ax}"
            else:
                prog = f"s1c-{cfg}-{ax}"
                build(prog, c_program(cfg, ax, m))
            markers[jn] = m
            rows.append(Row(jn, st, "safe", "-", "stophang", "-", C_BASE.format(prog=prog), role, jn))
            if cfg == "e709":
                preds.append((jn, "tag5_pairs", "17-29", "E709", st))
            elif cfg == "u":
                for h in ("HP", "HA", "HN"):
                    preds.append((jn, "frac_tag2_of_o1", "1.0", h, st))
            elif cfg == "k7":
                preds += [(jn, "frac_tag2_of_o1", "0.0", "HP", st), (jn, "frac_tag2_of_o1", "0.0", "HA", st),
                          (jn, "frac_tag2_of_o1", "1.0", "HN", st)]
            elif cfg in ("k0", "k3"):
                preds += [(jn, "frac_tag2_of_o1", "0.25", "HP", st), (jn, "frac_tag2_of_o1", "0|1", "HA", st),
                          (jn, "frac_tag2_of_o1", "1.0", "HN", st)]
            else:
                preds += [(jn, "frac_tag2_of_o1", "0.5", "HP", st), (jn, "frac_tag2_of_o1", "0|1", "HA", st),
                          (jn, "frac_tag2_of_o1", "1.0", "HN", st)]
        if nm == "c-k7":
            m += 1
            jn = "c-k7-x-rep"
            prog = "s1c-k7-x"
            rows.append(Row(jn, "replicate", "safe", "-", "stophang", "-", C_BASE.format(prog=prog),
                            "replicate of c-k7-x (same program: identical job)", "c-k7-x"))
            preds.append((jn, "frac_tag2_of_o1", "same as c-k7-x", "repeat", "replicate"))
    (BINS / "c-markers.tsv").write_text("".join(f"{k}\t{v}\n" for k, v in markers.items()))
    # controls first
    rows = [r for r in rows if r.set == "control"] + [r for r in rows if r.set != "control"]
    head = """C (pixel): Q276, a guard that cannot hold.  E709's o4 guard is replaced by complementary
predicated writes of o1: tag 2 (marker*16 + 2) under p1, tag 2' (+0xc) under !p1.  The `!p1` write
is placed FIRST and the `p1` write second, so that if no gating exists (HN) both land and tag 2 wins
(the proposal listed the p1 write first, which makes HN predict tag 2' and indistinguishable from
HP/HA at K = 7: PREFLIGHT.md).  Every configuration runs as an x job and a y job (source pixel
identity needs the pair, as E709; the proposal's job list had x/y only for k7: 13 jobs, not 9).
o1 lands in the previous tile's region (E570): the scorer maps destination to source through the
pair.  Premise to confirm from E570 before reading: o1 lands for every source pixel."""
    return rows, preds, needs, head


# ------------------------------------------------------------------------------------------ G
LOD_UNITS = 64.0


def g_ladder(n, pitch=1 / 2048.0):
    """op0(col) linear in the column so that LOD*64 crosses the integer n at column 32 with `pitch` of
    a 1/64 step per column: op0 = (1 + col/64) K + C (the SETUP's fmad), LOD = log2(op0 * 64)."""
    op32 = 2.0 ** (n / LOD_UNITS) / 64.0
    slope = op32 * math.log(2) / LOD_UNITS * pitch            # d op0 / d col
    K = f32r(64 * slope)
    C = f32r(op32 - 1.5 * K)
    cols = []
    for col in range(64):
        op = (1 + col / 64) * K + C                            # exact product, float64
        cols.append(math.log2(op * 64) * LOD_UNITS)
    first = next((c for c, v in enumerate(cols) if v >= n), None)
    return K, C, cols, first


def p_g():
    pr = tomllib.loads((TEXD / "probes/p1141-lodg.toml").read_text())["probe"][0]
    labels = pr["labels"]
    ctl_text = pr["cases"][labels.index("lf-r8")]
    rows, preds, needs = [], [], []
    src = REPO / "probes/texture/templates"
    base = dict(name="s1g", question="s1", source="tx_map.s", coords=True, pixels=True, params={},
                inputs=["PRE", "SETUP", "SMP"])

    def build(name, case):
        p = probe._probe({**base, "name": name, "cases": [case]}, "s1-g.toml")
        probe.build(p, BINS, src)
        needs.append(f"$S/{name}__0.bin")
        return f"probe --temps 32 --coords --pixels \"$S/{name}__0.bin\""

    # control: E721's lf-r8 byte for byte
    cmd = build("s1g-ctl-lf-r8", ctl_text)
    ref = gzip.open(TEXD / "out-hw/p1141tex-dumps/tex-a-lod/lf-r8.txt.gz", "rt").read()
    rows.append(Row("g-ctl-lf-r8", "control", "safe", "-", "stophang", "-", cmd,
                    "control: E721's lf-r8 ladder unchanged (its image sha256 must reproduce)", "g-ctl-lf-r8"))
    vals = []
    for line in ref.splitlines():
        m = re.search(r"row (\d+): (.*)$", line)
        if m:
            vals += [v.rjust(8, "0") for v in m.group(2).split()]
    import hashlib
    preds.append(("g-ctl-lf-r8", "pix_sha256", hashlib.sha256(",".join(vals).encode()).hexdigest(), "E721 run", "control"))
    setup = ctl_text[1]
    for n in (13, 22, 56, 2):
        K, C, cols, first = g_ladder(n)
        text = [ctl_text[0], "\n".join(
            ["mov.skipinv r24, #0x3fbf0000", "mov.skipinv r25, #0x3f810000",
             "and.skipinv r1, pa0, #0x3f", "shl.skipinv r1, r1, #17", "or.skipinv r1, r1, #0x3f800000",
             f"mov.skipinv r2, #0x{bits(K):08x}", f"mov.skipinv r3, #0x{bits(C):08x}",
             "fmad.skipinv r26, r1, r2, r3", "mov.skipinv r27, #0x00000000", "mov.skipinv r28, #0x00000000",
             "mov.skipinv r29, #0x00000000", "mov r20, #0x07fc0200", "mov r21, #0x0c03f03f",
             "mov r22, #0x5caf0000", "mov r23, #0x00800800"]), ctl_text[2]]
        for rep in ("", "-r2"):
            nm = f"g-s{n}{rep}"
            c = build(f"s1g-s{n}{rep}", text)
            rows.append(Row(nm, "heldout" if not rep else "replicate", "safe", "-", "stophang", "-", c,
                            f"fine ladder across LOD*64 = {n} (u, v constant): exact crossing at column {first}",
                            f"g-s{n}"))
            preds += [(nm, "exact_crossing_col", str(first), "H13: within +-40 columns of the exact column", "heldout"),
                      (nm, "ladder_pitch", "1/2048 of a 1/64 step per column", "design", "heldout"),
                      (nm, "K_C_words", f"0x{bits(K):08x},0x{bits(C):08x}", "design", "heldout")]
    head = """G (pixel): Q280, the footprint's precision.  One operand ramps so that LOD*64 crosses the integer
n (13, 22, 56, 2: the steps of the misses) at column 32, with a pitch of 1/2048 of a 1/64 step per
column.  The proposal's 1/4096 pitch spans only +-32 columns = +-0.0078 of a step, narrower than the
+-0.01 noise it wants to detect (+-40 columns), so the pitch is 1/2048 (+-0.0156 step).  u and v are
constants (so that only the LOD varies along the row; E721's lf-r ladders also ramped u).  Whether a
raw-dword point-sampled output changes at all with the LOD fraction is not shown by any record:
the control (E721's lf-r8, unchanged) and 'at least one transition per ladder' are the first checks.
Cases are rebuilt from the p1141 lodg SETUP text with K, C replaced; nothing here reads a result."""
    return rows, preds, needs, head


# ------------------------------------------------------------------------------------------ B2
def trunc32(v):
    w = v.astype(np.float32)
    up = w.astype(np.float64) > v
    w[up] = np.nextafter(w[up], np.float32(-np.inf))
    return w


def b2_jobs():
    Z = lambda z0, dz, ax: (z0, z0 + dz, z0) if ax == "x" else (z0, z0, z0 + dz)
    tri0 = ((0, 0), (512, 0), (0, 512))
    mv = lambda dx, dy: tuple((x + dx, y + dy) for x, y in tri0)
    return [
        ("d-ctl", "control", 256, 128, tri0, Z(0.125, 1 / 16, "x"), "control: dp-ax-b2 as run (7680 pixels at -1 ulp, 1536 at -2)"),
        ("d-shift", "heldout", 256, 128, mv(64, 32), Z(0.125, 1 / 16, "x"), "triangle moved by (64, 32): HT region fixed, HV moves"),
        ("d-tall", "heldout", 256, 512, tri0, Z(0.125, 1 / 16, "x"), "dyadic A, B = 0 on 256 x 512: HT grows per tile row"),
        ("d-b3", "heldout", 256, 128, tri0, Z(0.0625, 1 / 16, "x"), "binade 3 (z0 = 0.0625): more, larger deviations"),
        ("d-ygrad", "heldout", 256, 512, tri0, Z(0.125, 1 / 16, "y"), "dyadic B, A = 0 on 256 x 512: HV rotates with the gradient"),
    ]


def p_b2():
    rows, preds = [], []
    for nm, st, w, h, V, Zs, role in b2_jobs():
        rows.append(Row(nm, st, "safe", "-", "stophang", "-", tri_depth_cmd(w, h, V, Zs), role, nm))
    # frozen reading of d-ctl from the E731 dump (dp-ax-b2): the deviation map and its boundary line
    sys_path = str(REPO / "tools/usse-asm")
    from b2model import ctl_model
    preds += ctl_model(rows)
    head = """B2 (pixel): Q200 second term, the lower-binade deviation of a dyadic plane.  d-ctl reproduces dp-ax-b2
(E731) first.  Scorer: stored - trunc32(exact) in ulps per pixel; the map of non-zero pixels; frozen
predictions are the region under HT (target-tied: the d-ctl map, in target coordinates) and under HV
(vertex-tied: the d-ctl map translated by (64, 32)), the boundary line fitted on d-ctl's data, written
before the run (predictions/p-b2.tsv + p-b2-set-*.bits).  d-tall / d-ygrad / d-b3 carry qualitative
frozen predictions only (counts per tile row, orientation).  The rule for the term is not expected
to close here (the proposal says so): this maps the region."""
    return rows, preds, [], head


# ------------------------------------------------------------------------------------------ D
def p_d():
    pr = tomllib.loads((TEXD / "probes/p1141-addr.toml").read_text())["probe"][0]
    labels = pr["labels"]
    cj = {c["name"]: c for c in json.load(open(TEXD / "gen/cases.json"))}
    src = REPO / "probes/texture/templates"
    rows, preds, needs = [], [], []
    base = dict(name="s1d", question="s1", source="tx_map.s", coords=True, pixels=True, params={},
                inputs=["PRE", "SETUP", "SMP"])
    built = {}

    def build(label):
        if label not in built:
            nm = "s1d-" + label.replace("ad-", "")
            p = probe._probe({**base, "name": nm.lower(), "cases": [pr["cases"][labels.index(label)]]}, "s1-d.toml")
            probe.build(p, BINS, src)
            built[label] = p.name
            needs.append(f"$S/{p.name}__0.bin")
        return built[label]

    def job(nm, label, pages, st, role, knobs, outcome):
        b = build(label)
        extra = f" --scratch-pages {pages}" if pages != 16 else ""
        rows.append(Row(nm, st, "risky" if "expectfault" in knobs else "safe", "-", knobs, "-",
                        f'probe --temps 32 --coords --pixels{extra} "$S/{b}__0.bin"', role, nm))
        preds.append((nm, "scratch_line", f"({pages * 4} KiB)", "knob", st))
        a4 = cj[label]["preds"]["A4"]
        for m, v in (("HB", outcome[0]), ("HX", outcome[1])):
            preds.append((nm, "outcome", v, m, st))
        preds.append((nm, "pix_sha256_if_complete", a4, "A4 (frozen with E722's cases.json)", st))
    job("d-ok-64", "ad-tw128x32-L0e2", 64, "control", "control: E722's passing case at 64 pages (extent 0x10000)",
        "stophang", ("complete", "complete"))
    HX = "hypo:hx:4"      # HX (another limit: a fault at 64 pages) is a stated hypothesis: measured, not a stop
    job("d-L2e2-64", "ad-tw64x64-L2e2", 64, "heldout", "extent 84 KiB, E722 faulted at 16 pages", HX,
        ("complete", "fault"))
    job("d-L3e3-64", "ad-tw64x64-L3e3", 64, "heldout", "extent 85 KiB", HX, ("complete", "fault"))
    job("d-st-L3e2-64", "ad-st128x32-L3e2", 64, "heldout", "extent 170 KiB (strided)", HX,
        ("complete", "fault"))
    job("d-L2e2-21", "ad-tw64x64-L2e2", 21, "heldout", "scratch = 84 KiB = the extent: the boundary", HX,
        ("complete", "?"))
    job("d-L2e2-20", "ad-tw64x64-L2e2", 20, "heldout", "scratch 80 KiB < the extent: faults 0x90002",
        "expectfault", ("fault", "fault"))
    job("d-L2e2-16", "ad-tw64x64-L2e2", 16, "control", "control: E722's job unchanged (faults 0x90002); last",
        "expectfault", ("fault", "fault"))
    # d-L2e2-16 (E722's fault reproduction) stays last: nothing in the stage depends on it (the knob proof is the
    # scratch line); only d-ok-64 leads
    head = """D (pixel): Q281, the 64 KiB scratch.  Texture base = the scratch buffer; probe --scratch-pages N
(16 to 64) enlarges it.  The three extents that faulted at 16 pages (84, 85, 170 KiB) fit in 64.
The probe fills the scratch with 0xD0000000 | i, so a read past the texture's own bytes returns the
dword index: the A4 image hash of E722's frozen cases.json is the prediction under HB.  Knob proof:
the probe's 'scratch at ... (N KiB)' line must say N = pages x 4.  Fit: none (E722's 13 of 16 fit
cases are the model; these are held out).  The two faulting jobs run last."""
    return rows, preds, needs, head


# ------------------------------------------------------------------------------------------ F
def p_f():
    rows, preds = [], []

    def job(nm, mask, st, role, n=2, extra="", P="-", runs=2, fault=False):
        for r in range(1, runs + 1):
            name = f"{nm}-r{r}"
            kn = f"alias_skip={mask}" + (" expectfault" if fault else f" hypo:{nm}:2")   # HJ: a fault is measured
            rows.append(Row(name, st if r == 1 else "replicate", "risky" if fault else "safe", P, kn, "-",
                            f"tri -n {n} --keep-going --wait-ms 6000{extra}", role, nm))
            preds.append((name, "outcome", "fault 0x91000" if fault else "exact", "HI" if not fault else "E573", st))
            if not fault:
                preds.append((name, "outcome", "fault", "HJ", st))
    for nm, mask, role in (("f-12", "0x6", "buffers 1 and 2"), ("f-13", "0xa", "buffers 1 and 3"),
                           ("f-23", "0xc", "buffers 2 and 3"), ("f-45", "0x30", "buffers 4 and 5"),
                           ("f-15", "0x22", "buffers 1 and 5"), ("f-all15", "0x3e", "buffers 1 to 5 together")):
        job(nm, mask, "heldout", f"{role} left out: HI exact, HJ a pair faults")
    job("f-3r", "0xdc0", "heldout", "three renders, buffers 6, 7, 8, 10, 11 left out", n=3)
    for mask in ("0xdc0", "0x1f"):
        job(f"f-dpm-{mask[2:]}", mask, "heldout", f"1024x768 partial renders (0x23 pages), mask {mask}", n=2,
            extra=" --width 1024 --height 768 --keep-overflow", P="0x23")
    job("f-ctl0", "0x1", "control", "control: buffer 0 alone left out faults 0x91000 at 0x3000b0xx (E573); last",
        fault=True)
    head = """F (pixel): Q076, the remaining pages, with debugfs alias_skip (a mask of firmware buffer ids,
bits 16 to 31 refused; applies to render VMs created after the write; a reset leaves it alone).
tri -n 2 --keep-going as E573/E592 ran it; each condition twice (the proposal's '11 jobs (2 repeats
each)' is 9 conditions = 20 jobs with f-dpm's two masks).  A fault in a pair job is HJ, a stated
hypothesis: measured (knob hypo:COND:2), not a stop.  f-ctl0 reproduces E573 and faults by design
(reset + health after); it is last: nothing depends on it, the knob proof is the read-back marker.  The mask is written, read back and marked in the kernel log
before each job and put back to 0 after it.  Buffer 9 is the TA3D control block (never masked here).
f-dpm uses --keep-overflow (a partial render's ENOSPC is not a failure); P = 0x23."""
    return rows, preds, [], head
