project: Volitility-Model
role: pipeline-builder
task: BUILD-B lane - data_io.py and surface.py to CONTRACT.md v1.0 plus REVIEW_A fix round (R2, R9, R10, R11, R21)
deliverables: <REPO>/data_io.py, <REPO>/surface.py
status: delivered
lesson: Before writing a guarded-import stub, ls the repo for the upstream module (bs_pricing.py already existed, plain import used). A smoke check that term structure differs from k=0 is weak: assert k_i == ln(K/F(T_i)) and varies across T. A narrowed-scope diagnostic needs two anti-vacuity injections: one at an in-domain node (must count) and one at an extrapolated node (must not count).
domain: Volitility-Model - R21 recorded: 56 extrapolated-node butterfly violations (spline, clean chain, full grid 56/4680), excluded by R11 scope. In-domain R11 counts on clean chain: spline butterfly 0/4348, rbf 0/4348, calendar 0/4389 both - REVIEW_A prediction (spline in-domain == 0) HELD. Noisy chain in-domain: rbf butterfly 1/3912, spline 8/3912 (tick rounding in wings, R15 opinion), calendar 0/3953.
friction: first flow-board --show used backslash path via Bash and failed (known from own agent-memory); redone with forward slashes. SendMessage unavailable so no hub notice sent from this lane. REVIEW_A.md landed after first delivery; applied via hub relay. One own-test error: asserted K=80 out-of-domain on the clean chain where T=1/12 quotes reach k=-0.395 (test wrong, code right).
assumptions: sigma_true unparseable cell -> NaN; prepare_quotes raises ValueError on schema violations beyond missing columns; chain.attrs["rows_read"]; forward() returns float for scalar; fetch_yfinance_chain untested (no network); spline clamps (T,k) to grid ranges.
stubs_left: none
attestation: edited only data_io.py and surface.py (plus this run-log); did not edit other lanes' files
