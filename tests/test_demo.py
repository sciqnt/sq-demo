"""sq-demo contract: deterministic, conformance-clean, offline, multi-account.

The demo portfolio is sciqnt's PUBLIC FACE (first-run experience, docs,
screenshots) — these tests pin the properties that make that safe: same figures
forever (seeded), schema-clean, no network. Three accounts in three currencies
(EUR/USD/GBP) so the first-run screen showcases cross-account, cross-currency
aggregation. (The platform's void-fill rule is the app's to test — see the NOTE.)
"""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "core"))
sys.path.insert(0, str(HERE.parents[0] / "src"))

import sq_demo                                                  # noqa: E402
from sq_demo import portfolio                                   # noqa: E402
from sq_schema import TransactionType, conformance              # noqa: E402

ASOF = datetime(2026, 6, 1, tzinfo=timezone.utc)


class TestDiscoveryContract(unittest.TestCase):
    def test_three_named_accounts(self):
        self.assertEqual(sq_demo.accounts(), ["growth", "usa", "trading"])
        self.assertTrue(callable(sq_demo.snapshot))
        self.assertTrue(callable(sq_demo.load_history))
        self.assertTrue(sq_demo.DEMO)

    def test_accounts_span_three_currencies(self):
        ccys = {sq_demo.snapshot(account=a).account.base_currency
                for a in sq_demo.accounts()}
        self.assertEqual(ccys, {"EUR", "USD", "GBP"})

    def test_account_label_resolves_bare_or_full(self):
        # the platform passes the bare label back; full id also works
        self.assertEqual(portfolio._resolve("growth"), "demo:growth")
        self.assertEqual(portfolio._resolve("demo:growth"), "demo:growth")


class TestEveryAccountConforms(unittest.TestCase):
    def test_conformance_clean_now_and_pit(self):
        for acct in sq_demo.accounts():
            self.assertEqual(conformance.check_snapshot(sq_demo.snapshot(account=acct)), [],
                             f"{acct} snapshot not conformance-clean")
            self.assertEqual(conformance.check_snapshot(sq_demo.snapshot(account=acct, asof=ASOF)), [],
                             f"{acct} PIT snapshot not conformance-clean")

    def test_history_is_rich(self):
        # the growth account exercises every transaction kind (incl. realised sells)
        txns = sq_demo.load_history(account="growth")
        types = {t.type for t in txns}
        for needed in (TransactionType.DEPOSIT, TransactionType.BUY,
                       TransactionType.SELL, TransactionType.DIVIDEND):
            self.assertIn(needed, types)
        self.assertTrue(any(t.fee for t in txns))

    def test_transaction_ids_unique_across_accounts(self):
        ids = [t.transaction_id for a in sq_demo.accounts()
               for t in sq_demo.load_history(account=a)]
        self.assertEqual(len(ids), len(set(ids)), "transaction ids collide across accounts")


class TestShowcaseProperties(unittest.TestCase):
    def test_trading_has_a_closed_position_with_realised_pl(self):
        snap = sq_demo.snapshot(account="trading", asof=ASOF)
        closed = [p for p in snap.positions if not p.is_open]
        self.assertTrue(closed, "trading account should have a fully-closed position")
        self.assertTrue(any(p.realized_pl_base != 0 for p in closed),
                        "the closed position should carry realised P/L")

    def test_trading_holds_crypto(self):
        snap = sq_demo.snapshot(account="trading")
        classes = {i.asset_class.name for i in snap.instruments}
        self.assertIn("CRYPTO", classes)


class TestDeterminism(unittest.TestCase):
    def test_same_figures_forever(self):
        for acct in sq_demo.accounts():
            a = sq_demo.snapshot(account=acct, asof=ASOF)
            b = sq_demo.snapshot(account=acct, asof=ASOF)
            self.assertEqual([(p.instrument_id, p.quantity, p.value_base) for p in a.positions],
                             [(p.instrument_id, p.quantity, p.value_base) for p in b.positions])
            self.assertEqual(a.cash_balances[0].amount, b.cash_balances[0].amount)

    def test_past_never_changes_as_walk_extends(self):
        portfolio._walks.clear()
        early = portfolio.price("demo:swrd", ASOF.date())
        portfolio.price("demo:swrd", datetime.now(timezone.utc).date())
        self.assertEqual(portfolio.price("demo:swrd", ASOF.date()), early)


# NOTE: the demo's "void-fill" behaviour (demo shows only when no real account is
# connected; demo never appears in the connect menu) is the PLATFORM's decision and
# is tested in the app repo:
#   sciqnt/sciqnt → core/tests/test_void_fill.py :: TestDemoVoidFill
# (the rule is `sq_platform.aggregated._apply_demo_void_fill`). It can't live here:
# it reaches into app internals (P11 — a connector must not depend on the app) and
# needs the demo to be a *discoverable* bundle, only true AFTER this conformance passes.


if __name__ == "__main__":
    unittest.main()
