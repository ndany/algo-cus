# Trading Algorithm Innovation - Implementation Plan

## Overview

Evolve this educational trading algorithm project into a full recommendation engine with:
- Real market data (free APIs)
- Honest validation (walk-forward backtesting)
- Intelligent strategy combination (ensemble + regime detection)
- Explainable recommendations with paper trading
- Rich interactive visualization throughout

## Constraints

- **Data**: Free, publicly accessible APIs only (yfinance, FRED)
- **Execution**: Manual (system is a recommendation engine, not auto-trader)
- **Purpose**: Learning about markets and algorithmic trading
- **Validation**: Must be able to verify recommendation quality and correctness
- **Visualization**: First-class concern throughout, not bolted on at the end

## Configuration

| Parameter | Default | Notes |
|-----------|---------|-------|
| Tickers | AMZN, GOOG, JPM, MSFT | Configurable list in `config.py` |
| Commission | 0.1% | Per trade |
| Slippage | 0.3% | Manual execution estimate |
| Initial Capital | $10,000 | Per backtest |

---

## Phase 1: Real Market Data + Core Visualization — DONE

**Goal**: Replace synthetic data with real yfinance data; establish plotly-based interactive charts.

### New Files
- `config.py` — Central configuration (tickers, slippage, paths)
- `data/__init__.py` — Package exports
- `data/market_data.py` — `MarketDataProvider` wrapping yfinance
  - Local parquet cache in `data/cache/` (gitignored)
  - NaN handling, gap detection, validation
  - Output matches existing DataFrame contract: `Date, Open, High, Low, Close, Volume`
- `data/fred_data.py` — Stub for Phase 5 (interface only)
- `visualization/__init__.py` — Package exports
- `visualization/charts.py` — Plotly interactive charts
  - Candlestick + volume
  - Strategy signal overlays (buy/sell markers)
  - Multi-strategy equity curve comparison
  - All functions return `plotly.Figure` (dashboard, Jupyter, or HTML)

### Modified Files
- `requirements.txt` — Add yfinance, plotly, dash, pytest, pytest-cov
- `.gitignore` — Add data/cache/, output/, .pytest_cache/
- `strategies/base.py` — Add `get_params()`, `set_params()`, `confidence()`
- All 3 strategy files — Implement `get_params()`/`set_params()`
- `examples/run_backtest.py` — Accept `--ticker` arg, use interactive charts

### Design Decisions
- DataFrame column contract (`Date, Open, High, Low, Close, Volume`) is sacred — zero changes to existing strategy/engine interfaces
- Parquet cache avoids rate limits and enables offline development
- Synthetic data remains as fallback for testing (deterministic, fast)

---

## Phase 2: Walk-Forward Backtesting + Bias Guards — DONE

**Goal**: Honest validation framework that prevents overfitting.

### New Files
- `backtest/walk_forward.py` — `WalkForwardEngine`
  - Sequential train/test splits preserving time order
  - Configurable: `n_splits`, `train_ratio`, `gap_days`
  - `WalkForwardResult` with per-fold metrics
  - `degradation_ratio` = out-of-sample / in-sample Sharpe (measures overfitting)
- `backtest/bias_guards.py`
  - Lookahead bias detection
  - Parameter stability testing
  - Buy-and-hold benchmark comparison
- `visualization/walk_forward.py`
  - Train/test window timeline on price chart
  - In-sample vs out-of-sample bar charts per fold
  - Parameter sensitivity heatmap

### Modified Files
- `backtest/engine.py`
  - Extract `calculate_metrics()` as standalone function
  - Add `start_date`/`end_date` slicing support
  - Add configurable `slippage` parameter (default 0.3%)

### Design Decisions
- Grid search for parameter optimization (transparent, not opaque ML)
- `gap_days` prevents information leakage at train/test boundaries
- `degradation_ratio` teaches overfitting visually

---

## Phase 3: Ensemble Framework + Regime Detection

**Goal**: Combine strategies intelligently based on market conditions.

### New Files
- `strategies/regime_detector.py` — Market regime classification
  - Regimes: `TRENDING_UP`, `TRENDING_DOWN`, `MEAN_REVERTING`, `HIGH_VOLATILITY`
  - Methods: ADX (trend strength), volatility ratio, Hurst exponent
- `strategies/ensemble.py` — `EnsembleStrategy(Strategy)`
  - Weighted vote based on current regime and strategy affinity
  - `SimpleVoteEnsemble` for equal-weight majority vote
- `visualization/regime.py`
  - Price chart with regime-colored background
  - Ensemble attribution (stacked area)
  - Strategy correlation heatmap

---

## Phase 4: Recommendation & Validation Layer

**Goal**: Explainable, actionable recommendations with paper trading.

### New Files
- `recommendations/engine.py` — `RecommendationEngine`
  - Confidence score (0-1): strategy agreement + regime clarity + historical accuracy
  - Plain-English reasoning for every recommendation
  - Risk level and suggested position size
- `recommendations/paper_trading.py` — `PaperTradingLog`
  - Log recommendations, record outcomes
  - Compare paper results vs backtest predictions
  - JSON persistence in `output/paper_trades.json`
- `recommendations/explainability.py`
  - Per-signal breakdown: indicator value, threshold, distance, historical context
- `visualization/recommendations.py`
  - Confidence gauge, reasoning panel
  - Paper trade timeline with P&L
  - Confidence calibration plot
  - Backtest-vs-paper overlay

---

## Phase 5: FRED Macro Data Integration

**Goal**: Add economic context to regime detection and recommendations.

### Modified Files
- `data/fred_data.py` — Complete implementation
  - Series: Fed Funds rate, yield curve, VIX, unemployment, CPI
  - Forward-fill to align with daily price data
- `strategies/regime_detector.py` — Add `detect_with_macro()`
  - Inverted yield curve = risk-off
  - VIX spike = high-volatility regime
- `visualization/macro.py`
  - Macro indicator dashboard
  - Regime-macro correlation chart

---

## Web Dashboard — DONE (built early, before Phase 3)

**Goal**: Deployable web app with dark trader workstation UX.

### What Was Built
- `dashboard/app.py` — Dash app with progressive disclosure (summary → strategy drill-down)
- `dashboard/auth.py` — Supabase Google OAuth + invitation codes
- `dashboard/theme.py` — Dark color palette, custom plotly `trader_dark` template
- `dashboard/assets/style.css` — Trader workstation CSS (JetBrains Mono, cyan/green/red accents)
- `dashboard/analysis.py` — Orchestrates data fetch → strategies → backtests → walk-forward
- `Procfile` + `render.yaml` — Render deployment config

### UX Flow
1. Enter ticker → ANALYZE
2. Summary: metrics tiles, candlestick, portfolio comparison, strategy cards
3. Click strategy → detail: signals, drawdown, walk-forward
4. Back to summary

### Deployment
- Render free tier (with UptimeRobot to avoid cold starts)
- Supabase for auth + invitation codes
- See `docs/DEPLOYMENT.md` for progressive scaling roadmap (5 stages, free → $40/month)

### Future Dashboard Additions (as phases complete)
- Phase 3: Regime overlay on price chart, ensemble attribution view
- Phase 4: Recommendations tab, paper trading log
- Phase 5: Macro context panel on summary view

---

## Dependency Graph

```
Phase 1 (Data + Viz + Tests)       ✅ DONE
  |
  v
Phase 2 (Walk-Forward)             ✅ DONE
  |
  v
Web Dashboard                      ✅ DONE (built early)
  |
  v
Phase 3 (Ensemble + Regime) ------> Phase 5 (FRED Macro)
  |                                       |
  v                                       v
Phase 4 (Recommendations) <--------------+
  |
  v
Dashboard additions (per phase)
```

## Review Checkpoints

1. After Phases 1-2 + Web Dashboard (foundation) ← **current**
2. After Phase 3 (core innovation)
3. After Phases 4-5 (recommendations + macro)

## Testing Strategy

- `pytest` with `pytest-cov` for coverage reporting
- Tests use synthetic data by default (fast, deterministic)
- Integration tests for yfinance/FRED marked with `@pytest.mark.integration`
- Coverage reports in `output/coverage/`

## Final Directory Structure

```
algo-cus/
  config.py              Central configuration
  Procfile               Render deployment start command
  render.yaml            Render service configuration
  backtest/              engine.py, walk_forward.py, bias_guards.py
  data/                  sample_data.py, market_data.py, fred_data.py, cache/
  strategies/            base.py, 3 existing, regime_detector.py, ensemble.py
  recommendations/       engine.py, paper_trading.py, explainability.py
  visualization/         charts.py, walk_forward.py, regime.py, recommendations.py, macro.py
  dashboard/             app.py, auth.py, theme.py, analysis.py, assets/
  tests/                 mirroring each module
  examples/              run_backtest.py, run_recommendation.py
  output/                (gitignored: HTML charts, paper trade logs, coverage)
```

## Known Risks

1. **yfinance fragility** — scrapes Yahoo Finance, can break. Mitigated by caching + synthetic fallback.
2. **Regime detection lag** — regimes easier to see in hindsight. Use only lagged indicators, visualize delay.
3. **FRED API key** — `fredapi` needs free key. Support env var with CSV fallback.
4. **Slippage realism** — 0.3% is an estimate. Configurable, paper trading will validate.
