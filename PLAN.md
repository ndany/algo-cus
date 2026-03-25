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

## Phase 1: Real Market Data + Core Visualization

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

## Phase 2: Walk-Forward Backtesting + Bias Guards

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

## Phase 6: Interactive Dashboard

**Goal**: Unified Dash app tying everything together.

### New Files
- `dashboard/app.py` — Main Dash application
- `dashboard/layouts/` — One module per tab
- `dashboard/callbacks/` — Interactivity per tab
- `dashboard/components.py` — Reusable UI pieces

### Tabs
1. Market Overview (candlestick, volume, regime, macro)
2. Strategy Lab (parameter sliders, real-time backtest)
3. Walk-Forward Analysis
4. Ensemble & Regime
5. Recommendations
6. Paper Trading
7. Learning Center

---

## Dependency Graph

```
Phase 1 (Data + Viz + Tests)
  |
  v
Phase 2 (Walk-Forward)
  |
  v
Phase 3 (Ensemble + Regime) ------> Phase 5 (FRED Macro)
  |                                       |
  v                                       v
Phase 4 (Recommendations) <--------------+
  |
  v
Phase 6 (Dashboard)
```

## Review Checkpoints

1. After Phases 1-2 (foundation)
2. After Phase 3 (core innovation)
3. After Phases 4-5 (recommendations + macro)
4. After Phase 6 (dashboard)

## Testing Strategy

- `pytest` with `pytest-cov` for coverage reporting
- Tests use synthetic data by default (fast, deterministic)
- Integration tests for yfinance/FRED marked with `@pytest.mark.integration`
- Coverage reports in `output/coverage/`

## Final Directory Structure

```
algo-cus/
  config.py
  backtest/       engine.py, walk_forward.py, bias_guards.py
  data/           sample_data.py, market_data.py, fred_data.py, cache/
  strategies/     base.py, 3 existing, regime_detector.py, ensemble.py
  recommendations/ engine.py, paper_trading.py, explainability.py
  visualization/  charts.py, walk_forward.py, regime.py, recommendations.py, macro.py
  dashboard/      app.py, components.py, layouts/, callbacks/
  tests/          mirroring each module
  examples/       run_backtest.py, run_dashboard.py, run_recommendation.py
  output/         (gitignored: HTML charts, paper trade logs, coverage)
```

## Known Risks

1. **yfinance fragility** — scrapes Yahoo Finance, can break. Mitigated by caching + synthetic fallback.
2. **Regime detection lag** — regimes easier to see in hindsight. Use only lagged indicators, visualize delay.
3. **FRED API key** — `fredapi` needs free key. Support env var with CSV fallback.
4. **Slippage realism** — 0.3% is an estimate. Configurable, paper trading will validate.
