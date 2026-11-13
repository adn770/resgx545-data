#!/usr/bin/env python3
"""hflag_score.py: scores the frozen rules of hflag_rule.json on a kept q139 directory.
Usage: python -I hflag_score.py KEPT_DIR [cases-file]   (reads cases.tsv and NAME.txt.gz,
NAME.tri.param.bin.gz, NAME.tri.tadata.bin.gz).  Readers copied into lib/ from
resgx545-data render/closing-r10-geo (score/lib_dump.py etc., gen/q139even.py etc.).
Scoring logic follows r10-geo score/score.py last_flag() and score_q139c()."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(HERE, "lib"))
import lib_dump as L  # noqa: E402
import q139even as E  # noqa: E402
import q139model as Q  # noqa: E402
import q139_fit as F  # noqa: E402

FIT_NAMES = None


def rows(d):
    with open(os.path.join(d, "cases.tsv")) as f:
        ls = f.read().splitlines()
    head = ls[0].split("\t")
    return [dict(zip(head, l.split("\t"))) for l in ls[1:]]


def size_of(args):
    a = args.split()
    return int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])


def kpokes(args):
    import re
    return " ".join("--kpoke-render " + x for x in re.findall(r"--kpoke-render (\S+)", args))


def flag_model(w, h, kp, model):
    """(slot of the last target tile in block order, wrong tiles), or None if its header is gone."""
    pred = E.predict(w, h, kp, model)
    key = Q.KEYS["blkrow"]
    n = E.geometry(w, h, kp)[0]
    last = max((t for t, v in pred.items() if v is not None), key=lambda t: key(t[1], t[0], 0, 0, n))
    # the last target tile in block order over ALL target tiles (not only surviving ones)
    lastall = max(pred, key=lambda t: key(t[1], t[0], 0, 0, n))
    return pred, last, lastall


def main(d):
    cases = rows(d)
    lay = {}
    out = []
    # controls first (baseline layout needs one per size)
    loaded = {}
    for r in cases:
        n = r["name"]
        w, h = size_of(r["args"])
        t = L.read_text(os.path.join(d, n + ".txt"))
        ok = t is not None and "job: ok" in t
        tad = L.read_bytes(os.path.join(d, n + ".tri.tadata.bin"))
        par = L.read_bytes(os.path.join(d, n + ".tri.param.bin"))
        loaded[n] = (w, h, t, ok, tad, par)
        if "kpoke-render" not in r["args"] and ok and tad and par:
            comp, bad = L.image_tiles(t, w, h)
            okb, txt, ly = L.baseline_layout(tad, par, w, h)
            if comp and not bad and okb:
                lay[(w, h)] = ly
            out.append("CONTROL %s: image complete %s, wrong %d; %s" % (n, comp, len(bad), txt))
    tot = {}
    for r in cases:
        n, sset = r["name"], r["set"]
        w, h, t, ok, tad, par = loaded[n]
        kp = kpokes(r["args"])
        cls = sset + ("/risky" if r["risk"] == "risky" else "")
        if "kpoke-render" not in r["args"]:
            ctl = L.headers(tad, L.header_base(tad), stop_zero=1 << 30)
            fl = sorted(i for i, c, rr, f, s in ctl if f & 0x80)
            out.append("ROW %s (%s, unpoked control): flag bit 7 at slots %s of %d headers" % (
                n, cls, fl, len(ctl)))
            continue
        if not ok or not tad or not par or (w, h) not in lay:
            out.append("ROW %s (%s): cannot tell (job ok %s)" % (n, cls, ok))
            tot.setdefault(sset, []).append(None)
            continue
        comp, bad = L.image_tiles(t, w, h)
        if not comp:
            out.append("ROW %s (%s): cannot tell (image not whole)" % (n, cls))
            tot.setdefault(sset, []).append(None)
            continue
        base = lay[(w, h)]["base"]
        hs = L.headers(tad, base, stop_zero=1 << 30)
        flagged = sorted(i for i, c, rr, f, s in hs if f & 0x80)
        highest = max(i for i, c, rr, f, s in hs)
        # H-HIGHEST model side: highest slot a predicted header takes (all tiles, target or not)
        hm = max(E.headers(w, h, kp, "H-EVEN"))
        want = L.target_tiles(w, h)
        highest_t = max(i for i, c, rr, f, s in hs if L.tile_of(c, rr) in want and s)
        hhit = len(flagged) == 1 and flagged[0] == highest_t
        pred_t = {L.tile_of(c, rr) for i, c, rr, f, s in hs if s and flagged and i <= flagged[-1]} & want
        got = want - bad
        right = len(pred_t & got) + len((want - pred_t) & bad)
        hlast = len(flagged) == 1 and right == len(want)
        # H-FLAGSLOT, H-EVEN and R7-BLK (blkrow) forms
        res = {}
        for m in ("H-EVEN", "blkrow"):
            pred, last, lastall = flag_model(w, h, kp, m)
            fs_slot = pred[lastall]
            if fs_slot is None:
                res[m] = (None, None, None)
                continue
            lw = {tt for tt, v in pred.items() if v is None or v > fs_slot}
            ok_fs = len(flagged) == 1 and flagged[0] == fs_slot and lw == bad
            res[m] = (fs_slot, lw == bad, ok_fs)
        rv = res["H-EVEN"]
        hfs = None if rv[0] is None else rv[2]
        hhi_dump = len(flagged) == 1 and flagged[0] == highest and True
        hhi_model = len(flagged) == 1 and flagged[0] == hm
        slots_ok = None
        obs = L.observed_slots(tad, base, w, h)
        for m in ("H-EVEN", "blkrow"):
            pred = E.predict(w, h, kp, m)
            ag = sum(1 for tt, v in pred.items()
                     if (v is None and not obs.get(tt)) or (v is not None and v in obs.get(tt, [])))
            res[m] += (ag, len(pred))
        rv = res["H-EVEN"]
        out.append("ROW %s (%s, %dx%d): wrong %d; headers %d; bit7 headers %d at %s; "
                   "H-FLAGSLOT(H-EVEN) slot %s -> %s (wrong-set %s); R7-BLK form slot %s -> %s; "
                   "H-HIGHEST-T (highest target-tile stream header) %d -> %s; H-HIGHEST dump-highest %d -> %s, model-highest %d -> %s; "
                   "H-LAST right %d of %d -> %s; slots H-EVEN %d of %d, R7-BLK %d of %d" % (
                       n, cls, w, h, len(bad), len(hs), len(flagged), flagged[:4], rv[0],
                       "undefined" if hfs is None else hfs, rv[1], res["blkrow"][0],
                       res["blkrow"][2], highest_t, hhit, highest, hhi_dump, hm, hhi_model, right, len(want),
                       hlast, rv[3], rv[4], res["blkrow"][3], res["blkrow"][4]))
        out.append("   PARTS %s: flagslot %s highest(dump) %s; flagged==highest %s" % (
            n, rv[0], highest, flagged == [highest]))
        tot.setdefault(sset, []).append(dict(
            name=n, hlast=hlast, hfs=hfs, hfs_r7=res["blkrow"][2], hhi=hhi_dump, hhim=hhi_model, hhit=hhit, parts_t=(rv[0] is not None and rv[0] != highest_t),
            parts=(rv[0] is not None and rv[0] != highest), nflag=len(flagged),
            slotsok=(rv[3] == rv[4]), r7ok=(res["blkrow"][3] == res["blkrow"][4])))
    for k, v in tot.items():
        v2 = [x for x in v if x]
        out.append("TOTAL set %s: %d rows, %d decided; H-LAST held %d; H-FLAGSLOT(H-EVEN) held %d "
                   "undefined %d; H-FLAGSLOT(R7-BLK form) held %d; H-HIGHEST(dump) held %d; "
                   "H-HIGHEST(model) held %d; H-HIGHEST-T held %d; rows where flagslot != highest-T slot %d; rows where flagslot != highest slot %d; "
                   "rows with exactly one bit7 header %d; H-EVEN slots exact %d, R7-BLK exact %d" % (
                       k, len(v), len(v2), sum(x["hlast"] for x in v2),
                       sum(1 for x in v2 if x["hfs"]), sum(1 for x in v2 if x["hfs"] is None),
                       sum(1 for x in v2 if x["hfs_r7"]), sum(x["hhi"] for x in v2),
                       sum(x["hhim"] for x in v2), sum(x["hhit"] for x in v2), sum(x["parts_t"] for x in v2), sum(x["parts"] for x in v2),
                       sum(x["nflag"] == 1 for x in v2), sum(x["slotsok"] for x in v2),
                       sum(x["r7ok"] for x in v2)))
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1])
