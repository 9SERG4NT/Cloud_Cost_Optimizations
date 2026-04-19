#!/usr/bin/env python3
"""
Analyze Azure resources for rightsizing opportunities.

Identifies the most expensive resources within each service and flags cost outliers.

Usage:
    python rightsizing_analyzer.py [--service SERVICE_NAME] [--data-dir PATH]
"""

import argparse
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("Error: pandas is required. Install with: pip install pandas", file=sys.stderr)
    sys.exit(1)


def analyze_rightsizing(data_dir: str, service_name: str = None):
    csv_path = Path(data_dir) / "EA-Cost-FOCUS_1.0.csv"
    if not csv_path.exists():
        print(f"Error: FOCUS CSV not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("AZURE RIGHTSIZING ANALYSIS REPORT")
    print("=" * 80)

    df = pd.read_csv(str(csv_path), low_memory=False)
    df["EffectiveCost"] = pd.to_numeric(df["EffectiveCost"], errors="coerce").fillna(0)

    if service_name:
        df = df[df["ServiceName"].str.lower().str.contains(service_name.lower())]
        if df.empty:
            print(f"No data found for service '{service_name}'")
            return
        print(f"Filter: {service_name}")

    print(f"Dataset: {len(df):,} line items\n")

    svc_groups = df.groupby("ServiceName")
    step = 0

    for svc_name, svc_df in sorted(svc_groups, key=lambda x: x[1]["EffectiveCost"].sum(), reverse=True)[:8]:
        svc_total = svc_df["EffectiveCost"].sum()
        if svc_total < 1.0:
            continue

        step += 1
        print(f"\n[{step}] SERVICE: {svc_name} (Total: ${svc_total:,.2f})")
        print("-" * 80)

        if "ResourceName" in svc_df.columns:
            res_costs = svc_df.groupby("ResourceName")["EffectiveCost"].sum().sort_values(ascending=False)
            avg_res_cost = res_costs.mean()

            print(f"  Average resource cost: ${avg_res_cost:,.2f}")
            print(f"  Top resources:")
            for res, cost in res_costs.head(5).items():
                if res and str(res) != "nan":
                    flag = " ** OUTLIER **" if cost > avg_res_cost * 2 else ""
                    print(f"    * {res}: ${cost:,.2f}{flag}")

        if "ResourceType" in svc_df.columns:
            type_costs = svc_df.groupby("ResourceType")["EffectiveCost"].sum().sort_values(ascending=False).head(5)
            print(f"  Resource types:")
            for rtype, cost in type_costs.items():
                if rtype and str(rtype) != "nan":
                    print(f"    * {rtype}: ${cost:,.2f}")

    print(f"\n{'=' * 80}")
    print("RECOMMENDATIONS:")
    print("  1. Resources flagged as OUTLIER cost >2x the service average")
    print("  2. Consider downgrading SKU tiers for outlier resources")
    print("  3. Use Azure Advisor for specific rightsizing recommendations")
    print("  4. Review premium SKUs - are they justified by workload?")


def main():
    parser = argparse.ArgumentParser(description='Azure rightsizing analysis')
    parser.add_argument('--service', help='Filter to specific Azure service name')
    parser.add_argument('--data-dir', default=str(Path(__file__).resolve().parent.parent.parent.parent.parent / "data"),
                        help='Path to data directory')
    parser.add_argument('--profile', help='(Ignored)')
    args = parser.parse_args()

    try:
        analyze_rightsizing(data_dir=args.data_dir, service_name=args.service)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
