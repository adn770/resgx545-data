# SPDX-License-Identifier: MIT
"""mock/world.py: r19-k0's fake laptop for kit/session.py mock. answer() sees the tool's name, the
argv and the world's tokens, never a case name; timeline() gives regtimeline's samples (the kit's
fake regtimeline runs the wrapped tool's fake, then prints them). P is what the GPU sees: the
debugfs knob render_pb_pages as the kit wrote it (the fake debugfs, $FAKE_DBGREAL), never a row's
name; N is the argv's --final-pb-pages (t18b writes the knob itself).

The fake is as strict as the tools on this session's forms (sgxfive-test of a581c06 = t10 and
ec50498 = t18b): `probe --tri pixel --width W --height H --vertices 1500 [--dump-render DIR] FILE`
(FILE must exist); `tri` with only the options the k0-z and geometry rows give, values checked;
--final-pb-pages only on t18b, 0x23 to 0x422, and only with --geometry (the tool's refusal, rc 2);
--geometry N needs -n > N; an output directory that does not exist fails as the tool does.
regtimeline (rt) must be `0 0.3 RT -- CMD...` with gen/plan.py's registers.

The DPM model (E625; fork 456404fcffe5 for the knob): the 1024x768 triangle needs U = 19 pages;
the geometry kick overflows (1 partial render, raised when 2 * thr0 < 21) iff thr0 = P - 0x22 < 19;
the final holds 2 + 5 pages after an overflowed kick, 19 + 5 otherwise, and overflows iff that is
above its threshold: N - 0x22 under H-UPD, the context's own (P's, raised) under H-IGN and H-LATE.
3072x2048 and 2048x2048 probes: partial renders as r13-dpm and r10-dpm read them.

EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model     H-UPD: every control reads its frozen value, both stages run (0, 0)
  late      H-LATE: the final's 0x0624 reads N - 0x22, the final follows P: the controls pass
            (f0-up's final completes either way), f0-down completes: both stages run
  ign       H-IGN: f0-same-1 reads 0x0624 0x400 after the final: f0 stops (24, the session ends)
  k0diff    the module changes the ZLS store: k0-z-t10's depth store differs: k0 stops (24,
            on_stop end: kg and f0 never run)
  a0diff    k0-a0's param dump differs from r10-dpm's (the probe's dumps are mock/fixtures, the
            kept ones): k0 stops (24)
  a0tail    k0-a0's param dump has r19-k0's 4 zero dwords past a stream's end (0x12de30): the
            masked control passes, every stage runs
  geo0      the geometry kick at P 0x28 does not overflow: k0-geo-t10-1 stops kg (24)
  noread    the timelines have no page count: k0-pr1-1 has no knob reading, the premise (25)
  downfail  f0-down's final ends `job: failed: job cancelled` (rc 1, no kernel line): soft, void,
            twice in a row: f0 stops (24)
  downjob   f0-down's final prints a non-overflow `job: failed:` but the tool ends rc 0:
            hook_check's stop:jobfail stops f0 (24)
  downhang  f0-down-1 hangs (a kernel hang line): unexpected, the session stops (4)
"""
import gzip
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# gen/plan.py's constants (tests/test_plan.py holds them equal; the mock tree has no gen/ import)
RT = ("0x012c,0x0620-0x0628,0x0658,0x0660,0x0668,0x0700,0x070c-0x0710,0x0720-0x0734,0x0748,"
      "0x0a74")
D_OFF = 0x22
RAISE = 0x20

EXPECT = {"model": (0, {"k0": 0, "kg": 0, "f0": 0}),
          "late": (0, {"k0": 0, "kg": 0, "f0": 0}),
          "ign": (24, {"k0": 0, "kg": 0, "f0": 24}),
          "k0diff": (24, {"k0": 24}),
          "a0diff": (24, {"k0": 24}),
          "a0tail": (0, {"k0": 0, "kg": 0, "f0": 0}),
          "geo0": (24, {"k0": 0, "kg": 24}),
          "noread": (25, {"k0": 25}),
          "downfail": (24, {"k0": 0, "kg": 0, "f0": 24}),
          "downjob": (24, {"k0": 0, "kg": 0, "f0": 24}),
          "downhang": (4, {"k0": 0, "kg": 0, "f0": 4})}

OVF = "scene overflowed the parameter buffer, context kept (No space left on device)"
PROBE_OVF = f"probe p1139-green: failed: {OVF}\n"
U1 = 19                 # pages of the 1024x768 triangle (E625)
HELD_AFTER_PR = 2       # pages a partial render leaves (E625 gps_left) [infer]
SECOND = 5              # the second triangle's pages [infer]
PROBE_NEED = {(3072, 2048): 0x2E0, (2048, 2048): 0x1A0}
PROBE_PR = {(3072, 2048): {0x294: 1, 0x1A0: 2, 0xC0: 4}, (2048, 2048): {0x140: 1}}

# options: name -> takes a value
TRI_OPTS = {"--width": 1, "--height": 1, "-n": 1, "--geometry": 1, "--keep-going": 0,
            "--keep-overflow": 0, "--wait-ms": 1, "--dump-render": 1, "--dump-each": 0,
            "--words": 1, "--regs": 1, "--max-width": 1, "--max-height": 1, "--tri-full": 0,
            "--tri-z": 1, "--depth": 0, "--depth-ctl": 1, "--depth-fill": 1, "--depth-store": 0,
            "--depth-dump": 1, "--poke": 1, "--pixels": 0, "--kpoke-render": 1}
T18B_ONLY = {"--final-pb-pages": 1}
PROBE_OPTS = {"--width": 1, "--height": 1, "--vertices": 1, "--dump-render": 1}


def usage(why):
    return dict(rc=2, err=f"sgxfive-test: {why}\nusage: sgxfive-test COMMAND ...\n")


def knob():
    p = os.path.join(os.environ.get("FAKE_DBGREAL", ""), "render_pb_pages")
    try:
        return int(open(p).read().strip(), 0)
    except (OSError, ValueError):
        return 0x422


def parse(argv, opts):
    got, pos, i = {}, [], 0
    while i < len(argv):
        a = argv[i]
        if a in opts:
            if opts[a]:
                if i + 1 >= len(argv):
                    return None, f"{a} without its value"
                got.setdefault(a, []).append(argv[i + 1])
                i += 2
            else:
                got[a] = [True]
                i += 1
        elif a.startswith("-"):
            return None, f"bad option {a}"
        else:
            pos.append(a)
            i += 1
    return (got, pos), None


def probe(argv, world):
    if argv[:3] != ["probe", "--tri", "pixel"]:
        return usage(f"no such probe form {argv[:3]}")
    p, why = parse(argv[3:], PROBE_OPTS)
    if p is None:
        return usage(why)
    o, pos = p
    if len(pos) != 1 or not os.path.exists(pos[0]) or o.get("--vertices") != ["1500"]:
        return usage("probe: one program FILE that exists, --vertices 1500")
    w, h = int(o["--width"][0]), int(o["--height"][0])
    if (w, h) not in PROBE_NEED:
        return usage(f"no model of {w}x{h}")
    thr0 = knob() - D_OFF
    out = (f"programs asm\nprobe p1139-green: scratch at 0x3f00a000 (64 KiB)\n"
           f"probe p1139-green: tri {w}x{h} (1500 vertices), pixel replaced\n")
    rc, files = 0, {}
    if thr0 < PROBE_NEED[(w, h)]:
        out += PROBE_OVF
        rc = 3
    if "--dump-render" in o:          # the kept a0-cal-2048 dumps (mock/fixtures, r10-dpm's)
        d = o["--dump-render"][0]
        for f in ("param", "tadata"):
            with gzip.open(os.path.join(HERE, "fixtures", f"a0-cal-2048.p1139-green.{f}.bin.gz")) as g:
                b = g.read()
            if "a0diff" in world and f == "param":
                b = bytes([b[0] ^ 1]) + b[1:]
            if "a0tail" in world and f == "param":      # r19-k0's 4 stale dwords, the other way
                b = b[:0x12DE30] + bytes(16) + b[0x12DE40:]
            files[os.path.join(d, f"p1139-green.{f}.bin")] = b
        out += f"probe p1139-green: render memory to {d}/p1139-green.{{param,tadata}}.bin (64, 32 bytes)\n"
    return dict(rc=rc, out=out, files=files)


def zls(o, world, tool):
    """k0-z: r13-zls zb-c-ctl's 64x32 store (its kept output, cut)."""
    w, h = int(o["--width"][0]), int(o["--height"][0])
    d = o["--depth-dump"][0]
    store = (0x3F000000).to_bytes(4, "little") * 2048 + (0xDEADBEEF).to_bytes(4, "little") * 16384
    if "k0diff" in world and tool == "t10":
        store = (0x3F000000).to_bytes(4, "little") * 2047 + (0xDEADBEEF).to_bytes(4, "little") * 16385
    changed = store.count((0x3F000000).to_bytes(4, "little"))
    out = (f"tri: render context for targets up to {w}x{h}\njob: ok\n"
           "depth #1: 18432 dwords, 0 changed, 1 distinct; 0x3f400000 x 18432\n"
           f"depth store #1: 18432 dwords, {changed} changed, 2 distinct\n"
           f"target: {w}x{h} hash 0xfc73845f9e506325\ndiff: 0 of {w * h} pixels\noutside: 0 dwords\n"
           f"tri {w}x{h} #1: {w * h} triangle, 0 background, 0 other; wrong 0 inside, 0 outside, "
           f"0 at edges; 0 if flipped; guard 0\ntri {w}x{h} #1: 39400 us\ntri: 1 renders ok\n")
    files = {os.path.join(d, "depth.1.bin"): (0x3F400000).to_bytes(4, "little") * 18432,
             os.path.join(d, "depth-store.1.bin"): store}
    return dict(rc=0, out=out, files=files)


def scene(o, world):
    """The geometry rows' renders: [(overflowed, thr after, partial renders, final)] per render."""
    n = int(o["-n"][0])
    p = knob()
    fin = int(o["--final-pb-pages"][0], 0) if "--final-pb-pages" in o else 0
    t0 = p - D_OFF
    out, held, raised = [], 0, False
    if "geo0" in world:
        t0 = 0x30
    for k in range(1, n + 1):
        final = k == 2 and fin
        need = U1 if k != 2 else SECOND
        held = (held + need) if k != 3 else U1
        if final and "ign" not in world and "late" not in world:
            thr = fin - D_OFF
        else:
            thr = t0 + (RAISE if raised and k == 2 else 0)
        ovf = held > thr
        if ovf:
            raised = raised or 2 * thr < U1 + 2
            held = HELD_AFTER_PR
        after = (fin - D_OFF) if (final and ("ign" not in world)) else t0
        out.append((ovf, after, int(ovf), bool(final)))
        if k == 2:
            raised = False
    return out


def geometry(o, world, tool):
    w, h = int(o["--width"][0]), int(o["--height"][0])
    n = int(o["-n"][0])
    geo = int(o["--geometry"][0])
    if geo >> (n - 1):
        return usage(f"--geometry is for tri, renders 1 to {n - 1}")
    fin = o.get("--final-pb-pages", [None])[0]
    if fin is not None:
        v = int(fin, 0)
        if not 0x23 <= v <= 0x422:
            return usage(f"bad --final-pb-pages {fin}")
    words_dir, dump_dir = o["--words"][0], o["--dump-render"][0]
    rs = scene(o, world)
    p = knob()
    lst = max(p, int(fin, 0)) if fin else p
    files, out = {}, [f"tri: render context for targets up to {w}x{h}"]
    if fin:
        out.append(f"tri: final renders' PB {fin} pages (debugfs render_final_pb_pages)")

    def snap(k, thr, pbt):
        files[os.path.join(words_dir, f"words.{k}.txt")] = "".join(
            f"pb:{i}=0x{v:08x}\n" for i, v in zip(range(10, 14), pbt)).encode()
        ta = [0] * 64
        if k == 1 and rs[0][0]:
            ta[35], ta[37], ta[38] = p - D_OFF - 2, 1 << 16 | (p - D_OFF), 0x20
        files[os.path.join(words_dir, f"ta3d.{k}.bin")] = b"".join(x.to_bytes(4, "little") for x in ta)
        out.append(f"tri: words {k} to {words_dir}/words.{k}.txt (60 bytes), {words_dir}/ta3d.{k}.bin "
                   "(256 bytes)")
        out.append(f"tri: registers at snapshot {k}")
        out.append("regs: 0x0600-0x0750 at 0x80080000")
        out.extend(f"reg 0x{r:04x} 0x{(thr if r == 0x624 else 0):08x}" for r in range(0x600, 0x754, 4))

    def pbw(pp):
        g = pp - D_OFF
        return (lst + 0x10, g, g, g - 0x100 if g > 0x100 else 0)
    snap(0, p - D_OFF, pbw(p))
    rc = 0
    for k, (ovf, after, _, final) in enumerate(rs, 1):
        # f0-down's final: a threshold below the 19 pages the open scene holds
        down = final and int(fin, 0) - D_OFF < U1 and bool(world & {"downhang", "downfail", "downjob"})
        if down and "downhang" in world:
            out.append("job: failed: job hung, context lost (Connection timed out)")
            return dict(rc=1, out="\n".join(out) + "\n", files=files,
                        kmsg=["sgxfive: render job 7 hung, recovered"])
        if down and "downfail" in world:
            out.append("job: failed: job cancelled, context lost (Operation canceled)")
            return dict(rc=1, out="\n".join(out) + "\n", files=files)
        if down and "downjob" in world:
            out.append("job: failed: job cancelled, context lost (Operation canceled)")
        else:
            out.append(f"job: failed: {OVF}" if ovf else "job: ok")
        stored = final and "ign" not in world
        snap(k, after, pbw(int(fin, 0) if stored else p) if final or k == 3 else pbw(p))
        if k == geo and not ovf:
            out.append(f"tri {w}x{h} #{k}: geometry only, the scene left open")
            continue
        if ovf:
            out.append(f"tri {w}x{h} #{k}: overflowed, 120000 triangle, 600000 background, 66432 "
                       "other; wrong 0 inside, 0 outside, 0 at edges; 0 if flipped; guard 0")
            if "--dump-each" in o:
                files[os.path.join(dump_dir, f"tri.{k}.param.bin")] = bytes(16)
                files[os.path.join(dump_dir, f"tri.{k}.tadata.bin")] = bytes(16)
            continue
        short = any(r[0] for r in rs[:k - 1])          # E038: the partial renders' tiles repainted
        out.append(f"target: {w}x{h} hash 0x1\ndiff: {9000 if short else 0} of {w * h} pixels\n"
                   "outside: 0 dwords\nlayout: fb 0x3e001000")
        out.append(f"tri {w}x{h} #{k}: {207456 - (9000 if short else 0)} triangle, 578976 background, "
                   f"0 other; wrong {9000 if short else 0} inside, 0 outside, 0 at edges; 0 if flipped; "
                   "guard 0")
        out.append(f"tri {w}x{h} #{k}: 20000 us")
        if short:
            rc = 1
    files[os.path.join(dump_dir, "tri.param.bin")] = bytes(16)
    files[os.path.join(dump_dir, "tri.tadata.bin")] = bytes(16)
    out.append("tri: 1 of 2 renders ok" if rc else "tri: renders ok")
    return dict(rc=rc, out="\n".join(out) + "\n", files=files)


def answer(tool, argv, world):
    if tool == "rt":
        if argv[:3] != ["0", "0.3", RT] or argv[3:4] != ["--"]:
            return usage(f"regtimeline: not TOTAL 0, LEAD 0.3 and the session's registers: {argv[:4]}")
        return None
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if tool not in ("t10", "t18b"):
        return usage(f"no such tool {tool}")
    if argv[0] == "probe":
        return probe(argv, world)
    if argv[0] != "tri":
        return usage(f"no form {argv[0]}")
    opts = dict(TRI_OPTS, **(T18B_ONLY if tool == "t18b" else {}))
    p, why = parse(argv[1:], opts)
    if p is None:
        return usage(why)
    o, pos = p
    if pos:
        return usage(f"stray {pos}")
    if "--final-pb-pages" in o and "--geometry" not in o:
        return usage("--final-pb-pages is for tri with --geometry")
    if "--depth" in o:
        return zls(o, world, tool)
    if "--geometry" in o:
        return geometry(o, world, tool)
    return usage("no model of this tri form")


def timeline(tool, regs, argv, rc, world):
    """regtimeline's samples: per render, its pages rising to the abort or the need, a partial
    render (0x0658 = 1) at each abort; 0x0624 the render's threshold."""
    if not argv or argv[0] not in ("probe", "tri"):
        return None
    p = knob()
    samples = []                        # (0x0624, pages, partial render)
    if argv[0] == "probe":
        o, _ = parse(argv[3:], PROBE_OPTS)[0]
        wh = (int(o["--width"][0]), int(o["--height"][0]))
        t0 = p - D_OFF
        n = PROBE_PR[wh].get(t0, 1 if t0 < PROBE_NEED[wh] else 0)
        for pg in range(0, min(t0, PROBE_NEED[wh]) + 1, 16):
            samples.append((t0, pg, 0))
        for _ in range(n):
            samples += [(t0, t0, 1), (t0, 2, 0)]
    else:
        rs = scene(parse(argv[1:], {**TRI_OPTS, **T18B_ONLY})[0][0], world)
        for ovf, after, nprs, final in rs:
            th = after
            for pg in range(1, 20, 6):
                samples.append((th, pg, 0))
            if ovf:
                samples += [(th, th, 1), (th, 2, 0)]
    if "noread" in world:
        samples = [(t, 0, f) for t, _, f in samples]
    rows = []
    for t, pg, f in samples:
        v = {0x624: t, 0x724: (pg << 16) | pg, 0x72C: 1 << 16 | 1, 0x658: f, 0x748: 0x1F}
        rows.append([v.get(r, 0) for r in regs])
    return rows
