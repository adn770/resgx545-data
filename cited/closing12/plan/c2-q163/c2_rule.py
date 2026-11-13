"""C2 / Q163 frozen rule: E700's VDM counter on the 11.31 state sweeps (vdm/state-units).

Held out: all 133 jobs of /Users/jtorra/src/resgx545-data/vdm/state-units (scripts vdm-state-units 36,
vdm-state-risky 78, vdm-state-grid 19). Fit rows: none (the counter was fitted on E413 and tested on
E700's 52 jobs; neither is in this data).

RUN ORDER: cases.tsv row order inside each script (= marker order in kernel.log); the scripts run
units, risky, grid in this order (output.txt clocks 23:05, 23:25, 23:35). Other scripts ran between
(not kept); every script's exit trap does a GPU reset, so c = 0 at the start of each script (assumption).

STATE (teacher forced, from the observed outcome of every job, as E700's scoring did):
  hung job (a 'hung, recovering' line in the job's kernel.log section)  -> c = 0
  any 'SGX reset:' line in the job's section (reset event)               -> c = 0 after the job
  completed job (rc 0, no hung line)                                     -> c = f(c, adds) per model
  rc not in (0, 3) and no hung line                                      -> void, c unchanged, not scored

JOB INPUT: v1, v2 = bits 11:9 of word 1 (block 1) and word 9 (block 2); default 2 (plain). For
'--vdm W^=mask' v = (2 ^ (mask >> 9)) & 7 (base v = 2, as E700/E545); for '--vdm W=value'
v = (value >> 9) & 7. A job with no --vdm has v1 = v2 = 2.

EXCLUDED (not scored; the hang has a known word cause, E545): word has bits 15:13 = 0, 5, 6, 7
(base bits 15:13 = 1, new = 1 ^ ((mask >> 13) & 7), for '^=' forms; for '=' forms (value>>13)&7),
bit 17 flipped (mask & 0x20000 for '^=' forms), and the closed forms 0x0800e105 / 0x08002505.
Excluded rows still update c from their observed outcome.

COUNTER (E700): g(v) = v - 2 for v >= 2. add = g(v1) + g(v2) (+ v < 2 term per model). Hang iff
c + add > 8. A completed job sets c = c + add (clamped at 0 below, M1..M3).
  M0: v < 2 adds 0.
  M1: v = 1 adds -1, v = 0 adds 0, c not below 0.
  M2: M1; a job with a v = 0 block that completes sets c = 0; block-2 v = 1 hangs iff c = 0.
  M3: M1; block-2 v = 1 hangs iff c = 0 (E701's post hoc variant, formed before this data).
RIVALS: NULL (stateless: hang iff g(v1)+g(v2) >= 9, v<2 adds 0, E700's T' = 9); NEVER (never hang);
V16 (hang iff v1 or v2 in {1, 6}, 11.31's own reading).

SCORED SETS: S = non-excluded jobs with a block v != 2 (v in 0..7). S37 = those with v in 3..7;
SLO = v in {0, 1}. TRIV = non-excluded jobs with v1 = v2 = 2 (all counter models predict
complete); a TRIV hang is a counter miss.

PASS CRITERION, per counter variant X (M0, M1, M2, M3):
  HOLDS    : 0 misses on S37, 0 misses on TRIV, and X right on more jobs of S than NEVER and V16.
  PARTLY   : 1 or 2 misses on S37 + TRIV.
  REFUTED  : >= 3 misses on S37 + TRIV for X.
The counter's verdict is the best variant's; v < 2 clause verdict: X right on all SLO jobs.
A miss = a v in 3..7 job that hangs with c + add <= 8, or completes with c + add > 8, with no
reset logged between (E700's refutation clause), or a TRIV job that hangs.
"""
import re

LIMIT = 8
CLOSED = {0x0800e105, 0x08002505}


def parse_vdm(args):
    """-> dict word -> (op, value) from the '--vdm W^=mask' / '--vdm W=value' arguments."""
    out = {}
    toks = args.split()
    for i, t in enumerate(toks):
        if t == "--vdm" and i + 1 < len(toks):
            m = re.fullmatch(r"(\d+)(\^?)=(0x[0-9a-fA-F]+|\d+)", toks[i + 1])
            out[int(m.group(1))] = ("x" if m.group(2) else "s", int(m.group(3), 0))
    return out


def job_input(args):
    """-> (v1, v2, excluded_reason or None)."""
    w = parse_vdm(args)
    v = {}
    why = None
    for word, blk in ((1, 1), (9, 2)):
        v[blk] = 2
        if word not in w:
            continue
        op, val = w[word]
        if op == "x":
            v[blk] = (2 ^ (val >> 9)) & 7
            b1513 = 1 ^ ((val >> 13) & 7)
            if b1513 in (0, 5, 6, 7):
                why = "bits15:13=%d" % b1513
            if val & 0x20000:
                why = "bit17"
        else:
            v[blk] = (val >> 9) & 7
            if val in CLOSED:
                why = "closed-form"
            elif ((val >> 13) & 7) in (0, 5, 6, 7):
                why = "bits15:13=%d" % ((val >> 13) & 7)
    return v[1], v[2], why


def g(vv, model):
    if vv >= 2:
        return vv - 2
    if model == "M0":
        return 0
    return -1 if vv == 1 else 0


def predict(model, c, v1, v2):
    """-> (hang_predicted, c_after_if_complete)."""
    if model in ("NEVER",):
        return False, c
    if model == "NULL":
        s = max(g(v1, "M0"), 0) + max(g(v2, "M0"), 0)
        return s >= 9, c
    if model == "V16":
        return (v1 in (1, 6) or v2 in (1, 6)), c
    add = g(v1, model) + g(v2, model)
    hang = c + add > LIMIT
    if model in ("M2", "M3") and v2 == 1 and c == 0:
        hang = True
    c2 = c + add
    if model != "M0":
        c2 = max(c2, 0)
    if model == "M2" and (v1 == 0 or v2 == 0):
        c2 = 0
    return hang, c2


def verdict(misses_s37_triv, right_s, right_never, right_v16, nmodel_ok_slo=None):
    if misses_s37_triv == 0 and right_s > right_never and right_s > right_v16:
        return "HOLDS"
    if misses_s37_triv <= 2:
        return "PARTLY"
    return "REFUTED"
