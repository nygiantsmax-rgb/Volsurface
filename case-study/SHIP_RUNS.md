# Ship runs (S7 gate)

The rule for shipping: run the app live with the sandbox off, and repeat run, debug, run until a run is clean (run n). Then do one more run (run n+1) on byte-identical files. Push only if both runs are clean and their hash lists match.

Both runs were made on 2026-11-02 from the repo root by the hub (main session). Exit codes were read with PowerShell `$LASTEXITCODE`, not a pipe tail, and every Python call except the mutation proof ran with `-W error`.

## Commands
1. `python -W error <module>.py` for each of: bs_pricing, synthetic, data_io, surface, viz, oracle_check, selftest
2. `python -W error main.py --no-open` (rbf, default synthetic chain)
3. `python -W error main.py --no-open --method spline --x-axis strike`
4. `python selftest.py --mutation-proof` (mutations are applied to temp copies; live hashes are asserted unchanged)

## Results

| Check | run n | run n+1 |
|---|---|---|
| bs_pricing.py | 0 | 0 |
| synthetic.py | 0 | 0 |
| data_io.py | 0 | 0 |
| surface.py | 0 | 0 |
| viz.py | 0 | 0 |
| oracle_check.py | 0 | 0 |
| selftest.py | 0 | 0 |
| main.py (rbf) | 0 | 0 |
| main.py (spline, strike axis) | 0 | 0 |
| selftest.py --mutation-proof | 0 | 0 |
| Mutation baseline | `rc=0 failed=[]` | `rc=0 failed=[]` |
| Mutations | 14 RED as required, 1 INFO | 14 RED as required, 1 INFO |
| Hashes unchanged during run | yes | yes |

The INFO row is `iv_price_only_alone_vega_guard_masks`. On its own it cannot go red, because the R-2 vega guard masks it. The paired mutation `iv_price_only_and_no_vega_guard` does go red.

## Hash lists (sha256 prefix): run n == run n+1 == pushed tree

| File | sha256 |
|---|---|
| bs_pricing.py | 12deadc4 |
| synthetic.py | 1414ff07 |
| data_io.py | 589f5c78 |
| surface.py | be111b3e |
| viz.py | edc7196f |
| main.py | 900228c8 |
| selftest.py | 34fbf338 |
| oracle_check.py | e44e67b8 |
| requirements.txt | 60d0c169 |
| README.md | b0a1b59f |

## Earlier hub runs that led to this gate
- **S1 (baseline after pause):** all green on the pre-R-9 bytes.
- **S4 (after the R-9 fix round):** all green, and the mutation proof was first run by the hub here.
- **S5b (live market smoke run, non-gating):** one live `--ticker` run on a liquid US index ETF exited 0. The README covers it under real-chain diagnostics.

Not covered: a live `--ticker` run inside the gate (it needs network, so it was non-gating), and a `--csv` run against a real user file.
