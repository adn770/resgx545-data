# SPDX-License-Identifier: MIT
"""world_rd.py: the fake tool's answers for the rows of p7-rdc and p7-rd (r7-rp, Q276), from ARGV ONLY: the command must be R6's
p6-rd shape (C_BASE) exactly and the program is the LAST argument's file name.  It does not import the generator's model
(rd7model): the words each program writes are typed here by hand from the plan (closing7/a/exp-pixel-r7.md 3.4), so a slip in
the generator shows as a mismatch, not as a mock that agrees by construction.

Images: every row's image starts from a REAL kept image of R6's p6-rd (resgx545-data render/closing-r6-pixel, attempt
20261112-142113): R6's programs take their own row's image, the new ones a template (x-rd-6 <- rd-6, x-rd-7 <- rd-7, n-rd-5 <- rd-5,
cl-* <- c-rd-0).  In the image, every word with the template's marker is given the program's marker, and every own-source word that
carries the template's top label (the readback's word) is replaced by what the world's model reads from the register (no word: the
background 0xff203040, as E878's n-rd-1).  Words of the walk's other outputs (D words) stay, so the old 0.90-of-TRI rule cannot
decide and the own-source rule must.
Tokens (FAKE_WORLD words):
  model     H-MOD4: o1..o3 read their own word, o4..o7 the word of o_(j-4); every frozen prediction holds
  hstore    H-STORE: every register reads the word written to it (cl-p4: lane 0 only, the predicate gates)
  gatefail  c-ow keeps its FIRST o0 write (1:2): c-ow fails, the p7-rdc gate FAILS
  o4none    c-e709 draws no tag-5 word: G-o4 fails the gate
  noall4    c-all4 draws no tag-5 word: p7-rd is void
  norep     rd-2 reads o0's word (1:2): not replicated
  rival     x-rd-6: 5 percent of its own-source words are S (tag 15): a rival class above 0.02, cannot tell
  fault     x-rd-6 faults (3D side BIF fault, `job: failed: job faulted`, rc 1)
The real tool (t4, 4623753) writes DIR/<program>.param.bin and DIR/<program>.tadata.bin for --dump-render DIR and, when DIR is
missing, prints `probe NAME: failed: --dump-render: No such file or directory` after the rows and exits 3 (realmock, measured)."""
from __future__ import annotations

import gzip
import os
import re
import zlib

R6K = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data") + "/render/closing-r6-pixel/out/20261112-142113/p6-rd"
BG = 0xff203040
TAG = {i: i + 1 for i in range(8)}
SHAPE = re.compile(r"^probe --tri pixel --temps 32 --pixels --dump-render (\S+) --width 64 --height 64 --vtx-coords 2 "
                   r"--blk 4=0x00030001 --slot pixpds=(\S+)/pds_iter_xy\.bin:12 --slot vtxuse=(\S+)/vtx_coords\.bin (\S+)\.bin$")
FAULT_KMSG = "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90100 at 0x10000016 (PD 0x30d6e000) stalls job 86, recovering"


def walk(j):
    return {i: TAG[i] | (0x10 if i == j else 0x20) for i in range(8)}


def bits2(skip):
    w = {i: TAG[i] | 0x20 for i in range(8)}
    w[skip] = None
    return w


def clean(j):
    w = {i: None for i in range(8)}
    w[0], w[j] = 0x21, TAG[j] | 0x10
    return w


# program stem (no -x / -y) -> (template R6 row, words, register read, predicated: (lane that writes) or None, new markers x/y)
PROGS = {f"r6o-rd-{j}": (f"rd-{j}", walk(j), j, None, None) for j in range(1, 8)}
PROGS.update({
    "r6o-n-rd-4": ("n-rd-4", bits2(4), 4, None, None),
    "r6o-x-rd-4": ("x-rd-4", {**walk(4), 4: 13 | 0x10}, 4, None, None),
    "r7o-x-rd-6": ("rd-6", {**walk(6), 6: 15 | 0x10}, 6, None, (0x1f0, 0x1f1)),
    "r7o-x-rd-7": ("rd-7", {**walk(7), 7: 0x10}, 7, None, (0x1f2, 0x1f3)),
    "r7o-n-rd-5": ("rd-5", bits2(5), 5, None, (0x1f4, 0x1f5)),
    "r7o-cl-4": ("c-rd-0", clean(4), 4, None, (0x1f6, 0x1f7)),
    "r7o-cl-5": ("c-rd-0", clean(5), 5, None, (0x1f8, 0x1f9)),
    "r7o-cl-6": ("c-rd-0", clean(6), 6, None, (0x1fa, 0x1fb)),
    "r7o-cl-7": ("c-rd-0", clean(7), 7, None, (0x1fc, 0x1fd)),
    "r7o-cl-p4": ("c-rd-0", clean(4), 4, 0, (0x1fe, 0x1ff)),
})
CONTROLS = {"r4o-e709": "c-e709", "r4o-u": "c-u", "r5o-c-all4": "c-all4", "r6o-c-ow": "c-ow", "r6o-c-rd-0": "c-rd-0",
            "r6o-c-prd-0-k1": "c-prd-0-k1", "r6o-c-prd-0-k7": "c-prd-0-k7"}


def _rows(text):
    r = {}
    for ln in text.splitlines():
        m = re.search(r"row (\d+): (.*)$", ln)
        if m:
            r[int(m[1])] = [int(v, 16) for v in m[2].split()]
    return [r[i] for i in sorted(r)]


_cache = {}


def r6_image(row):
    if row not in _cache:
        _cache[row] = _rows(gzip.open(os.path.join(R6K, row + ".txt.gz")).read().decode())
    return [list(r) for r in _cache[row]]


def f32_hi(v):
    import struct
    return struct.unpack("<f", struct.pack("<I", v & 0xffff0000))[0]


def own(v, x, y, ax, m):
    """The word has marker m and decodes to the pixel itself along its job's axis."""
    if v == BG or ((v & 0xffff) >> 6) != m:
        return False
    c = round(f32_hi(v) * 32 + 32 - .5)
    return c == (x if ax == "x" else y)


def top_label(g, ax, m):
    c = {}
    for y, r in enumerate(g):
        for x, v in enumerate(r):
            if own(v, x, y, ax, m):
                c[v & 0x3f] = c.get(v & 0x3f, 0) + 1
    return max(c, key=lambda k: (c[k], k)) if c else None


def template_marker(g, ax):
    """The template's job marker: the commonest marker among the words that decode to their own pixel."""
    c = {}
    for y, r in enumerate(g):
        for x, v in enumerate(r):
            if v != BG:
                mk = (v & 0xffff) >> 6
                if round(f32_hi(v) * 32 + 32 - .5) == (x if ax == "x" else y):
                    c[mk] = c.get(mk, 0) + 1
    return max(c, key=lambda k: (c[k], k))


def readback(words, j, pred_lane, lane, model):
    """The 6-bit word the readback of o_j returns at a lane, or None (the background word)."""
    w = dict(words)
    if pred_lane is not None and lane != pred_lane:
        w[j] = None                                   # the predicated write runs on its lane only
    if model == "hstore":
        return w[j]
    return w[j] if j < 4 else w[j - 4]               # H-MOD4 (an o4 write is never read back: the predicate cannot show)


def h(key, mod):
    return zlib.crc32(key.encode()) % mod


def image(stem, ax, tokens):
    if stem in CONTROLS:
        g = r6_image(f"{CONTROLS[stem]}-{ax}")
        if (stem == "r6o-c-ow" and "gatefail" in tokens) or (stem == "r4o-e709" and "o4none" in tokens) \
                or (stem == "r5o-c-all4" and "noall4" in tokens):
            m = template_marker(g, ax)
            for y, r in enumerate(g):
                for x, v in enumerate(r):
                    if stem == "r6o-c-ow" and own(v, x, y, ax, m) and (v & 0x3f) == 0x11:
                        r[x] = (v & ~0x3f) | 0x21                   # the first o0 write stays
                    elif stem != "r6o-c-ow" and v != BG and (v & 15) in (5, 13):
                        r[x] = BG                                   # no tag-5 word
        return g
    tmpl, words, j, plane, mks = PROGS[stem]
    g = r6_image(f"{tmpl}-{ax}")
    m_old = template_marker(g, ax)
    m_new = m_old if mks is None else mks[0 if ax == "x" else 1]
    top = top_label(g, ax, m_old)
    model = "hstore" if "hstore" in tokens else "model"
    for y, r in enumerate(g):
        for x, v in enumerate(r):
            if v == BG or ((v & 0xffff) >> 6) != m_old:
                continue
            lo = v & 0x3f
            if own(v, x, y, ax, m_old) and lo == top:
                lane = (x & 1) | (y & 1) << 1
                wd = readback(words, j, plane, lane, model)
                if stem == "r6o-rd-2" and "norep" in tokens:
                    wd = 0x21
                if stem == "r7o-x-rd-6" and "rival" in tokens and h(f"{ax}{x},{y}", 20) == 0:
                    wd = words[6]
                if wd is None:
                    r[x] = BG
                    continue
                lo = wd
            r[x] = (v & 0xffff0000) | (m_new << 6) | lo
    return g


def o0_line(name, g):
    c = {}
    for r in g:
        for v in r:
            c[v] = c.get(v, 0) + 1
    top = sorted(c.items(), key=lambda t: (-t[1], t[0]))
    s = " ".join(f"0x{v:08x} x{n}" for v, n in top[:4])
    rest = sum(n for _, n in top[4:])
    return f"probe {name}: o0 mixed {s}" + (f" other x{rest}" if rest else "")


def handles(tool, argv):
    return tool == "t4" and SHAPE.match(" ".join(argv)) is not None and \
        os.path.basename(argv[-1])[:-4].rsplit("-", 1)[0] in {**PROGS, **CONTROLS}


def answer(tool, argv, tokens):
    tokens = set(tokens)
    m = SHAPE.match(" ".join(argv))
    if tool != "t4" or not m:
        return dict(out="", err="sgxfive-test: not a p7 row of this world\n", rc=2, kmsg=[])
    ddir, prog = m[1], argv[-1]
    name = os.path.basename(prog)[:-4]
    stem, ax = name.rsplit("-", 1)
    if not os.path.exists(prog):
        return dict(out=f"probe {name}: failed: {prog}: No such file or directory\n", err="", rc=3, kmsg=[])
    head = ["programs asm", f"probe {name}: scratch at 0x3e00e000 (64 KiB)",
            f"probe {name}: tri 64x64 (2 coordinates) (block words 4), vtxuse pixel pixpds replaced"]
    if "fault" in tokens and stem == "r7o-x-rd-6":
        return dict(out="\n".join(head) + "\njob: failed: job faulted\n", err="", rc=1, kmsg=[FAULT_KMSG])
    g = image(stem, ax, tokens)
    lines = head + [o0_line(name, g)] + [f"probe {name}: row {y}: " + " ".join(f"{v:08x}" for v in r) for y, r in enumerate(g)]
    if not os.path.isdir(ddir):
        lines.append(f"probe {name}: failed: --dump-render: No such file or directory")
        return dict(out="\n".join(lines) + "\n", err="", rc=3, kmsg=[])
    p, t = os.path.join(ddir, name + ".param.bin"), os.path.join(ddir, name + ".tadata.bin")
    open(p, "wb").write(b"\0" * 4096)
    open(t, "wb").write(b"\0" * 1024)
    lines.append(f"probe {name}: render memory to {ddir}/{name}.{{param,tadata}}.bin (4096, 1024 bytes)")
    return dict(out="\n".join(lines) + "\n", err="", rc=0, kmsg=[])
