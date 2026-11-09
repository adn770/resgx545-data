#!/usr/bin/env python3
"""p1141/ta gen_p1141ta.py: writes the run tables, programs, declared sets and frozen predictions.

Outputs (all under p1141/ta, scratch):
  run/tables/*.txt       one table a script, run_table_ta.sh format  name|set|risk|P|knobs|rt|args
  programs/*.s, stage-bins/*.bin   our own USSE programs (usse-asm of ~/src/resgx545, read only)
  declared.tsv           case, table, set (fit / heldout / control / explore), risk
  predictions-declared.tsv  case, quantity, value, model   (value ? = exploration: cannot fail)
Sets: 'heldout' = outcome never used to form the model it tests; 'fit' = a case already in a record or
in the data the model was formed on (repeated to check determinism); 'control' = must reproduce; 'explore' = ?.
Everything is deterministic (seed 1141); rerunning rewrites identical files.
"""
import pathlib, random, subprocess, sys
P = pathlib.Path(__file__).resolve().parent.parent
ASM = pathlib.Path.home() / 'src/resgx545/tools/usse-asm/usse-asm'
TAB = P / 'run/tables'; TAB.mkdir(parents=True, exist_ok=True)
(P / 'programs').mkdir(exist_ok=True); (P / 'stage-bins').mkdir(exist_ok=True)
decl, pred = [], []
def D(case, table, st, risk): decl.append((case, table, st, risk))
def PR(case, q, v, model): pred.append((case, q, v, model))
def write(name, header, rows):
    (TAB / f'{name}.txt').write_text(header + '\n'.join('|'.join(r) for r in rows) + '\n')

# ---------------------------------------------------------------- 1. VDM counter series (Q163, Q102)
BASE = ('probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 '
        '--obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel "$S/p1131-green__0.bin"')
def vargs(v1, v2):
    a = BASE
    if v1 != 2: a += f' --vdm 1^=0x{(2 ^ v1) << 9:08x}'
    if v2 != 2: a += f' --vdm 9^=0x{(2 ^ v2) << 9:08x}'
    return a + ' "$S/p1131-blue__0.bin"'
def model(series, m):
    """m in M0 (v<2 adds 0), M1 (v=1 adds -1, clamp 0), M2 (M1, v=0 sets c=0, block-2 v=1 hangs iff c==0)."""
    c, out = 0, []
    for v1, v2 in series:
        add, hang_now = 0, False
        for blk, v in ((1, v1), (2, v2)):
            if v >= 2: add += v - 2
            elif v == 1 and m != 'M0':
                if m == 'M2' and blk == 2 and c == 0: hang_now = True
                add -= 1
            elif v == 0 and m == 'M2': c = 0
        h = hang_now or (c + add > 8)
        out.append('H' if h else 'ok')
        c = 0 if h else max(c + add, 0)
    return out
rng = random.Random(1141)
SER = {
 'A1-v4x12': ([(4, 2)] * 12, 'heldout'), 'A2-v3x12': ([(3, 2)] * 12, 'heldout'),
 'A3-v7x6': ([(7, 2)] * 6, 'heldout'),
 'A4-rand16': ([(rng.choice([2, 2, 3, 4, 5, 6, 7]), rng.choice([2, 2, 3, 4, 5, 6, 7])) for _ in range(16)], 'heldout'),
 'A5-v5v3x6': ([(5, 3)] * 6, 'heldout'),
 'B1-b2v1x4': ([(2, 1)] * 4, 'explore'), 'B2-v1-at-8': ([(6, 2), (6, 2), (2, 1), (3, 2), (3, 2)], 'explore'),
 'B3-v0-at-8': ([(6, 2), (6, 2), (2, 0), (3, 2), (3, 2)], 'explore'),
 'B4-b1v1-at-4': ([(6, 2), (1, 2), (1, 2), (1, 2), (6, 2), (6, 2)], 'explore'),
 'B5-b1v1-at-0': ([(1, 2)] * 3, 'explore'), 'B6-b1v0-at-8': ([(6, 2), (6, 2), (0, 2), (3, 2), (3, 2)], 'explore'),
}
for sname, (ser, st) in SER.items():
    risk_tab = 'vdm-series-a' if sname[0] == 'A' else 'vdm-series-b'
    rows = []
    for i, (v1, v2) in enumerate(ser):
        n = f'vs-{sname}-{i:02d}'
        rows.append((n, st, 'risky' if sname[0] == 'B' else 'safe', '-', '' if i == 0 else 'noreset', '-', vargs(v1, v2)))
        D(n, risk_tab, st, rows[-1][2])
        for m in ('M0', 'M1', 'M2'):
            PR(n, 'job', model(ser, m)[i], m)
    SER[sname] = (ser, st, rows, risk_tab)
for t in ('vdm-series-a', 'vdm-series-b'):
    rows = [r for s in SER.values() if s[3] == t for r in s[2]]
    write(t, '#need $S/p1131-green__0.bin $S/p1131-blue__0.bin\n# VDM_STATE1 bits 11:9 counter series (Q163, Q102); '
             'a job after a hang starts from c=0 (the failure handler resets); the first job of a series resets\n', rows)

# ---------------------------------------------------------------- 2. capacity: attribute rows axis (Q094)
def cap(n, f, a):
    x = f'--vdm 6^=0x{(15 ^ f) << 28:08x} ' if f != 15 else ''
    ar = f'--vdm 7^=0x{(a << 7) ^ 0x80:08x} ' if a != 1 else ''
    return (f'probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords {n} {x}{ar}'
            f'--dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c{n}.bin" "$S/p1131-fmt-{n}__0.bin"')
CAPS = []   # (name, set, n, f, a, R, V)
for a in (1, 5, 7, 9, 10, 12, 16, 8):   # R3 V11 = 33 rows; a = 8 is the anomaly case of vtask5 (1 vertex lost), a = 1 the base
    CAPS.append((f'cap-n8-f10-a{a}', 'fit' if a in (1, 8) else 'heldout', 8, 10, a, 3, 11))
for a in (9, 12, 16, 24): CAPS.append((f'cap-n11-f7-a{a}', 'heldout', 11, 7, a, 4, 8))
for a in (9, 16, 32): CAPS.append((f'cap-n2-f15-a{a}', 'heldout', 2, 15, a, 2, 16))
CAPS.append(('cap-n8-f10-a8-r3', 'control', 8, 10, 8, 3, 11))
rows = []
seen = set()
for name, st, n, f, a, R, V in CAPS:
    nm = name
    while nm in seen: nm += 'x'
    seen.add(nm)
    rows.append((nm, st, 'safe', '-', '', '-', cap(n, f, a)))
    D(nm, 'capacity', st, 'safe')
    # MA: rows counted R*V only, C in 33..35: no vertex lost at R*V <= 33 whatever the attribute rows.
    PR(nm, 'lost>0', 'no', 'MA-attr-free')
    # MB: one attribute row budget unit per 8 rows (floor(a/8)) added to R*V, C = 33.
    PR(nm, 'lost>0', 'yes' if R * V + a // 8 > 33 else 'no', 'MB-a8')
write('capacity', '#need $S/pix_pa0.bin $S/p1131-fmt-8__0.bin $S/p1131-fmt-11__0.bin $S/p1131-fmt-2__0.bin $S/vtx_c8.bin $S/vtx_c11.bin $S/vtx_c2.bin\n'
      '# Q094: R*V 32 and 33 with attribute rows (VDM word 7 bits 14:7) beyond the 8 already run. Safe: no hang expected.\n', rows)
# Rows are VDM word 7 bits 27:24 (the tool sets (4+N+3)/4 there, tri_probe.c:381); the vertex size field (OUTSEL
# 19:16) caps N at 11, but the rows can be forced with an existing --vdm 7^= xor: R*V = 35 and 36 become reachable
# (34 does not: 2 x 17, 17 x 2). Mnat: the allocation follows the natural rows (forced rows change nothing).
def capr(n, f, R):
    rn = (4 + n + 3) // 4
    x = f'--vdm 6^=0x{(15 ^ f) << 28:08x} ' if f != 15 else ''
    r = f'--vdm 7^=0x{(rn ^ R) << 24:08x} ' if R != rn else ''
    return (f'probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords {n} {x}{r}'
            f'--dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c{n}.bin" "$S/p1131-fmt-{n}__0.bin"')
rows = []
for name, st, n, f, R in (('capr-n9-f7-R4', 'control', 9, 7, 4), ('capr-n8-f7-R4', 'heldout', 8, 7, 4), ('capr-n8-f10-R3', 'control', 8, 10, 3),
                          ('capr-n11-f5-R5', 'heldout', 11, 5, 5), ('capr-n2-f4-R7', 'heldout', 2, 4, 7), ('capr-n11-f6-R5', 'heldout', 11, 6, 5),
                          ('capr-n8-f6-R5', 'heldout', 8, 6, 5), ('capr-n2-f4-R7-r2', 'control', 2, 4, 7), ('capr-n11-f5-R6', 'heldout', 11, 5, 6),
                          ('capr-n11-f7-R5', 'heldout', 11, 7, 5)):
    V = f + 1; Rn = (4 + n + 3) // 4
    rows.append((name, st, 'risky', '-', '', '-', capr(n, f, R))); D(name, 'capacity-rows', st, 'risky')
    for mdl, c in (('C33', 33), ('C34', 34), ('C35', 35)): PR(name, 'lost>0', 'yes' if R * V > c else 'no', mdl)
    PR(name, 'lost>0', 'yes' if Rn * V > 33 else 'no', 'Mnat-natural-rows')
write('capacity-rows', '#need $S/pix_pa0.bin $S/p1131-fmt-8__0.bin $S/p1131-fmt-9__0.bin $S/p1131-fmt-11__0.bin $S/p1131-fmt-2__0.bin $S/vtx_c8.bin $S/vtx_c9.bin $S/vtx_c11.bin $S/vtx_c2.bin\n'
      '# Q094: rows forced in VDM word 7 (existing --vdm); R*V 30, 35, 36, 40; controls: forced = natural, N=8 R=4 against N=9 R=4\n', rows)

# ---------------------------------------------------------------- 3. DPM (Q210, Q211, Q103)
RT = '0x0624-0x0628,0x0654-0x0660,0x0700-0x0710,0x0720-0x0724,0x0748'
G = '--dump-render "$W/dump"'
def wide(v): return f'probe --tri pixel --width 4096 --height 4096 --vertices {v} {G}  "$S39/p1139-green.bin"'
rows = []
for v, p, st in ((1500, '0x422', 'fit'), (1500, '0x424', 'heldout'), (1500, '0x430', 'heldout'), (1500, '0x440', 'heldout'),
                 (1500, '0x442', 'heldout'), (1500, '0x460', 'heldout'), (1500, '0x500', 'heldout'), (1500, '0x422', 'control'),
                 (1400, '0x422', 'heldout'), (1300, '0x422', 'heldout')):
    n = f'oom-{v}-{p}' + ('-r2' if st == 'control' else '')
    rows.append((n, st, 'safe', p, '', RT, wide(v))); D(n, 'dpm-oom', st, 'safe')
    thr0 = 0x400
    PR(n, 'raised', 'no', 'HA-dw36-guard')                               # dw36 != 0 blocks the raise at any P
    PR(n, 'raised', 'yes' if int(p, 16) - 0x22 >= thr0 + 0x20 else 'no', 'HP-pages')   # raise needs pages for thr0 + 0x20
    PR(n, 'raised', '?', 'H2-second-crossing')                            # exception of the rule: not predicted
write('dpm-oom', '#need $S39/p1139-green.bin\n# Q210: wd-glist-1500 (110 of 111, the miss) with the 0x0624 timeline (regtimeline); P over the '
      'raise boundary 0x442 = 0x400 + 0x20 + 0x22\n', rows)
def tri(n, mv, extra=''):
    mv = ' '.join(f'--move {i}:{x},{y}' for i, (x, y) in mv)
    return (f'tri --width 1024 --height 768 -n {n} --keep-overflow --wait-ms 20000 --dump-render "$W/dump" --dump-each --words "$W/words" '
            f'--regs 0x0700-0x074c {mv}').strip()
rows = []
for p in ('0x28', '0x30', '0x422'):
    cfg = [('n1', 1, []), ('stack4', 4, []), ('disj4', 4, [(2, (192, 0)), (3, (384, 0)), (4, (576, 0))])]
    for nm, n, mv in cfg:
        c = f'stk-{nm}-{p}'
        rows.append((c, 'heldout', 'safe', p, '', '0x0624-0x0628,0x0654-0x0660,0x0720-0x0724', tri(n, mv)))
        D(c, 'dpm-stack', 'heldout', 'safe')
        PR(c, 'pages_disj_gt_stack', 'yes' if nm == 'disj4' and p == '0x422' else '?', 'HG-geometry')
        PR(c, 'pages_disj_eq_stack', 'yes' if nm == 'disj4' and p == '0x422' else '?', 'HT-touch-per-run')
rows.append(('stk-stack4-0x28-r2', 'control', 'safe', '0x28', '', '0x0624-0x0628,0x0654-0x0660,0x0720-0x0724', tri(4, []))); D('stk-stack4-0x28-r2', 'dpm-stack', 'control', 'safe')
write('dpm-stack', '# Q211: 4 triangles stacked against 4 apart (move 192 px steps), P 0x28 / 0x30 (overflow) and 0x422 (none). '
      'recompute checks the geometry (distinct regions) so a case whose triangles did not separate is flagged\n', rows)
rows = []
for nm, p, kn in (('hang-300-0x40-nohold', '0x40', ''), ('hang-300-0x40-nohold-r2', '0x40', ''), ('hang-300-0x40-hold', '0x40', 'hold'),
                  ('hang-300-0x40-hold-r2', '0x40', 'hold'), ('hang-450-0x100-hold', '0x100', 'hold'), ('hang-450-0x100-nohold', '0x100', '')):
    v = 300 if '300' in nm else 450
    rows.append((nm, 'heldout' if 'r2' not in nm else 'control', 'risky', p, kn, RT, wide(v)))
    D(nm, 'dpm-hang', rows[-1][1], 'risky')
    PR(nm, 'hung_line', 'yes' if v == 300 else '?', 'HL-pr-count')     # the two logged jobs had 47 and 92 partial renders
    PR(nm, 'hung_line', 'yes' if 'nohold' not in nm and v == 300 else ('no' if 'nohold' in nm and v == 300 else '?'), 'HH-hold-only')
write('dpm-hang', '#need $S39/p1139-green.bin\n# Q103: hold_recovery off against on, same jobs; a long job timeout needs a kernel constant (not here)\n', rows)

# ---------------------------------------------------------------- 4. EOT store forms (Q183) and per-tile globals (Q053)
def asm(name, text):
    (P / 'programs' / f'{name}.s').write_text(text)
    r = subprocess.run([str(ASM), '-o', str(P / 'stage-bins' / f'{name}.bin'), '-'], input=text, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
def eot(reg, skip, pos, m):
    mv = f'mov.skipinv {reg}, #0x{0x5CAF0000 + 16 * m:08X}' if skip else f'mov {reg}, #0x{0x5CAF0000 + 16 * m:08X}'
    st = [mv, f'stad [{reg},+#0], r2', 'idf drc0, bif', 'wdf drc0']
    body = ['phas #0, #0, pixel, end, parallel'] + ['mov.skipinv r0, #0x00000000'] * 4
    if pos == 'pre': body += st + ['emitpix1.freep #0 /* incp */, r0, r1']
    else: body += ['emitpix1.freep #0 /* incp */, r0, r1'] + st
    body += ['emitpix2.end.freep #0 /* incp */, r2, r3, r0, #0x00000000']
    return '\n'.join(body) + '\n'
E = '--tri pixel --pixels --width 64 --height 64 --slot pixpds="$S34/pds_iter_xy.bin:12" --slot vtxuse="$S34/vtx_coords.bin" --vtx-coords 2'
rows, m = [], 0
cells = [(s, p, t) for t in (32, 8) for p in ('mid', 'pre') for s in (True, False)]
for skip, pos, temps in cells:
    m += 1
    nm = f'eots-{"skip" if skip else "plain"}-{pos}-t{temps}'
    asm(nm, eot('r1', skip, pos, m))
    st = 'control' if (skip and pos == 'mid' and temps == 32) else 'heldout'
    rows.append((nm, st, 'risky', '-', '', '-', f'probe --temps {temps} {E} --slot eot="$S41/{nm}.bin" "$S34/pix_pa0.bin"'))
    D(nm, 'eot-store', st, 'risky')
    PR(nm, 'fault', 'yes' if skip else 'no', 'HS-skipinv')
    PR(nm, 'fault', 'yes' if pos == 'mid' else 'no', 'HP-position')
    PR(nm, 'fault', 'yes' if temps == 32 else 'no', 'HT-temps')
m += 1
asm('eots-e130-r4', eot('r4', False, 'pre', m))
rows.append(('eots-e130-r4-t8', 'control', 'risky', '-', '', '-', f'probe --temps 8 {E} --slot eot="$S41/eots-e130-r4.bin" "$S34/pix_pa0.bin"'))
D('eots-e130-r4-t8', 'eot-store', 'control', 'risky')
for mdl in ('HS-skipinv', 'HP-position', 'HT-temps'): PR('eots-e130-r4-t8', 'fault', 'no', mdl)
rows.append(('eots-plain-eot-t8', 'control', 'risky', '-', '', '-', f'probe --temps 8 {E} "$S34/pix_pa0.bin"'))
D('eots-plain-eot-t8', 'eot-store', 'control', 'risky')
for mdl in ('HS-skipinv', 'HP-position', 'HT-temps'): PR('eots-plain-eot-t8', 'fault', 'no', mdl)
write('eot-store', '#need ' + ' '.join(f'$S41/{r[0]}.bin' for r in rows[:-2]) + ' $S41/eots-e130-r4.bin $S34/pix_pa0.bin $S34/pds_iter_xy.bin $S34/vtx_coords.bin\n'
      '# Q183: E572 second form against factors (mov flag, position, temps), r1 as the address register; the E130 form (r4) as control\n', rows)
rows = []
for nm, st in (('ctl', 'control'), ('ga', 'heldout'), ('gb', 'heldout'), ('ga-256', 'heldout'), ('gb-256', 'heldout')):
    w = 256 if '256' in nm else 128
    rows.append((f'eotg-{nm}', st, 'safe', '-', '', '-', f'probe --temps 8 --tri pixev:60 --width {w} --height 128 --slot eot="$S41/{"eot_tile" if nm == "ctl" else "eot_tile_" + nm.split("-")[0]}.bin" "$S41/ta-eot-tile-{nm}__0.bin"'))
    D(f'eotg-{nm}', 'eot-globals', st, 'safe')
    PR(f'eotg-{nm}', 'completes', 'yes', 'H-E130-form-completes')
write('eot-globals', '#need $S41/eot_tile.bin $S41/eot_tile_ga.bin $S41/eot_tile_gb.bin $S41/ta-eot-tile-ctl__0.bin $S41/ta-eot-tile-ga__0.bin $S41/ta-eot-tile-gb__0.bin $S41/ta-eot-tile-ga-256__0.bin $S41/ta-eot-tile-gb-256__0.bin\n'
      '# Q053 EOT half: eot_tile.s with g16-g31 and g39-g43 (+ sa0-sa10) as the stored sources; E130 form (stores before the emits)\n', rows)

# ---------------------------------------------------------------- 5. o4 under a g25 test (Q023)
O4 = ('probe --tri pixel --temps 32 --pixels --dump-render "$W/dump" --width 64 --height 64 --vtx-coords 2 --blk 4=0x00030001 '
      '--slot pixpds="$S34/pds_iter_xy.bin:12" --slot vtxuse="$S34/vtx_coords.bin"')
rows, m = [], 200
for k in (0, 1, 2, 3, 'u'):
    for ax in ('x', 'y'):
        m += 1; pa = 'pa0' if ax == 'x' else 'pa1'
        ops = ['phas #0, #0, pixel, end, parallel'] + [f'or.skipinv o{j}, {pa}, #0x{m * 16 + j + 1:x}' for j in range(4)]
        if k == 'u': ops.append(f'or.skipinv o4, {pa}, #0x{m * 16 + 5:x}')
        else: ops += [f'xor.testtaz.chan0 !c0, p1, g25, #{k}', f'p1 or.skipinv o4, {pa}, #0x{m * 16 + 5:x}']
        ops += [f'or.skipinv o{j}, {pa}, #0x{m * 16 + j + 1:x}' for j in (5, 6)] + [f'or.skipinv.end o7, {pa}, #0x{m * 16 + 8:x}']
        nm = f'o4g-{k}-{ax}'
        asm(nm, '\n'.join(ops) + '\n')
        rows.append((nm, 'control' if k == 'u' else 'heldout', 'risky', '-', '', '-', f'{O4} "$S41/{nm}.bin"'))
        D(nm, 'o4-g25', rows[-1][1], 'risky')
        PR(nm, 'tag5_pairs', '>0' if k in (0, 'u') else '0', 'HL0-lane0-only')
        PR(nm, 'tag5_pairs', '>0', 'HAny-lane')
        PR(nm, 'tag5_pairs', '?', 'HNot-lane-id')
(P / 'programs' / 'o4-markers.tsv').write_text(''.join(f'o4g-{k}-{ax}\t{201 + 2 * i + j}\n' for i, k in enumerate((0, 1, 2, 3, 'u')) for j, ax in enumerate(('x', 'y'))))
write('o4-g25', '#need ' + ' '.join(f'$S41/{r[0]}.bin' for r in rows) + ' $S34/pds_iter_xy.bin $S34/vtx_coords.bin\n'
      '# Q023: o4 written only by the lanes whose g25 equals k; tags as E570 (o4 = tag 5); x and y job a case\n', rows)

(P / 'declared.tsv').write_text('case\ttable\tset\trisk\n' + ''.join('\t'.join(r) + '\n' for r in decl))
(P / 'predictions-declared.tsv').write_text('case\tquantity\tvalue\tmodel\n' + ''.join('\t'.join(r) + '\n' for r in pred))
import collections
c = collections.Counter(r[1] for r in decl)
print(dict(c), 'jobs', len(decl), 'risky', sum(1 for r in decl if r[3] == 'risky'))
