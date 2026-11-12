"""worlds.py: r7-geo's ARGV-DRIVEN fake laptop.  The fake tool never sees a case name: it answers from its own path (t4 =
...sgxfive-test-rgn4 refuses odd heights as the rgn4 build does; t6 = anything else) and its argv only:

  fill ... --poke 'pds:pixev:12^=V'   the 128 x 64 fill under the world's Q206 reading (INDEP, or xfirst / yfirst), hashed with
            the tool's FNV-1a, the tool's lines (diff, `fill: FAIL` and rc 1 when a pixel is wrong)
  probe ... "$S/NAME.bin"   a texture fill: the program's own T1 word (read from the program's bytes: the `mov r21, #T1` limm)
            gives the type and size; the image of the world's layout (RASTERW for 1 and 3, S32 for 4, H-STEP for 5; worlds s2wcap,
            fix16, mem change them); the iteration probe (--tri ... p1138-it-a0__0.bin): pa0 = the clip-z plane at the centre in
            float32 where E606's rule covers, 0xff203040 elsewhere
  tri --tri-v ... [--depth ...]   E606's coverage (or, with --tri-unit 12, the world's rounding: HU, or ha / setupN / far), the colour
            image's hash and triangle count, --pixels rows; with --depth the dump DIR/depth.1.bin: 0xdeadbeef everywhere, the tile area
            1.0f, covered pixels the plane in float32 (world zls-dead leaves one tile-area dword unwritten; world depth-off adds 8 units)
  THE RECORDS' OWN ARGV: a command equal to a control's record command (E606 cases 412, 1206, 262, 926 and I0 1016, E680 1400246,
            E681 1400606, E683 1401234) answers with the record's kept output (rows in the rgn4 tool's form) and dump
  tri, fill (bare)  the health pair: exact unless FAKE_HEALTH_BAD

  tool PATH ARGS...    the fake tool (tests/fake_tool4.sh, fake_tool6.sh exec this)
World: FAKE_WORLD, comma separated tokens: model (default) xfirst yfirst s2wcap fix16 mem ha setup5 far zls-dead depth-off
big-fail (a 4096 x 4096 depth row whose first x is below 600000/256 is refused: zd's 4096 rows 1, 2 and 4) norecord (the records'
own argv answered by the model, not the kept output: the controls must fail) tiny-refuse (16 x 8 and 32 x 16 refused) nodump nohash fault-zd.
"""
import gzip
import os
import re
import shlex
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "gen"))
import models as M  # noqa: E402

D = "/Users/jtorra/src/resgx545-data"
FAULT3D = "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90100 at 0x10000016 (PD 0x30d6e000) stalls job 86, recovering"


def opt(a, name, cast=str, default=None):
    return cast(a[a.index(name) + 1]) if name in a else default


def toks(world):
    return set((world or "model").split(","))


def gz(p):
    with gzip.open(p, "rb") as f:
        return f.read()


# ---- the records' own argv ----------------------------------------------------------------------------------------------
def _rle_rows(text, w):
    out = []
    for ln in text.splitlines():
        if ln.startswith("rle "):
            y, _, rest = ln[4:].partition(":")
            vals = []
            for t in rest.split():
                v, _, n = t.rpartition("x")
                vals += [v] * int(n)
            out.append("row %s: %s" % (y, " ".join(vals)))
    return out


def record(a):
    """(text, dump bytes or None) when argv's triangle is a control's record, else None."""
    if "--tri-v" not in a:
        return None
    v = opt(a, "--tri-v")
    w, h = opt(a, "--width", int), opt(a, "--height", int)
    for ln in open(os.path.join(D, "isp/arith-1138/cases.tsv")):
        f = ln.rstrip("\n").split("\t")
        if f[0] in ("412", "1206", "262", "926", "1016") and ",".join(f[5:11]) == v and (int(f[3]), int(f[4])) == (w, h):
            if a[0] == "probe":
                return gz(os.path.join(D, "isp/arith-1138/main/I0/%s.txt.gz" % f[0])).decode(), None
            return (gz(os.path.join(D, "isp/arith-1138/main/D/%s.txt.gz" % f[0])).decode(),
                    gz(os.path.join(D, "isp/arith-1138/main/D/%s.depth.gz" % f[0])))
    for cid in ("1400246", "1400606", "1401234"):
        jl = [ln for ln in open(os.path.join(D, "isp/coverage-envelope/main/jobs.tsv")) if ln.startswith(cid + "\t")][0]
        if ("--tri-v " + v + " ") in jl and ("--width %d --height %d " % (w, h)) in jl:
            t = gz(os.path.join(D, "isp/coverage-envelope/main/raw/%s.txt.gz" % cid)).decode()
            keep = [ln for ln in t.splitlines() if not ln.startswith("rle ")]
            rows = _rle_rows(t, w) if "--pixels" in a else []
            i = [k for k, ln in enumerate(keep) if ln.startswith("layout:")][0]
            return "\n".join(keep[:i] + rows + keep[i:]) + "\n", None
    return None


# ---- fills ----------------------------------------------------------------------------------------------------------------
def fill(a, w_):
    W, H = opt(a, "--width", int, 64), opt(a, "--height", int, 32)
    stride = opt(a, "--stride", int, 256)
    pk = opt(a, "--poke")
    m = "XFIRST" if "xfirst" in w_ else ("YFIRST" if "yfirst" in w_ else "INDEP")
    v = int(re.match(r"pds:pixev:12\^=(0x[0-9a-f]+)$", pk).group(1), 16) if pk else 0
    fx, fy = M.split_poke(v)
    img = M.fill_image(W, H, fx, fy, m)
    wrong = [i for i, p in enumerate(img) if p != M.FCOL]
    out = ["programs asm", "job: ok", "job time: 23 us"]
    if not ("nohash" in w_ and pk):
        out.append("target: %dx%d hash 0x%016x" % (W, H, M.fnv(img)))
    out.append("diff: %d of %d pixels" % (len(wrong), W * H) + (", first (%d, %d) 0x%08x expected 0x%08x" % (
        wrong[0] % W, wrong[0] // W, img[wrong[0]], M.FCOL) if wrong else ""))
    out.append("outside: 0 dwords")
    if wrong:
        out += ["fill: FAIL, %d wrong dwords" % len(wrong)]
        return "\n".join(out) + "\n", "", 1, [], {}
    out.append("fill: ok, %dx%d at (0, 0), stride %d, colour 0x%08x" % (W, H, stride, M.FCOL))
    return "\n".join(out) + "\n", "", 0, [], {}


# ---- probes ---------------------------------------------------------------------------------------------------------------
DIS = os.path.join(KP, "debug/asm/tools/usse-dis/usse-dis")     # built by tests/run_all.sh from resgx545 1c64f3a


def t1_of(path):
    """The T1 word a texture program loads (`mov r21, #T1`), read with the pinned disassembler: the fake answers from the program
    the argv names, never from its file name."""
    import subprocess
    out = subprocess.run([DIS, path], capture_output=True, text=True).stdout
    m = re.search(r"\bmov r21, #(0x[0-9A-Fa-f]+)", out)
    if not m:
        raise ValueError("no mov r21 in " + path)
    return int(m.group(1), 16)


def probe(a, w_):
    prog_path = a[-1]
    name = os.path.basename(prog_path).split(".")[0]
    if not os.path.exists(prog_path):
        return "", "sgxfive-test: %s: No such file or directory\n" % prog_path, 1, [], {}
    if "--tri" in a:
        rec = None if "norecord" in w_ else record(a)
        if rec:
            return rec[0], "", 0, [], {}
        W, H = opt(a, "--width", int), opt(a, "--height", int)
        v, z = [int(t) for t in opt(a, "--tri-v").split(",")], [M.Fraction(t) for t in opt(a, "--tri-z").split(",")]
        cov = M.cover(v, W, H)
        pl = M.plane_image(v, [2 * x - 1 for x in z], W, H).astype(np.float32).view(np.uint32)
        img = np.where(cov, pl, np.uint32(M.BG))
        rows = ["probe %s: row %d: %s" % (name, y, " ".join("%08x" % p for p in img[y])) for y in range(H)]
        out = ["programs asm", "probe %s: tri %dx%d (2 coordinates), vtxuse pixel pixpds replaced" % (name, W, H)] + rows
        return "\n".join(out) + "\n", "", 0, [], {}
    t1 = t1_of(prog_path)
    ty, w, h = t1 >> 29, ((t1 >> 12) & 0xFFF) + 1, (t1 & 0xFFF) + 1
    if ty == 5:
        img = M.type5_image("H-FIX16" if "fix16" in w_ else "H-STEP", w)
        if "mem" in w_ and "-zero" in name:
            img = [0] * 2048
    else:
        hyp = "RASTERW" if ty in (1, 3) else ("S2WCAP" if "s2wcap" in w_ else "S32")
        img = M.tex_image(hyp, w, h)
    rows = ["probe %s: row %d: %s" % (name, y, " ".join("%08x" % p for p in img[64 * y:64 * y + 64])) for y in range(32)]
    out = ["programs asm", "probe %s: scratch at 0x3e003000 (64 KiB)" % name, "probe %s: job time: 624 us" % name] + rows
    return "\n".join(out) + "\n", "", 0, [], {}


# ---- triangles ------------------------------------------------------------------------------------------------------------
def tri(a, w_, ver):
    W, H = opt(a, "--width", int), opt(a, "--height", int)
    head = ["tri: render context for targets up to %dx%d" % (W, H)]
    if (H % 2 and ver == 4) or ("tiny-refuse" in w_ and W * H <= 512):
        return "\n".join(head + ["tri: FAILED after 0 renders"]) + "\n", "sgxfive-test: render: Invalid argument\n", 1, [], {}
    if "fault-zd" in w_ and W == 640:
        return "\n".join(head + ["job: failed: job faulted, context lost (Input/output error)", "tri: FAILED after 0 renders"]) + "\n", \
            "", 1, [FAULT3D], {}
    if "big-fail" in w_ and W * H > 4 * 1024 * 1024 and "--depth" in a and int(opt(a, "--tri-v").split(",")[0]) < 600000:
        return "\n".join(head + ["tri: FAILED after 0 renders"]) + "\n", "sgxfive-test: depth buffer: Cannot allocate memory\n", 1, [], {}
    ddir = opt(a, "--depth-dump")
    rec = None if "norecord" in w_ else record(a)
    files, dline = {}, []
    if rec:
        text, dump = rec
        if dump is not None:
            if os.path.isdir(ddir):
                files[os.path.join(ddir, "depth.1.bin")] = dump
            else:
                text += "depth #1: --depth-dump: No such file or directory\n"
        return text, "", 0, [], files
    v = [int(t) for t in opt(a, "--tri-v").split(",")]
    unit = opt(a, "--tri-unit", int, 8)
    if unit == 12:
        if "ha" in w_:
            cov = M.cover4096(v, W, H, "HA")
        elif "far" in w_:
            cov = M.cover4096(v, W, H, "FAR")
        elif any(t.startswith("setup") for t in w_):
            cov = M.cover4096(v, W, H, "SETUP", int([t for t in w_ if t.startswith("setup")][0][5:]))
        else:
            cov = M.cover4096(v, W, H, "HU")
    else:
        cov = M.cover(v, W, H)
    if "--depth" in a:
        z = [M.Fraction(t) for t in opt(a, "--tri-z").split(",")]
        pages = opt(a, "--depth-pages", int)
        buf = np.full(pages * 1024, M.FILL, dtype=np.uint32)
        aw, ah = M.G.area(W, H)
        buf[M.depth_index(aw, ah).ravel()] = M.ONE
        pl = M.plane_image(v, z, W, H) + (8 * M.U if "depth-off" in w_ else 0.0)
        idx = M.depth_index(W, H)
        buf[idx[cov]] = pl[cov].astype(np.float32).view(np.uint32)
        if "zls-dead" in w_:
            buf[M.depth_index(aw, ah).ravel()[-1]] = M.FILL
        if os.path.isdir(ddir) and "nodump" not in w_:
            files[os.path.join(ddir, "depth.1.bin")] = buf.astype("<u4").tobytes()
        else:
            dline = ["depth #1: --depth-dump: No such file or directory"]
    h = M.image_hash(cov) if cov.size <= 4 * 1024 * 1024 else 0x1234
    rows = []
    if "--pixels" in a:
        rows = ["row %d: %s" % (y, " ".join("0x%08x" % (M.GREEN if c else M.BG) for c in cov[y])) for y in range(H)]
    n = int(cov.sum())
    out = head + ["job: ok"] + dline + (["target: %dx%d hash 0x%016x" % (W, H, h)] if "nohash" not in w_ else []) + \
        ["diff: 0 of %d pixels" % (W * H), "outside: 0 dwords"] + rows + \
        ["layout: fb 0x3e001000", "tri %dx%d #1: %d triangle, %d background, 0 other; wrong 0 inside" % (W, H, n, W * H - n),
         "tri: 1 renders ok"]
    return "\n".join(out) + "\n", "", 0, [], files


def answer(path, a, world):
    w_ = toks(world)
    ver = 4 if path.endswith("sgxfive-test-rgn4") else 6
    if a in (["fill"], ["tri"]):
        if os.environ.get("FAKE_HEALTH_BAD"):
            return "job: failed\n", "", 1, [], {}
        return "job: ok\ndiff: 0 of %d pixels\n" % (2048 if a == ["fill"] else 4096), "", 0, [], {}
    if a[0] == "fill":
        return fill(a, w_)
    if a[0] == "probe":
        return probe(a, w_)
    if a[0] == "tri":
        return tri(a, w_, ver)
    return "", "sgxfive-test: usage (the fake knows no such command)\n", 2, [], {}


def tool(argv):
    path, a = argv[0], argv[1:]
    out, err, rc, kmsg, files = answer(path, a, os.environ.get("FAKE_WORLD", "model"))
    for p, b in files.items():
        with open(p, "wb") as f:
            f.write(b)
    if kmsg and os.environ.get("KMSG"):
        with open(os.environ["KMSG"], "a") as f:
            f.write("\n".join(kmsg) + "\n")
    with open(os.environ.get("FAKE_LOG", os.devnull), "a") as f:
        f.write("%s %s\n" % (os.path.basename(path), " ".join(a)))
    sys.stdout.write(out)
    sys.stderr.write(err)
    return rc


def kept(d, stage, world="model", kp=KP, stage_dir=None):
    """A kept stage directory as run_stage.sh writes it (cases.tsv, void.tsv, NAME.txt.gz, .err.gz, .dmesg.gz, .depth.1.bin.gz),
    every row of tables/STAGE.txt answered by the world from its argv; gate refusals and soft failures go to void.tsv."""
    os.makedirs(d, exist_ok=True)
    hdr = "name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_req\tfault_word\tfree_kb\n"
    cases, void, skip = [hdr], [hdr], set()
    S = stage_dir or os.path.join(kp, "bins")
    for ln in open(os.path.join(kp, "tables", stage + ".txt")).read().splitlines():
        if not ln or ln.startswith("#"):
            continue
        name, sset, risk, knobs, tl, args = ln.split("|", 5)
        kn = knobs.split()
        grp = [k[4:] for k in kn if k.startswith("grp:")]
        if grp and grp[0] in skip:
            continue
        wd = os.path.join(d, "work"); os.makedirs(os.path.join(wd, "depth"), exist_ok=True)
        a = shlex.split(args.replace("$W", wd).replace("$S", S))
        path = "/h/sgxfive-test-rgn4" if tl == "t4" else "/h/scratch/r7g/bin/sgxfive-test"
        out, err, rc, kmsg, files = answer(path, a, world)
        for p, b in files.items():
            with gzip.open(os.path.join(d, name + ".depth.1.bin.gz"), "wb") as f:
                f.write(b)
        for suf, txt in ((".txt", out), (".err", err), (".dmesg", "\n".join(kmsg))):
            with gzip.open(os.path.join(d, name + suf + ".gz"), "wb") as f:
                f.write(txt.encode())
        cls = "fault" if kmsg else ("ok" if rc == 0 or (rc == 1 and "diff:" in out) else "fail")
        line = "\t".join([name, stage, sset, risk, knobs, tl, args, str(rc), cls, "-", "-", "999999"]) + "\n"
        if cls == "fail" and ("soft" in kn or "gate" in kn):
            void.append(line)
            if "gate" in kn and grp:
                skip.add(grp[0])
        else:
            cases.append(line)
    for f, rows in (("cases.tsv", cases), ("void.tsv", void)):
        with open(os.path.join(d, f), "w") as fh:
            fh.writelines(rows)
    import shutil
    shutil.rmtree(os.path.join(d, "work"), ignore_errors=True)
    return d


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "tool":
        sys.exit(tool(sys.argv[2:]))
    print(__doc__)
