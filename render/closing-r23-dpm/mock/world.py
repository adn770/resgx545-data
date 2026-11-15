# SPDX-License-Identifier: MIT
"""mock/world.py: r23-dpm's fake laptop for kit/session.py mock (r21-zls's for rl and zn, r20-own's
for og, with t22b's keep, background and --ctx2-geometry lines). answer() sees the tool's name, the
argv, the world's tokens and the debugfs knobs the runner wrote ($FAKE_DBGREAL), never a case
name; timeline() gives regtimeline's samples. The pages are what the GPU sees: render_pb_pages as
the kit wrote it, the final render's N from --final-pb-pages.

The scene's page need (E625): 19 pages for the 1024x768 triangle. A render overflows when its
threshold (P - 0x22, or N - 0x22 for the final of a geometry job) is below the need; its first
abort is raised iff 2 thr < 21 (TA3DCtl dword 38 = 0x20 in ta3d.1.bin, else 0). A 64x64 owner
(og) never overflows at 0x422 or 0x200.

As strict as t22b (b2b6bc0) on this session's rows: `tri` only, the options it takes here with
their arity; --final-pb-pages needs --geometry; --depth-ctl-next needs -n 2; --refill K:BUF=V
needs 2 <= K <= -n and --depth for BUF depth; --move N:DX,DY needs 1 <= N <= -n; --keep-target K
needs 2 <= K <= -n and no --ctx2; --bg-pds FILE:N and --bg-pixel FILE need their files;
--ctx2-geometry N needs --ctx2 and N <= -n; --kept-copy and --close-first-early need --ctx2; the
--depth options need --depth. regtimeline (rt) must be `0 0.3 REGS -- CMD...` with plan.RT.

EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model     H-RELOAD, H-TAKICK, H-LOADNODRAW, every premise and control as predicted: 0
  alt       H-REPAINT, H-RENDEREND, H-HOSTBITS: every stage runs (0)
  finalovf  the final render overflows too: rl-c2's premise stops rl (24), og runs, zn-c's premise
            stops zn (24); the driver goes on (0)
  noregs    no --regs block: rl-c2 (a control) has no thr reading: the session stops (25)
  nogeo     the tool makes no geometry kick of the second context (no kept.geo.1.bin): the runner
            stops at og's first row (23: a file the scorer reads was not kept), before hook_check
  geoempty  every copy after the second context's kick reads 0 bytes: no stop (cannot tell rows)
  fault     the second context's render faults in og's second row: the session stops (4)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import plan as PL  # noqa: E402

ALL0 = {"rl": 0, "og": 0, "zn": 0}
EXPECT = {"model": (0, ALL0),
          "alt": (0, ALL0),
          "finalovf": (0, {"rl": 24, "og": 0, "zn": 24}),
          "noregs": (25, {"rl": 25}),
          "nogeo": (23, {"rl": 0, "og": 23}),
          "geoempty": (0, ALL0),
          "fault": (4, {"rl": 0, "og": 4})}
VAL = {"--width", "--height", "-n", "--geometry", "--wait-ms", "--dump-render", "--words", "--regs",
       "--poke", "--depth-ctl", "--depth-ctl-next", "--depth-fill", "--depth-dump",
       "--depth-store-fill", "--depth-pages", "--move", "--final-pb-pages", "--refill", "--bg-pds",
       "--bg-pixel", "--keep-target", "--kept-copy", "--kpoke-render", "--ctx2-geometry"}
FLAGS = {"--keep-going", "--keep-overflow", "--dump-each", "--depth", "--depth-store", "--ctx2",
         "--close-first-early"}
OVF = "job: failed: scene overflowed the parameter buffer, context kept (No space left on device)\n"
LOAD, STORE = 0x3E001000, 0x3E341000
RD12, RD13 = 0x1000, 0x341000
OG_SIZE = PL.OG_SIZE


def usage(why):
    return dict(rc=2, err=f"sgxfive-test: {why}\nusage: sgxfive-test COMMAND ...\n")


def dbg(name, default):
    try:
        return open(os.path.join(os.environ.get("FAKE_DBGREAL", ""), name)).read().strip()
    except OSError:
        return default


def counter(name):
    """the row count of a stage form in this world (FAKE_DIR survives from job to job)"""
    d = os.environ.get("FAKE_DIR")
    if not d:
        return 1
    p = os.path.join(d, name)
    n = int(open(p).read()) + 1 if os.path.exists(p) else 1
    with open(p, "w") as f:
        f.write(str(n))
    return n


def parse(tool, argv):
    if tool != "t22b":
        return None, f"{tool}: no row of this session runs it"
    if argv[:1] != ["tri"]:
        return None, f"no such command {argv[:1]}"
    o, i = {}, 1
    while i < len(argv):
        a = argv[i]
        if a in VAL:
            if i + 1 >= len(argv):
                return None, f"{a} without its value"
            o.setdefault(a, []).append(argv[i + 1])
            i += 2
        elif a in FLAGS:
            o[a] = True
            i += 1
        else:
            return None, f"unknown option {a}"
    for a in ("--keep-target", "--bg-pds", "--bg-pixel", "--ctx2-geometry", "--kept-copy"):
        if len(o.get(a, [])) > 1:
            return None, f"{a} is given once"
    geo = int(o.get("--geometry", ["0"])[0], 0)
    n = int(o.get("-n", ["1"])[0])
    if "--final-pb-pages" in o and not geo:
        return None, "--final-pb-pages is for tri with --geometry"
    if geo >> (n - 1):
        return None, "--geometry: the last render closes the scene"
    if "--depth-ctl-next" in o and n < 2:
        return None, "--depth-ctl-next needs -n 2"
    for r in o.get("--refill", []):
        k, _, rest = r.partition(":")
        buf, _, v = rest.partition("=")
        if not (2 <= int(k) <= n) or buf != "depth" or "--depth" not in o or not v:
            return None, f"bad --refill {r}"
    for m in o.get("--move", []):
        k, _, d = m.partition(":")
        if not (1 <= int(k) <= n) or len(d.split(",")) != 2:
            return None, f"bad --move {m}"
    if any(k.startswith("--depth-") for k in o) and "--depth" not in o:
        return None, "the --depth options need --depth"
    if "--keep-target" in o and (not 2 <= int(o["--keep-target"][0]) <= n or "--ctx2" in o):
        return None, "--keep-target K is for renders 2 to -n, without --ctx2"
    if "--bg-pds" in o:
        f, _, nd = o["--bg-pds"][0].rpartition(":")
        if not f or not nd.isdigit() or not os.path.isfile(f):
            return None, f"bad --bg-pds {o['--bg-pds'][0]}"
    if "--bg-pixel" in o and not os.path.isfile(o["--bg-pixel"][0]):
        return None, f"--bg-pixel {o['--bg-pixel'][0]}: No such file or directory"
    if "--ctx2-geometry" in o and ("--ctx2" not in o or int(o["--ctx2-geometry"][0]) > n
                                   or "--final-pb-pages" in o):
        return None, "--ctx2-geometry N is for tri --ctx2, renders 1 to -n"
    if ("--kept-copy" in o or "--close-first-early" in o) and "--ctx2" not in o:
        return None, "--kept-copy and --close-first-early are for --ctx2"
    return o, None


def plan_job(o, world):
    """[(overflowed, threshold, raised)] per render the 3D runs (a geometry render that does not
    overflow runs none: None)."""
    p = int(dbg("render_pb_pages", "0x422"), 0)
    n = int(o.get("-n", ["1"])[0])
    geo = int(o.get("--geometry", ["0"])[0], 0)
    nfin = int(o["--final-pb-pages"][0], 0) if "--final-pb-pages" in o else p
    out = []
    for i in range(n):
        thr = (p if geo >> i & 1 or not geo else nfin) - PL.D_OFF
        if "finalovf" in world and geo and not geo >> i & 1:
            thr = p - PL.D_OFF
        ov = thr < PL.U_TRI
        out.append(None if geo >> i & 1 and not ov else (ov, thr, ov and 2 * thr < PL.U_TRI + 2))
    return out


def ctl_of(o, k):
    c = o.get("--depth-ctl", ["0x0"])[0]
    if k > 1 and "--depth-ctl-next" in o:
        c = o["--depth-ctl-next"][0]
    return int(c, 0)


def words_txt(o, k):
    return "".join(f"rd:{i}=0x{v:08x}\n" for i, v in
                   ((1, 0x3E000000), (11, ctl_of(o, max(k, 1))), (12, RD12), (13, RD13),
                    (53, 0x480)))


def zstore(form, nd):
    """the store after the final at the refill 0.75 (score.py's forms, window dwords by E465's
    layout): nodraw = H-LOADNODRAW (0.75 everywhere), loadtest = H-HOSTBITS of a load row (0.5
    inside T2), hostbits = zn-c's no-load form (0.5 inside T2 and T1, 1.0 elsewhere); cached in
    FAKE_DIR for the world."""
    d = os.environ.get("FAKE_DIR")
    p = os.path.join(d, f"zstore.{form}.{nd}.bin") if d else None
    if p and os.path.exists(p):
        return open(p, "rb").read()
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "score"))
    import score as SC
    base = PL.ONE if form == "hostbits" else PL.R75
    v = [base] * nd
    if form != "nodraw":
        for i, e1, e2 in SC.window2(PL.MOVE):
            if i < nd and (e2 != 0 or (form == "hostbits" and e1 == 1)):
                v[i] = PL.HALF
    b = struct.pack("<%dI" % nd, *v)
    if p:
        with open(p, "wb") as f:
            f.write(b)
    return b


def keep_report(o, jobs, world):
    """render 2's keep line: red the final's triangle (and render 1's rest when not raised)."""
    if "--bg-pds" not in o:
        return (f"tri 1024x768 #2: target kept, {PL.NPIX} pixels changed, colours 0x{PL.NAVY:08x} "
                f"{PL.BG_PIX}, 0x{PL.RED:08x} {PL.T_PIX}; guard 0\n")
    red = PL.T_PIX + (18582 if jobs[0] and not jobs[0][2] else 0)
    green = 100000
    if "alt" in world:          # H-REPAINT: render 1's green painted with the sentinel
        return (f"tri 1024x768 #2: target kept, {red + green} pixels changed, colours "
                f"0x{PL.SENT:08x} {PL.NPIX - red}, 0x{PL.RED:08x} {red}; guard 0\n")
    return (f"tri 1024x768 #2: target kept, {red} pixels changed, colours 0x{PL.SENT:08x} "
            f"{PL.NPIX - red - green}, 0x{PL.RED:08x} {red}, 0x{PL.GREEN:08x} {green}; guard 0\n")


def tri(o, world):
    WR = o["--dump-render"][0] if "--dump-render" in o else None
    WD = o["--words"][0] if "--words" in o else None
    w, h = int(o["--width"][0]), int(o["--height"][0])
    jobs = plan_job(o, world)
    ours = "--bg-pds" in o
    keep = int(o["--keep-target"][0]) if "--keep-target" in o else 0
    out, files, rc = "", {}, 0
    if ours:
        out += ("tri: background object's programs: primary pds_bg_pos (12 data dwords), pixel "
                "shader bg_reload_1024 (32 temporaries)\n")
    if "--depth" in o:
        out += f"depth: 0x{LOAD:08x} 832 pages, fill x, base 0x3e000000, control 0x{ctl_of(o, 1):08x}\n"
        if "--depth-store" in o:
            out += f"depth store: 0x{STORE:08x} 832 pages, fill x\n"
    if WD:
        files[f"{WD}/words.0.txt"] = words_txt(o, 0).encode()
    for i, j in enumerate(jobs):
        k = i + 1
        if k >= 2 and "--refill" in o:
            for r in o["--refill"]:
                if int(r.split(":")[0]) == k:
                    out += f"refill: render {k} buf depth value {r.split('=')[1]}\n"
        if keep == k:
            out += f"tri: render {k} on the target as render {k - 1} left it (--keep-target)\n"
        if WD:
            files[f"{WD}/words.{k}.txt"] = words_txt(o, k).encode()
            ta3d = bytearray(236)
            if j is not None and j[2]:
                ta3d[38 * 4] = 0x20
            files[f"{WD}/ta3d.{k}.bin"] = bytes(ta3d)
        if j is None:
            out += f"job: ok\ntri {w}x{h} #{k}: geometry only, the scene left open\n"
            continue
        ov, thr, _ = j
        out += OVF if ov else "job: ok\n"
        if "noregs" not in world:
            out += "regs: 0x0600-0x0750 at 0x80080000\n" + "".join(
                f"reg 0x{r:04x} 0x{thr if r == 0x624 else 0:08x}\n" for r in range(0x600, 0x754, 4))
        if "--depth" in o:
            ld = int(o["--depth-ctl"][0], 0) & 0x4002
            nd = int(o["--depth-pages"][0], 0) * 1024
            depth = (PL.ONE).to_bytes(4, "little") * nd
            store = depth
            if k == len(jobs) and "--refill" in o:
                store = zstore(("loadtest" if "alt" in world else "nodraw") if ld else "hostbits",
                               nd)
            dd = o.get("--depth-dump", [None])[0]
            if dd:
                files[f"{dd}/depth.{k}.bin"] = depth
                if "--depth-store" in o:
                    files[f"{dd}/depth-store.{k}.bin"] = store
            out += f"depth #{k}: {nd} dwords, {nd} changed, 1 distinct; 0x00000000 x {nd}\n"
            if "--depth-store" in o:
                out += f"depth store #{k}: {nd} dwords, {nd} changed, 32768+ distinct; 0x0 x 1\n"
        last = k == len(jobs)
        out += f"target: {w}x{h} hash 0x0\n"
        if keep == k and not ov:
            out += f"diff: 1234 of {w * h} pixels, first (0, 0) 0x{PL.RED:08x} expected 0x0 (render {k - 1}'s)\n"
            out += keep_report(o, jobs, world)
        else:
            bad = 0 if (last and not ov and not any(jobs[:-1]) and not ours) else 1234
            tri_n = PL.T_PIX if not ov else 162544
            bg, oth = (0, w * h - tri_n) if ours else (w * h - tri_n, 0)
            out += f"diff: {bad} of {w * h} pixels\n"
            out += (f"tri {w}x{h} #{k}: " + ("overflowed, " if ov else "") +
                    f"{tri_n} triangle, {bg} background, {oth} other; wrong 0 inside, 0 outside, 0 "
                    f"at edges; 0 if flipped; guard 0" + ("; background ours, not checked" if ours
                                                         else "") + "\n")
            if not ov and bad and not ours:
                rc = 1
        if ov and WR and "--dump-each" in o:
            files[f"{WR}/tri.{k}.param.bin"] = bytes(64)
            files[f"{WR}/tri.{k}.tadata.bin"] = bytes(64)
    if WR:
        files[f"{WR}/tri.param.bin"] = bytes(64)
        files[f"{WR}/tri.tadata.bin"] = bytes(64)
    return dict(rc=rc, out=out, files=files)


def owner_pages(b):
    for (p, i), v in PL.OWNER.items():
        struct.pack_into("<I", b, p * 4096 + 4 * i, v)


def og(o, world):
    """E1087's own1 form with the second context's geometry kick (t22b's lines, cmd_tri())."""
    if (o["--width"][0], o["--height"][0], o.get("-n", ["1"])[0]) != ("64", "64", "1"):
        return usage("og: the 64x64 -n 1 form only")
    kdir, wdir = o["--kept-copy"][0], o["--words"][0]
    for d in (kdir, wdir):
        if not os.path.isdir(d):
            return dict(rc=1, err=f"sgxfive-test: {d}: No such file or directory\n")
    flag = int(o["--kpoke-render"][0].rpartition("^=")[2], 0)
    keep = dbg("render_keep", "0") in ("1", "Y", "y")
    n = counter("r23d_og_rows")
    files, out = {}, ["tri: render context for targets up to 64x64", "tri: second render context",
                      f"tri: words 0 to {wdir}/words.0.txt (3079 bytes), {wdir}/ta3d.0.bin (236 bytes)",
                      f"tri: kpoke before render 1: ta:7^=0x{flag:x}", "job: ok",
                      f"tri: words 101 to {wdir}/words.101.txt (3079 bytes), {wdir}/ta3d.101.bin (236 bytes)",
                      "tri: closed the first context before the second context's render 1"]
    for k in (0, 101, 201, 1):
        files[f"{wdir}/words.{k}.txt"] = "rtds:11=0x20406000\n"
        files[f"{wdir}/ta3d.{k}.bin"] = bytes(236)
    p = f"{kdir}/kept.closed.1.bin"
    files[p] = bytes(OG_SIZE)
    out.append("tri: render_kept after closing the first context, before the second context's "
               f"render 1: {p} ({OG_SIZE} bytes)")
    out.append(f"tri: words 201 to {wdir}/words.201.txt (3079 bytes), {wdir}/ta3d.201.bin (236 bytes)")
    if not keep or ("fault" in world and n == 2):
        out += ["job: failed: job faulted, context lost (Input/output error)",
                "sgxfive-test: second context render: job faulted, context lost"]
        return dict(rc=1, out="\n".join(out) + "\n", files=files,
                    kmsg=["sgxfive: BIF fault 0x90400 at 0x3241100f (PD 0x0) stalls job 9, "
                          "recovering"], latch=(0x90400, 0x3241100F))
    after = bytearray(OG_SIZE)
    if flag & 0x8:
        owner_pages(after)
    out.append("job: ok")
    if "nogeo" not in world:
        geo = bytearray(OG_SIZE)
        if flag & 0x8 and "alt" not in world:
            owner_pages(geo)
        p = f"{kdir}/kept.geo.1.bin"
        if "geoempty" in world:
            files[p] = b""
            out += ["tri2 64x64 #1: geometry only, the scene left open",
                    "tri: render_kept still empty after 10 reads after the second context's "
                    "geometry kick, before its closing render 1 (10 ms apart): the copy is empty",
                    "tri: render_kept after the second context's geometry kick, before its closing "
                    f"render 1: {p} (0 bytes)"]
        else:
            files[p] = bytes(geo)
            out += ["tri2 64x64 #1: geometry only, the scene left open",
                    "tri: render_kept after the second context's geometry kick, before its closing "
                    f"render 1: {p} ({OG_SIZE} bytes)"]
        out += ["tri2 64x64 #1: closing render", "job: ok"]
    out.append("tri2 64x64 #1: 1062 triangle, 3034 background, 0 other; wrong 0 inside, 0 outside, "
               "0 at edges; 612 if flipped; guard 0")
    p = f"{kdir}/kept.1.bin"
    files[p] = bytes(after)
    out += [f"tri: render_kept after the second context's render 1: {p} ({OG_SIZE} bytes)",
            f"tri: words 1 to {wdir}/words.1.txt (3079 bytes), {wdir}/ta3d.1.bin (236 bytes)",
            "target: 64x64 hash 0x99385a04ee01c585", "diff: 0 of 4096 pixels",
            "tri 64x64 #1: 1062 triangle, 3034 background, 0 other; wrong 0 inside, 0 outside, "
            "0 at edges; 612 if flipped; guard 0", "tri 64x64 #1: 22920 us", "tri: 1 renders ok",
            "tri: closing the second context"]
    return dict(out="\n".join(out) + "\n", files=files)


def answer(tool, argv, world):
    if tool == "rt":
        if argv[:3] != ["0", PL.LEAD, PL.RT] or argv[3:4] != ["--"]:
            return usage(f"regtimeline: not TOTAL 0, LEAD 0.3 and the plan's registers: {argv[:4]}")
        return None
    if not argv or argv in (["fill"], ["tri"]):
        return None
    o, why = parse(tool, argv)
    if o is None:
        return usage(why)
    if "--ctx2" in o:
        return og(o, world)
    return tri(o, world)


def timeline(tool, regs, argv, rc, world):
    """regtimeline's samples of the wrapped job: the TA's page status up to each abort, one
    0x0658 stretch per partial render; 0x0480-0x0488 the render's ZLS word and bases."""
    o, why = parse("t22b", argv)
    if o is None:
        return None
    rows = []
    for i, j in enumerate(plan_job(o, world)):
        if j is None:
            continue
        ov, thr, _ = j
        top = min(thr, PL.U_TRI)
        c = ctl_of(o, i + 1) if "--depth" in o else 0
        z = (c, RD12, RD13) if "--depth" in o else (0, 0, 0)
        samples = [(p, 0, z[0]) for p in range(0, top + 1, 4)]
        if ov:
            samples += [(top, 1, z[0])] + [(top, 1, z[0] | 0x000C4000)] * 9
            samples += [(2, 0, z[0]), (PL.U_TRI - thr + 2, 0, z[0])]
        for st, pr, zw in samples:
            v = {0x624: thr, 0x724: (st << 16) | st, 0x658: pr, 0x480: zw, 0x484: z[1],
                 0x488: z[2]}
            rows.append([v.get(r, 0) for r in regs])
    return rows
