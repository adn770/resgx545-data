"""Detail of an-t0b27's halves where R10-BF11 and FTZ-OUT part (run after score_b.py; frozen rule_b)."""
exec(open("score_b.py").read().split("for nm in (")[0])
spec_an = json.load(open(D + "/texture/p1141/support/specs.json"))["an-t0b27"]["spec"]
hw = pins.pixels(gzip.open(D + "/texture/p1132/tx-lod/an-t0b27.txt.gz", "rt").read(), 2048)
foot = foot_tm(spec_an)
print("pixel(x,y) ch bytes(00,10,01,11) kx ky | stage outputs unflushed (top, bot, y) | BF11 OUT IN INOUT HW (half bits)")
for p, (fp, got) in enumerate(zip(foot, hw)):
    t, kx, ky = fp
    for c in (0, 1):
        b4 = [v >> 8 * c & 255 for v in t]
        res = {m: R.two_stage(b4, kx, ky, m) for m in ("none", "out", "in", "inout")}
        if len({res[m] for m in res}) > 1 or res["none"] != got >> 16 * c & 0xFFFF:
            d = [R.decode(b) for b in b4]
            top, bot = R.stage_bf11(d[0], d[1], kx), R.stage_bf11(d[2], d[3], kx)
            y = R.stage_bf11(top, bot, ky)
            print(f"({p % 64},{p // 64}) c{c} {b4} kx {kx} ky {ky} | {top:.3e} {bot:.3e} {y:.3e} | "
                  f"{res['none']:04x} {res['out']:04x} {res['in']:04x} {res['inout']:04x} HW {got >> 16 * c & 0xFFFF:04x}")
