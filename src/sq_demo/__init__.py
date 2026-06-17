"""sq-demo — the deterministic demo portfolio (sciqnt's public face).

Activates ONLY while no real account is connected (the platform's void-fill
rule; config `demo_mode`: auto|on|off). Fully synthetic, fully deterministic —
fictional instruments, seeded price walks, scripted multi-year histories. These
ARE the public figures: every screenshot, doc, and first-run screen renders from
here, never from anyone's real finances.

THREE accounts in THREE currencies (EUR/USD/GBP) so the first-run screen shows
cross-account, cross-currency aggregation — the platform converts each into the
portfolio base via the FX provider.

Discovery contract (same as every broker bundle):
  * `accounts()` — the demo account ids; the PLATFORM decides whether the demo
    participates (it can't know about other brokers — modularity).
  * `snapshot(asof=None, *, account=None)` — conformance-clean snapshot for one
    account at the seeded walk's prices; `asof` supported (PIT-correct).
  * `load_history(account=None)` — that account's canonical transaction stream
    (charts / TWR / XIRR / flows all derive from it, same as a broker).
"""
from datetime import datetime
from typing import Optional

from .portfolio import accounts, build_snapshot, transactions

DEMO = True                       # the platform's marker for void-fill


def snapshot(asof: Optional[datetime] = None, *, account: Optional[str] = None):
    return build_snapshot(account=account, asof=asof)


def load_history(account: Optional[str] = None):
    return transactions(account=account)


__all__ = ["snapshot", "accounts", "load_history", "DEMO"]
