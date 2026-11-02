"""viz.py - Plotly dashboard builder and HTML writer (BUILD-C, CONTRACT.md sections 7.1 and 7.2).

Public API
----------
build_dashboard(surface, quotes, params, colorscale="Viridis", x_axis="k",
                n_smiles=5, strike_fractions=(0.8, 0.9, 1.0, 1.1, 1.2)) -> go.Figure
write_dashboard(fig, path, plotlyjs="cdn") -> str

Units (CONTRACT.md section 1.2): every stored field is a decimal; PERCENT appears only
here, as display values (iv * 100) inside the figure. This module never recomputes an
implied vol: surface values come from Surface.iv / Surface.smile / Surface.term_structure
and market values come from the quotes `iv` column.

Trace order inside the figure is fixed (the colorscale dropdown and the smile slider
address traces by index):
    0                  "IV surface" (go.Surface)
    1                  "Market quotes" (go.Scatter3d)
    2 .. 2+2m-1        per smile: line "Smile T=..y", then markers "Quotes T=..y"
    then               "Term K=..." per strike fraction, then "ATM-forward (k=0)"

Diagnostics wording: the title says "not guaranteed arbitrage-free" on purpose; the
checks in surface.arbitrage_report are diagnostics, not guarantees.
"""
from __future__ import annotations

import datetime
import os
import sys

import numpy as np
import plotly.colors as pc
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from bs_pricing import IV_STATUS_NEWTON, IV_STATUS_BRENT
from surface import smile, term_structure

_VALID_X_AXIS = ("k", "strike")
_VALID_COLORSCALE = ("Viridis", "Plasma")
_VALID_PLOTLYJS = ("cdn", "inline")
_HOVER = ("Strike: %{customdata[0]:.2f}<br>Expiry: %{customdata[2]} "
          "(%{customdata[1]:.0f}d)<br>IV: %{customdata[3]:.2f}%<extra></extra>")
TITLE = ("Implied volatility surface (OTM quotes, total-variance interpolation; "
         "diagnostics only - not guaranteed arbitrage-free)")
_K_TITLE = "Log-moneyness k = ln(K/F)"
_STRIKE_TITLE = "Strike"


def _expiry_label(params, T):
    """Expiry label per CONTRACT.md 5.1: valuation_date + round(T*365) days, else 'T=<T:.3f>y'."""
    vd = getattr(params, "valuation_date", None)
    if vd is None:
        return "T=%.3fy" % float(T)
    return (vd + datetime.timedelta(days=int(round(float(T) * 365.0)))).isoformat()


def _customdata(params, K, T, iv_pct, k):
    """Stack [K, T_days, expiry_label, iv_pct, k] on a new last axis (object dtype: the label is text)."""
    K, T, iv_pct, k = np.broadcast_arrays(np.asarray(K, float), np.asarray(T, float),
                                          np.asarray(iv_pct, float), np.asarray(k, float))
    out = np.empty(K.shape + (5,), dtype=object)
    out[..., 0] = K
    out[..., 1] = T * 365.0
    labels = np.empty(T.shape, dtype=object)
    for idx in np.ndindex(T.shape):
        labels[idx] = _expiry_label(params, T[idx])
    out[..., 2] = labels
    out[..., 3] = iv_pct
    out[..., 4] = k
    return out


def _pick_maturities(Ts, n):
    """Choose up to n entries from sorted array Ts, spread evenly (always includes first and last when n>=2)."""
    m = len(Ts)
    if m <= n:
        return list(Ts)
    idx = np.unique(np.round(np.linspace(0, m - 1, n)).astype(int))
    return [Ts[i] for i in idx]


def build_dashboard(surface, quotes, params, colorscale="Viridis", x_axis="k",
                    n_smiles=5, strike_fractions=(0.8, 0.9, 1.0, 1.1, 1.2)):
    """Build the single-figure dashboard (CONTRACT.md 7.1). Pure: writes no files.

    Row 1: full-width 3D IV surface (x = T years, y = k or strike, z = IV percent) with market
    quotes overlaid as Scatter3d; hover shows Strike / Expiry / IV; dropdown switches Viridis/Plasma.
    Row 2 left: smiles at up to `n_smiles` quoted maturities (interpolated line + market markers),
    slider toggles which smile is visible. Row 2 right: term structures at fixed strikes
    (strike = fraction * spot, per-maturity k_i mapping done by surface.term_structure) plus the
    separate ATM-forward (k=0) curve; points outside the quoted k range (in_domain False) are NaN, rendered as a gap in the line (R13);
    the same gap rule applies to the smile lines (OX-2).

    Raises ValueError for an unknown x_axis / colorscale, n_smiles < 1, or no usable quotes.
    """
    if x_axis not in _VALID_X_AXIS:
        raise ValueError("x_axis must be one of %s, got %r" % (_VALID_X_AXIS, x_axis))
    if colorscale not in _VALID_COLORSCALE:
        raise ValueError("colorscale must be one of %s, got %r" % (_VALID_COLORSCALE, colorscale))
    if n_smiles < 1:
        raise ValueError("n_smiles must be >= 1")
    by_strike = x_axis == "strike"
    y_title = _STRIKE_TITLE if by_strike else _K_TITLE

    usable = quotes[quotes["status"].isin([IV_STATUS_NEWTON, IV_STATUS_BRENT])]
    if len(usable) == 0:
        raise ValueError("no quotes with a finite IV (status 0/1); nothing to overlay")

    T_grid = np.asarray(surface.T_grid, float)
    k_grid = np.asarray(surface.k_grid, float)
    n_T, n_k = len(T_grid), len(k_grid)

    fig = make_subplots(
        rows=2, cols=2,
        specs=[[{"type": "scene", "colspan": 2}, None], [{"type": "xy"}, {"type": "xy"}]],
        row_heights=[0.62, 0.38], vertical_spacing=0.08,
        subplot_titles=("", "", "Smiles (slider selects expiry)",
                        "Term structures (fixed strike vs ATM-forward)"),
    )

    # ---- trace 0: the surface; arrays are (n_k, n_T), the transpose of Surface.iv ----------
    X = np.broadcast_to(T_grid[None, :], (n_k, n_T)).copy()
    if by_strike:
        Y = np.asarray(surface.K, float).T.copy()
    else:
        Y = np.broadcast_to(k_grid[:, None], (n_k, n_T)).copy()
    Z = 100.0 * np.asarray(surface.iv, float).T          # percent: display only
    Kt = np.asarray(surface.K, float).T
    Kg = np.broadcast_to(k_grid[:, None], (n_k, n_T))
    cd = _customdata(params, Kt, X, Z, Kg)
    fig.add_trace(go.Surface(x=X, y=Y, z=Z, customdata=cd, hovertemplate=_HOVER,
                             name="IV surface", colorscale=colorscale,
                             colorbar=dict(title=dict(text="IV (%)"), len=0.5, y=0.78),
                             showscale=True), row=1, col=1)

    # ---- trace 1: market quotes overlay -----------------------------------------------------
    qK = usable["strike"].to_numpy(float)
    qT = usable["T"].to_numpy(float)
    qk = usable["k"].to_numpy(float)
    qiv = 100.0 * usable["iv"].to_numpy(float)
    fig.add_trace(go.Scatter3d(x=qT, y=qK if by_strike else qk, z=qiv, mode="markers",
                               name="Market quotes",
                               marker=dict(size=2.5, color="black", opacity=0.8),
                               customdata=_customdata(params, qK, qT, qiv, qk),
                               hovertemplate=_HOVER), row=1, col=1)

    # ---- smiles: pairs of (line, markers) --------------------------------------------------
    dropped = tuple(getattr(surface, "dropped_T", ()))
    Tq = np.unique(qT)
    Tq = np.array([t for t in Tq if not any(np.isclose(t, d) for d in dropped)])
    if len(Tq) == 0:
        raise ValueError("no usable maturities among quotes")
    smile_Ts = _pick_maturities(Tq, int(n_smiles))
    smile_trace_idx = []
    for T in smile_Ts:
        sm = smile(surface, float(T))
        xs = sm["strike"].to_numpy(float) if by_strike else sm["k"].to_numpy(float)
        # OX-2 (R13 principle): smile k nodes outside the quoted domain are y = NaN (gap), never an
        # extrapolated value. Domain = Surface.in_domain at the grid row nearest this maturity; smile()
        # with n_k=None returns k_grid, so its columns align with that row.
        i_row = int(np.argmin(np.abs(T_grid - float(T))))
        dom = np.asarray(surface.in_domain[i_row], bool)
        if len(dom) != len(sm):
            raise ValueError("smile length %d != in_domain row length %d" % (len(sm), len(dom)))
        y_smile = np.where(dom, 100.0 * sm["iv"].to_numpy(float), np.nan)
        i_line = len(fig.data)
        fig.add_trace(go.Scatter(x=xs, y=y_smile, mode="lines",
                                 name="Smile T=%.3fy" % T, visible=False,
                                 hovertemplate="%s=%%{x:.4f}<br>IV: %%{y:.2f}%%<extra>T=%.3fy</extra>"
                                 % ("Strike" if by_strike else "k", T)), row=2, col=1)
        m = np.isclose(qT, T)
        fig.add_trace(go.Scatter(x=(qK[m] if by_strike else qk[m]), y=qiv[m], mode="markers",
                                 name="Quotes T=%.3fy" % T, visible=False,
                                 marker=dict(size=6, color="black", symbol="diamond"),
                                 hovertemplate="%s=%%{x:.4f}<br>IV: %%{y:.2f}%%<extra>market T=%.3fy</extra>"
                                 % ("Strike" if by_strike else "k", T)), row=2, col=1)
        smile_trace_idx.append((i_line, i_line + 1))

    # ---- term structures --------------------------------------------------------------------
    for f in strike_fractions:
        Kf = float(f) * float(params.S)
        _add_term(fig, term_structure(surface, Kf), "Term K=%.2f" % Kf)
    _add_term(fig, term_structure(surface, None), "ATM-forward (k=0)", dash="dash")

    # ---- slider: smile i visible, the rest hidden; non-smile traces keep visibility ---------
    n_tr = len(fig.data)
    base = [True] * n_tr
    for a, b in smile_trace_idx:
        base[a] = base[b] = False
    steps = []
    for i, (T, (a, b)) in enumerate(zip(smile_Ts, smile_trace_idx)):
        vis = list(base)
        vis[a] = vis[b] = True
        steps.append(dict(method="restyle", args=[{"visible": vis}], label="T=%.3fy" % T))
        if i == 0:                                   # initial state = first smile shown
            for j, v in enumerate(vis):
                fig.data[j].visible = v
    sliders = [dict(active=0, steps=steps, x=0.0, len=0.5, y=-0.04,
                    currentvalue=dict(prefix="Smile expiry: "))]

    cs_buttons = [dict(label=name, method="restyle",
                       args=[{"colorscale": [pc.get_colorscale(name)]}, [0]])
                  for name in _VALID_COLORSCALE]
    cs_buttons.sort(key=lambda b: b["label"] != colorscale)   # initial first
    updatemenus = [dict(type="dropdown", buttons=cs_buttons, x=0.0, y=1.0, xanchor="left",
                        yanchor="top", showactive=True)]

    fig.update_layout(
        title=dict(text=TITLE),
        scene=dict(xaxis=dict(title=dict(text="Time to maturity (years)")),
                   yaxis=dict(title=dict(text=y_title)),
                   zaxis=dict(title=dict(text="Implied volatility (%)"))),
        sliders=sliders, updatemenus=updatemenus,
        height=1000, margin=dict(l=40, r=40, t=80, b=80), legend=dict(font=dict(size=10)),
    )
    fig.update_xaxes(title_text=("Strike" if by_strike else _K_TITLE), row=2, col=1)
    fig.update_yaxes(title_text="Implied volatility (%)", row=2, col=1)
    fig.update_xaxes(title_text="Time to maturity (years)", row=2, col=2)
    fig.update_yaxes(title_text="Implied volatility (%)", row=2, col=2)
    return fig


def _add_term(fig, ts, name, dash=None):
    """Add one term-structure trace (x = T years, y = IV percent); out-of-domain points are NaN, a gap in the line (R13)."""
    in_dom = ts["in_domain"].to_numpy(bool)
    # R13: out-of-domain points (in_domain False, from term_structure, not recomputed here) are y = NaN,
    # i.e. a gap in the line, never an extrapolated value presented as a market fact.
    y_pct = np.where(in_dom, 100.0 * ts["iv"].to_numpy(float), np.nan)
    fig.add_trace(go.Scatter(
        x=ts["T"].to_numpy(float), y=y_pct, mode="lines+markers",
        name=name, line=dict(dash=dash) if dash else None,
        marker=dict(size=5),
        customdata=np.column_stack([ts["k"].to_numpy(float)]),
        hovertemplate=("T=%{x:.3f}y<br>IV: %{y:.2f}%<br>k=%{customdata[0]:.4f}"
                       "<extra>" + name + "</extra>")),
        row=2, col=2)


def write_dashboard(fig, path, plotlyjs="cdn"):
    """Write the figure as a standalone HTML file (CONTRACT.md 7.2) and return its absolute path.

    plotlyjs "cdn" (default, needs internet when the file is opened) or "inline" (fully offline,
    about 5 MB). Creates missing parent directories. Raises ValueError for any other plotlyjs.
    """
    if plotlyjs not in _VALID_PLOTLYJS:
        raise ValueError("plotlyjs must be one of %s, got %r" % (_VALID_PLOTLYJS, plotlyjs))
    out = os.path.abspath(str(path))
    parent = os.path.dirname(out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    fig.write_html(out, include_plotlyjs=plotlyjs, full_html=True)
    return out


def _selftest():
    """Tiny structural self-check on a synthetic Surface-like object; exits non-zero on failure."""
    import pandas as pd
    from types import SimpleNamespace

    class _P:
        S = 100.0
        valuation_date = datetime.date(2026, 1, 2)

        @staticmethod
        def forward(T):
            return 100.0 * np.exp(0.02 * np.asarray(T, float))

    T_grid = np.linspace(0.1, 1.0, 5)
    k_grid = np.linspace(-0.3, 0.3, 7)
    w = (0.04 * T_grid)[:, None] * (1 + 0.5 * k_grid[None, :] ** 2)
    iv = np.sqrt(w / T_grid[:, None])
    p = _P()
    F = p.forward(T_grid)

    def _eval(T, k):
        T = np.asarray(T, float)
        k = np.asarray(k, float)
        return np.sqrt(0.04 * (1 + 0.5 * k ** 2) + 0 * T)

    sf = SimpleNamespace(T_grid=T_grid, k_grid=k_grid, w=w, iv=iv, F=F,
                         K=F[:, None] * np.exp(k_grid[None, :]), params=p, dropped_T=(),
                         evaluate=_eval,
                         k_lo=np.full(5, -0.3), k_hi=np.full(5, 0.3),
                         in_domain=np.ones((5, 7), bool))   # R9/R10 fields
    q = pd.DataFrame({"strike": [95.0, 105.0], "T": [0.1, 0.55], "type": ["P", "C"],
                      "price": [1.0, 2.0], "F": [100.2, 101.1], "k": [-0.05, 0.04],
                      "iv": [0.2, 0.21], "w": [0.004, 0.024], "status": [0, 1]})
    fig = build_dashboard(sf, q, p)
    d = fig.to_dict()
    assert d["data"][0]["type"] == "surface" and d["data"][0]["hovertemplate"] == _HOVER
    assert "not guaranteed arbitrage-free" in d["layout"]["title"]["text"]
    # plotly 7 to_dict() base64-encodes numeric arrays ({'dtype','bdata','shape'}); read fig.data for shape
    assert np.shape(fig.data[0].z) == (7, 5), np.shape(fig.data[0].z)
    assert np.shape(fig.data[0].customdata) == (7, 5, 5)
    try:
        build_dashboard(sf, q, p, x_axis="bad")
    except ValueError:
        pass
    else:
        raise AssertionError("bad x_axis did not raise")
    print("viz selftest ok: %d traces" % len(fig.data))


if __name__ == "__main__":
    try:
        _selftest()
    except Exception as exc:  # noqa: BLE001 - report and exit non-zero
        print("viz selftest FAILED: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
