# SPDX-License-Identifier: MIT
"""rdmodel.py: the frozen configurations and model family of stage p6-rd (Q276: is an o4..o7 write stored, and does the predicate
gate it), shared by the generator (programs, frozen predictions) and the scorer's tests.  The scorer reads the predictions from
predictions/p6-rd.tsv, not from here.  The fake tool does NOT use this module: it interprets the staged program's own decode
(tests/fake_o4.py), so a slip in a configuration here shows up as a mismatch, not as a mock that agrees by construction.

Plan: closing6/pixel/exp-pixel-r6.md section 2 (decisions R6-2 a, pixel decisions 2 a, 3 a).  Word layout (R5, E858): low 16 bits =
marker << 6 | bits 5:4 << 4 | tag; tags o0 1, o1 12 then 2, o2 3, o3 4, o4 5, o5 6, o6 7, o7 8 (o5model.TAG).
A configuration: the words each output is given (low 6 bits, None = not written), the readback (`mov.skipinv r10, oJ` then
`mov.skipinv.end o0, r10` as the last two instructions: the own pixel shows what oJ held, E373), and for the predicate rows the
pair written to oJ (`or.skipinv oJ` with bits 0, then `p1 or.skipinv oJ` with bit 4; p1 = (g25 == k) set right after o0).
Labels of one own-pixel word: "T:B" (tag T, bits 5:4 = B).  Classes of a readback configuration (section 2.1):
  S   the label of the word oJ was given (bits 5:4 = 1)        A0  "1:2", o0's word
  A4  o_(J-4)'s word, bits 2 (J >= 4; at J = 4 it is o0's word, so A4 = A0 there and the class is named A0)
  X   fewer than 5 percent of the TRI pixels carry the job's marker      O:T.B  >= 90 percent carry one other marker's word
  W:T.B  the job's marker with a label none of the above names (recorded as it is)."""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
import o5model as M  # noqa: E402

TAG = M.TAG
MODELS = ["H-STORE", "H-FOUR", "H-O0", "H-MOD4"]
RD_J = range(1, 8)
PRD_J, PRD_K = (3, 4), (0, 1, 2, 3, 7)
PMODELS = ["gated", "ignored", "never"]
CPRD_K = (1, 7)
TRI_MIN = 300              # TRI (own c-rd-0 words in both jobs) below this: readback cannot be read
CLASS_SHARE, X_SHARE, O_SHARE, LANE_SHARE, CTL_SHARE = 0.90, 0.05, 0.90, 0.95, 0.95


def lab(w6):
    return f"{w6 & 15}:{(w6 >> 4) & 3}"


def walk(j):
    return M.walk(j)


def config(name):
    """dict(words, read, pred) of a readback configuration (rd-j, n-rd-j, x-rd-j, prd-j-k), or None for the special controls."""
    if name.startswith("rd-"):
        j = int(name[3:])
        return dict(words=walk(j), read=j, pred=None)
    if name.startswith("n-rd-"):
        j = int(name[5:])
        w = {i: TAG[i] | 0x20 for i in range(8)}
        w[j] = None
        return dict(words=w, read=j, pred=None)
    if name.startswith("x-rd-"):
        j = int(name[5:])
        w = walk(j)
        w[j] = (9 + j) | 0x10
        return dict(words=w, read=j, pred=None)
    if name.startswith("prd-"):
        _, j, k = name.split("-")
        j, k = int(j), int(k[1:])
        return dict(words=M.base(), read=j, pred=(j, k))
    return None


def labels(name):
    """{class: label} of a readback configuration: S, A0, A4 (A4 only for J >= 5: at J = 4 it is A0)."""
    c = config(name)
    j = c["read"]
    s = c["words"][j] if c["words"][j] is not None else TAG[j] | 0x10       # n-rd: the S word cannot exist in the job
    out = {"S": lab(s), "A0": "1:2"}
    if j >= 5:
        out["A4"] = f"{TAG[j - 4]}:2"
    return out


def rd_class(model, j):
    """The frozen class of rd-j under a model."""
    if model == "H-STORE":
        return "S"
    if model == "H-O0":
        return "A0"
    if j < 4:
        return "S"
    if model == "H-FOUR":
        return "!S"
    return "A0" if j == 4 else "A4"                                  # H-MOD4


def rd_vector(model):
    return tuple(rd_class(model, j) for j in RD_J)


def matches(frozen, read):
    return read is not None and (read != "S" if frozen == "!S" else read == frozen)


def prd_lanes(j, k, pmodel):
    """The frozen own-pixel label of lanes 0..3 of prd-j-k (the readback of oJ) under gated / ignored / never."""
    b4, b0 = lab(TAG[j] | 0x10), lab(TAG[j])
    return tuple((b4 if (pmodel == "ignored" or (pmodel == "gated" and lane == k)) else b0) for lane in range(4))


def cprd_lanes(k):
    """c-prd-0-kK: o0 = W_0 (bits 2), p1 o0 = W_1 (bits 1): frozen [infer from E808's o1 result] W_1 on lane k, W_0 elsewhere."""
    return tuple("1:1" if lane == k else "1:2" for lane in range(4))


def lane_of(x, y):
    return (x & 1) | (y & 1) << 1
