"""selftest.py - content-level verification of the Volitility-Model build (QA lane).

Written against .claude/CONTRACT.md (+ .claude/REVIEW_A.md, binding). Plain asserts, no pytest.
Run:   python selftest.py                 -> runs every check, exit 0 only if ALL pass, else exit 1
       python selftest.py --only NAME     -> run checks whose name contains NAME
       python selftest.py --hashes        -> print sha256 of every source file under test
       python selftest.py --mutation-proof-> prove the suite can go red (mutations on a TEMP COPY only)

The code under test is located via env SELFTEST_ROOT (default: this file's directory). The mutation
proof copies the sources to a temp tree, injects one defect per copy, sets SELFTEST_ROOT to the copy
and expects a non-zero exit AND the named check to be among the FAILED lines. Live files are never
written; their sha256 is asserted unchanged at the end of the proof.

Independence: every reference value here is re-derived from the CONTRACT/textbook with math.erfc and
numpy, never by calling the module that is being checked (no circular oracle).
"""
import datetime
import hashlib
import io
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
import warnings
import contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.environ.get("SELFTEST_ROOT", HERE))
SOURCES = ["bs_pricing.py", "synthetic.py", "data_io.py", "surface.py", "viz.py", "main.py",
           "requirements.txt"]
MODULES = ["bs_pricing", "synthetic", "data_io", "surface", "viz"]

sys.dont_write_bytecode = True          # stale .pyc must never invert a result
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path.insert(0, ROOT)

import numpy as np                      # noqa: E402
import pandas as pd                     # noqa: E402

warnings.simplefilter("error", RuntimeWarning)   # any numpy warning anywhere is a failure

CHECKS = []
NOTES = []      # report-only measurements printed at the end (never asserted)


def check(fn):
    CHECKS.append(fn)
    return fn


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def ensure(cond, msg):
    if not cond:
        raise AssertionError(msg)


# ----------------------------------------------------------------------------------------------
# Independent references (CONTRACT section 3 / textbook; no import of the code under test)
# ----------------------------------------------------------------------------------------------
def ncdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def ref_price(S, K, T, r, q, sig, is_call):
    d1 = (math.log(S / K) + (r - q + 0.5 * sig * sig) * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    if is_call:
        return S * math.exp(-q * T) * ncdf(d1) - K * math.exp(-r * T) * ncdf(d2)
    return K * math.exp(-r * T) * ncdf(-d2) - S * math.exp(-q * T) * ncdf(-d1)


def ref_true_vol(k, T):
    """CONTRACT 4.1 reimplemented from the prose."""
    atm = 0.18 + 0.06 * (1.0 - math.exp(-T / 1.0))
    theta = T * atm ** 2
    rho, phi = -0.7, 1.5
    w = 0.5 * theta * (1.0 + rho * phi * k + math.sqrt((phi * k + rho) ** 2 + 1.0 - rho ** 2))
    return math.sqrt(w / T)


def imp():
    import importlib
    mods = []
    for name in MODULES:
        try:
            m = importlib.import_module(name)
            ensure(os.path.abspath(m.__file__).startswith(ROOT), "module %s not loaded from %s" % (name, ROOT))
        except ImportError as e:      # a missing/broken module is a finding; checks needing it go red on use
            m = _Missing(name, e)
        mods.append(m)
    return tuple(mods)


class _Missing(object):
    """Stand-in for a module that failed to import: any attribute use raises (so dependent checks go RED)."""
    def __init__(self, name, err):
        self._n, self._e = name, err

    def __getattr__(self, a):
        raise AssertionError("module %s not importable (%s); needed for %s" % (self._n, self._e, a))


_CACHE = {}


def clean_setup():
    """Clean (noise-free, un-ticked, nothing dropped) chain + params + quotes."""
    if "clean" not in _CACHE:
        bsp, syn, dio, srf, viz = imp()
        chain = syn.generate_chain(noise_bps=0.0, tick=0.0, min_price=0.0)
        params = dio.MarketParams(S=syn.DEFAULT_S, r=syn.DEFAULT_R, q=syn.DEFAULT_Q)
        quotes = srf.prepare_quotes(chain, params)
        _CACHE["clean"] = (chain, params, quotes)
    return _CACHE["clean"]


def clean_surface(method):
    key = "surf_" + method
    if key not in _CACHE:
        bsp, syn, dio, srf, viz = imp()
        chain, params, quotes = clean_setup()
        _CACHE[key] = srf.build_surface(quotes, params, method=method)
    return _CACHE[key]


def noisy_setup():
    if "noisy" not in _CACHE:
        bsp, syn, dio, srf, viz = imp()
        chain = syn.generate_chain()
        params = dio.MarketParams(S=syn.DEFAULT_S, r=syn.DEFAULT_R, q=syn.DEFAULT_Q)
        quotes = srf.prepare_quotes(chain, params)
        _CACHE["noisy"] = (chain, params, quotes)
    return _CACHE["noisy"]


# ----------------------------------------------------------------------------------------------
# 0. Hygiene: files present, no stubs left, import-safe, ASCII, real __main__ guards
# ----------------------------------------------------------------------------------------------
@check
def c00_files_present_no_stub_markers():
    for f in SOURCES:
        ensure(os.path.isfile(os.path.join(ROOT, f)), "missing source file %s (CONTRACT 1.1)" % f)
    for f in SOURCES:
        txt = open(os.path.join(ROOT, f), encoding="utf-8").read()
        ensure("STUB per CONTRACT.md" not in txt, "%s still contains a 'STUB per CONTRACT.md' marker (CONTRACT 11)" % f)
    req = open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8").read().lower()
    for lib in ("numpy", "scipy", "pandas", "plotly"):
        ensure(lib in req, "requirements.txt lacks %s" % lib)


@check
def c00_import_safe_no_output():
    for m in MODULES:
        p = subprocess.run([sys.executable, "-c", "import %s" % m], cwd=ROOT, capture_output=True,
                           env=dict(os.environ, PYTHONPATH=ROOT))
        ensure(p.returncode == 0, "import %s failed rc=%d stderr=%s" % (m, p.returncode, p.stderr[-300:]))
        ensure(p.stdout == b"", "import %s printed to stdout (CONTRACT 1.1 import-safe): %r" % (m, p.stdout[:100]))
        ensure(b"STUB" not in p.stderr, "import %s emitted a STUB warning" % m)


@check
def c00_main_has_real_main_guard():
    txt = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    ensure(re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:\s*\n\s*sys\.exit\(\s*main\(\)\s*\)', txt),
           "main.py lacks 'if __name__ == \"__main__\": sys.exit(main())' (CONTRACT 8)")


@check
def c00_status_constants_pinned():
    bsp = imp()[0]
    ensure((bsp.IV_STATUS_NEWTON, bsp.IV_STATUS_BRENT, bsp.IV_STATUS_OUT_OF_BOUNDS, bsp.IV_STATUS_FAILED,
            bsp.IV_STATUS_INVALID_INPUT) == (0, 1, 2, 3, 4), "status int codes differ from CONTRACT 2.3")
    ensure(dict(bsp.IV_STATUS_NAMES) == {0: "newton", 1: "brent", 2: "out_of_bounds", 3: "failed",
                                         4: "invalid_input"}, "IV_STATUS_NAMES differs from CONTRACT 2.3")
    ensure((bsp.IV_MIN, bsp.IV_MAX, bsp.BOUND_EPS) == (1e-4, 5.0, 1e-10), "IV_MIN/IV_MAX/BOUND_EPS differ from 2.3")


# ----------------------------------------------------------------------------------------------
# 1. BS sanity (plan check 1)
# ----------------------------------------------------------------------------------------------
@check
def c01_bs_hand_value_and_independent_reference():
    bsp = imp()[0]
    # hand value S=K=100,T=1,r=.05,q=.02,sig=.2 : d1=.25,d2=.05 -> C=9.2271 (derived with erfc, see ref_price)
    c = float(bsp.bs_price(100.0, 100.0, 1.0, 0.05, 0.02, 0.2, True))
    ensure(abs(c - ref_price(100, 100, 1, 0.05, 0.02, 0.2, True)) < 1e-10, "call %r != independent reference" % c)
    ensure(abs(c - 9.2271) < 5e-4, "call %r not near hand value 9.2271" % c)
    p = float(bsp.bs_price(100.0, 100.0, 1.0, 0.05, 0.02, 0.2, False))
    ensure(abs(p - ref_price(100, 100, 1, 0.05, 0.02, 0.2, False)) < 1e-10, "put %r != independent reference" % p)
    ensure(0.0 < p < c, "put should be cheaper than call here (r>q): C=%r P=%r" % (c, p))


@check
def c01_put_call_parity_random_grid():
    bsp = imp()[0]
    rng = np.random.default_rng(12345)
    n = 400
    S = rng.uniform(20, 300, n)
    K = S * rng.uniform(0.5, 1.6, n)
    T = rng.uniform(0.02, 3.0, n)
    r = rng.uniform(-0.01, 0.08, n)
    q = rng.uniform(0.0, 0.06, n)
    sig = rng.uniform(0.05, 1.2, n)
    C = bsp.bs_price(S, K, T, r, q, sig, True)
    P = bsp.bs_price(S, K, T, r, q, sig, False)
    ensure(C.shape == (n,), "shape %r" % (C.shape,))
    err = np.abs(C - P - (S * np.exp(-q * T) - K * np.exp(-r * T)))
    ensure(np.isfinite(err).all() and err.max() <= 1e-10, "parity max err %.3e > 1e-10" % err.max())
    ref = np.array([ref_price(S[i], K[i], T[i], r[i], q[i], sig[i], True) for i in range(n)])
    ensure(np.abs(C - ref).max() <= 1e-9, "call vs independent ref max diff %.3e" % np.abs(C - ref).max())
    # anti-vacuity: the grid must actually span regimes (some ITM some OTM, nonzero prices)
    ensure((K > S).any() and (K < S).any() and (C > 1e-6).sum() > n // 2, "grid degenerate")


@check
def c01_vega_and_bounds():
    bsp = imp()[0]
    S, K, T, r, q, sig = 100.0, 105.0, 0.75, 0.03, 0.01, 0.27
    h = 1e-5
    fd = (ref_price(S, K, T, r, q, sig + h, True) - ref_price(S, K, T, r, q, sig - h, True)) / (2 * h)
    v = float(bsp.bs_vega(S, K, T, r, q, sig))
    ensure(abs(v - fd) < 1e-6, "vega %r vs finite diff %r (per 1.00 sigma, CONTRACT 3.2)" % (v, fd))
    lo, up = bsp.price_bounds(S, K, T, r, q, True)
    ensure(abs(float(lo) - max(S * math.exp(-q * T) - K * math.exp(-r * T), 0.0)) < 1e-12, "call lower bound")
    ensure(abs(float(up) - S * math.exp(-q * T)) < 1e-12, "call upper bound")
    lo, up = bsp.price_bounds(S, K, T, r, q, False)
    ensure(abs(float(lo) - max(K * math.exp(-r * T) - S * math.exp(-q * T), 0.0)) < 1e-12, "put lower bound")
    ensure(abs(float(up) - K * math.exp(-r * T)) < 1e-12, "put upper bound")
    nanlo, nanup = bsp.price_bounds(-1.0, K, T, r, q, True)
    ensure(np.isnan(nanlo) and np.isnan(nanup), "S<=0 must give NaN bounds")


@check
def c01_degenerate_pricing_rules():
    bsp = imp()[0]
    # T = 0 -> discounted intrinsic with T clipped to 0; sigma <= 0 likewise
    ensure(abs(float(bsp.bs_price(110.0, 100.0, 0.0, 0.05, 0.02, 0.2, True)) - 10.0) < 1e-12, "T=0 call intrinsic")
    ensure(abs(float(bsp.bs_price(90.0, 100.0, 0.0, 0.05, 0.02, 0.2, False)) - 10.0) < 1e-12, "T=0 put intrinsic")
    v = float(bsp.bs_price(100.0, 90.0, 1.0, 0.05, 0.02, 0.0, True))
    ensure(abs(v - max(100 * math.exp(-0.02) - 90 * math.exp(-0.05), 0)) < 1e-12, "sigma=0 -> discounted intrinsic")
    ensure(np.isnan(bsp.bs_price(100.0, 100.0, 1.0, 0.05, 0.02, -0.1, True)), "sigma<0 must be NaN")
    ensure(np.isnan(bsp.bs_price(-5.0, 100.0, 1.0, 0.05, 0.02, 0.2, True)), "S<=0 must be NaN")
    ensure(np.isnan(bsp.bs_price(100.0, 0.0, 1.0, 0.05, 0.02, 0.2, True)), "K<=0 must be NaN")
    ensure(np.isnan(bsp.bs_price(np.nan, 100.0, 1.0, 0.05, 0.02, 0.2, True)), "NaN in must be NaN out")
    ensure(float(bsp.bs_vega(100.0, 100.0, 0.0, 0.05, 0.02, 0.2)) == 0.0, "vega in degenerate region must be 0.0")
    try:
        bsp.bs_price(np.ones(3), np.ones(4), 1.0, 0.0, 0.0, 0.2, True)
    except ValueError:
        pass
    else:
        raise AssertionError("non-broadcastable shapes must raise ValueError (the only raise)")


# ----------------------------------------------------------------------------------------------
# 2. IV round trip (plan check 2) + control totals 2 and 4
# ----------------------------------------------------------------------------------------------
@check
def c02_iv_round_trip_clean_chain():
    bsp, syn, dio, srf, viz = imp()
    chain, params, quotes = clean_setup()
    ok = quotes["status"].isin([0, 1])
    n_ok = int(ok.sum())
    ensure(n_ok >= 0.9 * len(quotes), "only %d/%d quotes solved (<90%%, CONTRACT 12 anti-vacuity)" % (n_ok, len(quotes)))
    ensure(len(quotes) > 50, "quotes frame implausibly small: %d" % len(quotes))
    ensure("sigma_true" in quotes.columns, "sigma_true must be carried through (2.2)")
    err = (quotes.loc[ok, "iv"] - quotes.loc[ok, "sigma_true"]).abs()
    ensure(len(err) == n_ok and n_ok > 0, "nothing compared")
    ensure(err.max() <= 1e-6, "clean round-trip max |iv - sigma_true| = %.3e > 1e-6" % err.max())
    # R-1 / section 12: the deep-OTM rows (sub-1e-6 prices, where price-only acceptance returns garbage)
    # must be INCLUDED in the 1e-6 round trip. Anti-vacuity: they must exist and be solved.
    deep = ok & (quotes["price"] < 1e-6)
    n_deep = int(deep.sum())
    NOTES.append("clean chain status counts %r ; status in {0,1} fraction %.4f (%d/%d) ; deep-OTM (price<1e-6) solved rows %d" % (
        {int(k): int(v) for k, v in quotes["status"].value_counts().sort_index().items()}, n_ok / len(quotes), n_ok, len(quotes), n_deep))
    ensure(n_deep >= 1, "anti-vacuity: no deep-OTM (price < 1e-6) rows reached the solver; the R-1 check would be vacuous")
    err_deep = (quotes.loc[deep, "iv"] - quotes.loc[deep, "sigma_true"]).abs()
    ensure(err_deep.max() <= 1e-6, "deep-OTM rows (n=%d, price<1e-6): max |iv - sigma_true| = %.3e > 1e-6 (R-1: price-only acceptance?)" % (n_deep, err_deep.max()))
    # w identity
    w_err =(quotes.loc[ok, "w"] - quotes.loc[ok, "iv"] ** 2 * quotes.loc[ok, "T"]).abs().max()
    ensure(w_err <= 1e-14, "w != iv^2*T (%.2e)" % w_err)


@check
def c02_iv_noisy_default_chain_tolerance():
    chain, params, quotes = noisy_setup()
    ok = quotes["status"].isin([0, 1])
    ensure(ok.sum() > 0.5 * len(quotes), "too few solved quotes in noisy chain: %d/%d" % (ok.sum(), len(quotes)))
    err = (quotes.loc[ok, "iv"] - quotes.loc[ok, "sigma_true"]).abs()
    ensure(err.max() <= 0.02, "noisy max |iv - sigma_true| = %.4f > 0.02 (CONTRACT 12)" % err.max())


@check
def c02_control_totals_quotes_and_status():
    bsp, syn, dio, srf, viz = imp()
    for name, (chain, params, quotes) in (("clean", clean_setup()), ("noisy", noisy_setup())):
        F = params.S * np.exp((params.r - params.q) * chain["T"].to_numpy())
        k = np.log(chain["strike"].to_numpy() / F)
        isp = chain["type"].to_numpy() == "P"
        isc = chain["type"].to_numpy() == "C"
        expect = int(((isp & (k < 0)) | (isc & (k >= 0))).sum())      # independent recompute, CONTRACT 10.2
        ensure(len(quotes) == expect, "%s: len(quotes)=%d != independent OTM count %d" % (name, len(quotes), expect))
        counts = quotes["status"].value_counts()
        ensure(int(counts.sum()) == len(quotes) and set(counts.index) <= {0, 1, 2, 3, 4}, "status sum / values")
        fin = np.isfinite(quotes["iv"].to_numpy())
        ensure((fin == quotes["status"].isin([0, 1]).to_numpy()).all(), "%s: iv finite <=> status in {0,1} violated (10.4)" % name)
        ensure((np.isnan(quotes["w"].to_numpy()) == ~fin).all(), "w NaN iff iv NaN violated")
        ensure(list(quotes.columns[:9]) == ["strike", "T", "type", "price", "F", "k", "iv", "w", "status"],
               "quotes columns/order differ from 2.2: %r" % list(quotes.columns))
        ensure(quotes["status"].dtype == np.int8, "status dtype %r != int8" % quotes["status"].dtype)
        ensure(np.allclose(quotes["F"], params.S * np.exp((params.r - params.q) * quotes["T"]), rtol=1e-13, atol=0), "F column")
        ensure(np.allclose(quotes["k"], np.log(quotes["strike"] / quotes["F"]), rtol=0, atol=1e-13), "k column")
        key = list(zip(quotes["T"], quotes["strike"]))
        ensure(key == sorted(key) and (quotes.index == range(len(quotes))).all(), "sorted by (T,strike), RangeIndex")
        # side rule on every row
        ensure(((quotes["type"] == "P") == (quotes["k"] < 0)).all(), "OTM side rule broken on a row (2.2)")


@check
def c02_otm_boundary_k_equals_zero_goes_to_call():
    bsp, syn, dio, srf, viz = imp()
    params = dio.MarketParams(S=100.0, r=0.04, q=0.015)
    T = 0.5
    F = float(params.forward(T))
    rows = []
    for K in (F, F * 0.9, F * 1.1):
        for typ in ("C", "P"):
            sig = 0.2
            rows.append((K, T, typ, ref_price(100.0, K, T, 0.04, 0.015, sig, typ == "C")))
    chain = pd.DataFrame(rows, columns=["strike", "T", "type", "price"])
    q = srf.prepare_quotes(chain, params)
    ensure(len(q) == 3, "expected 3 OTM rows (P@0.9F, C@F, C@1.1F), got %d" % len(q))
    at = q[np.isclose(q["strike"], F)]
    ensure(len(at) == 1 and at["type"].iloc[0] == "C" and abs(at["k"].iloc[0]) < 1e-15, "K==F must keep the CALL only (R2)")
    ensure(set(q.loc[q["k"] < 0, "type"]) == {"P"} and set(q.loc[q["k"] > 0, "type"]) == {"C"}, "sides")
    ensure(q["status"].isin([0, 1]).all() and np.allclose(q["iv"], 0.2, atol=1e-6), "iv should recover 0.2: %r" % q["iv"].tolist())


@check
def c02_prepare_quotes_boundaries():
    bsp, syn, dio, srf, viz = imp()
    params = dio.MarketParams(S=100.0, r=0.04, q=0.015)
    # single row chain
    one = pd.DataFrame([(110.0, 0.5, "C", ref_price(100, 110, 0.5, 0.04, 0.015, 0.25, True))],
                       columns=["strike", "T", "type", "price"])
    q1 = srf.prepare_quotes(one, params)
    ensure(len(q1) == 1 and q1["status"].iloc[0] in (0, 1), "single-row chain")
    # ITM-only chain -> zero quote rows, no raise
    itm = pd.DataFrame([(90.0, 0.5, "C", 12.0)], columns=["strike", "T", "type", "price"])
    q0 = srf.prepare_quotes(itm, params)
    ensure(len(q0) == 0, "ITM-only chain must yield empty quotes, got %d" % len(q0))
    # bad quotes are KEPT with status >= 2 and iv NaN; never raise
    bad = pd.DataFrame([(110.0, 0.5, "C", 0.0001), (110.0, 0.5, "C", 999.0), (120.0, 0.5, "C", 3.0)][:2] +
                       [(120.0, 0.5, "C", 3.0)], columns=["strike", "T", "type", "price"])
    bad.loc[1, "strike"] = 111.0
    bad.loc[0, "price"] = 1e-14          # below lower bound + eps / no time value
    qb = srf.prepare_quotes(bad, params)
    ensure(len(qb) == 3, "failed solves must be KEPT (len=%d)" % len(qb))
    st = qb.set_index("strike")["status"]
    ensure(st[110.0] >= 2 and st[111.0] == 2, "below-bound / above-upper-bound statuses: %r" % st.to_dict())
    ensure(np.isnan(qb.loc[qb["status"] >= 2, "iv"]).all(), "iv must be NaN when status>=2")
    # missing columns -> ValueError, nothing else
    try:
        srf.prepare_quotes(pd.DataFrame({"strike": [1.0]}), params)
    except ValueError:
        pass
    else:
        raise AssertionError("missing columns must raise ValueError (CONTRACT 6.2)")


# ----------------------------------------------------------------------------------------------
# 3. Edge cases (plan check 3)
# ----------------------------------------------------------------------------------------------
@check
def c03_edge_below_intrinsic_nan_out_of_bounds():
    bsp = imp()[0]
    S, K, T, r, q = 100.0, 80.0, 1.0, 0.05, 0.02
    lo = max(S * math.exp(-q * T) - K * math.exp(-r * T), 0.0)
    iv, st = bsp.implied_vol(lo - 1.0, S, K, T, r, q, True)
    ensure(np.isnan(iv) and int(st) == 2, "below-intrinsic -> NaN/status 2, got %r/%r" % (iv, st))
    iv, st = bsp.implied_vol(lo, S, K, T, r, q, True)       # exactly at the lower bound: no time value
    ensure(np.isnan(iv) and int(st) == 2, "price == lower bound -> NaN/status 2 (2.3), got %r/%r" % (iv, st))
    iv, st = bsp.implied_vol(S * math.exp(-q * T) + 1.0, S, K, T, r, q, True)    # above upper bound
    ensure(np.isnan(iv) and int(st) == 2, "above upper bound -> status 2, got %r/%r" % (iv, st))
    ok = ref_price(S, K, T, r, q, 0.3, True)
    iv, st = bsp.implied_vol(ok, S, K, T, r, q, True)
    ensure(int(st) in (0, 1) and abs(float(iv) - 0.3) < 1e-6, "in-bounds quote must solve: %r/%r" % (iv, st))


@check
def c03_edge_invalid_input_status4_and_order():
    bsp = imp()[0]
    cases = [(5.0, 100.0, 100.0, 0.0, 0.0, 0.0), (5.0, 100.0, 100.0, -1.0, 0.0, 0.0), (np.nan, 100.0, 100.0, 1.0, 0.0, 0.0),
             (0.0, 100.0, 100.0, 1.0, 0.0, 0.0), (-3.0, 100.0, 100.0, 1.0, 0.0, 0.0), (5.0, 0.0, 100.0, 1.0, 0.0, 0.0),
             (5.0, 100.0, -1.0, 1.0, 0.0, 0.0), (5.0, 100.0, 100.0, 1.0, np.inf, 0.0), (5.0, 100.0, 100.0, 1.0, 0.0, np.nan)]
    for (p, S, K, T, r, q) in cases:
        iv, st = bsp.implied_vol(p, S, K, T, r, q, True)
        ensure(np.isnan(iv) and int(st) == 4, "invalid input %r -> status 4, got %r/%r" % ((p, S, K, T, r, q), iv, st))
    # order: invalid (4) beats out-of-bounds (2): T<=0 AND price below bound
    iv, st = bsp.implied_vol(-1.0, 100.0, 100.0, 0.0, 0.0, 0.0, True)
    ensure(int(st) == 4, "evaluation order 4 before 2 violated, status=%r" % st)
    # vectorised: dtype/shape contract, no raise on a mixed batch
    iv, st = bsp.implied_vol(np.array([5.0, np.nan, 1e-14]), 100.0, 100.0, 1.0, 0.0, 0.0, True)
    ensure(iv.shape == (3,) and st.shape == (3,) and st.dtype == np.int8 and iv.dtype == np.float64, "dtype/shape %r %r" % (iv.dtype, st.dtype))
    ensure(int(st[1]) == 4 and int(st[2]) >= 2 and np.isfinite(iv[0]), "mixed batch statuses %r" % st.tolist())


@check
def c03_edge_tiny_T_no_crash_no_warning():
    bsp = imp()[0]
    with warnings.catch_warnings():
        warnings.simplefilter("error")                   # ANY warning is a failure
        with np.errstate(all="raise"):                   # and any floating-point error inside the module
            p = bsp.bs_price(100.0, 100.0, 1e-8, 0.04, 0.01, 0.2, True)
            v = bsp.bs_vega(100.0, 100.0, 1e-8, 0.04, 0.01, 0.2)
            c = ref_price(100.0, 100.0, 1e-8, 0.04, 0.01, 0.2, True)
            ensure(abs(float(p) - c) < 1e-6, "T=1e-8 price %r vs ref %r" % (p, c))
            ensure(np.isfinite(float(v)) and float(v) >= 0.0, "vega finite >=0")
            iv, st = bsp.implied_vol(c, 100.0, 100.0, 1e-8, 0.04, 0.01, True)
            ensure(int(st) in (0, 1, 2, 3), "status in range")
            iv, st = bsp.implied_vol(np.array([0.5, 0.0004, 1e-9]), 100.0, np.array([100.0, 100.0, 150.0]), 1e-8, 0.0, 0.0, True)
            ensure(st.shape == (3,), "array T=1e-8 call")
            p0 = bsp.bs_price(np.array([100.0, 100.0]), 100.0, np.array([0.0, 1e-300]), 0.0, 0.0, 0.2, True)
            ensure(np.isfinite(p0).all(), "T=0 / T=1e-300 must not produce NaN or warn")


@check
def c03_edge_deep_otm_and_extreme_vol():
    bsp = imp()[0]
    S, T, r, q = 100.0, 0.25, 0.04, 0.015
    for K, is_call, sig in ((300.0, True, 0.5), (20.0, False, 0.5), (200.0, True, 0.3), (50.0, False, 0.25)):
        p = ref_price(S, K, T, r, q, sig, is_call)
        iv, st = bsp.implied_vol(p, S, K, T, r, q, is_call)       # must not raise or warn
        ensure(int(st) in (0, 1, 2, 3), "status %r" % st)
        if int(st) in (0, 1):
            ensure(abs(float(iv) - sig) <= 1e-6, "deep OTM K=%r: iv=%r != true %r (R-1: no price-only acceptance)" % (K, iv, sig))
        else:
            ensure(np.isnan(iv), "failed solve must be NaN")
    # high-vol bracket end: sigma 4.9 solves, true sigma 6 (> IV_MAX) must NOT yield a finite garbage root
    p_hi = ref_price(S, 100.0, 1.0, r, q, 4.9, True)
    iv, st = bsp.implied_vol(p_hi, S, 100.0, 1.0, r, q, True)
    ensure(int(st) in (0, 1) and abs(float(iv) - 4.9) < 1e-5, "sigma=4.9 should solve, got %r/%r" % (iv, st))
    p_big = ref_price(S, 100.0, 1.0, r, q, 6.0, True)
    iv, st = bsp.implied_vol(p_big, S, 100.0, 1.0, r, q, True)
    ensure(np.isnan(iv) and int(st) in (2, 3), "sigma above IV_MAX must be NaN with status 2/3, got %r/%r" % (iv, st))


# ----------------------------------------------------------------------------------------------
# synthetic.py / data_io.py (support; CONTRACT 4, 5)
# ----------------------------------------------------------------------------------------------
@check
def c10_true_vol_matches_ssvi_spec():
    bsp, syn, dio, srf, viz = imp()
    for T in (1 / 12, 0.5, 1.0, 2.0):
        for k in (-0.6, -0.2, 0.0, 0.15, 0.4):
            got = float(syn.true_vol(k, T))
            ensure(abs(got - ref_true_vol(k, T)) < 1e-12, "true_vol(%r,%r)=%r != spec %r" % (k, T, got, ref_true_vol(k, T)))
    ensure(np.isnan(syn.true_vol(0.0, 0.0)) and np.isnan(syn.true_vol(0.0, -1.0)), "T<=0 -> NaN (CONTRACT 4.1/9)")
    out = syn.true_vol(np.array([[-0.1], [0.1]]), np.array([0.5, 1.0, 2.0]))
    ensure(out.shape == (2, 3), "true_vol must broadcast k x T, got %r" % (out.shape,))
    # total variance increasing in T at fixed k (the calendar-arbitrage-free claim, truth side)
    Ts = np.array([1 / 12, 0.25, 0.5, 1.0, 2.0])
    for k in np.linspace(-0.6, 0.4, 11):
        w = np.array([float(syn.true_vol(k, t)) ** 2 * t for t in Ts])
        ensure((np.diff(w) > 0).all(), "truth total variance not increasing in T at k=%r: %r" % (k, w))


@check
def c10_generate_chain_contract():
    bsp, syn, dio, srf, viz = imp()
    a = syn.generate_chain()
    b = syn.generate_chain()
    ensure(a.equals(b), "generate_chain not deterministic for the same arguments")
    ensure(not a.equals(syn.generate_chain(seed=1)), "different seed gave an identical chain (noise has no effect)")
    ensure(list(a.columns) == ["strike", "T", "type", "price", "sigma_true"], "columns %r" % list(a.columns))
    ensure(set(a["type"]) == {"C", "P"} and (a["price"] >= 0.05 - 1e-12).all(), "type set / min_price default 0.05")
    ensure(np.allclose(a["price"] / 0.01, np.round(a["price"] / 0.01), atol=1e-6), "default tick 0.01 not applied")
    keys = list(zip(a["T"], a["strike"], a["type"].map({"C": 0, "P": 1})))
    ensure(keys == sorted(keys) and (a.index == range(len(a))).all(), "sorted (T,strike,C<P) with RangeIndex")
    ensure(not a.duplicated(["strike", "T", "type"]).any(), "duplicate (strike,T,type) in generated chain")
    c = syn.generate_chain(noise_bps=0.0, tick=0.0, min_price=0.0)
    ensure(len(c) == 2 * len(syn.DEFAULT_MATURITIES_YEARS) * len(syn.DEFAULT_STRIKE_FRACTIONS), "clean chain row count %d" % len(c))
    # clean price == independent reference at sigma_true (non-circular)
    sub = c.iloc[::37]
    for _, row in sub.iterrows():
        ref = ref_price(100.0, row["strike"], row["T"], 0.04, 0.015, row["sigma_true"], row["type"] == "C")
        ensure(abs(row["price"] - ref) < 1e-9, "clean price %r != reference %r" % (row["price"], ref))
        k = math.log(row["strike"] / (100.0 * math.exp((0.04 - 0.015) * row["T"])))
        ensure(abs(row["sigma_true"] - ref_true_vol(k, row["T"])) < 1e-12, "sigma_true != SSVI spec")
    # noise is multiplicative and non-zero at 5 bps (anti-vacuity: noise actually reached the prices)
    n = syn.generate_chain(tick=0.0, min_price=0.0)
    rel = ((n["price"] - c["price"]) / c["price"]).abs()
    ensure(0 < rel.max() < 0.01 and rel.median() > 1e-6, "noise magnitude implausible: max %.2e" % rel.max())
    for bad in (dict(maturities=[]), dict(strikes=[]), dict(S=0.0), dict(S=-1.0), dict(noise_bps=-1.0), dict(tick=-0.01)):
        try:
            syn.generate_chain(**bad)
        except ValueError:
            continue
        raise AssertionError("generate_chain(%r) must raise ValueError (CONTRACT 9)" % (bad,))


@check
def c11_market_params():
    bsp, syn, dio, srf, viz = imp()
    p = dio.MarketParams(S=100.0, r=0.04, q=0.015)
    ensure(abs(float(p.forward(2.0)) - 100.0 * math.exp(0.025 * 2.0)) < 1e-12, "forward(T) = S*exp((r-q)T)")
    f = p.forward(np.array([0.5, 1.0]))
    ensure(np.asarray(f).shape == (2,), "forward must keep array shape")
    for kw in (dict(S=0.0, r=0.0, q=0.0), dict(S=-1.0, r=0.0, q=0.0), dict(S=np.nan, r=0.0, q=0.0),
               dict(S=100.0, r=np.inf, q=0.0), dict(S=100.0, r=0.0, q=np.nan)):
        try:
            dio.MarketParams(**kw)
        except ValueError:
            continue
        raise AssertionError("MarketParams(%r) must raise ValueError (5.1)" % (kw,))
    try:
        p.S = 1.0
    except Exception:
        pass
    else:
        raise AssertionError("MarketParams must be frozen")


def _write(path, text, enc="utf-8", newline="\n"):
    with open(path, "w", encoding=enc, newline="") as fh:
        fh.write(text.replace("\n", newline))


@check
def c11_loader_quarantine_and_control_total():
    bsp, syn, dio, srf, viz = imp()
    d = tempfile.mkdtemp(prefix="vst_")
    try:
        path = os.path.join(d, "c.csv")
        lines = ["Strike , TYPE,Price,T,junk",                     # line 1 header, case/space tolerant, extra col dropped
                 "100,call,5.5,0.5,x",                              # 2 ok
                 "100,Put,4.5,0.5,x",                               # 3 ok
                 "",                                                # 4 blank (not a data row)
                 "105,C,abc,0.5,x",                                 # 5 non_numeric
                 "-5,C,1.0,0.5,x",                                  # 6 non_positive strike
                 "110,C,0,0.5,x",                                   # 7 non_positive price
                 "110,C,1.0,0,x",                                   # 8 non_positive T
                 "110,Z,1.0,0.5,x",                                 # 9 bad_type
                 "100,C,5.6,0.5,x",                                 # 10 duplicate of line 2
                 "120,C,,0.5,x",                                    # 11 non_numeric (empty)
                 "120,P,2.0,0.5,x"]                                 # 12 ok
        _write(path, "\n".join(lines) + "\n", enc="utf-8-sig", newline="\r\n")   # BOM + CRLF
        chain, rejects = dio.load_chain_csv(path)
        n_rows = len([ln for ln in lines[1:] if ln.strip()])
        ensure(n_rows == len(chain) + len(rejects), "control total 10.1: %d != %d + %d" % (n_rows, len(chain), len(rejects)))
        ensure(len(chain) == 3 and len(rejects) == 7, "chain %d rejects %d" % (len(chain), len(rejects)))
        ensure(list(chain.columns) == ["strike", "T", "type", "price"], "chain columns %r" % list(chain.columns))
        ensure(set(chain["type"]) == {"C", "P"}, "type not normalised to C/P")
        ensure(list(rejects.columns[:3]) == ["line", "reason", "raw"], "rejects columns %r" % list(rejects.columns))
        got = {int(r.line): r.reason for r in rejects.itertuples()}
        want = {5: "non_numeric", 6: "non_positive", 7: "non_positive", 8: "non_positive", 9: "bad_type",
                10: "duplicate", 11: "non_numeric"}
        ensure(got == want, "reject lines/reasons %r != %r" % (got, want))
        ensure(abs(float(chain.loc[(chain["strike"] == 100) & (chain["type"] == "C"), "price"].iloc[0]) - 5.5) < 1e-15,
               "the FIRST duplicate must be kept")
    finally:
        shutil.rmtree(d, ignore_errors=True)


@check
def c11_loader_expiry_and_file_errors():
    bsp, syn, dio, srf, viz = imp()
    d = tempfile.mkdtemp(prefix="vst_")
    try:
        p1 = os.path.join(d, "e.csv")
        _write(p1, "strike,type,price,expiry\n100,C,5,2025-07-01\n100,P,4,2025-01-01\n100,P,4,garbage\n100,C,2,2025-01-01\n")
        try:
            dio.load_chain_csv(p1)
        except ValueError:
            pass
        else:
            raise AssertionError("expiry without valuation_date must raise ValueError (5.2)")
        params = dio.MarketParams(S=100.0, r=0.0, q=0.0, valuation_date=datetime.date(2025, 1, 1))
        chain, rej = dio.load_chain_csv(p1, params)
        ensure(len(chain) == 1 and abs(chain["T"].iloc[0] - 181 / 365.0) < 1e-15, "T=(expiry-val).days/365: %r" % chain["T"].tolist())
        ensure(sorted(rej["reason"]) == ["bad_date", "non_positive", "non_positive"], "reject reasons %r" % rej["reason"].tolist())
        # both T and expiry present -> T wins
        p2 = os.path.join(d, "b.csv")
        _write(p2, "strike,type,price,T,expiry\n100,C,5,0.25,2030-01-01\n")
        chain, rej = dio.load_chain_csv(p2, params)
        ensure(abs(chain["T"].iloc[0] - 0.25) < 1e-15, "T must win over expiry")
        # sigma_true kept
        p3 = os.path.join(d, "s.csv")
        _write(p3, "strike,type,price,T,sigma_true\n100,C,5,0.25,0.2\n")
        chain, _ = dio.load_chain_csv(p3)
        ensure("sigma_true" in chain.columns and chain["sigma_true"].iloc[0] == 0.2, "sigma_true kept")
        # file-level errors
        for name, body, exc in (("nofile.csv", None, FileNotFoundError),
                                ("nocol.csv", "strike,price,T\n100,5,0.5\n", ValueError),
                                ("none.csv", "strike,type,price,T\n100,C,-1,0.5\n", ValueError),
                                ("empty.csv", "strike,type,price,T\n", ValueError)):
            pth = os.path.join(d, name)
            if body is not None:
                _write(pth, body)
            try:
                dio.load_chain_csv(pth)
            except exc:
                continue
            raise AssertionError("%s must raise %s (5.2)" % (name, exc.__name__))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ----------------------------------------------------------------------------------------------
# 4. Surface (plan check 4) + control totals 3 and 5
# ----------------------------------------------------------------------------------------------
@check
def c04_surface_finite_and_shapes_both_methods():
    bsp, syn, dio, srf, viz = imp()
    chain, params, quotes = clean_setup()
    for method in ("rbf", "spline"):
        s = clean_surface(method)
        nT, nk = len(s.T_grid), len(s.k_grid)
        ensure((nT, nk) == (60, 80), "%s default grid %r != (60,80)" % (method, (nT, nk)))
        for nm in ("w", "iv", "K"):
            a = getattr(s, nm)
            ensure(a.shape == (nT, nk), "%s.%s shape %r (axis order [i_T, j_k], 6.1)" % (method, nm, a.shape))
        ensure(np.isfinite(s.w).all() and np.isfinite(s.iv).all(), "%s: NaN/inf in w or iv (10.5)" % method)
        ensure((s.w >= 0).all() and (s.iv >= 0).all(), "%s: negative w/iv" % method)
        ensure((np.diff(s.T_grid) > 0).all() and s.T_grid[0] > 0 and (np.diff(s.k_grid) > 0).all(), "%s grids monotone, T>0" % method)
        ensure(np.allclose(s.iv, np.sqrt(s.w / s.T_grid[:, None]), rtol=1e-12, atol=1e-14), "%s: iv != sqrt(w/T)" % method)
        Fg = params.S * np.exp((params.r - params.q) * s.T_grid)
        ensure(np.allclose(s.F, Fg, rtol=1e-13), "%s: F != S*exp((r-q)T)" % method)
        ensure(np.allclose(s.K, Fg[:, None] * np.exp(s.k_grid[None, :]), rtol=1e-12), "%s: K != F*exp(k)" % method)
        ensure(s.method == method, "method field")
        # R9 governing definition, re-derived from the quotes (not from surface internals)
        use = quotes[quotes["status"].isin([0, 1]) & ~quotes["T"].isin(list(s.dropped_T))]
        g = use.groupby("T")["k"].agg(["min", "max"]).sort_index()
        klo = np.interp(s.T_grid, g.index.to_numpy(), g["min"].to_numpy())
        khi = np.interp(s.T_grid, g.index.to_numpy(), g["max"].to_numpy())
        ensure(s.k_lo.shape == (nT,) and s.k_hi.shape == (nT,) and np.allclose(s.k_lo, klo, atol=1e-12) and np.allclose(s.k_hi, khi, atol=1e-12), "%s: k_lo/k_hi != R9 definition" % method)
        ensure(s.in_domain.shape == (nT, nk) and s.in_domain.dtype == bool, "%s: in_domain shape/dtype" % method)
        ind = (klo[:, None] <= s.k_grid[None, :]) & (s.k_grid[None, :] <= khi[:, None])
        ensure((s.in_domain == ind).all(), "%s: in_domain differs from independent R9 mask in %d nodes" % (method, int((s.in_domain != ind).sum())))
        ensure(0.25 * s.in_domain.size < s.in_domain.sum() < s.in_domain.size, "%s: in_domain is vacuous (all True or <25%%): %d/%d" % (method, s.in_domain.sum(), s.in_domain.size))
        usable = quotes[quotes["status"].isin([0, 1]) & ~quotes["T"].isin(list(s.dropped_T))]
        ensure(s.n_quotes_used == len(usable) and len(usable) > 0, "%s: n_quotes_used %d != independent %d (10.3)" % (method, s.n_quotes_used, len(usable)))
        ensure(abs(s.T_grid[0] - usable["T"].min()) < 1e-12 and abs(s.T_grid[-1] - usable["T"].max()) < 1e-12, "T range = quoted T range")
        ensure(abs(s.k_grid[0] - usable["k"].min()) < 1e-12 and abs(s.k_grid[-1] - usable["k"].max()) < 1e-12, "k range = union of quoted k")


@check
def c04_surface_matches_market_and_truth():
    bsp, syn, dio, srf, viz = imp()
    chain, params, quotes = clean_setup()
    ok = quotes[quotes["status"].isin([0, 1])]
    for method in ("rbf", "spline"):
        s = clean_surface(method)
        pred = s.evaluate(ok["T"].to_numpy(), ok["k"].to_numpy())
        ensure(pred.shape == (len(ok),) and np.isfinite(pred).all(), "%s evaluate at quotes" % method)
        e_mkt = np.abs(pred - ok["iv"].to_numpy())
        ensure(e_mkt.max() <= 0.01, "%s: |evaluate - market iv| at quote points max %.4f > 0.01" % (method, e_mkt.max()))
        # vs ground truth at own-maturity interior points (CONTRACT 12): quoted-range midpoints between quotes
        errs = []
        for T, g in ok.groupby("T"):
            ks = np.sort(g["k"].to_numpy())
            mid = 0.5 * (ks[:-1] + ks[1:])
            for kk in mid:
                errs.append(abs(float(s.evaluate(T, kk)) - ref_true_vol(kk, T)))
        ensure(len(errs) > 100, "anti-vacuity: too few interior probes (%d)" % len(errs))
        ensure(max(errs) <= 0.01, "%s: interior |evaluate - true_vol| max %.4f > 0.01" % (method, max(errs)))
        # off-grid T (between maturities), k within the intersection of ALL maturities' quoted ranges
        kmin = ok.groupby("T")["k"].min().max()
        kmax = ok.groupby("T")["k"].max().min()
        Ts = np.sort(ok["T"].unique())
        e2 = []
        for a, b in zip(Ts[:-1], Ts[1:]):
            Tm = 0.5 * (a + b)
            for kk in np.linspace(kmin, kmax, 9):
                e2.append(abs(float(s.evaluate(Tm, kk)) - ref_true_vol(kk, Tm)))
        ensure(max(e2) <= 0.01, "%s: off-grid-T |evaluate - true_vol| max %.4f > 0.01 (CONTRACT 12 assumption)" % (method, max(e2)))
        # evaluate_w consistency and domain errors
        w = s.evaluate_w(1.0, 0.0)
        ensure(abs(float(s.evaluate(1.0, 0.0)) - math.sqrt(float(w) / 1.0)) < 1e-12, "evaluate vs evaluate_w")
        for bad in (0.0, -1.0):
            try:
                s.evaluate(bad, 0.0)
            except ValueError:
                continue
            raise AssertionError("evaluate(T=%r) must raise ValueError (6.1)" % bad)
        ensure(np.isnan(s.evaluate(np.nan, 0.0)), "NaN in -> NaN out")
        far = s.evaluate(1.0, 5.0)
        ensure(np.isfinite(far), "extrapolation must be finite")


@check
def c04_build_surface_errors_and_thin_maturity_drop():
    bsp, syn, dio, srf, viz = imp()
    chain, params, quotes = clean_setup()
    for kw in (dict(method="griddata"), dict(n_T=1), dict(n_k=3)):
        try:
            srf.build_surface(quotes, params, **kw)
        except ValueError:
            continue
        raise AssertionError("build_surface(%r) must raise ValueError (6.3)" % (kw,))
    one_T = quotes[quotes["T"] == quotes["T"].min()]
    try:
        srf.build_surface(one_T, params)
    except ValueError:
        pass
    else:
        raise AssertionError("<2 maturities must raise ValueError")
    try:
        srf.build_surface(quotes.iloc[0:0], params)
    except ValueError:
        pass
    else:
        raise AssertionError("empty quotes must raise ValueError")
    # thin maturity (3 usable quotes < MIN_QUOTES_PER_T=4) is DROPPED, not an error, and recorded
    Tmid = float(np.sort(quotes["T"].unique())[3])
    thin = pd.concat([quotes[quotes["T"] != Tmid], quotes[quotes["T"] == Tmid].iloc[:3]], ignore_index=True)
    for method in ("rbf", "spline"):
        s = srf.build_surface(thin, params, method=method, n_T=20, n_k=30)
        ensure(tuple(s.dropped_T) == (Tmid,), "%s: dropped_T %r != (%r,)" % (method, s.dropped_T, Tmid))
        ensure(s.n_quotes_used == int((thin["status"].isin([0, 1]) & (thin["T"] != Tmid)).sum()), "n_quotes_used excludes dropped T (10.3)")
        ensure(np.isfinite(s.w).all(), "finite after drop")
    # failed-solve rows must not feed the interpolator: poison them with status>=2 + NaN and compare
    poisoned = quotes.copy()
    idx = poisoned.index[::7]
    poisoned.loc[idx, "status"] = np.int8(3)
    poisoned.loc[idx, ["iv", "w"]] = np.nan
    s = srf.build_surface(poisoned, params, method="spline", n_T=20, n_k=30)
    ensure(s.n_quotes_used == int(poisoned["status"].isin([0, 1]).sum()) and np.isfinite(s.w).all(), "status>=2 rows excluded")


# ----------------------------------------------------------------------------------------------
# 5. Diagnostics (plan check 5): independent recount, injected violations reach the counter
# ----------------------------------------------------------------------------------------------
def _indep_masks(ind):
    """R11 scope, re-derived from the in_domain matrix: calendar pairs and butterfly triples."""
    cal = ind[:-1, :] & ind[1:, :]
    bf = ind[:, :-2] & ind[:, 1:-1] & ind[:, 2:]
    return cal, bf


def _indep_calendar(w, tol, ind=None):
    dw = w[1:, :] - w[:-1, :]
    cal = np.ones(dw.shape, bool) if ind is None else _indep_masks(ind)[0]
    v = cal & (dw < -tol)
    return int(v.sum()), float(max(0.0, (-dw[cal]).max())) if cal.any() else 0.0, int(cal.sum())


def _indep_butterfly(S, r, q, T, K, iv, tol, ind=None):
    nT, nk = iv.shape
    mask = np.ones((nT, nk - 2), bool) if ind is None else _indep_masks(ind)[1]
    viol, mx, n = 0, 0.0, 0
    for i in range(nT):
        C = np.array([ref_price(S, K[i, j], T[i], r, q, iv[i, j], True) for j in range(nk)])
        s = np.diff(C) / np.diff(K[i])
        d2 = np.diff(s)
        m = mask[i]
        viol += int(((d2 < -tol) & m).sum())
        if m.any():
            mx = max(mx, float(max(0.0, (-d2[m]).max())))
        n += int(m.sum())
    return viol, mx, n


def _replace_w(s, w):
    import dataclasses
    iv = np.sqrt(np.maximum(w, 0.0) / s.T_grid[:, None])
    return dataclasses.replace(s, w=w, iv=iv)


@check
def c05_arbitrage_report_format_and_wording():
    bsp, syn, dio, srf, viz = imp()
    s = clean_surface("spline")
    rep = srf.arbitrage_report(s)
    ensure(set(rep.keys()) == {"disclaimer", "calendar", "butterfly", "lines"}, "keys %r (no extra keys, 6.4)" % sorted(rep))
    ensure(set(rep["calendar"]) == {"n_checked", "n_violations", "max_violation_w", "tol"}, "calendar keys %r" % sorted(rep["calendar"]))
    ensure(set(rep["butterfly"]) == {"n_checked", "n_violations", "max_violation", "tol"}, "butterfly keys %r" % sorted(rep["butterfly"]))
    ensure(not any(isinstance(v, (bool, np.bool_)) for blk in (rep, rep["calendar"], rep["butterfly"]) for v in blk.values()),
           "a boolean pass/ok/verdict value is forbidden (6.4)")
    want = srf.DIAGNOSTIC_DISCLAIMER
    ensure(rep["disclaimer"] == want, "report disclaimer != surface.DIAGNOSTIC_DISCLAIMER")
    ensure(want.startswith("DIAGNOSTIC ONLY:") and "inside the quoted domain" in want and "do not enforce or guarantee an arbitrage-free surface" in want
           and "extrapolated regions" in want, "disclaimer lacks R11(c) scope wording: %r" % want)
    L = rep["lines"]
    ensure(isinstance(L, list) and len(L) == 3 and all(isinstance(x, str) for x in L), "lines must be 3 str")
    ensure(all(x.isascii() for x in L), "lines must be ASCII")
    c, b = rep["calendar"], rep["butterfly"]
    ensure(L[0] == want, "lines[0]")
    ensure(L[1] == "calendar: %d/%d violations (max %.2e in total variance, tol %.1e)" % (c["n_violations"], c["n_checked"], c["max_violation_w"], c["tol"]), "lines[1] %r" % L[1])
    ensure(L[2] == "butterfly: %d/%d violations (max %.2e in dC/dK, tol %.1e)" % (b["n_violations"], b["n_checked"], b["max_violation"], b["tol"]), "lines[2] %r" % L[2])
    nT, nk = s.w.shape
    cal_m, bf_m = _indep_masks(s.in_domain)
    ensure(c["n_checked"] == int(cal_m.sum()) and b["n_checked"] == int(bf_m.sum()), "n_checked %r/%r != in-domain pair/triple counts %d/%d (R11 a,b)" % (c["n_checked"], b["n_checked"], cal_m.sum(), bf_m.sum()))
    ensure(all(isinstance(v, int) and not isinstance(v, bool) for v in (c["n_checked"], c["n_violations"], b["n_checked"], b["n_violations"])), "counts must be int")
    ensure(c["max_violation_w"] >= 0 and b["max_violation"] >= 0 and (c["tol"], b["tol"]) == (1e-6, 1e-8), "max>=0 and default tolerances")
    for x in L + [rep["disclaimer"]]:
        ensure("is arbitrage-free" not in x.lower() and "no arbitrage" not in x.lower(), "guarantee wording in %r" % x)


@check
def c05_r12_n_checked_not_vacuous_clean_chain():
    bsp, syn, dio, srf, viz = imp()
    for method in ("rbf", "spline"):
        s = clean_surface(method)
        rep = srf.arbitrage_report(s)
        nT, nk = s.w.shape
        fc, fb = (nT - 1) * nk, nT * (nk - 2)
        NOTES.append("R12 %s: calendar n_checked %d/%d (%.1f%%), butterfly n_checked %d/%d (%.1f%%)" % (
            method, rep["calendar"]["n_checked"], fc, 100.0 * rep["calendar"]["n_checked"] / fc,
            rep["butterfly"]["n_checked"], fb, 100.0 * rep["butterfly"]["n_checked"] / fb))
        ensure(rep["calendar"]["n_checked"] >= 0.25 * fc, "%s: calendar n_checked %d < 25%% of full grid %d (R12)" % (method, rep["calendar"]["n_checked"], fc))
        ensure(rep["butterfly"]["n_checked"] >= 0.25 * fb, "%s: butterfly n_checked %d < 25%% of full grid %d (R12)" % (method, rep["butterfly"]["n_checked"], fb))


@check
def c05_calendar_clean_truth_zero_and_injected_detected():
    bsp, syn, dio, srf, viz = imp()
    for method in ("rbf", "spline"):
        s = clean_surface(method)
        ind = s.in_domain
        rep = srf.arbitrage_report(s)
        ensure(rep["calendar"]["n_violations"] == 0, "%s: clean-truth surface shows %d in-domain calendar violations (CONTRACT 12)" % (method, rep["calendar"]["n_violations"]))
        iv0, mx0, n0 = _indep_calendar(s.w, 1e-6, ind)
        ensure(iv0 == 0 and n0 == rep["calendar"]["n_checked"], "independent recount disagrees on clean surface")
        # R12: single injection at an IN-DOMAIN pair (i,j)-(i+1,j); the counted violation must be that node
        pairs = np.argwhere(ind[:-1, :] & ind[1:, :])
        ensure(len(pairs) > 100, "anti-vacuity: too few in-domain pairs")
        i, j = [int(v) for v in pairs[len(pairs) // 2]]
        w2 = s.w.copy()
        w2[i + 1, j] = s.w[i, j] * 0.5
        ensure(w2[i + 1, j] - s.w[i, j] < -1e-6, "injection too small to exceed tol")
        bad = srf.arbitrage_report(_replace_w(s, w2))
        ensure(bad["calendar"]["n_violations"] == 1, "%s: one injected in-domain violation at (%d,%d) counted %d times (expected exactly 1)" % (method, i + 1, j, bad["calendar"]["n_violations"]))
        dw = w2[1:, :] - w2[:-1, :]
        viol_nodes = np.argwhere((dw < -1e-6) & _indep_masks(ind)[0])
        ensure(viol_nodes.tolist() == [[i, j]], "independent location of the counted violation %r != injected (%d,%d)" % (viol_nodes.tolist(), i, j))
        ensure(abs(bad["calendar"]["max_violation_w"] - float(s.w[i, j] - w2[i + 1, j])) < 1e-12, "max_violation_w != injected size")
        # same-size injection at an OUT-of-domain pair must NOT be counted (scope is in-domain only, R11)
        outp = np.argwhere(~(ind[:-1, :] & ind[1:, :]) & (s.w[:-1, :] > 1e-3))
        ensure(len(outp) > 0, "anti-vacuity: no out-of-domain pair available (mask is all True?)")
        oi, oj = [int(v) for v in outp[0]]
        w4 = s.w.copy()
        w4[oi + 1, oj] = s.w[oi, oj] * 0.5
        ensure(_indep_calendar(w4, 1e-6)[0] >= 1, "anti-vacuity: out-of-domain injection is not a violation at all")
        out_rep = srf.arbitrage_report(_replace_w(s, w4))
        ensure(out_rep["calendar"]["n_violations"] == 0, "%s: out-of-domain injection at (%d,%d) was counted (%d): scope mask not applied (R11a)" % (method, oi + 1, oj, out_rep["calendar"]["n_violations"]))
        # whole-row injection, recount must match the masked independent count exactly
        w5 = s.w.copy()
        w5[30, :] = w5[29, :] * 0.5
        e5, mx5, _ = _indep_calendar(w5, 1e-6, ind)
        r5 = srf.arbitrage_report(_replace_w(s, w5))
        ensure(e5 >= 1 and r5["calendar"]["n_violations"] == e5 and abs(r5["calendar"]["max_violation_w"] - mx5) < 1e-12, "row injection: report %r vs independent %d/%.3e" % (r5["calendar"], e5, mx5))
        loose = srf.arbitrage_report(_replace_w(s, w5), tol_calendar_w=10.0)
        ensure(loose["calendar"]["n_violations"] == 0, "tol_calendar_w not honoured")


@check
def c05_butterfly_independent_recount_and_injection():
    bsp, syn, dio, srf, viz = imp()
    import dataclasses
    for method in ("rbf", "spline"):
        s = clean_surface(method)
        p = s.params
        rep = srf.arbitrage_report(s)
        e, mx, n = _indep_butterfly(p.S, p.r, p.q, s.T_grid, s.K, s.iv, 1e-8, s.in_domain)
        NOTES.append("clean %s in-domain butterfly: report %d/%d, independent %d/%d" % (method, rep["butterfly"]["n_violations"], rep["butterfly"]["n_checked"], e, n))
        ensure(rep["butterfly"]["n_violations"] == e and rep["butterfly"]["n_checked"] == n,
               "%s: butterfly report %r != independent masked recount (%d/%d)" % (method, rep["butterfly"], e, n))
        if method == "spline":
            ensure(rep["butterfly"]["n_violations"] == 0, "R21(3): clean-chain spline in-domain butterfly n_violations = %d/%d (expected 0) - REAL in-domain defect" % (rep["butterfly"]["n_violations"], rep["butterfly"]["n_checked"]))
        trip = np.argwhere(_indep_masks(s.in_domain)[1])
        i, j = [int(v) for v in trip[len(trip) // 2]]
        iv2 = s.iv.copy()
        iv2[i, j + 1] += 0.25            # centre node of an in-domain triple
        rep2 = srf.arbitrage_report(dataclasses.replace(s, iv=iv2))
        e2, mx2, _ = _indep_butterfly(p.S, p.r, p.q, s.T_grid, s.K, iv2, 1e-8, s.in_domain)
        ensure(e2 > e, "anti-vacuity: injected spike produced no extra independent violation (%d vs %d)" % (e2, e))
        ensure(rep2["butterfly"]["n_violations"] == e2, "%s: injected butterfly violations: report %d vs independent %d" % (method, rep2["butterfly"]["n_violations"], e2))
        ensure(abs(rep2["butterfly"]["max_violation"] - mx2) <= 1e-9 * max(1.0, mx2) and mx2 > 0, "max_violation %r vs %r" % (rep2["butterfly"]["max_violation"], mx2))
        loose = srf.arbitrage_report(dataclasses.replace(s, iv=iv2), tol_butterfly=1e6)
        ensure(loose["butterfly"]["n_violations"] == 0, "tol_butterfly not honoured")
        # out-of-domain spike must not be counted
        outn = np.argwhere(~s.in_domain[:, 2:-2])
        if len(outn):
            oi, oj = [int(v) for v in outn[0]]
            iv3 = s.iv.copy()
            iv3[oi, oj + 3] += 0.25
            eo, _, _ = _indep_butterfly(p.S, p.r, p.q, s.T_grid, s.K, iv3, 1e-8, s.in_domain)
            ro = srf.arbitrage_report(dataclasses.replace(s, iv=iv3))
            ensure(ro["butterfly"]["n_violations"] == eo, "%s: out-of-domain spike: report %d vs masked independent %d" % (method, ro["butterfly"]["n_violations"], eo))


@check
def c06_term_structure_per_maturity_mapping():
    bsp, syn, dio, srf, viz = imp()
    chain, params, quotes = clean_setup()
    for method in ("rbf", "spline"):
        s = clean_surface(method)
        for frac in (0.8, 0.9, 1.1, 1.2):
            K = frac * params.S
            ts = srf.term_structure(s, K)
            ensure(list(ts.columns) == ["T", "k", "iv", "in_domain"], "columns %r" % list(ts.columns))
            ensure(len(ts) == len(s.T_grid) and np.allclose(ts["T"], s.T_grid), "T = surface.T_grid")
            Fi = params.S * np.exp((params.r - params.q) * s.T_grid)
            ensure(np.allclose(ts["k"], np.log(K / Fi), atol=1e-13), "k_i != ln(K/F(T_i)) (R4)")
            ensure(ts["k"].nunique() > 10 and ts["k"].max() - ts["k"].min() > 0.01, "anti-vacuity: k column is (nearly) constant - fixed-k row")
            ev = s.evaluate(s.T_grid, ts["k"].to_numpy())
            ensure(np.allclose(ts["iv"], ev, atol=1e-12), "iv != surface.evaluate(T_i, k_i)")
            ind = (ts["k"] >= s.k_lo) & (ts["k"] <= s.k_hi)       # R10
            ensure((ts["in_domain"].to_numpy() == ind.to_numpy()).all(), "in_domain flag != R10 rule k_lo[i] <= k_i <= k_hi[i]")
            atm = srf.term_structure(s)
            ensure(np.allclose(atm["k"], 0.0) and atm["in_domain"].all(), "K=None -> ATM-forward k==0")
            diff = np.abs(ts["iv"].to_numpy() - atm["iv"].to_numpy()).max()
            ensure(diff > 1e-4, "%s: fixed-strike curve (K=%.0f) equals the k=0 curve (max diff %.2e): per-maturity mapping not applied" % (method, K, diff))
        for badK in (0.0, -5.0):
            try:
                srf.term_structure(s, badK)
            except ValueError:
                continue
            raise AssertionError("term_structure(K=%r) must raise ValueError (6.6)" % badK)
        # some strike must be out-of-domain at short maturity (the extrapolation flag is real)


@check
def c06_r10_in_domain_false_case_reachable_noisy_chain():
    bsp, syn, dio, srf, viz = imp()
    chain, params, quotes = noisy_setup()
    for method in ("rbf", "spline"):
        s = srf.build_surface(quotes, params, method=method)
        ts = srf.term_structure(s, 0.8 * params.S)
        T0 = float(s.T_grid[0])
        ensure(abs(T0 - 1 / 12) < 1e-9, "first grid T %r != 1/12" % T0)
        use = quotes[quotes["status"].isin([0, 1]) & (abs(quotes["T"] - T0) < 1e-12)]
        kmin, kmax = float(use["k"].min()), float(use["k"].max())
        k0 = math.log(0.8 * params.S / (params.S * math.exp((params.r - params.q) * T0)))
        ensure(k0 < kmin, "anti-vacuity: 0.8S at T=1/12 (k=%.3f) is not outside the quoted range [%.3f, %.3f]" % (k0, kmin, kmax))
        ensure(not bool(ts["in_domain"].iloc[0]), "%s: in_domain True for 0.8*S at T=1/12 (k=%.3f outside quoted [%.3f,%.3f]) - R10 label cannot fail" % (method, k0, kmin, kmax))
        ensure(bool(ts["in_domain"].any()) and not bool(ts["in_domain"].all()), "%s: in_domain must be mixed for 0.8S (some maturities cover it)" % method)
        ATM = srf.term_structure(s)
        ensure(bool(ATM["in_domain"].all()), "ATM-forward k=0 should be in domain at every maturity")


@check
def c06_r13_ox2_viz_gaps_where_out_of_domain_noisy_chain():
    bsp, syn, dio, srf, viz = imp()
    chain, params, quotes = noisy_setup()
    for method in ("rbf", "spline"):
        s = srf.build_surface(quotes, params, method=method)
        fig = viz.build_dashboard(s, quotes, params)
        data = fig.data
        name = "Term K=%.2f" % (0.8 * params.S)
        tr = [t for t in data if t.name == name]
        ensure(len(tr) == 1, "trace %r missing" % name)
        y = np.asarray(tr[0].y, dtype=float)
        ts = srf.term_structure(s, 0.8 * params.S)
        dom = ts["in_domain"].to_numpy(bool)
        ensure(len(y) == len(dom), "term trace length")
        ensure((~dom).any() and dom.any(), "anti-vacuity: 0.8S must be mixed in/out of domain")
        ensure((np.isnan(y) == ~dom).all(), "%s: term y NaN pattern != ~in_domain (R13): NaN at %d, out-of-domain %d" % (method, int(np.isnan(y).sum()), int((~dom).sum())))
        ensure(np.allclose(y[dom], 100.0 * ts["iv"].to_numpy(float)[dom]), "in-domain term y != 100*iv")
        # OX-2 smile: nearest-row domain at the first smile maturity
        sm_tr = [t for t in data if str(t.name).startswith("Smile T=")]
        ensure(len(sm_tr) >= 1, "no smile traces")
        T0 = float(s.T_grid[0])
        first = [t for t in sm_tr if abs(float(t.name.split("=")[1].rstrip("y")) - T0) < 5e-4]
        ensure(len(first) == 1, "smile at T=1/12 not found")
        ys = np.asarray(first[0].y, dtype=float)
        domrow = s.in_domain[0]
        ensure(len(ys) == len(domrow) and (~domrow).any(), "smile length / anti-vacuity")
        ensure((np.isnan(ys) == ~domrow).all(), "%s: smile y NaN pattern != ~in_domain at T=1/12 (OX-2): %d vs %d" % (method, int(np.isnan(ys).sum()), int((~domrow).sum())))


@check
def c06_smile_slice():
    bsp, syn, dio, srf, viz = imp()
    s = clean_surface("spline")
    sm = srf.smile(s, 0.37)
    ensure(list(sm.columns) == ["k", "strike", "iv"] and len(sm) == len(s.k_grid), "smile columns/len")
    ensure(np.allclose(sm["strike"], s.params.forward(0.37) * np.exp(sm["k"])), "smile strike = F(T)*exp(k)")
    ensure(np.allclose(sm["iv"], s.evaluate(0.37, sm["k"].to_numpy())) and (np.diff(sm["k"]) > 0).all(), "smile iv / order")
    ensure(len(srf.smile(s, 0.37, n_k=11)) == 11, "smile n_k")
    try:
        srf.smile(s, 0.0)
    except ValueError:
        pass
    else:
        raise AssertionError("smile(T<=0) must raise ValueError")


# ----------------------------------------------------------------------------------------------
# 7. Dashboard content (plan check 7): parse fig.to_dict()
# ----------------------------------------------------------------------------------------------
HOVER = "Strike: %{customdata[0]:.2f}<br>Expiry: %{customdata[2]} (%{customdata[1]:.0f}d)<br>IV: %{customdata[3]:.2f}%<extra></extra>"


def arr(x):
    """Decode a plotly array that may be a numpy array, list, or {'dtype','bdata'} binary dict."""
    import base64
    if isinstance(x, dict) and "bdata" in x:
        a = np.frombuffer(base64.b64decode(x["bdata"]), dtype=np.dtype(x["dtype"]))
        if "shape" in x:
            a = a.reshape([int(v) for v in str(x["shape"]).split(",")])
        return a
    return np.asarray(x)


def _fig(x_axis="k", colorscale="Viridis"):
    bsp, syn, dio, srf, viz = imp()
    chain, params, quotes = clean_setup()
    s = clean_surface("spline")
    return viz.build_dashboard(s, quotes, params, colorscale=colorscale, x_axis=x_axis), s, quotes, params


@check
def c07_dashboard_contract_from_fig_dict():
    bsp, syn, dio, srf, viz = imp()
    for x_axis in ("k", "strike"):
        fig, s, quotes, params = _fig(x_axis)
        d = fig.to_dict()
        data = d["data"]
        surf = [t for t in data if t.get("type") == "surface"]
        ensure(len(surf) == 1 and surf[0].get("name") == "IV surface", "exactly one surface trace named 'IV surface'")
        t = surf[0]
        nT, nk = s.w.shape
        z = arr(t["z"]).astype(float)
        ensure(z.shape == (nk, nT), "%s: surface z shape %r != (n_k,n_T) (7.1)" % (x_axis, z.shape))
        ensure(np.allclose(z, 100.0 * s.iv.T, atol=1e-9), "%s: z != 100*iv.T (percent only at display; no recompute)" % x_axis)
        ensure(z.max() > 5.0, "anti-vacuity: z looks like decimals, not percent (max %.4f)" % z.max())
        x, y = arr(t["x"]).astype(float), arr(t["y"]).astype(float)
        ensure(x.shape == (nk, nT) and np.allclose(x, s.T_grid[None, :]), "x must be T_grid broadcast, shape (n_k,n_T)")
        ensure(np.allclose(y, s.k_grid[:, None]) if x_axis == "k" else np.allclose(y, s.K.T), "%s: y axis wrong" % x_axis)
        cd = arr(t["customdata"])
        ensure(cd.shape == (nk, nT, 5), "customdata shape %r != (n_k,n_T,5)" % (cd.shape,))
        ensure(np.allclose(cd[..., 0].astype(float), s.K.T) and np.allclose(cd[..., 1].astype(float), s.T_grid[None, :] * 365.0), "customdata K / T_days")
        ensure(np.allclose(cd[..., 3].astype(float), 100.0 * s.iv.T) and np.allclose(cd[..., 4].astype(float), s.k_grid[:, None]), "customdata iv_pct / k")
        ensure(t.get("hovertemplate") == HOVER, "%s: surface hovertemplate != contract: %r" % (x_axis, t.get("hovertemplate")))
        ens = d["layout"]["scene"]
        ensure(ens["xaxis"]["title"]["text"] == "Time to maturity (years)", "x title %r" % ens["xaxis"]["title"])
        ensure(ens["yaxis"]["title"]["text"] == ("Log-moneyness k = ln(K/F)" if x_axis == "k" else "Strike"), "y title")
        ensure(ens["zaxis"]["title"]["text"] == "Implied volatility (%)", "z title")
        mk = [t for t in data if t.get("type") == "scatter3d" and t.get("name") == "Market quotes"]
        ensure(len(mk) == 1, "one Scatter3d named 'Market quotes'")
        ok = quotes[quotes["status"].isin([0, 1])]
        ensure(len(arr(mk[0]["z"])) == len(ok) and len(ok) > 0, "overlay must hold exactly the status 0/1 quotes: %d vs %d" % (len(arr(mk[0]["z"])), len(ok)))
        ensure(np.allclose(np.sort(arr(mk[0]["z"]).astype(float)), np.sort(100.0 * ok["iv"].to_numpy())), "overlay z = 100*iv of usable quotes")
        ensure(mk[0].get("hovertemplate") == HOVER, "overlay hovertemplate")
        names = [t.get("name", "") for t in data]
        smiles = [t for t in data if str(t.get("name", "")).startswith("Smile T=")]
        qmark = [t for t in data if str(t.get("name", "")).startswith("Quotes T=")]
        terms = [t for t in data if str(t.get("name", "")).startswith("Term K=")]
        ensure(1 <= len(smiles) <= 5 and len(qmark) == len(smiles), "smile traces %d / quote marker traces %d" % (len(smiles), len(qmark)))
        ensure(len(terms) == 5 and "ATM-forward (k=0)" in names, "term traces %d, ATM curve present %r" % (len(terms), "ATM-forward (k=0)" in names))
        ensure(all(n in names for n in ["Term K=%.2f" % (f * params.S) for f in (0.8, 0.9, 1.0, 1.1, 1.2)]), "term trace names %r" % [n for n in names if n.startswith("Term")])
        ensure({t.get("xaxis") for t in smiles}.isdisjoint({t.get("xaxis") for t in terms}), "smile and term panels must live on different 2-D axes")
        ensure(len({t.get("xaxis") for t in data if t.get("type") == "scatter"}) == 2, "both row-2 panels must exist")
        # term-structure traces carry percent y, per-maturity mapping applied (not equal to ATM curve)
        atm = [t for t in data if t.get("name") == "ATM-forward (k=0)"][0]
        t100 = [t for t in terms if t["name"] == "Term K=%.2f" % (1.2 * params.S)][0]
        ya, y1 = arr(atm["y"]).astype(float), arr(t100["y"]).astype(float)
        ensure(ya.max() > 5.0 and np.abs(ya - y1).max() > 1e-2, "term-structure traces look like the same row or decimals")
        # title phrase, dropdown, slider
        title = d["layout"]["title"]["text"]
        ensure("not guaranteed arbitrage-free" in title, "title lacks 'not guaranteed arbitrage-free': %r" % title)
        ums = d["layout"].get("updatemenus", [])
        flat = " ".join(str(u) for u in ums)
        ensure(len(ums) >= 1 and "Viridis" in flat and "Plasma" in flat and "colorscale" in flat, "colorscale dropdown missing")
        ensure(len(d["layout"].get("sliders", [])) >= 1, "slider missing")
        # smile visibility: exactly one smile visible initially is not mandated; but steps must toggle visibility
        sl = d["layout"]["sliders"][0]
        ensure(len(sl["steps"]) >= 2 and all("visible" in str(st) for st in sl["steps"]), "slider steps must toggle trace visibility")


@check
def c07_dashboard_dropdown_initial_and_bad_options():
    bsp, syn, dio, srf, viz = imp()
    fig, s, quotes, params = _fig("k", "Plasma")
    t = [t for t in fig.to_dict()["data"] if t.get("type") == "surface"][0]
    cs = t["colorscale"]
    cs0 = cs if isinstance(cs, str) else str(cs)
    ensure("Plasma" in cs0 or (not isinstance(cs, str) and len(cs) > 5), "initial colorscale should reflect argument Plasma: %r" % (cs0[:60],))
    from plotly import colors as pc
    plasma_first = pc.sample_colorscale("Plasma", [0.0])[0]
    viridis_first = pc.sample_colorscale("Viridis", [0.0])[0]
    first = cs[0][1] if not isinstance(cs, str) else None
    if first is not None:
        ensure(str(first).replace(" ", "") != str(viridis_first).replace(" ", "") or plasma_first == viridis_first, "initial colorscale is Viridis though Plasma requested")
    for kw in (dict(x_axis="strikes"), dict(colorscale="Jet")):
        try:
            viz.build_dashboard(s, quotes, params, **kw)
        except ValueError:
            continue
        raise AssertionError("build_dashboard(%r) must raise ValueError (7.1)" % (kw,))


@check
def c07_write_dashboard_file():
    bsp, syn, dio, srf, viz = imp()
    fig, s, quotes, params = _fig("k")
    d = tempfile.mkdtemp(prefix="vst_")
    try:
        out = os.path.join(d, "sub", "deeper", "x.html")
        ret = viz.write_dashboard(fig, out)
        ensure(os.path.isabs(ret) and os.path.samefile(ret, out), "must return the absolute path: %r" % ret)
        txt = open(out, encoding="utf-8").read()
        ensure("hovertemplate" in txt and "Strike: %{customdata[0]:.2f}" in txt and "Expiry:" in txt and "IV:" in txt, "html lacks hover fields")
        ensure("not guaranteed arbitrage-free" in txt and "IV surface" in txt, "html lacks title / surface trace")
        ensure("cdn.plot.ly" in txt and os.path.getsize(out) < 3_000_000, "default must be cdn (small file)")
        out2 = os.path.join(d, "inline.html")
        viz.write_dashboard(fig, out2, plotlyjs="inline")
        ensure(os.path.getsize(out2) > 1_000_000, "inline must embed plotly.js (size %d)" % os.path.getsize(out2))
        try:
            viz.write_dashboard(fig, os.path.join(d, "z.html"), plotlyjs="local")
        except ValueError:
            pass
        else:
            raise AssertionError("bad plotlyjs must raise ValueError (7.2)")
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ----------------------------------------------------------------------------------------------
# 9. End-to-end main.py (plan check 9, headless). Exit codes are read from the native process.
# ----------------------------------------------------------------------------------------------
def run_main(args, cwd):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=ROOT)
    p = subprocess.run([sys.executable, os.path.join(ROOT, "main.py")] + args, cwd=cwd, capture_output=True, env=env, timeout=300)
    return p.returncode, p.stdout, p.stderr


@check
def c09_main_end_to_end():
    d = tempfile.mkdtemp(prefix="vst_")
    try:
        out = os.path.join(d, "o.html")
        rc, so, se = run_main(["--no-open", "--out", out], d)
        ensure(rc == 0, "main.py --no-open rc=%d stderr=%s" % (rc, se[-400:]))
        ensure(so.isascii() and se.isascii(), "console output must be ASCII")
        txt = so.decode("ascii")
        ensure(os.path.isfile(out) and os.path.getsize(out) > 10_000, "output html missing/too small")
        for nm in ("newton", "brent", "out_of_bounds", "failed", "invalid_input"):
            ensure(nm in txt, "status breakdown lacks %r (zeros must be shown)" % nm)
        want = [imp()[3].DIAGNOSTIC_DISCLAIMER]
        ensure(want[0] in txt and re.search(r"calendar: \d+/\d+ violations", txt) and re.search(r"butterfly: \d+/\d+ violations", txt), "arbitrage lines not printed verbatim")
        ensure("%" in txt and os.path.abspath(out).lower() in txt.lower().replace("/", "\\") or out.lower() in txt.lower() or "o.html" in txt, "output path not printed")
        ensure("is arbitrage-free" not in txt.lower(), "console claims arbitrage-free")
        ensure(not os.path.exists(os.path.join(d, "vol_surface.html")), "--out ignored")
        # the written HTML is the dashboard
        h = open(out, encoding="utf-8").read()
        ensure("hovertemplate" in h and "not guaranteed arbitrage-free" in h, "html content")
        # variants
        for extra in (["--method", "spline"], ["--x-axis", "strike", "--colorscale", "Plasma"], ["--n-T", "20", "--n-k", "30"]):
            rc, so, se = run_main(["--no-open", "--out", os.path.join(d, "v.html")] + extra, d)
            ensure(rc == 0, "main.py %r rc=%d stderr=%s" % (extra, rc, se[-300:]))
    finally:
        shutil.rmtree(d, ignore_errors=True)


@check
def c09_main_csv_round_trip_and_exit_codes():
    d = tempfile.mkdtemp(prefix="vst_")
    try:
        chain_csv = os.path.join(d, "chain.csv")
        rc, so1, se = run_main(["--no-open", "--out", os.path.join(d, "a.html"), "--export-chain", chain_csv], d)
        ensure(rc == 0 and os.path.isfile(chain_csv), "export-chain rc=%d %s" % (rc, se[-300:]))
        back, rej = None, None
        rc, so2, se = run_main(["--no-open", "--out", os.path.join(d, "b.html"), "--csv", chain_csv, "--spot", "100", "--rate", "0.04", "--div", "0.015"], d)
        ensure(rc == 0, "--csv run rc=%d stderr=%s" % (rc, se[-300:]))

        def keyed(b):
            return [ln for ln in b.decode("ascii").splitlines() if re.search(r"(IV range|calendar:|butterfly:|newton|brent|out_of_bounds)", ln)]
        k1, k2 = keyed(so1), keyed(so2)
        ensure(len(k1) >= 4 and any("IV range" in x for x in k1) and any("calendar:" in x for x in k1),"anti-vacuity: too few comparable console lines (%d)" % len(k1))
        ensure(k1 == k2, "synthetic run and re-fed exported CSV disagree:\n%r\n%r" % (k1, k2))
        # exit-code contract (CONTRACT 8): 2 = usage/input error
        bad_cases = [(["--csv", chain_csv], "csv without --spot"),
                     (["--csv", os.path.join(d, "nope.csv"), "--spot", "100"], "missing csv"),
                     (["--csv", chain_csv, "--ticker", "SPY", "--spot", "100"], "csv + ticker"),
                     (["--method", "griddata"], "bad method"),
                     (["--x-axis", "z"], "bad axis")]
        badfile = os.path.join(d, "bad.csv")
        _write(badfile, "strike,price\n100,5\n")
        bad_cases.append((["--csv", badfile, "--spot", "100"], "csv missing required columns"))
        for args, why in bad_cases:
            rc, so, se = run_main(["--no-open", "--out", os.path.join(d, "c.html")] + args, d)
            ensure(rc == 2, "%s: exit code %d != 2" % (why, rc))
            ensure(se.isascii() and len(se) > 0, "%s: error text must be on stderr and ASCII" % why)
        ensure(not os.path.exists(os.path.join(d, "c.html")), "a failed run must not leave an html file")
        # exit 3: surface cannot be built (one maturity only)
        one = os.path.join(d, "one.csv")
        _write(one, "strike,type,price,T\n110,C,2.0,0.5\n120,C,0.9,0.5\n130,C,0.3,0.5\n140,C,0.1,0.5\n90,P,0.4,0.5\n")
        rc, so, se = run_main(["--no-open", "--out", os.path.join(d, "one.html"), "--csv", one, "--spot", "100", "--rate", "0.04", "--div", "0.0"], d)
        ensure(rc == 3, "single-maturity csv: exit code %d != 3 (build_surface ValueError)" % rc)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ----------------------------------------------------------------------------------------------
# runner
# ----------------------------------------------------------------------------------------------
def tick0_report():
    """Report-only (never asserted): in-domain butterfly counts on the noisy chain with tick=0."""
    bsp, syn, dio, srf, viz = imp()
    params = dio.MarketParams(S=syn.DEFAULT_S, r=syn.DEFAULT_R, q=syn.DEFAULT_Q)
    for tick in (0.01, 0.0):
        quotes = srf.prepare_quotes(syn.generate_chain(tick=tick), params)
        for method in ("rbf", "spline"):
            rp = srf.arbitrage_report(srf.build_surface(quotes, params, method=method))
            print("REPORT noisy chain tick=%s %s: butterfly %d/%d, calendar %d/%d" % (tick, method, rp["butterfly"]["n_violations"], rp["butterfly"]["n_checked"], rp["calendar"]["n_violations"], rp["calendar"]["n_checked"]))


def run_checks(only=None):
    failed = []
    for fn in CHECKS:
        if only and only not in fn.__name__:
            continue
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                fn()
            print("PASS %s" % fn.__name__)
        except Exception as e:           # AssertionError or an unexpected crash: both are red
            failed.append(fn.__name__)
            msg = str(e).replace("\n", " | ")
            kind = "FAIL" if isinstance(e, AssertionError) else "ERROR(%s)" % type(e).__name__
            print("%s %s: %s" % (kind, fn.__name__, msg[:600]))
            if not isinstance(e, AssertionError):
                tb = traceback.format_exc().splitlines()[-4:]
                print("    " + " / ".join(x.strip() for x in tb)[:500])
    return failed


# ----------------------------------------------------------------------------------------------
# mutation proof: every mutation is applied to a TEMP COPY; live hashes asserted unchanged
# ----------------------------------------------------------------------------------------------
# (name, file, regex, replacement, count_expected_min, checks that MUST be among the FAILED lines)
MUTATION_TABLE = [
    # (name, file, regex, replacement, checks of which at least one MUST be red)
    ("q_sign_in_d1", "bs_pricing.py", r"\(r - q \+ 0\.5 \* sigma \* sigma\) \* Tc\) / vol_safe", "(r + q + 0.5 * sigma * sigma) * Tc) / vol_safe",
     ["c01_bs_hand_value_and_independent_reference", "c10_generate_chain_contract"]),
    ("otm_boundary_to_put", "surface.py", r"OTM_CALL_AT_BOUNDARY = True", "OTM_CALL_AT_BOUNDARY = False",
     ["c02_otm_boundary_k_equals_zero_goes_to_call"]),
    ("term_structure_fixed_k_row", "surface.py", r"k = np\.log\(float\(Ks\) / np\.asarray\(surface\.params\.forward\(Tg\), dtype=np\.float64\)\)", "k = np.zeros_like(Tg)",
     ["c06_term_structure_per_maturity_mapping"]),
    ("calendar_check_blind", "surface.py", r"cal_viol = cal_mask & \(dw < -tol_calendar_w\)", "cal_viol = cal_mask & (dw < -1e9)",
     ["c05_calendar_clean_truth_zero_and_injected_detected"]),
    ("butterfly_check_blind", "surface.py", r"bf_viol = bf_mask & \(ds < -tol_butterfly\)", "bf_viol = bf_mask & (ds < -1e9)",
     ["c05_butterfly_independent_recount_and_injection"]),
    ("calendar_mask_removed_scope", "surface.py", r"cal_mask = ind\[:-1, :\] & ind\[1:, :\]", "cal_mask = np.ones_like(dw, dtype=bool)",
     ["c05_calendar_clean_truth_zero_and_injected_detected", "c05_arbitrage_report_format_and_wording"]),
    ("in_domain_old_union_rule", "surface.py", r"in_domain = \(k >= surface\.k_lo\) & \(k <= surface\.k_hi\)", "in_domain = (k >= surface.k_grid[0]) & (k <= surface.k_grid[-1])",
     ["c06_r10_in_domain_false_case_reachable_noisy_chain", "c06_term_structure_per_maturity_mapping"]),
    ("iv_returns_seed_value", "bs_pricing.py", r"iv\[idx\[done\]\] = sig\[done\]", "iv[idx[done]] = np.sqrt(2.0 * math.pi / ts[done]) * ps[done] / (ss[done] * np.exp(-qs[done] * ts[done]))",
     ["c02_iv_round_trip_clean_chain"]),
    ("viz_term_nan_mask_removed", "viz.py", r"y_pct = np\.where\(in_dom, 100\.0 \* ts\[\"iv\"\]\.to_numpy\(float\), np\.nan\)", "y_pct = 100.0 * ts[\"iv\"].to_numpy(float)",
     ["c06_r13_ox2_viz_gaps_where_out_of_domain_noisy_chain"]),
    ("viz_smile_nan_mask_removed", "viz.py", r"y_smile = np\.where\(dom, 100\.0 \* sm\[\"iv\"\]\.to_numpy\(float\), np\.nan\)", "y_smile = 100.0 * sm[\"iv\"].to_numpy(float)",
     ["c06_r13_ox2_viz_gaps_where_out_of_domain_noisy_chain"]),
    ("hover_drops_expiry", "viz.py", r"<br>Expiry: %\{customdata\[2\]\}", "<br>Exp: %{customdata[2]}",
     ["c07_dashboard_contract_from_fig_dict", "c07_write_dashboard_file"]),
    ("surface_z_in_decimals", "viz.py", r"Z = 100\.0 \* np\.asarray\(surface\.iv, float\)\.T", "Z = 1.0 * np.asarray(surface.iv, float).T",
     ["c07_dashboard_contract_from_fig_dict"]),
    ("loader_keeps_last_duplicate", "data_io.py", r"if key in seen:", "if False:",
     ["c11_loader_quarantine_and_control_total"]),
    ("iv_price_only_alone_vega_guard_masks", "bs_pricing.py", r"conv = usable & \(np\.abs\(diff\) <= tol\) & \(\(np\.abs\(step\) <= _SIGMA_RES\) \| \(diff == 0\.0\)\)", "conv = usable & (np.abs(diff) <= tol)",
     []),
    ("iv_price_only_and_no_vega_guard", "bs_pricing.py",
     [r"conv = usable & \(np\.abs\(diff\) <= tol\) & \(\(np\.abs\(step\) <= _SIGMA_RES\) \| \(diff == 0\.0\)\)", r"usable = vega >= 1e-8 "],
     ["conv = usable & (np.abs(diff) <= tol)", "usable = vega >= 0.0 "],
     ["c02_iv_round_trip_clean_chain"]),
]


def copy_tree(dst):
    os.makedirs(dst)
    for f in SOURCES + ["selftest.py"]:
        src = os.path.join(HERE if f == "selftest.py" else ROOT, f)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(dst, f))


def run_selftest_in(root, only=None):
    env = dict(os.environ, SELFTEST_ROOT=root, PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    cmd = [sys.executable, os.path.join(root, "selftest.py")] + (["--only", only] if only else [])
    p = subprocess.run(cmd, cwd=root, capture_output=True, env=env, timeout=900)
    out = p.stdout.decode("utf-8", "replace")
    failed = [ln.split()[1].rstrip(":") for ln in out.splitlines() if ln.startswith(("FAIL", "ERROR"))]
    return p.returncode, failed, out


def mutation_proof():
    table = globals().get("MUTATION_TABLE")
    ensure(table, "MUTATION_TABLE not defined")
    before = {f: sha(os.path.join(ROOT, f)) for f in SOURCES if os.path.isfile(os.path.join(ROOT, f))}
    base = tempfile.mkdtemp(prefix="vmut_")
    bad = 0
    try:
        # baseline: the unmutated copy must be as green/red as live (so a red mutation is attributable)
        b = os.path.join(base, "baseline")
        copy_tree(b)
        rc0, failed0, _ = run_selftest_in(b)
        print("BASELINE copy: rc=%d failed=%s" % (rc0, failed0))
        for name, fname, pattern, repl, must_fail in table:
            dst = os.path.join(base, name)
            copy_tree(dst)
            p = os.path.join(dst, fname)
            txt = open(p, encoding="utf-8").read()
            pats = pattern if isinstance(pattern, list) else [pattern]
            repls = repl if isinstance(repl, list) else [repl]
            new, n = txt, 0
            for pt, rp in zip(pats, repls):
                new, n1 = re.subn(pt, rp, new, flags=re.S)
                if n1 < 1:
                    n = 0
                    break
                n += n1
            if n < 1 or new == txt:
                print("MUTATION %-28s NOT APPLIED (pattern matched %d) -> proof invalid" % (name, n))
                bad += 1
                continue
            open(p, "w", encoding="utf-8", newline="").write(new)
            rc, failed, out = run_selftest_in(dst)
            new_red = [x for x in failed if x not in failed0]
            hit = [c for c in must_fail if c in failed]
            verdict = "RED as required" if (rc != 0 and hit) else "NOT CAUGHT"
            if not must_fail:
                verdict = "INFO (no red required; shows a second guard masks this mutation alone)"
            print("MUTATION %-28s applied x%d  rc=%d  required=%s  caught=%s  new_red=%s -> %s" % (name, n, rc, must_fail, hit, new_red, verdict))
            if verdict.startswith("NOT"):
                bad += 1
        after = {f: sha(os.path.join(ROOT, f)) for f in before}
        ensure(after == before, "LIVE SOURCE HASH CHANGED during mutation proof")
        print("live source hashes unchanged after proof: OK")
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return bad


def _load_mutation_table():
    p = os.path.join(HERE, "selftest_mutations.txt")
    return None


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--hashes" in args:
        for f in SOURCES + ["selftest.py"]:
            fp = os.path.join(HERE if f == "selftest.py" else ROOT, f)
            print("%s  %s" % (sha(fp) if os.path.isfile(fp) else "MISSING", f))
        sys.exit(0)
    if "--mutation-proof" in args:
        sys.exit(1 if mutation_proof() else 0)
    if "--report-tick0" in args:
        tick0_report()
        sys.exit(0)
    only = args[args.index("--only") + 1] if "--only" in args else None
    failed = run_checks(only)
    for n in NOTES:
        print("NOTE " + n)
    ran = [fn.__name__ for fn in CHECKS if not only or only in fn.__name__]
    if not ran:
        print("NO CHECKS RAN (filter %r)" % only)
        sys.exit(1)
    if failed:
        print("RESULT: %d of %d checks FAILED: %s" % (len(failed), len(ran), ", ".join(failed)))
        sys.exit(1)
    print("RESULT: all %d checks passed (content-level; see mutation proof for evidence the suite can fail)" % len(ran))
    sys.exit(0)
