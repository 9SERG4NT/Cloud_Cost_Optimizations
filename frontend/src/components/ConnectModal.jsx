import { useState, useEffect } from 'react';

const PROVIDERS = [
  { id: 'aws', name: 'AWS', icon: '🟠', placeholder_key: 'Access Key ID', placeholder_secret: 'Secret Access Key', placeholder_region: 'us-east-1' },
  { id: 'azure', name: 'Azure', icon: '🔵', placeholder_key: 'Client ID', placeholder_secret: 'Client Secret', placeholder_region: 'eastus' },
  { id: 'gcp', name: 'GCP', icon: '🔴', placeholder_key: 'Project ID', placeholder_secret: 'Service Account JSON Key', placeholder_region: 'us-central1' },
];

const CONNECT_STEPS = [
  'Validating credentials',
  'Fetching account info',
  'Scanning resources',
  'Loading cost data',
  'Connection established',
];

export default function ConnectModal({ connections, onConnect, onClose }) {
  const [step, setStep] = useState('select'); // 'select' | 'form' | 'connecting' | 'success'
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [form, setForm] = useState({ account: '', key: '', secret: '', region: '' });
  const [connectStep, setConnectStep] = useState(0);

  const provider = PROVIDERS.find((p) => p.id === selectedProvider);
  const existingConn = connections.find((c) => c.id === selectedProvider);

  const handleSelectProvider = (id) => {
    setSelectedProvider(id);
    const conn = connections.find((c) => c.id === id);
    if (conn?.status === 'connected') {
      setForm({ account: conn.account || '', key: '', secret: '', region: conn.region || '' });
    } else {
      setForm({ account: '', key: '', secret: '', region: PROVIDERS.find((p) => p.id === id)?.placeholder_region || '' });
    }
    setStep('form');
  };

  const handleConnect = () => {
    setStep('connecting');
    setConnectStep(0);
  };

  useEffect(() => {
    if (step !== 'connecting') return;
    if (connectStep < CONNECT_STEPS.length - 1) {
      const t = setTimeout(() => setConnectStep((s) => s + 1), 700);
      return () => clearTimeout(t);
    } else {
      const t = setTimeout(() => setStep('success'), 600);
      return () => clearTimeout(t);
    }
  }, [step, connectStep]);

  const handleDone = () => {
    onConnect({
      id: selectedProvider,
      name: provider?.name,
      icon: provider?.icon,
      account: form.account || `ACC-${Math.floor(Math.random() * 900 + 100)}`,
      region: form.region,
      status: 'connected',
    });
  };

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        {/* Header */}
        <div className="modal-header">
          <div className="modal-header-icon">🔌</div>
          <div>
            <h2>Connect Cloud Deployment</h2>
            <p>Link your cloud environment for cost analysis</p>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {step === 'select' && (
            <>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                Select your cloud provider to get started:
              </p>
              <div className="provider-select-grid">
                {PROVIDERS.map((p) => {
                  const conn = connections.find((c) => c.id === p.id);
                  return (
                    <button
                      key={p.id}
                      className={`provider-select-btn ${selectedProvider === p.id ? 'selected' : ''}`}
                      onClick={() => handleSelectProvider(p.id)}
                    >
                      <span className="p-logo">{p.icon}</span>
                      <span>{p.name}</span>
                      {conn?.status === 'connected' && (
                        <span style={{ fontSize: '0.65rem', color: 'var(--accent-emerald)', fontWeight: 700 }}>✓ Connected</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </>
          )}

          {step === 'form' && provider && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '18px', padding: '10px 14px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)' }}>
                <span style={{ fontSize: '1.4rem' }}>{provider.icon}</span>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>{provider.name}</div>
                  {existingConn?.status === 'connected' && (
                    <div style={{ fontSize: '0.72rem', color: 'var(--accent-emerald)', fontWeight: 600 }}>Currently connected — updating credentials</div>
                  )}
                </div>
                <button className="card-action-btn" style={{ marginLeft: 'auto' }} onClick={() => setStep('select')}>← Back</button>
              </div>

              <div className="form-group">
                <label>Account ID / Name</label>
                <input
                  className="form-control"
                  placeholder={`e.g. ACC-001 or My ${provider.name} Account`}
                  value={form.account}
                  onChange={(e) => setForm((f) => ({ ...f, account: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label>{provider.placeholder_key}</label>
                <input
                  className="form-control"
                  placeholder={`Enter your ${provider.placeholder_key}`}
                  value={form.key}
                  onChange={(e) => setForm((f) => ({ ...f, key: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label>{provider.placeholder_secret}</label>
                <input
                  className="form-control"
                  type="password"
                  placeholder="••••••••••••••••"
                  value={form.secret}
                  onChange={(e) => setForm((f) => ({ ...f, secret: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label>Default Region</label>
                <input
                  className="form-control"
                  placeholder={provider.placeholder_region}
                  value={form.region}
                  onChange={(e) => setForm((f) => ({ ...f, region: e.target.value }))}
                />
              </div>
              <div style={{ padding: '10px 14px', background: 'var(--accent-blue-pale)', border: '1px solid var(--border-accent)', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', color: 'var(--accent-blue)' }}>
                🔒 Credentials are only used to fetch cost & usage data and are never stored on our servers.
              </div>
            </>
          )}

          {step === 'connecting' && (
            <div className="connect-progress">
              <div className="connect-spinner" />
              <p>Connecting to {provider?.name}...</p>
              <div className="connect-steps">
                {CONNECT_STEPS.map((s, i) => (
                  <div key={i} className={`connect-step ${i < connectStep ? 'done' : i === connectStep ? 'active' : ''}`}>
                    <div className="step-check">{i < connectStep ? '✓' : ''}</div>
                    {s}
                  </div>
                ))}
              </div>
            </div>
          )}

          {step === 'success' && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <div style={{ fontSize: '3rem', marginBottom: '12px' }}>✅</div>
              <h3 style={{ fontWeight: 700, marginBottom: '8px', color: 'var(--text-primary)' }}>
                {provider?.name} Connected!
              </h3>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', maxWidth: '320px', margin: '0 auto 16px' }}>
                Your {provider?.name} deployment is now connected. Cost data is being fetched and will be available shortly.
              </p>
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', flexWrap: 'wrap' }}>
                <span className="col-badge badge-green">✓ Account Linked</span>
                <span className="col-badge badge-green">✓ Cost API Ready</span>
                <span className="col-badge badge-green">✓ Resources Scanned</span>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="modal-footer">
          {step === 'select' && (
            <button className="btn-secondary" onClick={onClose}>Cancel</button>
          )}
          {step === 'form' && (
            <>
              <button className="btn-secondary" onClick={onClose}>Cancel</button>
              <button className="btn-primary" onClick={handleConnect}>
                🔌 Connect Deployment
              </button>
            </>
          )}
          {step === 'success' && (
            <>
              <button className="btn-secondary" onClick={onClose}>Close</button>
              <button className="btn-primary" onClick={handleDone}>
                ✓ Done
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
