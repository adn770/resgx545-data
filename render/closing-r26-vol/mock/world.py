# SPDX-License-Identifier: MIT
"""mock/world.py: r26-vol's fake laptop for kit/session.py mock. answer() sees the tool's name,
the argv and the world's tokens; it returns None (the health pair) or dict(rc, out, err, kmsg,
latch). The probe's NAME is its FILE's base name, as the tool prints it; what a program samples
is read from that name (c-*: E567's kept images, mock/e567.json, written by gen/make.py; vb-B-wW:
a bit's image), never from a case table.

As strict as t24 (1341034) on this session's rows: `probe` with --temps N, --coords, --pixels and
one FILE; anything else is refused as the tool's usage error (rc 2). Output as t24's: the scratch
line, the job time, the o0 summary (the four most frequent values, then `other xN`) and, with
--pixels, `probe NAME: row Y:` and 64 pixels a row.

A bit's image (vb-B-*) is c-w0's with every pixel XORed by a word of the bit: the same at w 0 and
w 1.5 unless the world makes w act on it.

EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  novol    no bit makes w act, every control as E567 (H-NOVOL 19 of 19): all run (0)
  vol      T3 bit 9 makes w act (its w 1.5 image differs): all run (0), H-NOVOL not supported
  drift    t0b27's repeat differs from its w 0 job: all run (0), that bit cannot tell
  cubeoff  TEXTYPE 2 ignores w too (c-cube-w15 reads c-cube-w5's image): vc's control FAILs in the
           scorer (the job reads ok), the gate skips vb (None)
  nopix    a tool that prints no pixel rows: hook_check stops vc at its first row (24) and the
           session ends (on_stop = "end")
  fault    vb-t3b12-w15 faults the job (a BIF fault, the context lost): vb stops on the
           unexpected fault (4)
"""
import json
import os
import re

ALL0 = {"vc": 0, "vb": 0}
EXPECT = {"novol": (0, ALL0),
          "vol": (0, ALL0),
          "drift": (0, ALL0),
          "cubeoff": (0, {"vc": 0, "vb": None}),
          "nopix": (24, {"vc": 24}),
          "fault": (4, {"vc": 0, "vb": 4})}
HERE = os.path.dirname(os.path.abspath(__file__))
CONTROL = {"c-w0": "ty0-3d-w0", "c-w15": "ty0-3d-w15", "c-cube-w5": "rt2-3d-w5",
           "c-cube-w15": "rt2-3d-w15", "c-w0b": "ty0-3d-w0"}
_IMAGES = {}


def images():
    if not _IMAGES:
        with open(os.path.join(HERE, "e567.json")) as f:
            _IMAGES.update(json.load(f))
    return _IMAGES


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


def bit_word(b):
    """a word of the bit name (t0b27 -> 0x00001b00 | word): the image's XOR in this mock."""
    m = re.match(r"t([03])b(\d+)$", b)
    return int(m[2]) << 8 | (int(m[1]) + 1) << 16


def picture(name, world):
    """the 2048 pixels (ints) of a program, in this world."""
    if name in CONTROL:
        lab = CONTROL[name]
        if "cubeoff" in world and name == "c-cube-w15":
            lab = "rt2-3d-w5"
        return [int(v, 16) for v in images()[lab]]
    m = re.match(r"vb-(t[03]b\d+)-(w0|w15|w0r)$", name)
    if not m:
        return None
    x = bit_word(m[1])
    if "vol" in world and m[1] == "t3b9" and m[2] == "w15":
        x ^= 0x00400000
    if "drift" in world and m[1] == "t0b27" and m[2] == "w0r":
        x ^= 0x00000001
    return [int(v, 16) ^ x for v in images()["ty0-3d-w0"]]


def o0_line(name, p):
    cnt = {}
    for v in p:
        cnt[v] = cnt.get(v, 0) + 1
    if len(cnt) == 1:
        return f"probe {name}: o0 0x{p[0]:08x} (2048 of 2048)"
    order = sorted(cnt, key=lambda v: (-cnt[v], p.index(v)))
    s = "".join(f" 0x{v:08x} x{cnt[v]}" for v in order[:4])
    other = sum(cnt[v] for v in order[4:])
    return f"probe {name}: o0 mixed{s}" + (f" other x{other}" if other else "")


def probe(argv, world):
    pr, why = parse(argv, {"--temps"}, {"--coords", "--pixels"})
    if why:
        return usage(why)
    o, files = pr
    if len(files) != 1 or not files[0].endswith(".bin"):
        return usage("probe takes one FILE here")
    if not o.get("--temps", ["x"])[0].isdigit():
        return usage("--temps N")
    name = os.path.basename(files[0])[:-len(".bin")]
    p = picture(name, world)
    if p is None:
        return usage(f"{name} is not this session's program")
    out = [f"probe {name}: scratch at 0x3e003000 (64 KiB)"]
    if "fault" in world and name == "vb-t3b12-w15":
        out.append(f"probe {name}: failed: job faulted, context lost (Input/output error)")
        return dict(rc=1, out="\n".join(out) + "\n", err="",
                    kmsg=["sgxfive: BIF fault 0x90020 at 0x3e013000 (PD 0xf4f2000) stalls "
                          "job 7, recovering"], latch=(0x90020, 0x3e013000))
    out.append(f"probe {name}: job time: 390 us")
    out.append(o0_line(name, p))
    if "--pixels" in o and "nopix" not in world:
        out += [f"probe {name}: row {y}: " + " ".join(f"{v:08x}" for v in p[y * 64:(y + 1) * 64])
                for y in range(32)]
    return dict(rc=0, out="\n".join(out) + "\n")


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe" and tool == "t24":
        return probe(argv, world)
    return usage(f"{argv[0]} is not this session's")
