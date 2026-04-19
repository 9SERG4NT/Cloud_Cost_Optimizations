import { useState, useEffect } from 'react';
import { listReports } from '../api';

const REPORT_PRESETS = [
  { icon: '📋', label: 'Monthly Report', desc: 'Executive summary + action items', prompt: 'Generate a professional monthly cloud cost optimization report. Include an executive summary, top 5 cost drivers, anomalies detected, rightsizing opportunities, RI savings potential, and a prioritized action plan.' },
  { icon: '🔍', label: 'Waste Audit', desc: 'All idle & unused resources', prompt: 'Run a comprehensive waste audit on all Azure accounts. List every idle and unused resource, estimate total monthly waste, and provide a step-by-step remediation plan.' },
  { icon: '📈', label: 'Anomaly Report', desc: 'Spike analysis & root cause', prompt: 'Generate an anomaly detection report for all Azure accounts. Identify all services spending more than 1.5x the average, analyze potential root causes, and recommend mitigations.' },
  { icon: '💡', label: 'RI Savings Report', desc: 'Reserved Instance analysis', prompt: 'Analyze all Azure Reserved Instance recommendations. Show a table of each RI opportunity with on-demand cost, reserved cost, net savings, and recommended action priority.' },
  { icon: '⚙️', label: 'Rightsizing Report', desc: 'Oversized resource analysis', prompt: 'Perform a full rightsizing analysis across all Azure services. Identify the top outlier resources by cost, recommend specific SKU changes, and estimate monthly savings.' },
  { icon: '💰', label: 'Account Breakdown', desc: 'Spend by account & service', prompt: 'Generate a detailed cost breakdown for all Azure EA accounts. Show spend by account, by service category, and by region. Identify the top 3 cost reduction opportunities per account.' },
];

export default function ReportsTab({ onSendMessage, onChangeTab }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await listReports();
        setReports(data.reports || []);
      } catch {
        setReports([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleGenerate = (prompt) => {
    onSendMessage(prompt);
    onChangeTab('analysis');
  };

  return (
    <div className="dashboard-page">
      <div className="page-header">
        <div className="page-header-title">
          <h1>Cost Reports</h1>
          <p>Generate AI-powered reports from your real Azure billing data</p>
        </div>
        <div className="page-header-actions">
          <button className="card-action-btn" onClick={() => handleGenerate(REPORT_PRESETS[0].prompt)}>
            ＋ Generate Monthly Report
          </button>
        </div>
      </div>

      {/* Report Presets */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <div className="card-title-icon">⚡</div>
            Generate a Report
          </div>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Click any template to generate via AI · Results appear in Analysis tab
          </span>
        </div>
        <div className="card-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
            {REPORT_PRESETS.map((r, i) => (
              <button
                key={i}
                className="welcome-prompt"
                onClick={() => handleGenerate(r.prompt)}
                style={{ textAlign: 'left' }}
              >
                <span className="icon">{r.icon}</span>
                <div className="label">{r.label}</div>
                <div className="desc">{r.desc}</div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Saved Reports */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <div className="card-title-icon">📂</div>
            Saved Reports
          </div>
        </div>
        <div className="card-body">
          {loading ? (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Loading…</div>
          ) : reports.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {reports.map((rep, i) => (
                <div
                  key={i}
                  style={{
                    padding: '14px 16px',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-md)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--text-primary)' }}>
                      📋 {rep.title}
                    </div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '3px' }}>
                      {rep.created_at ? new Date(rep.created_at).toLocaleString() : 'No date'}
                    </div>
                  </div>
                  <button
                    className="card-action-btn"
                    style={{ fontSize: '0.75rem' }}
                    onClick={() => {
                      onSendMessage(`Show me the saved report titled "${rep.title}"`);
                      onChangeTab('analysis');
                    }}
                  >
                    View →
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">📋</div>
              <p>No saved reports yet.<br />Generate a report above — it will appear here after saving.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
