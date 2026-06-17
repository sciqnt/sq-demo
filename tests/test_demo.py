"""sq-demo contract: five personas on REAL tickers, conformance-clean, offline.

The demo is now real transactions on real tickers, priced LIVE by the platform's
market-data overlay. The CONNECTOR itself stays offline + deterministic: it marks
positions to a baked fallback price (the live overlay is the platform's job, not
the bundle's), so these tests need no network. A different persona is chosen at
random each launch — so we test the SET of personas, not a fixed one.
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


class TestDiscoveryContract(unittest.TestCase):
    def test_five_personas(self):
        self.assertEqual(set(P.PERSONAS), {"bull", "bear", "crypto", "unlucky", "boglehead"})

    def test_accounts_is_the_chosen_persona(self):
        accts = sq_demo.accounts()
        self.assertEqual(len(accts), 1)
        self.assertIn(accts[0], P.PERSONAS)

    def test_current_persona_metadata(self):
        meta = sq_demo.current_persona()
        self.assertIn(meta["id"], P.PERSONAS)
        self.assertTrue(meta["name"] and meta["emoji"] and meta["tagline"])

    def test_resolve_bare_or_full(self):
        self.assertEqual(P._resolve("bull"), "bull")
        self.assertEqual(P._resolve("demo:bull"), "bull")


class TestEveryPersona(unittest.TestCase):
    def test_conformance_clean_now_and_pit(self):
        for name in P.PERSONAS:
            self.assertEqual(conformance.check_snapshot(P.build_snapshot(name)), [],
                             f"{name} not conformance-clean")
            self.assertEqual(conformance.check_snapshot(P.build_snapshot(name, asof=ASOF)), [],
                             f"{name} PIT not conformance-clean")

    def test_holdings_are_real_tickers(self):
        for name in P.PERSONAS:
            snap = P.build_snapshot(name)
            for inst in snap.instruments:
                tk = inst.identifiers["ticker"]
                self.assertRegex(tk, _TICKER, f"{name}: {tk!r} doesn't look like a real ticker")
                self.assertIn(tk, P._NOW, f"{name}: {tk} has no fallback price in _NOW")

    def test_history_on_real_tickers(self):
        for name in P.PERSONAS:
            txns = P.transactions(name)
            self.assertTrue(any(t.type == TransactionType.DEPOSIT for t in txns))
            self.assertTrue(any(t.type == TransactionType.BUY for t in txns))

    def test_transaction_ids_unique_across_personas(self):
        ids = [t.transaction_id for n in P.PERSONAS for t in P.transactions(n)]
        self.assertEqual(len(ids), len(set(ids)))


class TestPersonaCharacter(unittest.TestCase):
    """The baked fallback (overridden by live) gives each persona its character."""
    def _upl(self, name):
        snap = P.build_snapshot(name)
        return sum((p.unrealized_pl_base for p in snap.positions if p.is_open), 0)

    def test_unlucky_is_underwater(self):
        self.assertLess(self._upl("unlucky"), 0, "the unlucky persona should show a loss")

    def test_bull_and_crypto_are_up(self):
        self.assertGreater(self._upl("bull"), 0)
        self.assertGreater(self._upl("crypto"), 0)

    def test_crypto_holds_crypto(self):
        classes = {i.asset_class.name for i in P.build_snapshot("crypto").instruments}
        self.assertIn("CRYPTO", classes)


class TestPerPersonaDeterminism(unittest.TestCase):
    def test_same_persona_same_figures(self):
        # rotation is random, but a GIVEN persona renders identically (baked).
        for name in P.PERSONAS:
            a, b = P.build_snapshot(name, asof=ASOF), P.build_snapshot(name, asof=ASOF)
            self.assertEqual([(p.instrument_id, p.value_base) for p in a.positions],
                             [(p.instrument_id, p.value_base) for p in b.positions])


# NOTE: void-fill (demo only while nothing real is connected) is the PLATFORM's
# decision, tested in sciqnt/sciqnt → core/tests/test_void_fill.py.


if __name__ == "__main__":
    unittest.main()
