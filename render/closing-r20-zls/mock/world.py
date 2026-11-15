# SPDX-License-Identifier: MIT
"""mock/world.py: r20-zls's fake laptop for kit/session.py mock. answer() sees the tool's name, the
argv and the world's tokens, never a case name; timeline() gives regtimeline's samples. The pages
are what the GPU sees: the debugfs knob render_pb_pages as the kit wrote it ($FAKE_DBGREAL), and
the final render's N from --final-pb-pages, never a row's name.

The scene's page need (E625, read on r19-dpm's kept peaks): 19 pages for the 1024x768 triangle
(default or z = 0.5), 49 for the full-screen ramp. A render overflows when its threshold (P -
0x22, or N - 0x22 for the final of a geometry job) is below the need; its first abort is raised
iff 2 thr < U + 2 (TA3DCtl dword 38 = 0x20 in ta3d.1.bin, else 0).

As strict as t18b (ec50498) on this session's rows: `tri` only, the options it takes here with
their arity; --final-pb-pages needs --geometry; --depth-ctl-next needs -n 2; --refill K:BUF=V
needs 2 <= K <= -n and --depth for BUF depth; --move N:DX,DY needs 1 <= N <= -n; the --depth
options need --depth. regtimeline (rt) must be `0 0.3 REGS -- CMD...` with plan.RT. The dumps are
short (the scorer reads only the window dwords a dump holds).

EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model     every premise and control as predicted: every stage runs (0); zm's finals leave
            sentinel pixels (rc 1 with `job: ok` and a diff line: expectdiff's reading)
  finalovf  the final render overflows too: zc-geo's premise stops zc (24) and the session ends
            (on_stop = "end")
  noregs    no --regs block: zc-geo has no thr reading: the premise stops the session (25)
  ctloff    E628's no-load control stores indices: zc stops (24), the session ends
  storeoff  zc-geo's store after the final differs from render 1's inside the window while the
            tool's reports are equal: zc runs (0), its scorer control fails and the gates skip
            zr, zm and zq
  norefill  the tool prints no refill line: zr's first row stops zr (24); zm and zq run
  zregsoff  0x0480-0x0488 never read the poked word: no stop anywhere (zregs voids only the
            register readings)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import plan as PL  # noqa: E402

ALL0 = {"zc": 0, "zr": 0, "zm": 0, "zq": 0}
EXPECT = {"model": (0, ALL0),
          "finalovf": (24, {"zc": 24}),
          "noregs": (25, {"zc": 25}),
          "ctloff": (24, {"zc": 24}),
          "storeoff": (0, {"zc": 0, "zr": None, "zm": None, "zq": None}),
          "norefill": (0, dict(ALL0, zr=24)),
          "zregsoff": (0, ALL0)}
VAL = {"--width", "--height", "-n", "--geometry", "--wait-ms", "--dump-render", "--words", "--regs",
       "--poke", "--depth-ctl", "--depth-ctl-next", "--depth-fill", "--depth-dump",
       "--depth-store-fill", "--depth-pages", "--move", "--tri-z", "--final-pb-pages", "--refill"}
FLAGS = {"--keep-going", "--keep-overflow", "--dump-each", "--depth", "--depth-store", "--tri-full"}
OVF = "job: failed: scene overflowed the parameter buffer, context kept (No space left on device)\n"
NDW = 8192                                    # the mock's dump length (dwords)
LOAD, STORE = 0x3E001000, 0x3E341000


def usage(why):
    return dict(rc=2, err=f"sgxfive-test: {why}\nusage: sgxfive-test COMMAND ...\n")


def dbg(name, default):
    try:
        return open(os.path.join(os.environ.get("FAKE_DBGREAL", ""), name)).read().strip()
    except OSError:
        return default


def parse(tool, argv):
    if tool != "t18b":
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
    return o, None


def need(o):
    return PL.U_RAMP if "--tri-full" in o else PL.U_TRI


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
        ov = thr < need(o)
        out.append(None if geo >> i & 1 and not ov else
                   (ov, thr, ov and 2 * thr < need(o) + 2))
    return out


def ctl_of(o, k):
    c = o.get("--depth-ctl", ["0x0"])[0]
    if k > 1 and "--depth-ctl-next" in o:
        c = o["--depth-ctl-next"][0]
    return int(c, 0)


def words_txt(o, k):
    return "".join(f"rd:{i}=0x{v:08x}\n" for i, v in
                   ((1, 0x3E000000), (11, ctl_of(o, max(k, 1))), (12, 0x1000), (13, 0x341000),
                    (53, 0x480)))


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
    W = o["--dump-render"][0] if "--dump-render" in o else None
    WD = o["--words"][0] if "--words" in o else None
    w, h = int(o["--width"][0]), int(o["--height"][0])
    jobs = plan_job(o, world)
    out, files, rc = "", {}, 0
    if "--depth" in o:
        out += f"depth: 0x{LOAD:08x} 832 pages, fill x, base 0x3e000000, control 0x{ctl_of(o, 1):08x}\n"
        if "--depth-store" in o:
            out += f"depth store: 0x{STORE:08x} 832 pages, fill x\n"
    if WD:
        files[f"{WD}/words.0.txt"] = words_txt(o, 0).encode()
    for i, j in enumerate(jobs):
        k = i + 1
        if k >= 2 and "--refill" in o and "norefill" not in world:
            for r in o["--refill"]:
                if int(r.split(":")[0]) == k:
                    out += f"refill: render {k} buf depth value {r.split('=')[1]}\n"
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
            depth = bytes(4 * NDW)
            store = (0x3F000000).to_bytes(4, "little") * NDW
            if "storeoff" in world and k == 2:
                store = (0x3F800000).to_bytes(4, "little") * NDW
            dd = o.get("--depth-dump", [None])[0]
            if dd:
                files[f"{dd}/depth.{k}.bin"] = depth
            out += f"depth #{k}: {NDW} dwords, {NDW} changed, 1 distinct; 0x00000000 x {NDW}\n"
            if "--depth-store" in o:
                if dd:
                    files[f"{dd}/depth-store.{k}.bin"] = store
                idx = "ctloff" in world or ld or "--geometry" in o
                out += (f"depth store #{k}: {NDW} dwords, {NDW} changed, "
                        + ("32768+ distinct; 0x00000000 x 1\n" if idx else
                           "3 distinct; 0x3f000000 x 1\n"))
        last = k == len(jobs)
        holes = 5 if last and "--move" in o and "--depth" not in o else 0
        bad = 0 if (last and not ov and not holes and not any(jobs[:-1])) else 1234 + holes
        out += f"target: {w}x{h} hash 0x0\ndiff: {bad} of {w * h} pixels\n"
        out += (f"tri {w}x{h} #{k}: " + ("overflowed, " if ov else "") +
                f"1000 triangle, {w * h - 1000 - holes} background, {holes} other; wrong 0 inside, "
                f"{holes} outside, 0 at edges; 0 if flipped; guard 0\n")
        if ov:
            if W and "--dump-each" in o:
                files[f"{W}/tri.{k}.param.bin"] = bytes(64)
                files[f"{W}/tri.{k}.tadata.bin"] = bytes(64)
        else:
            rc = rc or (1 if bad else 0)
    if W:
        files[f"{W}/tri.param.bin"] = bytes(64)
        files[f"{W}/tri.tadata.bin"] = bytes(64)
    return dict(rc=rc, out=out, files=files)


def timeline(tool, regs, argv, rc, world):
    """regtimeline's samples of the wrapped job: the TA's page status up to each abort, one
    0x0658 stretch per partial render; 0x0480-0x0488 the render's ZLS word and bases."""
    o, why = parse("t18b", argv)       # TOOL: the wrapper's view; every row wraps t18b
    if o is None:
        return None
    rows = []
    for i, j in enumerate(plan_job(o, world)):
        if j is None:
            continue
        ov, thr, _ = j
        top = min(thr, need(o))
        z = (0, 0, 0) if "zregsoff" in world or "--depth" not in o else (
            ctl_of(o, i + 1), LOAD, STORE if "--depth-store" in o else LOAD)
        samples = [(p, 0) for p in range(0, top + 1, 4)]
        if ov:
            samples += [(top, 1), (2, 0), (need(o) - thr + 2, 0)]
        for st, pr in samples:
            v = {0x624: thr, 0x724: (st << 16) | st, 0x658: pr, 0x480: z[0], 0x484: z[1],
                 0x488: z[2]}
            rows.append([v.get(r, 0) for r in regs])
    return rows
