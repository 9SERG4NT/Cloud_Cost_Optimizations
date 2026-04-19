"""
MCP-style Tool Registry for the OmniCloud FinOps Agent.

Each tool is defined with:
  - name, description, parameters (JSON Schema)
  - An execute(**params) → str function

Tools (All Data-Driven — no AWS credentials needed):
  1: Cost Anomaly Detector (FOCUS CSV)
  2: Find Unused/Idle Resources (FOCUS CSV)
  3: Rightsizing Analyzer (FOCUS CSV)
  4: RI Recommendations (EA Reservations)
  5: Reservation Utilization (EA Reservations)
  6: Query Azure Billing (FOCUS CSV)
  7: FinOps Knowledge Base (Reference docs)
  8: Report Template (Markdown template)
"""

import json
import pandas as pd
from typing import Any
from pathlib import Path

from backend.config import (
    EA_FOCUS_CSV_PATH,
    EA_RI_RECS_CSV_PATH,
    EA_RI_DETAILS_CSV_PATH,
    EA_RI_TRANSACTIONS_CSV_PATH,
    REFERENCES_DIR,
    TEMPLATES_DIR,
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TOOLS: list[dict] = []
_EXECUTORS: dict[str, callable] = {}

# Cached DataFrames (loaded on first use to avoid slow startup)
_FOCUS_DF = None
_RI_RECS_DF = None
_RI_DETAILS_DF = None


def register_tool(name: str, description: str, parameters: dict):
    """Decorator to register a tool function."""
    def decorator(fn):
        TOOLS.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        })
        _EXECUTORS[name] = fn
        return fn
    return decorator


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a registered tool by name and return its text output."""
    fn = _EXECUTORS.get(name)
    if fn is None:
        return f"Error: Unknown tool '{name}'"
    try:
        return fn(**arguments)
    except Exception as exc:
        return f"Error executing tool '{name}': {exc}"


def get_tool_schemas() -> list[dict]:
    """Return the list of tool schemas for the LLM's tools parameter."""
    return TOOLS


# ---------------------------------------------------------------------------
# Lazy CSV Loaders
# ---------------------------------------------------------------------------

def _get_focus_df() -> pd.DataFrame:
    """Load the FOCUS billing CSV lazily."""
    global _FOCUS_DF
    if _FOCUS_DF is None:
        path = Path(EA_FOCUS_CSV_PATH)
        if not path.exists():
            raise FileNotFoundError(f"FOCUS CSV not found: {path}")
        _FOCUS_DF = pd.read_csv(str(path), low_memory=False)
        _FOCUS_DF["EffectiveCost"] = pd.to_numeric(_FOCUS_DF["EffectiveCost"], errors="coerce").fillna(0)
        _FOCUS_DF["BilledCost"] = pd.to_numeric(_FOCUS_DF["BilledCost"], errors="coerce").fillna(0)
    return _FOCUS_DF


def _get_ri_recs_df() -> pd.DataFrame:
    global _RI_RECS_DF
    if _RI_RECS_DF is None:
        path = Path(EA_RI_RECS_CSV_PATH)
        if not path.exists():
            raise FileNotFoundError(f"RI Recommendations CSV not found: {path}")
        _RI_RECS_DF = pd.read_csv(str(path))
    return _RI_RECS_DF


def _get_ri_details_df() -> pd.DataFrame:
    global _RI_DETAILS_DF
    if _RI_DETAILS_DF is None:
        path = Path(EA_RI_DETAILS_CSV_PATH)
        if not path.exists():
            raise FileNotFoundError(f"RI Details CSV not found: {path}")
        _RI_DETAILS_DF = pd.read_csv(str(path))
    return _RI_DETAILS_DF


# ---------------------------------------------------------------------------
# Tool 1: Cost Anomaly Detector
# ---------------------------------------------------------------------------

@register_tool(
    name="cost_anomaly_detector",
    description=(
        "Detect cost anomalies and unusual spending in the Azure enterprise billing data. "
        "Analyzes the FOCUS billing dataset to find services or accounts with spending that "
        "significantly exceeds the average. Identifies top cost drivers and spending outliers."
    ),
    parameters={
        "type": "object",
        "properties": {
            "threshold": {
                "type": "number",
                "description": "Anomaly threshold multiplier (default 1.5 = 50% above average triggers alert).",
            },
        },
        "required": [],
    },
)
def _cost_anomaly_detector(threshold: float = 1.5) -> str:
    df = _get_focus_df()

    lines = []
    lines.append("AZURE COST ANOMALY DETECTION REPORT")
    lines.append("=" * 60)
    lines.append(f"Dataset: {len(df):,} billing line items")
    lines.append(f"Anomaly threshold: {threshold}x average")
    lines.append("")

    # -- Service-level anomalies --
    svc_costs = df.groupby("ServiceName")["EffectiveCost"].sum().sort_values(ascending=False)
    avg_cost = svc_costs.mean()

    anomalies = svc_costs[svc_costs > avg_cost * threshold]
    lines.append(f"SERVICE-LEVEL ANOMALIES (>{threshold}x avg of ${avg_cost:,.2f}):")
    lines.append("-" * 60)
    for svc, cost in anomalies.items():
        ratio = cost / avg_cost if avg_cost > 0 else 0
        lines.append(f"  [!] {svc}: ${cost:,.2f} ({ratio:.1f}x average)")
    lines.append("")

    # -- Account-level anomalies --
    acct_costs = df.groupby("SubAccountName")["EffectiveCost"].sum().sort_values(ascending=False)
    avg_acct = acct_costs.mean()
    acct_anomalies = acct_costs[acct_costs > avg_acct * threshold]

    lines.append(f"ACCOUNT-LEVEL ANOMALIES (>{threshold}x avg of ${avg_acct:,.2f}):")
    lines.append("-" * 60)
    for acct, cost in acct_anomalies.items():
        ratio = cost / avg_acct if avg_acct > 0 else 0
        lines.append(f"  [!] {acct}: ${cost:,.2f} ({ratio:.1f}x average)")
    lines.append("")

    # -- Top 10 most expensive resources --
    if "ResourceName" in df.columns:
        resource_costs = df.groupby("ResourceName")["EffectiveCost"].sum().sort_values(ascending=False).head(10)
        lines.append("TOP 10 MOST EXPENSIVE RESOURCES:")
        lines.append("-" * 60)
        for res, cost in resource_costs.items():
            lines.append(f"  {res}: ${cost:,.2f}")
    lines.append("")

    # -- Summary --
    total = df["EffectiveCost"].sum()
    lines.append(f"TOTAL SPEND: ${total:,.2f}")
    lines.append(f"Services analyzed: {len(svc_costs)}")
    lines.append(f"Accounts analyzed: {len(acct_costs)}")
    lines.append(f"Service anomalies found: {len(anomalies)}")
    lines.append(f"Account anomalies found: {len(acct_anomalies)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 2: Find Unused/Idle Resources
# ---------------------------------------------------------------------------

@register_tool(
    name="find_unused_resources",
    description=(
        "Scan Azure billing data for potentially unused or idle resources. "
        "Finds resources with near-zero cost (< $0.01) that may be provisioned but unused. "
        "Also identifies resources with zero consumed quantity."
    ),
    parameters={
        "type": "object",
        "properties": {
            "cost_threshold": {
                "type": "number",
                "description": "Maximum cost to consider a resource 'idle' (default $0.01).",
            },
        },
        "required": [],
    },
)
def _find_unused_resources(cost_threshold: float = 0.01) -> str:
    df = _get_focus_df()

    lines = []
    lines.append("AZURE UNUSED/IDLE RESOURCE REPORT")
    lines.append("=" * 60)

    # Find resources with near-zero cost
    if "ResourceName" in df.columns:
        resource_costs = df.groupby(["ResourceName", "ServiceName", "SubAccountName"])["EffectiveCost"].sum()
        idle = resource_costs[
            (resource_costs >= 0) & (resource_costs <= cost_threshold) & (resource_costs.index.get_level_values(0) != "")
        ].sort_values()

        lines.append(f"\nIDLE RESOURCES (cost ≤ ${cost_threshold}):")
        lines.append("-" * 60)
        count = 0
        for (res, svc, acct), cost in idle.items():
            if res and str(res) != "nan":
                lines.append(f"  • {res}")
                lines.append(f"    Service: {svc} | Account: {acct} | Cost: ${cost:.4f}")
                count += 1
                if count >= 50:
                    lines.append(f"  ... and {len(idle) - 50} more")
                    break

        lines.append(f"\nTotal idle resources found: {count}")

    # Find zero-consumption resources
    if "ConsumedQuantity" in df.columns:
        df["ConsumedQuantity"] = pd.to_numeric(df["ConsumedQuantity"], errors="coerce").fillna(0)
        zero_consumption = df[df["ConsumedQuantity"] == 0]
        zero_by_svc = zero_consumption.groupby("ServiceName").size().sort_values(ascending=False).head(10)

        lines.append(f"\nZERO-CONSUMPTION LINE ITEMS BY SERVICE:")
        lines.append("-" * 60)
        for svc, cnt in zero_by_svc.items():
            lines.append(f"  {svc}: {cnt} line items")

    # Recommendations
    lines.append("\nRECOMMENDATIONS:")
    lines.append("-" * 60)
    lines.append("  1. Review idle resources — delete if truly unused")
    lines.append("  2. Check zero-consumption items for orphaned provisioned resources")
    lines.append("  3. Implement Azure Advisor recommendations for right-sizing")
    lines.append("  4. Set up Azure Policy to auto-tag and track resource lifecycle")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 3: Rightsizing Analyzer
# ---------------------------------------------------------------------------

@register_tool(
    name="rightsizing_analyzer",
    description=(
        "Analyze Azure resources for rightsizing opportunities. Identifies the most expensive "
        "resources within each service category and flags cost outliers that may be over-provisioned. "
        "Compares individual resource costs against service averages."
    ),
    parameters={
        "type": "object",
        "properties": {
            "service_name": {
                "type": "string",
                "description": "Filter to a specific Azure service (e.g. 'Virtual Machines'). Omit for all.",
            },
        },
        "required": [],
    },
)
def _rightsizing_analyzer(service_name: str = None) -> str:
    df = _get_focus_df()

    lines = []
    lines.append("AZURE RIGHTSIZING ANALYSIS REPORT")
    lines.append("=" * 60)

    work_df = df.copy()
    if service_name:
        work_df = work_df[work_df["ServiceName"].str.lower().str.contains(service_name.lower())]
        if work_df.empty:
            return f"No data found for service '{service_name}'. Available services: {', '.join(df['ServiceName'].unique()[:15])}"

    # Analyze top services
    svc_groups = work_df.groupby("ServiceName")

    for svc_name, svc_df in sorted(svc_groups, key=lambda x: x[1]["EffectiveCost"].sum(), reverse=True)[:8]:
        svc_total = svc_df["EffectiveCost"].sum()
        if svc_total < 1.0:
            continue

        lines.append(f"\n{'─' * 60}")
        lines.append(f"SERVICE: {svc_name} (Total: ${svc_total:,.2f})")
        lines.append(f"{'─' * 60}")

        if "ResourceName" in svc_df.columns:
            res_costs = svc_df.groupby("ResourceName")["EffectiveCost"].sum().sort_values(ascending=False)
            avg_res_cost = res_costs.mean()

            # Show top resources and flag outliers
            lines.append(f"  Average resource cost: ${avg_res_cost:,.2f}")
            lines.append(f"  Top resources:")
            for res, cost in res_costs.head(5).items():
                if res and str(res) != "nan":
                    flag = " ⚠️ OUTLIER" if cost > avg_res_cost * 2 else ""
                    lines.append(f"    • {res}: ${cost:,.2f}{flag}")

        # Show SKU/ResourceType distribution if available
        if "ResourceType" in svc_df.columns:
            type_costs = svc_df.groupby("ResourceType")["EffectiveCost"].sum().sort_values(ascending=False).head(5)
            lines.append(f"  Resource types:")
            for rtype, cost in type_costs.items():
                if rtype and str(rtype) != "nan":
                    lines.append(f"    • {rtype}: ${cost:,.2f}")

    lines.append(f"\n{'=' * 60}")
    lines.append("RECOMMENDATIONS:")
    lines.append("  1. Resources flagged as OUTLIER cost >2x the service average")
    lines.append("  2. Consider downgrading SKU tiers for outlier resources")
    lines.append("  3. Use Azure Advisor for specific rightsizing recommendations")
    lines.append("  4. Review if premium SKUs are justified by workload requirements")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 4: RI Recommendations
# ---------------------------------------------------------------------------

@register_tool(
    name="analyze_ri_recommendations",
    description=(
        "Analyze Azure Reserved Instance (RI) purchase recommendations from the enterprise data. "
        "Shows recommended reservations with projected net savings, comparing on-demand vs reserved pricing. "
        "Based on actual usage patterns from the EA billing data."
    ),
    parameters={
        "type": "object",
        "properties": {
            "term": {
                "type": "string",
                "description": "Filter by reservation term: 'P1Y' (1-year) or 'P3Y' (3-year).",
                "enum": ["P1Y", "P3Y"],
            },
        },
        "required": [],
    },
)
def _analyze_ri_recommendations(term: str = None) -> str:
    df = _get_ri_recs_df()

    lines = []
    lines.append("AZURE RESERVED INSTANCE RECOMMENDATIONS")
    lines.append("=" * 60)

    if term:
        df = df[df["Term"] == term]
        lines.append(f"Filter: {term} term only")

    if df.empty:
        return "No RI recommendations found for the specified criteria."

    lines.append(f"Total recommendations: {len(df)}")
    lines.append("")

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

        lines.append(f"  >> {sku} ({location})")
        lines.append(f"     Type: {res_type} | Term: {r_term} | Lookback: {lookback}")
        lines.append(f"     Recommended Qty: {qty}")
        lines.append(f"     On-Demand Cost:  ${on_demand:,.2f}")
        lines.append(f"     Reserved Cost:   ${reserved:,.2f}")
        lines.append(f"     Net Savings:     ${savings:,.2f} ({savings_pct:.1f}%)")
        lines.append("")

    lines.append("=" * 60)
    lines.append("SUMMARY")
    lines.append(f"  Total On-Demand Cost:  ${total_on_demand:,.2f}")
    lines.append(f"  Total Reserved Cost:   ${total_reserved:,.2f}")
    lines.append(f"  Total Potential Savings: ${total_savings:,.2f}")
    if total_on_demand > 0:
        lines.append(f"  Overall Savings Rate:  {total_savings/total_on_demand*100:.1f}%")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 5: Reservation Utilization
# ---------------------------------------------------------------------------

@register_tool(
    name="reservation_utilization",
    description=(
        "Analyze Azure Reserved Instance utilization rates. Shows how well current "
        "reservations are being used, identifying underutilized RIs that represent waste. "
        "Calculates utilization percentage for each reservation."
    ),
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
def _reservation_utilization() -> str:
    df = _get_ri_details_df()

    lines = []
    lines.append("AZURE RESERVATION UTILIZATION REPORT")
    lines.append("=" * 60)

    # Convert numeric columns
    df["ReservedHours"] = pd.to_numeric(df["ReservedHours"], errors="coerce").fillna(0)
    df["UsedHours"] = pd.to_numeric(df["UsedHours"], errors="coerce").fillna(0)

    # Group by ReservationId
    ri_groups = df.groupby("ReservationId").agg({
        "ReservedHours": "sum",
        "UsedHours": "sum",
    })
    ri_groups["Utilization"] = (ri_groups["UsedHours"] / ri_groups["ReservedHours"] * 100).fillna(0)
    ri_groups["WastedHours"] = ri_groups["ReservedHours"] - ri_groups["UsedHours"]

    lines.append(f"Total reservations tracked: {len(ri_groups)}")
    lines.append("")

    # Summary stats
    avg_util = ri_groups["Utilization"].mean()
    total_reserved = ri_groups["ReservedHours"].sum()
    total_used = ri_groups["UsedHours"].sum()
    total_wasted = ri_groups["WastedHours"].sum()

    lines.append("OVERALL METRICS:")
    lines.append("-" * 60)
    lines.append(f"  Average Utilization: {avg_util:.1f}%")
    lines.append(f"  Total Reserved Hours: {total_reserved:,.0f}")
    lines.append(f"  Total Used Hours:     {total_used:,.0f}")
    lines.append(f"  Total Wasted Hours:   {total_wasted:,.0f}")
    lines.append("")

    # Underutilized RIs (< 80%)
    underutilized = ri_groups[ri_groups["Utilization"] < 80].sort_values("Utilization")
    if not underutilized.empty:
        lines.append(f"UNDERUTILIZED RESERVATIONS (<80%):")
        lines.append("-" * 60)
        for ri_id, row in underutilized.iterrows():
            lines.append(f"  [!] {ri_id[:36]}...")
            lines.append(f"      Utilization: {row['Utilization']:.1f}% | Wasted: {row['WastedHours']:,.0f} hours")

    # Well-utilized RIs (>= 80%)
    well_utilized = ri_groups[ri_groups["Utilization"] >= 80]
    lines.append(f"\nWell-utilized reservations (≥80%): {len(well_utilized)}")

    lines.append("\nRECOMMENDATIONS:")
    lines.append("  1. Investigate underutilized RIs — workloads may have been decommissioned")
    lines.append("  2. Consider exchanging underutilized RIs for better-fitting SKUs")
    lines.append("  3. Target ≥90% utilization for optimal RI ROI")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 6: Query Azure Billing (flexible)
# ---------------------------------------------------------------------------

@register_tool(
    name="query_azure_billing",
    description=(
        "Query the Azure enterprise billing data (FOCUS 1.0 format, 135K+ line items). "
        "Filters and aggregates costs by account, service, region, or service category. "
        "Use this for any billing breakdown, cost summary, or spending analysis question."
    ),
    parameters={
        "type": "object",
        "properties": {
            "account_name": {
                "type": "string",
                "description": "Azure sub-account name to filter (e.g. 'Trey Research IT').",
            },
            "service_name": {
                "type": "string",
                "description": "Azure service name to filter (e.g. 'Virtual Machines', 'SQL Database').",
            },
            "service_category": {
                "type": "string",
                "description": "Service category to filter (e.g. 'Compute', 'Storage', 'Networking').",
            },
            "region": {
                "type": "string",
                "description": "Azure region to filter (e.g. 'East US', 'West Europe').",
            },
            "group_by": {
                "type": "string",
                "description": "Column to group results by.",
                "enum": ["ServiceName", "ServiceCategory", "RegionName", "SubAccountName", "ChargeCategory", "ResourceType"],
            },
            "top_n": {
                "type": "integer",
                "description": "Number of top results to return (default 15).",
            },
        },
        "required": [],
    },
)
def _query_azure_billing(
    account_name: str = None,
    service_name: str = None,
    service_category: str = None,
    region: str = None,
    group_by: str = None,
    top_n: int = 15,
) -> str:
    df = _get_focus_df()

    # Apply filters
    if account_name:
        df = df[df["SubAccountName"].str.lower().str.contains(account_name.lower(), na=False)]
    if service_name:
        df = df[df["ServiceName"].str.lower().str.contains(service_name.lower(), na=False)]
    if service_category:
        df = df[df["ServiceCategory"].str.lower().str.contains(service_category.lower(), na=False)]
    if region:
        df = df[df["RegionName"].str.lower().str.contains(region.lower(), na=False)]

    if df.empty:
        return "No billing records match the specified filters."

    lines = []
    lines.append(f"Azure Billing Query Results ({len(df):,} records)")
    lines.append("=" * 60)

    total = df["EffectiveCost"].sum()
    lines.append(f"Total Cost: ${total:,.2f}")
    lines.append("")

    # Group by the requested column (or default to ServiceName)
    gb_col = group_by if (group_by and group_by in df.columns) else "ServiceName"
    grouped = df.groupby(gb_col)["EffectiveCost"].sum().sort_values(ascending=False).head(top_n)

    lines.append(f"Breakdown by {gb_col}:")
    lines.append("-" * 50)
    for key, cost in grouped.items():
        pct = (cost / total * 100) if total > 0 else 0
        lines.append(f"  {key}: ${cost:,.2f} ({pct:.1f}%)")

    # Also show account breakdown if not already grouping by account
    if gb_col != "SubAccountName":
        acct_totals = df.groupby("SubAccountName")["EffectiveCost"].sum().sort_values(ascending=False).head(5)
        lines.append(f"\nTop Accounts:")
        lines.append("-" * 50)
        for acct, cost in acct_totals.items():
            pct = (cost / total * 100) if total > 0 else 0
            lines.append(f"  {acct}: ${cost:,.2f} ({pct:.1f}%)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 7: FinOps Knowledge Base
# ---------------------------------------------------------------------------

_KNOWLEDGE_TOPICS = {
    "best_practices": {
        "title": "AWS Cost Optimization Best Practices",
        "description": "Compute, storage, network, database & container optimization strategies",
        "file": REFERENCES_DIR / "best_practices.md",
    },
    "service_alternatives": {
        "title": "AWS Service Alternatives & Pricing",
        "description": "Cost-effective service selection: EC2 vs Lambda vs Fargate, S3 tiers, DB options, networking",
        "file": REFERENCES_DIR / "service_alternatives.md",
    },
    "finops_governance": {
        "title": "FinOps Governance Framework",
        "description": "Tagging, budgets, monthly reviews, roles, chargeback, KPIs & policies",
        "file": REFERENCES_DIR / "finops_governance.md",
    },
}


def _search_knowledge(topic: str = None, query: str = None) -> str:
    """Search reference docs by topic key and/or keyword query."""
    if topic and topic in _KNOWLEDGE_TOPICS:
        files_to_search = [_KNOWLEDGE_TOPICS[topic]]
    else:
        files_to_search = list(_KNOWLEDGE_TOPICS.values())

    results = []
    for entry in files_to_search:
        fpath = Path(entry["file"])
        if not fpath.exists():
            continue
        content = fpath.read_text(encoding="utf-8")

        if query:
            sections = []
            current_heading = ""
            current_body = []
            for line in content.split("\n"):
                if line.startswith("## "):
                    if current_heading and current_body:
                        sections.append((current_heading, "\n".join(current_body)))
                    current_heading = line
                    current_body = []
                else:
                    current_body.append(line)
            if current_heading and current_body:
                sections.append((current_heading, "\n".join(current_body)))

            query_lower = query.lower()
            matched = [
                f"{heading}\n{body}"
                for heading, body in sections
                if query_lower in heading.lower() or query_lower in body.lower()
            ]
            if matched:
                results.append(f"[DOC] {entry['title']}\n{'=' * 50}\n" + "\n---\n".join(matched[:3]))
        else:
            results.append(f"[DOC] {entry['title']}\n{'=' * 50}\n{content[:3000]}")

    if not results:
        return f"No knowledge base results found for query '{query or topic}'. Available topics: {', '.join(_KNOWLEDGE_TOPICS.keys())}"

    return "\n\n".join(results)


@register_tool(
    name="query_finops_knowledge",
    description=(
        "Search the FinOps knowledge base for best practices, optimization strategies, "
        "service alternatives, governance frameworks, tagging strategies, budget management, "
        "and cost optimization guidance. Use this for advisory and strategic questions."
    ),
    parameters={
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Specific topic to query. Options: best_practices, service_alternatives, finops_governance.",
                "enum": ["best_practices", "service_alternatives", "finops_governance"],
            },
            "query": {
                "type": "string",
                "description": "Keyword or phrase to search for (e.g. 'rightsizing', 'S3 storage classes', 'tagging strategy').",
            },
        },
        "required": [],
    },
)
def _query_finops_knowledge(topic: str = None, query: str = None) -> str:
    return _search_knowledge(topic=topic, query=query)


# ---------------------------------------------------------------------------
# Tool 8: Report Template
# ---------------------------------------------------------------------------

@register_tool(
    name="get_report_template",
    description=(
        "Retrieve the professional monthly cost optimization report template. "
        "Use this when the user asks to generate, create, or see a cost report template. "
        "Returns a structured markdown template with sections for executive summary, "
        "cost breakdown, anomalies, optimization activities, and action items."
    ),
    parameters={
        "type": "object",
        "properties": {
            "template_name": {
                "type": "string",
                "description": "Template name. Currently only 'monthly_cost_report' is available.",
                "enum": ["monthly_cost_report"],
            },
        },
        "required": [],
    },
)
def _get_report_template(template_name: str = "monthly_cost_report") -> str:
    template_file = TEMPLATES_DIR / f"{template_name}.md"
    if not template_file.exists():
        return f"Error: Template '{template_name}' not found. Available: monthly_cost_report"
    return template_file.read_text(encoding="utf-8")
