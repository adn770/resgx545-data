# SPDX-License-Identifier: MIT
"""mock/world.py: r8-ldpm's fake laptop for kit/session.py mock. answer() sees the tool's name, the
argv and the world's tokens, never a case name; timeline() gives regtimeline's samples (the kit's
fake regtimeline runs the wrapped tool's fake, then prints them). The threshold is what the GPU
sees: the debugfs knob render_pb_pages as the kit wrote it (the fake debugfs, $FAKE_DBGREAL), never
a row's name. The scene follows the frozen tables (gen/plan.py: E874's step model, H-SPAN, F9,
HU1, R7-dpm's kept --vtx-coords readings), so in the world `model` every control passes.

The fake is as strict as the tool (sgxfive-test of resgx545 4623753): `probe` takes only --tri
pixel, --width, --height, --vertices, --vtx-coords, --slot vtxuse=FILE, --dump-render DIR and one
program FILE; `tri` only --width, --height, -n, --geometry, --move, --tri-unit, --tri-v,
--keep-going, --keep-overflow, --wait-ms, --dump-render, --words, --regs; a file it reads must
exist, an option it does not take is rc 2. regtimeline (rt) must be `0 0.3 REGS -- CMD...` with
R5-dpm's 16 registers.

EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model     every stage runs, every control passes
  ctloff    a0-c4-b5's job leaves 1 global page, not 2: hook_check stops a0 (rc 24) and the gate
            keeps every later stage from running
  noread    a0-cal-2048's capture has no 0x0724 page count: no knob, no steps; the control has no
            reading, the premise stops the session (rc 25)
  fault     a 3072x3072 band 6 job of m6 faults: rc 4, the session stops
  rc3other  an sp job ends rc 3 without the overflow line: not the expected end, rc 4
  f9off     f9's 1536x1536 calibration needs one page more: hook_check stops f9 (rc 24), k and u
            still run
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import plan as PL  # noqa: E402

LATER = {"sp": 0, "m6": 0, "v": 0, "f9": 0, "k": 0, "u": 0}
EXPECT = {"model": (0, {"a0": 0, **LATER}),
          "ctloff": (0, {"a0": 24}),
          "noread": (25, {"a0": 25}),
          "fault": (4, {"a0": 0, "sp": 0, "m6": 4}),
          "rc3other": (4, {"a0": 0, "sp": 4}),
          "f9off": (0, {"a0": 0, "sp": 0, "m6": 0, "v": 0, "f9": 24, "k": 0, "u": 0})}
REGS = PL.RT
PROBE_OPTS = {"--width", "--height", "--vertices", "--vtx-coords", "--slot", "--dump-render"}
TRI_OPTS = {"--width", "--height", "-n", "--geometry", "--move", "--tri-unit", "--tri-v", "--wait-ms",
            "--dump-render", "--words", "--regs"}
TRI_FLAGS = {"--keep-going", "--keep-overflow"}
OVERFLOW = "probe p1139-green: failed: scene overflowed the parameter buffer, context kept (No space left on device)\n"
VCAL8 = ({2: 0x4F, 3: 0x98, 4: 0x9E, 5: 0xE5, 6: 0xE7, 7: 0x12D, 8: 0x133, 9: 0x17A, 10: 0x17E,
          11: 0x1C4, 12: 0x1C9, 13: 0x1CB, 14: 0x210, 15: 0x215, 16: 0x25D, 17: 0x260, 18: 0x2B0}, 691)


def usage(why):
    return dict(rc=2, err=f"sgxfive-test: {why}\nusage: sgxfive-test COMMAND ...\n")


def knob():
    p = os.path.join(os.environ.get("FAKE_DBGREAL", ""), "render_pb_pages")
    try:
        return int(open(p).read().strip(), 0)
    except (OSError, ValueError):
        return 0x422


def parse(argv, opts, flags=()):
    """{option: [values]} and the positionals; None and why on an option the tool does not take."""
    got, pos, i = {}, [], 0
    while i < len(argv):
        a = argv[i]
        if a in flags:
            got.setdefault(a, []).append(True)
            i += 1
        elif a in opts:
            if i + 1 >= len(argv):
                return None, f"{a} without its value"
            got.setdefault(a, []).append(argv[i + 1])
            i += 2
        elif a.startswith("-"):
            return None, f"unknown option {a}"
        else:
            pos.append(a)
            i += 1
    return (got, pos), None


def scene(argv):
    """(kind, w, h, S, A, U, peaks-after) of the job the argv runs at the knob's threshold."""
    if argv[:3] == ["probe", "--tri", "pixel"]:
        p, why = parse(argv[3:], PROBE_OPTS)
        if p is None:
            return None, why
        o, pos = p
        if len(pos) != 1 or not os.path.exists(pos[0]):
            return None, "probe: one program FILE that exists"
        for s in o.get("--slot", []):
            if not s.startswith("vtxuse=") or not os.path.exists(s[len("vtxuse="):]):
                return None, f"bad --slot {s}"
        if o.get("--vertices") != ["1500"]:
            return None, "the DPM rows run --vertices 1500"
        w, h = int(o["--width"][0]), int(o["--height"][0])
        n = o.get("--vtx-coords", [None])[0]
        if n == "4":
            S, U = PL.VCAL4
            A = {}
        elif n == "8":
            S, U = VCAL8
            A = {}
        else:
            S, A, B, U = PL.model(w, h)
        return dict(kind="probe", w=w, h=h, S=S, A=A, U=U, dump=o.get("--dump-render", [None])[0],
                    coords=n, written="--slot" in o), None
    if argv[:1] == ["tri"]:
        p, why = parse(argv[1:], TRI_OPTS, TRI_FLAGS)
        if p is None:
            return None, why
        o, pos = p
        if pos:
            return None, f"tri takes no FILE ({pos})"
        w, h = int(o["--width"][0]), int(o["--height"][0])
        a = " ".join(argv)
        row = dict(args=a, knobs=[])
        import importlib.util
        spec = importlib.util.spec_from_file_location("r8score", os.path.join(os.path.dirname(HERE), "score", "score.py"))
        sc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sc)
        U = sc.need_of(row)
        return dict(kind="tri", w=w, h=h, S={}, A={}, U=U, dump=o.get("--dump-render", [None])[0],
                    words=o.get("--words", [None])[0]), None
    return None, f"no such command {argv[:1]}"


DATA = "/Users/jtorra/src/resgx545-data/render"
KEPT_DUMPS = {("4", False): "closing-r7-dpm/out/a1/s-v/v-cal-c4", ("4", True): "closing-r7-dpm/out/a1/s-v/v-cal-c4",
              ("8", False): "closing-r6-dpm/out/a2/r-v/v-cal-c8", ("8", True): "closing-r7-dpm/out/a1/s-v/v-cal-c8"}


def kept_dump(sc, kind):
    """A --vtx-coords job's dump: the published R6-dpm or R7-dpm calibration dump of its kind (so
    stage v's scorer reads real object blocks: in this world the written N 8 runs repeat); any
    other job's, 64 zero bytes."""
    import gzip
    p = KEPT_DUMPS.get((sc.get("coords"), sc.get("written")))
    try:
        return gzip.open(f"{DATA}/{p}.p1139-green.{kind}.bin.gz").read() if p else bytes(64)
    except OSError:
        return bytes(64)


def answer(tool, argv, world):
    if tool == "rt":
        if argv[:3] != ["0", "0.3", REGS] or argv[3:4] != ["--"]:
            return usage(f"regtimeline: not TOTAL 0, LEAD 0.3 and R5-dpm's registers: {argv[:4]}")
        return None
    if not argv or argv in (["fill"], ["tri"]):
        return None
    sc, why = scene(argv)
    if sc is None:
        return usage(why)
    thr0 = knob() - PL.D_OFF
    files = {}
    if sc["kind"] == "probe":
        out = f"probe p1139-green: tri {sc['w']}x{sc['h']} (1500 vertices), pixel replaced\n"
        rc = 0
        if thr0 < sc["U"]:
            out += OVERFLOW
            rc = 3
            if "rc3other" in world and sc["w"] == 2048 and sc["h"] == 4096:
                out = out.replace("scene overflowed the parameter buffer", "render timed out")
        if sc["dump"]:
            for k in ("param", "tadata"):
                files[os.path.join(sc["dump"], f"p1139-green.{k}.bin")] = kept_dump(sc, k)
        a = dict(rc=rc, out=out, files=files)
    else:
        over = thr0 < sc["U"]
        out = f"tri: render context for targets up to {sc['w']}x{sc['h']}\n"
        out += "job: failed: scene overflowed the parameter buffer, context kept\n" if over else ""
        out += f"target: {sc['w']}x{sc['h']} hash 0x0\ndiff: 0 of {sc['w'] * sc['h']} pixels\n"
        if sc["words"]:
            files[os.path.join(sc["words"], "words.0.txt")] = "reg 0x0700 0x00000000\n"
        if sc["dump"]:
            files[os.path.join(sc["dump"], "tri.param.bin")] = bytes(64)
            files[os.path.join(sc["dump"], "tri.tadata.bin")] = bytes(64)
        a = dict(rc=0, out=out, files=files)
    if "fault" in world and sc["kind"] == "probe" and (sc["w"], sc["h"]) == (3072, 3072) and thr0 == 0x3D0:
        a["kmsg"] = ["SGX BIF fault: requestor 0x0 (mock)"]
        a["latch"] = (0x10, 0x10000011)
    return a


def runpeaks(sc, thr0):
    """The runs' peaks of the frozen tables where they have them, else one partial render."""
    w, h, U = sc["w"], sc["h"], sc["U"]
    if thr0 >= U:
        return [U]
    if sc["kind"] == "probe":
        f = PL.T["f9"].get(f"{w}x{h}:0x{thr0:x}")
        if f and f["F9"]:
            return [int(x, 16) for x in f["F9"][1]]
        return [thr0, max(2, min(U - thr0 + 1, thr0 + 0x20))]
    if (w, h) == (4096, 4096) and U == 287 and thr0 == 0x80:
        return list(PL.QF_PEAKS)
    for s in PL.T["k"]:
        if s["U"] == U and (s["w"], s["h"]) == (w, h) and f"0x{thr0:x}" in s["pred"]:
            return [int(x, 16) for x in s["pred"][f"0x{thr0:x}"]["H-KICKS"][1]]
    return [thr0, max(2, U - thr0 + 1)]


def timeline(tool, regs, argv, rc, world):
    """regtimeline's samples of the wrapped job (values per register of REGS, in order)."""
    sc, why = scene(argv)
    if sc is None:
        return None
    thr0 = knob() - PL.D_OFF
    S, A = sc["S"], sc["A"]
    peaks = runpeaks(sc, thr0)
    left = PL.span_left(thr0, S, A) if A else 1
    left = left if left in (1, 2) else 1
    if "ctloff" in world and (sc["w"], sc["h"], thr0) == (2048, 2048, 0xE2):
        left = 1
    if "f9off" in world and sc["kind"] == "probe" and (sc["w"], sc["h"]) == (1536, 1536) and thr0 >= sc["U"]:
        peaks = [sc["U"] + 1]
    samples = [(0, 0, 0)]                          # (pages, global pages, partial render)
    g = 1
    for i, pk in enumerate(peaks):
        start = 1 if i == 0 else 2
        for p in range(start, pk + 1):
            if i == 0:
                g = 1 + sum(1 for v in S.values() if v < p)
            samples.append((p, g, 0))
        if i < len(peaks) - 1:
            g = left if i == 0 else 1
            samples += [(pk, g, 1), (1, g, 1)]
    if "noread" in world and sc["kind"] == "probe" and thr0 == 0x140:
        samples = [(0, g, f) for p, g, f in samples]
    rows = []
    for p, g, f in samples:
        v = {0x624: thr0, 0x724: (p << 16) | p, 0x72C: (g << 16) | g, 0x658: f}
        rows.append([v.get(r, 0) for r in regs])
    return rows
