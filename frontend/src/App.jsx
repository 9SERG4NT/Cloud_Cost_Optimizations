import { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import AnalysisPanel from './components/AnalysisPanel';
import ConnectModal from './components/ConnectModal';
import ReportsTab from './components/ReportsTab';
import { sendMessage, listSessions, getSession, listTools } from './api';
import './App.css';

const NAV_TABS = [
  { id: 'dashboard', icon: '📊', label: 'Dashboard' },
  { id: 'analysis', icon: '🔍', label: 'AI Analysis' },
  { id: 'resources', icon: '☁️', label: 'Resources' },
  { id: 'reports', icon: '📋', label: 'Reports' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeToolCalls, setActiveToolCalls] = useState([]);
  const [toolCount, setToolCount] = useState(7);
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [connections, setConnections] = useState([
    { id: 'aws', name: 'AWS', icon: '🟠', status: 'connected', account: 'ACC-001', region: 'us-east-1' },
    { id: 'azure', name: 'Azure', icon: '🔵', status: 'connected', account: 'ACC-002', region: 'eastus' },
    { id: 'gcp', name: 'GCP', icon: '🔴', status: 'disconnected', account: null, region: null },
  ]);

  useEffect(() => {
    loadSessions();
    loadToolCount();
  }, []);

  const loadSessions = async () => {
    try {
      const data = await listSessions();
      setSessions(data.sessions || []);
    } catch (err) {
      console.warn('Could not load sessions:', err.message);
    }
  };

  const loadToolCount = async () => {
    try {
      const data = await listTools();
      setToolCount(data.tools?.length || 7);
    } catch (err) {
      console.warn('Could not load tools:', err.message);
    }
  };

  const handleSelectSession = useCallback(async (sessionId) => {
    try {
      const data = await getSession(sessionId);
      setActiveSessionId(sessionId);
      setMessages(
        (data.messages || []).map((m) => ({
          role: m.role,
          content: m.content,
          toolCalls: [],
        }))
      );
      setActiveTab('analysis');
    } catch (err) {
      console.error('Failed to load session:', err);
    }
  }, []);

  const handleNewAnalysis = useCallback(() => {
    setActiveSessionId(null);
    setMessages([]);
    setActiveTab('analysis');
  }, []);

  const handleSendMessage = useCallback(
    async (text) => {
      const userMsg = { role: 'user', content: text, toolCalls: [] };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setActiveToolCalls(['analyzing_query']);
      setActiveTab('analysis');

      try {
        const data = await sendMessage({ message: text, sessionId: activeSessionId });
        const assistantMsg = {
          role: 'assistant',
          content: data.response,
          toolCalls: data.tool_calls_made || [],
        };
        setMessages((prev) => [...prev, assistantMsg]);
        if (!activeSessionId && data.session_id) setActiveSessionId(data.session_id);
        loadSessions();
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: `⚠️ **Error**: ${err.message}\n\nPlease ensure the backend is running at \`http://localhost:8000\`.`,
            toolCalls: [],
          },
        ]);
      } finally {
        setIsLoading(false);
        setActiveToolCalls([]);
      }
    },
    [activeSessionId]
  );

  const handleConnect = (newConnection) => {
    setConnections((prev) =>
      prev.map((c) => (c.id === newConnection.id ? { ...c, ...newConnection, status: 'connected' } : c))
    );
    setShowConnectModal(false);
  };

  const connectedCount = connections.filter((c) => c.status === 'connected').length;

  return (
    <div className="app-shell">
      {/* ── Top Navigation Bar ── */}
      <header className="topbar">
        <a className="topbar-brand" href="#">
          <div className="topbar-brand-icon">⚡</div>
          <div className="topbar-brand-text">
            <strong>OmniCloud</strong>
            <span>FinOps Platform</span>
          </div>
        </a>

        <nav className="topbar-nav">
          {NAV_TABS.map((tab) => (
            <button
              key={tab.id}
              className={`topbar-nav-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="nav-icon">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="topbar-right">
          <div className="status-pill">
            <span className="dot" />
            {connectedCount} Cloud{connectedCount !== 1 ? 's' : ''} Connected
          </div>
          <button className="connect-btn" onClick={() => setShowConnectModal(true)}>
            <span>＋</span> Connect Deployment
          </button>
        </div>
      </header>

      {/* ── App Body ── */}
      <div className="app-body">
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onNewAnalysis={handleNewAnalysis}
          onSendMessage={handleSendMessage}
          toolCount={toolCount}
          connections={connections}
          activeTab={activeTab}
          onChangeTab={setActiveTab}
        />

        <main className="main-content">
          {activeTab === 'dashboard' && (
            <Dashboard
              connections={connections}
              onSendMessage={handleSendMessage}
              onConnect={() => setShowConnectModal(true)}
            />
          )}
          {activeTab === 'analysis' && (
            <AnalysisPanel
              messages={messages}
              isLoading={isLoading}
              activeToolCalls={activeToolCalls}
              onSendMessage={handleSendMessage}
              sessionId={activeSessionId}
            />
          )}
          {activeTab === 'resources' && (
            <Dashboard
              connections={connections}
              onSendMessage={handleSendMessage}
              onConnect={() => setShowConnectModal(true)}
              resourcesOnly
            />
          )}
          {activeTab === 'reports' && (
            <ReportsTab onSendMessage={handleSendMessage} onChangeTab={setActiveTab} />
          )}
        </main>
      </div>

      {/* ── Connect Modal ── */}
      {showConnectModal && (
        <ConnectModal
          connections={connections}
          onConnect={handleConnect}
          onClose={() => setShowConnectModal(false)}
        />
      )}
    </div>
  );
}
