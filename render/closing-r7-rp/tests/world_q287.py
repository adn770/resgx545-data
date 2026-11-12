"""world_q287.py: the fake tool's answers for s0 and q287, from ARGV ONLY (never a case name).

  handles(tool, argv)        a bare `tri` (s0's default triangle) or a `tri ... --depth` row
  answer(tool, argv, tokens) dict(out, err, rc, kmsg); writes DIR/depth.1.bin as the real tool does (and REFUSES a missing
                             --depth-dump DIR as it does: the `depth #1: --depth-dump: No such file or directory` line, no file)
  tool: "t4" | "t6" | "t7".  t4 and t6 refuse an odd width (`render: Invalid argument`, rc 1); t7 accepts it.
  A depth row: --depth-pages pages of 0xdeadbeef; the tile area 1.0f; the band of the world's rule holds a ramp value; the
  store is tile-major at the --depth-ctl word's pitch (G + 1 tiles a row).  A poke cmd:9=V sets the screen width the band is
  computed from (H-SCR: (V & 0xffff) + 1), blk:6=F the viewport's half width (H-VP: 2 x F).
Tokens (FAKE_WORLD split on commas): model (default: rule A; twins read H-SCR), hscr, hvp (what twins follow), floor, ceil, round,
  rstrict (the band rule), ceil-odd (CEIL at odd widths only, A at even ones), refuse-odd (t7 refuses odd widths too), nodump (no dump written), fault (3D-side fault, rc 1),
  t7even (t7 stores one column more at even widths), t7bad (t7's default triangle draws wrong), t4zbad (t4's depth rows store one
  column less), lowpages (the dump is only the tool's own minimum, W * H dwords: what an unset --depth-pages would give).
"""
import os
import re
import shlex
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "gen"))
import models_q287 as M  # noqa: E402

FAULT3D = "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90100 at 0x10000016 (PD 0x30d6e000) stalls job 86, recovering"


def opt(a, name, cast=str, default=None):
    return cast(a[a.index(name) + 1]) if name in a else default


def opts(a, name):
    return [a[i + 1] for i, t in enumerate(a) if t == name]


def handles(tool, argv):
    return bool(argv) and argv[0] == "tri" and (len(argv) == 1 or "--depth" in argv)


def _poke(a, key):
    for v in opts(a, "--poke"):
        m = re.match(r"%s=(0x[0-9a-fA-F]+)$" % re.escape(key), v)
        if m:
            return int(m.group(1), 16)
    return None


def f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def rule_of(t, w=0):
    if "ceil-odd" in t:
        return "CEIL" if w % 2 else "A"
    for tok, r in (("floor", "FLOOR"), ("ceil", "CEIL"), ("round", "ROUND"), ("rstrict", "RSTRICT")):
        if tok in t:
            return r
    return "A"


def answer(tool, argv, tokens):
    t = set(tokens or ["model"])
    a = list(argv)
    if len(a) == 1:                                                  # s0's default 64 x 64 triangle
        if tool == "t7" and "t7bad" in t:
            return dict(out="job: ok\ndiff: 5 of 4096 pixels, first (3, 4) 0x00000000 expected 0xff00ff00\n", err="", rc=1, kmsg=[])
        return dict(out="job: ok\ndiff: 0 of 4096 pixels\n", err="", rc=0, kmsg=[])
    W, H = opt(a, "--width", int), opt(a, "--height", int)
    head = ["tri: render context for targets up to %dx%d" % (W, H)]
    if W % 2 and (tool in ("t4", "t6") or "refuse-odd" in t):
        out = head + ["job: rejected (Invalid argument)", "target: %dx%d hash 0x725d85be93d04c05" % (W, H),
                      "diff: %d of %d pixels, first (0, 0) 0x00000000 expected 0xff00ff00" % (W * H, W * H),
                      "outside: 1706 dwords", "layout: fb 0x3e013000", "tri: FAILED after 0 renders"]
        return dict(out="\n".join(out) + "\n", err="sgxfive-test: render: Invalid argument\n", rc=1, kmsg=[])
    if "fault" in t:
        return dict(out="\n".join(head + ["job: failed: job faulted, context lost (Input/output error)", "tri: FAILED after 0 renders"]) + "\n",
                    err="", rc=1, kmsg=[FAULT3D])
    rule = rule_of(t, W)
    bw, bh = W, H
    sw = _poke(a, "cmd:9")
    vp = _poke(a, "blk:6")
    if sw is not None and "hvp" not in t:
        bw = (sw & 0xFFFF) + 1
    if vp is not None and "hvp" in t:
        bw = int(round(2 * f32(vp)))
    if "hvp" in t and sw is not None and vp is None:
        bw = W
    pages = opt(a, "--depth-pages", int)
    ptiles = M.pitch_tiles(opt(a, "--depth-ctl", lambda s: int(s, 0)))
    n = W * H if "lowpages" in t else pages * 1024
    words = [0xDEADBEEF] * n
    aw, ah = M.G.area(W, H)
    band = M.band(rule, bw, bh)
    if (tool == "t7" and "t7even" in t and W % 2 == 0) or (tool == "t4" and "t4zbad" in t):
        xs = max(x for x, _ in band) + 1
        band = band - {(xs - 1, y) for y in range(ah)} if tool == "t4" else band | {(xs, y) for (x, y) in list(band) if x == xs - 1}
    for y in range(ah):
        for x in range(aw):
            i = M.dword_index(x, y, ptiles)
            if i < n:
                words[i] = 0x3E800000 + x + y if (x, y) in band else M.G.BG
    ddir = opt(a, "--depth-dump")
    files, dline = {}, []
    if ddir and os.path.isdir(ddir) and "nodump" not in t:
        files[os.path.join(ddir, "depth.1.bin")] = struct.pack("<%dI" % n, *words)
    else:
        dline = ["depth #1: --depth-dump: No such file or directory"]
    out = head + ["job: ok"] + dline + ["target: %dx%d hash 0x1" % (W, H), "diff: 0 of %d pixels" % (W * H), "outside: 0 dwords",
                                         "tri %dx%d #1: %d triangle, 0 background, 0 other" % (W, H, W * H), "tri: 1 renders ok"]
    for p, b in files.items():
        with open(p, "wb") as f:
            f.write(b)
    return dict(out="\n".join(out) + "\n", err="", rc=0, kmsg=[])


def kept(d, stage, world="model", kp=KP):
    """A kept stage directory as the runner writes it (cases.tsv, NAME.txt.gz, .err.gz, .dmesg.gz, .depth.1.bin.gz), every row
    of tables/STAGE.txt answered by the world from its argv; with gateodd and a refused gate row, the oddw rows are skipped."""
    import gzip
    os.makedirs(d, exist_ok=True)
    cases = ["name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_req\tfault_word\tfree_kb\n"]
    toks = set(world.split(","))
    skip_odd = False
    for ln in open(os.path.join(kp, "tables", stage + ".txt")).read().splitlines():
        if not ln or ln.startswith("#"):
            continue
        name, sset, risk, knobs, tl, args = ln.split("|", 5)
        kn = knobs.split()
        if skip_odd and "oddw" in kn:
            continue
        w = os.path.join(d, "w." + name)
        os.makedirs(os.path.join(w, "depth"), exist_ok=True)
        a = shlex.split(args.replace("$W", w))
        r = answer(tl, a, toks)
        dump = os.path.join(w, "depth", "depth.1.bin")
        if os.path.exists(dump):
            with open(dump, "rb") as f, gzip.open(os.path.join(d, name + ".depth.1.bin.gz"), "wb") as g:
                g.write(f.read())
            os.remove(dump)
        os.rmdir(os.path.join(w, "depth"))
        os.rmdir(w)
        for suf, txt in ((".txt", r["out"]), (".err", r["err"]), (".dmesg", "\n".join(r["kmsg"]))):
            with gzip.open(os.path.join(d, name + suf + ".gz"), "wb") as f:
                f.write(txt.encode())
        if r["kmsg"]:
            cls = "fault"
        elif r["rc"] == 0 or (r["rc"] == 1 and "diff:" in r["out"] and "FAILED after" not in r["out"]):
            cls = "ok"
        else:
            cls = "fail"
        if "gateodd" in kn and cls == "fail":
            skip_odd = True
        cases.append("\t".join([name, stage, sset, risk, knobs, tl, args, str(r["rc"]), cls, "-", "-", "999999"]) + "\n")
    with open(os.path.join(d, "cases.tsv"), "w") as f:
        f.writelines(cases)
    return d
