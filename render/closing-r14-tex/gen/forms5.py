# SPDX-License-Identifier: MIT
"""forms5.py: the uv5 coordinate forms of addr5's corner rows (gen/addr5.py), standard library
only, so score/score.py reads them without the generator's pins: s = ks x + cs (x 0 to 63),
t = kt y + ct (y 0 to 31), at the texel centres; every region holds pixels."""
FORMS = {(8, 8): ((1, -28), (1, -12)),
         (32, 32): ((1, -16), (2, -16)),
         (128, 32): ((4, -64), (2, -16)),
         (32, 128): ((1, -16), (8, -64)),
         (128, 128): ((4, -64), (8, -64)),
         (256, 32): ((8, -128), (2, -16))}


def install(uv5_form):
    """Add the forms to addr.py's UV5_FORM (once)."""
    for k, v in FORMS.items():
        uv5_form.setdefault(k, v)
