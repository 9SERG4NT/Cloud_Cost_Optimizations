const TOOL_LABELS = {
  analyzing_query: 'Analyzing Query',
  get_aws_cost_data: 'Fetching AWS Costs',
  get_azure_cost_data: 'Fetching Azure Costs',
  find_unused_resources: 'Scanning Resources',
  rightsizing_analysis: 'Rightsizing Analysis',
  detect_anomalies: 'Detecting Anomalies',
  generate_report: 'Generating Report',
};

export default function ToolBadge({ toolName, isComplete }) {
  const label = TOOL_LABELS[toolName] || toolName?.replace(/_/g, ' ') || 'Running tool';

  return (
    <span className={`tool-badge ${isComplete ? 'complete' : ''}`}>
      {isComplete ? (
        <span>✓</span>
      ) : (
        <span className="spinner" />
      )}
      {isComplete ? `✓ ${label}` : label}
    </span>
  );
}
