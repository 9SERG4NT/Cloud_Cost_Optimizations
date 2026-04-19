#!/usr/bin/env python3
"""
Find unused or idle Azure resources from FOCUS billing data.

Identifies resources with near-zero cost that may be provisioned but unused.

Usage:
    python find_unused_resources.py [--cost-threshold AMOUNT] [--data-dir PATH]
"""

import argparse
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("Error: pandas is required. Install with: pip install pandas", file=sys.stderr)
    sys.exit(1)


def find_unused(data_dir: str, cost_threshold: float = 0.01):
    csv_path = Path(data_dir) / "EA-Cost-FOCUS_1.0.csv"
    if not csv_path.exists():
        print(f"Error: FOCUS CSV not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("AZURE UNUSED/IDLE RESOURCE REPORT")
    print("=" * 80)

    df = pd.read_csv(str(csv_path), low_memory=False)
    df["EffectiveCost"] = pd.to_numeric(df["EffectiveCost"], errors="coerce").fillna(0)

    print(f"Dataset: {len(df):,} line items")
    print(f"Cost threshold: ${cost_threshold}")

    # Find resources with near-zero cost
    if "ResourceName" in df.columns:
        resource_costs = df.groupby(["ResourceName", "ServiceName", "SubAccountName"])["EffectiveCost"].sum()
        idle = resource_costs[
            (resource_costs >= 0) & (resource_costs <= cost_threshold)
        ].sort_values()

        print(f"\n[1/3] IDLE RESOURCES (cost <= ${cost_threshold}):")
        print("-" * 80)
        count = 0
        for (res, svc, acct), cost in idle.items():
            if res and str(res) != "nan":
                print(f"  * {res}")
                print(f"    Service: {svc} | Account: {acct} | Cost: ${cost:.4f}")
                count += 1
                if count >= 50:
                    print(f"  ... and {len(idle) - 50} more idle resources")
                    break

        print(f"\nTotal idle resources: {count}")

    # Zero-consumption items
    if "ConsumedQuantity" in df.columns:
        df["ConsumedQuantity"] = pd.to_numeric(df["ConsumedQuantity"], errors="coerce").fillna(0)
        zero = df[df["ConsumedQuantity"] == 0]
        zero_by_svc = zero.groupby("ServiceName").size().sort_values(ascending=False).head(10)

        print(f"\n[2/3] ZERO-CONSUMPTION LINE ITEMS BY SERVICE:")
        print("-" * 80)
        for svc, cnt in zero_by_svc.items():
            print(f"  {svc}: {cnt} line items")

    # Cost by service for context
    svc_costs = df.groupby("ServiceName")["EffectiveCost"].sum().sort_values(ascending=False).head(10)
    total = df["EffectiveCost"].sum()

    print(f"\n[3/3] TOP SERVICES (for context):")
    print("-" * 80)
    for svc, cost in svc_costs.items():
        pct = (cost / total * 100) if total > 0 else 0
        print(f"  {svc}: ${cost:,.2f} ({pct:.1f}%)")

    print(f"\n{'=' * 80}")
    print("RECOMMENDATIONS:")
    print("  1. Review idle resources - delete if truly unused")
    print("  2. Check zero-consumption items for orphaned provisioned resources")
    print("  3. Use Azure Advisor for automated idle resource detection")
    print("  4. Set up Azure Policy to auto-tag resource lifecycle")


def main():
    parser = argparse.ArgumentParser(description='Find unused Azure resources')
    parser.add_argument('--cost-threshold', type=float, default=0.01,
                        help='Maximum cost to consider idle (default: $0.01)')
    parser.add_argument('--data-dir', default=str(Path(__file__).resolve().parent.parent.parent.parent.parent / "data"),
                        help='Path to data directory')
    parser.add_argument('--profile', help='(Ignored)')
    args = parser.parse_args()

    try:
        find_unused(data_dir=args.data_dir, cost_threshold=args.cost_threshold)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
