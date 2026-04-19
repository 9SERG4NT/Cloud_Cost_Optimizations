#!/usr/bin/env python3
"""
Spot instance / low-priority VM recommendations for Azure.

Analyzes VM workloads to identify candidates for Azure Spot VMs.

Usage:
    python spot_recommendations.py [--data-dir PATH]
"""

import argparse
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("Error: pandas is required. Install with: pip install pandas", file=sys.stderr)
    sys.exit(1)


def spot_recommendations(data_dir: str):
    csv_path = Path(data_dir) / "EA-Cost-FOCUS_1.0.csv"
    if not csv_path.exists():
        print(f"Error: FOCUS CSV not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("AZURE SPOT VM RECOMMENDATIONS")
    print("=" * 80)

    df = pd.read_csv(str(csv_path), low_memory=False)
    df["EffectiveCost"] = pd.to_numeric(df["EffectiveCost"], errors="coerce").fillna(0)

    # Filter to VM-related services
    vm_services = ["Virtual Machines", "Virtual Machine Scale Sets"]
    vm_df = df[df["ServiceName"].isin(vm_services)]

    if vm_df.empty:
        print("No Virtual Machine data found in billing data.")
        return

    print(f"VM line items: {len(vm_df):,}")

    # Analyze by account and resource
    total_vm_cost = vm_df["EffectiveCost"].sum()
    print(f"Total VM Spend: ${total_vm_cost:,.2f}\n")

    # Group by SubAccountName
    acct_costs = vm_df.groupby("SubAccountName")["EffectiveCost"].sum().sort_values(ascending=False)

    print("[1/3] VM COSTS BY ACCOUNT:")
    print("-" * 80)
    for acct, cost in acct_costs.items():
        pct = (cost / total_vm_cost * 100) if total_vm_cost > 0 else 0
        print(f"  {acct}: ${cost:,.2f} ({pct:.1f}%)")

    # Top VM resources
    if "ResourceName" in vm_df.columns:
        res_costs = vm_df.groupby(["ResourceName", "SubAccountName"])["EffectiveCost"].sum().sort_values(ascending=False).head(15)
        print(f"\n[2/3] TOP VM RESOURCES (Spot Candidates):")
        print("-" * 80)
        for (res, acct), cost in res_costs.items():
            if res and str(res) != "nan":
                # Estimate spot savings (Azure Spot typically saves 60-90%)
                spot_savings = cost * 0.70  # Conservative 70% estimate
                print(f"  {res} ({acct})")
                print(f"    Current: ${cost:,.2f} | Est. Spot Price: ${cost - spot_savings:,.2f} | Savings: ${spot_savings:,.2f}")

    # Region breakdown
    if "RegionName" in vm_df.columns:
        region_costs = vm_df.groupby("RegionName")["EffectiveCost"].sum().sort_values(ascending=False).head(5)
        print(f"\n[3/3] VM COSTS BY REGION:")
        print("-" * 80)
        for region, cost in region_costs.items():
            pct = (cost / total_vm_cost * 100) if total_vm_cost > 0 else 0
            print(f"  {region}: ${cost:,.2f} ({pct:.1f}%)")

    # Estimate total potential savings
    potential_savings = total_vm_cost * 0.70
    print(f"\n{'=' * 80}")
    print(f"SPOT VM SAVINGS ESTIMATE:")
    print(f"  Current VM spend:     ${total_vm_cost:,.2f}")
    print(f"  Est. Spot savings:    ${potential_savings:,.2f} (up to 70%)")
    print(f"  Est. cost with Spot:  ${total_vm_cost - potential_savings:,.2f}")

    print(f"\nRECOMMENDATIONS:")
    print(f"  1. Azure Spot VMs offer up to 90% discount vs on-demand")
    print(f"  2. Best for: batch processing, dev/test, CI/CD, stateless workloads")
    print(f"  3. NOT suitable for: production databases, stateful services")
    print(f"  4. Use VMSS with Spot priority for auto-scaling workloads")
    print(f"  5. Implement eviction handling for graceful interruptions")


def main():
    parser = argparse.ArgumentParser(description='Azure Spot VM recommendations')
    parser.add_argument('--data-dir', default=str(Path(__file__).resolve().parent.parent.parent.parent.parent / "data"),
                        help='Path to data directory')
    parser.add_argument('--profile', help='(Ignored)')
    args = parser.parse_args()

    try:
        spot_recommendations(data_dir=args.data_dir)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
