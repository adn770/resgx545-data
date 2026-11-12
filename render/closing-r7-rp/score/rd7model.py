# SPDX-License-Identifier: MIT
"""rd7model.py: the configurations, labels and frozen model classes of stages p7-rdc and p7-rd (r7-rp, Q276; plan
closing7/a/exp-pixel-r7.md 1.4 and 3.4).  R6's model module (rd_rdmodel.py, a copy of closing6/r6-pixel/score/rdmodel.py with its
one import renamed) gives the readback configurations and the rd vector; this module adds the round-7 rows and rules.  The generator
writes the frozen predictions from here; the scorer reads them from predictions/p7-rd.tsv, not from here.  The world (tests/
world_rd.py) does NOT import this module: it answers from its own table of program words.

Rows of p7-rd: replicates rd-1..rd-7, n-rd-4, x-rd-4 (R6's programs byte for byte); held out x-rd-6, x-rd-7 (o6 / o7 written with
the R6 formula (9 + j) | 0x10: tag 15 with bit 4, and at j = 7 0x10, tag 0 with bit 4: "tag 16" does not fit the 4-bit tag), n-rd-5
(no o5 write); clean cl-4..cl-7 (only o0 = word A 0x21, 1:2, and o_j = word B, o_j's tag with bit 4, written, then read); cl-p4 at
k = 0 (cl-4 with its o4 write under `p1`, p1 = (g25 == 0))."""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
import rd_o5model as M  # noqa: E402
import rd_rdmodel as RM  # noqa: E402

TAG = M.TAG
MODELS = RM.MODELS                         # H-STORE, H-FOUR, H-O0, H-MOD4 (frozen in R6)
RD = [f"rd-{j}" for j in RM.RD_J]
REPL = RD + ["n-rd-4", "x-rd-4"]           # replicates of R6's p6-rd (R6's programs byte for byte)
HELD = ["x-rd-6", "x-rd-7", "n-rd-5"]      # held out, own-source rule
CLEAN = ["cl-4", "cl-5", "cl-6", "cl-7"]   # held out, R6's original rule
CLP = "cl-p4"                              # held out, R6's lane rule
CONTROLS = ["c-e709", "c-u", "c-all4", "c-ow", "c-rd-0", "c-prd-0-k1", "c-prd-0-k7"]
# R6's top labels (fold/posthoc_r6.txt section A, the same in the x and the y job of every configuration)
R6_TOP = {"rd-1": "2:1", "rd-2": "3:1", "rd-3": "4:1", "rd-4": "1:2", "rd-5": "2:2", "rd-6": "3:2", "rd-7": "4:2",
          "n-rd-4": "1:2", "x-rd-4": "1:2"}
WORD_A = 0x21                              # tag 1, bits 2 (R6's W_A)
OWN_SHARE, RIVAL_MAX = 0.85, 0.02          # the frozen own-source rule (plan 3.4)
OWN_MIN = RM.TRI_MIN                       # fewer own-source words than this in a job: the rule cannot read it (cannot tell)
CLP_K = 0


def lab(w6):
    return RM.lab(w6)


def config(name):
    """dict(words, read, pred) of a p7-rd configuration."""
    if name.startswith("cl-p"):
        j = int(name[4:])
        w = {i: None for i in range(8)}
        w[0], w[j] = WORD_A, TAG[j] | 0x10
        return dict(words=w, read=j, pred=(j, CLP_K))
    if name.startswith("cl-"):
        j = int(name[3:])
        w = {i: None for i in range(8)}
        w[0], w[j] = WORD_A, TAG[j] | 0x10
        return dict(words=w, read=j, pred=None)
    return RM.config(name)


def labels(name):
    """{class: label}: S (the word written to the register read), A0 (o0's word, 1:2), A4 (o_(j-4)'s word, j >= 5; not for clean
    rows, whose o1..o3 are unwritten)."""
    if name.startswith("cl-"):
        c = config(name)
        return {"S": lab(c["words"][c["read"]]), "A0": lab(WORD_A)}
    return RM.labels(name)


def klass(model, name):
    """The frozen class of a readback or clean configuration under a model ('!S': any decided class but S)."""
    if name.startswith("rd-"):
        return RM.rd_class(model, int(name[3:]))
    c = config(name)
    j, wj = c["read"], c["words"][c["read"]]
    if model == "H-O0":
        return "A0"
    if model == "H-STORE":
        return "S" if wj is not None else "!S"
    if model == "H-FOUR":
        return "S" if j < 4 and wj is not None else "!S"
    # H-MOD4: o_j for j < 4, o_(j-4) for j >= 4
    if name.startswith("cl-"):
        return "A0" if j == 4 else "!S"            # cl-5..7: o1..o3 hold no word of the program: not word B
    return "A0" if j == 4 else "A4"


def clp_lanes(model):
    """cl-p4's frozen own-pixel label per lane 0..3 ('!5:1': any label but word B)."""
    b = lab(TAG[4] | 0x10)
    if model in ("H-MOD4", "H-O0"):
        return tuple(lab(WORD_A) for _ in range(4))
    if model == "H-STORE":                          # gated (R6's c-prd-0: the predicate gates per lane), stored and read back
        return tuple(b if lane == CLP_K else "!" + b for lane in range(4))
    return tuple("!" + b for _ in range(4))          # H-FOUR: never o4's own word


def lane_match(frozen, read):
    return read is not None and (read != frozen[1:] if frozen.startswith("!") else read == frozen)


def store_j(name):
    """The register number a configuration reads (for "H-STORE at j")."""
    return config(name)["read"]
