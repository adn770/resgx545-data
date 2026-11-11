"""worlds.py: R4-A worlds built from the REAL kept files of R3K-regress (the two-render rows pb-n40-a and pb-n60, the one-render
pb-e40-m2-64a and pb-e20-m2-64 for the K2-lesson world), with the kernel's `kpoke ... applied` lines and the poked dwords
added for the poke rows.  One world, two uses:

  kept(outdir, stage, world)      a kept stage directory (cases.tsv, NAME.txt.gz, NAME.dmesg.gz, dumps) for the scorer tests
  fake(dirpath, world)            per-case files for tests/fake_tool.sh (NAME.out, NAME.rc, NAME.param, NAME.tadata, NAME.kmsg,
                                  NAME.armed), so that the runner itself runs the world (tests/run_mock.sh)

Worlds (WORLDS): old, field, q030, both, mixed (hypotheses and their mixes); ctl-k2 (the controls come back with one-render
values, K2's k-pb0 mismatch seen from the other side: they FAIL and the gate closes), ctl-nodata (p0's output missing), p2-notapplied,
p2-armed, p3-short (15 of 16 pokes applied), p4-hang (p4a hangs: the stage stops, p4b never runs), p4-other (0 triangle, some
other pixels).  python3 tests/worlds.py fake DIR WORLD writes the fake-tool files.
"""
import gzip
import os
import re
import struct
import sys

DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
REG = os.path.join(DATA, "render/closing-r3k-regress/out/20261110-222647/rg-pb")
STAGES = {"a-pb0": ["pb-d0-te40", "pb-p0-te60", "pb-p1-te40"],
          "a-pb": ["pb-p2-own11", "pb-p3a-twin", "pb-p3b-twin", "pb-p4a-ffff", "pb-p4b-ffff"]}
SET = {"pb-d0-te40": "control", "pb-p0-te60": "control", "pb-p1-te40": "control", "pb-p2-own11": "control",
       "pb-p3a-twin": "heldout", "pb-p3b-twin": "replicate", "pb-p4a-ffff": "heldout", "pb-p4b-ffff": "replicate"}


def _gz(p):
    with gzip.open(p, "rb") as f:
        return f.read()


def src(job):
    return {"out": _gz(os.path.join(REG, job + ".txt.gz")).decode(), "param": _gz(os.path.join(REG, job + ".tri.param.bin.gz")),
            "tadata": _gz(os.path.join(REG, job + ".tri.tadata.bin.gz"))}


def poke(param, words):
    b = bytearray(param)
    for i, v in words:
        struct.pack_into("<I", b, 4 * i, v)
    return bytes(b)


def twin_words():
    p = src("pb-n60")["param"]
    return [struct.unpack_from("<I", p, 4 * i)[0] for i in range(11, 26)] + [0]


P3 = list(zip(range(11, 27), twin_words()))
P4 = [(11, 0xFFFFFFFF)]
P2 = [(11, 0)]


def applied(pokes):
    return "".join("gma500 0000:00:02.0: [drm] sgxfive: kpoke par:%d=0x%08x applied\n" % (i, v) for i, v in pokes)


def drawn(out, tri=2016, other=0):
    """The render-2 line and diff of a partly drawn image."""
    bg = 4096 - tri - other
    out = re.sub(r"^tri 64x64 #2: .*$", "tri 64x64 #2: %d triangle, %d background, %d other; wrong %d inside, 0 outside, 0 at edges; "
                 "%d if flipped; guard 0" % (tri, bg, other, 4096 - tri, 4096 - tri), out, flags=re.M)
    return re.sub(r"^diff: .*$", "diff: %d of 4096 pixels, first (1, 1) 0xff000080 expected 0xffff0000" % (4096 - tri), out, flags=re.M)


def job_ctl(kind):
    s = src({"n40": "pb-n40-a", "n60": "pb-n60", "e40": "pb-e40-m2-64a", "e20": "pb-e20-m2-64"}[kind])
    rc = 0 if kind in ("n60", "e20") else 1
    return {"out": s["out"], "param": s["param"], "tadata": s["tadata"], "rc": rc, "class": "ok", "kmsg": "", "armed": ""}


def job_poke(base, pokes, applied_pokes=None, out=None):
    s = src(base)
    o = out if out is not None else s["out"]
    rc = 0 if re.search(r"^diff: 0 of", o, re.M) else 1
    return {"out": o, "param": poke(src("pb-n40-a")["param"], pokes), "tadata": s["tadata"], "rc": rc, "class": "ok",
            "kmsg": applied(pokes if applied_pokes is None else applied_pokes), "armed": ""}


def world(name):
    """{case: job dict or None (not run)} for a world."""
    w = {"pb-d0-te40": job_ctl("n40"), "pb-p0-te60": job_ctl("n60"), "pb-p1-te40": job_ctl("n40"),
         "pb-p2-own11": job_poke("pb-n40-a", P2)}
    twin_out = src("pb-n60")["out"]
    empty_out = src("pb-n40-a")["out"]
    p3_twin = job_poke("pb-n60", P3, out=twin_out)
    p3_empty = job_poke("pb-n40-a", P3, out=empty_out)
    p4_empty = job_poke("pb-n40-a", P4, out=empty_out)
    p4_drawn = job_poke("pb-n40-a", P4, out=drawn(empty_out))
    if name in ("old", "p2-notapplied", "p2-armed", "p3-short", "p4-hang", "p4-other", "ctl-k2", "ctl-nodata"):
        w.update({"pb-p3a-twin": p3_twin, "pb-p3b-twin": dict(p3_twin), "pb-p4a-ffff": p4_empty, "pb-p4b-ffff": dict(p4_empty)})
    elif name == "field":
        w.update({"pb-p3a-twin": p3_empty, "pb-p3b-twin": dict(p3_empty), "pb-p4a-ffff": p4_drawn, "pb-p4b-ffff": dict(p4_drawn)})
    elif name == "q030":
        w.update({"pb-p3a-twin": p3_empty, "pb-p3b-twin": dict(p3_empty), "pb-p4a-ffff": p4_empty, "pb-p4b-ffff": dict(p4_empty)})
    elif name == "both":
        w.update({"pb-p3a-twin": p3_twin, "pb-p3b-twin": dict(p3_twin), "pb-p4a-ffff": p4_drawn, "pb-p4b-ffff": dict(p4_drawn)})
    elif name == "mixed":
        w.update({"pb-p3a-twin": p3_twin, "pb-p3b-twin": p3_empty, "pb-p4a-ffff": p4_empty, "pb-p4b-ffff": dict(p4_empty)})
    else:
        raise KeyError(name)
    if name == "ctl-k2":
        w["pb-d0-te40"], w["pb-p1-te40"], w["pb-p0-te60"] = job_ctl("e40"), job_ctl("e40"), job_ctl("e20")
    if name == "ctl-nodata":
        w["pb-p0-te60"] = dict(w["pb-p0-te60"], out="")
    if name == "p2-notapplied":
        w["pb-p2-own11"] = dict(w["pb-p2-own11"], kmsg="")
    if name == "p2-armed":
        w["pb-p2-own11"] = dict(w["pb-p2-own11"], armed="par:11=0x00000000\n")
    if name == "p3-short":
        w["pb-p3a-twin"] = dict(w["pb-p3a-twin"], kmsg=applied(P3[:15]))
    if name == "p4-hang":
        w["pb-p4a-ffff"] = dict(p4_empty, out=empty_out.split("target:")[0] + "job: failed: job hung, context lost (Connection timed out)\n",
                                rc=1, **{"class": "hang"}, param=None, kmsg=applied(P4) + "gma500 0000:00:02.0: [drm] sgxfive: job 9 hung, recovering\n")
        w["pb-p4b-ffff"] = None
    if name == "p4-other":
        w["pb-p4a-ffff"] = dict(p4_empty, out=drawn(empty_out, tri=0, other=300))
        w["pb-p4b-ffff"] = dict(w["pb-p4a-ffff"])
    return w


WORLDS = ["old", "field", "q030", "both", "mixed", "ctl-k2", "ctl-nodata", "p2-notapplied", "p2-armed", "p3-short", "p4-hang",
          "p4-other"]
CMD = "tri -n 2 --geometry 1 (see tables/)"


def _wgz(p, data):
    with gzip.GzipFile(p, "wb", mtime=0) as f:
        f.write(data)


def kept(outdir, stage, name, skip=()):
    os.makedirs(outdir, exist_ok=True)
    w = world(name)
    lines = ["name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tmode\tfault_req\treset_rc\theld_msg\n"]
    for case in STAGES[stage]:
        j = w.get(case)
        if j is None or case in skip:
            continue
        if j["out"]:
            _wgz(os.path.join(outdir, case + ".txt.gz"), j["out"].encode())
        _wgz(os.path.join(outdir, case + ".dmesg.gz"), ("resgx545 case %s 1-1\n" % case + j["kmsg"]).encode())
        _wgz(os.path.join(outdir, case + ".kpoke.txt.gz"), j["armed"].encode())
        if j.get("param") is not None:
            _wgz(os.path.join(outdir, case + ".tri.param.bin.gz"), j["param"])
            _wgz(os.path.join(outdir, case + ".tri.tadata.bin.gz"), j["tadata"])
        lines.append("\t".join((case, stage, SET[case], "safe", "rgn:1 expectdiff", "-", CMD, str(j["rc"]), j["class"], "plain", "-",
                                "-", "no")) + "\n")
    open(os.path.join(outdir, "cases.tsv"), "w").write("".join(lines))
    return outdir


def fake(dirpath, name):
    os.makedirs(dirpath, exist_ok=True)
    for case, j in world(name).items():
        if j is None:
            open(os.path.join(dirpath, case + ".notrun"), "w").write("")
            continue
        open(os.path.join(dirpath, case + ".out"), "w").write(j["out"])
        open(os.path.join(dirpath, case + ".rc"), "w").write("%d\n" % j["rc"])
        open(os.path.join(dirpath, case + ".kmsg"), "w").write(j["kmsg"])
        open(os.path.join(dirpath, case + ".armed"), "w").write(j["armed"])
        if j.get("param") is not None:
            open(os.path.join(dirpath, case + ".param"), "wb").write(j["param"])
            open(os.path.join(dirpath, case + ".tadata"), "wb").write(j["tadata"])
        if j["class"] == "hang":
            open(os.path.join(dirpath, case + ".hang"), "w").write("")
    return dirpath


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "fake":
        fake(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        sys.exit(2)
