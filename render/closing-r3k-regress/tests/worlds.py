"""worlds.py: kept-output directories built from the REAL records the predictions came from (and from K2's k-pb0), so a scorer test
runs on real tool output and real dumps; a mutation function can change any job's text or leave it out.

  build(outdir, stage, srcmap=None, mutate=None, skip=(), cls=None)
    stage    rg-ctl | rg-pb
    srcmap   {case: ("e728", job) | ("k2", job)}  overrides the source of a rg-pb row (default: E728 for pb-e*, K2 for pb-n*)
    mutate   {case: function(text) -> text}       applied to the tool output
    skip     cases without a cases.tsv row
    cls      {case: (rc, class)}                  rc/class written (default: the record's rc, ok)
"""
import gzip
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "gen"))
import rgen as G  # noqa: E402


def gz(path, data):
    with gzip.GzipFile(path, "wb", mtime=0) as f:
        f.write(data)


def rd(path):
    if not os.path.exists(path):
        return None
    with gzip.open(path, "rb") as f:
        return f.read()


def build(outdir, stage, srcmap=None, mutate=None, skip=(), cls=None):
    os.makedirs(outdir, exist_ok=True)
    mutate, cls, srcmap = mutate or {}, cls or {}, srcmap or {}
    rows = []
    if stage == "rg-ctl":
        items = [(c[0], c[1], c[2], c[3], c[4], c[5]) for c in G.CTL]
        for case, sset, cmd, d, srcn, dump in items:
            out = rd(os.path.join(d, srcn + ".txt.gz"))
            rc = G._rc_from_cases(d, srcn)
            dumps = {}
            if dump == "tri":
                dumps = {"tri.tadata.bin": rd(os.path.join(d, srcn + ".tri.tadata.bin.gz")), "tri.param.bin": rd(os.path.join(d, srcn + ".tri.param.bin.gz"))}
            elif dump:
                dumps = {dump.split(".", 1)[1] + ".tadata.bin": rd(os.path.join(d, dump + ".tadata.bin.gz")),
                         dump.split(".", 1)[1] + ".param.bin": rd(os.path.join(d, dump + ".param.bin.gz"))}
            rows.append((case, sset, "expectdiff" if cmd.startswith("tri") else "stophang", cmd, out, rc, dumps))
    else:
        for case, sset, size, te, mode, srcn, rc in G.PB_E:
            kind, job = srcmap.get(case, ("e728", srcn))
            rows.append((case, sset, "expectdiff", G.pb_cmd_e(size, te, mode)) + _pb_src(kind, job, rc))
        for case, sset, te, k2n in G.PB_N:
            kind, job = srcmap.get(case, ("k2", k2n))
            rows.append((case, sset, "expectdiff", G.pb_cmd_n(te)) + _pb_src(kind, job, 1))
    lines = ["name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tmode\tfault_req\treset_rc\theld_msg\n"]
    for case, sset, knobs, cmd, out, rc, dumps in rows:
        if case in skip:
            continue
        if case in mutate:
            out = mutate[case](out.decode()).encode()
        if out is not None:
            gz(os.path.join(outdir, case + ".txt.gz"), out)
        gz(os.path.join(outdir, case + ".dmesg.gz"), b"gma500: nothing special\n")
        for k, v in dumps.items():
            if v is not None:
                gz(os.path.join(outdir, "%s.%s.gz" % (case, k)), v)
        rc2, cl = cls.get(case, (rc, "ok"))
        lines.append("\t".join((case, stage, sset, "safe", knobs, "-", cmd, str(rc2), cl, "plain", "-", "-", "no")) + "\n")
    open(os.path.join(outdir, "cases.tsv"), "w").write("".join(lines))
    return outdir


def _pb_src(kind, job, rc):
    base = G.SRC_E if kind == "e728" else G.K2
    out = rd(os.path.join(base, job + ".txt.gz"))
    dumps = {"tri.tadata.bin": rd(os.path.join(base, job + ".tri.tadata.bin.gz")), "tri.param.bin": rd(os.path.join(base, job + ".tri.param.bin.gz"))}
    if kind == "k2":
        rc = G._rc_from_cases(G.K2, job)
    return (out, rc, dumps)
