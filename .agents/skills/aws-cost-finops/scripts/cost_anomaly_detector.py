#!/usr/bin/env python3
"""
Detect cost anomalies and unusual spending patterns in Azure enterprise billing data.

This script analyzes the FOCUS 1.0 billing CSV to find:
- Services with spending significantly above average
- Accounts with unusual cost spikes
- Top 10 most expensive resources

Usage:
    python cost_anomaly_detector.py [--threshold MULTIPLIER] [--data-dir PATH]

No AWS credentials required — reads local CSV data.
"""

import argparse
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("Error: pandas is required. Install with: pip install pandas", file=sys.stderr)
    sys.exit(1)


def detect_anomalies(data_dir: str, threshold: float = 1.5):
    """Detect cost anomalies in FOCUS billing data."""
    csv_path = Path(data_dir) / "EA-Cost-FOCUS_1.0.csv"
    if not csv_path.exists():
        print(f"Error: FOCUS CSV not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("AZURE COST ANOMALY DETECTION REPORT")
    print("=" * 80)
    print(f"Loading data from: {csv_path.name}")

    df = pd.read_csv(str(csv_path), low_memory=False)
    df["EffectiveCost"] = pd.to_numeric(df["EffectiveCost"], errors="coerce").fillna(0)

    print(f"Dataset: {len(df):,} billing line items")
    print(f"Anomaly threshold: {threshold}x average")

    # -- Service-level anomalies --
    svc_costs = df.groupby("ServiceName")["EffectiveCost"].sum().sort_values(ascending=False)
    avg_cost = svc_costs.mean()

    anomalies = svc_costs[svc_costs > avg_cost * threshold]
    print(f"\n[1/4] SERVICE-LEVEL ANOMALIES (>{threshold}x avg of ${avg_cost:,.2f}):")
    print("-" * 80)
    for svc, cost in anomalies.items():
        ratio = cost / avg_cost if avg_cost > 0 else 0
        severity = "HIGH" if ratio > 5 else "MEDIUM"
        print(f"  [{severity}] {svc}: ${cost:,.2f} ({ratio:.1f}x average)")

    if anomalies.empty:
        print("  No service-level anomalies detected.")

    # -- Account-level anomalies --
    acct_costs = df.groupby("SubAccountName")["EffectiveCost"].sum().sort_values(ascending=False)
    avg_acct = acct_costs.mean()
    acct_anomalies = acct_costs[acct_costs > avg_acct * threshold]

    print(f"\n[2/4] ACCOUNT-LEVEL ANOMALIES (>{threshold}x avg of ${avg_acct:,.2f}):")
    print("-" * 80)
    for acct, cost in acct_anomalies.items():
        ratio = cost / avg_acct if avg_acct > 0 else 0
        print(f"  [!] {acct}: ${cost:,.2f} ({ratio:.1f}x average)")

    if acct_anomalies.empty:
        print("  No account-level anomalies detected.")

    # -- Top 10 most expensive resources --
    if "ResourceName" in df.columns:
        resource_costs = df.groupby("ResourceName")["EffectiveCost"].sum().sort_values(ascending=False).head(10)
        print(f"\n[3/4] TOP 10 MOST EXPENSIVE RESOURCES:")
        print("-" * 80)
        for res, cost in resource_costs.items():
            if res and str(res) != "nan":
                print(f"  {res}: ${cost:,.2f}")

    # -- Service category breakdown --
    if "ServiceCategory" in df.columns:
        cat_costs = df.groupby("ServiceCategory")["EffectiveCost"].sum().sort_values(ascending=False).head(10)
        print(f"\n[4/4] COST BY SERVICE CATEGORY:")
        print("-" * 80)
        total = df["EffectiveCost"].sum()
        for cat, cost in cat_costs.items():
            pct = (cost / total * 100) if total > 0 else 0
            print(f"  {cat}: ${cost:,.2f} ({pct:.1f}%)")

    # -- Summary --
    total = df["EffectiveCost"].sum()
    print(f"\n{'=' * 80}")
    print(f"SUMMARY")
    print(f"  Total Spend: ${total:,.2f}")
    print(f"  Services analyzed: {len(svc_costs)}")
    print(f"  Accounts analyzed: {len(acct_costs)}")
    print(f"  Service anomalies: {len(anomalies)}")
    print(f"  Account anomalies: {len(acct_anomalies)}")

    print(f"\nRECOMMENDED ACTIONS:")
    print(f"  1. Investigate HIGH severity anomalies immediately")
    print(f"  2. Review top cost drivers for optimization opportunities")
    print(f"  3. Set up Azure Cost Management alerts for anomaly detection")
    print(f"  4. Implement resource tagging for better cost attribution")
    print(f"  5. Run rightsizing_analyzer.py for specific resource recommendations")


def main():
    parser = argparse.ArgumentParser(
        description='Detect Azure cost anomalies from FOCUS billing data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default analysis (1.5x threshold)
  python cost_anomaly_detector.py

  # Stricter threshold (2x = 100% above average)
  python cost_anomaly_detector.py --threshold 2.0

  # Specify data directory
  python cost_anomaly_detector.py --data-dir ./data
        """
    )

    parser.add_argument('--threshold', type=float, default=1.5,
                        help='Anomaly threshold multiplier (default: 1.5 = 50%% above average)')
    parser.add_argument('--data-dir', default=str(Path(__file__).resolve().parent.parent.parent.parent.parent / "data"),
                        help='Path to data directory containing CSV files')
    # Keep --profile for backward compatibility but ignore it
    parser.add_argument('--profile', help='(Ignored - no AWS credentials needed)')

    args = parser.parse_args()

    try:
        detect_anomalies(data_dir=args.data_dir, threshold=args.threshold)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
