#!/usr/bin/env python
"""
oracle_check.py - ORACLE lane (role: oracle-verifier), Volitility-Model.

Independent re-derivation of:
  * Black-Scholes-Merton European prices with a continuous dividend yield,
  * vega, no-arbitrage price bounds,
  * implied volatility (plain bisection, own status taxonomy per CONTRACT 2.3),
  * the SSVI ground truth of CONTRACT 4.1,
written from .claude/CONTRACT.md v1.0 and the textbook formula
  d1 = (ln(S/K) + (r - q + sigma^2/2) T) / (sigma sqrt T),  d2 = d1 - sigma sqrt T
  C  = S e^{-qT} N(d1) - K e^{-rT} N(d2),   P = K e^{-rT} N(-d2) - S e^{-qT} N(-d1)
BEFORE any built module was read. The oracle uses only math (erfc, exp, log)
and, as a second CDF implementation for calibration only, scipy.stats.norm.
It never imports bs_pricing for any expected value.

Then (sections bs / synth / surface) it imports the BUILT modules and compares.

Usage:
  python oracle_check.py [--src DIR] [--sections calib,bs,synth,surface]
    --src DIR   directory holding the built modules (default: this file's dir).
                Use a scratch COPY for isolation; the script removes its own
                dir and cwd from sys.path when --src points elsewhere.
Exit code: 0 iff every check in the requested sections passed, 1 otherwise,
2 on usage error. A missing module is a FAIL, not a skip.
Console output is ASCII only.
"""
import sys

sys.dont_write_bytecode = True  # never drop __pycache__ into the tree under test

import argparse
import dataclasses
import functools
import hashlib
import importlib
import itertools
import math
import os
import warnings

import numpy as np

# =============================================================================
# SPEC BLOCK - every constant the oracle relies on, with its CONTRACT.md ref.
# Spec in force when written: CONTRACT.md v1.0 only (REVIEW_A.md did not exist).
# A REVIEW_A ruling that changes one of these is a one-place edit HERE, with
# the ruling ID in the comment - never a silent tolerance tweak.
# =============================================================================
SPEC_VERSION = "CONTRACT.md v1.0 + team-lead ruling R-1 (no REVIEW_A.md at oracle write time)"
# R-1 (team lead, relayed by hub 2026-11-02): the 3.4 price-only acceptance is superseded by
# section 12 - IV is judged in VOL SPACE against the true sigma. The oracle bisection stops on
# bracket width (1e-15 in sigma), not on a price residual. Near-zero-price deep-OTM rows are
# reported as a SEPARATE class (check B6z), never mixed with B6e.
ORC_NEAR_ZERO_PRICE = 1e-6  # classification threshold only (price units); not a tolerance
SPEC_STATUS = {"newton": 0, "brent": 1, "out_of_bounds": 2, "failed": 3, "invalid_input": 4}  # 2.3
SPEC_STATUS_CONST = {"IV_STATUS_NEWTON": 0, "IV_STATUS_BRENT": 1, "IV_STATUS_OUT_OF_BOUNDS": 2,
                     "IV_STATUS_FAILED": 3, "IV_STATUS_INVALID_INPUT": 4}  # 2.3
SPEC_IV_MIN = 1e-4          # 2.3
SPEC_IV_MAX = 5.0           # 2.3
SPEC_BOUND_EPS = 1e-10      # 2.3, absolute price units
SPEC_SOLVER_TOL = 1e-8      # 3.4, absolute price residual
SPEC_DEGEN_SST = 1e-12      # 3.1, sigma*sqrt(T) below this -> discounted intrinsic
# SSVI truth, 4.1
SPEC_SSVI_RHO = -0.7
SPEC_SSVI_PHI = 1.5
SPEC_ATM_A0 = 0.18
SPEC_ATM_A1 = 0.06
SPEC_ATM_TAU = 1.0
# synthetic defaults, 4 / 4.2
SPEC_DEFAULT_S = 100.0
SPEC_DEFAULT_R = 0.04
SPEC_DEFAULT_Q = 0.015
SPEC_DEFAULT_MATS = (1 / 12, 2 / 12, 3 / 12, 6 / 12, 9 / 12, 1.0, 1.5, 2.0)
SPEC_DEFAULT_FRACS = tuple(np.arange(0.60, 1.40 + 1e-9, 0.025))
SPEC_CHAIN_COLS = ["strike", "T", "type", "price", "sigma_true"]                       # 2.1
SPEC_QUOTE_COLS = ["strike", "T", "type", "price", "F", "k", "iv", "w", "status", "sigma_true"]  # 2.2
SPEC_DEFAULT_MIN_PRICE = 0.05   # 4.2
SPEC_DEFAULT_TICK = 0.01        # 4.2
# acceptance tolerances, 12
SPEC_TOL_PARITY = 1e-10
SPEC_TOL_RT_CLEAN = 1e-6
SPEC_RT_MIN_FRAC = 0.90
SPEC_TOL_RT_NOISY = 0.02
SPEC_TOL_SURF = 0.01
SPEC_TOL_TS_DIFF = 1e-4
# diagnostics, 6.4
SPEC_TOL_CAL = 1e-6
SPEC_TOL_BFLY = 1e-8
# REVIEW_A R11(c) (binding over 6.4; landed 13:09 after the oracle was saved):
SPEC_DISCLAIMER = ("DIAGNOSTIC ONLY: these checks count violations at grid nodes inside the quoted domain; "
                   "they do not enforce or guarantee an arbitrage-free surface and say nothing about "
                   "extrapolated regions.")
# REVIEW_A R6: puts priced directly (no parity, no 1-N). Observable consequence checked by B1p:
# deep-OTM small prices carry full RELATIVE precision. Oracle-chosen rel limit:
ORC_SMALL_PRICE_RTOL = 1e-8
# Oracle-chosen comparison tolerances (not contract numbers; derived, stated once):
#  price compare: abs 1e-10 (= the contract parity tol, 12) + rel 1e-12 for large prices.
ORC_PRICE_ATOL = 1e-10
ORC_PRICE_RTOL = 1e-12
ORC_VEGA_ATOL = 1e-9
ORC_VEGA_RTOL = 1e-10
#  IV residual gate: contract 3.4 says converged iff |price(iv) - price| <= tol (1e-8);
#  slack 1e-11 covers oracle-vs-built pricer float differences (~1e-14).
ORC_RESID_SLACK = 1e-11
#  IV error gate where oracle vega >= 1e-2: residual 1e-8 / vega 1e-2 -> 1e-6.
ORC_IV_VEGA_FLOOR = 1e-2
ORC_IV_ERR = 1e-6


# =============================================================================
# ORACLE - scalar, math-only. Written from the spec before reading built code.
# =============================================================================
def o_ncdf(x):
    """Standard normal CDF via erfc (no cancellation in the deep left tail)."""
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def o_npdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _finite(*v):
    return all(isinstance(a, (int, float, np.floating, np.integer)) and math.isfinite(float(a)) for a in v)


def _isnan_any(*v):
    return any(math.isnan(float(a)) for a in v)


def o_forward(S, r, q, T):
    return S * math.exp((r - q) * T)


def o_intrinsic(S, K, T, r, q, is_call):
    Tc = max(T, 0.0)
    a = S * math.exp(-q * Tc)
    b = K * math.exp(-r * Tc)
    return max(a - b, 0.0) if is_call else max(b - a, 0.0)


def o_price(S, K, T, r, q, sigma, is_call, qs=1.0):
    """BSM price per CONTRACT 3.1. qs multiplies q INSIDE d1 only: qs=1.0 is the
    textbook formula; qs=-1.0 is the plan check-8 mutation (used only for the
    self-mutation gate)."""
    S, K, T, r, q, sigma = float(S), float(K), float(T), float(r), float(q), float(sigma)
    if _isnan_any(S, K, T, r, q, sigma):
        return float("nan")
    if S <= 0 or K <= 0 or sigma < 0:
        return float("nan")
    if T <= 0 or sigma <= 0 or sigma * math.sqrt(T) < SPEC_DEGEN_SST:
        return o_intrinsic(S, K, T, r, q, is_call)
    sst = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r - qs * q + 0.5 * sigma * sigma) * T) / sst
    d2 = d1 - sst
    dfq = math.exp(-q * T)
    dfr = math.exp(-r * T)
    if is_call:
        return S * dfq * o_ncdf(d1) - K * dfr * o_ncdf(d2)
    return K * dfr * o_ncdf(-d2) - S * dfq * o_ncdf(-d1)


def o_vega(S, K, T, r, q, sigma):
    """d price / d sigma per 1.00 of sigma (CONTRACT 3.2)."""
    S, K, T, r, q, sigma = float(S), float(K), float(T), float(r), float(q), float(sigma)
    if _isnan_any(S, K, T, r, q, sigma):
        return float("nan")
    if S <= 0 or K <= 0 or sigma < 0:
        return float("nan")
    if T <= 0 or sigma <= 0 or sigma * math.sqrt(T) < SPEC_DEGEN_SST:
        return 0.0
    sst = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / sst
    return S * math.exp(-q * T) * o_npdf(d1) * math.sqrt(T)


def o_bounds(S, K, T, r, q, is_call):
    """(lower, upper) no-arbitrage bounds per CONTRACT 3.3."""
    S, K, T, r, q = float(S), float(K), float(T), float(r), float(q)
    if _isnan_any(S, K, T, r, q) or S <= 0 or K <= 0:
        return float("nan"), float("nan")
    Tc = max(T, 0.0)
    a = S * math.exp(-q * Tc)
    b = K * math.exp(-r * Tc)
    if is_call:
        return max(a - b, 0.0), a
    return max(b - a, 0.0), b


O_SOLVED = 0  # oracle cannot tell newton from brent; built must return a code in {0,1}


def o_iv(price, S, K, T, r, q, is_call, pricer=o_price):
    """Implied vol by plain bisection on [IV_MIN, IV_MAX]. Returns (iv, code) with
    code 0 (= solved, built must be in {0,1}), 2, 3 or 4 per CONTRACT 2.3,
    evaluation order 4, then 2, then solve."""
    vals = [float(v) for v in (price, S, K, T, r, q)]
    if not all(math.isfinite(v) for v in vals):
        return float("nan"), 4
    price, S, K, T, r, q = vals
    if S <= 0 or K <= 0 or T <= 0 or price <= 0:
        return float("nan"), 4
    lb, ub = o_bounds(S, K, T, r, q, is_call)
    if price <= lb + SPEC_BOUND_EPS or price >= ub - SPEC_BOUND_EPS:
        return float("nan"), 2
    lo, hi = SPEC_IV_MIN, SPEC_IV_MAX
    flo = pricer(S, K, T, r, q, lo, is_call) - price
    fhi = pricer(S, K, T, r, q, hi, is_call) - price
    if flo > 0 or fhi < 0:
        return float("nan"), 3
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if pricer(S, K, T, r, q, mid, is_call) - price > 0:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-15:
            break
    return 0.5 * (lo + hi), O_SOLVED


def o_atm_vol(T):
    return SPEC_ATM_A0 + SPEC_ATM_A1 * (1.0 - math.exp(-T / SPEC_ATM_TAU))


def o_true_w(k, T):
    if not (math.isfinite(k) and math.isfinite(T)) or T <= 0:
        return float("nan")
    theta = T * o_atm_vol(T) ** 2
    rho, phi = SPEC_SSVI_RHO, SPEC_SSVI_PHI
    return 0.5 * theta * (1.0 + rho * phi * k + math.sqrt((phi * k + rho) ** 2 + 1.0 - rho * rho))


def o_true_vol(k, T):
    w = o_true_w(float(k), float(T))
    if math.isnan(w):
        return float("nan")
    return math.sqrt(w / float(T))


def o_domain(q_T, q_k, usable, dropped_T, T_grid, k_grid):
    """REVIEW_A R9 governing definition, own code path: per usable maturity (not dropped) the
    min/max k of status-{0,1} quotes, linearly interpolated in T onto T_grid."""
    q_T = np.asarray(q_T, float); q_k = np.asarray(q_k, float)
    drop = np.asarray(list(dropped_T), float)
    Tm, kmin, kmax = [], [], []
    for t in sorted(set(q_T[usable].tolist())):
        if drop.size and np.any(np.abs(drop - t) <= 1e-15):
            continue
        sel = usable & (q_T == t)
        Tm.append(t); kmin.append(float(q_k[sel].min())); kmax.append(float(q_k[sel].max()))
    k_lo = np.interp(T_grid, Tm, kmin)
    k_hi = np.interp(T_grid, Tm, kmax)
    dom = (k_lo[:, None] <= k_grid[None, :]) & (k_grid[None, :] <= k_hi[:, None])
    return k_lo, k_hi, dom


def o_calendar(w, tol, dom=None):
    """6.4 calendar count, scope per R11(a) when dom is given; own code path."""
    w = np.asarray(w, dtype=float)
    dw = w[1:, :] - w[:-1, :]
    pair = np.ones_like(dw, bool) if dom is None else (dom[1:, :] & dom[:-1, :])
    d = dw[pair]
    n_checked = int(d.size)
    n_viol = int(np.sum(d < -tol))
    maxv = float(max(0.0, float(np.max(-d)))) if d.size else 0.0
    return n_checked, n_viol, maxv


def o_butterfly(K, T_grid, iv, S, r, q, tol, dom=None, pricer=o_price):
    """6.4 butterfly count, scope per R11(b) when dom is given, repricing calls with the ORACLE pricer."""
    K = np.asarray(K, dtype=float)
    iv = np.asarray(iv, dtype=float)
    n_T, n_k = K.shape
    n_viol = 0
    n_chk = 0
    maxv = 0.0
    for i in range(n_T):
        C = np.array([pricer(S, K[i, j], T_grid[i], r, q, iv[i, j], True) for j in range(n_k)])
        s = np.diff(C) / np.diff(K[i])
        d = np.diff(s)
        trip = np.ones(n_k - 2, bool) if dom is None else (dom[i, :-2] & dom[i, 1:-1] & dom[i, 2:])
        d = d[trip]
        n_chk += int(d.size)
        n_viol += int(np.sum(d < -tol))
        if d.size:
            maxv = max(maxv, float(np.max(-d)))
    return n_chk, n_viol, max(0.0, maxv)


# vectorised wrappers over flat lists (oracle side; loops in python)
def ov_price(S, K, T, r, q, sig, isc, qs=1.0):
    return np.array([o_price(a, b, c, d, e, f, bool(g), qs=qs) for a, b, c, d, e, f, g in zip(S, K, T, r, q, sig, isc)])


def ov_vega(S, K, T, r, q, sig):
    return np.array([o_vega(a, b, c, d, e, f) for a, b, c, d, e, f in zip(S, K, T, r, q, sig)])


# =============================================================================
# Harness
# =============================================================================
def _ascii(s):
    return str(s).encode("ascii", "replace").decode("ascii")


class Report:
    def __init__(self):
        self.rows = []

    def check(self, cid, ok, msg, owner="-"):
        st = "PASS" if ok else "FAIL"
        self.rows.append((st, cid, owner, _ascii(msg)))
        print("[%s] %-6s owner=%-8s %s" % (st, cid, owner, _ascii(msg)))
        return bool(ok)

    def info(self, cid, msg):
        print("[INFO] %-6s %s" % (cid, _ascii(msg)))

    def fails(self):
        return [r for r in self.rows if r[0] == "FAIL"]


def cmp_arrays(got, exp, atol, rtol):
    """Elementwise compare. NaN==NaN counts as agreement; NaN vs number is a mismatch."""
    got = np.asarray(got, dtype=float).ravel()
    exp = np.asarray(exp, dtype=float).ravel()
    if got.shape != exp.shape:
        return {"n": int(exp.size), "n_bad": int(max(exp.size, 1)), "max_err": float("inf"),
                "worst": -1, "nan_mismatch": -1, "shape": "got %s exp %s" % (got.shape, exp.shape)}
    gn, en = np.isnan(got), np.isnan(exp)
    nan_mm = gn ^ en
    both = ~(gn | en)
    err = np.zeros_like(exp)
    err[both] = np.abs(got[both] - exp[both])
    bad = nan_mm.copy()
    bad[both] = err[both] > atol + rtol * np.abs(exp[both])
    score = err.copy()
    score[nan_mm] = np.inf
    worst = int(np.argmax(score)) if score.size else -1
    return {"n": int(exp.size), "n_bad": int(bad.sum()), "max_err": float(err.max()) if err.size else 0.0,
            "worst": worst, "nan_mismatch": int(nan_mm.sum()), "shape": "ok", "bad_mask": bad}


def fmt_cmp(c):
    return "n=%d bad=%d nan_mismatch=%d max_abs_err=%.3e worst_idx=%d shape=%s" % (
        c["n"], c["n_bad"], c["nan_mismatch"], c["max_err"], c["worst"], c["shape"])


def call_quiet(fn, *a, **kw):
    """Call built code, recording every warning; never raises."""
    with warnings.catch_warnings(record=True) as wl:
        warnings.simplefilter("always")
        try:
            out = fn(*a, **kw)
            exc = None
        except Exception as e:  # converted to a FAIL by the caller
            out, exc = None, e
    return out, list(wl), exc


def warn_summary(wl):
    return "; ".join("%s: %s" % (w.category.__name__, str(w.message)[:80]) for w in wl[:3])


def quiet_ok(rep, cid, what, wl, exc, owner):
    if exc is not None:
        return rep.check(cid, False, "%s raised %s: %s" % (what, type(exc).__name__, exc), owner)
    return rep.check(cid, len(wl) == 0, "%s emitted %d warnings %s" % (what, len(wl), warn_summary(wl)), owner)


SRC_FILES = ("bs_pricing.py", "synthetic.py", "data_io.py", "surface.py")


def sha_files(d):
    out = {}
    for f in SRC_FILES:
        p = os.path.join(d, f)
        if os.path.exists(p):
            with open(p, "rb") as fh:
                out[f] = hashlib.sha256(fh.read()).hexdigest()
        else:
            out[f] = "MISSING"
    return out


# =============================================================================
# Section calib - oracle vs known-good values; no built code touched.
# =============================================================================
HAND_S, HAND_K, HAND_T, HAND_R, HAND_Q, HAND_SIG = 100.0, 100.0, 1.0, 0.05, 0.02, 0.2
# Hand derivation: ln(S/K)=0; (r-q+sig^2/2)T = 0.03+0.02 = 0.05; sig*sqrtT = 0.2
#   d1 = 0.05/0.2 = 0.25, d2 = 0.05. N(0.25)=0.598706326, N(0.05)=0.519938806.
#   e^-0.02 = 0.980198673, e^-0.05 = 0.951229425.
#   C = 98.0198673*0.598706326 - 95.1229425*0.519938806 = 58.685114 - 49.458110 = 9.227005
#   P = C - (98.0198673 - 95.1229425) = 9.227005 - 2.896925 = 6.330080
HAND_C, HAND_P, HAND_TOL = 9.227005, 6.330080, 2e-5
# Hull, Options Futures and Other Derivatives, Example (S=42,K=40,r=0.1,T=0.5,sig=0.2,q=0):
HULL_C, HULL_P, HULL_TOL = 4.7594, 0.8086, 1e-4


def calib_hand_ok(pricer):
    c = pricer(HAND_S, HAND_K, HAND_T, HAND_R, HAND_Q, HAND_SIG, True)
    p = pricer(HAND_S, HAND_K, HAND_T, HAND_R, HAND_Q, HAND_SIG, False)
    return abs(c - HAND_C) <= HAND_TOL and abs(p - HAND_P) <= HAND_TOL, c, p


def section_calib(rep):
    print("--- section calib (oracle only, no built code) ---")
    c = o_price(42.0, 40.0, 0.5, 0.10, 0.0, 0.2, True)
    p = o_price(42.0, 40.0, 0.5, 0.10, 0.0, 0.2, False)
    rep.check("C1", abs(c - HULL_C) <= HULL_TOL and abs(p - HULL_P) <= HULL_TOL,
              "Hull example C=%.6f (ref %.4f) P=%.6f (ref %.4f)" % (c, HULL_C, p, HULL_P), "ORACLE")
    ok, c, p = calib_hand_ok(o_price)
    rep.check("C2", ok, "hand case S=K=100 T=1 r=.05 q=.02 s=.2: C=%.7f (hand %.6f) P=%.7f (hand %.6f)"
              % (c, HAND_C, p, HAND_P), "ORACLE")
    # second CDF implementation
    from scipy.stats import norm
    xs = np.linspace(-37.0, 8.0, 901)
    a = np.array([o_ncdf(x) for x in xs])
    b = norm.cdf(xs)
    rel = np.max(np.abs(a - b) / np.maximum(b, 1e-300))
    rep.check("C3", rel <= 1e-12, "erfc CDF vs scipy.stats.norm.cdf on [-37,8]: max rel err %.3e" % rel, "ORACLE")
    # oracle parity (puts priced directly, so this is a real identity check)
    rng = np.random.default_rng(12345)
    worst = 0.0
    for _ in range(2000):
        S = rng.uniform(50, 150); K = rng.uniform(40, 200); T = rng.uniform(1e-3, 5)
        r = rng.uniform(-0.01, 0.08); q = rng.uniform(0, 0.06); s = rng.uniform(0.02, 2.0)
        lhs = o_price(S, K, T, r, q, s, True) - o_price(S, K, T, r, q, s, False)
        rhs = S * math.exp(-q * T) - K * math.exp(-r * T)
        worst = max(worst, abs(lhs - rhs))
    rep.check("C4", worst <= SPEC_TOL_PARITY, "oracle put-call parity, 2000 random pts: max %.3e" % worst, "ORACLE")
    # vega closed form vs central FD of own price
    worst = 0.0
    for S, K, T, r, q, s in [(100, 100, 1, .05, .02, .2), (100, 70, .25, .03, .0, .4), (100, 140, 2, .04, .015, .25),
                             (50, 55, .1, .01, .03, .6), (100, 100, 1e-4, .05, .02, .3)]:
        h = 1e-5
        fd = (o_price(S, K, T, r, q, s + h, True) - o_price(S, K, T, r, q, s - h, True)) / (2 * h)
        v = o_vega(S, K, T, r, q, s)
        worst = max(worst, abs(fd - v) / max(abs(v), 1e-12))
    rep.check("C5", worst <= 1e-6, "oracle vega vs central FD of oracle price: max rel %.3e" % worst, "ORACLE")
    # oracle IV round trip
    worst = 0.0
    n = 0
    for K, T, s, isc in itertools.product([60, 90, 100, 110, 150], [0.05, 0.5, 2.0], [0.08, 0.3, 1.2], [True, False]):
        pr = o_price(100, K, T, .04, .015, s, isc)
        if o_vega(100, K, T, .04, .015, s) < ORC_IV_VEGA_FLOOR:
            continue
        iv, code = o_iv(pr, 100, K, T, .04, .015, isc)
        if code == O_SOLVED:
            n += 1
            worst = max(worst, abs(iv - s))
        else:
            worst = float("inf")
    rep.check("C6", n > 50 and worst <= 1e-9, "oracle IV round trip on %d vega-decent pts: max |iv-s| %.3e" % (n, worst), "ORACLE")
    # SSVI analytic self-check: at k=0, w = theta, so true_vol(0,T) = atm_vol(T)
    worst = max(abs(o_true_vol(0.0, T) - o_atm_vol(T)) for T in SPEC_DEFAULT_MATS)
    rep.check("C7", worst <= 1e-15, "SSVI true_vol(0,T) == atm_vol(T): max %.3e" % worst, "ORACLE")
    # truth calendar sanity on the default domain (w non-decreasing in T at fixed k)
    ks = np.linspace(-1.0, 1.0, 81)
    Ts = np.linspace(1 / 12, 2.0, 60)
    wgrid = np.array([[o_true_w(k, T) for k in ks] for T in Ts])
    nchk, nv, mv = o_calendar(wgrid, 0.0)
    rep.check("C8", nv == 0, "SSVI truth calendar on T[1/12,2] x k[-1,1]: %d/%d decreasing steps (max %.3e)" % (nv, nchk, mv), "ORACLE")
    # SELF-MUTATION: the q-sign-in-d1 mutation must turn the hand-case gate red
    mut = functools.partial(o_price, qs=-1.0)
    ok_m, cm, pm = calib_hand_ok(mut)
    rep.check("M1", (not ok_m) and abs(cm - HAND_C) > 1e-3,
              "mutation qs=-1 in d1 turns hand-case gate RED: C_mut=%.6f vs hand %.6f (gate ok=%s)" % (cm, HAND_C, ok_m), "ORACLE")


# =============================================================================
# Section bs - built bs_pricing vs oracle
# =============================================================================
def price_grid():
    Ks = [40.0, 60.0, 80.0, 95.0, 100.0, 105.0, 120.0, 150.0, 250.0]
    Ts = [1e-8, 1e-4, 1 / 52, 1 / 12, 0.25, 1.0, 2.0, 5.0]
    sig = [0.01, 0.05, 0.2, 0.5, 1.0, 3.0]
    rs = [0.0, 0.05, -0.01]
    qs = [0.0, 0.02, 0.06]
    rows = list(itertools.product(Ks, Ts, sig, rs, qs, [True, False]))
    a = np.array([[100.0, K, T, r, q, s] for K, T, s, r, q, _ in rows])
    isc = np.array([c for *_, c in rows], dtype=bool)
    return a[:, 0], a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5], isc


def section_bs(rep, bp):
    print("--- section bs (built bs_pricing vs oracle) ---")
    O = "BUILD-A"
    # B0 constants
    bad = []
    for name, val in SPEC_STATUS_CONST.items():
        if getattr(bp, name, None) != val:
            bad.append("%s=%r" % (name, getattr(bp, name, None)))
    names = getattr(bp, "IV_STATUS_NAMES", None)
    if names != {v: k for k, v in SPEC_STATUS.items()}:
        bad.append("IV_STATUS_NAMES=%r" % (names,))
    for name, val in (("IV_MIN", SPEC_IV_MIN), ("IV_MAX", SPEC_IV_MAX), ("BOUND_EPS", SPEC_BOUND_EPS)):
        if getattr(bp, name, None) != val:
            bad.append("%s=%r" % (name, getattr(bp, name, None)))
    rep.check("B0", not bad, "status constants / IV_MIN / IV_MAX / BOUND_EPS per 2.3: %s" % (bad or "all match"), O)

    S, K, T, r, q, sig, isc = price_grid()
    exp = ov_price(S, K, T, r, q, sig, isc)
    got, wl, exc = call_quiet(bp.bs_price, S, K, T, r, q, sig, isc)
    quiet_ok(rep, "B1w", "bs_price(grid %d pts)" % S.size, wl, exc, O)
    if exc is None:
        c = cmp_arrays(got, exp, ORC_PRICE_ATOL, ORC_PRICE_RTOL)
        msg = fmt_cmp(c)
        if c["worst"] >= 0 and c["n_bad"]:
            i = c["worst"]
            msg += " | worst: K=%g T=%g s=%g r=%g q=%g call=%s built=%.12g oracle=%.12g" % (
                K[i], T[i], sig[i], r[i], q[i], isc[i], np.ravel(got)[i], exp[i])
        rep.check("B1", c["n_bad"] == 0, "bs_price vs oracle (atol %.0e rtol %.0e): %s" % (ORC_PRICE_ATOL, ORC_PRICE_RTOL, msg), O)
        # R6 observable: small (deep OTM) prices keep relative precision
        gr = np.ravel(got)
        sm = (exp > 1e-300) & (exp < 1e-6)
        rel = np.abs(gr[sm] - exp[sm]) / exp[sm]
        nbad = int(np.sum(~(rel <= ORC_SMALL_PRICE_RTOL)))
        msg = "R6 small prices (1e-300<p<1e-6, %d rows: %d puts) rel err max %.3e, %d over %.0e" % (
            int(sm.sum()), int(np.sum(sm & ~isc)), float(np.nanmax(rel)) if rel.size else -1, nbad, ORC_SMALL_PRICE_RTOL)
        if nbad:
            i = np.where(sm)[0][int(np.nanargmax(np.where(np.isnan(rel), np.inf, rel)))]
            msg += " | worst K=%g T=%g s=%g call=%s built=%.6e oracle=%.6e" % (K[i], T[i], sig[i], isc[i], gr[i], exp[i])
        rep.check("B1p", sm.sum() > 0 and nbad == 0, msg, O)
        rep.check("B1d", isinstance(got, np.ndarray) and got.dtype == np.float64 and got.shape == S.shape,
                  "bs_price returns float64 ndarray of broadcast shape: type=%s dtype=%s shape=%s" % (
                      type(got).__name__, getattr(got, "dtype", None), getattr(got, "shape", None)), O)
        # SELF-MUTATION M2: same comparison against the q-sign mutated oracle must go red
        exp_m = ov_price(S, K, T, r, q, sig, isc, qs=-1.0)
        reached = int(np.sum(np.abs(exp_m - exp) > ORC_PRICE_ATOL))
        cm = cmp_arrays(got, exp_m, ORC_PRICE_ATOL, ORC_PRICE_RTOL)
        rep.check("M2", reached > 0 and cm["n_bad"] > 0,
                  "mutated oracle (qs=-1) differs from oracle on %d pts; same compare vs built flags %d mismatches" % (
                      reached, cm["n_bad"]), "ORACLE")
    # B2 parity on built
    rng = np.random.default_rng(777)
    n = 3000
    Sp = rng.uniform(50, 150, n); Kp = rng.uniform(40, 200, n); Tp = rng.uniform(1e-3, 5, n)
    rp = rng.uniform(-0.01, 0.08, n); qp = rng.uniform(0, 0.06, n); sp = rng.uniform(0.02, 2.0, n)
    (cc, w1, e1) = call_quiet(bp.bs_price, Sp, Kp, Tp, rp, qp, sp, True)
    (pp, w2, e2) = call_quiet(bp.bs_price, Sp, Kp, Tp, rp, qp, sp, False)
    if e1 is None and e2 is None:
        dev = np.abs(np.asarray(cc) - np.asarray(pp) - (Sp * np.exp(-qp * Tp) - Kp * np.exp(-rp * Tp)))
        rep.check("B2", float(np.nanmax(dev)) <= SPEC_TOL_PARITY and not np.isnan(dev).any(),
                  "built put-call parity, %d random pts: max %.3e (tol %.0e, 12)" % (n, float(np.nanmax(dev)), SPEC_TOL_PARITY), O)
        ce = ov_price(Sp, Kp, Tp, rp, qp, sp, np.ones(n, bool))
        c = cmp_arrays(cc, ce, ORC_PRICE_ATOL, ORC_PRICE_RTOL)
        rep.check("B2o", c["n_bad"] == 0, "built call vs oracle on parity grid: %s" % fmt_cmp(c), O)
    else:
        rep.check("B2", False, "bs_price raised on parity grid: %s / %s" % (e1, e2), O)

    # B3 degenerate and invalid inputs
    cases = [
        # (S, K, T, r, q, sigma, is_call, expected, label)
        (100, 90, 0.0, .05, .02, .2, True, o_intrinsic(100, 90, 0, .05, .02, True), "T=0 call -> intrinsic"),
        (100, 110, 0.0, .05, .02, .2, False, o_intrinsic(100, 110, 0, .05, .02, False), "T=0 put -> intrinsic"),
        (100, 90, -0.5, .05, .02, .2, True, 10.0, "T<0 call -> undiscounted intrinsic (T clipped to 0)"),
        (100, 90, 1.0, .05, .02, 0.0, True, o_intrinsic(100, 90, 1, .05, .02, True), "sigma=0 -> discounted intrinsic"),
        (100, 120, 1.0, .05, .02, 0.0, False, o_intrinsic(100, 120, 1, .05, .02, False), "sigma=0 put -> disc intrinsic"),
        (100, 90, 1.0, .05, .02, 1e-13, True, o_intrinsic(100, 90, 1, .05, .02, True), "sigma*sqrtT<1e-12 -> intrinsic"),
        (100, 90, 1e-30, .05, .02, .2, True, o_intrinsic(100, 90, 1e-30, .05, .02, True), "T=1e-30 -> intrinsic"),
        (100, 100, 1e-8, .05, .02, .2, True, o_price(100, 100, 1e-8, .05, .02, .2, True), "T=1e-8 ATM finite"),
        (100, 90, 1.0, .05, .02, -0.1, True, float("nan"), "sigma<0 -> NaN"),
        (0.0, 90, 1.0, .05, .02, .2, True, float("nan"), "S=0 -> NaN"),
        (-1.0, 90, 1.0, .05, .02, .2, True, float("nan"), "S<0 -> NaN"),
        (100, 0.0, 1.0, .05, .02, .2, True, float("nan"), "K=0 -> NaN"),
        (float("nan"), 90, 1.0, .05, .02, .2, True, float("nan"), "S NaN -> NaN"),
        (100, float("nan"), 1.0, .05, .02, .2, True, float("nan"), "K NaN -> NaN"),
        (100, 90, float("nan"), .05, .02, .2, True, float("nan"), "T NaN -> NaN"),
        (100, 90, 1.0, float("nan"), .02, .2, True, float("nan"), "r NaN -> NaN"),
        (100, 90, 1.0, .05, float("nan"), .2, True, float("nan"), "q NaN -> NaN"),
        (100, 90, 1.0, .05, .02, float("nan"), True, float("nan"), "sigma NaN -> NaN"),
    ]
    bad = []
    nwarn = 0
    for S_, K_, T_, r_, q_, s_, c_, e_, lab in cases:
        got, wl, exc = call_quiet(bp.bs_price, S_, K_, T_, r_, q_, s_, c_)
        nwarn += len(wl)
        if exc is not None:
            bad.append("%s: raised %s" % (lab, type(exc).__name__))
            continue
        g = float(got)
        if not isinstance(got, np.ndarray) or got.ndim != 0:
            bad.append("%s: not a 0-d ndarray (%s)" % (lab, type(got).__name__))
        if math.isnan(e_):
            if not math.isnan(g):
                bad.append("%s: got %.6g expected NaN" % (lab, g))
        elif not (abs(g - e_) <= ORC_PRICE_ATOL + ORC_PRICE_RTOL * abs(e_)):
            bad.append("%s: got %.12g expected %.12g" % (lab, g, e_))
    rep.check("B3", not bad, "bs_price degenerate/invalid cases (%d): %s" % (len(cases), "; ".join(bad) or "all match"), O)
    rep.check("B3w", nwarn == 0, "bs_price degenerate/invalid cases emitted %d warnings" % nwarn, O)
    # broadcasting and the one raise
    Kc = np.array([80.0, 100.0, 120.0])[:, None]
    Tc = np.array([0.1, 0.5, 1.0, 2.0])[None, :]
    got, wl, exc = call_quiet(bp.bs_price, 100.0, Kc, Tc, 0.04, 0.015, 0.25, True)
    ok = exc is None and np.shape(got) == (3, 4)
    if ok:
        e = np.array([[o_price(100, k, t, .04, .015, .25, True) for t in Tc[0]] for k in Kc[:, 0]])
        ok = cmp_arrays(got, e, ORC_PRICE_ATOL, ORC_PRICE_RTOL)["n_bad"] == 0
    rep.check("B3b", ok, "bs_price broadcasts (3,1)x(1,4) -> (3,4) and matches oracle: shape=%s exc=%s" % (np.shape(got), exc), O)
    got, wl, exc = call_quiet(bp.bs_price, np.ones(3) * 100, np.ones(4) * 100, 1.0, .05, .02, .2, True)
    rep.check("B3r", isinstance(exc, ValueError), "non-broadcastable shapes raise ValueError: got %s" % (type(exc).__name__ if exc else "no exception"), O)

    # B4 vega
    S, K, T, r, q, sig, isc = price_grid()
    m = isc  # vega has no is_call; use half the grid
    S, K, T, r, q, sig = S[m], K[m], T[m], r[m], q[m], sig[m]
    exp = ov_vega(S, K, T, r, q, sig)
    got, wl, exc = call_quiet(bp.bs_vega, S, K, T, r, q, sig)
    quiet_ok(rep, "B4w", "bs_vega(grid)", wl, exc, O)
    if exc is None:
        c = cmp_arrays(got, exp, ORC_VEGA_ATOL, ORC_VEGA_RTOL)
        rep.check("B4", c["n_bad"] == 0, "bs_vega vs oracle closed form (per 1.00 sigma): %s" % fmt_cmp(c), O)
    vcases = [((100, 90, 0.0, .05, .02, .2), 0.0, "T=0 -> 0"), ((100, 90, 1.0, .05, .02, 0.0), 0.0, "sigma=0 -> 0"),
              ((100, 90, 1.0, .05, .02, 1e-13), 0.0, "sst<1e-12 -> 0"), ((100, 90, 1.0, .05, .02, -0.1), float("nan"), "sigma<0 -> NaN"),
              ((0.0, 90, 1.0, .05, .02, .2), float("nan"), "S=0 -> NaN"), ((100, 0.0, 1.0, .05, .02, .2), float("nan"), "K=0 -> NaN"),
              ((100, 90, float("nan"), .05, .02, .2), float("nan"), "T NaN -> NaN")]
    bad = []
    for args, e_, lab in vcases:
        got, wl, exc = call_quiet(bp.bs_vega, *args)
        if exc is not None or wl:
            bad.append("%s: exc=%s warnings=%d" % (lab, exc, len(wl)))
            continue
        g = float(got)
        if (math.isnan(e_) and not math.isnan(g)) or (not math.isnan(e_) and g != e_):
            bad.append("%s: got %r" % (lab, g))
    rep.check("B4e", not bad, "bs_vega degenerate/invalid: %s" % ("; ".join(bad) or "all match"), O)

    # B5 price_bounds
    S, K, T, r, q, sig, isc = price_grid()
    lo_e = np.array([o_bounds(a, b, c, d, e, bool(f))[0] for a, b, c, d, e, f in zip(S, K, T, r, q, isc)])
    hi_e = np.array([o_bounds(a, b, c, d, e, bool(f))[1] for a, b, c, d, e, f in zip(S, K, T, r, q, isc)])
    got, wl, exc = call_quiet(bp.price_bounds, S, K, T, r, q, isc)
    quiet_ok(rep, "B5w", "price_bounds(grid)", wl, exc, O)
    if exc is None:
        ok_t = isinstance(got, tuple) and len(got) == 2
        rep.check("B5t", ok_t, "price_bounds returns a 2-tuple: %s" % type(got).__name__, O)
        if ok_t:
            c1 = cmp_arrays(got[0], lo_e, ORC_PRICE_ATOL, ORC_PRICE_RTOL)
            c2 = cmp_arrays(got[1], hi_e, ORC_PRICE_ATOL, ORC_PRICE_RTOL)
            rep.check("B5", c1["n_bad"] == 0 and c2["n_bad"] == 0, "price_bounds vs oracle: lower %s | upper %s" % (fmt_cmp(c1), fmt_cmp(c2)), O)
    bad = []
    for args, lab in [((0.0, 90, 1, .05, .02, True), "S=0"), ((100, -5, 1, .05, .02, False), "K<0"),
                      ((100, 90, float("nan"), .05, .02, True), "T NaN")]:
        got, wl, exc = call_quiet(bp.price_bounds, *args)
        if exc is not None or not (math.isnan(float(got[0])) and math.isnan(float(got[1]))):
            bad.append("%s: %s exc=%s" % (lab, got, exc))
    got, wl, exc = call_quiet(bp.price_bounds, 100.0, 90.0, -1.0, .05, .02, True)
    if exc is not None or abs(float(got[0]) - 10.0) > 1e-12 or abs(float(got[1]) - 100.0) > 1e-12:
        bad.append("T<0 clip: %s exc=%s (expected (10,100))" % (got, exc))
    rep.check("B5e", not bad, "price_bounds invalid/clip cases: %s" % ("; ".join(bad) or "all match"), O)

    section_iv(rep, bp)


def iv_grid():
    Ks = [50.0, 70.0, 85.0, 95.0, 100.0, 105.0, 115.0, 130.0, 160.0, 200.0]
    Ts = [1 / 52, 1 / 12, 0.25, 0.5, 1.0, 2.0, 3.0]
    sig = [0.05, 0.12, 0.25, 0.5, 0.9, 1.5]
    rq = [(0.04, 0.015), (0.0, 0.0), (0.06, 0.03), (-0.005, 0.02)]
    rows = list(itertools.product(Ks, Ts, sig, rq, [True, False]))
    S = np.full(len(rows), 100.0)
    K = np.array([x[0] for x in rows]); T = np.array([x[1] for x in rows]); s = np.array([x[2] for x in rows])
    r = np.array([x[3][0] for x in rows]); q = np.array([x[3][1] for x in rows]); c = np.array([x[4] for x in rows], bool)
    return S, K, T, r, q, s, c


def section_iv(rep, bp):
    O = "BUILD-A"
    S, K, T, r, q, s, c = iv_grid()
    price = ov_price(S, K, T, r, q, s, c)  # ORACLE prices: non-circular input
    out, wl, exc = call_quiet(bp.implied_vol, price, S, K, T, r, q, c)
    quiet_ok(rep, "B6w", "implied_vol(oracle-priced grid %d pts)" % S.size, wl, exc, O)
    if exc is not None:
        return
    ok_t = isinstance(out, tuple) and len(out) == 2
    rep.check("B6t", ok_t, "implied_vol returns (iv, status)", O)
    if not ok_t:
        return
    iv, st = np.asarray(out[0]), np.asarray(out[1])
    rep.check("B6d", iv.dtype == np.float64 and st.dtype == np.int8 and iv.shape == S.shape and st.shape == S.shape,
              "dtypes/shapes: iv %s %s, status %s %s (want float64/int8, %s)" % (iv.dtype, iv.shape, st.dtype, st.shape, S.shape), O)
    rep.check("B6n", bool(np.all(np.isfinite(iv) == np.isin(st, [0, 1]))),
              "iv finite <=> status in {0,1} (2.3): violations %d" % int(np.sum(np.isfinite(iv) != np.isin(st, [0, 1]))), O)
    # expected status class from the oracle
    exp_cls = np.empty(S.size, dtype=int)
    ambiguous = 0
    for i in range(S.size):
        lb, ub = o_bounds(S[i], K[i], T[i], r[i], q[i], bool(c[i]))
        if abs(price[i] - (lb + SPEC_BOUND_EPS)) < 1e-13 or abs(price[i] - (ub - SPEC_BOUND_EPS)) < 1e-13:
            exp_cls[i] = -1
            ambiguous += 1
            continue
        exp_cls[i] = o_iv(price[i], S[i], K[i], T[i], r[i], q[i], bool(c[i]))[1]
    solved_exp = exp_cls == O_SOLVED
    mism = []
    for i in range(S.size):
        if exp_cls[i] < 0:
            continue
        ok = (st[i] in (0, 1)) if exp_cls[i] == O_SOLVED else (st[i] == exp_cls[i])
        if not ok:
            mism.append(i)
    msg = "expected solvable=%d, out_of_bounds=%d, failed=%d, ambiguous(skipped)=%d; status mismatches=%d" % (
        int(solved_exp.sum()), int(np.sum(exp_cls == 2)), int(np.sum(exp_cls == 3)), ambiguous, len(mism))
    if mism:
        i = mism[0]
        msg += " | first: K=%g T=%g s=%g r=%g q=%g call=%s price=%.6g built_status=%d oracle=%d" % (
            K[i], T[i], s[i], r[i], q[i], c[i], price[i], st[i], exp_cls[i])
    rep.check("B6s", not mism and solved_exp.sum() > 0.5 * S.size, msg, O)
    rep.info("B6i", "built status counts: %s" % {int(k): int(v) for k, v in zip(*np.unique(st, return_counts=True))})
    # residual gate (contract 3.4 convergence definition) with the ORACLE pricer
    m = np.isin(st, [0, 1])
    resid = np.array([abs(o_price(S[i], K[i], T[i], r[i], q[i], iv[i], bool(c[i])) - price[i]) for i in np.where(m)[0]])
    lim = SPEC_SOLVER_TOL + ORC_RESID_SLACK
    rep.check("B6r", resid.size > 0 and float(resid.max()) <= lim,
              "|oracle_price(iv_built) - price| over %d solved rows: max %.3e (limit tol+slack %.3e)" % (resid.size, float(resid.max()) if resid.size else -1, lim), O)
    # iv accuracy where vega is decent
    veg = ov_vega(S, K, T, r, q, s)
    mv = m & (veg >= ORC_IV_VEGA_FLOOR)
    err = np.abs(iv[mv] - s[mv])
    rep.check("B6e", mv.sum() > 0 and float(err.max()) <= ORC_IV_ERR,
              "|iv_built - sigma| where vega>=%.0e (%d rows): max %.3e (limit %.0e)" % (ORC_IV_VEGA_FLOOR, int(mv.sum()), float(err.max()) if err.size else -1, ORC_IV_ERR), O)
    # R-1: vol-space accuracy on the remaining solved rows, split into two reported classes
    ml = m & (veg < ORC_IV_VEGA_FLOOR)
    for cid, cls, lab in (("B6l", ml & (price >= ORC_NEAR_ZERO_PRICE), "low-vega, price>=1e-6"),
                          ("B6z", ml & (price < ORC_NEAR_ZERO_PRICE), "near-zero-price deep OTM, price<1e-6")):
        if cls.any():
            e_ = np.abs(iv[cls] - s[cls])
            nb = int(np.sum(e_ > ORC_IV_ERR))
            j = int(np.argmax(e_)); ii = np.where(cls)[0][j]
            rep.check(cid, nb == 0, "R-1 vol-space |iv_built - sigma| on %s solved rows (%d): %d over %.0e, max %.3e | worst K=%g T=%g s=%g r=%g q=%g call=%s price=%.3e iv=%.8f" % (
                lab, int(cls.sum()), nb, ORC_IV_ERR, float(e_.max()), K[ii], T[ii], s[ii], r[ii], q[ii], c[ii], price[ii], iv[ii]), O)
        else:
            rep.info(cid, "no solved rows in class %s" % lab)
    # oracle's own bisection on the same rows (R-1: must match sigma within 1e-6 everywhere it solves)
    oe = []
    for i in np.where(solved_exp)[0]:
        v, _ = o_iv(price[i], S[i], K[i], T[i], r[i], q[i], bool(c[i]))
        oe.append(abs(v - s[i]))
    rep.check("C10", len(oe) > 0 and max(oe) <= ORC_IV_ERR, "oracle bisection |iv - sigma| over %d solvable grid rows: max %.3e" % (len(oe), max(oe) if oe else -1), "ORACLE")
    # SELF-MUTATION M3: the residual gate re-run with the q-mutated pricer must go red
    resid_m = np.array([abs(o_price(S[i], K[i], T[i], r[i], q[i], iv[i], bool(c[i]), qs=-1.0) - price[i]) for i in np.where(m)[0]])
    nred = int(np.sum(resid_m > lim))
    rep.check("M3", nred > 0, "residual gate with q-mutated pricer flags %d of %d solved rows (must be > 0)" % (nred, resid_m.size), "ORACLE")

    # B7 constructed status cases
    lbK80 = o_bounds(100, 80, 1, .05, .02, True)[0]
    ub_c = o_bounds(100, 100, 1, .05, .02, True)[1]
    ub_p = o_bounds(100, 100, 1, .05, .02, False)[1]
    p_hi = 0.5 * (o_price(100, 100, 1, .05, .02, SPEC_IV_MAX, True) + ub_c)
    Fk = o_forward(100, .05, .02, 1.0)
    p_lo = 0.5 * o_price(100, Fk, 1, .05, .02, SPEC_IV_MIN, True)
    p_t8 = o_price(100, 100, 1e-8, .05, .02, .2, True)
    p_dotm = o_price(100, 130, 0.05, .04, .015, .3, True)
    hand = o_price(HAND_S, HAND_K, HAND_T, HAND_R, HAND_Q, HAND_SIG, True)
    inf = float("inf"); nan = float("nan")
    cases = [  # price, S, K, T, r, q, call, expected status (0 = {0,1}), label
        (-1.0, 100, 100, 1, .05, .02, True, 4, "negative price -> 4 (4 before 2)"),
        (0.0, 100, 100, 1, .05, .02, True, 4, "zero price -> 4"),
        (nan, 100, 100, 1, .05, .02, True, 4, "NaN price -> 4"),
        (inf, 100, 100, 1, .05, .02, True, 4, "inf price -> 4"),
        (5.0, 0.0, 100, 1, .05, .02, True, 4, "S=0 -> 4"),
        (5.0, 100, -1.0, 1, .05, .02, True, 4, "K<0 -> 4"),
        (5.0, 100, 100, 0.0, .05, .02, True, 4, "T=0 -> 4"),
        (5.0, 100, 100, -1.0, .05, .02, True, 4, "T<0 -> 4"),
        (5.0, 100, 100, 1, nan, .02, True, 4, "r NaN -> 4"),
        (5.0, 100, 100, 1, .05, inf, True, 4, "q inf -> 4"),
        (lbK80, 100, 80, 1, .05, .02, True, 2, "price == lower bound -> 2"),
        (lbK80 + 0.5e-10, 100, 80, 1, .05, .02, True, 2, "price within BOUND_EPS of lower -> 2"),
        (lbK80 - 0.5, 100, 80, 1, .05, .02, True, 2, "price below intrinsic -> 2"),
        (ub_c, 100, 100, 1, .05, .02, True, 2, "call price == upper bound -> 2"),
        (ub_c + 0.01, 100, 100, 1, .05, .02, True, 2, "call price > upper bound -> 2"),
        (ub_p, 100, 100, 1, .05, .02, False, 2, "put price == upper bound -> 2"),
        (1e-12, 100, 200, 1 / 365, .04, .015, True, 2, "deep OTM short T price 1e-12 -> 2"),
        (p_hi, 100, 100, 1, .05, .02, True, 3, "in bounds but above BS(IV_MAX) -> 3"),
        (p_lo, 100, Fk, 1, .05, .02, True, 3, "K=F, price below BS(IV_MIN) -> 3"),
        (hand, HAND_S, HAND_K, HAND_T, HAND_R, HAND_Q, True, 0, "hand case -> solved"),
        (p_t8, 100, 100, 1e-8, .05, .02, True, 0, "T=1e-8 ATM -> solved, no warn"),
        (p_dotm, 100, 130, 0.05, .04, .015, True, 0, "deep OTM short T low vega -> solved"),
        (5e-9, 100, 130, 0.05, .04, .015, True, 0, "R-2: OTM call price 5e-9 in (1e-10,1e-8] -> solved, not 2"),
        (2e-10, 100, 75, 0.05, .04, .015, False, 0, "R-2: OTM put price 2e-10 in (1e-10,1e-8] -> solved, not 2"),
    ]
    # calibrate the cases against the oracle itself first
    cal_bad = [lab for (p_, S_, K_, T_, r_, q_, c_, e_, lab) in cases if o_iv(p_, S_, K_, T_, r_, q_, c_)[1] != e_]
    rep.check("C9", not cal_bad, "oracle agrees with every constructed status case: %s" % (cal_bad or "all"), "ORACLE")
    bad = []
    nwarn = 0
    for p_, S_, K_, T_, r_, q_, c_, e_, lab in cases:
        out, wl, exc = call_quiet(bp.implied_vol, p_, S_, K_, T_, r_, q_, c_)
        nwarn += len(wl)
        if exc is not None:
            bad.append("%s: raised %s: %s" % (lab, type(exc).__name__, exc))
            continue
        ivv, stt = out
        if np.ndim(ivv) != 0 or np.ndim(stt) != 0:
            bad.append("%s: scalar input not 0-d (%s,%s)" % (lab, np.shape(ivv), np.shape(stt)))
        si = int(stt)
        okc = (si in (0, 1)) if e_ == 0 else (si == e_)
        if not okc:
            bad.append("%s: status %d expected %s" % (lab, si, "{0,1}" if e_ == 0 else e_))
        if (si in (0, 1)) != bool(np.isfinite(float(ivv))):
            bad.append("%s: iv=%r inconsistent with status %d" % (lab, float(ivv), si))
        if e_ == 0 and si in (0, 1):
            res = abs(o_price(S_, K_, T_, r_, q_, float(ivv), c_) - p_)
            if res > SPEC_SOLVER_TOL + ORC_RESID_SLACK:
                bad.append("%s: residual %.3e" % (lab, res))
        if lab == "hand case -> solved" and si in (0, 1) and abs(float(ivv) - HAND_SIG) > 1e-6:
            bad.append("hand case iv %.10f != 0.2" % float(ivv))
    rep.check("B7", not bad, "implied_vol constructed status cases (%d): %s" % (len(cases), "; ".join(bad) or "all match"), O)
    rep.check("B7w", nwarn == 0, "implied_vol constructed cases emitted %d warnings" % nwarn, O)
    # vectorised call of the same cases must give the same statuses as the scalar calls
    arr = [np.array([cs[j] for cs in cases], dtype=float) for j in range(6)]
    cc = np.array([cs[6] for cs in cases], dtype=bool)
    out, wl, exc = call_quiet(bp.implied_vol, *arr, cc)
    if exc is None:
        stv = np.asarray(out[1])
        exp_v = np.array([cs[7] for cs in cases])
        okv = np.where(exp_v == 0, np.isin(stv, [0, 1]), stv == exp_v)
        rep.check("B7v", bool(okv.all()) and not wl, "vectorised constructed cases: %d/%d statuses match, %d warnings" % (int(okv.sum()), okv.size, len(wl)), O)
    else:
        rep.check("B7v", False, "vectorised constructed cases raised %s: %s" % (type(exc).__name__, exc), O)


# =============================================================================
# Section synth - built synthetic vs oracle truth and oracle prices
# =============================================================================
def otm_mask(strike, T, typ, S, r, q):
    F = np.array([o_forward(S, r, q, t) for t in T])
    k = np.log(np.asarray(strike) / F)
    typ = np.asarray(typ)
    return ((typ == "P") & (k < 0)) | ((typ == "C") & (k >= 0)), F, k


def section_synth(rep, sy, bp):
    print("--- section synth (built synthetic vs oracle) ---")
    O = "BUILD-A"
    bad = []
    for name, val in (("DEFAULT_S", SPEC_DEFAULT_S), ("DEFAULT_R", SPEC_DEFAULT_R), ("DEFAULT_Q", SPEC_DEFAULT_Q)):
        if getattr(sy, name, None) != val:
            bad.append("%s=%r" % (name, getattr(sy, name, None)))
    mats = getattr(sy, "DEFAULT_MATURITIES_YEARS", None)
    if mats is None or len(mats) != len(SPEC_DEFAULT_MATS) or np.max(np.abs(np.array(mats, float) - np.array(SPEC_DEFAULT_MATS))) > 1e-15:
        bad.append("DEFAULT_MATURITIES_YEARS=%r" % (mats,))
    fr = getattr(sy, "DEFAULT_STRIKE_FRACTIONS", None)
    if fr is None or len(fr) != len(SPEC_DEFAULT_FRACS) or np.max(np.abs(np.array(fr, float) - np.array(SPEC_DEFAULT_FRACS))) > 1e-12:
        bad.append("DEFAULT_STRIKE_FRACTIONS len=%s" % (None if fr is None else len(fr)))
    rep.check("S0", not bad, "synthetic module constants per 4: %s" % (bad or "all match"), O)

    ks = np.linspace(-1.2, 1.0, 45)
    Ts = np.array([1 / 52, 1 / 12, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0])
    KK, TT = np.meshgrid(ks, Ts)
    exp = np.array([[o_true_vol(k, t) for k in ks] for t in Ts])
    got, wl, exc = call_quiet(sy.true_vol, KK, TT)
    quiet_ok(rep, "S1w", "true_vol(grid)", wl, exc, O)
    if exc is None:
        c = cmp_arrays(got, exp, 1e-12, 1e-12)
        rep.check("S1", c["n_bad"] == 0 and np.shape(got) == KK.shape, "true_vol vs oracle SSVI (4.1): %s" % fmt_cmp(c), O)
    got, wl, exc = call_quiet(sy.true_vol, np.array([0.0, 0.1, -0.1]), np.array([0.0, -1.0, float("nan")]))
    rep.check("S1n", exc is None and bool(np.all(np.isnan(np.asarray(got, float)))),
              "true_vol T<=0 / NaN -> NaN: got %s exc=%s warnings=%d" % (got, exc, len(wl)), O)

    # clean chain
    clean, wl, exc = call_quiet(sy.generate_chain, noise_bps=0.0, tick=0.0, min_price=0.0)
    quiet_ok(rep, "S2w", "generate_chain(clean)", wl, exc, O)
    if exc is not None:
        return None
    rep.check("S2c", list(clean.columns) == SPEC_CHAIN_COLS, "clean chain columns %s (want %s)" % (list(clean.columns), SPEC_CHAIN_COLS), O)
    S, r, q = SPEC_DEFAULT_S, SPEC_DEFAULT_R, SPEC_DEFAULT_Q
    exp_rows = []
    for T in SPEC_DEFAULT_MATS:
        for f in SPEC_DEFAULT_FRACS:
            K = f * S
            sg = o_true_vol(math.log(K / o_forward(S, r, q, T)), T)
            for typ in ("C", "P"):
                p = o_price(S, K, T, r, q, sg, typ == "C")
                if p > 0:
                    exp_rows.append((T, K, typ, p, sg))
    exp_rows.sort(key=lambda x: (x[0], x[1], 0 if x[2] == "C" else 1))
    rep.check("S2n", len(clean) == len(exp_rows), "clean chain rows %d vs oracle %d (8 mats x 33 strikes x 2, price>0)" % (len(clean), len(exp_rows)), O)
    if len(clean) == len(exp_rows):
        e = np.array([(x[0], x[1], x[3], x[4]) for x in exp_rows])
        etype = np.array([x[2] for x in exp_rows])
        cT = cmp_arrays(clean["T"].to_numpy(float), e[:, 0], 1e-14, 0)
        cK = cmp_arrays(clean["strike"].to_numpy(float), e[:, 1], 1e-9, 0)
        tmatch = bool(np.all(clean["type"].to_numpy(dtype=object) == etype))
        rep.check("S2o", cT["n_bad"] == 0 and cK["n_bad"] == 0 and tmatch,
                  "clean chain (T,strike,type) order per 2.1 matches oracle sort: T %s | K %s | type match %s" % (fmt_cmp(cT), fmt_cmp(cK), tmatch), O)
        rep.check("S2i", list(clean.index) == list(range(len(clean))), "clean chain has RangeIndex 0..n-1", O)
    # sigma_true and price from the BUILT row's own K,T (no key alignment needed)
    K = clean["strike"].to_numpy(float); T = clean["T"].to_numpy(float); ty = clean["type"].to_numpy(dtype=object)
    sg_e = np.array([o_true_vol(math.log(k / o_forward(S, r, q, t)), t) for k, t in zip(K, T)])
    c = cmp_arrays(clean["sigma_true"].to_numpy(float), sg_e, 1e-12, 1e-12)
    rep.check("S3", c["n_bad"] == 0, "clean sigma_true vs oracle true_vol(ln(K/F_oracle),T): %s" % fmt_cmp(c), O)
    p_e = np.array([o_price(S, k, t, r, q, sg, typ == "C") for k, t, sg, typ in zip(K, T, sg_e, ty)])
    c = cmp_arrays(clean["price"].to_numpy(float), p_e, ORC_PRICE_ATOL, ORC_PRICE_RTOL)
    rep.check("S4", c["n_bad"] == 0, "clean prices vs ORACLE price at oracle sigma_true: %s" % fmt_cmp(c), O)
    # flow-lead item 4: built bs_price vs oracle price on every clean-chain row, with the worst row
    bpx, wlb, eb = call_quiet(bp.bs_price, S, K, T, r, q, sg_e, ty == "C")
    if eb is None:
        bpx = np.asarray(bpx, float)
        cb = cmp_arrays(bpx, p_e, ORC_PRICE_ATOL, ORC_PRICE_RTOL)
        ae = np.abs(bpx - p_e)
        re_ = np.where(p_e > 0, ae / np.where(p_e > 0, p_e, 1.0), 0.0)
        ia, ir = int(np.argmax(ae)), int(np.argmax(re_))
        rep.check("S4b", cb["n_bad"] == 0 and not wlb,
                  "built bs_price vs oracle on all %d clean rows: max abs %.3e at (K=%g T=%.4f %s p=%.6e) ; max rel %.3e at (K=%g T=%.4f %s p=%.6e)" % (
                      len(K), ae[ia], K[ia], T[ia], ty[ia], p_e[ia], re_[ir], K[ir], T[ir], ty[ir], p_e[ir]), O)
    else:
        rep.check("S4b", False, "bs_price raised on clean chain: %s" % eb, O)

    # round trip on the clean chain: built implied_vol, OTM rows selected by the oracle
    m, F, k = otm_mask(K, T, ty, S, r, q)
    px = clean["price"].to_numpy(float)
    out, wl, exc = call_quiet(bp.implied_vol, px[m], S, K[m], T[m], r, q, ty[m] == "C")
    quiet_ok(rep, "S5w", "implied_vol(clean OTM chain)", wl, exc, O)
    if exc is None:
        iv, st = np.asarray(out[0]), np.asarray(out[1])
        ok = np.isin(st, [0, 1])
        frac = float(ok.mean())
        err = np.abs(iv[ok] - clean["sigma_true"].to_numpy(float)[m][ok])
        mx = float(err.max()) if err.size else float("inf")
        rep.check("S5", mx <= SPEC_TOL_RT_CLEAN and frac >= SPEC_RT_MIN_FRAC,
                  "12 clean round trip on %d OTM rows: solved frac %.4f (min %.2f), max |iv-sigma_true| %.3e (tol %.0e)" % (
                      int(m.sum()), frac, SPEC_RT_MIN_FRAC, mx, SPEC_TOL_RT_CLEAN), O)
        if err.size and mx > SPEC_TOL_RT_CLEAN:
            j = int(np.argmax(err)); idx = np.where(m)[0][np.where(ok)[0][j]]
            rep.info("S5x", "worst row: K=%g T=%g type=%s price=%.6g vega=%.3e iv=%.8f sigma_true=%.8f" % (
                K[idx], T[idx], ty[idx], px[idx], o_vega(S, K[idx], T[idx], r, q, sg_e[idx]), iv[np.where(ok)[0][j]], sg_e[idx]))
        # oracle's own IV on the same prices, for comparison
        o_err = []
        o_codes = {}
        for i in np.where(m)[0]:
            v, code = o_iv(px[i], S, K[i], T[i], r, q, ty[i] == "C")
            o_codes[code] = o_codes.get(code, 0) + 1
            if code == O_SOLVED:
                o_err.append(abs(v - sg_e[i]))
        rep.check("S5o", len(o_err) > 0 and max(o_err) <= SPEC_TOL_RT_CLEAN,
                  "R-1 oracle bisection IV on the same %d clean OTM rows: codes %s, max |iv-sigma_true| %.3e (tol %.0e)" % (
                      int(m.sum()), o_codes, max(o_err) if o_err else -1, SPEC_TOL_RT_CLEAN), "ORACLE")
        # rows the oracle solves but the built code does not, and vice versa (each reported)
        sel = np.where(m)[0]
        ocode = np.array([o_iv(px[i], S, K[i], T[i], r, q, ty[i] == "C")[1] for i in sel])
        disagree = int(np.sum((ocode == O_SOLVED) != ok))
        rep.check("S5s", disagree == 0, "clean chain solved-set agreement built vs oracle: %d rows disagree (built solved %d, oracle solved %d)" % (
            disagree, int(ok.sum()), int(np.sum(ocode == O_SOLVED))), O)

    # default noisy chain
    d1, wl1, e1 = call_quiet(sy.generate_chain)
    d2, wl2, e2 = call_quiet(sy.generate_chain)
    quiet_ok(rep, "S6w", "generate_chain(default) x2", wl1 + wl2, e1 or e2, O)
    if e1 is None and e2 is None:
        rep.check("S6d", d1.equals(d2), "default chain deterministic across two calls", O)
        p = d1["price"].to_numpy(float)
        offtick = float(np.max(np.abs(p / SPEC_DEFAULT_TICK - np.round(p / SPEC_DEFAULT_TICK))))
        rep.check("S6t", offtick <= 1e-6, "default prices on the $0.01 tick: max off-tick %.3e ticks" % offtick, O)
        rep.check("S6m", float(p.min()) >= SPEC_DEFAULT_MIN_PRICE - 1e-12, "default min price %.4f >= %.2f" % (float(p.min()), SPEC_DEFAULT_MIN_PRICE), O)
        Kd = d1["strike"].to_numpy(float); Td = d1["T"].to_numpy(float)
        sg_d = np.array([o_true_vol(math.log(kk / o_forward(S, r, q, t)), t) for kk, t in zip(Kd, Td)])
        c = cmp_arrays(d1["sigma_true"].to_numpy(float), sg_d, 1e-12, 1e-12)
        rep.check("S6s", c["n_bad"] == 0 and list(d1.columns) == SPEC_CHAIN_COLS, "default chain sigma_true vs oracle: %s" % fmt_cmp(c), O)
        pc = np.array([o_price(S, kk, t, r, q, sg, typ == "C") for kk, t, sg, typ in zip(Kd, Td, sg_d, d1["type"].to_numpy(dtype=object))])
        changed = int(np.sum(np.abs(p - np.round(pc, 2)) > 1e-9))
        rep.info("S6n", "default chain rows %d; rows whose price differs from round(clean,2): %d (noise reached prices); max |p/p_clean-1| %.3e" % (
            len(d1), changed, float(np.max(np.abs(p / pc - 1)))))
        rep.check("S6r", changed > 0, "noise_bps=5 default actually perturbs prices (anti-vacuity): %d rows" % changed, O)
        md, Fd, kd = otm_mask(Kd, Td, d1["type"].to_numpy(dtype=object), S, r, q)
        out, wl, exc = call_quiet(bp.implied_vol, p[md], S, Kd[md], Td[md], r, q, d1["type"].to_numpy(dtype=object)[md] == "C")
        if exc is None:
            iv, st = np.asarray(out[0]), np.asarray(out[1])
            ok = np.isin(st, [0, 1])
            err = np.abs(iv[ok] - sg_d[md][ok])
            rep.check("S7", err.size > 0 and float(err.max()) <= SPEC_TOL_RT_NOISY,
                      "12 noisy default round trip: %d OTM rows, solved %d, max |iv-sigma_true| %.3e (tol %.2f)" % (
                          int(md.sum()), int(ok.sum()), float(err.max()) if err.size else -1, SPEC_TOL_RT_NOISY), O)
    # raises per 9
    bad = []
    for kw, lab in [({"S": 0.0}, "S=0"), ({"noise_bps": -1.0}, "noise<0"), ({"tick": -0.01}, "tick<0"), ({"maturities": []}, "empty maturities"), ({"strikes": []}, "empty strikes")]:
        _, _, exc = call_quiet(sy.generate_chain, **kw)
        if not isinstance(exc, ValueError):
            bad.append("%s: %s" % (lab, type(exc).__name__ if exc else "no raise"))
    rep.check("S8", not bad, "generate_chain raises ValueError per 9: %s" % ("; ".join(bad) or "all raise"), O)
    return clean


# =============================================================================
# Section surface - built surface.py, oracle-relevant checks only
# =============================================================================
def section_surface(rep, sf, dio, sy, bp, clean):
    print("--- section surface (built surface.py vs oracle) ---")
    O = "BUILD-B"
    S, r, q = SPEC_DEFAULT_S, SPEC_DEFAULT_R, SPEC_DEFAULT_Q
    params = dio.MarketParams(S=S, r=r, q=q)
    Ts = np.array(SPEC_DEFAULT_MATS)
    fw, wl, exc = call_quiet(params.forward, Ts)
    if exc is None:
        c = cmp_arrays(fw, [o_forward(S, r, q, t) for t in Ts], 1e-12, 1e-14)
        rep.check("F1", c["n_bad"] == 0, "MarketParams.forward vs oracle F=S e^{(r-q)T}: %s" % fmt_cmp(c), O)
    if clean is None:
        clean = sy.generate_chain(noise_bps=0.0, tick=0.0, min_price=0.0)
    qt, wl, exc = call_quiet(sf.prepare_quotes, clean, params)
    quiet_ok(rep, "Q0w", "prepare_quotes(clean)", wl, exc, O)
    if exc is not None:
        return
    rep.check("Q0c", list(qt.columns) == SPEC_QUOTE_COLS, "quotes columns %s" % list(qt.columns), O)
    K = clean["strike"].to_numpy(float); T = clean["T"].to_numpy(float); ty = clean["type"].to_numpy(dtype=object)
    m, F, k = otm_mask(K, T, ty, S, r, q)
    rep.check("Q1", len(qt) == int(m.sum()), "control total 2: len(quotes) %d vs oracle OTM recount %d (k>=0 -> call)" % (len(qt), int(m.sum())), O)
    qK = qt["strike"].to_numpy(float); qT = qt["T"].to_numpy(float); qty = qt["type"].to_numpy(dtype=object)
    qF = np.array([o_forward(S, r, q, t) for t in qT])
    c1 = cmp_arrays(qt["F"].to_numpy(float), qF, 1e-12, 1e-14)
    c2 = cmp_arrays(qt["k"].to_numpy(float), np.log(qK / qF), 1e-13, 0)
    side = ((qty == "P") & (np.log(qK / qF) < 0)) | ((qty == "C") & (np.log(qK / qF) >= 0))
    rep.check("Q2", c1["n_bad"] == 0 and c2["n_bad"] == 0 and bool(side.all()),
              "quotes F/k vs oracle and every row on OTM side: F %s | k %s | off-side rows %d" % (fmt_cmp(c1), fmt_cmp(c2), int((~side).sum())), O)
    qst = qt["status"].to_numpy(); qiv = qt["iv"].to_numpy(float); qp = qt["price"].to_numpy(float)
    rep.check("Q3", qt["status"].dtype == np.int8 and bool(np.all(np.isfinite(qiv) == np.isin(qst, [0, 1]))),
              "control total 4 on quotes: status dtype %s, iv-finite/status violations %d" % (qt["status"].dtype, int(np.sum(np.isfinite(qiv) != np.isin(qst, [0, 1])))), O)
    # iv vs oracle IV; status-2 rows must be out of bounds by the oracle's bounds
    bad_iv = 0; bad_st = []; n_cmp = 0; worst = 0.0
    for i in range(len(qt)):
        v, code = o_iv(qp[i], S, qK[i], qT[i], r, q, qty[i] == "C")
        if qst[i] in (0, 1):
            if code != O_SOLVED:
                bad_st.append(i)
            elif o_vega(S, qK[i], qT[i], r, q, v) >= ORC_IV_VEGA_FLOOR:
                n_cmp += 1
                worst = max(worst, abs(qiv[i] - v))
                if abs(qiv[i] - v) > ORC_IV_ERR:
                    bad_iv += 1
        elif code != qst[i]:
            bad_st.append(i)
    rep.check("Q4", not bad_st and bad_iv == 0 and n_cmp > 0,
              "quotes status vs oracle status (%d disagreements); iv vs oracle bisection on %d vega-decent rows: max %.3e, %d over %.0e" % (
                  len(bad_st), n_cmp, worst, bad_iv, ORC_IV_ERR), O)
    cw = cmp_arrays(qt["w"].to_numpy(float), qiv ** 2 * qT, 1e-15, 1e-13)
    rep.check("Q5", cw["n_bad"] == 0, "quotes w == iv^2 T: %s" % fmt_cmp(cw), O)

    usable = np.isin(qst, [0, 1])
    # R9/R10 on the NOISY default chain, where the clean-chain domain check is vacuous
    # (on the clean chain K=80 is in-domain at every T). Anti-vacuity: some rows must be False.
    dch = sy.generate_chain()
    qn, wln, en = call_quiet(sf.prepare_quotes, dch, params)
    sn, wln2, en2 = (None, [], en) if en is not None else call_quiet(sf.build_surface, qn, params, method="rbf")
    if en2 is None and sn is not None:
        un = np.isin(qn["status"].to_numpy(), [0, 1])
        Tn = np.asarray(sn.T_grid); kn = np.asarray(sn.k_grid)
        nlo, nhi, ndom = o_domain(qn["T"].to_numpy(float), qn["k"].to_numpy(float), un, sn.dropped_T, Tn, kn)
        bd = np.asarray(getattr(sn, "in_domain", np.zeros(0)), bool)
        dd = int(np.sum(bd != ndom)) if bd.shape == ndom.shape else -1
        tsn, _, e8 = call_quiet(sf.term_structure, sn, 80.0)
        if e8 is None:
            kx = np.log(80.0 / np.array([o_forward(S, r, q, t) for t in Tn]))
            tdn = (kx >= nlo) & (kx <= nhi)
            tsd = tsn["in_domain"].to_numpy(bool)
            rep.check("D2", dd == 0 and bool(np.all(tsd == tdn)) and int((~tdn).sum()) > 0,
                      "noisy default rbf: in_domain nodes differing %d of %d (oracle in-domain %d); term_structure(K=80) in_domain "
                      "mismatches %d, oracle False rows %d of %d (must be > 0)" % (
                          dd, ndom.size, int(ndom.sum()), int(np.sum(tsd != tdn)), int((~tdn).sum()), tdn.size), O)
        else:
            rep.check("D2", False, "term_structure on noisy surface raised %s" % e8, O)
        nc_n, nv_n, mv_n = o_calendar(np.asarray(sn.w), SPEC_TOL_CAL, ndom)
        nb_n, bv_n, bm_n = o_butterfly(np.asarray(sn.K), Tn, np.asarray(sn.iv), S, r, q, SPEC_TOL_BFLY, ndom)
        arn, _, e9 = call_quiet(sf.arbitrage_report, sn)
        if e9 is None:
            rep.check("D3", arn["calendar"]["n_violations"] == nv_n and arn["calendar"]["n_checked"] == nc_n and
                      arn["butterfly"]["n_violations"] == bv_n and arn["butterfly"]["n_checked"] == nb_n,
                      "noisy default rbf diagnostics: built calendar %s/%s butterfly %s/%s vs oracle %d/%d and %d/%d (counts reported, not judged as defects)" % (
                          arn["calendar"]["n_violations"], arn["calendar"]["n_checked"], arn["butterfly"]["n_violations"],
                          arn["butterfly"]["n_checked"], nv_n, nc_n, bv_n, nb_n), O)
    else:
        rep.check("D2", False, "noisy default chain surface build failed: %s" % en2, O)
    for method in ("rbf", "spline"):
        sfc, wl, exc = call_quiet(sf.build_surface, qt, params, method=method)
        quiet_ok(rep, "U0w-" + method[0], "build_surface(%s)" % method, wl, exc, O)
        if exc is not None:
            continue
        w = np.asarray(sfc.w); iv = np.asarray(sfc.iv); Kg = np.asarray(sfc.K); Tg = np.asarray(sfc.T_grid); kg = np.asarray(sfc.k_grid)
        fin = bool(np.isfinite(w).all() and np.isfinite(iv).all() and w.shape == iv.shape == Kg.shape == (Tg.size, kg.size) and (w >= 0).all())
        rep.check("U1-" + method[0], fin, "%s: finite w/iv, shapes (n_T,n_k)=%s, w>=0" % (method, w.shape), O)
        Fg = np.array([o_forward(S, r, q, t) for t in Tg])
        cF = cmp_arrays(sfc.F, Fg, 1e-12, 1e-14)
        cK = cmp_arrays(Kg, Fg[:, None] * np.exp(kg[None, :]), 1e-10, 1e-13)
        cI = cmp_arrays(iv, np.sqrt(np.maximum(w, 0) / Tg[:, None]), 1e-13, 1e-12)
        rep.check("U2-" + method[0], cF["n_bad"] == 0 and cK["n_bad"] == 0 and cI["n_bad"] == 0,
                  "%s: F vs oracle %s | K=F e^k %s | iv=sqrt(w/T) %s" % (method, fmt_cmp(cF), fmt_cmp(cK), fmt_cmp(cI)), O)
        # surface vs oracle truth at quoted maturities, k inside that maturity's usable quoted range
        worst = 0.0; where = None
        for t in np.unique(qT[usable]):
            mm = usable & (qT == t)
            if mm.sum() < 4:
                continue
            kk = np.linspace(qt["k"].to_numpy(float)[mm].min(), qt["k"].to_numpy(float)[mm].max(), 25)
            ev, wl2, e2 = call_quiet(sfc.evaluate, np.full_like(kk, t), kk)
            if e2 is not None:
                worst = float("inf"); where = "evaluate raised %s" % e2
                break
            tv = np.array([o_true_vol(x, t) for x in kk])
            d = np.abs(np.asarray(ev) - tv)
            if d.max() > worst:
                worst = float(d.max()); where = "T=%.4f k=%.4f" % (t, kk[int(np.argmax(d))])
        rep.check("U3-" + method[0], worst <= SPEC_TOL_SURF, "%s: |evaluate - oracle true_vol| interior, clean chain: max %.3e at %s (tol %.2f)" % (method, worst, where, SPEC_TOL_SURF), O)
        # diagnostics recomputed with the oracle pricer
        ar, wl3, e3 = call_quiet(sf.arbitrage_report, sfc)
        if e3 is not None:
            rep.check("A0-" + method[0], False, "arbitrage_report raised %s" % e3, O)
            continue
        keys_ok = set(ar.keys()) == {"disclaimer", "calendar", "butterfly", "lines"} and ar.get("disclaimer") == SPEC_DISCLAIMER
        rep.check("A0-" + method[0], keys_ok, "%s: arbitrage_report keys %s, disclaimer exact %s" % (method, sorted(ar.keys()), ar.get("disclaimer") == SPEC_DISCLAIMER), O)
        # R9 domain: oracle derivation from the quotes vs the built fields
        k_lo, k_hi, dom = o_domain(qT, qt["k"].to_numpy(float), usable, sfc.dropped_T, Tg, kg)
        b_lo, b_hi, b_dom = getattr(sfc, "k_lo", None), getattr(sfc, "k_hi", None), getattr(sfc, "in_domain", None)
        if b_lo is None or b_hi is None or b_dom is None:
            rep.check("D1-" + method[0], False, "%s: Surface lacks R9 fields k_lo/k_hi/in_domain" % method, O)
        else:
            c_lo = cmp_arrays(b_lo, k_lo, 1e-12, 0); c_hi = cmp_arrays(b_hi, k_hi, 1e-12, 0)
            b_dom = np.asarray(b_dom, bool)
            ndiff = int(np.sum(b_dom != dom)) if b_dom.shape == dom.shape else -1
            rep.check("D1-" + method[0], c_lo["n_bad"] == 0 and c_hi["n_bad"] == 0 and ndiff == 0,
                      "%s: R9 k_lo %s | k_hi %s | in_domain nodes differing from oracle %d of %d (oracle in-domain %d)" % (
                          method, fmt_cmp(c_lo), fmt_cmp(c_hi), ndiff, dom.size, int(dom.sum())), O)
        nc_full, nv_full, mv_full = o_calendar(w, SPEC_TOL_CAL)
        nb_full, bv_full, bm_full = o_butterfly(Kg, Tg, iv, S, r, q, SPEC_TOL_BFLY)
        rep.info("A9-" + method[0], "%s: FULL-grid (pre-R11 scope, reported not judged): calendar %d/%d max %.3e; butterfly %d/%d max %.3e" % (
            method, nv_full, nc_full, mv_full, bv_full, nb_full, bm_full))
        nc, nv, mv = o_calendar(w, SPEC_TOL_CAL, dom)
        cal = ar.get("calendar", {})
        rep.check("A1-" + method[0], cal.get("n_checked") == nc and cal.get("n_violations") == nv and abs(float(cal.get("max_violation_w", -1)) - mv) <= 1e-12,
                  "%s: calendar built %s/%s max %.3e vs oracle %d/%d max %.3e" % (method, cal.get("n_violations"), cal.get("n_checked"), float(cal.get("max_violation_w", float("nan"))), nv, nc, mv), O)
        nb, bv, bm = o_butterfly(Kg, Tg, iv, S, r, q, SPEC_TOL_BFLY, dom)
        rep.check("A3-" + method[0], nv == 0 and bv == 0 and nc >= 0.25 * nc_full and nb >= 0.25 * nb_full,
                  "%s: oracle in-domain counts on CLEAN chain: calendar %d/%d, butterfly %d/%d (12 + R12: zero violations, n_checked >= 25%% of full)" % (
                      method, nv, nc, bv, nb), O)
        bf = ar.get("butterfly", {})
        rep.check("A2-" + method[0], bf.get("n_checked") == nb and bf.get("n_violations") == bv and abs(float(bf.get("max_violation", -1)) - bm) <= 1e-9,
                  "%s: butterfly built %s/%s max %.3e vs oracle (own pricer) %d/%d max %.3e" % (method, bf.get("n_violations"), bf.get("n_checked"), float(bf.get("max_violation", float("nan"))), bv, nb, bm), O)
        # injected calendar violation must reach BOTH counters (anti-vacuity)
        # R12: inject at an in-domain pair (i+1, j) and require it to be counted
        w2 = w.copy()
        pairs = np.argwhere(dom[1:, :] & dom[:-1, :])
        ii, jj = (int(pairs[len(pairs) // 2][0]), int(pairs[len(pairs) // 2][1])) if len(pairs) else (0, kg.size // 2)
        w2[ii + 1, jj] = max(w2[ii, jj] - 1e-3, 0.0)
        nc2, nv2, _ = o_calendar(w2, SPEC_TOL_CAL, dom)
        try:
            s2 = dataclasses.replace(sfc, w=w2, iv=np.sqrt(w2 / Tg[:, None]))
            ar2, _, e4 = call_quiet(sf.arbitrage_report, s2)
            bnv2 = ar2["calendar"]["n_violations"] if e4 is None else None
        except Exception as e:  # dataclasses.replace may fail on a non-dataclass Surface
            bnv2, e4 = None, e
        rep.check("M4-" + method[0], nv2 > nv and bnv2 is not None and bnv2 > cal.get("n_violations", 0),
                  "%s: injected calendar violation: oracle %d -> %d, built %s -> %s (err %s)" % (method, nv, nv2, cal.get("n_violations"), bnv2, e4), "ORACLE")
        # term structure per-maturity mapping
        Kfix = 80.0
        ts, wl5, e5 = call_quiet(sf.term_structure, sfc, Kfix)
        atm, wl6, e6 = call_quiet(sf.term_structure, sfc, None)
        if e5 is None and e6 is None:
            kexp = np.log(Kfix / Fg)
            ck = cmp_arrays(ts["k"].to_numpy(float), kexp, 1e-13, 0)
            tdom = (kexp >= k_lo) & (kexp <= k_hi)  # R10, oracle k_lo/k_hi
            dom_ok = bool(np.all(ts["in_domain"].to_numpy(bool) == tdom))
            rep.info("T0-" + method[0], "%s: K=80 in_domain True on %d/%d T rows (oracle); old 6.6 rule would say %d" % (
                method, int(tdom.sum()), tdom.size, int(np.sum((kexp >= kg[0]) & (kexp <= kg[-1])))))
            cT = cmp_arrays(ts["T"].to_numpy(float), Tg, 0, 0)
            atm0 = float(np.max(np.abs(atm["k"].to_numpy(float))))
            diff = float(np.max(np.abs(ts["iv"].to_numpy(float) - atm["iv"].to_numpy(float))))
            rep.check("T1-" + method[0], ck["n_bad"] == 0 and dom_ok and cT["n_bad"] == 0 and atm0 == 0.0 and diff > SPEC_TOL_TS_DIFF,
                      "%s: term_structure(K=80) k_i=ln(K/F_oracle(T_i)) %s | in_domain match %s | ATM k max %.1e | max |fixed-K - ATM| %.3e (> %.0e)" % (
                          method, fmt_cmp(ck), dom_ok, atm0, diff, SPEC_TOL_TS_DIFF), O)
        else:
            rep.check("T1-" + method[0], False, "term_structure raised %s / %s" % (e5, e6), O)
        _, _, e7 = call_quiet(sf.term_structure, sfc, 0.0)
        rep.check("T2-" + method[0], isinstance(e7, ValueError), "term_structure K=0 raises ValueError: %s" % (type(e7).__name__ if e7 else "no raise"), O)
        nu = int(np.sum(usable & ~np.isin(qT, np.array(sfc.dropped_T, dtype=float))))
        rep.check("U4-" + method[0], sfc.n_quotes_used == nu, "control total 3: n_quotes_used %s vs oracle %d" % (sfc.n_quotes_used, nu), O)


# =============================================================================
def load_module(name, src, rep, owner):
    try:
        mod = importlib.import_module(name)
    except Exception as e:
        rep.check("I-" + name, False, "import %s from %s failed: %s: %s" % (name, src, type(e).__name__, e), owner)
        return None
    f = os.path.abspath(getattr(mod, "__file__", "") or "")
    ok = os.path.dirname(f) == os.path.abspath(src)
    rep.check("I-" + name, ok, "imported %s from %s" % (name, f), owner)
    return mod if ok else None


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Independent BS/IV oracle check (ASCII output).")
    ap.add_argument("--src", default=here)
    ap.add_argument("--sections", default="calib,bs,synth,surface")
    a = ap.parse_args(argv)
    src = os.path.abspath(a.src)
    sections = [s.strip() for s in a.sections.split(",") if s.strip()]
    unknown = set(sections) - {"calib", "bs", "synth", "surface"}
    if unknown:
        print("unknown sections: %s" % sorted(unknown))
        return 2
    # isolate imports to --src
    drop = {os.path.abspath(here), os.path.abspath(os.getcwd())}
    sys.path[:] = [src] + [p for p in sys.path if os.path.abspath(p or ".") not in drop and os.path.abspath(p or ".") != src]
    rep = Report()
    print("oracle_check.py  spec=%s" % SPEC_VERSION)
    print("src=%s" % src)
    print("REVIEW_A.md present at %s: %s" % (os.path.join(here, ".claude"), os.path.exists(os.path.join(here, ".claude", "REVIEW_A.md"))))
    h0 = sha_files(src)
    for f, h in h0.items():
        print("sha256-before %s %s" % (f, h))
    if "calib" in sections:
        section_calib(rep)
    bp = sy = sf = dio = None
    clean = None
    if any(s in sections for s in ("bs", "synth", "surface")):
        bp = load_module("bs_pricing", src, rep, "BUILD-A")
    if "bs" in sections and bp is not None:
        section_bs(rep, bp)
    if "synth" in sections or "surface" in sections:
        sy = load_module("synthetic", src, rep, "BUILD-A")
    if "synth" in sections and sy is not None and bp is not None:
        clean = section_synth(rep, sy, bp)
    if "surface" in sections:
        dio = load_module("data_io", src, rep, "BUILD-B")
        sf = load_module("surface", src, rep, "BUILD-B")
        if sf is not None and dio is not None and sy is not None and bp is not None:
            section_surface(rep, sf, dio, sy, bp, clean)
    h1 = sha_files(src)
    rep.check("H1", h0 == h1, "source hashes unchanged during run (else results not admissible): %s" % (
        [f for f in SRC_FILES if h0[f] != h1[f]] or "unchanged"), "ORACLE")
    fails = rep.fails()
    print("--- summary: %d checks, %d FAIL ---" % (len(rep.rows), len(fails)))
    for st, cid, owner, msg in fails:
        print("FAIL %s owner=%s" % (cid, owner))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
