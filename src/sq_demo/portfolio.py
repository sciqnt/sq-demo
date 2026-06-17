"""The deterministic demo portfolio — sciqnt's public face.

Everything here is SYNTHETIC and SEEDED: fictional instruments, a fixed anchor
date, seeded price walks, scripted contribution/trade/dividend histories. The
same dates always produce the same figures, so screenshots, docs, and the
first-run experience are reproducible and contain nobody's real finances (owner
decision 2026-06-12: "those should be the public figures"). Dates up to *today*
extend the walks deterministically — past values never change as time passes.

THREE accounts in THREE currencies — to showcase cross-account, cross-currency
aggregation (the platform converts each account's own-currency totals into the
portfolio base via the FX provider):

  * demo:growth  (EUR) — a long-term ETF/stock/bond ISA, monthly deposits.
  * demo:usa     (USD) — a US brokerage: index ETF, a mega-cap, a REIT.
  * demo:trading (GBP) — an active account: a UK stock, a crypto holding, and a
                         fully-closed position (realised P/L).
"""
import random
from datetime import date, datetime, time, timezone
from decimal import Decimal

from sq_schema import (
    Account, AssetClass, CashBalance, Instrument, PortfolioSnapshot,
    Transaction, TransactionType,
)
from sq_compute import fold_position

ANCHOR = date(2023, 1, 2)
_Q8 = Decimal("0.00000001")
_2DP = Decimal("0.01")

# instrument_id -> (ticker, name, asset_class, start_price, drift, vol)
_INST = {
    # demo:growth (EUR)
    "demo:swrd": ("SWRD", "Sample World ETF", AssetClass.ETF, Decimal("75"), 0.00045, 0.008),
    "demo:sqtc": ("SQTC", "Sample Tech Co", AssetClass.STOCK, Decimal("120"), 0.00065, 0.018),
    "demo:sbnd": ("SBND", "Sample Bond ETF", AssetClass.BOND, Decimal("100"), 0.00006, 0.0015),
    # demo:usa (USD)
    "demo:s500": ("S500", "Sample 500 ETF", AssetClass.ETF, Decimal("400"), 0.00050, 0.009),
    "demo:mega": ("MEGA", "Sample Mega Cap", AssetClass.STOCK, Decimal("180"), 0.00080, 0.021),
    "demo:sret": ("SRET", "Sample REIT ETF", AssetClass.ETF, Decimal("90"), 0.00018, 0.012),
    # demo:trading (GBP)
    "demo:lon":  ("LON", "Sample London PLC", AssetClass.STOCK, Decimal("28"), 0.00040, 0.016),
    "demo:coin": ("COIN", "Sample Coin", AssetClass.CRYPTO, Decimal("45"), 0.00110, 0.050),
    "demo:spec": ("SPEC", "Sample Spec Co", AssetClass.STOCK, Decimal("60"), 0.00005, 0.028),
}

# account_id -> spec. `script` drives the deterministic event stream:
#   deposit:  (day_of_month, amount)            monthly contribution
#   buys:     [(day, instrument, budget), …]    recurring monthly buys
#   divs:     [(day, instrument, per_share, months), …]  income on the holding
#   extra_buys/sells: [(date, instrument, …)]   one-offs (sell fraction 1.0 = close)
ACCOUNTS = {
    "demo:growth": {
        "ccy": "EUR", "name": "Growth ISA (demo)",
        "script": {
            "deposit": (1, Decimal("500")),
            "buys": [(5, "demo:swrd", Decimal("300")),
                     (10, "demo:sqtc", Decimal("250")),
                     (12, "demo:sbnd", Decimal("400"))],
            "divs": [(20, "demo:swrd", Decimal("0.45"), (3, 6, 9, 12)),
                     (20, "demo:sbnd", Decimal("0.90"), (6, 12))],
            "sells": [(date(2024, 7, 15), "demo:sqtc", 0.3),
                      (date(2025, 11, 20), "demo:sqtc", 0.4)],
        },
    },
    "demo:usa": {
        "ccy": "USD", "name": "US Brokerage (demo)",
        "script": {
            "deposit": (2, Decimal("700")),
            "buys": [(6, "demo:s500", Decimal("450")),
                     (11, "demo:mega", Decimal("300")),
                     (16, "demo:sret", Decimal("200"))],
            "divs": [(24, "demo:s500", Decimal("0.55"), (3, 6, 9, 12)),
                     (24, "demo:sret", Decimal("0.70"), (1, 4, 7, 10))],
            "sells": [],
        },
    },
    "demo:trading": {
        "ccy": "GBP", "name": "Active Trading (demo)",
        "script": {
            "deposit": (3, Decimal("400")),
            "buys": [(7, "demo:lon", Decimal("350")),
                     (14, "demo:coin", Decimal("250"))],
            "divs": [(18, "demo:lon", Decimal("0.30"), (4, 10))],
            # opened, ridden, then fully closed → realised P/L + a closed row.
            "extra_buys": [(date(2024, 2, 8), "demo:spec", Decimal("1500"))],
            "sells": [(date(2025, 6, 12), "demo:spec", 1.0)],
        },
    },
}

_walks: dict[str, list] = {}          # instrument_id -> [(date, Decimal)]


def _walk(inst_id: str, upto: date) -> list:
    """Seeded daily close walk from ANCHOR to `upto`, cached + extended on
    demand. random.Random(inst_id) makes every run — on any machine, forever —
    produce the identical series."""
    _, _, _, start, drift, vol = _INST[inst_id]
    series = _walks.setdefault(inst_id, [])
    if not series:
        series.append((ANCHOR, start))
    rng = random.Random(inst_id)
    have = len(series)
    d, px = series[-1]
    steps = (upto - ANCHOR).days
    draws = [rng.gauss(drift, vol) for _ in range(max(steps, 0))]
    for k in range(have - 1, steps):
        d = date.fromordinal(ANCHOR.toordinal() + k + 1)
        px = (px * (Decimal(1) + Decimal(str(round(draws[k], 6))))).quantize(_Q8)
        series.append((d, px))
    return series


def price(inst_id: str, on: date) -> Decimal:
    """Close at-or-before `on` (weekends/holidays don't exist in demo-land)."""
    on = min(on, date.today())
    series = _walk(inst_id, on)
    idx = min((on - ANCHOR).days, len(series) - 1)
    return series[max(idx, 0)][1]


def _dt(d: date) -> datetime:
    return datetime.combine(d, time(10, 0), tzinfo=timezone.utc)


def _months(start: date, end: date, day: int):
    y, m = start.year, start.month
    while True:
        d = date(y, m, min(day, 28))
        if d > end:
            return
        if d >= start:
            yield d
        m += 1
        if m > 12:
            m, y = 1, y + 1


def accounts() -> list[str]:
    """The BARE account labels (the platform shows them as `demo:<label>` and
    passes each back as `account=` to snapshot()/load_history()). The PLATFORM
    decides whether the demo participates (it can't know about other brokers —
    modularity)."""
    return [k.split(":", 1)[1] for k in ACCOUNTS]


def _resolve(account: str | None) -> str:
    """Accept a bare label ('growth') or a full id ('demo:growth')."""
    if account is None:
        return next(iter(ACCOUNTS))
    if account in ACCOUNTS:
        return account
    full = f"demo:{account}"
    if full in ACCOUNTS:
        return full
    raise KeyError(f"unknown demo account: {account!r}")


def transactions(account: str | None = None, upto: date | None = None) -> list[Transaction]:
    """The scripted, deterministic history for ONE account (default the first).
    Sign conventions mirror sq-degiro's canonical adapter (BUY qty+/amount−,
    SELL qty−/amount+, income amount+)."""
    acct = _resolve(account)
    spec = ACCOUNTS[acct]
    ccy = spec["ccy"]
    script = spec["script"]
    today = upto or date.today()
    out: list[Transaction] = []
    obs = _dt(ANCHOR)
    qty_held: dict[str, Decimal] = {}
    n = 0
    short = acct.split(":", 1)[1]

    def emit(d, ttype, *, inst=None, qty=None, px=None, amount, fee=None, desc=None):
        nonlocal n
        n += 1
        out.append(Transaction(
            valid_at=_dt(d), observed_at=obs,
            transaction_id=f"demo-{short}-{n:04d}", account_id=acct,
            instrument_id=inst, type=ttype, executed_at=_dt(d),
            quantity=qty, price_local=px, amount=amount,
            amount_currency=ccy, fee=fee, description=desc))

    def buy(d, inst_id, budget):
        px = price(inst_id, d)
        qty = Decimal(int(budget / px))
        if qty < 1:
            return
        emit(d, TransactionType.BUY, inst=inst_id, qty=qty, px=px,
             amount=-(qty * px).quantize(_2DP), fee=Decimal("1.50"), desc="demo buy")
        qty_held[inst_id] = qty_held.get(inst_id, Decimal(0)) + qty

    def sell(d, inst_id, fraction):
        held = qty_held.get(inst_id, Decimal(0))
        qty = held if fraction >= 1.0 else Decimal(int(held * Decimal(str(fraction))))
        if qty < 1:
            return
        px = price(inst_id, d)
        emit(d, TransactionType.SELL, inst=inst_id, qty=-qty, px=px,
             amount=(qty * px).quantize(_2DP), fee=Decimal("1.50"), desc="demo sell")
        qty_held[inst_id] = held - qty

    # Build the dated event list, then replay in order.
    events: list[tuple[date, str, tuple]] = []
    dep_day, dep_amt = script["deposit"]
    for d in _months(ANCHOR, today, dep_day):
        events.append((d, "deposit", (dep_amt,)))
    for day, inst, budget in script["buys"]:
        for d in _months(ANCHOR, today, day):
            events.append((d, "buy", (inst, budget)))
    for day, inst, per_share, months in script["divs"]:
        for d in _months(ANCHOR, today, day):
            if d.month in months:
                events.append((d, "div", (inst, per_share)))
    for d, inst, budget in script.get("extra_buys", []):
        if d <= today:
            events.append((d, "buy", (inst, budget)))
    for d, inst, fraction in script["sells"]:
        if d <= today:
            events.append((d, "sell", (inst, fraction)))
    events.sort(key=lambda e: (e[0], e[1]))

    for d, kind, args in events:
        if kind == "deposit":
            emit(d, TransactionType.DEPOSIT, amount=args[0], desc="demo deposit")
        elif kind == "buy":
            buy(d, *args)
        elif kind == "sell":
            sell(d, *args)
        elif kind == "div":
            inst, per_share = args
            if qty_held.get(inst, Decimal(0)) > 0:
                emit(d, TransactionType.DIVIDEND, inst=inst,
                     amount=(qty_held[inst] * per_share).quantize(_2DP), desc="demo income")
    return out


def _held_instruments(account: str) -> list[str]:
    """Instruments this account touches (buys + extra_buys), declaration order."""
    s = ACCOUNTS[account]["script"]
    seen: list[str] = []
    for _, inst, _ in s["buys"]:
        if inst not in seen:
            seen.append(inst)
    for _, inst, _ in s.get("extra_buys", []):
        if inst not in seen:
            seen.append(inst)
    return seen


def build_snapshot(account: str | None = None, asof: datetime | None = None) -> PortfolioSnapshot:
    """Fold one account's scripted history into a conformance-clean snapshot,
    marked to the seeded walk's price at `asof` (default today). Single-currency
    per account → unrealised P/L is all product-driven (fx component zero)."""
    acct = _resolve(account)
    ccy = ACCOUNTS[acct]["ccy"]
    asof_d = (asof.date() if asof else date.today())
    txns = transactions(acct, upto=asof_d)
    obs = _dt(ANCHOR)
    held = _held_instruments(acct)

    instruments = [
        Instrument(valid_at=obs, observed_at=obs, instrument_id=iid,
                   identifiers={"ticker": _INST[iid][0], "demo": iid},
                   name=_INST[iid][1], asset_class=_INST[iid][2],
                   listing_currency=ccy, listing_venue="DEMO")
        for iid in held
    ]
    positions = []
    for iid in held:
        pos = fold_position(acct, iid, ccy,
                            [t for t in txns if t.instrument_id == iid
                             and t.type in (TransactionType.BUY, TransactionType.SELL)],
                            asof=asof or _dt(asof_d))
        if pos.is_open:
            px = price(iid, asof_d)
            value = (pos.quantity * px).quantize(_Q8)
            pos = pos.model_copy(update={
                "last_price_local": px.quantize(_Q8),
                "value_base": value,
                "unrealized_product_pl_base": (value - pos.cost_basis_base).quantize(_Q8),
                "unrealized_currency_pl_base": Decimal("0E-8"),
            })
        positions.append(pos)

    cash = Decimal("0")
    for t in txns:
        cash += t.amount
        if t.fee:
            cash -= abs(t.fee)
    account_obj = Account(valid_at=obs, observed_at=obs, account_id=acct,
                          broker="demo", base_currency=ccy,
                          display_name=ACCOUNTS[acct]["name"])
    return PortfolioSnapshot(
        valid_at=asof or _dt(asof_d), observed_at=asof or _dt(asof_d),
        account=account_obj, instruments=instruments, positions=positions,
        cash_balances=[CashBalance(valid_at=obs, observed_at=obs, account_id=acct,
                                   currency=ccy, amount=cash.quantize(_2DP),
                                   amount_base=cash.quantize(_2DP))],
    )
