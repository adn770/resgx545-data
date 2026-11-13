"""c7_rule.py: FROZEN rules of check c7-q120 (Q120, formats 6 and 7 compressed layouts).
Rules are written from: z2y-f6 block 0 (FIT set for RULE_F6C) and z2x-f7-sa5 (FIT set for
RULE_F7K), both in render/closing-r10-zls out/20261113-102039/zst2 (E986).

RULE_F6C (format 6, a tile row whose 32 reference pixels are all equal, 'constant rows')
  A tile block (512 dwords, E985's block order) is cut in 4 groups of 48 bytes (12 dwords) =
  4 tile rows each; group q holds rows 4q..4q+3 (r = row mod 4), v_r the row's format-0 float
  (reference dword, as is, sign NOT set).  Predicted bytes of group q, offset 48 q:
    all bytes 0 unless written below, written in this order:
    1. record of row r at byte p = 6 + {0: 0, 1: 20, 2: 8, 3: 28}[r]:
         0x9e, v_r little endian (4 bytes), 0x00
    2. tail at bytes 46 and 47: 0x9e, low byte of v_2
    3. mask words (dword 0x3f000000, i.e. bytes 00 00 00 3f) at dword indices
         {1: 0, 0: 3, 2: 5, 3: 10}[r]  (row r -> dword index in the group)
  Applicable to group q only if rows 4q..4q+3 are all constant and every group before q in the
  block is applicable too (the stream is a fixed 48 bytes a group only then).  Pass criterion:
  all 12 dwords of the group equal the prediction.  Dwords after the last applicable group are
  not predicted (counted undecoded).
RIVAL_F6RAW (E985's format 6 raw layout: dword 32 r + x = v with the sign set): predicts the
  whole 512 dwords of the block; it is scored on the same groups (expected to fail).

RULE_F7K (format 7, constant stencil fill S, an x ramp, 64 x 32): in each tile block (256
  dwords) the first 12 dwords (48 bytes) are the bytes TEMPLATE (A = 0x3f, B = 0x1f, S = the
  fill byte; template read off z2x-f7-sa5 block 0 only, byte 0 first); no other dword of the
  buffer changes.  Pass: all 48 changed dwords equal the prediction and the 4 x 12 positions
  are the only changed dwords.
RIVAL_F7K (the fill byte replaced by a constant 0xa5, i.e. no dependence on S): same template
  with S = 0xa5 whatever the fill.
"""
import struct

SIGN = 0x80000000
REC = {0: 6, 1: 26, 2: 14, 3: 34}
MASKDW = {1: 0, 0: 3, 2: 5, 3: 10}


def f6c_group(v):
    """v: the 4 row floats (ints); returns the 12 dwords predicted"""
    b = bytearray(48)
    for r in range(4):
        p = REC[r]
        b[p:p + 6] = bytes([0x9e]) + struct.pack("<I", v[r]) + b"\x00"
    b[46] = 0x9e
    b[47] = v[2] & 0xff
    for r in range(4):
        i = 4 * MASKDW[r]
        b[i:i + 4] = struct.pack("<I", 0x3f000000)
    return list(struct.unpack("<12I", bytes(b)))


TEMPLATE = "ASBASBASBASBASBABASBASBASBASBASBSBASBASBASBASBAS"


def f7k_block(s, rival=False):
    m = {"A": 0x3f, "B": 0x1f, "S": 0xa5 if rival else s}
    b = bytes(m[c] for c in TEMPLATE)
    return list(struct.unpack("<12I", b))
