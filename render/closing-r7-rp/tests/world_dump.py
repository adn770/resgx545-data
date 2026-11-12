"""world_dump.py: the fake tool's answers for the `dump` area's rows (q293, q139), from ARGV ONLY (never a case name), and
kept(dir, stage, tokens): a kept stage directory as the runner writes it (cases.tsv, NAME.txt.gz, NAME.err.gz,
NAME.dmesg.gz, NAME.snap0/9.regs.gz, every file of $W/dump as NAME.<basename>.gz, all gzip -n).

  q293 rows (tri ... --poke cmd:1=0x40000000 at 64 x 64, -n 2 or 3, --geometry): the TA writes one 27-dword object per
       render (the 0x40000000 layout: zero at +11, format word at +12, E897), the kernel's par:N pokes land before their
       render (kmsg 'kpoke ... applied', the dump's dwords), the last render draws: the world's reading of the 3D (model:
       render 2's object draws iff its dword 38 is the format word 0x00040101 and render 1's object is displaced; E829's
       twin draws when render 1's dword 11 is it)
  q139 rows (tri --tri-full --pixels W x H, --kpoke-render 1:ta:N=V or none): the 1x region headers of a fake layout
       (macrotiles of the library's rule numbered down then across, raster inside, padding headers flagged outside), the
       image; a poked row's wrong tiles are its dataset's kept set (read from the session's frozen q139 files by the row's
       ARGS), whose headers the model moves off their slot
Tokens (FAKE_WORLD, comma separated; model = every frozen prediction holds):
  q293 rivals  obj2dark (u3: render 2's object drew nothing), plain (the objects 26 apart, format word at +11: u1 fails),
               t7drift (u2's hash differs), nopoke (no kernel 'applied' line, the pokes not in the dump), fault3 (render 3
               faults on the 3D side), nodump (no --dump-render file written)
  q139 rivals  inplace (wrong tiles keep their header in place: H-INPLACE), movedrew (one drawn tile's header moved too),
               norepl (one more wrong tile in every poked row: nothing replicates), badbase (the baseline lacks one tile's
               header), nodump
"""
import gzip
import os
import re
import shlex
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "score"))
import lib_dump as L  # noqa: E402

FAULT3D = ("gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90100 at 0x10000016 (PD 0x30d6e000) stalls job 86, "
           "recovering")
KPOKE = "gma500 0000:00:02.0: [drm] sgxfive: kpoke %s applied"
GREEN, BG, SENT = 0xff00ff00, 0xff000080, 0xdeadbeef
OBJ = [0x04000004, 0x00030001, 0x04000000, 0x3f800000, 0x3f800001, 0x3f800001, 0x3f800000, 0x01d00200, 0x000010f0,
       0x4e224830, 0x000e1010, 0x00000000, 0x00040101, 0, 0, 0, 0, 0x00100000, 0x00001000, 0x00003f00, 0x10500010,
       0x3f000000, 0x00105000, 0x00001000, 0x50003f00, 0x10500010, 0x3f000000]      # E888 t7's object (dwords 27-53)
PARAM_BYTES = 0x10000


def opt(a, name, cast=str, default=None):
    return cast(a[a.index(name) + 1]) if name in a else default


def all_opts(a, name):
    return [a[i + 1] for i, x in enumerate(a) if x == name]


def handles(tool, argv):
    a = list(argv)
    if tool != "t4" or not a or a[0] != "tri" or "--dump-render" not in a:
        return False
    if "--poke" in a and "cmd:1=0x40000000" in all_opts(a, "--poke") and opt(a, "--width") == "64":
        return True
    return "--pixels" in a and "--tri-full" in a and opt(a, "--width") in ("256", "640")


def _fnv(words):
    h = 0xcbf29ce484222325
    for w in words:
        h = ((h ^ w) * 0x100000001b3) & 0xffffffffffffffff
    return h


def _write_dump(d, param, tadata):
    with open(os.path.join(d, "tri.param.bin"), "wb") as f:
        f.write(param)
    with open(os.path.join(d, "tri.tadata.bin"), "wb") as f:
        f.write(tadata)


def _no_dir(out, n_ok, renders):
    return out + "tri: FAILED after %d renders\n" % n_ok, "sgxfive-test: --dump-render: No such file or directory\n", 1


# ---- q293 ------------------------------------------------------------------------------------------------------------------------
def q293(a, tok):
    n = opt(a, "-n", int, 1)
    geo = {int(x) for x in all_opts(a, "--geometry")}
    kp = [s.split(":", 1) for s in all_opts(a, "--kpoke-render")]
    d = opt(a, "--dump-render")
    step = 26 if "plain" in tok else 27
    words = [0] * (PARAM_BYTES // 4)
    out, kmsg = ["tri: render context for targets up to 64x64"], []
    for r in range(1, n + 1):
        out.append("tri: triangle (0,0) (192,0) (0,192), depth 0.5 0.5 0.5")
        for rn, spec in kp:
            if int(rn) == r:
                out.append("tri: kpoke before render %d: %s" % (r, spec))
                if "nopoke" not in tok:
                    s = L.norm_spec(spec)
                    kmsg.append(KPOKE % s)
                    dw, v = s[4:].split("=")
                    words[int(dw)] = int(v, 16)
        o = OBJ[:] if step == 27 else OBJ[:11] + OBJ[12:]
        base = (r - 1) * step
        words[base:base + len(o)] = o                  # render r's TA writes its object after the pokes before it
        if r in geo:
            out += ["job: ok", "tri 64x64 #%d: geometry only, the scene left open" % r]
            continue
        if "fault3" in tok:
            return "\n".join(out + ["job: failed: job faulted"]) + "\n", "", 1, [FAULT3D]
        # the world's 3D: the first object in the bit-29-set layout (format word at +11) draws
        draws = any(words[s + 11] == 0x00040101 for s in range(0, step * r, step))
        if "obj2dark" in tok and n == 3:
            draws = words[11] == 0x00040101
        if step == 26:
            draws = True
        tri = 4096 if draws else 0
        wrong = 0 if draws else 3969
        h = 0xd2bfb75560f4c325 if draws else (0x8ea26cdfee74a325 if "t7drift" not in tok else 0x1234)
        out += ["job: ok", "target: 64x64 hash 0x%016x" % h,
                "diff: %d of 4096 pixels%s" % (wrong, ", first (1, 1) 0xff000080 expected 0xffff0000" if wrong else ""),
                "outside: 0 dwords", "layout: fb 0x3e001000",
                "tri 64x64 #%d: %d triangle, %d background, 0 other; wrong %d inside, 0 outside, 0 at edges; %d if flipped; "
                "guard 0" % (r, tri, 4096 - tri, wrong, wrong),
                "tri 64x64 #%d: 10118 us" % r]
    ok = 0 if wrong else 1
    if not os.path.isdir(d or ""):
        o, e, rc = _no_dir("\n".join(out) + "\n", ok, n)
        return o, e, rc, kmsg
    if "nodump" not in tok:
        _write_dump(d, struct.pack("<%dI" % len(words), *words), b"\0" * 0x4000 + b"\1" * 64 + b"\0" * 0x1000)
    out.append("probe tri: render memory to %s/tri.{param,tadata}.bin (%d, %d bytes)" % (d, PARAM_BYTES, 0x5040))
    out.append("tri: %d of %d renders ok" % (ok, n) if wrong else "tri: %d renders ok" % n)
    return "\n".join(out) + "\n", "", 1 if wrong else 0, kmsg


# ---- q139 ------------------------------------------------------------------------------------------------------------------------
def rule(w, h):
    tx, ty = -(-w // 32), -(-h // 16)
    n = 4 if w * h >= 640 * 480 else 2
    mx, my = -(-(-(-tx // n)) // 4) * 4, -(-(-(-ty // n)) // 4) * 4
    return tx, ty, n, mx, my


def layout(w, h):
    """[(slot, x, y, mt, inside)] of the fake 1x layout: macrotiles down then across, raster inside each."""
    tx, ty, n, mx, my = rule(w, h)
    out = []
    for mc in range(n):
        for mr in range(n):
            mt = mc * n + mr
            for ly in range(my):
                for lx in range(mx):
                    x, y = mc * mx + lx, mr * my + ly
                    out.append((len(out), x, y, mt, x < tx and y < ty))
    return out


def frozen_wrong(w, h, spec):
    """The dataset's kept wrong set of the q139 row with these args (the session's frozen table and predictions)."""
    rows = {}
    for ln in open(os.path.join(KP, "tables", "q139.txt")).read().splitlines():
        if ln.startswith("#") or not ln.strip():
            continue
        name, _s, _r, _k, _t, args = ln.split("|", 5)
        t = shlex.split(args.replace('"$W/dump"', "D"))
        key = (opt(t, "--width", int), opt(t, "--height", int), tuple(all_opts(t, "--kpoke-render")))
        rows[key] = name
    name = rows[(w, h, tuple(spec))]
    P = L.load_predictions(os.path.join(KP, "predictions", "q139.tsv"))
    return L.tiles_parse(L.pred(P, name, "kept_wrong"))


def q139(a, tok):
    w, h = opt(a, "--width", int), opt(a, "--height", int)
    spec = all_opts(a, "--kpoke-render")
    d = opt(a, "--dump-render")
    wrong = frozen_wrong(w, h, spec) if spec else set()
    if wrong and "norepl" in tok:
        wrong = wrong | {(0, 0)} if (0, 0) not in wrong else wrong - {(0, 0)}
    lay = layout(w, h)
    base = 0x4000
    td = bytearray(base + 12 * len(lay) + 0x1000)
    par = bytearray(0x2000 + 0x80 * len(lay) + 0x1000)
    moved = set(wrong) if "inplace" not in tok else set()
    if wrong and "movedrew" in tok:
        drawn = sorted(L.target_tiles(w, h) - wrong)
        moved.add(drawn[0])
    for sl, x, y, mt, inside in lay:
        if not spec and "badbase" in tok and (x, y) == (1, 1):
            continue
        flags = 0x04 if sl % (len(lay) // (rule(w, h)[2] ** 2)) == 0 else 0
        stream = 0x2000 + 0x80 * sl if inside else 0
        if not inside:
            flags |= 0x02
        px = x
        if inside and (x, y) in moved:
            px, stream = 0x7f, 0                       # the header names no target tile: moved off its slot
        struct.pack_into("<3I", td, base + 12 * sl, flags << 24 | (2 * px) << 16 | mt << 12 | (2 * y), stream, 0)
        if stream:
            struct.pack_into("<3I", par, stream - 0x1000, 0x88000000 | sl, 0x00001000, 0xc0000000)
    img = []
    for y in range(h):
        img.append([SENT if (x // 32, y // 16) in wrong else GREEN for x in range(w)])
    bad = sum(row.count(SENT) for row in img)
    first = next(((x, y) for y in range(h) for x in range(w) if img[y][x] != GREEN), None)
    out = ["tri: render context for targets up to %dx%d" % (w, h),
           "tri: triangle (0,0) (%d,0) (0,%d), depth 0.5 0.5 0.5" % (3 * w, 3 * h)]
    out += ["tri: kpoke before render 1: %s" % s.split(":", 1)[1] for s in spec]
    kmsg = [KPOKE % L.norm_spec(s.split(":", 1)[1]) for s in spec]
    out += ["job: ok", "target: %dx%d hash 0x%016x" % (w, h, _fnv([len(wrong)] + sorted(x * 64 + y for x, y in wrong))),
            "diff: %d of %d pixels%s" % (bad, w * h, ", first (%d, %d) 0xdeadbeef expected 0xff00ff00" % first if first else ""),
            "outside: 0 dwords", "layout: fb 0x3e001000",
            "tri %dx%d #1: %d triangle, 0 background, %d other; wrong %d inside, 0 outside, 0 at edges; %d if flipped; guard 0"
            % (w, h, w * h - bad, bad, bad, bad), "tri %dx%d #1: 20344 us" % (w, h)]
    out += ["row %d: %s" % (y, " ".join("0x%08x" % p for p in row)) for y, row in enumerate(img)]
    ok = 0 if bad else 1
    if not os.path.isdir(d or ""):
        o, e, rc = _no_dir("\n".join(out) + "\n", ok, 1)
        return o, e, rc, kmsg
    if "nodump" not in tok:
        _write_dump(d, bytes(par), bytes(td))
    out.append("probe tri: render memory to %s/tri.{param,tadata}.bin (%d, %d bytes)" % (d, len(par), len(td)))
    out.append("tri: 0 of 1 renders ok" if bad else "tri: 1 renders ok")
    return "\n".join(out) + "\n", "", 1 if bad else 0, kmsg


def answer(tool, argv, tokens):
    a = list(argv)
    tok = set(tokens or {"model"})
    w = opt(a, "--width", int, 64)
    if tool == "t4" and w % 2:
        return dict(out="tri: render context for targets up to %dx64\njob: rejected (Invalid argument)\n" % w,
                    err="sgxfive-test: render: Invalid argument\n", rc=1, kmsg=[])
    if "cmd:1=0x40000000" in all_opts(a, "--poke"):
        o, e, rc, k = q293(a, tok)
    else:
        o, e, rc, k = q139(a, tok)
    return dict(out=o, err=e, rc=rc, kmsg=k)


# ---- a kept stage directory, as the runner writes it -----------------------------------------------------------------------------
def _gz(path, data):
    if isinstance(data, str):
        data = data.encode()
    with open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as f:
            f.write(data)


def table_rows(stage, kp=KP):
    out = []
    for ln in open(os.path.join(kp, "tables", stage + ".txt")).read().splitlines():
        if ln.startswith("#") or not ln.strip():
            continue
        out.append(ln.split("|", 5))
    return out


def kept(d, stage, tokens=("model",), kp=KP, work=None):
    """Run every row of tables/STAGE.txt through the world into the kept directory d (runner naming)."""
    import tempfile
    os.makedirs(d, exist_ok=True)
    lines = ["\t".join(["name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_req", "fault_word",
                        "free_kb"])]
    for name, st, risk, knobs, tool, args in table_rows(stage, kp):
        w = tempfile.mkdtemp(prefix="wd.", dir=work or d)
        os.makedirs(os.path.join(w, "depth"))
        os.makedirs(os.path.join(w, "dump"))
        argv = [x.replace("$W", w) for x in shlex.split(args)]
        r = answer(tool, argv, set(tokens))
        cls = "ok"
        if any("BIF fault" in k for k in r["kmsg"]):
            cls = "fault"
        elif r["rc"] != 0 and not (r["rc"] == 1 and "expectdiff" in knobs.split() and re.search(r"^diff:", r["out"], re.M)):
            cls = "fail"
        _gz(os.path.join(d, name + ".txt.gz"), r["out"])
        _gz(os.path.join(d, name + ".err.gz"), r["err"])
        _gz(os.path.join(d, name + ".dmesg.gz"), "".join("[1.0] %s\n" % k for k in r["kmsg"]))
        _gz(os.path.join(d, name + ".snap0.regs.gz"), "0x0c04 0x00000000\n")
        _gz(os.path.join(d, name + ".snap9.regs.gz"), "0x0c04 0x00000000\n")
        for sub in ("depth", "dump"):
            for f in sorted(os.listdir(os.path.join(w, sub))):
                with open(os.path.join(w, sub, f), "rb") as fh:
                    _gz(os.path.join(d, name + "." + f + ".gz"), fh.read())
        fw = re.search(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)", "".join(r["kmsg"]))
        lines.append("\t".join([name, stage, st, risk, knobs, tool, args, str(r["rc"]), cls, "-",
                                fw.group(2) if fw else "-", "900000"]))
        for sub in ("depth", "dump"):
            for f in os.listdir(os.path.join(w, sub)):
                os.remove(os.path.join(w, sub, f))
            os.rmdir(os.path.join(w, sub))
        os.rmdir(w)
    with open(os.path.join(d, "cases.tsv"), "w") as f:
        f.write("\n".join(lines) + "\n")
    return d
