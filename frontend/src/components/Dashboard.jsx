import { useState, useEffect, useCallback } from 'react';
import { getDashboard } from '../api';

const SERVICE_ICONS = {
  'Virtual Machines': '🖥️',
  'SQL Database': '🗄️',
  'Azure SQL Database': '🗄️',
  'SQL Managed Instance': '🗄️',
  'Azure App Service': '🌐',
  'Storage': '📦',
  'Azure Storage': '📦',
  'Virtual Network': '🔗',
  'Azure Monitor': '📊',
  'Bandwidth': '🔄',
  'Azure DNS': '🌍',
  'Container Registry': '📦',
  'Kubernetes': '⚙️',
  'Azure Kubernetes Service': '⚙️',
};

const STATUS_PROMPT = {
  Idle: (r) => `Analyze idle ${r.type} resources in the account "${r.account}". Should they be stopped, rightsized, or terminated? Estimate monthly savings.`,
  Unused: (r) => `Find unused ${r.type} resources in the account "${r.account}" that have $0 cost. What is the monthly waste and how should they be cleaned up?`,
};

const QUICK_ACTIONS = [
  { icon: '🔍', label: 'Find Unused Resources', desc: 'Scan for waste across all accounts', prompt: 'Find all unused and idle resources in my Azure environment and estimate total monthly savings.' },
  { icon: '⚙️', label: 'Rightsizing Analysis', desc: 'Identify oversized resources', prompt: 'Analyze my Azure resources for rightsizing opportunities. Which services have cost outliers above 2x the average?' },
  { icon: '📈', label: 'Anomaly Detection', desc: 'Detect unusual spending', prompt: 'Detect cost anomalies and unusual spending patterns in my Azure accounts. Which services are 1.5x above average?' },
  { icon: '💡', label: 'RI Recommendations', desc: 'Reserved Instance savings', prompt: 'Show me the Azure Reserved Instance purchase recommendations with projected net savings for each SKU.' },
  { icon: '💰', label: 'Cost Breakdown', desc: 'Analyze by service & account', prompt: 'Give me the full cost breakdown by service and by account for all Azure Enterprise Agreement billing data.' },
  { icon: '📋', label: 'Executive Report', desc: 'CFO-ready cost report', prompt: 'Generate a professional monthly cost optimization report with executive summary, top findings, and action items.' },
];

function fmt(n) {
  if (n === null || n === undefined) return '—';
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(2)}`;
}

export default function Dashboard({ connections, onSendMessage, onConnect, resourcesOnly = false }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const d = await getDashboard();
      setData(d);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  // ─── Resources-only view ────────────────────────────────────────────────
  if (resourcesOnly) {
    return (
      <div className="dashboard-page">
        <div className="page-header">
          <div className="page-header-title">
            <h1>Cloud Resources</h1>
            <p>Idle and unused resources from Azure billing data</p>
          </div>
          <div className="page-header-actions">
            <button className="card-action-btn" onClick={loadDashboard}>↻ Refresh</button>
            <button className="card-action-btn" onClick={() => onSendMessage('Find all unused and idle resources in my Azure environment.')}>
              🔍 Analyze All
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title"><div className="card-title-icon">⚠️</div>Idle / Unused Resources</div>
            {data && <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{data.idle_resource_count} resources · {data.data_size?.toLocaleString()} billing records</span>}
          </div>
          {loading ? (
            <div className="card-body"><div className="empty-state"><div className="empty-icon">⏳</div><p>Loading from billing data…</p></div></div>
          ) : error ? (
            <div className="card-body"><div className="empty-state"><div className="empty-icon">⚠️</div><p>Backend not available.<br /><small>{error}</small></p></div></div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="resource-table">
                <thead>
                  <tr>
                    <th>Resource Name</th>
                    <th>Service</th>
                    <th>Account</th>
                    <th>Status</th>
                    <th>Cost</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.idle_resources || []).map((r, i) => (
                    <tr key={i}>
                      <td className="col-name">{r.name}</td>
                      <td>{SERVICE_ICONS[r.type] || '☁️'} {r.type}</td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{r.account}</td>
                      <td>
                        <span className={`col-badge ${r.risk === 'high' ? 'badge-red' : 'badge-amber'}`}>{r.status}</span>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>${r.cost.toFixed(4)}</td>
                      <td>
                        <button
                          className="card-action-btn"
                          style={{ fontSize: '0.72rem', padding: '4px 10px' }}
                          onClick={() => onSendMessage((STATUS_PROMPT[r.status] || STATUS_PROMPT.Idle)(r))}
                        >
                          Analyze →
                        </button>
                      </td>
                    </tr>
                  ))}
                  {!data?.idle_resources?.length && (
                    <tr><td colSpan={6}><div className="empty-state"><p>No idle resources found</p></div></td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ─── Main Dashboard ─────────────────────────────────────────────────────
  const connectedCount = connections.filter((c) => c.status === 'connected').length;

  return (
    <div className="dashboard-page">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-title">
          <h1>Cloud Cost Dashboard</h1>
          <p>
            {data
              ? `Live data · ${data.data_size?.toLocaleString()} billing records across ${connectedCount} environment${connectedCount !== 1 ? 's' : ''}`
              : 'Loading billing data…'}
          </p>
        </div>
        <div className="page-header-actions">
          <button className="card-action-btn" onClick={loadDashboard}>↻ Refresh</button>
          <button className="card-action-btn" onClick={() => onSendMessage('Give me a comprehensive cost optimization executive report for all Azure accounts.')}>
            📊 Generate Report
          </button>
          <button className="connect-btn" onClick={onConnect}>＋ Add Cloud</button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div style={{ padding: '12px 18px', background: 'var(--accent-amber-pale)', border: '1px solid rgba(217,119,6,0.3)', borderRadius: 'var(--radius-md)', fontSize: '0.85rem', color: 'var(--accent-amber)', display: 'flex', alignItems: 'center', gap: '10px' }}>
          ⚠️ Backend not reachable — showing structural layout. Start the backend server to see live data.
        </div>
      )}

      {/* KPI Row */}
      <div className="kpi-grid">
        <div className="kpi-card blue">
          <div className="kpi-card-header">
            <span className="kpi-card-label">Total Spend</span>
            <div className="kpi-card-icon">💰</div>
          </div>
          <div className="kpi-card-value">{loading ? '…' : fmt(data?.total_spend)}</div>
          <div className="kpi-card-delta neutral">Azure EA billing data</div>
        </div>
        <div className="kpi-card emerald">
          <div className="kpi-card-header">
            <span className="kpi-card-label">RI Savings Opportunity</span>
            <div className="kpi-card-icon">💡</div>
          </div>
          <div className="kpi-card-value">{loading ? '…' : fmt(data?.ri_potential_savings)}</div>
          <div className="kpi-card-delta positive">↓ From RI recommendations</div>
        </div>
        <div className="kpi-card amber">
          <div className="kpi-card-header">
            <span className="kpi-card-label">Idle Resources</span>
            <div className="kpi-card-icon">⚠️</div>
          </div>
          <div className="kpi-card-value">{loading ? '…' : (data?.idle_resource_count ?? '—')}</div>
          <div className="kpi-card-delta negative">Near-zero cost resources</div>
        </div>
        <div className="kpi-card rose">
          <div className="kpi-card-header">
            <span className="kpi-card-label">Cost Anomalies</span>
            <div className="kpi-card-icon">🚨</div>
          </div>
          <div className="kpi-card-value">{loading ? '…' : (data?.anomaly_count ?? '—')}</div>
          <div className="kpi-card-delta neutral">Services &gt;1.5x average</div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="content-grid">
        {/* Left: Idle Resources from real data */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon">⚠️</div>
              Top Idle & Unused Resources
            </div>
            <button className="card-action-btn" onClick={() => onSendMessage('Find all unused and idle Azure resources and recommend which ones to stop, delete, or rightsize.')}>
              🔍 Analyze All
            </button>
          </div>
          {loading ? (
            <div className="card-body"><div style={{ display: 'flex', gap: '8px', alignItems: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}><span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⏳</span> Loading from billing data…</div></div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="resource-table">
                <thead>
                  <tr>
                    <th>Resource</th>
                    <th>Account</th>
                    <th>Status</th>
                    <th>Cost</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.idle_resources || []).map((r, i) => (
                    <tr key={i}>
                      <td>
                        <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-primary)' }}>{r.name}</div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{SERVICE_ICONS[r.type] || '☁️'} {r.type}</div>
                      </td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{r.account}</td>
                      <td>
                        <span className={`col-badge ${r.risk === 'high' ? 'badge-red' : 'badge-amber'}`}>{r.status}</span>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>${r.cost.toFixed(4)}</td>
                      <td>
                        <button
                          className="card-action-btn"
                          style={{ fontSize: '0.72rem', padding: '4px 10px' }}
                          onClick={() => onSendMessage((STATUS_PROMPT[r.status] || STATUS_PROMPT.Idle)(r))}
                        >
                          Analyze →
                        </button>
                      </td>
                    </tr>
                  ))}
                  {!loading && !data?.idle_resources?.length && (
                    <tr><td colSpan={5}><div className="empty-state"><p>No idle resources found or backend unavailable</p></div></td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right Column */}
        <div className="connect-panel">
          {/* Connected Clouds */}
          <div className="cloud-connect-card">
            <div className="cloud-connect-header">
              <h3>Connected Deployments</h3>
              <p>Manage your cloud environment connections</p>
            </div>
            <div className="cloud-provider-list">
              {connections.map((c) => (
                <button
                  key={c.id}
                  className={`cloud-provider-btn ${c.status === 'connected' ? 'connected' : ''}`}
                  onClick={c.status !== 'connected' ? onConnect : undefined}
                >
                  <div className="provider-logo">{c.icon}</div>
                  <div className="provider-info">
                    <div className="provider-name">{c.name}</div>
                    <div className="provider-status">
                      {c.status === 'connected' ? `✓ ${c.account} · ${c.region}` : 'Click to connect'}
                    </div>
                  </div>
                  <span className="provider-arrow">{c.status === 'connected' ? '✓' : '→'}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Cost by Service — real data */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">
                <div className="card-title-icon">📊</div>
                Cost by Service
              </div>
              {data && <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Live</span>}
            </div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {loading ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Loading…</div>
              ) : (data?.top_services || []).map((item) => (
                <div key={item.service}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '7px', fontSize: '0.82rem', fontWeight: 500, color: 'var(--text-primary)', minWidth: 0 }}>
                      <span>{SERVICE_ICONS[item.service] || '☁️'}</span>
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.service}</span>
                    </div>
                    <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-primary)', flexShrink: 0 }}>{fmt(item.spend)}</span>
                  </div>
                  <div style={{ height: '6px', background: 'var(--bg-surface)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${Math.min(item.pct, 100)}%`, background: 'var(--gradient-primary)', borderRadius: '4px', transition: 'width 0.6s ease' }} />
                  </div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '2px' }}>{item.pct}% of total</div>
                </div>
              ))}
              {!loading && !data?.top_services?.length && (
                <div className="empty-state" style={{ padding: '8px' }}><p style={{ fontSize: '0.78rem' }}>Backend not connected</p></div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Quick AI Actions */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <div className="card-title-icon">⚡</div>
            Quick AI Analysis
          </div>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>AI analyzes your real billing data via OpenRouter</span>
        </div>
        <div className="card-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
            {QUICK_ACTIONS.map((action, i) => (
              <button
                key={i}
                className="welcome-prompt"
                onClick={() => onSendMessage(action.prompt)}
                style={{ textAlign: 'left' }}
              >
                <span className="icon">{action.icon}</span>
                <div className="label">{action.label}</div>
                <div className="desc">{action.desc}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
