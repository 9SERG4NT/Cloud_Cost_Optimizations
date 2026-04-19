"""
Quick verification script for MCP tools and Azure CSV tool.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test 1: Tool registration
print("=" * 50)
print("TEST 1: MCP Tool Registration")
print("=" * 50)

from backend.mcp_tools import get_tool_schemas, execute_tool

schemas = get_tool_schemas()
print(f"  Registered {len(schemas)} MCP tools:")
for t in schemas:
    fn = t["function"]
    params = fn["parameters"]["properties"]
    print(f"    - {fn['name']}: {len(params)} params ({', '.join(params.keys())})")

assert len(schemas) == 9, f"Expected 9 tools, got {len(schemas)}"
print("  PASS: All 9 tools registered.\n")


# Test 2: Azure CSV tool execution
print("=" * 50)
print("TEST 2: Azure CSV Tool Execution")
print("=" * 50)

result = execute_tool("query_azure_billing", {"account_id": "ACC-001"})
print(f"  Result preview:\n{result[:500]}")

assert "ACC-001" not in result or "$" in result, "Expected dollar amounts in output"
assert "Error" not in result, f"Tool returned error: {result}"
print("  PASS: Azure CSV tool returned valid results.\n")


# Test 3: Azure CSV tool with filters
print("=" * 50)
print("TEST 3: Azure CSV Tool - Filtered Query")
print("=" * 50)

result2 = execute_tool("query_azure_billing", {
    "account_id": "ACC-002",
    "group_by": "ServiceName",
})
print(f"  Result preview:\n{result2[:500]}")
assert "Error" not in result2, f"Tool returned error: {result2}"
print("  PASS: Filtered query works.\n")


# Test 4: Azure CSV tool - empty result
print("=" * 50)
print("TEST 4: Azure CSV Tool - No Match")
print("=" * 50)

result3 = execute_tool("query_azure_billing", {"account_id": "ACC-999"})
print(f"  Result: {result3}")
assert "No Azure billing records" in result3, "Expected no-match message"
print("  PASS: No-match returns clean message.\n")


# Test 5: Tool schemas are valid for Ollama
print("=" * 50)
print("TEST 5: Schema Validation for Ollama")
print("=" * 50)

for t in schemas:
    assert t["type"] == "function", f"Expected type 'function', got {t['type']}"
    fn = t["function"]
    assert "name" in fn, "Missing 'name' in function schema"
    assert "description" in fn, "Missing 'description' in function schema"
    assert "parameters" in fn, "Missing 'parameters' in function schema"
    assert fn["parameters"]["type"] == "object", "Parameters should be type 'object'"
    print(f"    {fn['name']}: valid")

print("  PASS: All schemas valid for Ollama.\n")


# Test 6: FinOps Knowledge Base Tool
print("=" * 50)
print("TEST 6: FinOps Knowledge Base Tool")
print("=" * 50)

result4 = execute_tool("query_finops_knowledge", {"topic": "best_practices", "query": "rightsizing"})
print(f"  Result preview (first 300 chars):\n{result4[:300]}")
assert "Error" not in result4, f"Tool returned error: {result4}"
assert len(result4) > 100, "Expected substantial content from knowledge base"
print("  PASS: Knowledge base returned relevant content.\n")

# Test keyword search across all topics
result5 = execute_tool("query_finops_knowledge", {"query": "tagging"})
print(f"  Cross-topic search preview (first 300 chars):\n{result5[:300]}")
assert "Error" not in result5, f"Tool returned error: {result5}"
print("  PASS: Cross-topic keyword search works.\n")


# Test 7: Report Template Tool
print("=" * 50)
print("TEST 7: Report Template Tool")
print("=" * 50)

result6 = execute_tool("get_report_template", {"template_name": "monthly_cost_report"})
print(f"  Template preview (first 300 chars):\n{result6[:300]}")
assert "Error" not in result6, f"Tool returned error: {result6}"
assert "Executive Summary" in result6, "Expected 'Executive Summary' in template"
assert "Cost Breakdown" in result6, "Expected 'Cost Breakdown' in template"
print("  PASS: Report template returned successfully.\n")

# Test invalid template name
result7 = execute_tool("get_report_template", {"template_name": "nonexistent"})
print(f"  Invalid template result: {result7}")
assert "Error" in result7 or "not found" in result7, "Expected error for invalid template"
print("  PASS: Invalid template returns clean error.\n")


print("=" * 50)
print("ALL TESTS PASSED")
print("=" * 50)
