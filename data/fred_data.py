"""
FRED (Federal Reserve Economic Data) provider — stub for Phase 5.

Will provide macroeconomic data (yield curve, VIX, unemployment, etc.)
to enhance regime detection and recommendation confidence.
"""

import pandas as pd


class FREDProvider:
    """Fetches macroeconomic data from FRED. (Phase 5 implementation.)"""

    def fetch_series(self, series_id: str, start: str, end: str) -> pd.DataFrame:
        raise NotImplementedError("FRED integration is planned for Phase 5")

    def fetch_macro_dashboard(self, start: str, end: str) -> pd.DataFrame:
        raise NotImplementedError("FRED integration is planned for Phase 5")
