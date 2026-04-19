#!/usr/bin/env python3
"""
Analyze Azure Reserved Instance (RI) recommendations.

Shows RI purchase recommendations with projected savings from the EA data.

Usage:
    python analyze_ri_recommendations.py [--term P1Y|P3Y] [--data-dir PATH]
"""

import argparse
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("Error: pandas is required. Install with: pip install pandas", file=sys.stderr)
    sys.exit(1)


def analyze_ri(data_dir: str, term: str = None):
    csv_path = Path(data_dir) / "EA-Reservations-Recommendations.csv"
    if not csv_path.exists():
        print(f"Error: RI Recommendations CSV not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("AZURE RESERVED INSTANCE RECOMMENDATIONS")
    print("=" * 80)

    df = pd.read_csv(str(csv_path))

    if term:
        df = df[df["Term"] == term]
        print(f"Filter: {term} term only")

    if df.empty:
        print("No RI recommendations found.")
        return

    print(f"Total recommendations: {len(df)}\n")

    total_savings = 0
    total_on_demand = 0
    total_reserved = 0

    for _, row in df.iterrows():
        sku = row.get("SKU", "Unknown")
        location = row.get("Location", "Unknown")
        on_demand = float(row.get("CostWithNoReservedInstances", 0))
        reserved = float(row.get("TotalCostWithReservedInstances", 0))
        savings = float(row.get("NetSavings", 0))
        qty = row.get("RecommendedQuantity", 0)
        res_type = row.get("ResourceType", "unknown")
        lookback = row.get("LookBackPeriod", "Unknown")
        r_term = row.get("Term", "Unknown")

        total_savings += savings
        total_on_demand += on_demand
        total_reserved += reserved

        savings_pct = (savings / on_demand * 100) if on_demand > 0 else 0

        print(f"  >> {sku} ({location})")
        print(f"     Type: {res_type} | Term: {r_term} | Lookback: {lookback}")
        print(f"     Recommended Qty: {qty}")
        print(f"     On-Demand Cost:  ${on_demand:,.2f}")
        print(f"     Reserved Cost:   ${reserved:,.2f}")
        print(f"     Net Savings:     ${savings:,.2f} ({savings_pct:.1f}%)")
        print()

    print("=" * 80)
    print("SUMMARY")
    print(f"  Total On-Demand Cost:    ${total_on_demand:,.2f}")
    print(f"  Total Reserved Cost:     ${total_reserved:,.2f}")
    print(f"  Total Potential Savings: ${total_savings:,.2f}")
    if total_on_demand > 0:
        print(f"  Overall Savings Rate:   {total_savings/total_on_demand*100:.1f}%")

    print(f"\nRECOMMENDATIONS:")
    print(f"  1. Prioritize RIs with highest absolute savings")
    print(f"  2. Start with 1-year terms for flexibility, then move to 3-year")
    print(f"  3. Review instance flexibility groups for coverage optimization")
    print(f"  4. Monitor utilization after purchase with reservation_utilization")


def main():
    parser = argparse.ArgumentParser(description='Analyze Azure RI recommendations')
    parser.add_argument('--term', choices=['P1Y', 'P3Y'],
                        help='Filter by reservation term')
    parser.add_argument('--data-dir', default=str(Path(__file__).resolve().parent.parent.parent.parent.parent / "data"),
                        help='Path to data directory')
    parser.add_argument('--profile', help='(Ignored)')
    args = parser.parse_args()

    try:
        analyze_ri(data_dir=args.data_dir, term=args.term)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
