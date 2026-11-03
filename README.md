# Implied-volatility surface dashboard

Builds a 3D implied-volatility (IV) surface from an option chain and writes one standalone Plotly HTML
file. No server, no Dash, no Streamlit. The default input is a synthetic chain, so it runs with no data
and no API keys.

This README documents what the code does as built and what was verified by reading it and by the run-logs.
Where an earlier design document says something different, the difference is listed under
"Documentation versus behavior". The limitations in section 6 are part of the product, not footnotes.

## 1. Prerequisites

- Python 3.13 (the build was made and run on 3.13). Run every command below from the repository root.
- Packages, from `requirements.txt` (minimum versions): numpy>=2.0, scipy>=1.13, pandas>=2.2, plotly>=6.0.
  The build was run against numpy 2.5.3, scipy 1.18.1, pandas 3.0.6 and plotly 7.1.0.
- Optional, only for `--ticker`: `yfinance` (the build was run against 1.7.0) and network access.
  It is commented out in `requirements.txt`; install it yourself with `python -m pip install yfinance`.
- Credentials: none. Synthetic and `--csv` runs need no network. `--ticker` uses Yahoo data through
  yfinance and needs no key.
- Not needed: pytest, Dash, kaleido. `selftest.py` and `oracle_check.py` use plain asserts.

Install:

```
python -m pip install -r requirements.txt
```

## 2. Run

All commands come from the `main.py` argument parser. All rates and yields are DECIMALS (0.04, not 4).
Percent appears only in console text and in the figure.

1. Default synthetic chain, RBF interpolation, k axis, writes `vol_surface.html`, opens the browser:

   ```
   python main.py
   ```

2. Same, without opening a browser, to a chosen path (missing parent folders are created):

   ```
   python main.py --no-open --out out/vol.html
   ```

3. Spline interpolation and strike axis instead of RBF and k axis:

   ```
   python main.py --no-open --method spline --x-axis strike
   ```

4. Your own chain from CSV (`--spot` is required; `--div` defaults to 0.0; `--rate` defaults to 0.04):

   ```
   python main.py --csv chain.csv --spot 100 --rate 0.04 --div 0.01 --valuation-date 2026-01-02 --no-open
   ```

5. A live chain via yfinance (optional, network, never falls back to synthetic data):

   ```
   python main.py --ticker SYM --no-open
   ```

All options (from `main.py`):

| Option | Default | Meaning |
|---|---|---|
| `--csv PATH` | none | load the chain from CSV. Mutually exclusive with `--ticker` |
| `--ticker SYM` | none | fetch a live chain via yfinance. Mutually exclusive with `--csv` |
| `--spot X` | synthetic default 100.0 | spot price. Required with `--csv`. Ignored with `--ticker` (spot comes from Yahoo) |
| `--rate X` | 0.04 | flat continuous risk-free rate, decimal. Not a market curve |
| `--div X` | 0.0 with `--csv`; 0.015 synthetic | flat continuous dividend yield, decimal. Ignored with `--ticker` (q is chosen by the loader, see 6.3) |
| `--valuation-date YYYY-MM-DD` | none (`--ticker`: today) | needed when the CSV has an `expiry` column |
| `--method rbf\|spline` | rbf | interpolator |
| `--x-axis k\|strike` | k | x axis of the 3D surface and panels |
| `--colorscale Viridis\|Plasma` | Viridis | color scale |
| `--n-T N`, `--n-k N` | 60, 80 | grid points in T and k |
| `--noise-bps X`, `--seed N` | 5.0, 0 | synthetic only; ignored with a printed note for `--csv` and `--ticker` |
| `--export-chain PATH` | none | write the chain used as CSV (re-loadable with `--csv`) |
| `--out PATH` | `vol_surface.html` | output HTML. An existing file is overwritten without a prompt |
| `--offline` | off | embed plotly.js (about 5 MB) so the file opens without internet. Default loads plotly.js from a CDN |
| `--no-open` | off | do not open the browser |

CSV format (from `data_io.py`): UTF-8, comma delimiter, header on file line 1. Header names are case-insensitive.
Required columns: `strike`, `type` (C, P, call or put, any case), `price`, and ONE of `T` (years) or `expiry`
(yyyy-mm-dd). If both exist, `T` is used. `expiry` needs `--valuation-date`, and T is then
(expiry - valuation date) in days / 365. An optional numeric `sigma_true` column is kept. Unknown columns are
dropped. Records must be single-line. Bad rows (non-numeric, strike or price <= 0, T <= 0, bad type, bad date,
and every duplicate strike/T/type after the first) are quarantined and counted, not fatal.

### What a good default run prints

The lines appear in this order. The first line is always the params line.

```
params: S=100.0000 r=0.0400 q=0.0150 (continuous, decimal)
chain: <n> rows generated (rejected: n/a, synthetic)
quotes: <n> OTM rows | status: newton=<a>, brent=<b>, out_of_bounds=<c>, failed=<d>, invalid_input=<e>
usable quotes: <n> | dropped maturities (too few quotes): none
quoted IV range: <lo>% to <hi>%
surface grid: 60 T x 80 k, method=rbf
DIAGNOSTIC ONLY: these checks count violations at grid nodes inside the quoted domain; they do not enforce or guarantee an arbitrage-free surface and say nothing about extrapolated regions.
calendar: <v>/<n> violations (max <x> in total variance, tol 1.0e-06)
butterfly: <v>/<n> violations (max <x> in dC/dK, tol 1.0e-08)
wrote: <absolute path>vol_surface.html (<bytes> bytes)
```

Exit code 0. The status lines above show the form only; `<n>` values depend on the chain. With `--csv` the
`chain:` line reads `<n> data rows in file, <r> rejected, <k> kept`. With `--ticker` the params line is
followed by the note quoted in 6.3.

Exit codes (from `main.py`): 0 success; 2 usage or input error (argparse, load or fetch failure, bad CSV);
3 `build_surface` raised ValueError (too few or unusable quotes); 1 any other exception, including a broken
control total.

## 3. Verify a run

Exit code 0 alone is not enough. Check all of these.

1. The first console line starts with `params: S=` and shows the S, r and q you intended. For `--ticker`,
   read the printed q (see 6.3 and 7, OX-5).
2. The `quotes:` line shows nearly all rows as `newton` or `brent`. Some rows at `out_of_bounds` are expected
   for prices at or below 1e-10 above the no-arbitrage lower bound. For reference only: `selftest.py` builds a
   clean fixture with `generate_chain(noise_bps=0.0, tick=0.0, min_price=0.0)`. The command line cannot produce
   that chain (there is no tick or min-price flag). QA's log recorded status counts newton=124, brent=134,
   out_of_bounds=6 on that fixture, which is 258/264 solved (the 6 are prices from 7.5e-15 to 1.9e-11).
   The default `main.py` chain adds noise, so its counts differ.
3. The `calendar:` and `butterfly:` lines are DIAGNOSTICS (6.2). Read them as violations / checked, with the
   denominator. There is no pass/fail wording and no threshold.
4. Open the HTML. The 3D surface and quote markers should render. Term-structure lines should show gaps
   (not lines) where the strike falls outside the quoted range at that maturity (R13). Smile lines show gaps
   outside the quoted range at that maturity (OX-2). They use the same domain rule as the grid and the term
   structure (D13 closed, R-14 A). At a quoted maturity between grid rows the edge can be off by 0 or 1 node (D14, section 7).
5. The control totals run inside `main.py` as asserts and stop the run with exit 1 if broken. They are
   disabled by `python -O`; do not run with `-O`.

### Test commands

```
python selftest.py
python selftest.py --only NAME
python selftest.py --hashes
python selftest.py --mutation-proof
python selftest.py --report-tick0
python oracle_check.py
python oracle_check.py --src PATH_TO_SOURCES --sections calib,bs,synth,surface
```

- `selftest.py` (QA): runs every content check; one `PASS name` or `FAIL name: ...` line each, then
  `RESULT: all N checks passed ...` and exit 0, or `RESULT: k of N checks FAILED: ...` and exit 1.
  `--only` runs checks whose name contains NAME and exits 1 with `NO CHECKS RAN` if none match. `--hashes`
  prints the sha256 of each source file and `selftest.py`. `--report-tick0` prints report-only noisy-chain
  butterfly and calendar counts at tick 0.01 and tick 0 and asserts nothing.
- `--mutation-proof` copies the sources to a temp folder, injects one defect per copy, and requires the named
  check to turn red. It never writes live files and asserts the live hashes are unchanged. Before trusting
  it, find the line `BASELINE copy: rc=0 failed=[]` in its output and the line
  `live source hashes unchanged after proof: OK`. If the baseline is not green the proof prints
  `BASELINE copy is NOT green -> no RED can be attributed; proof invalid` and counts that as a failure. A mutation
  is credited RED only if its required check is among the failures NEW against the baseline (D12, closed).
  Each mutation prints a line `MUTATION <name> applied xN  rc=...  new_red=[...] -> RED as required`. The hub's last run
  gave 16 RED as required, 1 INFO and 0 NOT CAUGHT.
- `oracle_check.py` (ORACLE): an independent Black-Scholes, IV and surface oracle written from the spec. It
  ends with `--- summary: N checks, K FAIL ---`, one `FAIL id owner=...` line per failure, and exits 0 or 1
  (2 for an unknown `--sections` name). It prints sha256 of the sources before and checks that they are unchanged.
- The counts N are not assurance by themselves. See section 8 for which bytes each tool was last recorded against.

## 4. IV acceptance rule (governing)

The governing rule is rulings R-1 and R-2 from the project corrections log. CONTRACT section 3.4's
price-only text (accept when the price residual is <= 1e-8) is SUPERSEDED. That text accepts any sigma on a
deep out-of-the-money price near 3e-10, which contradicts the contract's own round-trip bar (<= 1e-6), and
section 12 wins the conflict.

As built (`bs_pricing.py`):

- Newton accepts only if the price residual is <= `tol` AND the vol-space step |residual / vega| is <= 1e-9
  (`_SIGMA_RES`), or the residual is exactly zero.
- Newton is used only where vega is finite and >= 1e-8. Rows with smaller or NaN vega go to Brent.
- Brent short-circuits only on an exact zero residual at an endpoint. Bracket is IV_MIN 1e-4 to IV_MAX 5.0.
- Status 2 (`out_of_bounds`) means price <= lower bound + 1e-10 or >= upper bound - 1e-10. A price in
  (1e-10, 1e-8] is solved, not out_of_bounds.
- Status codes: 0 newton, 1 brent, 2 out_of_bounds, 3 failed, 4 invalid_input. IV is finite exactly when
  status is 0 or 1.
- Puts are priced directly (`dK*N(-d2) - dS*N(-d1)`), never from put-call parity. No test enforces this (D9).

## 5. Method in brief

Forward F = S*exp((r-q)T). Log-moneyness k = ln(K/F). Only out-of-the-money quotes are used: puts for K < F
and calls for K >= F. The interpolation is over total variance w = IV^2 * T on a (T, k) grid, not over raw IV.
RBF (thin-plate spline) is the default; `--method spline` is also available. The fixed-strike term structure
uses per-maturity k = ln(K/F(T_i)). Quoted-domain bounds per maturity are `k_lo`, `k_hi` and a boolean
`in_domain` on the surface; the arbitrage diagnostics count only in-domain nodes. Maturities with fewer than 4
usable quotes are dropped and listed.

The quoted domain has one definition (R-14 A): `surface._in_domain`, exposed as `Surface.in_domain_at(T, k)`.
It is True where T lies in [T_grid[0], T_grid[-1]] and k lies between `k_lo` and `k_hi` interpolated linearly in T;
NaN gives False. The grid mask, `smile()`, `term_structure()` and the dashboard's gap mask (`viz._masked_pct`) all
use it. `smile(surface, T)` returns a DataFrame with columns `[k, strike, iv, in_domain]`; `in_domain` is a bool and
is False outside the quoted range at that T (`surface.py` lines 435-459).

## 6. Limitations

6.1 R14 is deferred. The 3D hover and surface corners carry no "extrapolated" tag (ruling R-3; the default in force
is R13 alone). The 3D surface therefore shows extrapolated regions with no label, including the corners. Measured by BUILD-C
(its run-log) on the default noisy chain at T = 1/12: 62 of the 80 k nodes are outside the quoted domain, for both
rbf and spline. REVIEW_B's hand estimate of the quoted k range there is about [-0.107, 0.093] of a grid
about [-0.56, 0.29]. The term-structure and smile lines do show gaps outside the quoted range.

6.2 Arbitrage checks are diagnostics, not guarantees. The calendar check compares total variance between adjacent
maturities. The butterfly check is a convexity proxy on call prices across the strike grid, not Durrleman's
condition. The vertical-spread bound (call price monotone and bounded in strike) is NOT checked. Scope is
in-domain grid nodes only; extrapolated regions are not assessed. The surface is not constrained to be
arbitrage-free.

6.3 A `--ticker` run applies European Black-Scholes to American-style options. The exact note printed by
`main.py` on that path, right after the params line, is:

```
note: European Black-Scholes with flat continuous r and q applied to American-style listed options; OTM-only quotes reduce but do not remove early-exercise and discrete-dividend bias; r is the --rate argument, not a market curve.
```

Also on the ticker path: q is `trailingAnnualDividendYield` if in [0, 0.25], else `dividendYield / 100` if in
[0, 0.25], else 0.0. The chosen q is printed in the params line. `--spot` and `--div` are ignored. The fetch
drops non-positive and duplicate rows silently, so the rejected count prints as `n/a`. Prices are bid/ask mid
where both are positive, else last price.

6.4 Noisy synthetic chain, in-domain butterfly counts (default noise, tick 0.01):
rbf 1/3912 and spline 8/3912. With tick = 0: 0/3871 for both. These are hub-run numbers from QA's
`--report-tick0` (recorded in QA's run-log). REVIEW_B reads this as SUPPORTING tick rounding in the wings as
the cause, but the comparison is not like-for-like: the denominator changed (3912 to 3871) because the tick = 0
chain changes which quotes survive the minimum price and so the domain. Treat tick rounding as supported, not confirmed.
The counts are not asserted by any check.

6.5 Spline, extrapolated nodes. On the clean synthetic chain, the spline method has 56 butterfly violations out of
4680 full-grid nodes (max 1.35e-02), all at extrapolated left-edge nodes (k about -0.56 to -0.54, short T).
They are EXCLUDED from the diagnostic by the in-domain scope (R11), not fixed. The in-domain spline count on that chain is 0/4348.
The grid is not trimmed to hide them.

6.6 Real-chain diagnostic counts (one dated run, not a quality measure). On 2026-11-02, a live `--ticker` smoke run
on a liquid US index ETF (hub-run, not reproducible because live data changes) exited 0 and printed q = 0.0075
(decimal), 953 OTM quotes and a quoted IV range of 12.30% to 121.53%. The in-domain diagnostics on raw mid quotes were:
calendar 575/2831 and butterfly 174/2793 violations / checked (method: the default, rbf; the hub passed no `--method` flag). These are diagnostics on one ticker on one day. They are NOT arbitrage opportunities and NOT evidence that the fit
failed. The likely sources are bid/ask noise in mids, American options priced with a European model
(early-exercise premium, mostly puts), discrete dividends against a continuous q, and stale or non-synchronous
quotes. Do not compare them with the near-zero synthetic counts: the synthetic counts test the code; these describe one day's data.

6.7 Smaller points. Synthetic truth is an SSVI surface; its arbitrage-free claim is a text claim backed by the
hand-checked conditions in the `synthetic.py` docstring, not by the surface diagnostics. Time is ACT/365. The loader accepts only single-line CSV records.

## 7. Open items (REVIEW_B sections 4 to 6, status as of the R-14 simplify delta pass)

| ID | Status | Owner | What is open |
|---|---|---|---|
| OX-1 / R14 | OPEN, deferred (R-3) | BUILD-C | 3D hover and corners not tagged as extrapolated (6.1) |
| OX-3 | OPEN | v2 decision | noisy-chain butterfly counts and the tick-rounding attribution (6.4) |
| OX-4 | ACCEPTED GAP | none | vertical-spread bound unchecked (6.2) |
| OX-5 | observed once, not verified | none in v1 | `dividendYield` unit assumption (percent) is unverified recall. One live run gave q = 0.0075, in range, which cannot settle it; which branch produced q was not reported. A field already in decimal and divided by 100 would also land in range. Read the printed q on every `--ticker` run |
| D9 | OPEN, deferred | QA | no test detects a parity-priced put; R6 rests on the oracle's direct-formula comparison and on reading |
| D12 | CLOSED (R-14 simplify delta, REVIEW_B section 6 point 4) | QA | the mutation proof now aborts as "proof invalid" on a non-green baseline and credits RED only from failures new against the baseline (`selftest.py` lines 1383-1386 and 1407-1409) |
| D13 | CLOSED (R-14 A, REVIEW_B section 6 point 1) | BUILD-B | one domain definition: `surface._in_domain`, exposed as `Surface.in_domain_at`. The grid mask, `smile()` and `term_structure()` all call it, so the smile mask no longer borrows the nearest grid row. Residual: D14 |
| D14 | OPEN, MINOR | BUILD-B if adopted | at a quoted maturity that lies between grid rows, the smile's domain edge is interpolated from the grid-row edges, not taken from the slice's own quoted extent. It can differ by 0 or 1 node per edge (`surface.py` lines 94-95 and 136). Hub measurement over 32 quoted-maturity slices (default and clean chains, rbf and spline): the forbidden direction (an extrapolated point drawn as data) occurred 0 times; only the conservative direction (up to 2 in-quote points hidden) occurred. Proposed fix: pass the quoted maturities and their edges to `_in_domain` |
| D15 | OPEN, MINOR | QA | the `c06_in_domain_single_definition` off-grid assertion checks conformance to R-14 (grid-sampled edges), not to the REVIEW_A R9 text, although its comment and messages say "R9 text" (`selftest.py` lines 1026-1043). Fix: relabel it as R-14 conformance |
| D7 test half | OPEN | QA | the params line is printed first (code closed), but no selftest asserts that ordering |
| D2, D8 | not re-read in the delta pass | BUILD-B | comment-only fixes were reported by the hub; REVIEW_B did not claim them closed |

OX-2 (smile gaps) and D1, D3 to D6, D10 are recorded CLOSED in REVIEW_B section 5. D4 was closed on the condition that D12 closed; REVIEW_B section 6 records D12 closed, so D4 is CLOSED unconditionally. D11 needed no fix.

## 8. Documentation versus behavior (findings)

- CONTRACT 3.4 (price-only acceptance) is not what is built. The rulings R-1 and R-2 govern (section 4). CONTRACT.md was
  deliberately not edited, so any copy of it is stale against R-1 to R-9.
- Oracle result, as of the R-14 simplify round. The hub's S7 gate ran `oracle_check.py` on the final tree and recorded
  108 checks and 0 FAIL, and `selftest.py` at 40 of 40 (`RESULT: all 40 checks passed ...`; 40 is the count of
  `@check` functions in `selftest.py`). The README's author could not run commands and did not observe these runs;
  the 108 comes from the hub's gate record, not from this author. The earlier ship-state run (commit dcf5428) recorded
  a different byte set; those hashes are superseded. Re-run `python oracle_check.py` yourself after any source change
  and read the line `--- summary: N checks, K FAIL ---`.
- Source hashes recorded by the hub S7 gate (sha256 prefixes, identical on run n and run n+1): bs_pricing 45346d20,
  synthetic 1414ff07, data_io 8f946e4a, surface 1a76c666, viz 05a69087, main c6dbc436, requirements 60d0c169,
  selftest 64c82b3d, oracle_check e44e67b8. Run `python selftest.py --hashes` and compare. A difference means the
  file changed after those runs. The author did not compute these hashes.
- Mutation proof, same gate and bytes: exit 0, it printed `BASELINE copy: rc=0 failed=[]`, 16 mutations were RED
  as required, 1 was INFO (`iv_price_only_alone_vega_guard_masks`), 0 were NOT CAUGHT, and live hashes were unchanged
  before and after. The baseline is now asserted by the code (D12 closed, section 7), not only printed.
- REVIEW_B section 6 (R-14 simplify delta) is the reviewer's as-built read of these bytes: D13, D12 and D4 closed,
  no MAJOR, new MINOR items D14 and D15. REVIEW_B did not run code; its execution evidence is the hub's gate record.
- Price-only acceptance alone is not caught by the mutation proof because the vega >= 1e-8 guard masks it (listed as an INFO row).
  Only the pair of mutations goes red. That is defense in depth, not a hole.
- `--ticker` silently ignores `--spot` and `--div`; no note is printed.
- CONTRACT 8 lists the console starting with the chain-rows line. As built (R3), the `params:` line is first, and the
  `chain:` line reads `rejected: n/a` for synthetic and ticker sources instead of a number.
- `selftest.py` and `oracle_check.py` read no files under `.claude/` (by grep of their source), so a fresh clone runs them.
  `oracle_check.py` prints a line `REVIEW_A.md present at ...: False` there; that is informational.
- The CSV control total counts non-blank lines, so a quoted field with an embedded newline makes it fail on a valid file.
  It fails closed (exit 1) and is also an `assert` (off under `-O`).
- `main.py` line 6 (a usage example in its docstring) and `selftest.py` line 1253 name a ticker symbol. This README does not.

## 9. Recovery

This tool keeps no database, workbook or other persistent state. It writes only the HTML (`--out`) and, if asked,
the CSV (`--export-chain`), both overwritten without a prompt. There is no dated backup to restore from.
If a run fails midway, nothing else is damaged: fix the cause and run again. To keep a prior output, give each run a
different `--out`. If a previously good HTML looks wrong, regenerate it from the same command (the synthetic path is
seeded, default seed 0, so it reproduces); for `--ticker`, live data changes, so export the chain with `--export-chain`
on the first run to keep a reproducible input.

## 10. Known failure messages

Errors go to stderr, ASCII only. Console and error text pass through `data_io.ascii_fold` (R-14 G): en and em dashes
become "-" and any other non-ASCII character becomes "?". This includes the text of yfinance errors that
`fetch_yfinance_chain` wraps (`data_io.py` line 372; `main.py` lines 47 and 192 call it).

| Text | Exit | Cause and action |
|---|---|---|
| `input error: ValueError: --csv requires --spot` | 2 | add `--spot` |
| `input error: ValueError: --valuation-date must be YYYY-MM-DD, got '...'` | 2 | fix the date |
| `input error: ValueError: CSV ...: missing required column '...' (found [...])` | 2 | add the column |
| `input error: ValueError: CSV ...: need a 'T' or an 'expiry' column` | 2 | add one |
| `input error: ValueError: CSV ...: 'expiry' column requires params.valuation_date` | 2 | pass `--valuation-date` |
| `input error: ValueError: CSV ...: zero valid rows (read N, rejected by reason: {...})` | 2 | inspect the reject reasons |
| `input error: FileNotFoundError: ...` (missing CSV; other OS errors print their own type name) | 2 | fix the path |
| `input error: RuntimeError: fetch_yfinance_chain(SYM) failed: <Type>: <message>` | 2 | module missing, no network, empty data or no usable expiries. Check yfinance and network. There is no synthetic fallback by design |
| `main.py: error: argument --ticker: not allowed with argument --csv` (argparse text) | 2 | pass one source |
| `build_surface failed: ...` (for example `fewer than 2 maturities with >= 4 usable quotes`) | 3 | the chain has too few usable quotes |
| `input error: RuntimeError: control total failed: read N != chain M + rejects R` | 2 | the loader's own row accounting failed; inspect the CSV |
| `unexpected error: RuntimeError: control total failed: ...` (quotes vs OTM count, status codes, iv finite vs status, grid shapes, n_quotes_used) | 1 | raised inside `prepare_quotes` or `build_surface`; `main.py` catches only ValueError around `build_surface`. Treat the run as invalid |
| `unexpected error: AssertionError: control total 1 broken: ...` | 1 | CSV row accounting failed; inspect the file |
| `unexpected error: AssertionError: control total 2 broken: ...` or `3` or `4` | 1 | internal count mismatch; treat the run as invalid and do not use the HTML |
| `unexpected error: <Type>: <message>` | 1 | any other exception, for example a failure writing `--out` |

## 11. Case study

This repository also publishes the team's flow artifacts as an AI multi-agent case study: how work was routed
between roles, the rulings that governed it, and the scoring and metrics of the run. Start at
`case-study/INDEX.md`. It is kept separate from the code. Paths inside those files refer to the original working
machine and do not exist in this repository. The code and this README do not depend on it.

## 12. Files

| File | Purpose |
|---|---|
| `main.py` | command-line entry point |
| `bs_pricing.py` | Black-Scholes price, vega, bounds, IV solver with status codes |
| `synthetic.py` | SSVI-based synthetic chain generator |
| `data_io.py` | CSV loader, yfinance fetch, `MarketParams` |
| `surface.py` | OTM quote preparation, surface build, arbitrage diagnostics, smile and term-structure slices |
| `viz.py` | Plotly dashboard |
| `selftest.py` | content-level checks and mutation proof |
| `oracle_check.py` | independent oracle comparison |
| `requirements.txt` | dependencies |
