# r9-x fold notes (builder, for the fold after the run)

- Records E975 (t3, Q078), E976 (srgb, Q282), E977 (zls, Q242/Q243), E978 (zst, Q120),
  E979 (far, Q199/Q261). Draft each method with `tools/records/new_record.py --session DIR`.
- t3: each held-out row has its bit-14-clear reference (`-ref`, H-TEXMODEL): if a reference
  differs from texmodel, rebuild the rivals from the measured reference before scoring (post hoc,
  stated). The six held-out geometries decide H-UCOL vs H-U01/H-URAW (they tie in range; H-U01 and
  H-URAW split only on b14-u02w16's pixels past the texture). R-U01 was formed post hoc on E566's
  s32x32 (O9-1, E968): b14-u02w16 is its first held-out test. If no rival is exact, table the
  per-pixel offset (kept dword - control dword) per geometry before any refit; a refit is post
  hoc. Bits 11/12: E566 replicates (H-CTL) and E564's an-* replicates; the twiddled reads are a
  reading table (named memory decodes every read).
- srgb: a1/a2/b1/b2 are the fit (each stage alone); fit the stage arithmetic on them, freeze the
  rule by hash in fold/, then score c1/c2 and E723's g-bl-st-b: the in-session split stated as
  such. The eq control's failure means the decode or a lerp identity is not as assumed: no row
  is read then.
- zls: Q242 rules are applied to the paired format-0 dump; a mismatch confined to dwords past the
  target (80 x 40 edge tiles) reads the band, not the rule. Q243's drawn counts: a count other than
  0 or 2048 is a reading (partial pass), not a model.
- zst: formats 3, 5, 6 are a reading table (dumps kept: depth.1.bin, stencil-store.1.bin); Q121
  needs `tri --isp2` (a userspace change, test first) in a later round.
- far: E684's band (1e-3 pixel) is undetermined in every rival; H-WRAP can tie H-CULL on far-x25n
  (both draw nothing). H-SAT ties H-EXACT on rows within 2^23 pixels by design.
- sgx-pipe/sgx-sim updates (sim in sync): only from the held models; refuse what stayed unmeasured.
