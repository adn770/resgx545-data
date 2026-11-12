"""worlds.py: r6-misc's ARGV-DRIVEN fake laptop.  The fake tool never sees a case name: it answers from its own path (t4 =
...sgxfive-test-rgn4, refuses odd heights as the rgn4 build does; t6 = anything else) and its argv only, as the tool and the module
would (round 4's fake answered by the kmsg marker's case name and so could not see a row's argv):

  fill      the target W x H (--stride), the pds:pixev:12^=V poke read as the x field (V < 0x1000, V / 8) or the y field (V / 0x1000)
            in half-tile units; the image of the world's Q289 model (M-OR, or M-ADD / M-XOR), hashed with the tool's FNV-1a; the
            tool's lines (job, target hash, diff with the first wrong pixel, outside, `fill: FAIL, N wrong dwords` and rc 1 when a
            pixel is wrong, as the kept sweeps show)
  tri ... --depth   (q287) the depth dump DIR/depth.1.bin of --depth-pages pages: 0xdeadbeef everywhere, the tile area 1.0f
            (0x3f800000) except the band of the world's rule (A, or FLOOR / CEIL), which holds a ramp value; t4 and an odd
            height: `sgxfive-test: render: Invalid argument`, rc 1 (the rgn4 tool's refusal); world refuse-odd: t6 refuses too
  tri ... --aa4     (q086) H-COV (or H-ANY) decides from the words the argv's --kpoke-render lines and the size give: completes
            (every pixel green, --pixels rows, diff 0) or faults on the 3D side (BIF fault 0x90100 at 0x10000016 in the kernel
            log, `job: failed: job faulted`), or TA side in world q086-ta
  tri, fill (bare)  the health pair: exact unless FAKE_HEALTH_BAD

  tool PATH ARGS...    the fake tool (tests/fake_tool4.sh, fake_tool6.sh exec this)
  kept(DIR, stage, world)   a kept stage directory as the runner writes it, for the scorer tests
World: FAKE_WORLD, comma separated tokens: model (default) add xor outside floor ceil refuse-odd hany allfault (every kpoked 4x
row faults) q086-ta fill-fault nohash nodump (the depth dump is not written).
"""
import gzip
import os
import re
import shlex
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "gen"))
import models as M  # noqa: E402

FAULT3D = "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90100 at 0x10000016 (PD 0x30d6e000) stalls job 86, recovering"
FAULTTA = "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90004 at 0x20006061 (PD 0x30d6e000) stalls job 86, recovering"
GREEN = 0xFF00FF00


def opt(a, name, cast=str, default=None):
    if name in a:
        return cast(a[a.index(name) + 1])
    return default


def toks(world):
    return set((world or "model").split(","))


def fill(a, w_):
    W, H = opt(a, "--width", int, 64), opt(a, "--height", int, 32)
    stride = opt(a, "--stride", int, 256)
    pk = opt(a, "--poke")
    op = "ADD" if "add" in w_ else ("XOR" if "xor" in w_ else "OR")
    if pk:
        v = int(re.match(r"pds:pixev:12\^=(0x[0-9a-f]+)$", pk).group(1), 16)
        ax = "x" if v < 0x1000 else "y"
        img = M.fill_image(W, H, ax, M.poke_field(ax, v), op)
    else:
        img = [M.COLOUR] * (W * H)
    if "fill-fault" in w_ and pk:
        return ("programs asm\njob: failed: job faulted, context lost (Input/output error)\nfill: FAILED\n", "", 1, [FAULT3D], {})
    wrong = [i for i, v in enumerate(img) if v != M.COLOUR]
    out = ["programs asm", "job: ok", "job time: 23 us"]
    if not ("nohash" in w_ and pk):
        out.append("target: %dx%d hash 0x%016x" % (W, H, M.fnv(img)))
    if wrong:
        out.append("diff: %d of %d pixels, first (%d, %d) 0x%08x expected 0x%08x" % (len(wrong), W * H, wrong[0] % W, wrong[0] // W,
                                                                                   img[wrong[0]], M.COLOUR))
    else:
        out.append("diff: 0 of %d pixels" % (W * H))
    out.append("outside: %d dwords" % (3 if "outside" in w_ and pk else 0))
    if wrong:
        out += ["fill: dword %d (%d, %d) = 0x%08x" % (wrong[0], wrong[0] % W, wrong[0] // W, img[wrong[0]]),
                "fill: FAIL, %d wrong dwords" % len(wrong)]
        return "\n".join(out) + "\n", "", 1, [], {}
    out.append("fill: ok, %dx%d at (0, 0), stride %d, colour 0x%08x" % (W, H, stride, M.COLOUR))
    return "\n".join(out) + "\n", "", 0, [], {}


def depth_tri(a, w_, ver):
    W, H = opt(a, "--width", int), opt(a, "--height", int)
    head = ["tri: render context for targets up to %dx%d" % (W, H)]
    if H % 2 and (ver == 4 or "refuse-odd" in w_):
        return "\n".join(head + ["layout: fb 0x3e013000", "tri: FAILED after 0 renders"]) + "\n", \
            "sgxfive-test: render: Invalid argument\n", 1, [], {}
    rule = "FLOOR" if "floor" in w_ else ("CEIL" if "ceil" in w_ else "A")
    pages = opt(a, "--depth-pages", int)
    words = [0xDEADBEEF] * (pages * 1024)
    aw, ah = M.G.area(W, H)
    band = M.band(rule, W, H)
    for y in range(ah):
        for x in range(aw):
            words[M.G.dword_index(x, y, W, H)] = 0x3E800000 + x + y if (x, y) in band else M.G.BG
    ddir = opt(a, "--depth-dump")
    if os.path.isdir(ddir) and "nodump" not in w_:         # the tool writes DIR/depth.1.bin and needs DIR (sgxfive-test.c depth_dump)
        files, dline = {os.path.join(ddir, "depth.1.bin"): struct.pack("<%dI" % len(words), *words)}, []
    else:
        files, dline = {}, ["depth #1: --depth-dump: No such file or directory"]
    out = head + ["job: ok"] + dline + [ "target: %dx%d hash 0x1" % (W, H), "diff: 0 of %d pixels" % (W * H), "outside: 0 dwords",
                  "tri %dx%d #1: %d triangle, 0 background, 0 other" % (W, H, W * H), "tri: 1 renders ok"]
    return "\n".join(out) + "\n", "", 0, [], files


def aa4_tri(a, w_):
    W, H = opt(a, "--width", int), opt(a, "--height", int)
    kp = {int(i): int(v, 16) for i, v in (re.match(r"1:ta:(\d+)=(0x[0-9a-f]+)$", a[j + 1]).groups()
                                          for j, t in enumerate(a) if t == "--kpoke-render")}
    ok = True if "hany" in w_ else (not kp if "allfault" in w_ else M.hcov_completes(W, H, kp))
    head = ["tri: render context for targets up to %dx%d" % (W, H), "tri: render context made for 4x targets (DRM_SGXFIVE_CTX_RENDER_AA_4X)"]
    head += ["tri: kpoke before render 1: ta:%d=0x%x" % (i, kp[i]) for i in sorted(kp)]
    rows = ["row %d: %s" % (y, " ".join(["0x%08x" % GREEN] * W)) for y in range(H)] if "--pixels" in a else []
    if ok:
        out = head + ["job: ok", "target: %dx%d hash 0x2" % (W, H), "diff: 0 of %d pixels" % (W * H), "outside: 0 dwords"] + rows + \
            ["tri %dx%d #1: %d triangle, 0 background, 0 other" % (W, H, W * H), "tri: 1 renders ok"]
        return "\n".join(out) + "\n", "", 0, [], {}
    out = head + ["job: failed: job faulted, context lost (Input/output error)", "target: %dx%d hash 0x3" % (W, H),
                  "diff: %d of %d pixels, first (1, 1) 0xff203040 expected 0xff00ff00" % (W * H // 2, W * H), "outside: 0 dwords"] + rows + \
        ["tri: FAILED after 0 renders"]
    return "\n".join(out) + "\n", "", 1, [FAULTTA if "q086-ta" in w_ else FAULT3D], {}


def answer(path, a, world):
    w_ = toks(world)
    ver = 4 if path.endswith("sgxfive-test-rgn4") else 6
    if a == ["fill"]:
        return ("job: ok\ndiff: 0 of 2048 pixels\n", "", 0, [], {}) if not os.environ.get("FAKE_HEALTH_BAD") else ("job: failed\n", "", 1, [], {})
    if a == ["tri"]:
        return ("job: ok\ndiff: 0 of 4096 pixels\n", "", 0, [], {}) if not os.environ.get("FAKE_HEALTH_BAD") else ("job: failed\n", "", 1, [], {})
    if a[0] == "fill":
        return fill(a, w_)
    if a[0] == "tri" and "--depth" in a:
        return depth_tri(a, w_, ver)
    if a[0] == "tri" and "--aa4" in a:
        return aa4_tri(a, w_)
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


def kept(d, stage, world="model", skip_groups=True, kp=KP):
    """A kept stage directory as run_stage.sh writes it (cases.tsv, NAME.txt.gz, .err.gz, .dmesg.gz, .depth.1.bin.gz), every row of
    tables/STAGE.txt answered by the world from its argv; a hypothesis group that reaches its count skips its other rows."""
    os.makedirs(d, exist_ok=True)
    hdr = "name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_req\tfault_word\tfree_kb\n"
    cases = [hdr]
    cnt, skipped = {}, set()
    for ln in open(os.path.join(kp, "tables", stage + ".txt")).read().splitlines():
        if not ln or ln.startswith("#"):
            continue
        name, sset, risk, knobs, tl, args = ln.split("|", 5)
        g = [k for k in knobs.split() if k.startswith("hypo:")]
        grp, gmax = (g[0].split(":")[1], int(g[0].split(":")[2])) if g else ("", 0)
        if skip_groups and grp in skipped:
            continue
        os.makedirs(os.path.join(d, "depth"), exist_ok=True)
        a = shlex.split(args.replace("$W", d))
        path = "/h/sgxfive-test-rgn4" if tl == "t4" else "/h/scratch/r6m/bin/sgxfive-test"
        out, err, rc, kmsg, files = answer(path, a, world)
        for p, b in files.items():
            with gzip.open(os.path.join(d, name + ".depth.1.bin.gz"), "wb") as f:
                f.write(b)
        for suf, txt in ((".txt", out), (".err", err), (".dmesg", "\n".join(kmsg))):
            with gzip.open(os.path.join(d, name + suf + ".gz"), "wb") as f:
                f.write(txt.encode())
        cls = "fault" if kmsg else ("ok" if rc == 0 or (rc == 1 and "diff:" in out and "FAILED after" not in out) else "fail")
        fi, fw = "-", "-"
        if kmsg:
            m = re.search(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)", kmsg[0])
            fi, fw = str(int(m.group(1), 16) & 0xFFFF), m.group(2)
            cnt[grp] = cnt.get(grp, 0) + 1
            if grp and cnt[grp] >= gmax:
                skipped.add(grp)
        cases.append("\t".join([name, stage, sset, risk, knobs, tl, args, str(rc), cls, fi, fw, "999999"]) + "\n")
    with open(os.path.join(d, "cases.tsv"), "w") as f:
        f.writelines(cases)
    return d


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "tool":
        sys.exit(tool(sys.argv[2:]))
    print(__doc__)
