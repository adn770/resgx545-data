# r19-k0 fold notes (post hoc, outside the freeze)

- Attempt 20261114-223342 stopped at k0-a0 (rc 24, no fault): its param dump's plain sha256
  2643d77d... is not r10-dpm's e366ead7.... The dumps differ in 4 dwords only, 0x12de30 to
  0x12de3c (page 301): 0xc0000000 in both kept B60AB0B4 runs, 0 here, the tail of a run of
  terminate words after a stream's last entry; the tadata dump, the image counts and the page
  steps equal, and the fork's knob-0 path is unchanged (2a650d74..456404fcffe5).
- Lead's decision (2026-11-14): keep module E0CC4027 and build r19-k0b with k0-a0's param control
  masked (each stream's repeated terminate words). r19-k0's other rows never ran.
- lead/build_tool18b.sh is round 18's recipe byte for byte; r19-k0b publishes the same file.
