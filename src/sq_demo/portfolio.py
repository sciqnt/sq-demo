"""The demo portfolio — real products, the real engine, five personas.

The demo is no longer synthetic price walks. Each persona is a curated
TRANSACTION HISTORY on REAL tickers; sciqnt's actual pipeline does the rest — the
market-data provider (yahoo) marks every holding to LIVE price, FX converts, the
engine computes P/L / TWR / drawdown / charts. So the first-run screen is a real
demonstration of the product on a known portfolio, not a fiction.

Determinism trade-off (supersedes the old "EUR-only, offline, frozen figures"
rule): the COST BASIS is baked from realistic historical entry levels (so a
persona always renders fast and never breaks when yahoo throttles), but the
CURRENT value + P/L are LIVE — they move with the market. That's the point: the
personas' *character* is their entry timing/choices; the live market scores them.

A different persona is chosen at RANDOM each launch (process lifetime) while no
real account is connected (the platform's void-fill rule decides participation).
"""
import random
from datetime import date, datetime, time, timezone
from decimal import Decimal

from sq_schema import (
    Account, AssetClass, CashBalance, Instrument, PortfolioSnapshot,
    Transaction, TransactionType,
)
from sq_compute import fold_position

_2DP = Decimal("0.01")
_OBS = datetime(2023, 1, 2, tzinfo=timezone.utc)   # fixed knowledge-time anchor

ETF, STOCK, BOND, CRYPTO = (AssetClass.ETF, AssetClass.STOCK,
                            AssetClass.BOND, AssetClass.CRYPTO)

# A holding = (ticker, name, asset_class, currency, [(buy_date, cash, entry_px), …]).
# entry_px is the baked realistic historical level paid; qty = cash / entry_px.
# The LIVE current price comes from the platform's market-data overlay by ticker.
PERSONAS = {
    "bull": {
        "emoji": "🐂", "tagline": "rode big tech all the way up",
        "ccy": "USD", "name": "The Bull",
        "deposits": [("2023-02-01", "12000"), ("2024-02-01", "8000")],
        "holdings": [
            ("AAPL", "Apple", STOCK, "USD", [("2023-02-06", "4000", "151")]),
            ("MSFT", "Microsoft", STOCK, "USD", [("2023-02-06", "4000", "258")]),
            ("NVDA", "NVIDIA", STOCK, "USD", [("2023-03-01", "3000", "23"),
                                              ("2024-02-05", "4000", "70")]),
            ("AMZN", "Amazon", STOCK, "USD", [("2023-04-03", "3000", "102")]),
        ],
    },
    "bear": {
        "emoji": "🐻", "tagline": "defensive, hedged, sat out the rally",
        "ccy": "USD", "name": "The Bear",
        "deposits": [("2023-02-01", "20000")],
        "holdings": [
            ("BND", "Total Bond ETF", BOND, "USD", [("2023-02-06", "5000", "72")]),
            ("GLD", "Gold ETF", ETF, "USD", [("2023-02-06", "5000", "172")]),
            ("KO", "Coca-Cola", STOCK, "USD", [("2023-03-01", "3000", "60")]),
            ("XLU", "Utilities ETF", ETF, "USD", [("2023-03-01", "3000", "68")]),
        ],
    },
    "crypto": {
        "emoji": "🦍", "tagline": "all in on coins, white-knuckle ride",
        "ccy": "USD", "name": "The Crypto Bro",
        "deposits": [("2023-02-01", "9000"), ("2024-10-01", "6000")],
        "holdings": [
            ("BTC-USD", "Bitcoin", CRYPTO, "USD", [("2023-02-06", "5000", "23000"),
                                                   ("2024-10-02", "4000", "62000")]),
            ("ETH-USD", "Ethereum", CRYPTO, "USD", [("2023-02-06", "3000", "1600")]),
            ("SOL-USD", "Solana", CRYPTO, "USD", [("2023-03-01", "2000", "22")]),
        ],
    },
    "unlucky": {
        "emoji": "📉", "tagline": "bought the tops, sold the bottoms",
        "ccy": "USD", "name": "The Unlucky",
        "deposits": [("2023-02-01", "15000")],
        "holdings": [
            # entry levels near the highs → live shows the damage
            ("PYPL", "PayPal", STOCK, "USD", [("2023-02-06", "4000", "85")]),
            ("INTC", "Intel", STOCK, "USD", [("2023-02-06", "4000", "30"),
                                             ("2024-01-15", "3000", "50")]),
            ("DIS", "Disney", STOCK, "USD", [("2023-04-03", "4000", "100")]),
        ],
    },
    "boglehead": {
        "emoji": "🧘", "tagline": "boring monthly index DCA, quietly winning",
        "ccy": "GBP", "name": "The Boglehead",
        "deposits": [("2023-02-01", "10000"), ("2024-02-01", "6000")],
        "holdings": [
            ("VWRL.L", "Vanguard FTSE All-World", ETF, "GBP",
             [("2023-02-06", "6000", "88"), ("2024-02-05", "4000", "100")]),
            ("AGGG.L", "iShares Global Bond", BOND, "GBP", [("2023-02-06", "4000", "4.4")]),
            ("VUSA.L", "Vanguard S&P 500", ETF, "GBP", [("2023-03-01", "4000", "62")]),
        ],
    },
}

# Recent fallback price per ticker (USD/GBP per the listing). Used ONLY when the
# live market-data overlay can't reach the provider (yahoo throttled / offline) —
# so the demo always renders realistic P/L instead of a flat "0.00". When the
# overlay succeeds it OVERRIDES these with the real live price. Refresh now & then.
_NOW = {
    "AAPL": "298", "MSFT": "386", "NVDA": "206", "AMZN": "240",          # bull
    "BND": "73", "GLD": "310", "KO": "70", "XLU": "80",                  # bear
    "BTC-USD": "100000", "ETH-USD": "3800", "SOL-USD": "190",            # crypto
    "PYPL": "72", "INTC": "20", "DIS": "115",                            # unlucky
    "VWRL.L": "115", "AGGG.L": "4.3", "VUSA.L": "90",                    # boglehead
}

# Pick ONE persona per process — un-seeded, so it rotates each launch.
_CHOSEN = random.choice(list(PERSONAS))


def accounts() -> list[str]:
    """One account this launch: the randomly-chosen persona. The platform shows
    it as `demo:<persona>` and passes the bare label back to snapshot()."""
    return [_CHOSEN]


def _resolve(account: str | None) -> str:
    if account is None:
        return _CHOSEN
    return account.split(":", 1)[1] if account.startswith("demo:") else account


def _dt(d: str | date) -> datetime:
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return datetime.combine(d, time(10, 0), tzinfo=timezone.utc)


def current_persona() -> dict:
    """The persona chosen for this launch (name/emoji/tagline) — the home banner
    can show 'demo: The Crypto Bro 🦍 — all in on coins'."""
    p = PERSONAS[_CHOSEN]
    return {"id": _CHOSEN, "name": p["name"], "emoji": p["emoji"], "tagline": p["tagline"]}


def transactions(account: str | None = None, upto: date | None = None) -> list[Transaction]:
    """The persona's scripted history on REAL tickers (deposits + dated buys at
    baked historical entry prices). Sign conventions mirror sq-degiro's adapter."""
    acct = _resolve(account)
    p = PERSONAS[acct]
    ccy = p["ccy"]
    today = upto or date.today()
    out: list[Transaction] = []
    n = 0

    def emit(d, ttype, *, inst=None, qty=None, px=None, amount, fee=None, desc=None):
        nonlocal n
        vd = _dt(d)
        if vd.date() > today:
            return
        n += 1
        out.append(Transaction(
            valid_at=vd, observed_at=_OBS, transaction_id=f"demo-{acct}-{n:04d}",
            account_id=f"demo:{acct}", instrument_id=inst, type=ttype, executed_at=vd,
            quantity=qty, price_local=px, amount=amount, amount_currency=ccy,
            fee=fee, description=desc))

    for d, amt in p["deposits"]:
        emit(d, TransactionType.DEPOSIT, amount=Decimal(amt), desc="demo deposit")
    for ticker, _name, _ac, _ccy, lots in p["holdings"]:
        iid = f"demo:{ticker}"
        for d, cash, entry in lots:
            entry_px = Decimal(entry)
            qty = (Decimal(cash) / entry_px).quantize(Decimal("0.00000001"))
            emit(d, TransactionType.BUY, inst=iid, qty=qty, px=entry_px,
                 amount=-(qty * entry_px).quantize(_2DP), fee=Decimal("1.50"),
                 desc=f"demo buy {ticker}")
    out.sort(key=lambda t: t.valid_at)
    return out


def build_snapshot(account: str | None = None, asof: datetime | None = None) -> PortfolioSnapshot:
    """Fold the persona's history into positions priced at the BAKED cost basis;
    the platform's market-data overlay then marks them to LIVE price by ticker
    (open positions whose ticker resolves get real current value + P/L; the rest
    pass through at cost — honest degradation). Real instruments, real engine."""
    acct = _resolve(account)
    p = PERSONAS[acct]
    ccy = p["ccy"]
    asof_d = (asof.date() if asof else date.today())
    txns = transactions(acct, upto=asof_d)

    instruments, positions = [], []
    for ticker, name, ac, listing_ccy, _lots in p["holdings"]:
        iid = f"demo:{ticker}"
        instruments.append(Instrument(
            valid_at=_OBS, observed_at=_OBS, instrument_id=iid,
            identifiers={"ticker": ticker}, name=name, asset_class=ac,
            listing_currency=listing_ccy, listing_venue="DEMO"))
        pos = fold_position(f"demo:{acct}", iid, listing_ccy,
                            [t for t in txns if t.instrument_id == iid
                             and t.type in (TransactionType.BUY, TransactionType.SELL)],
                            asof=asof or _dt(asof_d))
        if pos.is_open:
            # Mark to the recent fallback price; the platform's overlay OVERRIDES
            # with the live price by ticker when it can reach the provider. If it
            # can't (throttled/offline), this realistic value is the safe render.
            now_px = Decimal(_NOW.get(ticker, "0")) or pos.cost_basis_base / (pos.quantity or 1)
            value = (pos.quantity * now_px).quantize(Decimal("0.00000001"))
            pos = pos.model_copy(update={
                "last_price_local": now_px,
                "value_base": value,
                "unrealized_product_pl_base": (value - pos.cost_basis_base).quantize(Decimal("0.00000001")),
                "unrealized_currency_pl_base": Decimal("0E-8"),
            })
        positions.append(pos)

    cash = sum((t.amount for t in txns), Decimal("0"))
    cash -= sum((abs(t.fee) for t in txns if t.fee), Decimal("0"))
    account_obj = Account(valid_at=_OBS, observed_at=_OBS, account_id=f"demo:{acct}",
                          broker="demo", base_currency=ccy,
                          display_name=f"{p['name']} {p['emoji']} (demo)")
    return PortfolioSnapshot(
        valid_at=asof or _dt(asof_d), observed_at=asof or _dt(asof_d),
        account=account_obj, instruments=instruments, positions=positions,
        cash_balances=[CashBalance(valid_at=_OBS, observed_at=_OBS,
                                   account_id=f"demo:{acct}", currency=ccy,
                                   amount=cash.quantize(_2DP), amount_base=cash.quantize(_2DP))],
    )
