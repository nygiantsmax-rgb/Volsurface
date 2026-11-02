"""bs_pricing.py - vectorized Black-Scholes-Merton pricing and implied-vol solver.

Implements CONTRACT.md sections 2.3, 3 and 9 (BUILD-A).  Continuous dividend yield q,
continuous rate r, T in YEARS, sigma / iv as ANNUALISED DECIMALS (0.20 = 20 vol points).

Public API
----------
bs_price(S, K, T, r, q, sigma, is_call)      -> ndarray   (section 3.1)
bs_vega(S, K, T, r, q, sigma)                -> ndarray   (section 3.2, per 1.00 of sigma)
price_bounds(S, K, T, r, q, is_call)         -> (lower, upper)   (section 3.3)
implied_vol(price, S, K, T, r, q, is_call, tol, max_iter, sigma_lo, sigma_hi)
                                             -> (iv, status)     (section 3.4)
Constants: IV_STATUS_* (ints), IV_STATUS_NAMES, IV_MIN, IV_MAX, BOUND_EPS.

Error semantics (CONTRACT 9): only non-broadcastable shapes raise ValueError; NaN / non-finite
in any input gives NaN out; implied_vol never raises for bad quotes (NaN + status code).
No RuntimeWarning is emitted: every division / log / exp runs under np.errstate with safe
denominators substituted through np.where.

Library-module note: running ``python bs_pricing.py`` executes a reference check
(hand-computed price, put-call parity, IV round trip) and exits non-zero on failure.
"""
from __future__ import annotations

import math
import sys

import numpy as np
from scipy.optimize import brentq
from scipy.special import ndtr

# ---- status codes (CONTRACT 2.3; everyone imports these, nobody re-types the ints) ----
IV_STATUS_NEWTON = 0
IV_STATUS_BRENT = 1
IV_STATUS_OUT_OF_BOUNDS = 2
IV_STATUS_FAILED = 3
IV_STATUS_INVALID_INPUT = 4
IV_STATUS_NAMES = {0: "newton", 1: "brent", 2: "out_of_bounds", 3: "failed", 4: "invalid_input"}
IV_MIN = 1e-4
IV_MAX = 5.0
BOUND_EPS = 1e-10  # absolute, price units

_SIGMA_RES = 1e-9  # Newton acceptance also needs |price_err/vega| <= this (vol units)
_VOL_DEGENERATE = 1e-12  # sigma*sqrt(T) below this -> discounted intrinsic (CONTRACT 3.1)
_INV_SQRT_2PI = 1.0 / math.sqrt(2.0 * math.pi)


def _as_float(x):
    return np.asarray(x, dtype=np.float64)


def _broadcast(*args):
    """Broadcast all args to one shape (float64 views).  Non-broadcastable -> ValueError."""
    try:
        return np.broadcast_arrays(*[_as_float(a) for a in args])
    except ValueError as exc:
        raise ValueError("arguments are not broadcastable: %s" % exc) from None


def _broadcast_call(is_call, *args):
    """Broadcast numeric args AND is_call together (CONTRACT 3: is_call broadcasts too).

    Returns (arrays..., isc_bool).  Non-broadcastable -> ValueError.
    """
    try:
        out = np.broadcast_arrays(*[_as_float(a) for a in args], np.asarray(is_call, dtype=bool))
    except ValueError as exc:
        raise ValueError("arguments are not broadcastable: %s" % exc) from None
    return tuple(out[:-1]) + (out[-1],)


def _finite_all(*arrs):
    ok = np.ones(arrs[0].shape, dtype=bool)
    for a in arrs:
        ok &= np.isfinite(a)
    return ok


def _d1_d2(S, K, Tc, r, q, sigma, vol_safe):
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma * sigma) * Tc) / vol_safe
    return d1, d1 - vol_safe


def bs_price(S, K, T, r, q, sigma, is_call):
    """European Black-Scholes price with continuous dividend yield (CONTRACT 3.1).

    d1 = (ln(S/K) + (r - q + sigma^2/2) T) / (sigma sqrt T), d2 = d1 - sigma sqrt T
    C = S e^{-qT} N(d1) - K e^{-rT} N(d2);  P = K e^{-rT} N(-d2) - S e^{-qT} N(-d1)
    (put computed directly, not via parity, so deep-OTM puts keep full relative precision).

    Degenerate region (T <= 0, sigma <= 0, or sigma*sqrt(T) < 1e-12): discounted intrinsic,
    T clipped to >= 0 inside the exponentials.  S <= 0, K <= 0, sigma < 0 or any non-finite
    input gives NaN.  Arguments broadcast; returns float64 ndarray (0-d for scalar input).
    """
    S, K, T, r, q, sigma, isc = _broadcast_call(is_call, S, K, T, r, q, sigma)
    invalid = ~_finite_all(S, K, T, r, q, sigma) | (S <= 0) | (K <= 0) | (sigma < 0)
    with np.errstate(all="ignore"):
        Tc = np.maximum(T, 0.0)
        vol = sigma * np.sqrt(Tc)
        degenerate = (T <= 0) | (sigma <= 0) | ~(vol >= _VOL_DEGENERATE)
        vol_safe = np.where(degenerate, 1.0, vol)
        dS = S * np.exp(-q * Tc)
        dK = K * np.exp(-r * Tc)
        d1, d2 = _d1_d2(S, K, Tc, r, q, sigma, vol_safe)
        call = dS * ndtr(d1) - dK * ndtr(d2)
        put = dK * ndtr(-d2) - dS * ndtr(-d1)
        smooth = np.where(isc, call, put)
        intrinsic = np.where(isc, np.maximum(dS - dK, 0.0), np.maximum(dK - dS, 0.0))
        out = np.where(degenerate, intrinsic, smooth)
        out = np.where(invalid, np.nan, out)
    return np.asarray(out, dtype=np.float64)


def bs_vega(S, K, T, r, q, sigma):
    """d(price)/d(sigma) per 1.00 of sigma (NOT per vol point): S e^{-qT} phi(d1) sqrt(T).

    Same degenerate region as bs_price returns 0.0; same NaN rules (CONTRACT 3.2).
    """
    S, K, T, r, q, sigma = _broadcast(S, K, T, r, q, sigma)
    invalid = ~_finite_all(S, K, T, r, q, sigma) | (S <= 0) | (K <= 0) | (sigma < 0)
    with np.errstate(all="ignore"):
        Tc = np.maximum(T, 0.0)
        sqT = np.sqrt(Tc)
        vol = sigma * sqT
        degenerate = (T <= 0) | (sigma <= 0) | ~(vol >= _VOL_DEGENERATE)
        vol_safe = np.where(degenerate, 1.0, vol)
        d1, _ = _d1_d2(S, K, Tc, r, q, sigma, vol_safe)
        vega = S * np.exp(-q * Tc) * _INV_SQRT_2PI * np.exp(-0.5 * d1 * d1) * sqT
        vega = np.where(degenerate, 0.0, vega)
        vega = np.where(invalid, np.nan, vega)
    return np.asarray(vega, dtype=np.float64)


def price_bounds(S, K, T, r, q, is_call):
    """No-arbitrage price bounds (lower, upper), CONTRACT 3.3.

    call [max(S e^{-qT} - K e^{-rT}, 0), S e^{-qT}];  put [max(K e^{-rT} - S e^{-qT}, 0), K e^{-rT}].
    T clipped to >= 0.  S <= 0, K <= 0 or non-finite input gives NaN in both.
    """
    S, K, T, r, q, isc = _broadcast_call(is_call, S, K, T, r, q)
    invalid = ~_finite_all(S, K, T, r, q) | (S <= 0) | (K <= 0)
    with np.errstate(all="ignore"):
        Tc = np.maximum(T, 0.0)
        dS = S * np.exp(-q * Tc)
        dK = K * np.exp(-r * Tc)
        lower = np.where(isc, np.maximum(dS - dK, 0.0), np.maximum(dK - dS, 0.0))
        upper = np.where(isc, dS, dK)
        lower = np.where(invalid, np.nan, lower)
        upper = np.where(invalid, np.nan, upper)
    return np.asarray(lower, dtype=np.float64), np.asarray(upper, dtype=np.float64)


def implied_vol(price, S, K, T, r, q, is_call, tol=1e-8, max_iter=50,
                sigma_lo=IV_MIN, sigma_hi=IV_MAX):
    """Implied volatility with an explicit per-element status (CONTRACT 3.4 / 2.3).

    Returns (iv, status): iv float64 ndarray (decimals), status int8 ndarray, broadcast shape
    (0-d for all-scalar input).  iv is finite iff status in {0, 1}.
    Evaluation order: invalid input (4) -> bounds (2) -> solve (0 newton / 1 brent / 3 failed).
      4 invalid : any input NaN/inf, or S<=0, K<=0, T<=0, price<=0
      2 oob     : price <= lower_bound + BOUND_EPS or price >= upper_bound - BOUND_EPS
      3 failed  : in bounds, but no sign change on [sigma_lo, sigma_hi] or no convergence
    Algorithm: vectorized Newton from a Brenner-Subrahmanyam seed, sigma clipped to
    [sigma_lo, sigma_hi], at most max_iter steps (bracket-safeguarded: an out-of-bracket step is
    replaced by bisection).  R-2 guard (REVIEW_A.md R5): Newton accepts or steps an element only
    where vega is finite and >= 1e-8; otherwise it is retired to Brent with no resid/vega division.
    Elements not converged go to a per-element scipy brentq on [sigma_lo, sigma_hi] (xtol 1e-12).
    ``tol`` is an ABSOLUTE price residual: converged iff |bs_price(sigma) - price| <= tol.
    R-1 (OWNERSHIP.md corrections log) ratifies this rule; CONTRACT 3.4 yields to section 12.
    Stricter than the literal 3.4 text: Newton acceptance ALSO
    requires |residual / vega| <= 1e-9 (vol units), and Brent only short-circuits on an exact
    zero residual at an endpoint.  Reason: with absolute tol 1e-8 a deep-OTM quote priced below
    ~1e-8 is matched by ANY sigma (observed: iv=0.0001 returned vs truth 0.22 on a 3e-10 put).
    Never raises for bad quotes; emits no warnings.
    """
    price, S, K, T, r, q, isc = _broadcast_call(is_call, price, S, K, T, r, q)
    shape = price.shape
    isc = np.array(isc).ravel()
    p = price.ravel().copy()
    s = S.ravel().copy()
    k = K.ravel().copy()
    t = T.ravel().copy()
    rr = r.ravel().copy()
    qq = q.ravel().copy()
    n = p.size

    iv = np.full(n, np.nan)
    status = np.full(n, IV_STATUS_INVALID_INPUT, dtype=np.int8)

    with np.errstate(all="ignore"):
        valid = _finite_all(p, s, k, t, rr, qq) & (s > 0) & (k > 0) & (t > 0) & (p > 0)
        lower, upper = price_bounds(s, k, t, rr, qq, isc)
        oob = valid & ((p <= lower + BOUND_EPS) | (p >= upper - BOUND_EPS))
        status[oob] = IV_STATUS_OUT_OF_BOUNDS
        solve = valid & ~oob
        idx = np.flatnonzero(solve)

        if idx.size:
            ps, ss, ks, ts, rs, qs, cs = p[idx], s[idx], k[idx], t[idx], rr[idx], qq[idx], isc[idx]
            # Brenner-Subrahmanyam seed: sigma0 = sqrt(2 pi / T) * price / (S e^{-qT}), clipped.
            sig = np.sqrt(2.0 * math.pi / ts) * ps / (ss * np.exp(-qs * ts))
            sig = np.clip(sig, sigma_lo, sigma_hi)
            sig = np.where(np.isfinite(sig), sig, 0.2)
            active = np.ones(idx.size, dtype=bool)
            done = np.zeros(idx.size, dtype=bool)
            # Safeguarded Newton: a running bracket [blo, bhi] (price is increasing in sigma)
            # replaces any step that leaves it with a bisection step, so clipped / overshooting
            # Newton steps cannot bounce between the sigma bounds.
            blo = np.full(idx.size, float(sigma_lo))
            bhi = np.full(idx.size, float(sigma_hi))
            for _ in range(int(max_iter)):
                a = np.flatnonzero(active)
                if a.size == 0:
                    break
                diff = bs_price(ss[a], ks[a], ts[a], rs[a], qs[a], sig[a], cs[a]) - ps[a]
                vega = bs_vega(ss[a], ks[a], ts[a], rs[a], qs[a], sig[a])
                # converged: absolute price residual <= tol AND the implied Newton step is below
                # _SIGMA_RES in vol space (stops a sub-tol price from accepting any sigma; see
                # BUILD-A deviation note in implied_vol docstring)
                # R-2 guard (REVIEW_A.md R5): Newton may accept/step ONLY where vega is finite and
                # >= 1e-8.  Elsewhere the element is retired to Brent and no resid/vega division
                # is evaluated for it (safe denominator substituted).
                usable = vega >= 1e-8                      # False for NaN as well
                v_safe = np.where(usable, vega, 1.0)
                step = diff / v_safe
                conv = usable & (np.abs(diff) <= tol) & ((np.abs(step) <= _SIGMA_RES) | (diff == 0.0))
                done[a[conv]] = True
                active[a[conv | ~usable]] = False          # ~usable -> left not-done -> Brent
                go = usable & ~conv
                b = a[go]
                if b.size:
                    d_b = diff[go]
                    hi_side = d_b > 0
                    bhi[b] = np.where(hi_side, sig[b], bhi[b])
                    blo[b] = np.where(hi_side, blo[b], sig[b])
                    new = sig[b] - step[go]
                    outside = ~((new > blo[b]) & (new < bhi[b]))
                    sig[b] = np.where(outside, 0.5 * (blo[b] + bhi[b]), new)
            # elements still active after max_iter fall through to Brent
            iv[idx[done]] = sig[done]
            status[idx[done]] = IV_STATUS_NEWTON

            # ---- per-element Brent fallback ----
            for j in np.flatnonzero(~done):
                val, ok = _brent_one(ps[j], ss[j], ks[j], ts[j], rs[j], qs[j], bool(cs[j]),
                                     tol, sigma_lo, sigma_hi)
                if ok:
                    iv[idx[j]] = val
                    status[idx[j]] = IV_STATUS_BRENT
                else:
                    status[idx[j]] = IV_STATUS_FAILED

    return iv.reshape(shape), status.reshape(shape)


def _brent_one(p, s, k, t, r, q, is_call, tol, lo, hi):
    """Brent root of bs_price(sigma) - p on [lo, hi]; (value, ok).  ok False if no sign change."""
    def f(x):
        return float(bs_price(s, k, t, r, q, x, is_call)) - p

    flo, fhi = f(lo), f(hi)
    if not (math.isfinite(flo) and math.isfinite(fhi)):
        return float("nan"), False
    if flo == 0.0:
        return lo, True
    if fhi == 0.0:
        return hi, True
    if flo * fhi > 0.0:
        return float("nan"), False
    try:
        root = brentq(f, lo, hi, xtol=1e-12, maxiter=200)
    except (ValueError, RuntimeError):
        return float("nan"), False
    return float(root), True


def _self_test():
    """Reference check for __main__: returns list of failure strings (empty = pass)."""
    fails = []

    def ncdf(x):  # independent of scipy: math.erf
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    S, K, T, r, q, sg = 100.0, 100.0, 1.0, 0.05, 0.02, 0.2
    d1 = (math.log(S / K) + (r - q + 0.5 * sg * sg) * T) / (sg * math.sqrt(T))
    d2 = d1 - sg * math.sqrt(T)
    ref_c = S * math.exp(-q * T) * ncdf(d1) - K * math.exp(-r * T) * ncdf(d2)
    ref_p = K * math.exp(-r * T) * ncdf(-d2) - S * math.exp(-q * T) * ncdf(-d1)
    got_c = float(bs_price(S, K, T, r, q, sg, True))
    got_p = float(bs_price(S, K, T, r, q, sg, False))
    # hand value: d1=0.25, d2=0.05 -> C = 98.01987*0.598706 - 95.12294*0.519939 = 9.2270
    if abs(ref_c - 9.2270) > 5e-4:
        fails.append("hand value drift: ref_c=%r" % ref_c)
    if abs(got_c - ref_c) > 1e-12 or abs(got_p - ref_p) > 1e-12:
        fails.append("price mismatch call %r/%r put %r/%r" % (got_c, ref_c, got_p, ref_p))
    parity = got_c - got_p - (S * math.exp(-q * T) - K * math.exp(-r * T))
    if abs(parity) > 1e-10:
        fails.append("parity residual %r" % parity)
    iv, st = implied_vol(got_c, S, K, T, r, q, True)
    if int(st) not in (0, 1) or abs(float(iv) - sg) > 1e-6:
        fails.append("round trip iv=%r status=%r" % (float(iv), int(st)))
    iv, st = implied_vol(5.0, 100.0, 80.0, 1.0, 0.05, 0.02, True)  # call below intrinsic (~23.7)
    if int(st) != IV_STATUS_OUT_OF_BOUNDS or not np.isnan(float(iv)):
        fails.append("below-intrinsic call: want out_of_bounds+NaN, got %r/%r" % (float(iv), int(st)))
    both = bs_price(100.0, 100.0, 1.0, 0.05, 0.02, 0.2, np.array([True, False]))
    if both.shape != (2,):
        fails.append("is_call must broadcast; shape %r" % (both.shape,))
    iv2, st2 = implied_vol(both[0], 100.0, 100.0, 1.0, 0.05, 0.02, np.array([True, False]))
    if iv2.shape != (2,) or st2.shape != (2,):
        fails.append("implied_vol is_call broadcast shape %r" % (iv2.shape,))
    _, st = implied_vol(1.0, 100.0, 100.0, 0.0, 0.05, 0.02, True)
    if int(st) != IV_STATUS_INVALID_INPUT:
        fails.append("T=0 should be invalid_input, got %r" % int(st))
    return fails


if __name__ == "__main__":
    _fails = _self_test()
    if _fails:
        for _f in _fails:
            print("FAIL: " + _f)
        sys.exit(1)
    print("bs_pricing self-test OK")
    sys.exit(0)
