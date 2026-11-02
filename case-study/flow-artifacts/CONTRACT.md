> **Status for readers of this case study:** this is CONTRACT v1.0 as written at the start of the flow. It is SUPERSEDED IN PART by the rulings in OWNERSHIP.md (corrections log R-1 to R-9) and by REVIEW_A.md. Where they differ, the rulings and the shipped code govern; see the repo README for the rules in force.

# CONTRACT - Volitility-Model (3D implied-vol surface + standalone Plotly HTML)

STATUS: v1.0 IN FORCE (2026-11-02). Binding over this file: .claude/REVIEW_A.md rulings (OWNERSHIP.md, Binding rulings).
Governing givens (cited, not restated): approved plan <HOME>/.claude/plans/<approved-plan>.md ; flow board design givens (12:49). Where this file is silent, the plan governs.

Reading rule: each relation is stated ONCE, in the section named in the "Governs" column of section 1.3. Other sections POINT to it. If you find two statements that disagree, build to the governing one, stub/record the assumption in your run-log, do not block.

---------------------------------------------------------------------------------------------------
## 1. Layout, conventions, units

### 1.1 Files (flat, repo root; import as `from bs_pricing import ...`)
| File | Lane | Imports from this project |
|---|---|---|
| bs_pricing.py | BUILD-A | none (numpy, scipy only) |
| synthetic.py | BUILD-A | bs_pricing |
| data_io.py | BUILD-B | none (numpy, pandas, stdlib; yfinance lazily inside fetch_yfinance_chain) |
| surface.py | BUILD-B | bs_pricing, data_io |
| viz.py | BUILD-C | surface, data_io (plotly, numpy, pandas) |
| main.py | BUILD-C | all |
Acyclic. Every module is import-safe (no work at import time, no printing). Python 3.13, numpy 2.5, scipy 1.18, plotly 7.1, pandas 3.0 (copy-on-write: never chained assignment; use `df = df.assign(...)` or `df.loc[mask, col] = ...` on an owned copy).

### 1.2 Conventions (apply everywhere; the field name carries the unit where doubt exists)
- Time: T is in YEARS, ACT/365: T = (expiry_date - valuation_date).days / 365.0. T_days (display only) = T*365.
- Rates: r and q are CONTINUOUSLY compounded, annual, DECIMALS (0.04 = 4%). Flat in T. No discrete dividends.
- Volatility: iv, sigma, sigma_true are ANNUALISED DECIMALS (0.20 = 20 vol points). Percent appears ONLY in viz.py display values (iv*100) and console text, never in any stored field or function argument.
- Total variance: w = iv**2 * T (dimensionless). Never stored as percent.
- Forward: F(T) = S*exp((r-q)*T). Defined ONCE as `MarketParams.forward` (section 5.1); everything else calls it.
- Log-moneyness: k = ln(K/F(T)) (natural log, dimensionless). k >= 0 means K >= F.
- Prices/strikes/S: same currency, per share. `price` is the option MID (or last) price per share, undiscounted cash, never per-contract (no x100 multiplier).
- Floats are float64. Strings in `type` are exactly "C" or "P" (upper case). Booleans `is_call` are numpy/python bool.
- Console output: ASCII only (no en/em dashes, no unicode). Files written UTF-8, LF line endings from our code.
- As-of: there is one valuation instant per run, given by `MarketParams` (S, r, q, valuation_date). Quotes are a snapshot; there are no late/restated records. Duplicate rows for the same (strike, T, type) are a data error (section 5.2).

### 1.3 Governs (where each relation lives)
| Relation | Section |
|---|---|
| Solver status codes, names, iv-NaN rule | 2.3 |
| Axis order of w/iv/K | 6.1 |
| Chain DataFrame columns | 2.1 |
| Quotes DataFrame columns, OTM split rule | 2.2 |
| arbitrage_report return format | 6.4 |
| Control totals | 10 |
| Stub format | 11 |
| Error semantics per function | 9 |

---------------------------------------------------------------------------------------------------
## 2. Shared schemas

### 2.1 CHAIN DataFrame (input to prepare_quotes; produced by generate_chain, load_chain_csv, fetch_yfinance_chain)
Columns, in this order, float64 unless stated, no NaN allowed in the first four:
| Column | Type | Meaning |
|---|---|---|
| strike | float64 | K > 0 |
| T | float64 | years, > 0 |
| type | str | "C" or "P" |
| price | float64 | > 0, option price per share |
| sigma_true | float64, OPTIONAL | decimal; present only from generate_chain (or a CSV that carries it). Absent column = no ground truth. Never read by any pricing/solver/surface code path (only QA/oracle/diagnostics may read it). |
Index: default RangeIndex(0..n-1) after sorting by (T, strike, type) ascending with "C" before "P". There is NO `expiry` column in a chain (expiry is converted to T by the loader). Unknown extra CSV columns are dropped by the loader.

### 2.2 QUOTES DataFrame (output of prepare_quotes)
One row per chain row that is on the OTM side (rule below). Columns in this order:
| Column | Type | Meaning |
|---|---|---|
| strike | float64 | K |
| T | float64 | years |
| type | str | "C" or "P" (the OTM side) |
| price | float64 | from chain |
| F | float64 | MarketParams.forward(T) |
| k | float64 | ln(strike / F) |
| iv | float64 | decimal; NaN iff status >= 2 (section 2.3) |
| w | float64 | iv**2 * T; NaN iff iv is NaN |
| status | int8 | solver status code (section 2.3) |
| sigma_true | float64, OPTIONAL | carried through if the chain had it |
OTM split rule (governing): compute k first as `np.log(strike / F)`; keep a row iff (type == "P" and k < 0) or (type == "C" and k >= 0). ITM-side rows are removed here and nowhere else; no other filtering happens in prepare_quotes (failed solves are KEPT with status >= 2). Sorted by (T, strike); RangeIndex.

### 2.3 Solver status codes (constants live in bs_pricing; everyone imports them, never re-types the ints)
| Name (constant) | int | iv value | Meaning |
|---|---|---|---|
| IV_STATUS_NEWTON | 0 | finite | converged by vectorized Newton |
| IV_STATUS_BRENT | 1 | finite | converged by brentq fallback |
| IV_STATUS_OUT_OF_BOUNDS | 2 | NaN | price <= lower_bound + BOUND_EPS, or price >= upper_bound - BOUND_EPS (no-arb bounds, section 3.3) |
| IV_STATUS_FAILED | 3 | NaN | in bounds but no root in [IV_MIN, IV_MAX] (no sign change) or no convergence |
| IV_STATUS_INVALID_INPUT | 4 | NaN | any of price,S,K,T,r,q is NaN/inf, or S<=0, K<=0, T<=0, price<=0 |
Also exported: `IV_STATUS_NAMES = {0:"newton",1:"brent",2:"out_of_bounds",3:"failed",4:"invalid_input"}`, `IV_MIN = 1e-4`, `IV_MAX = 5.0`, `BOUND_EPS = 1e-10` (absolute, in price units). Rule: iv is finite iff status in {0,1}. Evaluation order when several apply: 4, then 2, then solve (0/1/3).

---------------------------------------------------------------------------------------------------
## 3. bs_pricing.py  (BUILD-A)

Shared rules for 3.1-3.4: arguments are array_like, broadcast with numpy rules; return float64 ndarray of the broadcast shape (0-d array for all-scalar input; callers use float()). `is_call` broadcasts too. Must emit NO RuntimeWarning or numpy FloatingPointError (wrap in np.errstate, use np.where with safe denominators). Non-broadcastable shapes raise ValueError (the only raise). NaN in any input gives NaN out; no other input validation raises.

### 3.1 bs_price
`bs_price(S, K, T, r, q, sigma, is_call) -> np.ndarray`  European Black-Scholes with continuous dividend yield (formula: plan section 2). Degenerate region: if T <= 0 or sigma <= 0 or sigma*sqrt(T) < 1e-12, return discounted intrinsic: call max(S*exp(-qT) - K*exp(-rT), 0), put max(K*exp(-rT) - S*exp(-qT), 0), with T clipped to >= 0 inside the exponentials. S <= 0 or K <= 0 gives NaN. sigma < 0 gives NaN. Units: sigma decimal.

### 3.2 bs_vega
`bs_vega(S, K, T, r, q, sigma) -> np.ndarray`  d(price)/d(sigma) per 1.00 of sigma (NOT per vol point): S*exp(-qT)*phi(d1)*sqrt(T). Same degenerate region as 3.1 returns 0.0. Same NaN rules.

### 3.3 price_bounds
`price_bounds(S, K, T, r, q, is_call) -> tuple[np.ndarray, np.ndarray]`  returns (lower, upper) no-arbitrage bounds: call [max(S e^{-qT} - K e^{-rT}, 0), S e^{-qT}], put [max(K e^{-rT} - S e^{-qT}, 0), K e^{-rT}]. T clipped to >= 0. Invalid inputs (S<=0, K<=0, NaN) give NaN in both.

### 3.4 implied_vol
`implied_vol(price, S, K, T, r, q, is_call, tol=1e-8, max_iter=50, sigma_lo=IV_MIN, sigma_hi=IV_MAX) -> tuple[np.ndarray, np.ndarray]`
Returns (iv, status): iv float64 ndarray, status int8 ndarray, both of the broadcast shape. Status semantics: section 2.3 (governing). Algorithm (plan section 2): validity/bounds check, then vectorized Newton (Brenner-Subrahmanyam start, sigma clipped to [sigma_lo, sigma_hi], at most max_iter steps), then per-element scipy.optimize.brentq on [sigma_lo, sigma_hi] for elements that did not converge or whose vega < 1e-8. `tol` is an ABSOLUTE PRICE residual: converged iff |bs_price(sigma) - price| <= tol (Brent additionally xtol=1e-12). Never raises for bad quotes (returns NaN + status); no warnings.

---------------------------------------------------------------------------------------------------
## 4. synthetic.py  (BUILD-A)

Module constants (so main and tests need not retype defaults): `DEFAULT_S = 100.0`, `DEFAULT_R = 0.04`, `DEFAULT_Q = 0.015`, `DEFAULT_MATURITIES_YEARS = (1/12, 2/12, 3/12, 6/12, 9/12, 1.0, 1.5, 2.0)`, `DEFAULT_STRIKE_FRACTIONS = tuple(np.arange(0.60, 1.40 + 1e-9, 0.025))` (strike = fraction * S).

### 4.1 true_vol
`true_vol(k, T) -> np.ndarray`  ground-truth implied vol, ANNUALISED DECIMAL, broadcast over k and T (k = ln(K/F), T years; T > 0 else NaN). Defined by SSVI total variance (this section governs; reference parameters are pinned so ORACLE can reimplement from this text):
  theta(T) = T * atm_vol(T)**2, with atm_vol(T) = 0.18 + 0.06*(1 - exp(-T/1.0))
  w(k,T) = (theta/2) * (1 + rho*phi*k + sqrt((phi*k + rho)**2 + 1 - rho**2)), rho = -0.7, phi = 1.5
  true_vol = sqrt(w / T)
theta is increasing in T and phi is constant, so the truth satisfies SSVI's calendar and butterfly sufficient conditions over the default domain. Changing any constant requires a version bump (section 15).

### 4.2 generate_chain
`generate_chain(S=DEFAULT_S, r=DEFAULT_R, q=DEFAULT_Q, maturities=None, strikes=None, noise_bps=5.0, tick=0.01, min_price=0.05, seed=0) -> pd.DataFrame`
Returns a CHAIN (section 2.1) INCLUDING `sigma_true`. For each maturity T (default DEFAULT_MATURITIES_YEARS) and each strike K (default S*DEFAULT_STRIKE_FRACTIONS), for both "C" and "P": sigma_true = true_vol(ln(K/F), T) with F from the formula in section 1.2; price = bs_price(...) at sigma_true; then multiply by (1 + noise_bps*1e-4 * z), z ~ N(0,1) from np.random.default_rng(seed) (noise_bps = 0 means no noise and no RNG draw effect on prices); then if tick > 0 round to the nearest tick (tick = 0 disables rounding); then DROP rows with price < min_price (defaults drop sub-5-cent quotes; min_price = 0 keeps everything with price > 0). Deterministic for a given argument set. Returns the chain only (no MarketParams); main constructs MarketParams from the same S, r, q it passed in. The noise-free/untick-ed chain (noise_bps=0, tick=0, min_price=0) is the "clean chain" used for exact round-trip tests.

---------------------------------------------------------------------------------------------------
## 5. data_io.py  (BUILD-B)

### 5.1 MarketParams
```
@dataclass(frozen=True)
class MarketParams:
    S: float                       # spot > 0
    r: float                       # continuous rate, decimal, annual
    q: float                       # continuous dividend yield, decimal, annual
    valuation_date: datetime.date | None = None   # None = unknown (only needed for expiry->T and hover date labels)
    def forward(self, T) -> np.ndarray | float   # F = S*exp((r-q)*T); array_like in, same shape out (float64); the ONLY place F is defined
```
__post_init__ raises ValueError if S is not finite > 0 or r, q not finite. Hover/expiry labels (viz) use valuation_date + round(T*365) days; if valuation_date is None the label is the string "T=<T:.3f>y".

### 5.2 load_chain_csv
`load_chain_csv(path, params=None) -> tuple[pd.DataFrame, pd.DataFrame]`  returns (chain, rejects).
CSV format: UTF-8 (BOM tolerated), comma delimiter, header on row 1, LF or CRLF. Header names case-insensitive, whitespace-stripped. Required: strike, type, price, and ONE of T or expiry (ISO yyyy-mm-dd). If both T and expiry are present, T is used and expiry ignored. `type` accepts C/P/call/put in any case, normalised to "C"/"P". Optional numeric sigma_true is kept. expiry requires params.valuation_date (else ValueError). T = (expiry - valuation_date).days / 365.0.
Row-level errors QUARANTINE (row removed from chain, appended to `rejects`): non-numeric/NaN field, strike <= 0, price <= 0, T <= 0 (including expiry on/before valuation date), unparseable type or date, duplicate (strike, T, type) after the first. `rejects` columns: `line` (int, 1-based file line of the row), `reason` (str, one of "non_numeric","non_positive","bad_type","bad_date","duplicate"), plus `raw` (str, the raw line). File-level errors HALT by raising: FileNotFoundError (path), ValueError (missing required column; expiry without valuation_date; zero rows left in chain). Chain returned per section 2.1. Control total: section 10.

### 5.3 fetch_yfinance_chain
`fetch_yfinance_chain(ticker, max_expiries=8, min_days=7, risk_free_rate=0.04, valuation_date=None) -> tuple[pd.DataFrame, MarketParams]`  OPTIONAL, network, only called via `--ticker`. Imports yfinance lazily. valuation_date default = today. Uses the nearest `max_expiries` expiries with >= min_days to expiry; price = (bid+ask)/2 when bid>0 and ask>0 else lastPrice; q = trailingAnnualDividendYield (or dividendYield) as a decimal, 0.0 if absent; S = last/regular market price. Any failure (module missing, no network, empty data, no usable expiries) raises RuntimeError with an ASCII message; NEVER silently falls back to synthetic data. Quotes pass through the same row rules as 5.2 (non-positive dropped; dropped rows are not reported here). Not exercised by selftest (no network assumption).

---------------------------------------------------------------------------------------------------
## 6. surface.py  (BUILD-B)

### 6.1 Surface dataclass (axis order stated ONCE here: every 2-D array is indexed [i_T, j_k], shape (n_T, n_k))
```
@dataclass
class Surface:
    T_grid: np.ndarray    # (n_T,) years, strictly increasing, all > 0
    k_grid: np.ndarray    # (n_k,) log-moneyness, strictly increasing
    w: np.ndarray         # (n_T, n_k) total variance, finite, >= 0
    iv: np.ndarray        # (n_T, n_k) decimals = sqrt(w / T_grid[:, None]); finite, >= 0
    F: np.ndarray         # (n_T,) params.forward(T_grid)
    K: np.ndarray         # (n_T, n_k) strike at each node = F[:, None] * exp(k_grid[None, :])
    method: str           # "rbf" or "spline"
    params: MarketParams
    n_quotes_used: int    # quotes rows with status in {0,1} that fed the interpolator
    dropped_T: tuple      # maturities (float years) removed for having < MIN_QUOTES_PER_T usable quotes; () if none
    _w_fn: Callable = field(repr=False)   # private (T_array, k_array) -> w_array, broadcast; the interpolator
    def evaluate(self, T, k) -> np.ndarray      # iv (decimal) at arbitrary (T, k)
    def evaluate_w(self, T, k) -> np.ndarray    # total variance at arbitrary (T, k)
```
Module constants: `MIN_QUOTES_PER_T = 4`, `W_FLOOR = 0.0`. evaluate/evaluate_w: array_like T and k broadcast; float64 result of broadcast shape; w clipped to >= W_FLOOR; iv = sqrt(w/T). Raises ValueError if any finite T <= 0; NaN input gives NaN output; otherwise always finite (extrapolates: rbf via the kernel, spline by clamping k to [k_grid[0], k_grid[-1]] and T to [T_grid[0], T_grid[-1]] - extrapolated values are NOT reliable and are labelled so by `in_domain` in 6.6). The grid arrays satisfy: Surface has no NaN/inf anywhere (guaranteed by build_surface or it raises).

### 6.2 prepare_quotes
`prepare_quotes(chain, params) -> pd.DataFrame`  returns QUOTES (section 2.2). Computes F = params.forward(T), k, applies the OTM split (2.2), calls implied_vol on the selected rows (is_call = type == "C"), sets w = iv**2 * T where iv finite. Never raises for bad quotes (they get status >= 2). Raises ValueError only if `chain` lacks the required columns (2.1). Does NOT read sigma_true except to carry it through. Control total: section 10.

### 6.3 build_surface
`build_surface(quotes, params, method="rbf", n_T=60, n_k=80, smoothing=1e-6) -> Surface`
Uses ONLY rows with status in {0,1}. Maturities with fewer than MIN_QUOTES_PER_T usable quotes are dropped (recorded in `dropped_T`, not an error); ValueError if fewer than 2 maturities remain, or method not in {"rbf","spline"}, or n_T < 2, n_k < 4. Interpolates TOTAL VARIANCE w over (T, k) (plan section 4), sets iv = sqrt(w/T).
Grid: T_grid = linspace(min usable T, max usable T, n_T); k_grid = linspace(min usable k, max usable k, n_k) (union of quoted k; corners beyond one maturity's own quoted wings are extrapolated).
- "rbf": scipy RBFInterpolator, kernel "thin_plate_spline", `smoothing` as given, inputs min-max scaled to [0,1] on each axis using the usable quotes' T and k ranges.
- "spline": stage 1 natural CubicSpline in k per usable maturity (ends clamped flat), stage 2 PchipInterpolator in T per k node, per plan section 4.
After interpolation: w = max(w, W_FLOOR); all outputs must be finite or ValueError("non-finite surface"). Surface.K/F per 6.1.

### 6.4 arbitrage_report (governing format)
`arbitrage_report(surface, tol_calendar_w=1e-6, tol_butterfly=1e-8) -> dict`
DIAGNOSTICS, NOT GUARANTEES: counts grid violations; neither enforces nor certifies no-arbitrage. Return value is EXACTLY this dict (keys and types fixed; no other keys, in particular NO boolean pass/ok/verdict key):
```
{
 "disclaimer": DIAGNOSTIC_DISCLAIMER,   # str constant exported by surface.py:
                                        # "DIAGNOSTIC ONLY: these checks count grid violations; they do not enforce or guarantee an arbitrage-free surface."
 "calendar":  {"n_checked": int, "n_violations": int, "max_violation_w": float, "tol": float},
 "butterfly": {"n_checked": int, "n_violations": int, "max_violation": float,   "tol": float},
 "lines": list[str],                    # ASCII, exactly 3 lines, printed verbatim by main:
}
```
lines[0] = disclaimer; lines[1] = f"calendar: {n_violations}/{n_checked} violations (max {max_violation_w:.2e} in total variance, tol {tol:.1e})"; lines[2] = f"butterfly: {n_violations}/{n_checked} violations (max {max_violation:.2e} in dC/dK, tol {tol:.1e})".
Calendar: for every k node j and consecutive T rows, dw = w[i+1,j] - w[i,j]; violation iff dw < -tol_calendar_w; n_checked = (n_T-1)*n_k; max_violation_w = max(0, max(-dw)). Butterfly: for each row i, call prices C_j = bs_price(S, K[i,j], T_grid[i], r, q, iv[i,j], True); slope s_j = (C[j+1]-C[j])/(K[i,j+1]-K[i,j]); violation iff s_{j+1} - s_j < -tol_butterfly (dimensionless, undiscounted call price convex in K <=> slope non-decreasing); n_checked = n_T*(n_k-2); max_violation = max(0, max(-(s_{j+1}-s_j))). Counts are integers; max_* are floats >= 0.

### 6.5 smile
`smile(surface, T, n_k=None) -> pd.DataFrame`  columns [k, strike, iv] (float64, decimals) at fixed T (years, any T > 0; need not be a grid node): k = surface.k_grid (or linspace over its range with n_k points if n_k given), strike = surface.params.forward(T)*exp(k), iv = surface.evaluate(T, k). Rows ascending in k.

### 6.6 term_structure
`term_structure(surface, K=None) -> pd.DataFrame`  columns [T, k, iv, in_domain] over T = surface.T_grid. For fixed strike K (> 0, currency units): per-maturity k_i = ln(K / F(T_i)) with F from params.forward (NOT a fixed k-row); iv = surface.evaluate(T_i, k_i). For K=None: the ATM-FORWARD curve, k_i = 0 for all i (a different curve, labelled as such by viz). in_domain (bool) = k_grid[0] <= k_i <= k_grid[-1]. K <= 0 raises ValueError.

---------------------------------------------------------------------------------------------------
## 7. viz.py  (BUILD-C)

### 7.1 build_dashboard
`build_dashboard(surface, quotes, params, colorscale="Viridis", x_axis="k", n_smiles=5, strike_fractions=(0.8, 0.9, 1.0, 1.1, 1.2)) -> plotly.graph_objects.Figure`
`x_axis` in {"k","strike"}, `colorscale` in {"Viridis","Plasma"}; otherwise ValueError. One make_subplots figure: row 1 a full-width 3D scene, row 2 two xy panels (left smiles, right term structures). Display units: iv shown as percent (iv*100). Contract points that QA parses from fig.to_dict():
- Surface trace: type "surface", name "IV surface". x, y, z all 2-D of shape (n_k, n_T) (z[j_k, i_T] = 100*iv[i_T, j_k], i.e. the transpose of Surface.iv; x = T_grid broadcast, y = k_grid broadcast if x_axis=="k" else Surface.K transposed). Axis titles exactly: "Time to maturity (years)", then "Log-moneyness k = ln(K/F)" or "Strike", then "Implied volatility (%)".
- customdata shape (n_k, n_T, 5) = [K, T_days, expiry_label, iv_pct, k] (expiry_label per 5.1); hovertemplate EXACTLY `Strike: %{customdata[0]:.2f}<br>Expiry: %{customdata[2]} (%{customdata[1]:.0f}d)<br>IV: %{customdata[3]:.2f}%<extra></extra>`.
- Dropdown (updatemenus) restyles `colorscale` between Viridis and Plasma; initial = the argument.
- Market overlay: Scatter3d, name "Market quotes", only quotes with status in {0,1}, same axes/units, same hover fields.
- Smiles (row 2 left): up to n_smiles distinct quote maturities spread evenly over the usable maturities; per maturity one line trace named "Smile T=<T:.3f>y" (surface.smile) and one marker trace of its quotes named "Quotes T=<T:.3f>y"; a slider (sliders) toggles which smile is visible. x is k or strike per x_axis.
- Term structures (row 2 right): for each f in strike_fractions, trace named "Term K=<f*S:.2f>" using term_structure(surface, f*params.S); plus one trace named "ATM-forward (k=0)". x is T in years, y is IV %.
- Layout title contains the exact phrase "not guaranteed arbitrage-free".
Pure function of its arguments; does not write files.

### 7.2 write_dashboard
`write_dashboard(fig, path, plotlyjs="cdn") -> str`  fig.write_html(path, include_plotlyjs=plotlyjs, full_html=True); plotlyjs in {"cdn","inline"} else ValueError ("inline" = fully offline, ~5 MB). Creates missing parent directories. Returns the absolute path (str). Standalone HTML only (user ruling): no server, no Dash.

---------------------------------------------------------------------------------------------------
## 8. main.py  (BUILD-C)

`main(argv=None) -> int`, with `if __name__ == "__main__": sys.exit(main())`. No flags = synthetic chain, rbf, k axis, Viridis, write vol_surface.html, open in browser.
| Flag | Default | Meaning |
|---|---|---|
| --csv PATH | none | load chain via load_chain_csv; requires --spot; mutually exclusive with --ticker |
| --ticker SYM | none | fetch_yfinance_chain; mutually exclusive with --csv |
| --spot S | none | spot (required with --csv) |
| --rate r | 0.04 | decimal |
| --div q | 0.0 with --csv; DEFAULT_Q for synthetic | decimal |
| --valuation-date YYYY-MM-DD | none (synthetic: not needed) | needed when the CSV has `expiry` |
| --method {rbf,spline} | rbf | |
| --x-axis {k,strike} | k | |
| --colorscale {Viridis,Plasma} | Viridis | |
| --n-T N / --n-k N | 60 / 80 | grid size |
| --noise-bps X / --seed N | 5.0 / 0 | synthetic only; ignored (with an ASCII note) for csv/ticker |
| --export-chain PATH | none | write the chain used as CSV (columns per 2.1, header row, full float repr) so it can be fed back to --csv |
| --out PATH | vol_surface.html | |
| --offline | off | plotlyjs="inline" |
| --no-open | off | skip webbrowser.open |
Console (ASCII, in this order): chain rows read / rejected / kept; quotes rows and solver status breakdown using IV_STATUS_NAMES (one count per name, zeros shown); usable quotes, dropped maturities; IV range (min/max, in percent, labelled "%"); the 3 arbitrage_report["lines"] verbatim; output path. Exit codes: 0 success; 2 usage or input error (argparse errors, load/fetch failure, bad CSV; ticker failure never falls back to synthetic); 3 build_surface raised ValueError (insufficient/unusable quotes); 1 any other exception. Error text goes to stderr, ASCII.

---------------------------------------------------------------------------------------------------
## 9. Error and NaN semantics (one row per function; "raise" = exception, "NaN" = value, "quarantine" = returned reject)
| Function | Bad input / bad data behavior |
|---|---|
| bs_price, bs_vega, price_bounds | NaN in = NaN out; S<=0, K<=0, sigma<0 -> NaN; T<=0 or sigma*sqrt(T)<1e-12 -> intrinsic (vega 0); only non-broadcastable shapes raise ValueError |
| implied_vol | never raises for data; NaN iv + status 2/3/4 (section 2.3) |
| generate_chain | raises ValueError for empty maturities/strikes, S<=0, noise_bps<0, tick<0; never NaN prices |
| true_vol | T<=0 -> NaN |
| load_chain_csv | row problems quarantine to `rejects`; file problems raise (5.2) |
| fetch_yfinance_chain | any failure raises RuntimeError (5.3) |
| MarketParams | ValueError on construction (5.1) |
| prepare_quotes | no raise for bad quotes (status>=2 rows kept); ValueError only for missing columns |
| build_surface | drops thin maturities; ValueError if <2 maturities left, bad method/size, or non-finite result |
| Surface.evaluate*, term_structure, smile | ValueError for T<=0 / K<=0; NaN in = NaN out; finite otherwise |
| arbitrage_report | never raises on a valid Surface; counts only |
| build_dashboard/write_dashboard | ValueError on bad option values (7.1/7.2) |
Nothing anywhere swallows an exception to continue silently; a caught exception is either converted per this table or re-raised.

---------------------------------------------------------------------------------------------------
## 10. Control totals (zero tolerance; each is an integer identity that main prints and selftest asserts)
1. Loader: data rows read from the CSV (excluding header and blank lines) == len(chain) + len(rejects).
2. prepare_quotes: len(quotes) == count of chain rows with (type=="P" and ln(strike/F)<0) or (type=="C" and ln(strike/F)>=0), recomputed independently from the chain; AND the sum over status codes {0..4} of rows == len(quotes).
3. build_surface: surface.n_quotes_used == number of quotes rows with status in {0,1} whose T is not in dropped_T.
4. Solver/iv: iv finite <=> status in {0,1} (2.3), on every quotes row.
5. Surface finiteness: np.isfinite(w).all() and np.isfinite(iv).all(); w.shape == iv.shape == K.shape == (len(T_grid), len(k_grid)).

---------------------------------------------------------------------------------------------------
## 11. Stub conventions (build in parallel, never block)
A builder needing another lane's function that may not exist yet writes the fallback INSIDE a guarded import:
```
try:
    from bs_pricing import implied_vol, IV_STATUS_NAMES   # real module wins as soon as it exists
except ModuleNotFoundError as _e:
    if _e.name != "bs_pricing":
        raise                                              # a real import error inside the module is NOT a stub case
    import warnings
    warnings.warn("STUB IN USE: bs_pricing (CONTRACT.md section 3)")
    # ===== STUB per CONTRACT.md section 3 =====
    def implied_vol(...): ...      # same signature, types, shapes, status codes as the contract; minimal but correct
    # ===== END STUB =====
```
Rules: (a) the marker text is exactly "STUB per CONTRACT.md section <N>" with N the governing section; (b) stubs copy signatures and constants verbatim from this file, never invent; (c) a stub is correct-but-slow, never a fake return value; (d) when the real module exists in the repo at the end of your work, delete the stub and leave a plain import; (e) record in your run-log every stub you left in and the assumption it carries. QA treats a remaining "STUB per CONTRACT.md" marker in final source as a finding.

---------------------------------------------------------------------------------------------------
## 12. Acceptance tolerances (inputs to QA/ORACLE; plan checks 1-8 govern what is checked)
- Parity / BS reference: |C - P - (S e^{-qT} - K e^{-rT})| <= 1e-10 on a random grid. Hand reference value: ORACLE/QA compute their own from the textbook formula (not from bs_pricing.py).
- IV round-trip on the CLEAN chain (4.2): max |iv - sigma_true| <= 1e-6 over quotes with status in {0,1}; ALSO assert at least 90% of quotes have status in {0,1} (anti-vacuity: an all-NaN result must fail).
- Noisy default chain: max |iv - sigma_true| <= 0.02 over status in {0,1} rows (ASSUMPTION; tick-rounding makes far-wing rows noisy; QA may tighten with evidence).
- Surface vs truth, CLEAN chain, interior nodes (k within each maturity's quoted range): |evaluate(T,k) - true_vol(k,T)| <= 0.01 for both methods (ASSUMPTION).
- Calendar check on the CLEAN chain surface: n_violations == 0; and an injected violation (decrease w at later T on a copy) must be detected: n_violations > 0.
- Fixed-strike term structure for an OTM strike differs from the k=0 curve by > 1e-4 somewhere (proves per-maturity mapping).
- HTML: assertions run on fig.to_dict() per 7.1 (trace names, hovertemplate string, axis titles, customdata shape), then on the written file existing and containing "hovertemplate".

---------------------------------------------------------------------------------------------------
## 13. Treatment decisions REVIEW-A should rule on (rulings land in REVIEW_A.md and bind over this file)
- R1 Dividend/forward: continuous flat q and r, F=S e^{(r-q)T} (1.2). Equity options (esp. yfinance) are American with discrete dividends; BS-European IV is an approximation. Rule on the disclosure wording and whether any mitigation is required in v1.
- R2 OTM split: puts K<F, calls K>=F, split by k>=0 not by K vs S (2.2); the single boundary quote at k==0 goes to the call.
- R3 Total variance: interpolation in w (not iv), RBF thin-plate + smoothing 1e-6 and min-max scaling (6.3); k_grid is the UNION of quoted k, so corners are extrapolated. Rule on smoothing default and on whether to trim to the intersection.
- R4 Fixed-strike mapping: per-maturity k_i, with `in_domain` flagging extrapolated points and a separate k=0 ATM-forward curve (6.6).
- R5 Diagnostics: calendar via dw on grid, butterfly via slope-difference of BS call prices on the grid (6.4); tolerances 1e-6 / 1e-8; no boolean verdict key by design; exact disclaimer string. Rule on wording and sufficiency of the butterfly proxy (it is not Durrleman's g(k) condition).
- R6 Solver: extra code 4 (INVALID_INPUT) beyond the plan's four; BOUND_EPS 1e-10 absolute; IV_MIN 1e-4, IV_MAX 5.0 (2.3).
- R7 Day count ACT/365 and flat T grid from quoted min to max T (1.2, 6.3).
- R8 Dashboard default plotlyjs="cdn" needs internet to render; "--offline" gives inline (7.2). Rule on whether the default should be inline.

---------------------------------------------------------------------------------------------------
## 14. Open items deferred (defaults in force; no lane blocks)
| Item | Default in force |
|---|---|
| RBF smoothing value | 1e-6 (6.3); builder may not change without a version bump; REVIEW-A may rule |
| Tolerances marked ASSUMPTION (section 12) | as written; QA may tighten, never loosen, and records evidence |
| yfinance dividend/risk-free sourcing | q from ticker info or 0.0; r = 0.04 argument (5.3) |
| Maturity-thinning rule (MIN_QUOTES_PER_T = 4) | as written (6.1) |
| Calendar/butterfly tolerances | 1e-6 / 1e-8 (6.4) |

---------------------------------------------------------------------------------------------------
## 15. Change protocol and changelog
Any change after lanes start = version bump + one changelog line naming lanes to re-check. Revision steps: demote STATUS to "vX DRAFT, NOT IN FORCE, vX-1 governs", land content edits (anchors never cross a section heading), run a duplicate-value grep over every value touched (status codes, string constants, trace names, tolerances), promote STATUS last.
| Version | Change | Re-check |
|---|---|---|
| v1.0 | initial contract | all lanes |
