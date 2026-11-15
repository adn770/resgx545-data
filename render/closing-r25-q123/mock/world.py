# SPDX-License-Identifier: MIT
"""mock/world.py: r25-q123's fake laptop for kit/session.py mock. answer() sees the tool's name,
the argv and the world's tokens; it returns None (the health pair) or dict(rc, out, err). The
placed program is read from its FILE's base name (gen/make.py's e492-read, e492-jump, c-lapc and
w-KIND-TTTT), never from a case table.

As strict as t22 (3c68e8d) on this session's rows: `probe` with --temps N, --place OFF=FILE (OFF
a multiple of 8, at least the heap's first page 0x1000, the program within 8192 words and the
5 MiB heap) and --place-form cbase|exe18, one FILE. Anything else is refused as the tool's usage
error (rc 2).

EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model     every link H-STEP80000, every landing H-INDEX, controls on their frozen o0: all run (0)
  step40000 the held-out placements read 0x40000's links: q123s runs (0), the scorer fails
  wrap256   the q123w landings take the index's low 8 bits (the heap base's word): runs (0)
  ctlstep   the q123s control reads another link: hook_check stops q123s (24), the session ends
  ctlword   E1098's c-lapc lands at the heap base: q123s runs (0), q123w stops (24), the end
  placebad  the placed words do not read back as built: q123s stops at its first row (24)
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import q123 as Q  # noqa: E402

ALL0 = {"q123s": 0, "q123w": 0}
EXPECT = {"model": (0, ALL0),
          "step40000": (0, ALL0),
          "wrap256": (0, ALL0),
          "ctlstep": (24, {"q123s": 24}),
          "ctlword": (24, {"q123s": 0, "q123w": 24}),
          "placebad": (24, {"q123s": 24})}
PROG = re.compile(r"^(?:e492-(read|jump)|c-lapc|w-(lapc|ba)-(\d{4}))$")
SIZE = {"e492-read": Q.SPAN, "e492-jump": Q.SPAN, "c-lapc": 600}


def usage(why):
    return dict(rc=2, err=f"sgxfive-test: {why}\nusage: sgxfive-test COMMAND ...\n")


def parse(argv, vals, flags):
    opts, files, i = {}, [], 1
    while i < len(argv):
        a = argv[i]
        if a in vals:
            if i + 1 >= len(argv):
                return None, f"{a} needs a value"
            opts.setdefault(a, []).append(argv[i + 1])
            i += 2
        elif a in flags:
            opts.setdefault(a, []).append(True)
            i += 1
        elif a.startswith("-"):
            return None, f"unknown option {a}"
        else:
            files.append(a)
            i += 1
    return (opts, files), None


def landing(prog, off, world):
    """o0 of the placed program prog at off in this world"""
    m = PROG.match(prog)
    if m[1]:                                       # E492's read or jump: the link
        if off == Q.CONTROL_OFF:
            return 0x2 if "ctlstep" in world else Q.link(off, Q.STEP)
        return Q.link(off, 0x40000 if "step40000" in world else Q.STEP)
    if prog == "c-lapc":
        return Q.WPAD | (590 & 0xFF) if "ctlword" in world else Q.PAD | 590
    t = int(m[3])
    return Q.word_models(t)["H-WRAP256" if "wrap256" in world else "H-INDEX"]


def probe(argv, world):
    p, why = parse(argv, {"--temps", "--place", "--place-form"}, set())
    if why:
        return usage(why)
    o, files = p
    if len(files) != 1 or len(o.get("--place", [])) > 1 or len(o.get("--temps", [])) != 1:
        return usage("probe takes one FILE, one --temps, at most one --place here")
    if ("--place" in o) != ("--place-form" in o) or "--place" not in o:
        return usage("this session's rows place a program with its form")
    off_s, pf = o["--place"][0].split("=", 1)
    off, form = int(off_s, 0), o["--place-form"][0]
    prog = os.path.basename(pf)[:-len(".bin")]
    if not PROG.match(prog) or form not in ("cbase", "exe18"):
        return usage(f"--place {o['--place'][0]} --place-form {form}")
    n = SIZE.get(prog, Q.WN)
    if off % 8 or off < 0x1000 or off + n * 8 > 0x500000 or n > 8192:
        return usage(f"--place {o['--place'][0]}")
    name = os.path.basename(files[0])[:-len(".bin")]
    v = landing(prog, off, world)
    k = n - 1 if "placebad" in world else n
    out = [f"probe {name}: program placed at 0x{0x37000000 + off:08x} (code heap base + "
           f"0x{off:x}), started as EXE and CBASE: DOUTU bits 21:0 0x000000",
           f"probe {name}: scratch at 0x3e003000 (64 KiB)",
           f"probe {name}: job time: 450 us",
           f"probe {name}: o0 0x{v:08x} (2048 of 2048)",
           f"probe {name}: placed words read back: {k} of {n} as built, hash 0x1"]
    return dict(rc=0, out="\n".join(out) + "\n")


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe":
        return probe(argv, world)
    return usage(f"{argv[0]} is not this session's")
