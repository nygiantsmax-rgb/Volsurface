"""data_io.py - market inputs for the implied-volatility surface tool (BUILD-B).

Governing spec: .claude/CONTRACT.md section 5 (binding rulings: .claude/REVIEW_A.md).

Public API
----------
MarketParams            frozen dataclass: S, r, q, valuation_date; the ONLY definition of
                        the forward F(T) = S * exp((r - q) * T) (CONTRACT 1.2 / 5.1).
load_chain_csv(path, params=None) -> (chain, rejects)
fetch_yfinance_chain(ticker, ...) -> (chain, MarketParams)    optional, network, opt-in only
CHAIN_COLUMNS, REJECT_COLUMNS, REJECT_REASONS                 schema constants

Units (CONTRACT 1.2): T in years ACT/365, r and q continuous annual DECIMALS, prices per
share. No percent appears anywhere in this module.

Row-level data problems are QUARANTINED (returned in `rejects`); file-level problems
RAISE. Nothing is dropped silently: len(chain) + len(rejects) == data rows read
(CONTRACT 10, control total 1) is asserted before returning.

This module imports nothing from the project (yfinance is imported lazily inside
fetch_yfinance_chain). Running `python data_io.py` executes a real self-check and exits
non-zero on failure.
"""
from __future__ import annotations

import csv
import datetime
import math
import os
import sys
import tempfile
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Column order of a CHAIN frame (CONTRACT 2.1). sigma_true is appended only if present.
CHAIN_COLUMNS = ("strike", "T", "type", "price")
REJECT_COLUMNS = ("line", "reason", "raw")
REJECT_REASONS = ("non_numeric", "non_positive", "bad_type", "bad_date", "duplicate")

_TYPE_MAP = {"C": "C", "CALL": "C", "P": "P", "PUT": "P"}


# ---------------------------------------------------------------------------
# MarketParams
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MarketParams:
    """One valuation instant: spot, continuous rate, continuous dividend yield.

    S: spot price, finite and > 0.  r, q: continuously compounded annual rates as
    DECIMALS (0.04 = 4 percent), finite.  valuation_date: datetime.date or None
    (None = unknown; then only T-based chains work and hover labels fall back to
    "T=<T:.3f>y", CONTRACT 5.1).
    """

    S: float
    r: float
    q: float
    valuation_date: datetime.date | None = None

    def __post_init__(self):
        for name in ("S", "r", "q"):
            val = getattr(self, name)
            try:
                ok = math.isfinite(float(val))
            except (TypeError, ValueError):
                ok = False
            if not ok:
                raise ValueError("MarketParams.%s must be a finite number, got %r" % (name, val))
        if not float(self.S) > 0.0:
            raise ValueError("MarketParams.S must be > 0, got %r" % (self.S,))
        if self.valuation_date is not None and not isinstance(self.valuation_date, datetime.date):
            raise ValueError("MarketParams.valuation_date must be datetime.date or None")

    def forward(self, T):
        """F(T) = S * exp((r - q) * T). The single definition of the forward.

        T is array_like (years). Returns a float64 ndarray of the same shape, or a
        python float when T is a scalar. NaN in gives NaN out; no validation of T.
        """
        arr = np.asarray(T, dtype=np.float64)
        out = float(self.S) * np.exp((float(self.r) - float(self.q)) * arr)
        if arr.ndim == 0:
            return float(out)
        return out


# ---------------------------------------------------------------------------
# CSV loader
# ---------------------------------------------------------------------------
def _parse_float(text):
    """float(text) or None if empty/unparseable/non-finite (underscores rejected)."""
    s = text.strip()
    if s == "" or "_" in s:
        return None
    try:
        val = float(s)
    except ValueError:
        return None
    if not math.isfinite(val):
        return None
    return val


def _parse_iso_date(text):
    """yyyy-mm-dd -> datetime.date, or None."""
    s = text.strip()
    if len(s) != 10:
        return None
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return None


def _classify_row(rec, use_T, params):
    """Parse one CSV record (dict of lower-case header -> str).

    Returns (strike, T, type, price, sigma_true_or_None) or a reject reason string.
    Check ORDER (documented because one row can fail several checks; the first hit is
    the recorded reason): non_numeric, bad_type, bad_date, non_positive.
    (duplicate is decided by the caller, it needs the set of rows already accepted.)
    """
    strike = _parse_float(rec["strike"])
    price = _parse_float(rec["price"])
    if strike is None or price is None:
        return "non_numeric"
    T = None
    if use_T:
        T = _parse_float(rec["t"])
        if T is None:
            return "non_numeric"
    typ = _TYPE_MAP.get(rec["type"].strip().upper())
    if typ is None:
        return "bad_type"
    if not use_T:
        exp = _parse_iso_date(rec["expiry"])
        if exp is None:
            return "bad_date"
        T = (exp - params.valuation_date).days / 365.0
    if strike <= 0.0 or price <= 0.0 or T <= 0.0:
        return "non_positive"
    sig = None
    if "sigma_true" in rec:
        # ASSUMPTION (recorded in run-log): an unparseable sigma_true is NOT a reason to
        # quarantine the quote (it is ground truth for tests only); it becomes NaN.
        sig = _parse_float(rec["sigma_true"])
    return (strike, T, typ, price, sig)


def load_chain_csv(path, params=None):
    """Load and validate an option-chain CSV (CONTRACT 5.2).

    Format: UTF-8 (BOM tolerated), comma delimiter, header on file line 1, LF or CRLF.
    Header names are case-insensitive and whitespace-stripped. Required: strike, type,
    price, and ONE of T (years) or expiry (yyyy-mm-dd). If both T and expiry exist, T
    is used and expiry ignored. type accepts C/P/call/put in any case. Optional numeric
    sigma_true is kept (unparseable cell -> NaN). Unknown columns are dropped. Records
    must be single-line (no embedded newlines inside quoted fields).

    expiry requires params.valuation_date; T = (expiry - valuation_date).days / 365.0.

    Returns (chain, rejects).
    chain: CONTRACT 2.1 (strike, T, type, price[, sigma_true]); sorted by (T, strike,
    type) with C before P; RangeIndex.
    rejects: columns line (int, 1-based file line), reason (one of REJECT_REASONS), raw
    (the raw line). Quarantined: non-numeric/NaN/malformed record, strike<=0, price<=0,
    T<=0 (incl. expiry on/before the valuation date), bad type, bad date, and every
    duplicate (strike, T, type) after the first accepted one.

    Raises: FileNotFoundError (path); ValueError (empty file, missing required column,
    duplicate header names, expiry without params.valuation_date, zero rows left in
    chain). Control total: data rows read == len(chain) + len(rejects), asserted.
    """
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:  # FileNotFoundError propagates
        text = fh.read()
    lines = [ln[:-1] if ln.endswith("\r") else ln for ln in text.split("\n")]
    if not lines or lines[0].strip() == "":
        raise ValueError("CSV %s: empty file or blank header line" % (path,))

    header = [h.strip().lower() for h in next(csv.reader([lines[0]]))]
    if len(set(header)) != len(header):
        raise ValueError("CSV %s: duplicate header names %r" % (path, header))
    for need in ("strike", "type", "price"):
        if need not in header:
            raise ValueError("CSV %s: missing required column '%s' (found %r)" % (path, need, header))
    has_T = "t" in header
    has_exp = "expiry" in header
    if not has_T and not has_exp:
        raise ValueError("CSV %s: need a 'T' or an 'expiry' column (found %r)" % (path, header))
    use_T = has_T  # T wins when both are present (CONTRACT 5.2)
    if not use_T and (params is None or params.valuation_date is None):
        raise ValueError("CSV %s: 'expiry' column requires params.valuation_date" % (path,))

    rows = []        # accepted tuples
    seen = set()
    rej_line, rej_reason, rej_raw = [], [], []
    rows_read = 0
    for lineno, raw in enumerate(lines[1:], start=2):
        if raw.strip() == "":
            continue  # blank lines are not data rows (control total 1)
        rows_read += 1
        try:
            fields = next(csv.reader([raw]))
        except (csv.Error, StopIteration):
            fields = None
        if fields is None or len(fields) != len(header):
            res = "non_numeric"  # malformed record (wrong field count / bad quoting)
        else:
            res = _classify_row(dict(zip(header, fields)), use_T, params)
        if not isinstance(res, str):
            key = (res[0], res[1], res[2])
            if key in seen:
                res = "duplicate"
            else:
                seen.add(key)
        if isinstance(res, str):
            rej_line.append(lineno)
            rej_reason.append(res)
            rej_raw.append(raw)
        else:
            rows.append(res)

    cols = {
        "strike": np.array([r[0] for r in rows], dtype=np.float64),
        "T": np.array([r[1] for r in rows], dtype=np.float64),
        "type": [r[2] for r in rows],
        "price": np.array([r[3] for r in rows], dtype=np.float64),
    }
    if "sigma_true" in header:
        cols["sigma_true"] = np.array(
            [np.nan if r[4] is None else r[4] for r in rows], dtype=np.float64)
    chain = pd.DataFrame(cols)
    if len(chain):
        chain = chain.sort_values(["T", "strike", "type"], kind="mergesort").reset_index(drop=True)
    rejects = pd.DataFrame({
        "line": pd.Series(rej_line, dtype="int64"),
        "reason": pd.Series(rej_reason, dtype="str"),
        "raw": pd.Series(rej_raw, dtype="str"),
    })

    # Control total 1 (CONTRACT 10): fail loudly, never drop rows silently.
    if len(chain) + len(rejects) != rows_read:
        raise RuntimeError("control total failed: read %d != chain %d + rejects %d"
                           % (rows_read, len(chain), len(rejects)))
    if len(chain) == 0:
        counts = rejects["reason"].value_counts().to_dict() if len(rejects) else {}
        raise ValueError("CSV %s: zero valid rows (read %d, rejected by reason: %r)"
                         % (path, rows_read, counts))
    chain.attrs["rows_read"] = rows_read
    return chain, rejects


# ---------------------------------------------------------------------------
# yfinance adapter (optional; network; only via --ticker)
# ---------------------------------------------------------------------------
def _ascii(msg):
    return str(msg).encode("ascii", "replace").decode("ascii")


Q_MAX = 0.25  # REVIEW_A R2: a q outside [0, Q_MAX] is never used


def _choose_q(info):
    """REVIEW_A R2: q = trailingAnnualDividendYield if finite and in [0, Q_MAX]; else
    dividendYield/100 if finite and in [0, Q_MAX]; else 0.0. Pure function of the info dict."""
    def _num(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return None
        return v if math.isfinite(v) else None

    t = _num(info.get("trailingAnnualDividendYield"))
    if t is not None and 0.0 <= t <= Q_MAX:
        return t
    d = _num(info.get("dividendYield"))
    if d is not None and 0.0 <= d / 100.0 <= Q_MAX:
        return d / 100.0
    return 0.0


def fetch_yfinance_chain(ticker, max_expiries=8, min_days=7, risk_free_rate=0.04,
                         valuation_date=None):
    """Fetch a live chain via yfinance (CONTRACT 5.3). Returns (chain, MarketParams).

    Uses the nearest `max_expiries` expiries with >= `min_days` calendar days to
    expiry. price = (bid + ask) / 2 when bid > 0 and ask > 0, else lastPrice. q per
    REVIEW_A R2: trailingAnnualDividendYield if in [0, 0.25], else dividendYield/100 if in
    [0, 0.25], else 0.0 (a DECIMAL). S = last price.
    valuation_date default = today. Non-positive prices/strikes are dropped silently
    here (not reported; CONTRACT 5.3).

    EVERY failure (module missing, no network, empty data, no usable expiries, bad
    arguments) raises RuntimeError with an ASCII message; it NEVER falls back to
    synthetic data. Not exercised by selftest (no network assumption).
    q follows REVIEW_A R2 (see _choose_q): trailingAnnualDividendYield if in [0, 0.25],
    else dividendYield/100 if in [0, 0.25], else 0.0. The chosen q is returned in the
    MarketParams.
    """
    try:
        if int(max_expiries) < 1 or int(min_days) < 0:
            raise ValueError("max_expiries must be >= 1 and min_days >= 0")
        import yfinance as yf  # lazy: optional dependency

        val = valuation_date if valuation_date is not None else datetime.date.today()
        tk = yf.Ticker(str(ticker))
        info = {}
        try:
            info = tk.info or {}
        except Exception:  # info is best effort; S falls back to fast_info/history below
            info = {}
        S = None
        try:
            S = float(tk.fast_info["lastPrice"])
        except Exception:
            S = None
        if S is None or not math.isfinite(S) or S <= 0:
            hist = tk.history(period="5d")
            if hist is None or len(hist) == 0:
                raise RuntimeError("no price history for %s" % ticker)
            S = float(hist["Close"].iloc[-1])
        q = _choose_q(info)  # REVIEW_A R2 range guard
        params = MarketParams(S=S, r=float(risk_free_rate), q=q, valuation_date=val)

        usable = []
        for e in tk.options:
            exp = datetime.date.fromisoformat(e)
            if (exp - val).days >= int(min_days):
                usable.append(exp)
        usable = sorted(usable)[: int(max_expiries)]
        if not usable:
            raise RuntimeError("no usable expiries for %s (min_days=%s)" % (ticker, min_days))

        parts = []
        for exp in usable:
            oc = tk.option_chain(exp.isoformat())
            T = (exp - val).days / 365.0
            for frame, typ in ((oc.calls, "C"), (oc.puts, "P")):
                if frame is None or len(frame) == 0:
                    continue
                bid = frame["bid"].to_numpy(dtype=np.float64)
                ask = frame["ask"].to_numpy(dtype=np.float64)
                last = frame["lastPrice"].to_numpy(dtype=np.float64)
                use_mid = (bid > 0) & (ask > 0)
                price = np.where(use_mid, 0.5 * (bid + ask), last)
                parts.append(pd.DataFrame({
                    "strike": frame["strike"].to_numpy(dtype=np.float64),
                    "T": np.full(len(frame), T, dtype=np.float64),
                    "type": typ,
                    "price": price,
                }))
        if not parts:
            raise RuntimeError("empty option data for %s" % ticker)
        chain = pd.concat(parts, ignore_index=True)
        ok = (np.isfinite(chain["strike"]) & np.isfinite(chain["price"])
              & (chain["strike"] > 0) & (chain["price"] > 0))
        chain = chain.loc[ok.to_numpy()].copy()
        chain = chain.drop_duplicates(subset=["strike", "T", "type"], keep="first")
        if len(chain) == 0:
            raise RuntimeError("no usable quotes for %s after filtering" % ticker)
        chain = chain.sort_values(["T", "strike", "type"], kind="mergesort").reset_index(drop=True)
        return chain, params
    except Exception as exc:  # converted per CONTRACT 9, never swallowed
        raise RuntimeError(_ascii("fetch_yfinance_chain(%s) failed: %s: %s"
                                  % (ticker, type(exc).__name__, exc))) from exc


# ---------------------------------------------------------------------------
# __main__ self-check (real assertions; exits non-zero on failure)
# ---------------------------------------------------------------------------
def _selfcheck():
    p = MarketParams(S=100.0, r=0.04, q=0.015, valuation_date=datetime.date(2026, 1, 1))
    f1 = p.forward(1.0)
    assert abs(f1 - 100.0 * math.exp(0.025)) < 1e-12, f1
    assert p.forward(np.array([0.5, 1.0])).shape == (2,)
    for bad in (dict(S=0.0, r=0.0, q=0.0), dict(S=1.0, r=float("nan"), q=0.0)):
        try:
            MarketParams(**bad)
        except ValueError:
            pass
        else:
            raise AssertionError("MarketParams accepted %r" % (bad,))

    body = (
        "Strike,TYPE,Price,Expiry,junk\r\n"
        "100,call,5.5,2026-07-01,x\r\n"      # ok (181 days)
        "100,C,5.5,2026-07-01,x\r\n"         # duplicate
        "100,put,4.0,2026-07-01,x\r\n"       # ok
        "\r\n"                                # blank: not a data row
        "abc,C,1,2026-07-01,x\r\n"           # non_numeric
        "90,Z,1,2026-07-01,x\r\n"            # bad_type
        "90,P,1,2026-13-45,x\r\n"            # bad_date
        "90,P,1,2025-12-31,x\r\n"            # non_positive (expiry before valuation)
        "90,P,-1,2026-07-01,x\r\n"           # non_positive price
        "90,P,1,2026-07-01\r\n"              # malformed (field count) -> non_numeric
    )
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "chain.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write(body)
        chain, rej = load_chain_csv(path, p)
        assert len(chain) == 2, chain
        assert chain.attrs["rows_read"] == 9
        assert len(chain) + len(rej) == 9
        assert list(chain["type"]) == ["C", "P"], chain
        assert abs(chain["T"].iloc[0] - 181 / 365.0) < 1e-15
        assert list(rej["reason"]) == ["duplicate", "non_numeric", "bad_type", "bad_date",
                                       "non_positive", "non_positive", "non_numeric"], list(rej["reason"])
        assert list(rej["line"]) == [3, 6, 7, 8, 9, 10, 11], list(rej["line"])
        for name, mutator in (("no valuation date", lambda: load_chain_csv(path, None)),
                              ("missing file", lambda: load_chain_csv(os.path.join(td, "nope.csv"), p))):
            try:
                mutator()
            except (ValueError, FileNotFoundError):
                pass
            else:
                raise AssertionError("expected an error for: " + name)
        empty = os.path.join(td, "empty.csv")
        with open(empty, "w", encoding="utf-8", newline="") as fh:
            fh.write("strike,type,price,T\n100,C,-1,0.5\n")
        try:
            load_chain_csv(empty)
        except ValueError:
            pass
        else:
            raise AssertionError("zero-valid-rows file did not raise")
    # REVIEW_A R2: range guard (each case would give a different q if the guard were removed)
    assert _choose_q({"trailingAnnualDividendYield": 0.02, "dividendYield": 0.44}) == 0.02
    assert abs(_choose_q({"trailingAnnualDividendYield": 0.5, "dividendYield": 1.5}) - 0.015) < 1e-15
    assert _choose_q({"trailingAnnualDividendYield": 0.5, "dividendYield": 44.0}) == 0.0
    assert _choose_q({"dividendYield": float("nan")}) == 0.0 and _choose_q({}) == 0.0
    assert _choose_q({"trailingAnnualDividendYield": -0.01}) == 0.0
    return True


if __name__ == "__main__":
    try:
        _selfcheck()
    except Exception as exc:  # any failure -> non-zero exit
        sys.stderr.write("data_io selfcheck FAILED: %s: %s\n" % (type(exc).__name__, exc))
        sys.exit(1)
    print("data_io selfcheck ok")
    sys.exit(0)
