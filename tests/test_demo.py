"""sq-demo contract: five personas, each with several (punny-broker) accounts on
REAL tickers, priced LIVE by the platform. Conformance-clean + offline here (the
bundle marks to a baked fallback; the live overlay is the platform's job). A
random persona is chosen each launch — so we test the SET via the `persona` seam.
"""
import re
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "core"))
sys.path.insert(0, str(HERE.parents[0] / "src"))

import sq_demo                                                  # noqa: E402
import sq_demo.portfolio as P                                  # noqa: E402
from sq_schema import TransactionType, conformance             # noqa: E402

ASOF = datetime(2026, 6, 1, tzinfo=timezone.utc)
_TICKER = re.compile(r"^[A-Z]{1,6}(-USD)?(\.[A-Z])?$")          # AAPL, BTC-USD, VWRL.L


def _accts(name):
    return list(P.PERSONAS[name]["accounts"])


class TestDiscoveryContract(unittest.TestCase):
    def test_five_personas(self):
        self.assertEqual(set(P.PERSONAS), {"bull", "bear", "crypto", "unlucky", "boglehead"})

    def test_chosen_persona_exposes_its_accounts(self):
        accts = sq_demo.accounts()
        self.assertGreaterEqual(len(accts), 2, "a persona should have ≥2 accounts to aggregate")
        self.assertEqual(accts, _accts(P._CHOSEN))

    def test_every_persona_has_multiple_accounts(self):
        for name in P.PERSONAS:
            self.assertGreaterEqual(len(_accts(name)), 2, f"{name} needs ≥2 accounts")

    def test_current_persona_metadata(self):
        meta = sq_demo.current_persona()
        self.assertIn(meta["id"], P.PERSONAS)
        self.assertTrue(meta["name"] and meta["emoji"] and meta["tagline"])


class TestEveryPersonaAccount(unittest.TestCase):
    def test_conformance_clean_now_and_pit(self):
        for name in P.PERSONAS:
            for acct in _accts(name):
                self.assertEqual(conformance.check_snapshot(P.build_snapshot(acct, persona=name)), [],
                                 f"{name}:{acct} not conformance-clean")
                self.assertEqual(
                    conformance.check_snapshot(P.build_snapshot(acct, persona=name, asof=ASOF)), [],
                    f"{name}:{acct} PIT not conformance-clean")

    def test_holdings_are_real_tickers_with_fallback_price(self):
        for name in P.PERSONAS:
            for acct in _accts(name):
                for inst in P.build_snapshot(acct, persona=name).instruments:
                    tk = inst.identifiers["ticker"]
                    self.assertRegex(tk, _TICKER, f"{name}:{acct}: {tk!r} not a real ticker")
                    self.assertIn(tk, P._NOW, f"{tk} missing a fallback price")
                    self.assertIn(tk, P._META, f"{tk} missing name/asset-class")

    def test_brokers_are_named(self):
        for name in P.PERSONAS:
            for acct, spec in P.PERSONAS[name]["accounts"].items():
                self.assertTrue(spec["broker"], f"{name}:{acct} has no broker name")

    def test_transaction_ids_unique_within_a_persona(self):
        for name in P.PERSONAS:
            ids = [t.transaction_id for a in _accts(name) for t in P.transactions(a, persona=name)]
            self.assertEqual(len(ids), len(set(ids)), f"{name}: txn ids collide")

    def test_each_account_has_a_deposit_and_buys(self):
        for name in P.PERSONAS:
            for acct in _accts(name):
                types = {t.type for t in P.transactions(acct, persona=name)}
                self.assertIn(TransactionType.DEPOSIT, types)
                self.assertIn(TransactionType.BUY, types)


class TestPersonaCharacter(unittest.TestCase):
    """Baked fallback (overridden by live) gives each persona its character —
    summed across its accounts."""
    def _upl(self, name):
        return sum((p.unrealized_pl_base
                    for a in _accts(name)
                    for p in P.build_snapshot(a, persona=name).positions if p.is_open), 0)

    def test_unlucky_is_underwater(self):
        self.assertLess(self._upl("unlucky"), 0)

    def test_bull_and_crypto_are_up(self):
        self.assertGreater(self._upl("bull"), 0)
        self.assertGreater(self._upl("crypto"), 0)

    def test_crypto_holds_crypto(self):
        classes = {i.asset_class.name for a in _accts("crypto")
                   for i in P.build_snapshot(a, persona="crypto").instruments}
        self.assertIn("CRYPTO", classes)

    def test_boglehead_spans_two_currencies(self):
        ccys = {P.build_snapshot(a, persona="boglehead").account.base_currency
                for a in _accts("boglehead")}
        self.assertEqual(ccys, {"GBP", "USD"})


class TestPerAccountDeterminism(unittest.TestCase):
    def test_same_account_same_figures(self):
        for name in P.PERSONAS:
            for acct in _accts(name):
                a = P.build_snapshot(acct, persona=name, asof=ASOF)
                b = P.build_snapshot(acct, persona=name, asof=ASOF)
                self.assertEqual([(p.instrument_id, p.value_base) for p in a.positions],
                                 [(p.instrument_id, p.value_base) for p in b.positions])


# NOTE: void-fill (demo only while nothing real is connected) is the PLATFORM's
# decision, tested in sciqnt/sciqnt → core/tests/test_void_fill.py.


if __name__ == "__main__":
    unittest.main()
