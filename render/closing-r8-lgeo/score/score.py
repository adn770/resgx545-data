#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r8-lgeo's scorer, frozen before the run. Every verdict rule comes from kit/scorekit.py
(headline, gate, tally, combine), the kept files are read through kit/kitscore.py (byte copies of
resgx545 91f21da, pinned in FROZEN.commits); the models' frozen outputs are predictions/ (written
by gen/lgen.py), the readers gen/texmodel.py, gen/zsmodel.py (pure functions) and score/lib_dump.py
with its byte copies (resgx545-data render/closing-r7-rp/score, pinned). Standard library only.

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL and ROW lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage of r8-lgeo is gated by another's controls)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Row states: held (True), FAILED (False), cannot tell (None). A job whose kept class is not ok
(rc 0, or rc 1 with its diff line: expectdiff), a void (soft) row, an output without its whole image or dump, is cannot tell,
never a pass. Every stage's controls gate every row of the stage (scorekit.headline).

tx3, tx4, tx5 (Q283, Q178): the 64 x 32 probe image (2048 dwords of `probe NAME: row N:` lines)
against each hypothesis's frozen pixels_sha; a control passes iff its image is the kept one; a row
whose `scratch at ... (N KiB)` line is not the frozen size cannot tell. tx4's two linear rows are
cannot tell unless their bridge (type 3 32 x 16 through the linear axis) gave E725's image. tx5's
explore rows print their values only.
zs2 (Q260): the covered image (0xff00ff00 pixels of `row Y:` lines) against the frozen spans of HA
and HU (predictions/zs2/NAME.VAR.spans); per sweep (five steps) the aimed pixel's states against
HA's and HU's; H-SHORT on rows whose longest edge is below 250 pixels (exact HA), H-BAND on the
others (every pixel off HA's image within 6.4e-4 pixel of an edge of 250 pixels or more), H-YAXIS
and H-GEOM on the 256 x 512 rows that miss HA's image (target y sweep, target x sweep).
q139 (Q139): the wrong-tile set of the --pixels image (lib_dump.image_tiles) and the header slots
of the dump (lib_dump.observed_slots, from the baseline's header base) against each order's frozen
set and slots (predictions/q139/NAME.ORDER.slots); a row holds for an order iff both agree."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402
import texmodel as T  # noqa: E402
import zsmodel as Z  # noqa: E402
import lib_dump as L  # noqa: E402

FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {"tx3": (".txt",) + FIXED, "tx4": (".txt",) + FIXED, "tx5": (".txt",) + FIXED,
            "zs2": (".txt",) + FIXED, "q139": (".txt", ".tri.param.bin", ".tri.tadata.bin") + FIXED}
GATES = {}
ORDERS = ("blkrow", "raster", "blkdown", "mtblk")


def producible(row):
    a = row["args"]
    if a.startswith("probe"):
        return {"rows"}
    keys = {"hash"}
    if "--dump-render" in a:
        keys.add("dump")
    return keys


def word(s):
    return "held" if s is True else "FAILED" if s is False else "cannot tell"


def cword(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n in cases:
        K.text(d, n + ".txt")
        if stage == "q139":
            L.read_bytes(os.path.join(d, n + ".tri.param.bin"))
            L.read_bytes(os.path.join(d, n + ".tri.tadata.bin"))


def done(cases, n):
    return n in cases and cases[n]["class"] == "ok"


def one(P, n, q, m):
    return P.get(n, {}).get(q, {}).get(m)


# ================================================================================ textures
def tex_reading(d, cases, P, n):
    """(image or None, why)."""
    if not done(cases, n):
        return None, "not a completed job" if n in cases else "did not run (or void)"
    text = K.text(d, n + ".txt")
    want = one(P, n, "scratch", "all") or "64 KiB"
    m = re.search(r"^probe \S+: scratch at 0x[0-9a-f]+ \((\d+) KiB\)", text, re.M)
    if not m or "%s KiB" % m.group(1) != want:
        return None, "scratch %s, frozen %s" % (m.group(1) + " KiB" if m else "not printed", want)
    img = T.probe_rows(text)
    if len(img) != T.FW * T.FH:
        return None, "%d pixels, not 2048" % len(img)
    return img, "read"


def tex_controls(stage, d, cases, P, lines):
    ctl = {}
    for t in K.table(KP, stage):
        if t["set"] != "control":
            continue
        n = t["name"]
        img, why = tex_reading(d, cases, P, n)
        want = one(P, n, "pixels_sha", "kept")
        ctl[n] = None if img is None else T.sha_list(img) == want
        lines.append("CONTROL %s: %s (kept image %s...): %s" % (n, why, want[:12], cword(ctl[n])))
    return ctl


def tex_rows(stage, d, cases, P, sets, hyps, lines, only=None):
    """{hyp: [state per row]} over the table's rows of `sets`."""
    out = {h: [] for h in hyps}
    for t in K.table(KP, stage):
        n = t["name"]
        if t["set"] not in sets or (only and not only(t)):
            continue
        img, why = tex_reading(d, cases, P, n)
        sha = None if img is None else T.sha_list(img)
        got = []
        for h in hyps:
            want = one(P, n, "pixels_sha", h)
            s = None if sha is None or want is None else sha == want
            out[h].append(s)
            if s:
                got.append(h)
        lines.append("ROW %s (%s): %s; matches %s" % (n, t["set"], why if img is None else "image read",
                                                     ",".join(got) or ("none" if img is not None else "-")))
    return out


def score_tx3(d):
    P, cases, lines = K.predictions(KP, "tx3"), K.rows(d), []
    ctl = tex_controls("tx3", d, cases, P, lines)
    t3 = tex_rows("tx3", d, cases, P, ("heldout",), ("H-MIN8", "H-2W", "RASTERW"), lines,
                  only=lambda t: one(P, t["name"], "type", "all") == "3")
    t1 = tex_rows("tx3", d, cases, P, ("heldout",), ("RASTERW", "H-MIN8", "H-2W"), lines,
                  only=lambda t: one(P, t["name"], "type", "all") == "1")
    out = lines + ["SUMMARY: Q283 type 3 below 8 wide: " + SK.headline("H-MIN8 (rows max(8, w) dwords apart) held",
                                                                        ctl, t3["H-MIN8"])]
    out += ["SUMMARY: Q283 type 3 rival: " + SK.headline("%s held" % h, ctl, t3[h]) for h in ("H-2W", "RASTERW")]
    out += ["SUMMARY: Q283 type 1 below 4 wide: " + SK.headline("RASTERW held", ctl, t1["RASTERW"])]
    out += ["SUMMARY: Q283 type 1 rival: " + SK.headline("%s held" % h, ctl, t1[h]) for h in ("H-MIN8", "H-2W")]
    return out


def score_tx4(d):
    P, cases, lines = K.predictions(KP, "tx4"), K.rows(d), []
    ctl = tex_controls("tx4", d, cases, P, lines)
    hy = ("H-BLKROW", "H-BLKCOL", "H-BLKZ")
    r = tex_rows("tx4", d, cases, P, ("heldout",), hy, lines, only=lambda t: "-lin-" not in t["name"])
    br = tex_rows("tx4", d, cases, P, ("bridge",), ("kept",), lines)["kept"]
    bridge = br[0] if br else None
    lines.append("BRIDGE tx4-lin-ty3-32x16 (the linear axis gives E725's map image): %s" % word(bridge))
    lin = tex_rows("tx4", d, cases, P, ("heldout",), ("RASTERW", "RASTERP2"), lines,
                   only=lambda t: "-lin-" in t["name"])
    if bridge is not True:
        lin = {h: [None] * len(v) for h, v in lin.items()}
    out = lines + ["SUMMARY: Q283 type 4 block order: " + SK.headline("H-BLKROW (32 x 32 blocks row by row) held", ctl,
                                                                     r["H-BLKROW"])]
    out += ["SUMMARY: Q283 type 4 rival: " + SK.headline("%s held" % h, ctl, r[h]) for h in hy[1:]]
    out += ["SUMMARY: Q283 type 3 at 24 and 40 wide (soft, bridge %s): " % word(bridge)
            + SK.headline("%s held" % h, ctl, lin[h]) for h in ("RASTERW", "RASTERP2")]
    return out


def score_tx5(d):
    P, cases, lines = K.predictions(KP, "tx5"), K.rows(d), []
    ctl = tex_controls("tx5", d, cases, P, lines)
    hy = ("H-DW8", "H-DW4B1")
    parted = lambda t: one(P, t["name"], "pixels_sha", "H-DW8") != one(P, t["name"], "pixels_sha", "H-DW4B1")  # noqa: E731
    r = tex_rows("tx5", d, cases, P, ("heldout",), hy, lines, only=parted)
    same = tex_rows("tx5", d, cases, P, ("heldout",), ("H-DW8",), lines, only=lambda t: not parted(t))["H-DW8"]
    ref, _ = tex_reading(d, cases, P, "tx5-ctl-16x16")
    for t in K.table(KP, "tx5"):
        if t["set"] != "explore":
            continue
        img, why = tex_reading(d, cases, P, t["name"])
        if img is None:
            lines.append("EXPLORE %s: %s" % (t["name"], why))
            continue
        vals = sorted(set(img))
        lines.append("EXPLORE %s: %d distinct values (%s%s); %s the plain 16 x 16 control's image" % (
            t["name"], len(vals), " ".join("%08x" % v for v in vals[:4]), " ..." if len(vals) > 4 else "",
            "equals" if ref is not None and img == ref else "differs from" if ref is not None else "no"))
    out = lines + ["SUMMARY: Q178 type 5 (rows where the two part): " + SK.headline(
        "H-DW8 (bit 0 of dword floor(t / 8)) held", ctl, r["H-DW8"])]
    out += ["SUMMARY: Q178 type 5 rival: " + SK.headline("H-DW4B1 (bit 1 of dword floor(t / 4)) held", ctl, r["H-DW4B1"])]
    out += ["SUMMARY: Q178 type 5 (rows where the two agree: the raster index, the high bits): " + SK.headline(
        "H-DW8 = H-DW4B1 held", ctl, same)]
    return out


# ================================================================================ zs2
def tri_image(text, w, h):
    """The covered x's of each row of a --pixels output ([sorted xs] per row), None unless whole."""
    rows = {}
    for m in re.finditer(r"^row (\d+): (.*)$", text, re.M):
        toks = m.group(2).split()
        if len(toks) != w:
            return None
        rows[int(m.group(1))] = [x for x, v in enumerate(toks) if v == "0xff00ff00"]
    if sorted(rows) != list(range(h)):
        return None
    return [rows[y] for y in range(h)]


def off_pixels(img, sp):
    out = []
    for y, (xs, (lo, hi)) in enumerate(zip(img, sp)):
        want = range(lo, hi) if hi > lo else range(0)
        if len(xs) == len(want) and (not xs or (xs[0] == want[0] and xs[-1] == want[-1])):
            continue
        a, b = set(xs), set(want)
        out += [(x, y) for x in sorted(a ^ b)]
    return out


def zs_args(t):
    toks = t["args"].split()
    return (int(toks[toks.index("--width") + 1]), int(toks[toks.index("--height") + 1]),
            [int(x) for x in toks[toks.index("--tri-v") + 1].split(",")])


def score_zs2(d):
    P, cases, lines = K.predictions(KP, "zs2"), K.rows(d), []
    ctl, rd = {}, {}
    for t in K.table(KP, "zs2"):
        n = t["name"]
        text = K.text(d, n + ".txt") if done(cases, n) else ""
        if t["set"] == "control":
            h = L.target_hash(text)
            want = one(P, n, "hash", "kept")
            ctl[n] = None if h is None else h == want
            lines.append("CONTROL %s: hash %s (kept %s): %s" % (n, h, want, cword(ctl[n])))
            continue
        w, hh, v = zs_args(t)
        img = tri_image(text, w, hh) if text else None
        r = dict(t=t, sweep=one(P, n, "sweep", "all"), axis=one(P, n, "target_axis", "all"), w=w, h=hh, v=v,
                 long=float(one(P, n, "longest_edge", "H-HA")) >= Z.LONG_PX)
        if img is None:
            r.update(read=False)
            lines.append("ROW %s: cannot tell (%s)" % (n, "no whole image" if text else "not a completed job"))
            rd[n] = r
            continue
        cx, cy = (int(x) for x in one(P, n, "aimed_px", "all").split(","))
        r.update(read=True, aimed=int(cx in img[cy]))
        for var in ("HA", "HU"):
            sp = Z.spans_parse(open(os.path.join(KP, "predictions/zs2/%s.%s.spans" % (n, var))).read(), hh)
            r["off_" + var] = off_pixels(img, sp)
        off = r["off_HA"]
        r["band"] = Z.in_band(v, "HA", off)
        lines.append("ROW %s: aimed pixel %d (HA %s, HU %s); off HA %d px%s, off HU %d px" % (
            n, r["aimed"], one(P, n, "aimed", "H-HA"), one(P, n, "aimed", "H-HU"), len(off),
            (" (all in E914's band)" if r["band"] else " (NOT all in the band)") if off else "", len(r["off_HU"])))
        rd[n] = r
    # per sweep: the aimed pixel's five states against HA's and HU's
    sweeps = {}
    for n, r in rd.items():
        sweeps.setdefault(r["sweep"], []).append(n)
    st = {"HA": {}, "HU": {}}
    for sw, names in sweeps.items():
        rs = [rd[n] for n in names]
        if not all(r["read"] for r in rs):
            for var in st:
                st[var][sw] = None
            lines.append("SWEEP %s: cannot tell (a step without its image)" % sw)
            continue
        obs = "".join(str(r["aimed"]) for r in rs)
        for var in st:
            st[var][sw] = obs == "".join(one(P, n, "aimed", "H-" + var) for n in names)
        lines.append("SWEEP %s: aimed pixel %s (HA %s, HU %s): HA %s, HU %s" % (
            sw, obs, "".join(one(P, n, "aimed", "H-HA") for n in names),
            "".join(one(P, n, "aimed", "H-HU") for n in names), word(st["HA"][sw]), word(st["HU"][sw])))
    g = [sw for sw in sweeps if sw.startswith("g ")]
    lt = [sw for sw in sweeps if not sw.startswith("g ")]
    out = lines + ["SUMMARY: Q260 negative ties at other grid points: " + SK.headline(
        "HA's step (the aimed pixel flips between d 0 and +1) held", ctl, [st["HA"][s] for s in g])]
    out.append("SUMMARY: Q260 rival at other grid points: " + SK.headline("HU's step held", ctl, [st["HU"][s] for s in g]))
    out.append("SUMMARY: Q260 long edges, E914's step table (d +1 negative, d 0 positive): " + SK.headline(
        "the step table held", ctl, [st["HA"][s] for s in lt]))
    short = [(not r["off_HA"]) if r["read"] else None for r in rd.values() if not r["long"]]
    band = [r["band"] if r["read"] else None for r in rd.values() if r["long"]]
    out.append("SUMMARY: Q260 H-SHORT: " + SK.headline("the image is HA's exactly where no edge reaches 250 pixels", ctl,
                                                        short))
    out.append("SUMMARY: Q260 H-BAND: " + SK.headline(
        "the image differs from HA's only within 6.4e-4 pixel of an edge of 250 pixels or more", ctl, band))
    miss = [r for r in rd.values() if r["read"] and r["off_HA"]]
    for wh in ((512, 256), (256, 512)):
        m = [r for r in miss if (r["w"], r["h"]) == wh]
        out.append("MISSES %dx%d: %d rows off HA's image: %d on target x sweeps, %d on target y sweeps" % (
            wh[0], wh[1], len(m), sum(r["axis"] == "x" for r in m), sum(r["axis"] == "y" for r in m)))
    tm = [r for r in miss if (r["w"], r["h"]) == (256, 512)]
    out.append("SUMMARY: Q260 which sweeps miss on 256 x 512: " + SK.headline(
        "H-YAXIS (on target y sweeps only) held", ctl, [r["axis"] == "y" for r in tm]))
    out.append("SUMMARY: Q260 rival on 256 x 512: " + SK.headline(
        "H-GEOM (the misses follow the transposed scene to target x) held", ctl, [r["axis"] == "x" for r in tm]))
    return out


# ================================================================================ q139
def q139_job(d, cases, n):
    if not done(cases, n):
        return None, "not a completed job" if n in cases else "did not run"
    j = dict(text=K.text(d, n + ".txt"), param=L.read_bytes(os.path.join(d, n + ".tri.param.bin")),
             tadata=L.read_bytes(os.path.join(d, n + ".tri.tadata.bin")))
    if not j["tadata"] or not j["param"]:
        return None, "no dump"
    return j, "read"


def slots_of(n, order):
    import q139model as Q
    return Q.slots_parse(open(os.path.join(KP, "predictions/q139/%s.%s.slots" % (n, order))).read().strip())


def slot_agree(pred, obs):
    return sum(1 for t, v in pred.items() if (v is None and not obs.get(t)) or (v is not None and v in obs.get(t, [])))


def score_q139(d):
    P, cases, lines = K.predictions(KP, "q139"), K.rows(d), []
    tab = K.table(KP, "q139")
    size = {t["name"]: tuple(int(x) for x in one(P, t["name"], "size", "all").split("x")) for t in tab}
    ctl, lay = {}, {}
    for t in tab:
        n = t["name"]
        if t["set"] != "control":
            continue
        w, h = size[n]
        j, why = q139_job(d, cases, n)
        if j is None:
            ctl[n] = None
            lines.append("CONTROL %s: cannot tell (%s)" % (n, why))
            continue
        complete, bad = L.image_tiles(j["text"], w, h)
        kept = one(P, n, "wrong", "kept")
        if kept is None:                        # a baseline: exact image, one header a tile, R7-BLK's slots
            ok, txt, ly = L.baseline_layout(j["tadata"], j["param"], w, h)
            pred = slots_of(n, "blkrow")
            agree = sum(1 for tl, v in pred.items() if ly and ly["slot"].get(tl) == v)
            ctl[n] = complete and not bad and ok and agree == len(pred)
            if ok:
                lay[(w, h)] = ly
            lines.append("CONTROL %s: image %s, %d wrong tiles; %s; slots as R7-BLK %d of %d: %s" % (
                n, "complete" if complete else "INCOMPLETE", len(bad), txt, agree, len(pred), cword(ctl[n])))
        else:
            ctl[n] = (L.tiles_text(bad) == kept) if complete else None
            lines.append("CONTROL %s: %d wrong tiles (kept %d): %s" % (n, len(bad), len(L.tiles_parse(kept)), cword(ctl[n])))
    states = {o: [] for o in ORDERS}
    for t in tab:
        n, sset = t["name"], t["set"]
        if sset == "control":
            continue
        w, h = size[n]
        j, why = q139_job(d, cases, n)
        comp = None
        if j is not None:
            comp, bad = L.image_tiles(j["text"], w, h)
        if j is None or not comp or (w, h) not in lay and sset == "heldout":
            for o in ORDERS:
                if sset == "heldout":
                    states[o].append(None)
            lines.append("ROW %s (%s): cannot tell (%s)" % (n, sset, why if j is None else "image not whole" if not comp
                                                           else "no baseline layout of %dx%d" % (w, h)))
            continue
        obs = L.observed_slots(j["tadata"], lay[(w, h)]["base"], w, h) if (w, h) in lay else None
        parts = []
        for o in ORDERS:
            ws = one(P, n, "wrong", o)
            same = L.tiles_text(bad) == ws
            pred = slots_of(n, o)
            ag = slot_agree(pred, obs) if obs is not None else None
            s = same and ag == len(pred)
            if sset == "heldout":
                states[o].append(s)
            parts.append("%s %s (wrong %s, slots %s of %d)" % (o, "yes" if s else "no", "=" if same else "differs",
                                                               "-" if ag is None else ag, len(pred)))
        kept = one(P, n, "wrong", "kept")
        rep = "" if kept is None else "; the dataset's image %s" % ("replicated" if L.tiles_text(bad) == kept else "NOT replicated")
        lines.append("ROW %s (%s): %d wrong tiles%s; %s" % (n, sset, len(bad), rep, "; ".join(parts)))
    out = lines + ["SUMMARY: Q139 write order on the held-out strides: " + SK.headline(
        "block order (blkrow) predicts the wrong-tile sets and every header slot", ctl, states["blkrow"])]
    out += ["SUMMARY: Q139 rival: " + SK.headline("%s held" % o, ctl, states[o]) for o in ORDERS[1:]]
    return out


SCORERS = {"tx3": score_tx3, "tx4": score_tx4, "tx5": score_tx5, "zs2": score_zs2, "q139": score_q139}


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        print("\n".join(SCORERS[argv[1]](argv[2])))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
