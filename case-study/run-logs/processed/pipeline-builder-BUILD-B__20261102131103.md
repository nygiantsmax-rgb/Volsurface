project: Volitility-Model
role: pipeline-builder
task: BUILD-B lane - data_io.py and surface.py to CONTRACT.md v1.0 plus REVIEW_A fix round (R2, R9, R10, R11, R21)
deliverables: <REPO>/data_io.py, <REPO>/surface.py
status: delivered
r21_1: K_GRID_MODE default is "union"; "intersection" remains only as a non-default internal option in surface.py (module constant, not a CLI flag, not used by main)
r21_2: R9 implemented as written incl. governing definition; Surface fields k_lo (n_T,), k_hi (n_T,), in_domain (n_T, n_k) bool, placed after K and before method; names unchanged
r21_3: R10 term_structure in_domain = surface.k_lo[i] <= k_i <= surface.k_hi[i]; R11 a-d implemented with in-domain-only n_checked and the exact R11(c) disclaimer
r21_4: falsifiable prediction HELD: clean chain, method=spline, in-domain butterfly n_violations = 0 of 4348 (rbf also 0/4348; calendar 0/4389 both)
r21_5: 56 extrapolated-node butterfly violations, excluded by R11 scope (spline, clean chain, full grid 56/4680). Spline not tuned.
n_checked_before_after_clean: calendar 4720 -> 4389; butterfly 4680 -> 4348 (60x80 grid)
noisy_chain_in_domain: rbf butterfly 1/3912, spline butterfly 8/3912, calendar 0/3953 both (noisy full-grid butterfly was 1 and 67)
r2: fetch_yfinance_chain q via _choose_q range guard [0, 0.25], Q_MAX constant; untested live (no network)
self_checks: python -W error data_io.py rc=0; python -W error surface.py rc=0 (PowerShell-independent direct exit codes read via echo $? without a pipe)
lesson: A narrowed-scope diagnostic needs two anti-vacuity injections: one at an in-domain node (must count) and one at an extrapolated node (must not count). Also ls the repo for the upstream module before writing a stub; here bs_pricing.py existed so a plain import was right. A smoke check that term structure differs from k=0 is weak: assert k_i == ln(K/F(T_i)) and varies across T.
domain: Volitility-Model - spline full-grid butterfly violations sit at extrapolated left-edge nodes (k about -0.56..-0.54 at short T) from flat clamp plus PCHIP in T; R11 scope excludes them, in-domain count is 0 on clean chain.
friction: first flow-board --show used backslash path via Bash and failed (known from own agent-memory); redone with forward slashes. SendMessage unavailable so no hub notice sent from this lane. REVIEW_A.md landed after first delivery; applied via hub relay. One own-test error: asserted K=80 out-of-domain on the clean chain where T=1/12 quotes reach k=-0.395 (test wrong, code right). flow-lead supplement arrived after fix was done; confirmed items rather than redoing.
assumptions: sigma_true unparseable cell -> NaN; prepare_quotes raises ValueError on schema violations beyond missing columns; chain.attrs["rows_read"]; forward() returns float for scalar; spline clamps (T,k) to grid ranges.
stubs_left: none
attestation: edited only data_io.py and surface.py (plus this run-log); did not edit other lanes' files
