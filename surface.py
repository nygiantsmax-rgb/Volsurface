"""surface.py - quotes -> implied-vol surface -> diagnostics and slices (BUILD-B).

Governing spec: .claude/CONTRACT.md sections 2.2, 6 and 10 (binding rulings:
.claude/REVIEW_A.md, cited by ID in comments).

Pipeline
--------
    chain --prepare_quotes--> quotes --build_surface--> Surface
    Surface --arbitrage_report / smile / term_structure--> diagnostics and slices

Axis order (stated once, CONTRACT 6.1): every 2-D array is indexed [i_T, j_k], shape
(n_T, n_k). The interpolated quantity is TOTAL VARIANCE w = iv**2 * T; iv is derived from
w in exactly ONE function (_iv_from_w) used by the grid build and by Surface.evaluate.
w is also produced by exactly one path: the Surface's private _w_fn (grid and evaluate
both call it).

Units: T years, k = ln(K/F) dimensionless, iv decimals. Percent never appears here.

arbitrage_report counts grid violations. It is a DIAGNOSTIC; it neither enforces nor
guarantees an arbitrage-free surface.

Running `python surface.py` executes a real self-check and exits non-zero on failure.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline, PchipInterpolator, RBFInterpolator

from bs_pricing import IV_STATUS_USABLE, bs_price, implied_vol
from data_io import MarketParams

# --- Tunables: each is ONE named constant so a REVIEW_A ruling is a one-line edit -----------
MIN_QUOTES_PER_T = 4          # CONTRACT 6.1: thinner maturities are dropped (dropped_T)
W_FLOOR = 0.0                 # CONTRACT 6.1: w clipped to >= W_FLOOR everywhere
K_GRID_MODE = "union"         # CONTRACT 6.3 / R3: "union" of quoted k (default) or "intersection"
OTM_CALL_AT_BOUNDARY = True   # CONTRACT 2.2 / R2: the k == 0 quote goes to the CALL
RBF_KERNEL = "thin_plate_spline"

# REVIEW_A R11(c): exact text; scope is in_domain nodes only.
DIAGNOSTIC_DISCLAIMER = ("DIAGNOSTIC ONLY: these checks count violations at grid nodes inside "
                         "the quoted domain; they do not enforce or guarantee an arbitrage-free "
                         "surface and say nothing about extrapolated regions.")

_QUOTE_COLUMNS = ["strike", "T", "type", "price", "F", "k", "iv", "w", "status"]
_REQUIRED_CHAIN = ("strike", "T", "type", "price")


# ---------------------------------------------------------------------------
# Single emitters (iv from w; w floor)
# ---------------------------------------------------------------------------
def _iv_from_w(w, T):
    """The ONLY place iv is derived from total variance: iv = sqrt(w / T).

    w, T broadcast. Callers guarantee T > 0 where finite. NaN in -> NaN out. No warnings.
    """
    w = np.asarray(w, dtype=np.float64)
    T = np.asarray(T, dtype=np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.sqrt(w / T)


def _make_w_fn(raw_fn, T_lo, T_hi, k_lo, k_hi, clamp):
    """Wrap a raw interpolator (flat T array, flat k array -> flat w array) into the
    Surface._w_fn contract: broadcast, NaN passthrough, optional clamping of (T, k) to the
    grid domain (spline), w >= W_FLOOR. Both the grid build and evaluate go through this.
    """
    def w_fn(T, k):
        Tb, kb = np.broadcast_arrays(np.asarray(T, dtype=np.float64),
                                     np.asarray(k, dtype=np.float64))
        out = np.full(Tb.shape, np.nan)
        ok = np.isfinite(Tb) & np.isfinite(kb)
        if ok.any():
            t = Tb[ok]
            kk = kb[ok]
            if clamp:
                t = np.clip(t, T_lo, T_hi)
                kk = np.clip(kk, k_lo, k_hi)
            out[ok] = np.asarray(raw_fn(t, kk), dtype=np.float64)
        with np.errstate(invalid="ignore"):
            return np.maximum(out, W_FLOOR)  # NaN stays NaN
    return w_fn


def _in_domain(T_nodes, k_lo, k_hi, T, k):
    """THE quoted-domain rule (REVIEW_A R9/R10, R-14 A): True where T lies inside the maturity range
    and k lies between the per-maturity quoted edges interpolated linearly in T. NaN gives False."""
    T = np.asarray(T, dtype=np.float64)
    k = np.asarray(k, dtype=np.float64)
    lo = np.interp(T, T_nodes, k_lo)
    hi = np.interp(T, T_nodes, k_hi)
    return (T >= T_nodes[0]) & (T <= T_nodes[-1]) & (k >= lo) & (k <= hi)


# ---------------------------------------------------------------------------
# Surface
# ---------------------------------------------------------------------------
@dataclass
class Surface:
    """Interpolated total-variance surface (CONTRACT 6.1). Arrays are indexed [i_T, j_k].

    T_grid (n_T,) years, strictly increasing, > 0.   k_grid (n_k,) log-moneyness.
    w (n_T, n_k) total variance, finite, >= 0.       iv (n_T, n_k) decimals = sqrt(w/T).
    F (n_T,) forward per maturity.                   K (n_T, n_k) strike per node.
    k_lo, k_hi, in_domain: REVIEW_A R9 governing definition. For each usable maturity T_m,
    kmin_m / kmax_m = min / max k over its status-0/1 quotes; k_lo = np.interp(T_grid, T_m,
    kmin_m), k_hi likewise; in_domain[i, j] = (k_lo[i] <= k_grid[j] <= k_hi[i]). Nodes
    outside are EXTRAPOLATED and not reliable. T_m, kmin_m, kmax_m keep the quoted maturities
    and edges so in_domain_at is exact at a quoted T (R-15 D14). in_domain_at(T, k) is the single definition of
    that rule at arbitrary (T, k); the in_domain grid, smile and term_structure all use it (R-14 A).
    method "rbf" | "spline".   params MarketParams.
    n_quotes_used: usable quotes (status 0/1) that fed the interpolator.
    dropped_T: maturities removed for having < MIN_QUOTES_PER_T usable quotes.
    """

    T_grid: np.ndarray
    k_grid: np.ndarray
    w: np.ndarray
    iv: np.ndarray
    F: np.ndarray
    K: np.ndarray
    k_lo: np.ndarray      # (n_T,) REVIEW_A R9: per-row lower edge of the quoted domain
    k_hi: np.ndarray      # (n_T,) REVIEW_A R9: per-row upper edge of the quoted domain
    in_domain: np.ndarray  # (n_T, n_k) bool, k_lo[i] <= k_grid[j] <= k_hi[i]; else EXTRAPOLATED
    method: str
    params: MarketParams
    n_quotes_used: int
    dropped_T: tuple
    T_m: np.ndarray       # (n_m,) quoted maturities that fed the surface (R-15 D14)
    kmin_m: np.ndarray    # (n_m,) min k over each maturity's status-0/1 quotes (REVIEW_A R9)
    kmax_m: np.ndarray    # (n_m,) max k over each maturity's status-0/1 quotes (REVIEW_A R9)
    _w_fn: Callable = field(repr=False)

    def in_domain_at(self, T, k):
        """Quoted-domain flag at arbitrary (T, k); broadcasts. Edges are interpolated over the QUOTED maturities, so at a quoted T this is the slice's exact quoted extent; at grid nodes it equals the in_domain grid bit-for-bit (R-14 A, R-15 D14)."""
        return _in_domain(self.T_m, self.kmin_m, self.kmax_m, T, k)

    def evaluate_w(self, T, k):
        """Total variance at arbitrary (T, k). array_like inputs broadcast; float64 result
        of the broadcast shape (0-d for scalars; use float()). w >= W_FLOOR.

        ValueError if any finite T <= 0; NaN in -> NaN out; otherwise finite. Outside the
        quoted domain values are EXTRAPOLATED and not reliable (rbf: kernel; spline:
        (T, k) clamped to the grid ranges); term_structure flags this via in_domain.
        """
        T = np.asarray(T, dtype=np.float64)
        k = np.asarray(k, dtype=np.float64)
        finite = np.isfinite(T)
        if np.any(T[finite] <= 0.0):
            raise ValueError("evaluate: T must be > 0 (years)")
        return self._w_fn(T, k)

    def evaluate(self, T, k):
        """Implied vol (decimal) at arbitrary (T, k): sqrt(evaluate_w / T). See evaluate_w."""
        w = self.evaluate_w(T, k)
        return _iv_from_w(w, np.asarray(T, dtype=np.float64))


# ---------------------------------------------------------------------------
# prepare_quotes
# ---------------------------------------------------------------------------
def prepare_quotes(chain, params):
    """CHAIN -> QUOTES (CONTRACT 2.2 / 6.2): forward, k, OTM split, implied vol, w.

    OTM split (governing rule, CONTRACT 2.2; boundary per OTM_CALL_AT_BOUNDARY): compute
    k = np.log(strike / F) first; keep a row iff (type == "P" and k < 0) or
    (type == "C" and k >= 0). ITM-side rows are removed here and nowhere else. Failed
    solves are KEPT with status >= 2 and iv = w = NaN. Output sorted by (T, strike),
    RangeIndex, columns strike, T, type, price, F, k, iv, w, status[, sigma_true].
    sigma_true is only carried through, never read.

    Raises ValueError for a chain that lacks required columns OR violates the CONTRACT
    2.1 schema in a way that would make the OTM split silently lose rows (non-finite or
    non-positive strike, non-finite T or price, type not in {"C","P"}). Quotes with
    T <= 0 or price <= 0 are NOT raised: they flow to implied_vol and get status 4.
    Structural self-checks run before returning (OTM count when OTM_CALL_AT_BOUNDARY, status
    sum, iv-finite <=> status 0/1); they are not the control-total gate, main's recount is.
    """
    missing = [c for c in _REQUIRED_CHAIN if c not in chain.columns]
    if missing:
        raise ValueError("prepare_quotes: chain lacks required columns %r" % (missing,))
    strike = chain["strike"].to_numpy(dtype=np.float64)
    T = chain["T"].to_numpy(dtype=np.float64)
    price = chain["price"].to_numpy(dtype=np.float64)
    typ = chain["type"].to_numpy(dtype=object).astype(str)
    if not (np.isfinite(strike).all() and (strike > 0).all()):
        raise ValueError("prepare_quotes: strike must be finite and > 0 (CONTRACT 2.1)")
    if not (np.isfinite(T).all() and np.isfinite(price).all()):
        raise ValueError("prepare_quotes: T and price must be finite (CONTRACT 2.1)")
    if not np.isin(typ, ("C", "P")).all():
        raise ValueError("prepare_quotes: type must be exactly 'C' or 'P' (CONTRACT 2.1)")

    F = np.asarray(params.forward(T), dtype=np.float64)
    k = np.log(strike / F)
    is_call = typ == "C"
    call_side = (k >= 0.0) if OTM_CALL_AT_BOUNDARY else (k > 0.0)
    keep = (is_call & call_side) | (~is_call & ~call_side)

    df = pd.DataFrame({
        "strike": strike[keep], "T": T[keep], "type": typ[keep], "price": price[keep],
        "F": F[keep], "k": k[keep],
    })
    if "sigma_true" in chain.columns:
        df["sigma_true"] = chain["sigma_true"].to_numpy(dtype=np.float64)[keep]
    df = df.sort_values(["T", "strike"], kind="mergesort").reset_index(drop=True)

    n = len(df)
    if n:
        iv, status = implied_vol(df["price"].to_numpy(), params.S, df["strike"].to_numpy(),
                                 df["T"].to_numpy(), params.r, params.q,
                                 (df["type"] == "C").to_numpy())
        iv = np.asarray(iv, dtype=np.float64)
        status = np.asarray(status).astype(np.int8)
    else:
        iv = np.empty(0)
        status = np.empty(0, dtype=np.int8)
    Tq = df["T"].to_numpy()
    with np.errstate(invalid="ignore"):
        w = np.where(np.isfinite(iv), iv * iv * Tq, np.nan)
    out = df.assign(iv=iv, w=w, status=status)
    cols = _QUOTE_COLUMNS + (["sigma_true"] if "sigma_true" in out.columns else [])
    out = out[cols]

    # STRUCTURAL CHECK (not the control-total gate; R-9 D2). The OTM-count test below is skipped
    # when OTM_CALL_AT_BOUNDARY is False, the very flag it polices, and its recount reuses this
    # function's own k. The status-sum test is structural. main.py's own independent recount
    # of CONTRACT 10 item 2 is the gate.
    expect = int(np.count_nonzero((typ == "P") & (np.log(strike / F) < 0.0))
                 + np.count_nonzero((typ == "C") & (np.log(strike / F) >= 0.0)))
    if OTM_CALL_AT_BOUNDARY and len(out) != expect:
        raise RuntimeError("control total failed: quotes %d != OTM count %d" % (len(out), expect))
    if sum(int((status == c).sum()) for c in range(5)) != len(out):
        raise RuntimeError("control total failed: status codes outside 0..4")
    # Control total 4: iv finite <=> status in {0, 1}.
    if not np.array_equal(np.isfinite(iv), np.isin(status, IV_STATUS_USABLE)):
        raise RuntimeError("control total failed: iv finite does not match status in {0,1}")
    return out


# ---------------------------------------------------------------------------
# build_surface
# ---------------------------------------------------------------------------
def _maturity_groups(T, k, w):
    """Group usable quotes by exact maturity: list of (T_i, k_sorted, w_sorted), T ascending.
    Exactly repeated k within a maturity (cannot happen for one OTM quote per strike) are
    averaged so CubicSpline gets strictly increasing abscissae."""
    out = []
    for t in np.unique(T):
        m = T == t
        kk, ww = k[m], w[m]
        order = np.argsort(kk, kind="mergesort")
        kk, ww = kk[order], ww[order]
        uk, inv = np.unique(kk, return_inverse=True)
        if len(uk) != len(kk):
            ww = np.bincount(inv, weights=ww) / np.bincount(inv)
            kk = uk
        out.append((float(t), kk, ww))
    return out


def _rbf_raw(T, k, w, smoothing):
    """RBF raw fn on min-max scaled (T, k); the scaling is frozen from the usable quotes
    and shared by the fit and every later evaluation (it lives in this closure)."""
    t0, t1 = float(T.min()), float(T.max())
    k0, k1 = float(k.min()), float(k.max())
    ts, ks = (t1 - t0), (k1 - k0)
    if not ts > 0 or not ks > 0:
        raise ValueError("rbf: degenerate quote range (T or k has zero width)")
    pts = np.column_stack(((T - t0) / ts, (k - k0) / ks))
    rbf = RBFInterpolator(pts, w, kernel=RBF_KERNEL, smoothing=smoothing)

    def raw(t, kk):
        return rbf(np.column_stack(((t - t0) / ts, (kk - k0) / ks)))
    return raw


def _spline_raw(groups):
    """Two-stage spline: natural CubicSpline in k per maturity (ends clamped flat at that
    maturity's own quoted wings), then PchipInterpolator in T per k point. Evaluated by
    unique T so memory stays O(n_maturities * points-per-T), never N x N."""
    Ts = np.array([g[0] for g in groups])
    splines = [CubicSpline(g[1], g[2], bc_type="natural") for g in groups]
    kmins = [g[1][0] for g in groups]
    kmaxs = [g[1][-1] for g in groups]

    def raw(t, kk):
        out = np.empty(t.shape)
        for tv in np.unique(t):
            sel = t == tv
            kv = kk[sel]
            W = np.vstack([sp(np.clip(kv, lo, hi))
                           for sp, lo, hi in zip(splines, kmins, kmaxs)])  # (n_mat, m)
            out[sel] = PchipInterpolator(Ts, W, axis=0)(tv) if len(kv) else kv
        return out
    return raw


def build_surface(quotes, params, method="rbf", n_T=60, n_k=80, smoothing=1e-6):
    """QUOTES -> Surface by interpolating TOTAL VARIANCE w over (T, k) (CONTRACT 6.3).

    Uses ONLY rows with status in {0, 1}. Maturities with fewer than MIN_QUOTES_PER_T
    usable quotes are dropped (reported in Surface.dropped_T). T_grid = linspace over the
    usable T range; k_grid = linspace over the usable k range (K_GRID_MODE "union" of
    quoted k, or "intersection" of per-maturity ranges). Corners beyond one maturity's own
    quoted wings are EXTRAPOLATED.
    "rbf": RBFInterpolator thin-plate spline, `smoothing`, inputs min-max scaled to [0,1].
    "spline": natural CubicSpline in k per maturity, PCHIP in T per k node.
    w >= W_FLOOR, iv = sqrt(w / T). Raises ValueError for a bad method, n_T < 2, n_k < 4,
    negative smoothing, fewer than 2 usable maturities, or a non-finite result
    ("non-finite surface"). Structural checks (n_quotes_used identity, grid shapes) run before returning;
    they are not the control-total gate, main's recount is.
    """
    if method not in ("rbf", "spline"):
        raise ValueError("build_surface: method must be 'rbf' or 'spline', got %r" % (method,))
    if int(n_T) < 2 or int(n_k) < 4:
        raise ValueError("build_surface: need n_T >= 2 and n_k >= 4")
    if not (np.isfinite(smoothing) and smoothing >= 0):
        raise ValueError("build_surface: smoothing must be finite and >= 0")
    if K_GRID_MODE not in ("union", "intersection"):
        raise ValueError("K_GRID_MODE must be 'union' or 'intersection'")

    ok = np.isin(quotes["status"].to_numpy(), IV_STATUS_USABLE)
    use = quotes.loc[ok]
    T_all = use["T"].to_numpy(dtype=np.float64)
    k_all = use["k"].to_numpy(dtype=np.float64)
    w_all = use["w"].to_numpy(dtype=np.float64)
    if not (np.isfinite(w_all).all() and (T_all > 0).all() and np.isfinite(k_all).all()):
        raise ValueError("build_surface: usable quotes contain non-finite or T<=0 values")

    uniq, counts = np.unique(T_all, return_counts=True)
    thin = uniq[counts < MIN_QUOTES_PER_T]
    dropped_T = tuple(float(t) for t in thin)
    keep = ~np.isin(T_all, thin)
    T_u, k_u, w_u = T_all[keep], k_all[keep], w_all[keep]
    n_used = int(keep.sum())
    mats = np.unique(T_u)
    if len(mats) < 2:
        raise ValueError("build_surface: fewer than 2 maturities with >= %d usable quotes "
                         "(dropped %r)" % (MIN_QUOTES_PER_T, dropped_T))

    groups = _maturity_groups(T_u, k_u, w_u)
    if K_GRID_MODE == "union":
        k_lo, k_hi = float(k_u.min()), float(k_u.max())
    else:
        k_lo = max(g[1][0] for g in groups)
        k_hi = min(g[1][-1] for g in groups)
        if not k_lo < k_hi:
            raise ValueError("build_surface: maturities share no common k range")
    T_lo, T_hi = float(mats[0]), float(mats[-1])
    T_grid = np.linspace(T_lo, T_hi, int(n_T))
    k_grid = np.linspace(k_lo, k_hi, int(n_k))

    if method == "rbf":
        raw, clamp = _rbf_raw(T_u, k_u, w_u, float(smoothing)), False
    else:
        raw, clamp = _spline_raw(groups), True
    w_fn = _make_w_fn(raw, T_lo, T_hi, k_lo, k_hi, clamp)

    w = w_fn(T_grid[:, None], k_grid[None, :])
    iv = _iv_from_w(w, T_grid[:, None])
    F = np.asarray(params.forward(T_grid), dtype=np.float64)
    K = F[:, None] * np.exp(k_grid[None, :])
    # REVIEW_A R9 (union grid kept; R21): per-row quoted domain, interpolated in T.
    T_m = np.array([g[0] for g in groups])
    kmin_m = np.array([g[1][0] for g in groups])
    kmax_m = np.array([g[1][-1] for g in groups])
    k_lo_row = np.interp(T_grid, T_m, kmin_m)
    k_hi_row = np.interp(T_grid, T_m, kmax_m)
    in_domain = _in_domain(T_grid, k_lo_row, k_hi_row, T_grid[:, None], k_grid[None, :])
    if not (np.isfinite(w).all() and np.isfinite(iv).all()):
        raise ValueError("non-finite surface")
    shape = (len(T_grid), len(k_grid))
    if not (w.shape == iv.shape == K.shape == shape):
        raise RuntimeError("control total failed: grid shapes %r %r %r" % (w.shape, iv.shape, K.shape))
    # STRUCTURAL CHECK (R-9 D2): n_used and expect_used come from the same mask, so this is
    # an identity that guards against edit slips only. It is NOT an independent control
    # total 3; main.py's own recount is the gate.
    expect_used = int(np.count_nonzero(ok & ~np.isin(quotes["T"].to_numpy(dtype=np.float64), thin)))
    if n_used != expect_used:
        raise RuntimeError("control total failed: n_quotes_used %d != %d" % (n_used, expect_used))
    return Surface(T_grid=T_grid, k_grid=k_grid, w=w, iv=iv, F=F, K=K, k_lo=k_lo_row,
                   k_hi=k_hi_row, in_domain=in_domain, method=method, params=params, n_quotes_used=n_used, dropped_T=dropped_T,
                   T_m=T_m, kmin_m=kmin_m, kmax_m=kmax_m, _w_fn=w_fn)


# ---------------------------------------------------------------------------
# arbitrage_report (DIAGNOSTICS, NOT GUARANTEES)
# ---------------------------------------------------------------------------
def arbitrage_report(surface, tol_calendar_w=1e-6, tol_butterfly=1e-8):
    """Count violations at grid nodes INSIDE the quoted domain. DIAGNOSTIC ONLY: it does not
    enforce or guarantee that the surface is free of arbitrage, says nothing about
    extrapolated regions, and returns NO boolean verdict (CONTRACT 6.4, REVIEW_A R11).

    Calendar (R11a): dw = w[i+1, j] - w[i, j]; the pair is checked iff in_domain[i, j] and
    in_domain[i+1, j]; violation iff dw < -tol_calendar_w; n_checked = number of such pairs.
    Butterfly (R11b; a convexity proxy on the grid, not Durrleman's g(k)): per maturity row,
    C_j = bs_price(S, K_ij, T_i, r, q, iv_ij, True) is the PRESENT-VALUE call price from
    bs_price (dimensionless slopes below; convexity in K is unchanged by the positive factor
    e^{rT}, so this is the forward-price butterfly condition, R11d); slopes
    s_j = (C_{j+1} - C_j) / (K_{j+1} - K_j); the triple (j, j+1, j+2) is checked iff all
    three nodes are in_domain; violation iff s_{j+1} - s_j < -tol_butterfly; n_checked =
    number of such triples.
    Returns exactly {"disclaimer", "calendar", "butterfly", "lines"} per CONTRACT 6.4.
    """
    w = surface.w
    ind = surface.in_domain
    dw = np.diff(w, axis=0)
    cal_mask = ind[:-1, :] & ind[1:, :]
    cal_viol = cal_mask & (dw < -tol_calendar_w)
    cal_max = float(max(0.0, np.max(-dw[cal_mask]))) if cal_mask.any() else 0.0

    p = surface.params
    C = np.asarray(bs_price(p.S, surface.K, surface.T_grid[:, None], p.r, p.q, surface.iv, True))
    dK = np.diff(surface.K, axis=1)
    s = np.diff(C, axis=1) / dK
    ds = np.diff(s, axis=1)
    bf_mask = ind[:, :-2] & ind[:, 1:-1] & ind[:, 2:]
    bf_viol = bf_mask & (ds < -tol_butterfly)
    bf_max = float(max(0.0, np.max(-ds[bf_mask]))) if bf_mask.any() else 0.0

    cal = {"n_checked": int(cal_mask.sum()), "n_violations": int(cal_viol.sum()),
           "max_violation_w": cal_max, "tol": float(tol_calendar_w)}
    bf = {"n_checked": int(bf_mask.sum()), "n_violations": int(bf_viol.sum()),
          "max_violation": bf_max, "tol": float(tol_butterfly)}
    lines = [
        DIAGNOSTIC_DISCLAIMER,
        "calendar: %d/%d violations (max %.2e in total variance, tol %.1e)"
        % (cal["n_violations"], cal["n_checked"], cal["max_violation_w"], cal["tol"]),
        "butterfly: %d/%d violations (max %.2e in dC/dK, tol %.1e)"
        % (bf["n_violations"], bf["n_checked"], bf["max_violation"], bf["tol"]),
    ]
    return {"disclaimer": DIAGNOSTIC_DISCLAIMER, "calendar": cal, "butterfly": bf, "lines": lines}


# ---------------------------------------------------------------------------
# Slices
# ---------------------------------------------------------------------------
def smile(surface, T, n_k=None):
    """IV smile at fixed T (years, any T > 0; need not be a grid node) (CONTRACT 6.5).

    Columns [k, strike, iv, in_domain] (iv float64 decimals; in_domain bool), ascending in k.
    k = surface.k_grid, or linspace over its range with n_k points when n_k is given
    (n_k >= 2). strike = params.forward(T) * exp(k). in_domain is False for k outside the
    quoted range at this T and for T outside [T_grid[0], T_grid[-1]] (Surface.in_domain_at).
    ValueError for non-scalar or non-positive T.
    """
    Ts = np.asarray(T, dtype=np.float64)
    if Ts.ndim != 0 or not np.isfinite(Ts) or Ts <= 0:
        raise ValueError("smile: T must be a finite scalar > 0 (years)")
    if n_k is None:
        k = surface.k_grid.copy()
    else:
        if int(n_k) < 2:
            raise ValueError("smile: n_k must be >= 2")
        k = np.linspace(surface.k_grid[0], surface.k_grid[-1], int(n_k))
    Tf = float(Ts)
    return pd.DataFrame({
        "k": k,
        "strike": float(surface.params.forward(Tf)) * np.exp(k),
        "iv": np.asarray(surface.evaluate(Tf, k), dtype=np.float64),
        "in_domain": surface.in_domain_at(Tf, k),
    })


def term_structure(surface, K=None):
    """IV term structure over T = surface.T_grid (CONTRACT 6.6). Columns [T, k, iv, in_domain].

    K given (> 0, currency units): FIXED-STRIKE curve with per-maturity
    k_i = ln(K / F(T_i)), F from params.forward (NOT a fixed row of k_grid).
    K=None: the ATM-FORWARD curve, k_i = 0 for every i (a different curve).
    in_domain = Surface.in_domain_at(T_i, k_i), i.e. _in_domain (REVIEW_A R10; governing
    definition R9 / Surface docstring); False rows are extrapolated. ValueError for K <= 0 or non-finite.
    """
    Tg = surface.T_grid
    if K is None:
        k = np.zeros_like(Tg)
    else:
        Ks = np.asarray(K, dtype=np.float64)
        if Ks.ndim != 0 or not np.isfinite(Ks) or Ks <= 0:
            raise ValueError("term_structure: K must be a finite scalar > 0")
        k = np.log(float(Ks) / np.asarray(surface.params.forward(Tg), dtype=np.float64))
    iv = np.asarray(surface.evaluate(Tg, k), dtype=np.float64)
    in_domain = surface.in_domain_at(Tg, k)  # R10
    return pd.DataFrame({"T": Tg.copy(), "k": k, "iv": iv, "in_domain": in_domain})


# ---------------------------------------------------------------------------
# __main__ self-check (real assertions; exits non-zero on failure)
# ---------------------------------------------------------------------------
def _clean_chain(S, r, q):
    """Self-check only: clean SSVI chain re-derived from CONTRACT 4.1 (no synthetic import)."""
    rho, phi = -0.7, 1.5
    rows = []
    for T in (1 / 12, 0.25, 0.5, 1.0, 2.0):
        F = S * np.exp((r - q) * T)
        theta = T * (0.18 + 0.06 * (1 - np.exp(-T))) ** 2
        for fr in np.arange(0.7, 1.3 + 1e-9, 0.05):
            K = fr * S
            kk = np.log(K / F)
            wv = 0.5 * theta * (1 + rho * phi * kk + np.sqrt((phi * kk + rho) ** 2 + 1 - rho ** 2))
            sg = float(np.sqrt(wv / T))
            for typ in ("C", "P"):
                px = float(bs_price(S, K, T, r, q, sg, typ == "C"))
                rows.append((K, T, typ, px, sg))
    return pd.DataFrame(rows, columns=["strike", "T", "type", "price", "sigma_true"])


def _selfcheck():
    p = MarketParams(S=100.0, r=0.04, q=0.015)
    chain = _clean_chain(p.S, p.r, p.q)
    qt = prepare_quotes(chain, p)
    assert len(qt) == len(chain) // 2, (len(qt), len(chain))
    ok = qt["status"].isin(IV_STATUS_USABLE)
    assert ok.mean() > 0.9, ok.mean()
    assert float((qt.loc[ok, "iv"] - qt.loc[ok, "sigma_true"]).abs().max()) < 1e-6
    assert (((qt["type"] == "P") & (qt["k"] < 0)) | ((qt["type"] == "C") & (qt["k"] >= 0))).all()
    for method in ("rbf", "spline"):
        s = build_surface(qt, p, method=method, n_T=20, n_k=30)
        assert np.isfinite(s.w).all() and np.isfinite(s.iv).all()
        assert s.w.shape == (20, 30) == s.K.shape
        rep = arbitrage_report(s)
        assert set(rep) == {"disclaimer", "calendar", "butterfly", "lines"}
        assert len(rep["lines"]) == 3 and rep["lines"][0] == DIAGNOSTIC_DISCLAIMER
        # R11 anti-vacuity: scope is narrower than the full grid but not empty
        assert 0.25 * 19 * 30 <= rep["calendar"]["n_checked"] < 19 * 30, rep["calendar"]
        assert 0.25 * 20 * 28 <= rep["butterfly"]["n_checked"] < 20 * 28, rep["butterfly"]
        assert rep["calendar"]["n_violations"] == 0 and rep["butterfly"]["n_violations"] == 0, rep
        assert s.in_domain.shape == s.w.shape and s.k_lo.shape == s.T_grid.shape
        # anti-vacuity: an injected calendar violation at an in-domain pair must be counted
        i, j = [(a, b) for a, b in zip(*np.nonzero(s.in_domain[:-1] & s.in_domain[1:]))][7]
        bad = Surface(**{**s.__dict__, "w": s.w.copy()})
        bad.w[i + 1, j] -= 0.05
        assert arbitrage_report(bad)["calendar"]["n_violations"] >= 1
        # ... and one injected at an extrapolated node must NOT be counted (scope works)
        ei, ej = [e for e in np.argwhere(~s.in_domain) if e[0] > 0][0]
        assert not s.in_domain[ei, ej]
        bad2 = Surface(**{**s.__dict__, "w": s.w.copy()})
        bad2.w[ei, ej] -= 0.05
        assert arbitrage_report(bad2)["calendar"]["n_violations"] == 0
        # per-maturity fixed-strike mapping: k_i == ln(K / F(T_i)) and varies with T
        ts = term_structure(s, 90.0)
        assert np.allclose(ts["k"], np.log(90.0 / p.forward(s.T_grid)))
        assert ts["k"].max() - ts["k"].min() > 0.01
        assert float(np.abs(ts["iv"] - term_structure(s)["iv"]).max()) > 1e-4
        sm = smile(s, 0.4)
        assert list(sm.columns) == ["k", "strike", "iv", "in_domain"] and np.isfinite(sm["iv"]).all()
        assert np.array_equal(s.in_domain, s.in_domain_at(s.T_grid[:, None], s.k_grid[None, :]))
        assert np.array_equal(s.in_domain_at(s.T_m, s.kmin_m), np.ones(len(s.T_m), bool)) and np.array_equal(s.in_domain_at(s.T_m, s.kmax_m), np.ones(len(s.T_m), bool))
    return True


if __name__ == "__main__":
    try:
        _selfcheck()
    except Exception as exc:  # any failure -> non-zero exit
        sys.stderr.write("surface selfcheck FAILED: %s: %s\n" % (type(exc).__name__, exc))
        sys.exit(1)
    print("surface selfcheck ok")
    sys.exit(0)
