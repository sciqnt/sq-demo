"""sq-demo — the demo portfolio: real products, real engine, five personas.

Each persona is a curated transaction history on REAL tickers; sciqnt's actual
market-data pipeline prices it LIVE (the demo holds no synthetic prices). A
different persona is chosen at random each launch while no real account is
connected (the platform's void-fill rule decides participation). Cost basis is
baked from realistic entry levels (robust, always renders); current value + P/L
are live. See `portfolio.py` for the determinism trade-off.

Discovery contract (same as every broker bundle):
  * `accounts()` — this launch's persona label; the platform shows `demo:<label>`.
  * `snapshot(asof=None, *, account=None)` — positions on real tickers, priced at
    cost; the platform's overlay marks them to live by ticker.
  * `load_history(account=None)` — the persona's transaction stream.
  * `current_persona()` — name/emoji/tagline for the home banner.
"""
from datetime import datetime
from typing import Optional

from .portfolio import accounts, build_snapshot, current_persona, transactions

DEMO = True                       # the platform's marker for void-fill


def snapshot(asof: Optional[datetime] = None, *, account: Optional[str] = None):
    return build_snapshot(account=account, asof=asof)


def load_history(account: Optional[str] = None):
    return transactions(account=account)


__all__ = ["snapshot", "accounts", "load_history", "current_persona", "DEMO"]
