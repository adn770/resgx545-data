# G5 post-run fix (2026-11-12)

The frozen `g5_blocks.as-run.py` (sha256 in `FREEZE-g5.sha256`) tested H-CUM's part (a) by
comparing its b_k with the objects whose entries carry the base dword in more than half of all
regions with a stream. At N 4 (2450 regions, about 2300 carrying each base) that reads "yes"; at
N 8 the dump has 4689 regions with a stream and each base object is carried by 2281 to 4131 of
them, so the test kept only objects 65 and 87 and read "NO" although the list of objects with a
base dword, printed on the line above it, equals H-CUM's b_k (17 of 17). The threshold was a
slip of the builder: the claim (a) tests is which objects carry a base dword, not how many
regions do.

`g5_blocks.py` compares b_k with every object that carries a base dword. The fixed output is
`g5_blocks.out`, the as-run output `g5_blocks.as-run.out`; only the two (a) lines change, in
wording at both N and in the reading at N 8 ("NO" to "yes"). The fix was made after the
as-run output was read, so (a) at N 8 is post hoc. Part (b), the steps, is unchanged (1 of 17
at N 8, 9 of 12 at N 4), and H-CUM stays not frozen.
