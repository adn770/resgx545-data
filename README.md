# resgx545-data

The measured data behind [resgx545](https://github.com/adn770/resgx545): every readback of
the probe campaign on a PowerVR SGX545 (Intel Cedarview), as the campaign runner wrote it.

## Layout

One directory per probe table, `<unit>/<feature>/`, the same unit and feature as the table
`probes/<unit>/<feature>.toml` in resgx545 that made it:

- `<unit>/<feature>/<probe>/raw.txt`: the probe host's output;
- `<unit>/<feature>/<probe>/report.txt`: its readout per case;
- `<unit>/<feature>/<probe>/bins/`: the assembled programs it ran;
- `<unit>/<feature>/env.toml`: the environment (kernel, firmware, tools) and the baseline
  before and after every probe.

Each table is one dataset. Its manifest, `datasets/<unit>-<feature>.toml` in resgx545, pins
the files by hash and names this repository (`repo = "data"`). resgx545's tests check the
manifests against a checkout of this repository placed beside it, or named by
`RESGX545_DATA`.

Data that derives from the closed driver (its captures, its firmware) is not here.

## Licence

MIT (LICENSE).
