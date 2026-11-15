# SPDX-License-Identifier: MIT
"""mock/world.py: r25-sa64's fake laptop for kit/session.py mock. answer() sees the tool's name,
the argv and the world's tokens; it returns None (the health pair) or dict(rc, out, err, files).
The probe's NAME is its FILE's base name, as the tool prints it; what a program stores is read
from that name (q019-RUN-rROWS-aLO: E391's markers 0xa<run><rows:02x><attribute:04x>; pk-e391 is
E391's case 0, pk-e125 E125's case 0 with its 16 dwords), never from a case table.

As strict as t24 (1341034) on this session's rows: `probe` with --temps N, --pds N with --use
FILE, --scratch-show N (1 to 64), --poke bg:N[^]=V, one FILE; anything else is refused as the
tool's usage error (rc 2). t24 echoes each applied poke after the job and prints the first N
changed scratch dwords, then `scratch K more changed` for the rest.

EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  none     attributes 32-63 reach no sa at any size (H-NONE, E391's reading): all run (0)
  all64    attributes 0-63 at their own sa at every size (H-ALL64): all run (0)
  rows     the size field limits a fill to 32 + 16 a row attributes (H-ROWS with a fit table
           that is not flat): all run (0)
  noecho   a tool without the echo: pk-e391 echoes 0 of 1: hook_check stops pk64 (24) and the
           session ends (on_stop = "end")
  capped   a tool that prints 32 dwords whatever --scratch-show says (`scratch 32 more changed`):
           hook_check stops pk64 (24), the session ends
  e1096off pk-e391's sa0-sa15 do not read E1096's markers: pk64's control FAILs in the scorer
           (the job reads ok), the gate skips q019 (None)
"""
import os
import re

ALL0 = {"pk64": 0, "q019": 0}
EXPECT = {"none": (0, ALL0),
          "all64": (0, ALL0),
          "rows": (0, ALL0),
          "noecho": (24, {"pk64": 24}),
          "capped": (24, {"pk64": 24}),
          "e1096off": (0, {"pk64": 0, "q019": None})}
BUILT = {("bg", 1): 0x00130000}   # the word as the library builds it
SPEC = re.compile(r"^(bg):(\d+)(\^?)=(0x[0-9a-fA-F]+|\d+)$")
STALE = 0x0DA7A000


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


def pokes(specs):
    lines = []
    for s in specs:
        m = SPEC.match(s)
        if not m:
            return None, f"--poke {s}"
        old = BUILT.get((m[1], int(m[2])), 0x11110000 | int(m[2]))
        v = int(m[4], 0)
        lines.append((m[1], int(m[2]), old, old ^ v if m[3] else v))
    return lines, None


def limit(world, rows):
    """How many attributes reach their sa at a size of ROWS rows, in this world."""
    if "all64" in world:
        return 64
    if "rows" in world:
        return min(64, 32 + 16 * rows)
    return 32


def probe(argv, world):
    p, why = parse(argv, {"--temps", "--pds", "--use", "--poke", "--scratch-show"},
                   {"--coords", "--pixels"})
    if why:
        return usage(why)
    o, files = p
    if len(files) != 1:
        return usage("probe takes one FILE here")
    if ("--pds" in o) != ("--use" in o):
        return usage("--pds needs --use")
    show = 32
    if "--scratch-show" in o:
        v = o["--scratch-show"][-1]
        if not v.isdigit() or not 1 <= int(v) <= 64:
            return usage(f"--scratch-show {v}")
        show = int(v)
    if "capped" in world:
        show = 32
    pk, why = pokes(o.get("--poke", []))
    if why:
        return usage(why)
    name = os.path.basename(files[0])[:-len(".bin")]
    out = [f"probe {name}: scratch at 0x3e003000 (64 KiB)"]
    if pk:
        out.append(f"probe {name}: pokes " + " ".join(o["--poke"]))
    if "noecho" not in world:
        out += [f"probe {name}: poked {s}:{i} 0x{a:08x} -> 0x{b:08x}" for s, i, a, b in pk]
    out.append(f"probe {name}: o0 0x{STALE:08x} (2048 of 2048)")
    if name == "pk-e125":
        sa = {k: 0xA0A00000 + k for k in range(16)}
    else:
        m = re.match(r"q019-(\d)-r(\d)-a(\d\d)$", name)
        run, rows, lo = (int(m[1]), int(m[2]), int(m[3])) if m else (1, 0, 0)
        if name == "pk-e391" and "e1096off" in world:
            lo = 16
        sa = {i: STALE for i in range(64)}
        sa.update({lo + k: 0xA0000000 | run << 24 | rows << 16 | (lo + k)
                   for k in range(16) if lo + k < limit(world, rows)})
    keys = sorted(sa)
    out += [f"probe {name}: scratch +0x{4 * i:03x} 0x{sa[i]:08x}" for i in keys[:show]]
    if len(keys) > show:
        out.append(f"probe {name}: scratch {len(keys) - show} more changed")
    return dict(rc=0, out="\n".join(out) + "\n")


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe":
        return probe(argv, world)
    return usage(f"{argv[0]} is not this session's")
