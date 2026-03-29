"""
JSON round-trip logic for dcc.Store.

Dash stores must hold JSON-serializable data, so DataFrames are
serialized as JSON strings and WalkForwardResult objects become
lightweight proxy dicts. This module handles both directions.
"""

import io

import pandas as pd


class WFProxy:
    """Lightweight stand-in for WalkForwardResult after JSON round-trip."""

    def __init__(self, d):
        self.strategy_name = d["strategy_name"]
        self.degradation_ratio = d["degradation_ratio"]
        self.folds = [type("Fold", (), {
            "fold_index": f["fold_index"],
            "in_sample_metrics": f["is_metrics"],
            "out_of_sample_metrics": f["oos_metrics"],
        })() for f in d["folds"]]


def serialize_analysis(result: dict) -> dict:
    """Convert analysis output into a JSON-safe dict for dcc.Store."""
    store_data = {
        "ticker": result["ticker"],
        "elapsed": result["elapsed"],
        "data_json": result["data"].to_json(date_format="iso"),
        "strategies": [],
        "buy_hold": result["buy_hold"],
        "walk_forward": [],
        "wf_splits_info": result["wf_splits_info"],
    }

    for sr in result["strategies"]:
        store_data["strategies"].append({
            "name": sr["name"],
            "signals_json": sr["signals_df"].to_json(date_format="iso"),
            "results_json": sr["backtest_results"].to_json(date_format="iso"),
            "metrics": sr["metrics"],
        })

    for wf in result["walk_forward"]:
        store_data["walk_forward"].append({
            "strategy_name": wf.strategy_name,
            "degradation_ratio": wf.degradation_ratio,
            "folds": [
                {
                    "fold_index": f.fold_index,
                    "is_metrics": f.in_sample_metrics,
                    "oos_metrics": f.out_of_sample_metrics,
                }
                for f in wf.folds
            ],
        })

    return store_data


def deserialize_store(store_data: dict) -> dict:
    """Reconstruct DataFrames and WF proxies from stored JSON."""
    data = pd.read_json(io.StringIO(store_data["data_json"]))
    data = data.sort_values("Date").reset_index(drop=True)

    result = {
        "ticker": store_data["ticker"],
        "data": data,
        "buy_hold": store_data["buy_hold"],
        "strategies": [],
        "walk_forward": [],
    }

    for sr in store_data["strategies"]:
        signals_df = pd.read_json(io.StringIO(sr["signals_json"])).sort_values("Date").reset_index(drop=True)
        results_df = pd.read_json(io.StringIO(sr["results_json"])).sort_values("Date").reset_index(drop=True)
        result["strategies"].append({
            "name": sr["name"],
            "signals_df": signals_df,
            "backtest_results": results_df,
            "metrics": sr["metrics"],
        })

    result["walk_forward"] = [WFProxy(wf) for wf in store_data["walk_forward"]]
    return result
