# SPDX-License-Identifier: MIT
"""mock/world.py: r9-lgeo's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name; it returns None (the health
pair) or dict(rc, out, err, files={path: bytes}, kmsg=[lines], latch=(int, word)). As strict as
the rgn4 tool for what the session uses: an option it does not take, an odd target side, a
--scratch-pages outside 16 to 64 or a missing program file is refused as the tool refuses it.

  probe [--temps N] [--coords] [--pixels] [--scratch-pages N] FILE
        the program FILE is looked up by its sha256 in mock/progs.tsv (gen/lgen.py: what each
        program samples), and the 64 x 32 image drawn under the world's layout: model = the frozen
        hypotheses (type 4 H-CEIL through the linear axis, H-BLKROW through the map axis; type 3
        RASTERW at format 12 and H-DW8 at format 5; type 1 RASTERW), rival = a rival (type 4
        H-PACK, type 3 format 5 H-TX8, type 1 RASTERP2; the map-axis controls are unchanged)
  tri --tri-full --pixels ... [--kpoke-render 1:ta:N=V] --keep-going --dump-render DIR
        the region headers H-EVEN writes (model; gen/q139even.py) or the same with each 4 x 4
        block's slots numbered down its columns (rival: (c & 3) 4 + (r & 3)) into
        DIR/tri.tadata.bin (base 0x4000, three dwords a header, word 0 = (2 c) << 16 | 2 r, a
        stream block in DIR/tri.param.bin for each), the image 0xff00ff00 except 0xdeadbeef on
        the tiles whose header did not survive
EXPECT: the driver's status and each stage's runner status in every world:
  model, rival     every stage ends 0 (the scorer decides: rival's frozen rows FAIL)
  norows           probes print no pixel rows: tx6's first control has no reading, premise rc 25
  soft2            the two first linear rows of tx6 fail (rc 1, no diff line): the second soft
                   failure in a row stops tx6 (rc 24); the driver goes on, q139b runs
  txfault          a probe of a type 4 texture through the linear axis faults (BIF fault,
                   latched): tx6 stops rc 4, the driver too
  ctlnohash        tri prints no hash: q139b's first control has no reading, rc 25
  nohash           the poked tri rows print no hash: the second stops q139b (rc 24)
  fault            a poked tri row faults: q139b stops rc 4, the driver too
  nodump           tri writes no dump: q139b's first row's kept files lack the scorer's
                   .tri.*.bin, rc 23
A token for the scorer's tests only (tests/test_score.py, not EXPECT): hi (format 5 words with
the high half of a dword first)."""
import hashlib
import json
import os
import shlex
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
import q139even as E  # noqa: E402
import texmodel as T  # noqa: E402
import tx6model as X  # noqa: E402

ALL0 = {"tx6": 0, "q139b": 0}
EXPECT = {"model": (0, ALL0), "rival": (0, ALL0),
          "norows": (25, {"tx6": 25}),
          "soft2": (0, dict(ALL0, tx6=24)),
          "txfault": (4, {"tx6": 4}),
          "ctlnohash": (25, {"tx6": 0, "q139b": 25}),
          "nohash": (0, dict(ALL0, q139b=24)),
          "fault": (4, {"tx6": 0, "q139b": 4}),
          "nodump": (23, {"tx6": 0, "q139b": 23})}
GREEN, SENT = 0xFF00FF00, 0xDEADBEEF
FAULT = "sgxfive: BIF fault 0x90004 at 0x10000016 stalls job 9, recovering"
PROBE_VAL = {"--temps", "--scratch-pages"}
PROBE_FLAG = {"--coords", "--pixels"}
TRI_VAL = {"--width", "--height", "--max-width", "--max-height", "--wait-ms", "--kpoke-render", "--dump-render"}
TRI_FLAG = {"--pixels", "--tri-full", "--keep-going"}


def usage(cmd):
    return dict(rc=2, err="usage: sgxfive-test %s ... (an option the tool does not take)\n" % cmd)


def parse(argv, vals, flags, positional=False):
    """{option: [values]} and the positional arguments, or None on an option the tool refuses."""
    opts, pos, i = {}, [], 1
    while i < len(argv):
        a = argv[i]
        if a in vals and i + 1 < len(argv):
            opts.setdefault(a, []).append(argv[i + 1])
            i += 2
        elif a in flags:
            opts.setdefault(a, []).append(True)
            i += 1
        elif positional and not a.startswith("--"):
            pos.append(a)
            i += 1
        else:
            return None, None
    return opts, pos


def progs():
    out = {}
    for ln in open(os.path.join(KP, "mock/progs.tsv")).read().splitlines():
        if ln and not ln.startswith("#"):
            sha, meta = ln.split("\t", 1)
            out[sha] = json.loads(meta)
    return out


# ---- probe -------------------------------------------------------------------------------------
def image(meta, world, pages):
    rival = "rival" in world
    ty, w, h, xo, yo, lin, fmt = (meta[k] for k in ("ty", "w", "h", "xo", "yo", "linear", "fmt"))
    if ty == 4 and lin:
        img = X.type4_image("H-PACK" if rival else "H-CEIL", w, h, xo, yo, dwords=pages * 1024)
    elif ty == 4:
        img = T.tex_image("H-BLKROW", w, h, xo, yo, dwords=pages * 1024)
    elif ty == 3 and fmt == 5:
        hyp = "H-TX8" if rival else "H-DW8"
        img = [X.widen565(v) for v in X.pad16_words(hyp, w, h, hi_first="hi" in world)]
    elif ty == 3:
        img = T.tex_image("RASTERW", w, h, xo, yo, dwords=pages * 1024)
    elif ty == 1 and lin:
        img = T.tex_image("RASTERP2" if rival else "RASTERW", w, h, linear=True, dwords=pages * 1024)
    else:
        raise ValueError(meta)
    return [0xA0A1A2A3 if p is None else p for p in img]


def probe(argv, world):
    opts, pos = parse(argv, PROBE_VAL, PROBE_FLAG, positional=True)
    if opts is None or len(pos) != 1:
        return usage("probe")
    pages = int(opts.get("--scratch-pages", ["16"])[0], 0)
    if not 16 <= pages <= 64:
        return usage("probe")
    path = pos[0]
    if not os.path.isfile(path):
        return dict(rc=1, err="sgxfive-test: %s: No such file or directory\n" % path)
    meta = progs().get(hashlib.sha256(open(path, "rb").read()).hexdigest())
    if meta is None:
        return dict(rc=1, out="probe: a program the mock does not know\n")
    name = os.path.basename(path).rsplit(".", 1)[0]
    if meta["linear"] and meta["ty"] == 1 and "soft2" in world and meta["w"] in (32, 24):
        return dict(rc=1, out="programs asm\nprobe %s: failed: job timed out\n" % name)
    if meta["linear"] and meta["ty"] == 4 and "txfault" in world:
        return dict(rc=3, out="programs asm\nprobe %s: failed: job faulted\n" % name, kmsg=[FAULT], latch=(4, 0x10000016))
    img = image(meta, world, pages)
    out = ["programs asm", "probe %s: scratch at 0x3e003000 (%d KiB)" % (name, 4 * pages),
           "probe %s: job time: 624 us" % name]
    if "--pixels" in opts and "norows" not in world:
        out += ["probe %s: row %d: %s" % (name, y, " ".join("%08x" % p for p in img[64 * y:64 * y + 64]))
                for y in range(32)]
    return dict(out="\n".join(out) + "\n")


# ---- tri: the Q139 dumps -----------------------------------------------------------------------
def headers(w, h, args, world):
    """{slot: (c, r)} of the surviving headers in the world's rule."""
    own = E.headers(w, h, args, "H-EVEN")
    if "rival" in world:
        own = {sl - (sl & 15) + (c & 3) * 4 + (r & 3): (c, r) for sl, (c, r) in own.items()}
    return own


def tri_full(opts, world):
    w, h = int(opts["--width"][0]), int(opts["--height"][0])
    pokes = opts.get("--kpoke-render", [])
    if pokes and "fault" in world:
        return dict(rc=3, out="tri: render context for targets up to %dx%d\njob: failed\n" % (w, h),
                    kmsg=[FAULT], latch=(4, 0x10000016))
    args = " ".join("--kpoke-render " + p for p in pokes)
    own = headers(w, h, args, world)
    tx, ty = -(-w // 32), -(-h // 16)
    drawn = {t for t in own.values() if t[0] < tx and t[1] < ty}
    base, top = 0x4000, max(own) + 1
    td = bytearray(base + 12 * top + 0x1000)
    par = bytearray(0x2000 + 0x80 * top + 0x1000)
    for sl, (c, r) in own.items():
        if (c, r) in drawn or not (c < tx and r < ty):
            stream = 0x2000 + 0x80 * sl
            struct.pack_into("<3I", td, base + 12 * sl, (2 * c) << 16 | (2 * r), stream, 0)
            struct.pack_into("<3I", par, stream - 0x1000, 0x88000000 | sl, 0x00001000, 0xC0000000)
    g, b = "0x%08x" % GREEN, "0x%08x" % SENT
    rows, bad = [], 0
    for y in range(h):
        px = [g if (x // 32, y // 16) in drawn else b for x in range(w)]
        bad += px.count(b)
        rows.append("row %d: %s" % (y, " ".join(px)))
    out = ["tri: render context for targets up to %dx%d" % (w, h)]
    out += ["tri: kpoke before render 1: %s" % p.split(":", 1)[1] for p in pokes]
    out += ["job: ok"]
    if not ("ctlnohash" in world or ("nohash" in world and pokes)):
        out.append("target: %dx%d hash 0x%016x" % (w, h, len(drawn) * 0x9E3779B97F4A7C15 & (2 ** 64 - 1)))
    out += ["diff: %d of %d pixels" % (bad, w * h), "outside: 0 dwords", "layout: fb 0x3e001000",
            "tri %dx%d #1: %d triangle, 0 background, %d other; wrong %d inside, 0 outside, 0 at edges; 0 if flipped; "
            "guard 0" % (w, h, w * h - bad, bad, bad)] + rows
    files = {}
    d = opts["--dump-render"][0]
    if "nodump" not in world:
        files = {os.path.join(d, "tri.param.bin"): bytes(par), os.path.join(d, "tri.tadata.bin"): bytes(td)}
        out.append("probe tri: render memory to %s/tri.{param,tadata}.bin (%d, %d bytes)" % (d, len(par), len(td)))
    out.append("tri: 0 of 1 renders ok" if bad else "tri: 1 renders ok")
    return dict(rc=1 if bad else 0, out="\n".join(out) + "\n", files=files)


def tri(argv, world):
    opts, _ = parse(argv, TRI_VAL, TRI_FLAG)
    if opts is None or "--width" not in opts or "--height" not in opts:
        return usage("tri")
    w, h = int(opts["--width"][0]), int(opts["--height"][0])
    if w % 2 or h % 2 or w > 4096 or h > 4096:
        return dict(rc=1, out="tri: render context for targets up to %dx%d\njob: rejected (Invalid argument)\n" % (w, h),
                    err="sgxfive-test: render: Invalid argument\n")
    if "--tri-full" in opts and "--dump-render" in opts:
        if not os.path.isdir(opts["--dump-render"][0]):
            return dict(rc=1, err="sgxfive-test: %s: No such file or directory\n" % opts["--dump-render"][0])
        return tri_full(opts, world)
    return usage("tri")


def answer(tool, argv, world):
    if tool != "t4" or not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe":
        return probe(argv, world)
    if argv[0] == "tri":
        return tri(argv, world)
    return usage(argv[0])


if __name__ == "__main__":      # python3 mock/world.py WORLD ARGS...: one answer, for a look by hand
    print(answer("t4", shlex.split(" ".join(sys.argv[2:])), set(sys.argv[1].split(",")))["out"][:2000])
