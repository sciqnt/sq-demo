"""The demo portfolio — real products, the real engine, five personas.

Each persona is a PERSON with several broker accounts (punny stand-ins for real
brokers — Robberhood, Interactive Crokers, Coinvase, Monomarket …), each holding
REAL tickers. sciqnt's actual pipeline does the rest — the market-data provider
(yahoo) marks every holding to LIVE price, FX converts, the engine computes P/L /
TWR / drawdown / charts AND aggregates across the persona's accounts. So the
first-run screen is a real demonstration of cross-account, cross-currency
aggregation on a known portfolio, not a fiction.

A different persona is chosen at RANDOM each launch (process lifetime) while no
real account is connected. The persona's *character* is its accounts/entry timing;
the live market scores it. The bundle holds no live prices (marks to a baked
recent level, `_NOW`, so it always renders + conformance runs offline); the
platform's overlay OVERRIDES with the live price by ticker. Cost basis is baked
from realistic historical entry levels.
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
_Q8 = Decimal("0.00000001")
_OBS = datetime(2023, 1, 2, tzinfo=timezone.utc)
ETF, STOCK, BOND, CRYPTO = (AssetClass.ETF, AssetClass.STOCK,
                            AssetClass.BOND, AssetClass.CRYPTO)

# ticker -> (display name, asset_class)
_META = {
    "AAPL": ("Apple", STOCK), "MSFT": ("Microsoft", STOCK), "NVDA": ("NVIDIA", STOCK),
    "AMZN": ("Amazon", STOCK), "GOOGL": ("Alphabet", STOCK),
    "BND": ("Total Bond ETF", BOND), "GLD": ("Gold ETF", ETF),
    "KO": ("Coca-Cola", STOCK), "XLU": ("Utilities ETF", ETF),
    "PYPL": ("PayPal", STOCK), "INTC": ("Intel", STOCK), "DIS": ("Disney", STOCK),
    "PTON": ("Peloton", STOCK), "GME": ("GameStop", STOCK),
    "VWRL.L": ("Vanguard FTSE All-World", ETF), "VUSA.L": ("Vanguard S&P 500", ETF),
    "VT": ("Vanguard Total World", ETF),
    "BTC-USD": ("Bitcoin", CRYPTO), "ETH-USD": ("Ethereum", CRYPTO),
    "SOL-USD": ("Solana", CRYPTO), "DOGE-USD": ("Dogecoin", CRYPTO),
}

# Recent fallback price per ticker — used ONLY when the live overlay can't reach
# the provider (throttled/offline); the overlay overrides with the real price.
_NOW = {
    "AAPL": "298", "MSFT": "386", "NVDA": "206", "AMZN": "240", "GOOGL": "175",
    "BND": "73", "GLD": "310", "KO": "70", "XLU": "80",
    "PYPL": "72", "INTC": "20", "DIS": "115", "PTON": "7", "GME": "28",
    "VWRL.L": "115", "VUSA.L": "90", "VT": "125",
    "BTC-USD": "100000", "ETH-USD": "3800", "SOL-USD": "190", "DOGE-USD": "0.38",
}

# Each account: {broker, ccy, holdings: [(ticker, [(buy_date, cash, entry_px), …]), …]}.
# A deposit covering the buys (+ a cash buffer) is added automatically.
PERSONAS = {
    "bull": {
        "emoji": "🐂", "name": "The Bull", "tagline": "rode big tech all the way up",
        "accounts": {
            "robberhood": {"broker": "Robberhood", "ccy": "USD", "holdings": [
                ("AAPL", [("2023-02-06", "4000", "151")]),
                ("NVDA", [("2023-03-01", "3000", "23"), ("2024-02-05", "4000", "70")]),
                ("AMZN", [("2023-04-03", "3000", "102")])]},
            "crokers": {"broker": "Interactive Crokers", "ccy": "USD", "holdings": [
                ("MSFT", [("2023-02-06", "4000", "258")]),
                ("GOOGL", [("2023-03-01", "3000", "95")])]},
        },
    },
    "bear": {
        "emoji": "🐻", "name": "The Bear", "tagline": "defensive, hedged, sat out the rally",
        "accounts": {
            "rearguard": {"broker": "Rearguard", "ccy": "USD", "holdings": [
                ("BND", [("2023-02-06", "6000", "72")]),
                ("GLD", [("2023-02-06", "5000", "172")])]},
            "infidelity": {"broker": "Infidelity", "ccy": "USD", "holdings": [
                ("KO", [("2023-03-01", "3000", "60")]),
                ("XLU", [("2023-03-01", "3000", "68")])]},
        },
    },
    "crypto": {
        "emoji": "🦍", "name": "The Crypto Bro", "tagline": "all in on coins, white-knuckle ride",
        "accounts": {
            "coinvase": {"broker": "Coinvase", "ccy": "USD", "holdings": [
                ("BTC-USD", [("2023-02-06", "5000", "23000"), ("2024-10-02", "4000", "62000")]),
                ("ETH-USD", [("2023-02-06", "3000", "1600")])]},
            "byenance": {"broker": "Bye-nance", "ccy": "USD", "holdings": [
                ("SOL-USD", [("2023-03-01", "2000", "22")]),
                ("DOGE-USD", [("2023-03-01", "1500", "0.08")])]},
            "monomarket": {"broker": "Monomarket", "ccy": "USD", "holdings": [
                ("GME", [("2024-05-13", "2000", "30")])]},   # the meme yolo
        },
    },
    "unlucky": {
        "emoji": "📉", "name": "The Unlucky", "tagline": "bought the tops, sold the bottoms",
        "accounts": {
            "robberhood": {"broker": "Robberhood", "ccy": "USD", "holdings": [
                ("PYPL", [("2023-02-06", "4000", "85")]),
                ("INTC", [("2023-02-06", "4000", "30"), ("2024-01-15", "3000", "50")]),
                ("DIS", [("2023-04-03", "4000", "100")])]},
            "webully": {"broker": "Webully", "ccy": "USD", "holdings": [
                ("PTON", [("2023-02-06", "3000", "14")])]},
        },
    },
    "boglehead": {
        "emoji": "🧘", "name": "The Boglehead", "tagline": "boring index DCA, quietly winning",
        "accounts": {
            "rearguard": {"broker": "Rearguard", "ccy": "GBP", "holdings": [
                ("VWRL.L", [("2023-02-06", "6000", "88"), ("2024-02-05", "4000", "100")]),
                ("VUSA.L", [("2023-03-01", "4000", "62")])]},
            "schwob": {"broker": "Schwob", "ccy": "USD", "holdings": [
                ("VT", [("2023-02-06", "5000", "95")]),
                ("BND", [("2023-03-01", "3000", "72")])]},
        },
    },
}

# Pick ONE persona per process — un-seeded, so it rotates each launch.
_CHOSEN = random.choice(list(PERSONAS))


def accounts() -> list[str]:
    """This launch's persona's broker accounts (punny stand-ins). The platform
    shows each as `demo:<label>` and aggregates them under the Portfolio."""
    return list(PERSONAS[_CHOSEN]["accounts"])


def current_persona() -> dict:
    """The persona chosen for this launch — for the home banner."""
    p = PERSONAS[_CHOSEN]
    return {"id": _CHOSEN, "name": p["name"], "emoji": p["emoji"], "tagline": p["tagline"]}


def _resolve(account: str | None, persona: str | None = None) -> str:
    if account is None:
        return next(iter(PERSONAS[persona or _CHOSEN]["accounts"]))
    return account.split(":", 1)[1] if account.startswith("demo:") else account


def _dt(d: str | date) -> datetime:
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return datetime.combine(d, time(10, 0), tzinfo=timezone.utc)


def transactions(account: str | None = None, upto: date | None = None,
                 *, persona: str | None = None) -> list[Transaction]:
    """One broker account's scripted history on REAL tickers: an upfront deposit
    that funds the buys (+ a small cash buffer), then the dated buys at baked
    historical entry prices. Sign conventions mirror sq-degiro's adapter.
    `persona` defaults to this launch's chosen one (a test seam)."""
    pname = persona or _CHOSEN
    label = _resolve(account, pname)
    spec = PERSONAS[pname]["accounts"][label]
    ccy = spec["ccy"]
    today = upto or date.today()
    out: list[Transaction] = []
    n = 0

    buys = [(d, cash, entry, tk) for tk, lots in spec["holdings"]
            for (d, cash, entry) in lots if date.fromisoformat(d) <= today]
    funded = sum(Decimal(cash) for _, cash, _, _ in buys) + Decimal("1000")
    first = min((date.fromisoformat(d) for d, *_ in buys), default=date(2023, 2, 1))

    def emit(d, ttype, *, inst=None, qty=None, px=None, amount, fee=None, desc=None):
        nonlocal n
        n += 1
        vd = _dt(d)
        out.append(Transaction(
            valid_at=vd, observed_at=_OBS, transaction_id=f"demo-{label}-{n:04d}",
            account_id=f"demo:{label}", instrument_id=inst, type=ttype, executed_at=vd,
            quantity=qty, price_local=px, amount=amount, amount_currency=ccy,
            fee=fee, description=desc))

    emit(first, TransactionType.DEPOSIT, amount=funded.quantize(_2DP), desc="demo deposit")
    for d, cash, entry, tk in sorted(buys):
        entry_px = Decimal(entry)
        qty = (Decimal(cash) / entry_px).quantize(_Q8)
        emit(d, TransactionType.BUY, inst=f"demo:{tk}", qty=qty, px=entry_px,
             amount=-(qty * entry_px).quantize(_2DP), fee=Decimal("1.50"),
             desc=f"demo buy {tk}")
    out.sort(key=lambda t: t.valid_at)
    return out


def build_snapshot(account: str | None = None, asof: datetime | None = None,
                   *, persona: str | None = None) -> PortfolioSnapshot:
    """Fold one broker account's history into positions priced at the BAKED
    fallback; the platform's market-data overlay then marks them to LIVE by ticker
    (and aggregates the persona's accounts into the Portfolio)."""
    pname = persona or _CHOSEN
    label = _resolve(account, pname)
    spec = PERSONAS[pname]["accounts"][label]
    ccy = spec["ccy"]
    asof_d = (asof.date() if asof else date.today())
    txns = transactions(label, upto=asof_d, persona=pname)

    instruments, positions = [], []
    for tk, _lots in spec["holdings"]:
        iid = f"demo:{tk}"
        name, ac = _META[tk]
        instruments.append(Instrument(
            valid_at=_OBS, observed_at=_OBS, instrument_id=iid,
            identifiers={"ticker": tk}, name=name, asset_class=ac,
            listing_currency=ccy, listing_venue="DEMO"))
        pos = fold_position(f"demo:{label}", iid, ccy,
                            [t for t in txns if t.instrument_id == iid
                             and t.type in (TransactionType.BUY, TransactionType.SELL)],
                            asof=asof or _dt(asof_d))
        if pos.is_open:
            now_px = Decimal(_NOW.get(tk, "0")) or (pos.cost_basis_base / (pos.quantity or 1))
            value = (pos.quantity * now_px).quantize(_Q8)
            pos = pos.model_copy(update={
                "last_price_local": now_px, "value_base": value,
                "unrealized_product_pl_base": (value - pos.cost_basis_base).quantize(_Q8),
                "unrealized_currency_pl_base": Decimal("0E-8"),
            })
        positions.append(pos)

    cash = sum((t.amount for t in txns), Decimal("0"))
    cash -= sum((abs(t.fee) for t in txns if t.fee), Decimal("0"))
    account_obj = Account(valid_at=_OBS, observed_at=_OBS, account_id=f"demo:{label}",
                          broker="demo", base_currency=ccy,
                          display_name=f"{spec['broker']} (demo)")
    return PortfolioSnapshot(
        valid_at=asof or _dt(asof_d), observed_at=asof or _dt(asof_d),
        account=account_obj, instruments=instruments, positions=positions,
        cash_balances=[CashBalance(valid_at=_OBS, observed_at=_OBS,
                                   account_id=f"demo:{label}", currency=ccy,
                                   amount=cash.quantize(_2DP), amount_base=cash.quantize(_2DP))],
    )
