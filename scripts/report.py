#!/usr/bin/env python
"""CLI reporting tool — run from desktop to query usage telemetry.

Usage:
    python scripts/report.py              # All reports
    python scripts/report.py active-users # Active users (7 days)
    python scripts/report.py tickers      # Most analyzed tickers
    python scripts/report.py interest     # Expressed interest
    python scripts/report.py logins       # Login frequency
"""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from dashboard.reporting import (
    get_active_users, get_top_tickers,
    get_expressed_interest, get_login_frequency,
)


def print_table(title, data, columns=None):
    """Print a list of dicts as a formatted table."""
    if data is None:
        print(f"\n{title}: No database connection\n")
        return
    if not data:
        print(f"\n{title}: No data\n")
        return
    if columns is None:
        columns = list(data[0].keys())
    widths = {c: max(len(c), max(len(str(row.get(c, ""))) for row in data))
              for c in columns}
    header = "  ".join(c.ljust(widths[c]) for c in columns)
    print(f"\n{title}")
    print("=" * len(header))
    print(header)
    print("-" * len(header))
    for row in data:
        print("  ".join(str(row.get(c, "")).ljust(widths[c]) for c in columns))
    print()


def main():
    report = sys.argv[1] if len(sys.argv) > 1 else "all"

    reports = {
        "active-users": ("Active Users (last 7 days)", get_active_users),
        "tickers": ("Top Tickers", get_top_tickers),
        "interest": ("Expressed Interest (unregistered attempts)", get_expressed_interest),
        "logins": ("Login Frequency", get_login_frequency),
    }

    if report == "all":
        for name, (title, fn) in reports.items():
            print_table(title, fn())
    elif report in reports:
        title, fn = reports[report]
        print_table(title, fn())
    else:
        print(f"Unknown report: {report}")
        print(f"Available: {', '.join(reports.keys())}, all")
        sys.exit(1)


if __name__ == "__main__":
    main()
