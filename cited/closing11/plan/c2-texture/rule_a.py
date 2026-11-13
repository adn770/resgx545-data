"""c2-texture check A (Q177 / E1000), frozen rule. Standard library only.

Offsets of T0 u address modes 4 to 7 on a twiddled 32-bit texture, as dwords read past E561's
index (texel index by the tile law of resgx545-data render/closing-r10-tex/gen/addr.py index()):
  H-MAX  (tested)  modes 4, 6, 7 (and mode 5 with the texel column s inside the texture):
                   index + 8 M + 52, M = max(W, H); mode 5 with s outside the texture and the
                   texel row t inside [0, H): 5 M + 52 + t (s < 0) or 6 M + 52 + t (s >= W).
  H-W    (rival)   the same with W for M everywhere (E957 / E983's reading).
  H-H    (rival)   the same with H for M everywhere.
Mode 5 with s outside and t outside [0, H) (the corners): not predicted by the offset rules;
  C-CONST (tested) dword 20 (t < 0, s < 0), 21 (t < 0, s >= W), 22 (t >= H, s < 0), 23 (t >= H,
                   s >= W), whatever the shape (E983's reading of one 32 x 8 texture).
  C-ROW  (rival)   the row rule above with t wrapped into the texture (what a row inside reads).
Mode 5 with s inside and t outside: no frozen prediction (not scored).
Scope: kept twiddled jobs (T1 bits 28-31 zero) whose u mode (T0 bits 6-8) is 4 to 7.
Per job and rule: pixels equal / pixels scored. A rule HOLDS a job if every scored pixel is
equal. A job DISCRIMINATES max from W (or from H) if the two predictions differ on at least one
pixel of it. A job is HELD OUT for the max rule only if it discriminates and no earlier fit read
it. Verdict on the question: held out for max-vs-W and max-vs-H discriminating jobs: count.
"""


def wrap(v, mode, n):
    return v % n if mode in (0, 4, 5) else min(max(v, 0), n - 1)


def morton(x, y, w, h):
    bw, bh = max(w, 1).bit_length() - 1, max(h, 1).bit_length() - 1
    common = min(bw, bh)
    i = 0
    for b in range(common):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    rest = (x if bw > bh else y) >> common
    return i | rest << (2 * common)


def index(s, t, w, h):
    tw, th = min(w, 16), min(h, 16)
    return morton(s % tw, t % th, tw, th) + tw * th * (s // tw + (w // tw) * (t // th))


def side(model, w, h):
    return {"H-MAX": max(w, h), "H-W": w, "H-H": h}[model]


def predict(model, w, h, um, vm, s, t):
    """Dword index read, or None where the rule gives none."""
    if um < 4:
        return None
    m = side(model, w, h)
    if um == 5 and not 0 <= s < w:
        if 0 <= t < h:
            return (5 if s < 0 else 6) * m + 52 + t
        return None
    return index(wrap(s, um, w), wrap(t, vm, h), w, h) + 8 * m + 52


def corner(model, w, h, s, t):
    """Mode 5, s outside the texture and t outside [0, h)."""
    left = s < 0
    if model == "C-CONST":
        return 20 + (0 if t < 0 else 2) + (0 if left else 1)
    if model == "C-ROW":
        tt = t % h
        return (5 if left else 6) * max(w, h) + 52 + tt
    raise ValueError(model)
