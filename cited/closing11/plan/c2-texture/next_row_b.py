"""Not scored: the stage outputs a later hardware row would read to bound the flush threshold.
Corner bytes (00, 10, 01, 11) = (0, 1, 0, 1) at ky = 0 reads the x stage alone (the y stage at k = 0 returns
A); (0, 0, 1, 1) at kx = 0 reads the y stage alone. Output half bits under R10-BF11 (no flush) per weight."""
exec(open("rule_b.py").read())
print("weight k, A=0 B=byte 1 (decoded %.4e, 2^-14 = %.4e): BF11 half bits, value" % (decode(1), TINY))
for k in range(8, 19):
    r = stage_bf11(0.0, decode(1), k)
    print(f"  k {k}: {r:.4e} half {half_rne(r):04x} {'below 2^-14 (flush predicted)' if r < TINY else 'normal'}")
print("byte 2 (decoded %.4e):" % decode(2))
for k in range(4, 12):
    r = stage_bf11(0.0, decode(2), k)
    print(f"  k {k}: {r:.4e} half {half_rne(r):04x} {'below 2^-14' if r < TINY else 'normal'}")
