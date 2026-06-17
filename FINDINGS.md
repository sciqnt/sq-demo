# sq-demo — findings & design notes

Living log. The demo is curated transaction histories on REAL instruments,
priced by the REAL engine — its "quirks" are design decisions.

- **Personas, not synthetic walks (REWRITE 2026-06-17, supersedes the old
  EUR-only seeded-walk + 3-account designs):** five characters — 🐂 The Bull,
  🐻 The Bear, 🦍 The Crypto Bro, 📉 The Unlucky, 🧘 The Boglehead — each a PERSON
  with **2–3 broker accounts** (punny stand-ins for real brokers: Robberhood,
  Interactive Crokers, Coinvase, Bye-nance, Monomarket, Rearguard, Infidelity,
  Webully, Schwob) holding REAL tickers (AAPL, BTC-USD, VWRL.L, …). One persona is
  chosen at RANDOM each launch (`random.choice`, process-lifetime) while no real
  account is connected; its accounts aggregate into the Portfolio (some span
  currencies — e.g. the Boglehead's GBP + USD accounts — to exercise FX rollup).
  Account labels can repeat across personas (only one persona is active per
  launch); `build_snapshot(..., persona=)` is the test seam to reach any of them.
- **Live prices via the platform, baked fallback in the bundle:** the bundle holds
  NO live prices and makes NO network call — it marks positions to a baked recent
  level (`_NOW`) so it always renders + conformance runs offline. The PLATFORM's
  market-data overlay (yahoo) then OVERRIDES each holding with the live price by
  ticker; if the provider is throttled/offline, the baked value is the safe render
  (honest degradation). So: real tickers, real engine, live P/L when reachable,
  realistic P/L always. Cost basis is baked from realistic historical entry levels.
- **Determinism trade-off:** a GIVEN persona renders identically (baked), but the
  *figures move with the market* (live) and the *persona rotates* — the demo is no
  longer the frozen "public figures" source. Conscious owner decision: a live
  showcase of the real product beats frozen synthetic figures.
- **Real tickers resolve for real:** unlike the old fictional SWRD/SQTC, these are
  genuine Yahoo-resolvable symbols (`.L` = LSE, `-USD` = crypto pair). They're
  illustrative example holdings, not endorsements (see `NOTICE.md`).
- **Sign conventions** mirror sq-degiro's canonical adapter (BUY qty+/
  amount−, SELL qty−/amount+, income amount+, fee positive-magnitude).
- **Weekends don't exist in demo-land** — the walk has a close every
  calendar day. Harmless for the demo's purpose; noted for honesty.
- **The BUNDLE is offline; the platform isn't necessarily** — the summary
  tab's benchmark line (vs IWDA.AS) does its own live price fetch even in
  demo mode, and degrades gracefully without network. Demo FIGURES stay
  deterministic; the benchmark comparison line may vary/disappear.
- **Live-verified (2026-06-17, multi-account):** full engine across the three
  accounts → portfolio aggregate ~116,912 USD (via ECB), +39,949 total P/L
  (realised + unrealised split), 8 open + 1 closed position, per-broker XIRR/TWR/
  drawdown, history chart, income + flows. Per-account figures are reproducible;
  the USD aggregate tracks the ECB rate at render time.
