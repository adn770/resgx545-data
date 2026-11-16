# SPDX-License-Identifier: MIT
"""mock/world.py: r34-q044's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name: a row is named by its program
(colour.bin or ramp.bin), its sideband's pack mode and its word 11 (--cmd 11=V). As strict as
sgxfive-test (resgx545 a581c06) on these forms: an option `probe` does not take, a missing value,
a second program, a --cmd other than word 11, a --sideband without an eot slot, a ramp row without
its pixpds (12 data dwords) and vtxuse slots and --vtx-coords 2, or a file that is not there is
refused (rc 2, usage).

The image of an argv that a frozen image names (the controls, the p1 references: E031, E268,
E385) is that image; any other reference is synthesised (E385's mode 0 ramp image, or E031's mode
0, with the mode in bits 15:8). A bit-25 row is its reference XOR the mode's H-INV25 mask (alt:
H-SUBSET's) over the dwords the reference wrote; a mode-4 ramp row at a low byte L sets the alpha
bit where the ramp alpha is >= L (alt: > L); every other word is its reference (alt: mode 5 rows
differ by 0x1000 a written dword, H-THRN).

Worlds (EXPECT: the driver's status and each stage's runner status; a stage whose gate closed is
skipped, so absent):
  model     every frozen model (H-E031, H-INV25, H-GE, H-THR1, H-NULL, H-REPEAT): 0 everywhere
  alt       the rivals (H-SUBSET, H-GT, H-THRN): 0 everywhere, the rows FAILED
  s0diff    E385's mode 4 image at 0x80 reads one alpha bit flipped: s0's control FAILED, so p1, p2
            and pw are skipped (their gate on s0 closes): 0
  s0nopix   s0's first control prints no pixel rows: the premise stops s0 (25), which ends the
            session (on_stop = "end")
  p1nopix   p1's held-out rows of mode 6 and 7 print no pixel rows: the second stops p1 by its
            rule (24); p2 and pw run: 0
  pwfault   mode 12's bit-25 row faults (a BIF fault latched): pw stops (4), the session (4)
  p2hang    the first mode-4 low-byte row of p2 never returns (timeout rc 124): p2 stops (6)
"""
import os

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGES = ("s0", "p1", "p2", "pw")
EXPECT = {"model": (0, {s: 0 for s in STAGES}),
          "alt": (0, {s: 0 for s in STAGES}),
          "s0diff": (0, {"s0": 0}),
          "s0nopix": (25, {"s0": 25}),
          "p1nopix": (0, {"s0": 0, "p1": 24, "p2": 0, "pw": 0}),
          "pwfault": (4, {"s0": 0, "p1": 0, "p2": 0, "pw": 4}),
          "p2hang": (6, {"s0": 0, "p1": 0, "p2": 6})}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
VALS = {"--temps", "--tri", "--width", "--height", "--vtx-coords", "--cmd", "--sideband", "--slot"}
FLAGS = {"--pixels"}
SENT = 0xDEADBEEF
BG = 0xFF203040


def gen():
    import sys
    sys.path.insert(0, os.path.join(KP, "gen"))
    sys.dont_write_bytecode = True
    import q044
    return q044


def parse(argv):
    o, pos, i = {}, [], 1
    while i < len(argv):
        a = argv[i]
        if a in FLAGS:
            o.setdefault(a, []).append(True)
            i += 1
        elif a in VALS and i + 1 < len(argv):
            o.setdefault(a, []).append(argv[i + 1])
            i += 2
        elif a.startswith("--"):
            return None
        else:
            pos.append(a)
            i += 1
    return o, pos


_FROZEN = {}


def frozen():
    """{(form, mode, word): image} of every frozen image of the tables (read once)."""
    if _FROZEN:
        return _FROZEN
    out = _FROZEN
    for st in STAGES:
        for ln in open(os.path.join(KP, "tables", st + ".txt")):
            if not ln.strip() or ln.startswith("#"):
                continue
            name, _, _, _, _, args = ln.rstrip("\n").split("|", 5)
            d = os.path.join(KP, "predictions", st)
            for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                if f.startswith(name + ".") and f.count(".") == 2:
                    a = args.split()
                    form = "ramp" if "--vtx-coords" in a else "colour"
                    mode = int(a[a.index("--sideband") + 1], 16) & 0x3F
                    word = int(a[a.index("--cmd") + 1].split("=")[1], 16)
                    out[(form, mode, word)] = [int(t, 16) for t in open(os.path.join(d, f)).read().split()]
    return out


def alpha():
    if "alpha" not in _FROZEN_ALPHA:
        _FROZEN_ALPHA["alpha"] = _alpha()
    return _FROZEN_ALPHA["alpha"]


_FROZEN_ALPHA = {}


def _alpha():
    return [None if t == "-" else int(t, 16)
            for t in open(os.path.join(KP, "predictions", "p2", "alpha.txt")).read().split()]


def masked(img, mask):
    return [v if v == SENT else v ^ mask for v in img]


def reference(fz, form, mode):
    if (form, mode, 0x80) in fz:
        return fz[(form, mode, 0x80)]
    base = fz[(form, 0, 0x80)]
    return [v if v == SENT else (v ^ (mode << 8)) for v in base]


def image(form, mode, word, world):
    Q = gen()
    fz = frozen()
    if (form, mode, word) in fz:
        img = list(fz[(form, mode, word)])
        if "s0diff" in world and (form, mode, word) == ("ramp", 4, 0x80):
            img[20 * 64 + 30] ^= 0x80000000
        return img
    ref = reference(fz, form, mode)
    if word == Q.B25:
        if mode in Q.Q012:
            return masked(ref, 0xFF000000)
        return masked(ref, (Q.SUBSET if "alt" in world else Q.INV25)[mode])
    if form == "ramp" and mode == 4 and word in Q.EQ:
        al, out = alpha(), []
        for i, v in enumerate(ref):
            hs = []
            for k, h in enumerate((v & 0xFFFF, v >> 16)):
                a = al[2 * i + k] if 2 * i + k < len(al) else None
                if a is not None:
                    on = a > word if "alt" in world else a >= word
                    h = (h & 0x7FFF) | (0x8000 if on else 0)
                hs.append(h)
            out.append(hs[0] | hs[1] << 16)
        return out
    if "alt" in world and mode == 5:
        return masked(ref, 0x1000)
    return list(ref)


def answer(tool, argv, world):
    if tool != "t10" or not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] != "probe":
        return USAGE
    r = parse(argv)
    if r is None or len(r[1]) != 1:
        return USAGE
    o, (path,) = r
    one = {k: v[0] for k, v in o.items() if len(v) == 1}
    if (one.get("--temps") != "32" or one.get("--tri") != "pixel" or "--pixels" not in o or
            one.get("--width") != "64" or one.get("--height") != "64" or
            len(o.get("--cmd", [])) != 1 or len(o.get("--sideband", [])) != 1):
        return USAGE
    k, _, v = one["--cmd"].partition("=")
    if k != "11" or not v:
        return USAGE
    word = int(v, 16)
    sb = int(one["--sideband"], 16)
    slots = dict(s.split("=", 1) for s in o.get("--slot", []) if "=" in s)
    form = {"colour.bin": "colour", "ramp.bin": "ramp"}.get(os.path.basename(path))
    if form is None or "eot" not in slots:
        return USAGE
    want = {"eot"} if form == "colour" else {"eot", "pixpds", "vtxuse"}
    if set(slots) != want or (form == "ramp" and (one.get("--vtx-coords") != "2" or
                                                  not slots["pixpds"].endswith(":12"))):
        return USAGE
    if form == "colour" and "--vtx-coords" in o:
        return USAGE
    for f in [path, slots["eot"]] + ([slots["pixpds"][:-3], slots["vtxuse"]]
                                     if form == "ramp" else []):
        if not os.path.isfile(f):
            return dict(rc=2, err="sgxfive-test: %s: No such file or directory\n" % f)
    mode = sb & 0x3F
    case = form
    Q = gen()
    if "pwfault" in world and mode == 12 and word == Q.B25:
        return dict(rc=3, out="probe %s: failed: job faulted\n" % case,
                    kmsg=["sgxfive: BIF fault 0x90004 at 0x1000c016 stalls job 9"],
                    latch=(4, 0x1000c016))
    if "p2hang" in world and form == "ramp" and mode == 4 and word == Q.EQ[0]:
        return dict(rc=124, out="")
    out = ["programs asm", "probe %s: scratch at 0x3e006000 (64 KiB)" % case,
           "probe %s: tri 64x64 (command words 11) (sideband 0x%08x), eot pixel replaced"
           % (case, sb)]
    if ("s0nopix" in world and (form, mode, word) == ("colour", 0, 0x80)) or (
            "p1nopix" in world and form == "colour" and mode in (6, 7) and word == Q.B25):
        return dict(out="\n".join(out) + "\n")
    img = image(form, mode, word, world)
    out += ["probe %s: row %d: " % (case, y) + " ".join("%08x" % x for x in img[64 * y:64 * y + 64])
            for y in range(64)]
    return dict(out="\n".join(out) + "\n")
