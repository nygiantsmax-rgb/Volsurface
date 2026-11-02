# REVIEW_A - Volitility-Model (domain-reviewer, contract pass)

STATUS: FINAL (2026-11-02). Reviews CONTRACT.md v1.0. Rulings marked CHANGE are BINDING over CONTRACT.md
(OWNERSHIP.md "Binding rulings"). Builders cite the ruling ID. ACCEPT = the contract text stands as written.
Method: ruled by reading only (no Bash in this role). Numeric claims below are HAND-DERIVED from CONTRACT.md 4.1
and 4.2 formulas; each names the query that confirms or refutes it fastest on real output.
Relay note: SendMessage was not available to this lane, so the hub relays from this file and the lane report.
Builds were already finished on disk when these rulings landed. Each CHANGE is a fix-in-place by its owner_lane,
and REVIEW-B re-checks every ruling against the as-built code. Team-lead ruling R-1 (OWNERSHIP.md corrections log)
governs IV acceptance; R5 below records the concession.

CHANGE list by lane (detail in each ruling):
- BUILD-A: R6, R16 (R5 is superseded by lead R-1: no further change beyond the R5 guard sentence)
- BUILD-B: R2, R9, R10, R11, R21
- BUILD-C: R3, R13, R14 (R14 deferrable by the hub)
- QA: R12

---------------------------------------------------------------------------------------------------
## Forward, dividends, data source

R1 - CONTRACT 1.2 (Forward), 5.1, 12 (parity) - ACCEPT
F = S*exp((r-q)T) with flat continuous r, q, and k = ln(K/F), are correct for European options on a stock with a
continuous yield (Black-Scholes-Merton). The parity reference in section 12,
C - P = S e^{-qT} - K e^{-rT}, is correct. Under this model, fixed-k comparison across T is the right calendar
coordinate: with deterministic r and q, calendar no-arbitrage holds iff w(k,T) is non-decreasing in T at fixed
forward log-moneyness k (Gatheral and Jacquier 2014, "Arbitrage-free SVI volatility surfaces"). No parity-implied
forward is required in v1. That mitigation would matter only on the optional --ticker path.

R2 - CONTRACT 5.3 (q sourcing) - CHANGE - lane BUILD-B
Problem: "q = trailingAnnualDividendYield (or dividendYield) as a decimal". UNVERIFIED IN-LANE, from recall:
Yahoo has been reporting `dividendYield` in PERCENT (e.g. 0.44 meaning 0.44%) while `trailingAnnualDividendYield`
stays a decimal. Read as a decimal, q = 0.44 moves F by a factor exp(-0.44T), which puts the OTM split (2.2) on the
wrong side for most strikes and makes every IV garbage. The operative rule below is a range guard, so it holds
whether or not that recall is right.
Required text (replaces the q clause of 5.3): "q: take `trailingAnnualDividendYield` if it is finite and
0 <= q <= 0.25. Otherwise take `dividendYield`/100 if that is finite and in [0, 0.25]. Otherwise q = 0.0. The
function returns the chosen q in MarketParams. A q outside [0, 0.25] is never used."
Basis: unit consistency, CONTRACT 1.2 ("r and q are ... DECIMALS").

R3 - CONTRACT 8 (console) and 13-R1 (disclosure) - CHANGE - lane BUILD-C (HANDOFF copies the wording into the README)
Required text (add to section 8's console list, as its first item): "Always print one line
`params: S=<S:.4f> r=<r:.4f> q=<q:.4f> (continuous, decimal)`. When the source is --ticker, also print exactly
`note: European Black-Scholes with flat continuous r and q applied to American-style listed options; OTM-only
quotes reduce but do not remove early-exercise and discrete-dividend bias; r is the --rate argument, not a market
curve.`"
Rationale: --div defaults to 0.0 with --csv (section 8). A dividend payer loaded without --div silently gets
F too high, and only a printed q lets the reader catch that. The ticker approximation is a treatment the user
must be told about, not one the code can fix in v1. Using OTM quotes only is the right mitigation: early-exercise
premium concentrates in ITM options.

## OTM split

R4 - CONTRACT 2.2 (OTM split rule) - ACCEPT
Split at k = ln(K/F) (the forward, not spot). K == F goes to the call (k >= 0). No near-ATM blending of put and call
IV in v1. Basis: OTM-at-forward selection is standard practice (for example the CBOE VIX white paper selects
OTM options around the forward). On every synthetic chain, put and call at the same strike carry identical
sigma_true, so the choice cannot bias the round-trip. For OTM quotes the no-arbitrage lower bound is exactly 0:
call with K >= F gives e^{-rT}(F-K) <= 0, put with K < F gives e^{-rT}(K-F) < 0. So IV_STATUS_OUT_OF_BOUNDS on
the low side fires only for price <= BOUND_EPS. Opinion (not binding): on real data, an IV jump at k = 0 is the
visible symptom of a mis-set q or r (see R2, R3).

## Solver

R5 - CONTRACT 3.4 (`tol` semantics) - SUPERSEDED by team-lead R-1 (conceded) - owner_lane BUILD-A
Ruling on the overrule: R-1 is correct, and it is better than my relative-residual text. R-1 requires
|resid| <= tol AND |resid/vega| <= 1e-9. The vol-step term bounds IV error directly, because IV error is
approximately resid/vega, whereas a relative price residual bounds it only through the ratio price/vega. Both
rules kill the false-converged case described below. R-1 kills it in the quantity that section 12 actually tests.
Binding tightening, which BUILD-A applies only if the as-built code does not already behave this way:
"Newton may accept an element only where vega >= 1e-8 and is finite. Where vega < 1e-8, the element is never
Newton-accepted; it routes to Brent, which evaluates no resid/vega division. Status 2 is unchanged:
price <= lower_bound + BOUND_EPS or price >= upper_bound - BOUND_EPS, with BOUND_EPS = 1e-10. For OTM quotes the
lower bound is 0 (R4), so a price in (1e-10, 1e-8] is NOT out_of_bounds. It is solved under R-1, and it relies on
R6 for an accurate price."
No looser rule is permitted. A price-only acceptance test is forbidden.
Original R5 problem statement, retained as the evidence for R-1: "tol is an ABSOLUTE PRICE residual: converged iff |bs_price(sigma) - price| <= tol". The clean chain
(4.2: min_price = 0) keeps OTM rows with prices from 1e-10 up to about 1e-8. Hand-derived example: T = 1/12,
K = 70 put, true w about 0.0040, d about 5.7, price on the order of 1e-9. For such a row, every sigma whose price
is below about 1e-8 "converges", including the Brenner-Subrahmanyam start. The result is status 0 with
|iv - sigma_true| far above the 1e-6 of section 12, which is a false converged marker.
WITHDRAWN, NOT IN FORCE (R-1 governs; retained for the record only): "`tol` is a RELATIVE price residual: Newton has converged iff
|bs_price(sigma) - price| <= tol * price. The denominator is never zero, because status 4 removes price <= 0 and
status 2 removes price <= lower_bound + BOUND_EPS, with lower_bound >= 0. Brent: an element gets status 1 iff
bs_price(sigma_lo) - price and bs_price(sigma_hi) - price differ in sign and brentq(xtol=1e-12) returns. No
further residual test applies to Brent (the root is bracketed in sigma to xtol). Otherwise status 3."
Basis: IV error is approximately price residual / vega. An absolute price tolerance gives no IV accuracy where
price is comparable to tol.

R6 - CONTRACT 3.1 (bs_price put branch) - CHANGE - lane BUILD-A
Required text (append to 3.1): "Calls and puts are each computed directly:
call = S e^{-qT} N(d1) - K e^{-rT} N(d2), put = K e^{-rT} N(-d2) - S e^{-qT} N(-d1), with N = scipy.special.ndtr
evaluated at the signed argument. Never compute a put from the call via parity, and never use 1 - N(x)."
Rationale: a deep OTM put derived by parity is a difference of numbers about 40 apart that should leave about 1e-9,
which is catastrophic cancellation. Together with R5, this quietly fails the 1e-6 round-trip for OTM puts. The
parity check in section 12 still applies, as a test of the two direct branches against each other.

R7 - CONTRACT 2.3, 3.4, 9 (status codes, bounds, NaN vs raise) - ACCEPT
Codes 0..4 and the evaluation order 4, then 2, then solve are sound. Code 4 is a strict refinement of the plan's
"failed", which it is right to separate: bad input versus no root. IV_MIN = 1e-4, IV_MAX = 5.0 and the absolute
BOUND_EPS = 1e-10 are acceptable. Under R5, BOUND_EPS also guarantees a positive denominator. The rules
"never raise for data, NaN plus status" and "raise only for non-broadcastable shapes" are the correct split
between data errors and programming errors.
Non-binding note for QA: on the clean chain, rows with price <= 1e-10 become status 2. Hand estimate: about 9 of
the roughly 264 OTM rows at T = 1/12 (puts K/S <= 0.65, calls K/S >= 1.275), and fewer at 2/12. That leaves the
90% anti-vacuity threshold of section 12 with little headroom on correct code. Confirm with:
`q = prepare_quotes(generate_chain(noise_bps=0, tick=0, min_price=0), mp); q.status.value_counts()`.

## Surface

R8 - CONTRACT 6.1, 6.3 (total variance, T > 0, w >= 0) - ACCEPT
Interpolating w = iv^2 T, not iv, is correct: calendar monotonicity is a statement about w. T_grid runs from the
minimum usable T, which is > 0, so sqrt(w/T) is safe. A floor of W_FLOOR = 0.0 is acceptable. A zero-floored node
can only arise in extrapolated regions, and R9-R11 label those.

R9 - CONTRACT 6.1, 6.3 (k_grid = union; per-maturity domain) - CHANGE - lane BUILD-B
Ruling on trimming to the intersection: REJECTED. Keep the union k_grid. Hand derivation on the DEFAULT noisy chain
(min_price = 0.05): at T = 1/12 the 90-strike put is about 0.057 (kept) and the 87.5 put is about 0.022 (dropped),
so the usable k range is about [-0.107, +0.093]. At T = 2 the 60-strike put is about 1.26 (kept), so the range is
about [-0.56, +0.29]. The intersection would cut every maturity down to about [-0.11, 0.09], an ATM sliver.
The union, without labelling, presents a short-dated region about 4x wider than its data as if it were a fitted
surface. Confirm with: `quotes[quotes.status <= 1].groupby('T').k.agg(['min','max'])`.
Required text (add to 6.1 Surface fields, after `K`, and to 6.3 after "Grid:"):
"  k_lo: np.ndarray       # (n_T,) per-row lower edge of the quoted domain
   k_hi: np.ndarray       # (n_T,) per-row upper edge of the quoted domain
   in_domain: np.ndarray  # (n_T, n_k) bool
 GOVERNING DEFINITION (stated once here; 6.4, 6.6, 7.1 and 12 point to it): for each usable maturity T_m (not in
 dropped_T), kmin_m and kmax_m are the min and max of k over its quotes with status in {0,1}. Then
 k_lo = np.interp(T_grid, T_m, kmin_m), k_hi = np.interp(T_grid, T_m, kmax_m), and
 in_domain[i, j] = (k_lo[i] <= k_grid[j] <= k_hi[i]). A node outside it is EXTRAPOLATED."
Section 12's "interior nodes (k within each maturity's quoted range)" means `surface.in_domain`.

R10 - CONTRACT 6.6 (term_structure in_domain) - CHANGE - lane BUILD-B
Problem: "in_domain = k_grid[0] <= k_i <= k_grid[-1]". Against a union grid, this is almost never False. Example:
the 0.8 S strike at T = 1/12 has k about -0.22, outside the quoted [-0.107, 0.093], yet it is flagged in_domain
True. That is a label that cannot fail, and it certifies extrapolation as reliable.
Required text (replaces that sentence): "in_domain (bool) = surface.k_lo[i] <= k_i <= surface.k_hi[i]
(governing definition 6.1 / R9)."

R11 - CONTRACT 6.4 (arbitrage_report scope, disclaimer, wording) - CHANGE - lane BUILD-B
Required text:
(a) Calendar: "the pair (i, j), (i+1, j) is checked iff in_domain[i, j] and in_domain[i+1, j]; n_checked = the
number of such pairs."
(b) Butterfly: "the triple (i, j), (i, j+1), (i, j+2) is checked iff all three nodes are in_domain;
n_checked = the number of such triples."
(c) DIAGNOSTIC_DISCLAIMER, exactly: "DIAGNOSTIC ONLY: these checks count violations at grid nodes inside the
quoted domain; they do not enforce or guarantee an arbitrage-free surface and say nothing about extrapolated
regions."
(d) Replace "(dimensionless, undiscounted call price convex in K <=> slope non-decreasing)" with "(dimensionless;
C is the present-value call price from bs_price, and convexity in K is unchanged by the positive factor e^{rT}, so
this is the forward-price butterfly condition)".
The dict keys, types, and the lines[1]/lines[2] formats are unchanged.
Rationale: with the full grid in scope, counts are dominated by RBF corner extrapolation (R9), so the clean-chain
"n_violations == 0" acceptance in section 12 can fail for a reason that says nothing about the fit, and a real
in-domain violation is diluted. The current disclaimer would overclaim once scope narrows, so it moves with the
scope. The current word "undiscounted" is factually wrong about what bs_price returns.

R12 - CONTRACT 12 (diagnostics acceptance) - CHANGE - lane QA
Required text (append to the calendar bullet of section 12): "Anti-vacuity: on the clean-chain surface, both
calendar and butterfly n_checked >= 0.25 * their full-grid maximum ((n_T-1)*n_k and n_T*(n_k-2)). The injected
calendar violation must be applied at a node (i+1, j) where in_domain[i, j] and in_domain[i+1, j] are both True,
and the test asserts the counted violation arises at that node."
Rationale: R11 narrows the scope, which creates a new vacuous pass (0/0 violations). A masked-out injection would
make the "can go red" proof meaningless (plan check 5).

R13 - CONTRACT 7.1 (term-structure traces) - CHANGE - lane BUILD-C
Required text (append to the "Term structures" bullet): "Points with in_domain False (6.6) are plotted as y = NaN
(a gap in the line), never as an extrapolated value. Trace names are unchanged."
Rationale: presentation materiality. A reader who did not build the tool would read a smooth 0.8 S line at
T = 1/12 as a market fact.

R14 - CONTRACT 7.1 (3D hover) - CHANGE (the hub may defer it, because it touches an exact string QA parses) - lane BUILD-C
Required text: "customdata shape (n_k, n_T, 6) = [K, T_days, expiry_label, iv_pct, k, domain_tag], where
domain_tag = "" if Surface.in_domain[i_T, j_k] else " (extrapolated)". hovertemplate EXACTLY
`Strike: %{customdata[0]:.2f}<br>Expiry: %{customdata[2]} (%{customdata[1]:.0f}d)<br>IV: %{customdata[3]:.2f}%%{customdata[5]}<extra></extra>`.
The Market quotes overlay uses domain_tag = ""."
Default if deferred: R13 alone is in force, and the 3D corners stay unlabelled. Record the deferral in
REVIEW_B.md as an open presentation exception, not a closed one.

R15 - CONTRACT 6.3 (RBF scaling, smoothing) - ACCEPT
Min-max scaling of T and k to [0,1] from the usable-quote ranges meets the plan's "comparable weight" (plan 4).
The same scaler must be applied inside _w_fn, which is implied by 6.1 and is checked in REVIEW-B. Thin-plate kernel
and smoothing = 1e-6 are accepted. On the clean chain, near-interpolation is what the 0.01 surface-vs-truth bound
needs. OPINION (no citable basis, not binding): on the noisy default chain, tick rounding in the wings will show as
in-domain butterfly counts at smoothing 1e-6. Raising it is a v2 decision that needs measured evidence, not a
v1 change.

R16 - CONTRACT 4.1 (synthetic truth claim) - CHANGE (text and docstring only; no change to any value) - lane BUILD-A (ORACLE and QA may assert it)
The claim is TRUE but unstated. Required text (replaces the sentence "theta is increasing ... default domain"):
"Arbitrage-freeness of the truth (SSVI, Gatheral and Jacquier 2014): with phi(theta) = phi constant, the
calendar-spread condition requires d(theta)/dT >= 0, which holds because theta = T*atm_vol^2 with atm_vol > 0 and
non-decreasing, and 0 <= d(theta*phi)/d(theta) = phi <= (1/rho^2)(1 + sqrt(1-rho^2)) phi, which is
1.5 <= 5.25 at rho = -0.7. The sufficient butterfly conditions are theta*phi*(1+|rho|) < 4 and
theta*phi^2*(1+|rho|) <= 4. The second binds at theta <= 4/(phi^2 (1+|rho|)) = 1.046, i.e. T <= about 18 years
(atm_vol <= 0.24). At the default maximum T = 2, theta = 0.1076: 0.274 < 4 and 0.412 <= 4. At-the-money,
w(0, T) = theta(T)."
Hand check: atm_vol(2) = 0.18 + 0.06(1 - e^-2) = 0.2319, so theta(2) = 2(0.2319)^2 = 0.1076.

R17 - CONTRACT 1.2, 7.1 (units, hover) - ACCEPT
Stored IV is decimal and percent appears only in display. z = 100*iv transposed to [j_k, i_T], the
"Implied volatility (%)" title, and customdata iv_pct are consistent. Basis: CONTRACT 1.2 states this convention
once. Non-binding wording note: 1.2's "undiscounted cash" for `price` means the premium as quoted (a present value),
and must not be read as license to discount or forward-value it.

R18 - CONTRACT 1.2, 6.3 (ACT/365, linear T grid from min to max usable T) - ACCEPT
Day-granularity ACT/365 is adequate for v1. 5.3's min_days = 7 keeps T > 0.019 on the ticker path.

R19 - CONTRACT 7.2, 13-R8 (plotlyjs = "cdn" default) - ACCEPT
Basis: plan section 5 states cdn as the default with an inline flag. The user ruling "standalone HTML" means
no server (board 12:49), not offline. --offline covers the offline case.

R20 - CONTRACT 6.4, 13-R5 (butterfly proxy and tolerances) - ACCEPT (scope fixed by R11)
Static butterfly no-arbitrage is C convex in K at fixed T (Breeden-Litzenberger: density = e^{rT} d2C/dK2 >= 0).
Slope differences on the actual non-uniform K[i, :] are the correct discrete form, and the grid proxy is
equivalent in the limit to Durrleman's g(k) >= 0. The calendar test, dw < -1e-6 at fixed k, is correct per R1.
The tolerances 1e-6 (w) and 1e-8 (slope difference) sit well above float64 pricing error. Keeping no boolean
verdict key is correct (LESSONS green-marker rule). The vertical-spread bound -e^{-rT} <= dC/dK <= 0 is not
checked. That is an accepted v1 gap, to be named in the README, not a change.

R21 - CONTRACT 6.3 spline / 6.4 (BUILD-B finding relayed by hub: spline 56/4680 butterfly violations on the clean chain, all at k-index 0..2, k about -0.56..-0.54; rbf 0) - CHANGE - lane BUILD-B
Ruling: do NOT switch the default K_GRID_MODE to intersection. Keep the union k_grid (R9), and fix the diagnostic
scope with R9 + R11. Basis: the violating nodes are extrapolated, not fitted. By hand on the clean chain,
T = 1/12 has its lowest usable put near K/S = 0.675, so k is about -0.40. Prices below that strike are
<= 1e-10 (status 2, R7). So k = -0.56 at short T lies outside [k_lo, k_hi]. Flat clamping plus PCHIP in T makes
the kink BUILD-B describes, and that kink sits entirely in extrapolated territory. Trimming the grid to the
intersection would hide it by deleting the region. On the default noisy chain it would also collapse the grid to
about [-0.11, 0.09] (R9 derivation), which is a worse outcome than the defect it removes.
Required behaviour:
(1) The K_GRID_MODE default is "union". An "intersection" value may stay as a non-default internal option. It is
not a CLI flag and not used by main.
(2) Implement R9 (k_lo, k_hi, in_domain) and R11 (in-domain-only counts).
(3) Falsifiable prediction, which BUILD-B records in its run-log and QA re-checks: on the clean chain with
method="spline", the R11 in-domain butterfly n_violations == 0. If that count is > 0, the spline fit has a real
in-domain defect. Report it as a finding. Do not mask it.
(4) Do not tune the spline. The full-grid figure of 56/4680 is an exception to report: BUILD-B states it in its
run-log as "56 extrapolated-node butterfly violations, excluded by R11 scope". It is not absorbed silently.
4680 = 60 * 78 confirms the pre-R11 full-grid n_checked of n_T*(n_k-2).

---------------------------------------------------------------------------------------------------
Disclosure / IP: none. Synthetic data only, no employer identifiers, GL codes or attributable error magnitudes.
CHANGE: R2, R3, R6, R9, R10, R11, R12, R13, R14, R16, R21 (R5 superseded by lead R-1, guard sentence binding)
