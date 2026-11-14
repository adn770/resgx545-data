# SPDX-License-Identifier: MIT
"""mock/world.py: r19-dpm's fake laptop for kit/session.py mock. answer() sees the tool's name, the
argv and the world's tokens, never a case name; timeline() gives regtimeline's samples. The pages
are what the GPU sees: the debugfs knob render_pb_pages as the kit wrote it ($FAKE_DBGREAL), and
the final render's N from --final-pb-pages, never a row's name.

The scene's page need (E625): 19 pages for the 1024x768 triangle (default or z = 0.5), 40 for the
full-screen ramp (two partial renders at 0x28 [infer]), 287 at 4096x4096. A render overflows when
its threshold (P - 0x22, or N - 0x22 for the final of a geometry job) is below the need.

As strict as the tools on this session's rows: `tri` only, the options sgxfive-test of ec50498
(t18b) and a581c06 (t10) take here with their arity; --final-pb-pages and --tadata-fill-render
are t18b's and need --geometry; --geometry refuses --bg-layer and --ctx2; --depth-ctl-next needs
-n 2; --bg-layer needs the knobs render_bg_layer=Y and a source. regtimeline (rt) must be
`0 0.3 REGS -- CMD...` with plan.RT.

EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model      every premise and control as predicted: every stage runs (0)
  finalovf   the final render overflows too (H-IGN or H-LATE of f0): every geometry stage (ld,
             dza, dzo, zs, rd) stops at its first row's premise (rc 24); the -n 1 stages run
  noregs     no --regs block: the ld controls have no thr reading: the premise stops the
             session (rc 25)
  ctloff     E628's no-load control stores indices: dzl stops (rc 24) and its gate skips dza
  zerosoft   the zeroed-page finals end `job: failed` (not a reading): soft, void, the second in a
             row stops ld (rc 24); the next stages run
  zerofault  the first zeroed-page final faults: no expectfault, rc 4, the session stops
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import plan as PL  # noqa: E402

ALL0 = {"ld": 0, "ldb": 0, "dzl": 0, "dza": 0, "dzc": 0, "dzo": 0, "zsc": 0, "zs": 0, "rd": 0}
EXPECT = {"model": (0, ALL0),
          "finalovf": (0, dict(ALL0, ld=24, dza=24, dzo=24, zs=24, rd=24)),
          "noregs": (25, {"ld": 25}),
          "ctloff": (0, dict(ALL0, dzl=24, dza=None)),
          "zerosoft": (0, dict(ALL0, ld=24)),
          "zerofault": (4, {"ld": 4})}
VAL = {"--width", "--height", "-n", "--geometry", "--wait-ms", "--dump-render", "--words", "--regs",
       "--poke", "--depth-ctl", "--depth-ctl-next", "--depth-fill", "--depth-dump",
       "--depth-store-fill", "--depth-pages", "--move", "--tri-z", "--final-pb-pages",
       "--tadata-fill-render"}
FLAGS = {"--keep-going", "--keep-overflow", "--dump-each", "--depth", "--depth-store", "--tri-full",
         "--bg-layer"}
T18_ONLY = {"--final-pb-pages", "--tadata-fill-render"}
OVF = "job: failed: scene overflowed the parameter buffer, context kept (No space left on device)\n"
CLEAR, TRI_Z = 0x3F800000, 0x3F000000


def usage(why):
    return dict(rc=2, err=f"sgxfive-test: {why}\nusage: sgxfive-test COMMAND ...\n")


def dbg(name, default):
    try:
        return open(os.path.join(os.environ.get("FAKE_DBGREAL", ""), name)).read().strip()
    except OSError:
        return default


def parse(tool, argv):
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
        if a in T18_ONLY and tool != "t18b":
            return None, f"{a}: not an option of {tool}"
    geo = "--geometry" in o
    n = int(o.get("-n", ["1"])[0])
    if (o.get("--final-pb-pages") or o.get("--tadata-fill-render")) and not geo:
        return None, "--final-pb-pages is for tri with --geometry"
    if "--bg-layer" in o and (geo or n != 1):
        return None, "--bg-layer: not with --geometry or -n other than 1"
    if "--depth-ctl-next" in o and n < 2:
        return None, "--depth-ctl-next needs -n 2"
    if "--bg-layer" in o and (dbg("render_bg_layer", "N") != "Y" or dbg("render_bg_src", "0x0") == "0x0"):
        return None, "--bg-layer: debugfs render_bg_layer is N"
    if any(k.startswith("--depth") for k in o) and "--depth" not in o:
        return None, "the --depth options need --depth"
    return o, None


def need(o):
    w = int(o["--width"][0])
    return 287 if w >= 4096 else 40 if "--tri-full" in o else 19


def plan_job(o, world):
    """[(overflowed, threshold)] per render the 3D runs (a geometry render that does not overflow
    runs none: None)."""
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
        out.append(None if geo >> i & 1 and not ov else (ov, thr))
    return out


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
    w, h = int(o["--width"][0]), int(o["--height"][0])
    jobs = plan_job(o, world)
    out, files, rc = "", {}, 0
    zero = "--tadata-fill-render" in o
    for i, j in enumerate(jobs):
        k = i + 1
        if j is None:
            out += f"job: ok\ntri {w}x{h} #{k}: geometry only, the scene left open\n"
            continue
        ov, thr = j
        if zero and k == 2 and "zerofault" in world:
            return dict(rc=1, out=out + "job: failed: job faulted, context lost (Input/output error)\n",
                        kmsg=["SGX BIF fault: requestor 0x0 (mock)"], latch=(0x10, 0x10000011))
        if zero and k == 2 and "zerosoft" in world:
            return dict(rc=1, out=out + "job: failed: Invalid argument\ntri: FAILED after 1 renders\n")
        out += OVF if ov else "job: ok\n"
        if "noregs" not in world:
            out += "regs: 0x0600-0x0750 at 0x80080000\n" + "".join(
                f"reg 0x{r:04x} 0x{thr if r == 0x624 else 0:08x}\n" for r in range(0x600, 0x754, 4))
        if "--depth" in o:
            n = w * h + 16384
            depth = (bytes(4) * 4) + bytes(4 * (n - 4))
            if "--depth-dump" in o:
                files[f"{o['--depth-dump'][0]}/depth.{k}.bin"] = depth
            if "--depth-store" in o:
                idx = "ctloff" in world or int(o["--depth-ctl"][0], 0) & 0x4002
                files[f"{o['--depth-dump'][0]}/depth-store.{k}.bin"] = depth
                out += (f"depth store #{k}: {n} dwords, {n} changed, "
                        + ("32768+ distinct; 0x00000000 x 1\n" if idx else
                           "3 distinct; 0x3f800000 x 1\n"))
        bad = 0 if not ov and k == len(jobs) and not any(jobs[:-1]) else 1234
        if "--bg-layer" in o:
            bad = 0 if not ov else 0
        out += f"diff: {bad} of {w * h} pixels\n"
        if ov:
            out += f"tri {w}x{h} #{k}: overflowed, 0 triangle, {w * h} background\n"
            if W and "--dump-each" in o:
                files[f"{W}/tri.{k}.param.bin"] = bytes(64)
                files[f"{W}/tri.{k}.tadata.bin"] = bytes(0x6000) + (1 << 16).to_bytes(4, "little") \
                    + bytes(0x43000)          # page 6 holds a list (ld's premise), 0x42000 none
        else:
            out += f"tri {w}x{h} #{k}: 1000 triangle, {w * h - 1000} background" + (
                f"; {w * h - 1000} layer texels in place, 0 elsewhere, 0 not a texel"
                if "--bg-layer" in o else "") + "\n"
            rc = rc or (1 if bad else 0)
        if "--words" in o:
            files[f"{o['--words'][0]}/ta3d.{k}.bin"] = bytes(236)
    if W:
        files[f"{W}/tri.param.bin"] = bytes(64)
        files[f"{W}/tri.tadata.bin"] = bytes(64)
    return dict(rc=rc, out=out, files=files)


def timeline(tool, regs, argv, rc, world):
    """regtimeline's samples of the wrapped job: the TA's page status up to each abort, one
    0x0658 stretch per partial render."""
    o, why = parse(tool, argv)
    if o is None:
        return None
    rows = []
    for j in plan_job(o, world):
        if j is None:
            continue
        ov, thr = j
        top = min(thr, need(o))
        samples = [(p, 0) for p in range(0, top + 1, 4)]
        if ov:
            samples += [(top, 1), (2, 0), (need(o) - thr + 2, 0)]
        for st, pr in samples:
            v = {0x624: thr, 0x724: (st << 16) | st, 0x658: pr}
            rows.append([v.get(r, 0) for r in regs])
    return rows
