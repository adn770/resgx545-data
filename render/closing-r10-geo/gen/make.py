#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r10-geo's generator. Writes tables/STAGE.txt and predictions/STAGE.tsv of the three
stages (pivot, bgw, q139c, in run order) and the per-row frozen files predictions/STAGE/...,
every repository input read at the commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now
Inputs: RESGX545_DATA (default /Users/jtorra/src/resgx545-data)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import bgl_model as M  # noqa: E402
import bgw as BGW  # noqa: E402
import pins  # noqa: E402
import pivot as PIV  # noqa: E402
import q139c as QC  # noqa: E402
import scorekit  # noqa: E402

HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("pivot", "bgw", "q139c")
HEADERS = {
    "pivot": """# R10-3 (a) pivot, Q261: E979's far-x23p, far-x24p and far-x25n (far vertex at 2^23, 2^24, -2^25 px, --tri-unit 5,
# 64 x 64) with the far vertex's y moved by d = 0 .. -544 px (gen/pivot.py: the in-span band pixels flip together at
# t* = 42.6, 51.4, 41.6 px; a row draws them iff d + D > t* under H-PIVOT). Frozen per pixel H-EXACT (no band) and
# H-EXACT-BAND (E979's), per row the pixel intervals of H-PIVOT (one y displacement D of the far vertex per triangle).
# Control that can fail: E684's far21d0 (E979's far-ctl). Stop: any fault or hang (#limit 0); a tri row without job: ok.""",
    "bgw": """# R10-3 (a) bgw, Q066: finite values in the layered background object's words 9 and 11 to 14 (r9-k1's s3 form, t9,
# the layer's knobs). Frozen per background pixel (3034, gen/bgmask.txt): H-INERT (E973: finite values change nothing)
# and H-SCALE0 (the word scales one coordinate, 0 read as 1; 12 v, 11 and 14 u; clamped outside [0, 1), E974).
# Controls that can fail: the unpoked layer first and last (identity texels >= 3000 of 3034). Stop: any fault or hang;
# a row without job: ok or without the tool's bg-layer line.""",
    "q139c": """# R10-3 (a) q139c, Q139: TA dumps of the four y-side macrotile words that drew whole and never faulted (gen/q139c.py
# names the kept jobs: ta/mtile-fields-risky, render/closing-r7-rp q139), the datasets' command with --keep-going and
# --dump-render "$W" (r9-lgeo's q139b form). Controls (reads:hash,dump): the 256 x 256 and 640 x 480 baselines, exact
# image and one header with a stream a target tile (the header base). Replicates (E907's dumped words, fy 10): m2-B2-10,
# part2-10_10_10; held out: m2-B2-11 (fy 11), 640 x 480 m2-B1-23 (fy 23). Frozen: every slot and wrong tile (H-EVEN =
# R7-BLK here, and the round 8 orders), H-LAST (E959: a tile draws iff its header is at or before the one flag bit 7
# header), H-FLAGSLOT (that header is the last target tile's in block order). needhash: the second row without a hash
# stops the stage (24). Run last: any fault or hang stops it (#limit 0) and the session.""",
}


def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def build():
    files, tables = {}, {}
    # pivot
    rows, pred = [], [HEAD]
    for name, st, knobs, args, models, iv in PIV.jobs():
        rows.append(f"{name}|{st}|safe|{knobs}|t4|{args}")
        for m, c in models.items():
            body = PIV.cov_text(c)
            files[f"predictions/pivot/{name}.{m}.txt"] = body.encode()
            pred.append(line(name, "pixels", "sha256:" + pins.sha(body), m, st, "gen/pivot.py"))
        if iv is not None:
            files[f"predictions/pivot/{name}.ivals.txt"] = iv.encode()
            pred.append(line(name, "ivals", "sha256:" + pins.sha(iv), "H-PIVOT", st, "gen/pivot.py"))
    tables["pivot"] = (rows, pred)
    # bgw
    rows, pred = [], [HEAD]
    for name, st, knobs, args, w, v, models in BGW.jobs():
        rows.append(f"{name}|{st}|safe|{knobs}|t9|{args}")
        for m, p in models.items():
            pred.append(line(name, "texmap", M.map_id(p), m, st, "gen/bgw.py"))
    tables["bgw"] = (rows, pred)
    # q139c
    rows, pred = [], [HEAD]
    output = pins.blob(QC.DATASET).decode()
    for name, st, knobs, args, q, extra in QC.jobs(output):
        rows.append(f"{name}|{st}|safe|{knobs}|t4|{args}")
        for quantity, mv in q.items():
            for m, v in mv.items():
                pred.append(line(name, quantity, v, m, st, "gen/q139c.py"))
        for fn, body in extra.items():
            files[f"predictions/q139c/{fn}"] = body.encode()
            pred.append(line(name, "slots", "sha256:" + pins.sha(body), fn.split(".")[-2], st,
                             "gen/q139c.py"))
    tables["q139c"] = (rows, pred)
    import score as SC
    for stage in ORDER:
        rows, pred = tables[stage]
        files[f"tables/{stage}.txt"] = (f"#stage {stage}\n#limit 0\n{HEADERS[stage]}\n"
                                        + "\n".join(rows) + "\n").encode()
        files[f"predictions/{stage}.tsv"] = "".join(pred).encode()
        controls = {}
        for r in rows:
            name, st, _, knobs, tool, args = r.split("|", 5)
            if st == "control":
                reads = [w[6:].split(",") for w in knobs.split() if w.startswith("reads:")]
                controls[name] = (tuple(reads[0]) if reads else (),
                                  dict(name=name, args=args, stage=stage))
        scorekit.refuse_unreadable(controls, SC.producible)
    return files


def main(argv):
    files = build()
    check = "--check" in argv
    bad = []
    for rel, b in sorted(files.items()):
        p = os.path.join(KP, rel)
        if check:
            if not os.path.exists(p) or open(p, "rb").read() != b:
                bad.append(rel)
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b)
    if check:
        for d in ("tables", "predictions", "predictions/pivot", "predictions/q139c"):
            full = os.path.join(KP, d)
            for n in sorted(os.listdir(full)) if os.path.isdir(full) else []:
                if not os.path.isdir(os.path.join(full, n)) and f"{d}/{n}" not in files:
                    bad.append(f"{d}/{n} (not written by the generator)")
        print("\n".join(f"differs: {b}" for b in bad) or f"generator current: {len(files)} files")
        return 1 if bad else 0
    print(f"wrote {len(files)} files; pins read: {', '.join(sorted(pins.READ))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
