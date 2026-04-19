#!/usr/bin/env python3
"""
Detect old-generation Azure SKUs that could be migrated to newer, cheaper options.

Scans billing data for known old-gen VM SKU patterns.

Usage:
    python detect_old_generations.py [--data-dir PATH]
"""

import argparse
import sys
import re
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("Error: pandas is required. Install with: pip install pandas", file=sys.stderr)
    sys.exit(1)

# Known old-gen patterns and their newer alternatives
OLD_GEN_PATTERNS = {
    r"Standard_D\d+_v2": "Dv2 -> Consider Dv5 or Ddsv5 series",
    r"Standard_D\d+_v3": "Dv3 -> Consider Dv5 or Ddsv5 series",
    r"Standard_D\d+s_v3": "Dsv3 -> Consider Dsv5 or Ddsv5 series",
    r"Standard_E\d+_v2": "Ev2 -> Consider Ev5 or Edsv5 series",
    r"Standard_E\d+_v3": "Ev3 -> Consider Ev5 or Edsv5 series",
    r"Standard_F\d+s": "Fs -> Consider Fsv2 series",
    r"Standard_A\d+": "A-series -> Consider B-series or Dv5 series",
    r"Standard_D\d+$": "D-series (original) -> Consider Dv5 series",
    r"Standard_DS\d+": "DS-series -> Consider Dsv5 series",
    r"Standard_D11_v2": "D11_v2 -> Consider Dv5 memory-optimized",
    r"Standard_B\d+s$": "Bs -> Consider B2ts_v2 or Bsv2 series",
}


def detect_old_gens(data_dir: str):
    csv_path = Path(data_dir) / "EA-Cost-FOCUS_1.0.csv"
    if not csv_path.exists():
        print(f"Error: FOCUS CSV not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("AZURE OLD-GENERATION SKU DETECTION REPORT")
    print("=" * 80)

    df = pd.read_csv(str(csv_path), low_memory=False)
    df["EffectiveCost"] = pd.to_numeric(df["EffectiveCost"], errors="coerce").fillna(0)

    # Also check RI recommendations for old-gen SKUs
    ri_path = Path(data_dir) / "EA-Reservations-Recommendations.csv"
    ri_skus = set()
    if ri_path.exists():
        ri_df = pd.read_csv(str(ri_path))
        if "SKU" in ri_df.columns:
            ri_skus = set(ri_df["SKU"].dropna().unique())

    # Check ResourceName and x_SkuDescription columns for old-gen patterns
    all_skus = set()
    for col in ["ResourceName", "ResourceType"]:
        if col in df.columns:
            all_skus.update(df[col].dropna().unique())
    all_skus.update(ri_skus)

    print(f"Scanning {len(all_skus)} unique resource names/types...\n")

    found = []
    for sku in all_skus:
        sku_str = str(sku)
        for pattern, recommendation in OLD_GEN_PATTERNS.items():
            if re.search(pattern, sku_str):
                # Get cost for this resource if available
                cost = 0
                if "ResourceName" in df.columns:
                    mask = df["ResourceName"] == sku
                    cost = df.loc[mask, "EffectiveCost"].sum()
                found.append({
                    "sku": sku_str,
                    "recommendation": recommendation,
                    "cost": cost,
                })
                break

    if found:
        found.sort(key=lambda x: x["cost"], reverse=True)
        print("OLD-GENERATION RESOURCES DETECTED:")
        print("-" * 80)
        for item in found:
            cost_str = f" (${item['cost']:,.2f})" if item["cost"] > 0 else ""
            print(f"  [!] {item['sku']}{cost_str}")
            print(f"      {item['recommendation']}")
            print()
    else:
        print("No old-generation SKUs detected in the billing data.")

    print(f"\n{'=' * 80}")
    print(f"Total old-gen resources found: {len(found)}")
    print(f"\nRECOMMENDATIONS:")
    print(f"  1. Newer generations offer 20-40% better price-performance")
    print(f"  2. Plan migrations during maintenance windows")
    print(f"  3. Test workload compatibility before migrating")
    print(f"  4. Consider Azure Migrate for assessment and planning")


def main():
    parser = argparse.ArgumentParser(description='Detect old-generation Azure SKUs')
    parser.add_argument('--data-dir', default=str(Path(__file__).resolve().parent.parent.parent.parent.parent / "data"),
                        help='Path to data directory')
    parser.add_argument('--profile', help='(Ignored)')
    args = parser.parse_args()

    try:
        detect_old_gens(data_dir=args.data_dir)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
