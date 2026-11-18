# r35-pk fold notes (builder)

- Record: E1146 only. Q302 narrows (R35-4 (a)); edit only Q302's own clauses.
- Built 2026-11-17/18 off resgx545 eea6d2a, data 1f5ebe6b6; kit lint clean.
- Post hoc for the fold (not frozen): the layout of modes 9, 10, 12, 13 (each stored dword names
  its pixel, the ramp's colours being unique), the scratch stride, the per-channel fits the
  scorer prints for modes 3 to 6 ("channels fit: ...") when no single rule holds.
- sgx-pipe: if a rule holds, model modes 4 to 6 (and the RGB565 rounding) with that rule, and
  admit 0x02000040/0x020000c0 in modes 0, 4, 5, 6 if H-1136 holds.
