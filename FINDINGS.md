# sq-demo — findings & design notes

Living log. This bundle is synthetic — its "quirks" are design decisions.

- **Determinism contract:** `random.Random(instrument_id)` walks from a
  fixed anchor (2023-01-02); past values NEVER change as the series
  extends to today. Screenshots taken months apart agree on history.
- **Multi-currency (SUPERSEDES the old EUR-only rule, 2026-06-17):** three
  accounts — `demo:growth` (EUR), `demo:usa` (USD), `demo:trading` (GBP) — to
  showcase cross-account, cross-currency aggregation on the first-run screen.
  Determinism story: **per-account figures stay seeded, deterministic, offline**
  (the bundle itself still makes no network call). The cross-currency AGGREGATE
  is computed by the PLATFORM's FX provider (ECB): point-in-time, so a fixed
  `--asof` reproduces; the *"today"* top-line tracks live ECB reference rates
  (cached after first fetch). Trade-off vs the original EUR-only promise: the
  public *aggregate* is no longer byte-identical across days/offline — accepted
  to demonstrate the headline feature. Pin fixed demo FX rates if byte-perfect
  offline reproducibility of the aggregate is wanted back.
- **Fictional tickers** deliberately resolve nowhere:
  Yahoo/OpenFIGI misses are negative-cached and quiet; the 1D intraday
  view falls back to the daily two-point series (honest degradation).
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
