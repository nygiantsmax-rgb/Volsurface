"""main.py - CLI entry point for the implied-volatility surface dashboard (BUILD-C, CONTRACT.md section 8).

Run:  python main.py                       (synthetic chain, rbf, k axis, writes vol_surface.html, opens it)
      python main.py --no-open --out out/vol.html
      python main.py --csv chain.csv --spot 100 --rate 0.04 --div 0.01 [--valuation-date 2026-01-02]
      python main.py --ticker SPY            (optional; needs yfinance and network; never falls back to synthetic)

Exit codes (CONTRACT.md section 8): 0 success; 2 usage or input error (argparse, load/fetch failure, bad CSV);
3 build_surface raised ValueError (insufficient or unusable quotes); 1 any other exception.
Error text goes to stderr, ASCII only. Percent appears only in console text and the figure; every stored
field and every function argument is a decimal (CONTRACT.md section 1.2).

Control totals printed here and asserted (CONTRACT.md section 10, zero tolerance): loader rows read ==
kept + rejected; len(quotes) == independently recounted OTM rows == sum of status counts; iv finite <=>
status in {0,1}; surface.n_quotes_used == usable quotes outside dropped maturities. A broken identity
raises AssertionError (exit 1): the run fails loudly rather than printing a plausible dashboard.
"""
from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import sys
import webbrowser

import numpy as np

from bs_pricing import IV_STATUS_NAMES, IV_STATUS_NEWTON, IV_STATUS_BRENT
from synthetic import generate_chain, DEFAULT_S, DEFAULT_R, DEFAULT_Q
from data_io import MarketParams, load_chain_csv, fetch_yfinance_chain
from surface import prepare_quotes, build_surface, arbitrage_report
from viz import build_dashboard, write_dashboard

# R3 (REVIEW_A.md): exact wording, printed on the --ticker path only.
_TICKER_NOTE = ("note: European Black-Scholes with flat continuous r and q applied to American-style listed "
                "options; OTM-only quotes reduce but do not remove early-exercise and discrete-dividend bias; "
                "r is the --rate argument, not a market curve.")

EXIT_OK = 0
EXIT_OTHER = 1
EXIT_INPUT = 2
EXIT_SURFACE = 3


def _ascii(text):
    """Fold to ASCII for the console (map, never crash)."""
    return str(text).replace("–", "-").replace("—", "-").encode("ascii", "replace").decode("ascii")


def _err(msg):
    print(_ascii(msg), file=sys.stderr)


def _build_parser():
    p = argparse.ArgumentParser(
        prog="main.py",
        description="3D implied-volatility surface from an option chain -> standalone Plotly HTML dashboard. "
                    "Default: synthetic chain (no data or API keys needed).")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--csv", metavar="PATH", help="load the chain from CSV (requires --spot)")
    src.add_argument("--ticker", metavar="SYM", help="fetch a live chain via yfinance (optional, network)")
    p.add_argument("--spot", type=float, default=None, help="spot price (required with --csv)")
    p.add_argument("--rate", type=float, default=0.04, help="continuous risk-free rate, decimal (default 0.04)")
    p.add_argument("--div", type=float, default=None,
                   help="continuous dividend yield, decimal (default 0.0 with --csv, %s synthetic)" % DEFAULT_Q)
    p.add_argument("--valuation-date", metavar="YYYY-MM-DD", default=None,
                   help="valuation date; needed when the CSV has an `expiry` column")
    p.add_argument("--method", choices=("rbf", "spline"), default="rbf")
    p.add_argument("--x-axis", choices=("k", "strike"), default="k", dest="x_axis")
    p.add_argument("--colorscale", choices=("Viridis", "Plasma"), default="Viridis")
    p.add_argument("--n-T", type=int, default=60, dest="n_T", help="grid points in T (default 60)")
    p.add_argument("--n-k", type=int, default=80, dest="n_k", help="grid points in k (default 80)")
    p.add_argument("--noise-bps", type=float, default=None, dest="noise_bps",
                   help="synthetic only: multiplicative price noise in bps (default 5.0)")
    p.add_argument("--seed", type=int, default=None, help="synthetic only: RNG seed (default 0)")
    p.add_argument("--export-chain", metavar="PATH", default=None, dest="export_chain",
                   help="write the chain used as CSV (re-loadable with --csv)")
    p.add_argument("--out", metavar="PATH", default="vol_surface.html", help="output HTML (default vol_surface.html)")
    p.add_argument("--offline", action="store_true", help="embed plotly.js (about 5 MB) so the file works offline")
    p.add_argument("--no-open", action="store_true", dest="no_open", help="do not open the browser")
    return p


def _parse_date(text):
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("--valuation-date must be YYYY-MM-DD, got %r" % text)


def _acquire_chain(args):
    """Return (chain, params, notes, n_read, n_rejected, source). Raises ValueError/OSError/RuntimeError (exit 2).

    n_read / n_rejected are None unless independently known (D1): for --csv they come from the loader's
    rejects AND a separate raw line count of the file; for --ticker (fetch drops rows silently) and
    synthetic (generator drops sub-min_price rows) there is no rejected count, so None, never a made-up 0.
    `notes` are printed AFTER the params line (D7).
    """
    notes = []
    vdate = _parse_date(args.valuation_date) if args.valuation_date else None
    if args.csv:
        if args.spot is None:
            raise ValueError("--csv requires --spot")
        if args.noise_bps is not None or args.seed is not None:
            notes.append("note: --noise-bps/--seed apply to the synthetic chain only; ignored for --csv")
        params = MarketParams(S=args.spot, r=args.rate, q=0.0 if args.div is None else args.div,
                              valuation_date=vdate)
        chain, rejects = load_chain_csv(args.csv, params)
        raw_rows = _count_csv_data_rows(args.csv)      # independent of the loader's own accounting
        return chain, params, notes, raw_rows, len(rejects), "csv"
    if args.ticker:
        if args.noise_bps is not None or args.seed is not None:
            notes.append("note: --noise-bps/--seed apply to the synthetic chain only; ignored for --ticker")
        chain, params = fetch_yfinance_chain(args.ticker, risk_free_rate=args.rate, valuation_date=vdate)
        return chain, params, notes, None, None, "ticker"
    S = DEFAULT_S if args.spot is None else args.spot
    q = DEFAULT_Q if args.div is None else args.div
    chain = generate_chain(S=S, r=args.rate, q=q,
                           noise_bps=5.0 if args.noise_bps is None else args.noise_bps,
                           seed=0 if args.seed is None else args.seed)
    params = MarketParams(S=S, r=args.rate, q=q, valuation_date=vdate)
    return chain, params, notes, None, None, "synthetic"


def _count_csv_data_rows(path):
    """Raw data rows in a CSV: non-blank lines minus the header line (CONTRACT.md section 10 item 1)."""
    with open(path, encoding="utf-8-sig", newline="") as fh:
        n = sum(1 for line in fh if line.strip())
    return max(n - 1, 0)


def _expected_otm_count(chain, params):
    """CONTRACT.md section 10 item 2: independent recount of OTM rows straight from the chain."""
    F = np.asarray(params.forward(chain["T"].to_numpy(float)), float)
    k = np.log(chain["strike"].to_numpy(float) / F)
    is_put = (chain["type"].to_numpy() == "P")
    return int(np.sum((is_put & (k < 0)) | (~is_put & (k >= 0))))


def _run(args):
    try:
        chain, params, notes, n_read, n_rej, source = _acquire_chain(args)
    except (ValueError, OSError, RuntimeError) as exc:   # load/fetch/usage problems -> exit 2
        _err("input error: %s: %s" % (type(exc).__name__, exc))
        return EXIT_INPUT
    # R3: first console item, always printed.
    print("params: S=%.4f r=%.4f q=%.4f (continuous, decimal)" % (params.S, params.r, params.q))
    if args.ticker:
        print(_TICKER_NOTE)
    for note in notes:                               # D7: after the params line
        print(note)
    if source == "csv":
        # D1: n_read is a raw line count of the file; kept + rejected come from the loader. Can fail.
        print("chain: %d data rows in file, %d rejected, %d kept" % (n_read, n_rej, len(chain)))
        assert n_read == len(chain) + n_rej, \
            "control total 1 broken: %d file rows != %d kept + %d rejected" % (n_read, len(chain), n_rej)
    elif source == "ticker":
        print("chain: %d rows kept (rejected: n/a, ticker fetch drops rows silently)" % len(chain))
    else:
        print("chain: %d rows generated (rejected: n/a, synthetic)" % len(chain))
    if args.export_chain:
        out_dir = os.path.dirname(os.path.abspath(args.export_chain))
        os.makedirs(out_dir, exist_ok=True)
        chain.to_csv(args.export_chain, index=False, lineterminator="\n")
        print("chain exported: %s" % os.path.abspath(args.export_chain))

    quotes = prepare_quotes(chain, params)
    expected = _expected_otm_count(chain, params)
    status = quotes["status"].to_numpy()
    counts = {code: int(np.sum(status == code)) for code in sorted(IV_STATUS_NAMES)}
    assert len(quotes) == expected, "control total 2 broken: %d quotes vs %d OTM chain rows" % (len(quotes), expected)
    assert sum(counts.values()) == len(quotes), "control total 2 broken: status counts do not sum to len(quotes)"
    ok = np.isin(status, (IV_STATUS_NEWTON, IV_STATUS_BRENT))
    assert np.array_equal(ok, np.isfinite(quotes["iv"].to_numpy(float))), \
        "control total 4 broken: iv finite <=> status in {0,1} violated"
    print("quotes: %d OTM rows | status: %s" % (
        len(quotes), ", ".join("%s=%d" % (IV_STATUS_NAMES[c], counts[c]) for c in sorted(counts))))

    try:
        surface = build_surface(quotes, params, method=args.method, n_T=args.n_T, n_k=args.n_k)
    except ValueError as exc:
        _err("build_surface failed: %s" % exc)
        return EXIT_SURFACE
    dropped = tuple(surface.dropped_T)
    keep = ok & ~np.isin(np.round(quotes["T"].to_numpy(float), 12), np.round(np.asarray(dropped, float), 12))
    assert surface.n_quotes_used == int(np.sum(keep)), \
        "control total 3 broken: n_quotes_used %d vs %d" % (surface.n_quotes_used, int(np.sum(keep)))
    print("usable quotes: %d | dropped maturities (too few quotes): %s" % (
        surface.n_quotes_used, ", ".join("%.4fy" % t for t in dropped) if dropped else "none"))
    iv_ok = quotes["iv"].to_numpy(float)[ok]
    print("quoted IV range: %.2f%% to %.2f%%" % (100.0 * iv_ok.min(), 100.0 * iv_ok.max()))
    print("surface grid: %d T x %d k, method=%s" % (len(surface.T_grid), len(surface.k_grid), surface.method))

    report = arbitrage_report(surface)
    for line in report["lines"]:
        print(_ascii(line))

    fig = build_dashboard(surface, quotes, params, colorscale=args.colorscale, x_axis=args.x_axis)
    path = write_dashboard(fig, args.out, plotlyjs="inline" if args.offline else "cdn")
    print("wrote: %s (%d bytes)" % (path, os.path.getsize(path)))
    if not args.no_open:
        webbrowser.open(pathlib.Path(path).as_uri())
    return EXIT_OK


def main(argv=None):
    """CLI entry; returns the process exit code (CONTRACT.md section 8)."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:                       # argparse: 0 for --help, 2 for usage errors
        return int(exc.code) if isinstance(exc.code, int) else EXIT_INPUT
    try:
        return _run(args)
    except Exception as exc:  # noqa: BLE001 - reported loudly, exit 1
        _err("unexpected error: %s: %s" % (type(exc).__name__, exc))
        return EXIT_OTHER


if __name__ == "__main__":
    sys.exit(main())
