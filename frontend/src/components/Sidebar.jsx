import { useState } from 'react';

const QUICK_TOPICS = [
  { key: 'best_practices', icon: '🏆', title: 'Best Practices', prompt: 'What are the best practices for cloud cost optimization? Give me a comprehensive overview.' },
  { key: 'service_alternatives', icon: '🔄', title: 'Service Alternatives', prompt: 'What are the most cost-effective cloud service alternatives? Compare compute, storage, and database options.' },
  { key: 'finops_governance', icon: '📋', title: 'FinOps Governance', prompt: 'Explain the FinOps governance framework including tagging strategy, budget management, and monthly review process.' },
];

export default function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewAnalysis,
  onSendMessage,
  toolCount,
  connections,
  activeTab,
  onChangeTab,
}) {
  const [topicsOpen, setTopicsOpen] = useState(true);

  const connectedProviders = connections?.filter((c) => c.status === 'connected') || [];

  return (
    <aside className="sidebar">
      {/* Quick Actions */}
      <div className="sidebar-section">
        <div className="sidebar-section-label">Quick Actions</div>
        <button className="sidebar-item" onClick={onNewAnalysis} style={{ background: 'var(--accent-blue)', color: 'white', fontWeight: 600 }}>
          <span className="item-icon">＋</span>
          New AI Analysis
        </button>
      </div>

      <div className="sidebar-divider" />

      {/* Navigation */}
      <div className="sidebar-section">
        <div className="sidebar-section-label">Navigation</div>
        {[
          { id: 'dashboard', icon: '📊', label: 'Dashboard' },
          { id: 'analysis', icon: '🔍', label: 'AI Analysis' },
          { id: 'resources', icon: '☁️', label: 'Resources' },
          { id: 'reports', icon: '📋', label: 'Reports' },
        ].map((tab) => (
          <button
            key={tab.id}
            className={`sidebar-item ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => onChangeTab(tab.id)}
          >
            <span className="item-icon">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      <div className="sidebar-divider" />

      {/* Connections Summary */}
      <div className="sidebar-section">
        <div className="sidebar-section-label">Connected Clouds</div>
        {connectedProviders.length === 0 ? (
          <div className="empty-state" style={{ padding: '12px 8px' }}>
            <div className="empty-icon" style={{ fontSize: '1.3rem' }}>☁️</div>
            <p style={{ fontSize: '0.78rem' }}>No clouds connected</p>
          </div>
        ) : (
          connectedProviders.map((c) => (
            <div key={c.id} className="sidebar-item" style={{ cursor: 'default' }}>
              <span className="item-icon">{c.icon}</span>
              <span style={{ flex: 1, fontSize: '0.82rem' }}>{c.name}</span>
              <span className="item-badge green">✓</span>
            </div>
          ))
        )}
      </div>

      <div className="sidebar-divider" />

      {/* Recent Sessions */}
      <div className="sidebar-section">
        <div className="sidebar-section-label">Recent Analyses</div>
      </div>
      <div className="session-list">
        {sessions.length === 0 ? (
          <div className="empty-state" style={{ padding: '8px' }}>
            <p style={{ fontSize: '0.78rem' }}>No analyses yet</p>
          </div>
        ) : (
          sessions.slice(0, 8).map((s) => (
            <div
              key={s.id}
              className={`session-card ${s.id === activeSessionId ? 'active' : ''}`}
              onClick={() => onSelectSession(s.id)}
            >
              <div className="sc-label">{s.preview || 'New analysis'}</div>
              <div className="sc-time">
                {s.createdAt
                  ? new Date(s.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                  : ''}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="sidebar-divider" />

      {/* Knowledge Topics */}
      <div className="sidebar-section">
        <button
          className="sidebar-section-label"
          style={{ display: 'flex', alignItems: 'center', width: '100%', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontWeight: 700, fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.8px', padding: '0 8px' }}
          onClick={() => setTopicsOpen((p) => !p)}
        >
          <span>📚 Knowledge Topics</span>
          <span style={{ marginLeft: 'auto' }}>{topicsOpen ? '▾' : '▸'}</span>
        </button>
        {topicsOpen && (
          <div style={{ marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {QUICK_TOPICS.map((t) => (
              <button
                key={t.key}
                className="sidebar-item"
                onClick={() => onSendMessage?.(t.prompt)}
              >
                <span className="item-icon">{t.icon}</span>
                <span style={{ fontSize: '0.82rem' }}>{t.title}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="tools-pill">
          <span className="dot" />
          <span>{toolCount} MCP Tools Active</span>
        </div>
      </div>
    </aside>
  );
}
