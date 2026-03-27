# Getting Started — Hands-On Validation Guide

Use this guide to set up the project, run it, and visually validate that everything works correctly.

## 1. Setup

```bash
# Clone and switch to the feature branch
git clone https://github.com/ndany/algo-cus.git
cd algo-cus
git checkout claude/trading-algorithm-innovation-llYOL

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

## 2. Run Tests (Verify Everything Works)

```bash
# Run all unit tests with coverage
python -m pytest tests/ -m "not integration" -q

# Expected: 75 tests passing, ~88% coverage
# Coverage HTML report generated at output/coverage/index.html
```

Open `output/coverage/index.html` in your browser to explore the coverage report.

## 3. Launch the Dashboard (Quickest Way to See Everything)

```bash
SKIP_AUTH=1 python -m dashboard.app
```

Open http://localhost:8050 in your browser.

**Visual validations:**
- [ ] Dark trader workstation theme loads (deep navy background, cyan accents)
- [ ] "ALGOSTATION" branding in the navbar with monospace font
- [ ] Empty state shows "Enter a ticker to begin" with dollar sign icon
- [ ] Ticker input has dark styling with uppercase transform

Now type `AMZN` in the ticker input and click **ANALYZE** (or press Enter).

**Wait 3-5 seconds** for yfinance to fetch data. The status bar will update.

**Summary view validations:**
- [ ] Status bar shows green checkmark with ticker name and elapsed time
- [ ] Top metrics row: ticker, buy & hold return, best strategy return, Sharpe, max drawdown, data points
- [ ] Metric values are color-coded: green for positive returns, red for negative, cyan for neutral
- [ ] Candlestick chart: green/red candles with volume bars below, dark background
- [ ] Portfolio comparison: three colored equity curves starting at $10,000
- [ ] Three strategy cards at the bottom with return, Sharpe, trade count, win rate, and robustness score
- [ ] All charts have the dark plotly theme (dark background, light gridlines)
- [ ] Charts are interactive: hover for values, zoom with drag, reset with double-click

**Click any strategy card** (e.g., "MA_Crossover(20,50)"):

**Strategy detail validations:**
- [ ] "← Back to Summary" button at the top
- [ ] Strategy name displayed in monospace
- [ ] Metrics row with return, Sharpe, max DD, trades, win rate, final value
- [ ] Signal chart: price line with green triangle-up (buy) and red triangle-down (sell) markers
- [ ] Drawdown chart: red shaded area showing peak-to-trough declines
- [ ] Walk-forward chart: grouped bars (green = in-sample, orange = out-of-sample) with degradation ratio
- [ ] Click "← Back to Summary" returns to the overview

**Try other tickers:** `GOOG`, `JPM`, `MSFT`

## 4. Backtest via CLI (Alternative to Dashboard)

```bash
python examples/run_backtest.py
```

**What to expect:**
- Terminal output showing metrics for 3 strategies (MA Crossover, RSI, Bollinger Bands)
- Interactive HTML charts saved in `output/`:
  - `Synthetic_candlestick.html` — Candlestick chart with volume bars
  - `Synthetic_MA_Crossover(20,50)_signals.html` — Price with buy/sell markers
  - `Synthetic_RSI(14)_signals.html` — Same for RSI
  - `Synthetic_Bollinger(20,2.0)_signals.html` — Same for Bollinger
  - `Synthetic_portfolio_comparison.html` — Equity curves overlaid
  - `Synthetic_metrics.html` — Side-by-side metrics table

```bash
# With real data
python examples/run_backtest.py --ticker AMZN
python examples/run_backtest.py --ticker AMZN GOOG JPM MSFT
```

**Visual validations:**
- [ ] Candlestick chart renders with green/red candles and volume bars below
- [ ] Buy signals (green triangles up) appear at logical points for each strategy
- [ ] Sell signals (red triangles down) appear at logical points
- [ ] MA Crossover: buy signals near where fast MA crosses above slow MA
- [ ] RSI: buy signals when price has dropped significantly (oversold)
- [ ] Bollinger: buy signals near the lower band
- [ ] Portfolio comparison: all three equity curves start at $10,000
- [ ] Charts are interactive (zoom, pan, hover shows values)
- [ ] Real price data looks correct (compare a chart to Yahoo Finance for sanity)

## 5. Walk-Forward Analysis

Open a Python session to run walk-forward validation interactively:

```python
import sys; sys.path.insert(0, ".")

from data import get_data
from strategies import MovingAverageCrossover, RSIStrategy, BollingerBandsStrategy
from backtest.walk_forward import WalkForwardEngine
from visualization.walk_forward import (
    plot_walk_forward_splits,
    plot_in_vs_out_sample,
    plot_degradation_summary,
)
from visualization.charts import save_figure

# Load data
data = get_data("AMZN")  # or "synthetic" for offline use

# Run walk-forward for each strategy
engine = WalkForwardEngine(n_splits=5, gap_days=5)

strategies = [
    MovingAverageCrossover(),
    RSIStrategy(),
    BollingerBandsStrategy(),
]

results = []
for s in strategies:
    result = engine.run(s, data)
    print(result.summary())
    results.append(result)

    # In-sample vs out-of-sample chart
    fig = plot_in_vs_out_sample(result)
    save_figure(fig, f"wf_{s.name}")

# Split visualization
splits_info = engine.get_splits_info(data)
fig = plot_walk_forward_splits(data, splits_info)
save_figure(fig, "wf_splits")

# Degradation ratio comparison
fig = plot_degradation_summary(results)
save_figure(fig, "wf_degradation")
```

**Visual validations:**
- [ ] `output/wf_splits.html` — Price chart with green (train) and orange (test) bands, non-overlapping
- [ ] `output/wf_MA_Crossover(20,50).html` — Grouped bars: in-sample (green) vs out-of-sample (orange)
- [ ] `output/wf_degradation.html` — Bar chart comparing strategy robustness
- [ ] Degradation ratios printed in terminal (closer to 1.0 = more robust, < 0.3 = likely overfit)

## 6. Bias Guards

```python
from backtest.bias_guards import (
    benchmark_buy_and_hold,
    benchmark_random,
    parameter_stability_test,
    detect_lookahead_bias,
)
from visualization.walk_forward import plot_parameter_sensitivity
from visualization.charts import save_figure

data = get_data("AMZN")

# Buy-and-hold benchmark — can our strategies beat this?
bh = benchmark_buy_and_hold(data)
print("Buy & Hold:", bh)

# Random baseline — can our strategies beat coin flips?
rand = benchmark_random(data, n_simulations=100)
print("Random:", rand)

# Lookahead bias check — should pass for all strategies
for s in [MovingAverageCrossover(), RSIStrategy(), BollingerBandsStrategy()]:
    result = detect_lookahead_bias(s, data)
    print(f"{s.name}: {'PASS' if result['passed'] else 'FAIL'} — {result['message']}")

# Parameter sensitivity — check if MA crossover is robust
stability = parameter_stability_test(
    MovingAverageCrossover(), data,
    param_ranges={"fast_period": [10, 15, 20, 25, 30], "slow_period": [40, 50, 60, 70]},
)
print(stability[["fast_period", "slow_period", "Sharpe Ratio", "Total Return (%)"]].to_string())

fig = plot_parameter_sensitivity(stability, x_param="fast_period", y_param="slow_period")
save_figure(fig, "param_sensitivity_ma")
```

**Visual validations:**
- [ ] All three strategies pass the lookahead bias check
- [ ] `output/param_sensitivity_ma.html` — Heatmap with Sharpe ratios. Gradual color transitions = robust; patchy/random colors = fragile
- [ ] Compare strategy returns vs buy-and-hold and random baselines in terminal output

## 7. Walk-Forward with Parameter Optimization

```python
from backtest.walk_forward import WalkForwardEngine
from strategies import MovingAverageCrossover
from visualization.walk_forward import plot_in_vs_out_sample
from visualization.charts import save_figure

data = get_data("AMZN")

engine = WalkForwardEngine(n_splits=4, gap_days=5)
result = engine.run(
    MovingAverageCrossover(),
    data,
    param_grid={"fast_period": [10, 15, 20, 25], "slow_period": [40, 50, 60]},
)

print(result.summary())
for fold in result.folds:
    print(f"  Fold {fold.fold_index}: best params = {fold.best_params}")

fig = plot_in_vs_out_sample(result)
save_figure(fig, "wf_optimized_ma")
```

**Visual validations:**
- [ ] Each fold may select different "best" parameters
- [ ] Degradation ratio with optimization should ideally be similar to without (if not, optimization is overfitting)

---

## Quick Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Make sure you activated the venv and ran `pip install -r requirements.txt` |
| `No data returned for TICKER` | Check internet connection; try `--ticker MSFT` as a known-good ticker |
| yfinance rate limit | Data is cached after first download; delete `data/cache/` to force re-download |
| Charts not opening | HTML files are in `output/` — open them manually in a browser |
| Tests fail on import | Run from the project root directory (`algo-cus/`) |
| Dashboard won't start | Check that `SKIP_AUTH=1` is set for local dev |
| Dashboard shows blank page | Open browser console for errors; check terminal for Python tracebacks |
| "SUPABASE_URL required" error | Set `SKIP_AUTH=1` to bypass auth locally |

## File Outputs Checklist

After running everything above, your `output/` directory should contain:

```
output/
  coverage/index.html              # Coverage report
  Synthetic_candlestick.html       # From step 4
  Synthetic_*_signals.html         # Signal charts (3 files)
  Synthetic_portfolio_comparison.html
  Synthetic_metrics.html
  AMZN_candlestick.html            # From step 4
  AMZN_*_signals.html
  AMZN_portfolio_comparison.html
  AMZN_metrics.html
  wf_splits.html                   # From step 5
  wf_*.html                        # Walk-forward charts
  wf_degradation.html
  param_sensitivity_ma.html        # From step 6
  wf_optimized_ma.html             # From step 7
```
