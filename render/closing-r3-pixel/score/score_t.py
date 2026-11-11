# SPDX-License-Identifier: MIT
"""Scorer of q-t (Q082 pixel side: occupancy with the working triangle loop).  Written before the run; frozen with the
predictions.

Every row: STATUS2 after the reset (0x400) and after the job, the loop proof (o0 = MARK on W x H of W x H for the full
triangles: else VOID), the burst and t6.  Controls: the stock green full triangle at seven sizes (o0 = 0xff00ff00 on W x H),
the loop at N = 1 at seven sizes (a size failing it is void), the 64x32 bridge (53 clear, 56 set).  Ladders: the first N with the
bit set per size, compared with the frozen first-set points of H-INST (per instance, incl. H-MA), H-TILE (per 32x16 tile, incl. H-WD)
and H-JOB (r3const.T_FIRST), scaled by the measured 64x32 first set / 56 (the bridge failing is reported).  H-WD adds t6 in
[120, 340] us at every size where the bit sets well above its threshold."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import re  # noqa: E402

import r3const as C  # noqa: E402
import r3lib as L  # noqa: E402
from r3job import job  # noqa: E402

LAD = re.compile(r"t-(\d+)x(\d+)-n(\d+)$")
GREEN = 0xff00ff00


def mark(n):
    return 0xC0DE0000 | n


def collect(k):
    """{'green': {size: rec}, 'n1': {size: rec}, 'bridge': {N: rec}, 'lad': {size: {N: rec}}, 'par': {N: rec}, 'x4': {N: rec}}"""
    d = {"green": {}, "n1": {}, "bridge": {}, "lad": {}, "par": {}, "x4": {}}
    for n in k.names():
        m = re.fullmatch(r"t-ctl-green-(\d+)x(\d+)", n)
        if m:
            w, h = int(m[1]), int(m[2])
            j = job(k, n)
            o = j["o0"]
            j["proof"] = bool(o and o[0] == "same" and o[1] == GREEN and o[2] == w * h == o[3])
            d["green"][(w, h)] = j
            continue
        m = re.fullmatch(r"t-ctl-n1-(\d+)x(\d+)", n)
        if m:
            w, h = int(m[1]), int(m[2])
            d["n1"][(w, h)] = job(k, n, mark=mark(1), count=w * h)
            continue
        m = re.fullmatch(r"t-bridge-64x32-n(\d+)", n)
        if m:
            d["bridge"][int(m[1])] = job(k, n, mark=mark(int(m[1])), count=2048)
            continue
        m = re.fullmatch(r"t-par-64x64-n(\d+)", n)
        if m:
            d["par"][int(m[1])] = job(k, n)
            continue
        m = re.fullmatch(r"t-4x4-n(\d+)", n)
        if m:
            d["x4"][int(m[1])] = job(k, n, mark=mark(int(m[1])), count=16)
            continue
        m = LAD.match(n)
        if m:
            w, h, N = int(m[1]), int(m[2]), int(m[3])
            d["lad"].setdefault((w, h), {})[N] = job(k, n, mark=mark(N), count=w * h)
    return d


def ok(j):
    return j is not None and not j["void"] and j["bit6"] is not None and j["proof"] is True


def first_set(lad):
    """(first N with the bit set among usable rows, last clear below it, monotone?)"""
    pts = sorted((N, j["bit6"]) for N, j in lad.items() if ok(j))
    fs = next((N for N, b in pts if b), None)
    lc = max((N for N, b in pts if not b and (fs is None or N < fs)), default=None)
    mono = all(not (a[1] and not b[1]) for a, b in zip(pts, pts[1:]))
    return fs, lc, mono, pts


def evaluate(d):
    """(lines, verdict dict, info)"""
    lines = []
    ctl_bad = []
    for size in C.T_SIZES:
        g, n1 = d["green"].get(size), d["n1"].get(size)
        if g is None or g["void"] or g["proof"] is not True or g["bit6"]:
            ctl_bad.append(f"green {size[0]}x{size[1]}")
        if not ok(n1) or n1["bit6"]:
            ctl_bad.append(f"n1 {size[0]}x{size[1]}")
    void_sizes = {size for size in C.T_SIZES if not ok(d["n1"].get(size))}
    br = {N: d["bridge"].get(N) for N in (53, 56)}
    bridge_ok = ok(br[53]) and ok(br[56]) and not br[53]["bit6"] and br[56]["bit6"]
    lines.append("bridge (64x32 at N = 53, 56; the fill's threshold: clear, set): "
                 + ("ok" if bridge_ok else "FAILED or void: " + str({N: (None if j is None else (j["void"] or j["bit6"])) for N, j in br.items()})))
    fs64 = first_set(d["lad"].get((64, 32), {}))[0] if (64, 32) in d["lad"] else None
    ref = fs64 if fs64 is not None else 56
    lines.append(f"reference first set at 64x32 (the ladder): {fs64}; cells scale by {ref} / 56")
    verdict = {h: [] for h in ("H-INST", "H-TILE", "H-JOB")}
    tab = []
    for size in C.T_SIZES:
        lad = d["lad"].get(size)
        if lad is None or size in void_sizes:
            tab.append((f"{size[0]}x{size[1]}", "void: the N = 1 loop control failed or not run" if lad is not None else "not run", "-", "-", "-", "-"))
            continue
        fs, lc, mono, pts = first_set(lad)
        usable_n = sorted(N for N, j in lad.items() if ok(j))
        cells = []
        for h in ("H-INST", "H-TILE", "H-JOB"):
            allowed = C.t_allowed(h, size, ref, ladder=sorted(lad))
            good = (fs in allowed) or (fs is None and None in allowed)
            # a size whose allowed point is not on the usable ladder (a row void) cannot be decided: decided only if every
            # allowed point lies outside (last clear, first set] or is a usable row (post-run fix C1, POSTRUN-FIX.md)
            decided = (None in allowed) or all((lc is not None and a <= lc) or (fs is not None and a > fs) or a in usable_n
                                               for a in allowed if a is not None)
            verdict[h].append((size, fs, allowed, good, decided, mono))
            cells.append(("ok" if good else "MISS") + ("" if decided else "?"))
        tab.append((f"{size[0]}x{size[1]}", "never set" if fs is None else fs, lc if lc is not None else "-", "yes" if mono else "NO", *cells))
    lines.append(L.table(tab, ["size", "first set N", "last clear", "monotone", "H-INST", "H-TILE", "H-JOB"]))
    # H-WD: the latch time at sizes where the bit sets well above its threshold
    n = hit = 0
    for size, lad in d["lad"].items():
        fs, _, _, _ = first_set(lad)
        if fs is None or size in void_sizes:
            continue
        for N, j in lad.items():
            if ok(j) and j["bit6"] and N >= C.LONG_FACTOR * fs and j["t6"] is not None:
                n += 1
                hit += C.T6_LO <= j["t6"] <= C.T6_HI
    lines.append(f"H-WD: t6 in [{C.T6_LO:.0f}, {C.T6_HI:.0f}] us in {hit} of {n} jobs set at N >= 1.3 x the size's first set")
    # the 4x4 rows: H-INST says set from 56; H-TILE and H-JOB clear
    x4 = d["x4"]
    x4_inst = [(N, x4[N]["bit6"]) for N in sorted(x4) if ok(x4[N])]
    for h, want in (("H-INST", True), ("H-TILE", False), ("H-JOB", False)):
        for N, b in x4_inst:
            verdict[h].append(((4, 4), N, ["set" if want else "clear"], b == want, True, True))
    lines.append("4x4 (16 pixels) at N = 56, 220, 880: " + (", ".join(f"{N} {'set' if b else 'clear'}" for N, b in x4_inst) or "not run"))
    par = d["par"]
    for N in sorted(par):
        j = par[N]
        lines.append(f"exploratory, default triangle 64x64 N = {N}: " + (j["void"] or f"bit 6 {'set' if j['bit6'] else 'clear'}, o0 {j['o0'][:2] if j['o0'] else '-'}"))
    return lines, verdict, dict(ctl_bad=ctl_bad, bridge_ok=bridge_ok, ref=ref, void_sizes=sorted(void_sizes))


def score_t(k, preds):
    d = collect(k)
    lines, verdict, info = evaluate(d)
    out = ["q-t: bridge, ladders, 4x4 (first N with bit 6 set per size; MISS = outside the hypothesis' frozen allowed points)"] + lines + [""]
    if info["ctl_bad"]:
        out.append("controls failed or void: " + str(info["ctl_bad"]) + " (a size whose N = 1 loop control failed is void; the others stand)")
    parts = []
    for h, rows in verdict.items():
        miss = [(s, fs) for s, fs, al, good, dec, mono in rows if not good and dec]
        und = [s for s, fs, al, good, dec, mono in rows if not dec]
        parts.append(f"{h} " + ("REFUTED at " + ",".join(f"{s[0]}x{s[1]}" for s, _ in miss) if miss else f"holds at {len(rows)} sizes" + (f" ({len(und)} undecided)" if und else "")))
    out.append("SUMMARY: q-t: " + "; ".join(parts) + f"; bridge {'ok' if info['bridge_ok'] else 'FAILED'}; reference N {info['ref']}; "
               f"void sizes {info['void_sizes']}; control problems {info['ctl_bad'] or 'none'}")
    return "\n".join(out), {"verdict": verdict, **info}
