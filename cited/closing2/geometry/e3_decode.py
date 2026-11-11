#!/usr/bin/env python3
"""Q230 offline: decode every g-e3 object of S1 and S1b (vertices in order, 1/w word, depth word, primitive list,
region headers with streams) with the landed pbdump, read-only."""
import sys, pathlib, gzip, struct
sys.dont_write_bytecode = True
HOME = pathlib.Path.home()
sys.path.insert(0, str(HOME / "src/resgx545/tools/usse-asm"))
import pbdump  # noqa: E402


def gz(p):
    return gzip.open(p).read() if p.exists() else None


def f32(w):
    return struct.unpack("<f", struct.pack("<I", w & 0xffffffff))[0]


def decode(param, tadata):
    ws = pbdump.obj(param) if param else []
    if not ws:
        return None
    o = pbdump.first_object(param, tadata)
    if o is None:
        return dict(unlisted=True, nwords=len(ws))
    big = 0
    for i, w in enumerate(o["packed"]):
        big |= w << (32 * i)
    nv = len(o["vertices"])
    vs = []
    for v in range(nv):
        y = (big >> (80 * v)) & 0xffffff
        x = (big >> (80 * v + 24)) & 0xffffff
        z = (big >> (80 * v + 48)) & 0xffffffff
        vs.append((x / 256 - 4096, y / 256 - 4096, z, o["PB_OBJ.RHW"][v]))
    regs = [(r.index, r.col, r.row, pbdump.region_flags(r.flags), r.stream) for r in pbdump.regions(tadata) if r.stream]
    return dict(nv=nv, vs=vs, prims=o["PB_OBJ.PRIM_LIST"], b15=o["PB_OBJ.PRIM_LIST bit 15"], isp=o["PB_OBJ.ISP_WORDS"],
                fmt=o["format"], regions=regs, nwords=len(ws))


def main():
    for tag, d in (("S1", HOME / "src/resgx545-data/render/closing-s1/out/g-e3"),
                   ("S1b", HOME / "src/resgx545-data/render/closing-s1b/out/g-e3")):
        d = pathlib.Path(d)
        names = sorted({p.name.split(".")[0] for p in d.glob("*.txt.gz")})
        for n in names:
            param = next((gz(p) for p in d.glob(f"{n}.*param.bin.gz")), None)
            tadata = next((gz(p) for p in d.glob(f"{n}.*tadata.bin.gz")), None)
            if param is None or tadata is None:
                print(tag, n, "no dump"); continue
            r = decode(param, tadata)
            if r is None:
                print(f"{tag} {n}: no object"); continue
            if r.get("unlisted"):
                print(f"{tag} {n}: written but unlisted ({r['nwords']} dwords)"); continue
            print(f"{tag} {n}: {r['nv']} vertices, prims {r['prims']} bit15 {r['b15']}, isp {[hex(w) for w in r['isp']]}, fmt {r['fmt']:#x}")
            for i, (x, y, z, rhw) in enumerate(r["vs"]):
                print(f"    v{i}: x {x:9.4f} y {y:9.4f} depth {z:#010x} = {f32(z):.7g}  1/w {rhw:#010x} = {f32(rhw):.8g}")
            print(f"    regions with streams: {[(c, rw) for _, c, rw, _, _ in r['regions']]}")


if __name__ == "__main__":
    main()
