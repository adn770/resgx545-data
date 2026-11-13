"""score.py: scores the frozen c7_rule.py on E986's kept dumps (render/closing-r10-zls zst2).
python -I score.py > score.out   (run from this directory with PYTHONPATH=.)"""
import struct
from lib import *
import c7_rule as R
import zst2 as Z

tw_of = lambda w: -(-w // 32)


def block_of(tx, ty, tw):
    return 2 * tw * (ty >> 1) + 2 * tx + (ty & 1)


def rowvals(ref, tx, ty, tw):
    """16 lists of 32 reference dwords of tile (tx, ty)"""
    slot = ty * tw + tx
    return [[ref[512 * slot + Z.in_tile_index(x, y)] for x in range(32)] for y in range(16)]


def f6_job(name, w, h, fit_blocks):
    d = dw("zst2", name)
    ref = dw("zst2", Z.ref_of(name))
    tw = tw_of(w)
    th = -(-h // 16)
    tot_changed = sum(v != FILL for v in d)
    dec = held = fail = 0
    print(f"== {name}: changed {tot_changed} dwords of {len(d)}")
    for ty in range(th):
        for tx in range(tw):
            blk = block_of(tx, ty, tw)
            rows = rowvals(ref, tx, ty, tw)
            data = d[512 * blk:512 * blk + 512]
            chg = sum(v != FILL for v in data)
            app = 0
            res = []
            for q in range(4):
                rs = rows[4 * q:4 * q + 4]
                if not all(len(set(r)) == 1 for r in rs):
                    break
                p = R.f6c_group([r[0] for r in rs])
                ok = data[12 * q:12 * q + 12] == p
                raw = []
                for r in range(4):
                    raw += [rs[r][0] | R.SIGN] * 0  # raw rival compared below
                res.append(ok)
            tag = "FIT" if (name, blk) in fit_blocks else "held-out"
            n_ok = sum(res)
            n_bad = len(res) - n_ok
            print(f"  tile ({tx},{ty}) block {blk} [{tag}]: changed {chg}; applicable groups "
                  f"{len(res)} -> held {n_ok}, failed {n_bad}; dwords decoded {12 * n_ok}, "
                  f"undecoded {chg - 12 * n_ok}")
            # rival: E985 raw layout on the first group's 12 dwords
            if res:
                rawp = [rows[y // 32][0] | R.SIGN if False else 0 for y in range(0)]
                raw_hit = sum(1 for q in range(len(res)) for i in range(12)
                              if data[12 * q + i] == (rows[(12 * q + i) // 32][(12 * q + i) % 32]
                                                      | R.SIGN))
                print(f"    rival F6RAW on the same {12 * len(res)} dwords: {raw_hit} equal")
            if tag == "FIT":
                dec += 12 * n_ok
            else:
                held += 12 * n_ok
                fail += 12 * n_bad
    print(f"  {name}: decoded dwords fit {dec}, held-out held {held}, held-out failed {fail}")


FIT = {("z2y-f6", 0)}
f6_job("z2y-f6", 64, 32, FIT)
f6_job("z2e-f6", 40, 20, FIT)
f6_job("z2d-f6", 64, 32, FIT)

print("== format 7, constant stencil fills (x ramp, 64 x 32)")
for n, S, tag in (("sa5", 0xa5, "FIT"), ("s00", 0x00, "held-out"), ("sff", 0xff, "held-out")):
    d = dw("zst2", "z2x-f7-" + n)
    for riv in (False, True):
        pred = {}
        for k in range(4):
            for i, v in enumerate(R.f7k_block(S, riv)):
                pred[256 * k + i] = v
        changed = {i for i, v in enumerate(d) if v != FILL}
        ok = sum(1 for i, v in pred.items() if d[i] == v)
        extra = len(changed - set(pred))
        print(f"  {n} [{tag}] {'RIVAL' if riv else 'RULE '}: {ok} of {len(pred)} dwords equal, "
              f"changed dwords outside the prediction {extra}; verdict "
              f"{'HELD' if ok == len(pred) and not extra else 'FAILED'}")
