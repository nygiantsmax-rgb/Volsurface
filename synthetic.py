"""synthetic.py - ground-truth SSVI volatility surface and synthetic option-chain generator.

Implements CONTRACT.md section 4 (BUILD-A).  T in years, vols as decimals, k = ln(K/F).

Truth surface (SSVI, parameters PINNED by CONTRACT 4.1 so ORACLE can reimplement them):
    theta(T) = T * atm_vol(T)^2,   atm_vol(T) = 0.18 + 0.06 * (1 - exp(-T / 1.0))
    w(k, T)  = (theta / 2) * (1 + rho*phi*k + sqrt((phi*k + rho)^2 + 1 - rho^2)),
               rho = -0.7, phi = 1.5
    true_vol = sqrt(w / T)

Arbitrage-freeness of the truth (REVIEW_A.md R16, with the two printed figures replaced by the
computed values per flow-lead): (SSVI, Gatheral and
Jacquier 2014): with phi(theta) = phi constant, the calendar-spread condition requires
d(theta)/dT >= 0, which holds because theta = T*atm_vol^2 with atm_vol > 0 and
non-decreasing, and 0 <= d(theta*phi)/d(theta) = phi <= (1/rho^2)(1 + sqrt(1-rho^2)) phi, which is
1.5 <= 5.25 at rho = -0.7. The sufficient butterfly conditions are theta*phi*(1+|rho|) < 4 and
theta*phi^2*(1+|rho|) <= 4. The second binds at theta <= 4/(phi^2 (1+|rho|)) = 1.046, i.e. T <= about 18 years
(atm_vol <= 0.24). At the default maximum T = 2, theta = 0.107537: 0.274 < 4 and 0.411 <= 4. At-the-money,
w(0, T) = theta(T).
Arithmetic check by BUILD-A (interpreter): theta(2) = 0.107537 exactly (R16's 0.1076 uses a
rounded atm_vol(2) = 0.2319); 0.107537*1.5*1.7 = 0.274 and 0.107537*2.25*1.7 = 0.411; the
theta = 1.046 crossing is at T = 18.16.  These are sufficient conditions, not a guarantee.
Library note: ``python synthetic.py`` runs a self-check and exits non-zero on failure.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from bs_pricing import bs_price

DEFAULT_S = 100.0
DEFAULT_R = 0.04
DEFAULT_Q = 0.015
DEFAULT_MATURITIES_YEARS = (1 / 12, 2 / 12, 3 / 12, 6 / 12, 9 / 12, 1.0, 1.5, 2.0)
DEFAULT_STRIKE_FRACTIONS = tuple(np.arange(0.60, 1.40 + 1e-9, 0.025))

_RHO = -0.7
_PHI = 1.5
_CHAIN_COLUMNS = ["strike", "T", "type", "price", "sigma_true"]


def true_vol(k, T):
    """Ground-truth implied vol (annualised DECIMAL) at log-moneyness k and maturity T years.

    Broadcasts over k and T; returns float64 ndarray (0-d for scalars).  T <= 0 or NaN in
    either argument gives NaN.  Formula and parameters: module docstring / CONTRACT 4.1.
    """
    k_a, T_a = np.broadcast_arrays(np.asarray(k, dtype=np.float64), np.asarray(T, dtype=np.float64))
    with np.errstate(all="ignore"):
        good = np.isfinite(k_a) & np.isfinite(T_a) & (T_a > 0)
        Ts = np.where(good, T_a, 1.0)
        ks = np.where(good, k_a, 0.0)
        atm = 0.18 + 0.06 * (1.0 - np.exp(-Ts / 1.0))
        theta = Ts * atm * atm
        pk = _PHI * ks
        w = 0.5 * theta * (1.0 + _RHO * pk + np.sqrt((pk + _RHO) ** 2 + 1.0 - _RHO ** 2))
        vol = np.sqrt(w / Ts)
        vol = np.where(good, vol, np.nan)
    return np.asarray(vol, dtype=np.float64)


def generate_chain(S=DEFAULT_S, r=DEFAULT_R, q=DEFAULT_Q, maturities=None, strikes=None,
                   noise_bps=5.0, tick=0.01, min_price=0.05, seed=0):
    """Synthetic option CHAIN (CONTRACT 2.1) priced from true_vol, INCLUDING ``sigma_true``.

    For each maturity T and strike K, for both "C" and "P": F = S*exp((r-q)T),
    sigma_true = true_vol(ln(K/F), T), price = bs_price at sigma_true; then multiplied by
    (1 + noise_bps*1e-4*z), z ~ N(0,1) from np.random.default_rng(seed) (noise_bps == 0: no
    noise); rounded to the nearest ``tick`` (tick == 0 disables); rows with price < min_price
    (or price <= 0) are dropped.  Columns: strike, T, type, price, sigma_true; sorted by
    (T, strike, type) with "C" before "P"; RangeIndex.  Deterministic for a given argument set.
    The clean chain (noise_bps=0, tick=0, min_price=0) is the exact round-trip fixture.
    Raises ValueError: empty maturities/strikes, S<=0 or non-finite, noise_bps<0, tick<0,
    min_price<0, non-positive/non-finite/duplicated maturities or strikes.
    """
    if not (np.isfinite(S) and S > 0):
        raise ValueError("S must be finite and > 0, got %r" % (S,))
    if not (np.isfinite(r) and np.isfinite(q)):
        raise ValueError("r and q must be finite")
    if not (np.isfinite(noise_bps) and noise_bps >= 0):
        raise ValueError("noise_bps must be >= 0, got %r" % (noise_bps,))
    if not (np.isfinite(tick) and tick >= 0):
        raise ValueError("tick must be >= 0, got %r" % (tick,))
    if not (np.isfinite(min_price) and min_price >= 0):
        raise ValueError("min_price must be >= 0, got %r" % (min_price,))
    mats = np.asarray(DEFAULT_MATURITIES_YEARS if maturities is None else maturities, dtype=np.float64).ravel()
    ks_ = np.asarray(S * np.asarray(DEFAULT_STRIKE_FRACTIONS) if strikes is None else strikes,
                     dtype=np.float64).ravel()
    if mats.size == 0 or ks_.size == 0:
        raise ValueError("maturities and strikes must be non-empty")
    if not (np.isfinite(mats).all() and (mats > 0).all()):
        raise ValueError("maturities must be finite and > 0")
    if not (np.isfinite(ks_).all() and (ks_ > 0).all()):
        raise ValueError("strikes must be finite and > 0")
    mats = np.sort(mats)
    ks_ = np.sort(ks_)
    if np.unique(mats).size != mats.size or np.unique(ks_).size != ks_.size:
        raise ValueError("duplicate maturities or strikes would create duplicate chain rows")

    # grid order: T outer, strike, then C before P  -> already the required sort order
    Tg = np.repeat(mats, ks_.size * 2)
    Kg = np.tile(np.repeat(ks_, 2), mats.size)
    is_call = np.tile(np.array([True, False]), mats.size * ks_.size)

    F = S * np.exp((r - q) * Tg)
    sigma_true = true_vol(np.log(Kg / F), Tg)
    price = bs_price(S, Kg, Tg, r, q, sigma_true, is_call)

    if noise_bps > 0:
        rng = np.random.default_rng(seed)
        price = price * (1.0 + noise_bps * 1e-4 * rng.standard_normal(price.size))
    if tick > 0:
        price = np.round(np.round(price / tick) * tick, 10)

    keep = (price >= min_price) & (price > 0) & np.isfinite(price)
    chain = pd.DataFrame({
        "strike": Kg[keep],
        "T": Tg[keep],
        "type": np.where(is_call[keep], "C", "P"),
        "price": price[keep],
        "sigma_true": sigma_true[keep],
    })
    chain = chain.sort_values(["T", "strike", "type"], kind="mergesort").reset_index(drop=True)
    return chain[_CHAIN_COLUMNS]


def _self_test():
    fails = []
    # hand check of the pinned formula at k=0, T=1: atm=0.18+0.06*(1-e^-1)
    atm = 0.18 + 0.06 * (1 - np.exp(-1.0))
    w0 = 0.5 * atm * atm * (1 + np.sqrt(0.49 + 1 - 0.49))  # k=0: sqrt(rho^2+1-rho^2)=1
    if abs(float(true_vol(0.0, 1.0)) - np.sqrt(w0)) > 1e-12 or abs(float(true_vol(0.0, 1.0)) - atm) > 1e-12:
        fails.append("true_vol(0,1) != atm_vol")
    if not np.isnan(true_vol(0.0, 0.0)):
        fails.append("true_vol(T=0) not NaN")
    a = generate_chain(noise_bps=0.0, tick=0.0, min_price=0.0)
    b = generate_chain(noise_bps=0.0, tick=0.0, min_price=0.0)
    if not a.equals(b):
        fails.append("generate_chain not deterministic")
    if list(a.columns) != _CHAIN_COLUMNS or len(a) == 0 or not (a["price"] > 0).all():
        fails.append("chain schema/price invalid")
    from bs_pricing import implied_vol
    F = DEFAULT_S * np.exp((DEFAULT_R - DEFAULT_Q) * a["T"].to_numpy())
    k = np.log(a["strike"].to_numpy() / F)
    otm = np.where(a["type"].to_numpy() == "P", k < 0, k >= 0)
    c = a[otm]
    iv, st = implied_vol(c["price"].to_numpy(), DEFAULT_S, c["strike"].to_numpy(), c["T"].to_numpy(),
                         DEFAULT_R, DEFAULT_Q, (c["type"] == "C").to_numpy())
    good = st <= 1
    if good.mean() < 0.9:
        fails.append("only %.3f of clean OTM quotes solved" % good.mean())
    elif np.max(np.abs(iv[good] - c["sigma_true"].to_numpy()[good])) > 1e-6:
        fails.append("clean round trip error too large")
    return fails


if __name__ == "__main__":
    _fails = _self_test()
    if _fails:
        for _f in _fails:
            print("FAIL: " + _f)
        sys.exit(1)
    print("synthetic self-test OK")
    sys.exit(0)
