# SPDX-License-Identifier: MIT
"""mock/world.py: r23-pk's fake laptop for kit/session.py mock. answer() sees the tool's name, the
argv and the world's tokens; it returns None (the health pair) or dict(rc, out, err, files). The
probe's NAME is its FILE's base name, as the tool prints it; what a probe program does is read
from that name (the q019 and pk programs are E391's and E125's, gen/q123.py's rows the placed
ones), never from a case table.

As strict as t22 (3c68e8d) on this session's rows: `probe` with --temps N, --coords, --pixels,
--pds N with --use FILE, --poke xfer:N[^]=V | bg:N[^]=V, --place OFF=FILE with --place-form
cbase|exe18 (OFF a multiple of 8, past the heap's first page, the program within 8192 words and
the 5 MiB heap), one FILE; `copy` with --every-value, --pixels, --poke tex:/xfer:. Anything
else is refused as the tool's usage error (rc 2). t22 echoes each applied poke after the job.

EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model     every echo as t22 prints it, E391's and E125's markers, E568's black, E037's copy
            hashes, every placed landing H-CARRY18 and the exe18 start honoured: all run (0)
  noecho    a tool without the echo (t10 to t20): pk-e391 echoes 0 of 1: hook_check stops pk (24)
            and the session ends (on_stop = "end")
  echooff   the echo shows bg:1 as built, not as poked: pk's controls FAIL in the scorer, the gates
            skip q019 and q181; q123 and q123h run (0)
  wrap      the bit-16 crossings land at the heap base (H-WRAP): q123 runs (0), q123h's gate shuts
  ctloff    the in-step run lands at the heap base: c-run's o0 is not its frozen word: hook_check
            stops q123 (24), the session ends
  placebad  the placed words do not read back as built: q123 stops at its first row (24), the end
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import q123 as Q  # noqa: E402

ALL0 = {"pk": 0, "q019": 0, "q181": 0, "q123": 0, "q123h": 0}
EXPECT = {"model": (0, ALL0),
          "noecho": (24, {"pk": 24}),
          "echooff": (0, {"pk": 0, "q019": None, "q181": None, "q123": 0, "q123h": 0}),
          "wrap": (0, {"pk": 0, "q019": 0, "q181": 0, "q123": 0, "q123h": None}),
          "ctloff": (24, {"pk": 0, "q019": 0, "q181": 0, "q123": 24}),
          "placebad": (24, {"pk": 0, "q019": 0, "q181": 0, "q123": 24})}
E037 = {"csc": "0xb6067a95fa98de2d", "none": "0xd3522437a14b6325"}
BUILT = {("bg", 1): 0x00130000, ("xfer", 17): 0x00000000}   # the words as the library builds them
ROWS = {q[0]: q for q in Q.Q123}
SPEC = re.compile(r"^(xfer|bg|tex):(\d+)(\^?)=(0x[0-9a-fA-F]+|\d+)$")


def usage(why):
    return dict(rc=2, err=f"sgxfive-test: {why}\nusage: sgxfive-test COMMAND ...\n")


def parse(argv, vals, flags):
    """{option: [values]}, the operands; a usage error for anything else."""
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


def pokes(specs, world, spaces):
    lines = []
    for s in specs:
        m = SPEC.match(s)
        if not m or m[1] not in spaces:
            return None, f"--poke {s}"
        old = BUILT.get((m[1], int(m[2])), 0x11110000 | int(m[2]))
        v = int(m[4], 0)
        new = old ^ v if m[3] else v
        if "echooff" in world and m[1] == "bg":
            new = old
        lines.append((m[1], int(m[2]), old, new))
    return lines, None


def probe(argv, world):
    p, why = parse(argv, {"--temps", "--pds", "--use", "--poke", "--place", "--place-form"},
                   {"--coords", "--pixels"})
    if why:
        return usage(why)
    o, files = p
    if len(files) != 1:
        return usage("probe takes one FILE here")
    if ("--pds" in o) != ("--use" in o) or ("--place" in o) != ("--place-form" in o):
        return usage("--pds needs --use, --place needs --place-form")
    pk, why = pokes(o.get("--poke", []), world, ("xfer", "bg"))
    if why:
        return usage(why)
    name = os.path.basename(files[0])[:-len(".bin")]
    out = [f"probe {name}: scratch at 0x3e003000 (64 KiB)"]
    if pk:
        out.append(f"probe {name}: pokes " + " ".join(o["--poke"]))
    if "--place" in o:
        off, pf = o["--place"][0].split("=", 1)
        off, form = int(off, 0), o["--place-form"][0]
        row = ROWS.get(os.path.basename(pf)[:-len(".bin")])
        if row is None or off % 8 or off < 0x1000 or form not in ("cbase", "exe18") or \
                (row[3], row[4]) != (form, off) or off + row[6] * 8 > 0x500000:
            return usage(f"--place {o['--place'][0]} --place-form {form}")
        _, stg, st, form, off, kind, n, t = row
        models = Q.q123_models(off, form, kind, n, t, 17 if stg == "q123h" else 16)
        if "ctloff" in world and row[0] == "c-run":
            v = Q.WPAD
        elif "wrap" in world and row[0].startswith("b16-"):
            v = models["H-WRAP"]
        else:
            v = models.get("H-CARRY18", models.get("H-EXE18"))
        out.append(f"probe {name}: program placed at 0x{0x37000000 + off:08x} (code heap base + "
                   f"0x{off:x}), started as {form}")
        out.append(f"probe {name}: o0 0x{v:08x} (2048 of 2048)")
        k = n - 1 if "placebad" in world else n
        out.append(f"probe {name}: placed words read back: {k} of {n} as built, hash 0x1")
    elif "--pds" in o:
        m = re.match(r"q019-(\d)-r(\d)-a(\d\d)$", name)
        run, rows, lo = (int(m[1]), int(m[2]), int(m[3])) if m else (1, 0, 0)
        mk = [0xA0000000 | run << 24 | rows << 16 | (lo + k) for k in range(16)]
        if name == "pk-e125":
            mk = [0xA0A00000 + k for k in range(16)]
        sa = {i: 0x0DA7A000 for i in range(64)}
        if lo < 32:
            sa.update({lo + k: v for k, v in enumerate(mk)})
        out.append(f"probe {name}: o0 0x0da7a000 (2048 of 2048)")
        out += [f"probe {name}: scratch +0x{4 * i:03x} 0x{sa[i]:08x}" for i in range(32)]
        out.append(f"probe {name}: scratch 32 more changed")
    else:
        out.append(f"probe {name}: o0 0xff000000 (2048 of 2048)")
        if "--pixels" in o:
            out += [f"probe {name}: row {y}: " + " ".join(["ff000000"] * 64) for y in range(32)]
    if "noecho" not in world:
        out += [f"probe {name}: poked {s}:{i} 0x{a:08x} -> 0x{b:08x}" for s, i, a, b in pk]
    return dict(rc=0, out="\n".join(out) + "\n")


def copy(argv, world):
    p, why = parse(argv, {"--poke"}, {"--every-value", "--pixels"})
    if why:
        return usage(why)
    o, files = p
    if files or "--every-value" not in o:
        return usage("copy here: --every-value")
    pk, why = pokes(o.get("--poke", []), world, ("xfer", "tex"))
    if why:
        return usage(why)
    h = E037["csc"] if any(s == "xfer" and i == 17 for s, i, _, _ in pk) else E037["none"]
    out = ["job: ok", f"target: 64x32 hash {h}", "diff: 2048 of 2048 pixels, first (0, 0) "
           "0xff000000 expected 0xff102030"]
    return dict(rc=1, out="\n".join(out) + "\n")


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe":
        return probe(argv, world)
    if argv[0] == "copy":
        return copy(argv, world)
    return usage(f"{argv[0]} is not this session's")
