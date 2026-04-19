import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import ToolBadge from './ToolBadge';

const STARTER_PROMPTS = [
  { icon: '🔍', label: 'Find Unused Resources', desc: 'Scan for waste & idle assets', prompt: 'Find all unused and idle resources across all Azure accounts and estimate total monthly savings.' },
  { icon: '💰', label: 'Cost Breakdown', desc: 'Analyze billing by service', prompt: 'Show me the full cost breakdown by Azure service and by account. Which services are driving the most spend?' },
  { icon: '⚙️', label: 'Rightsizing Analysis', desc: 'Find oversized resources', prompt: 'Analyze all Azure resources for rightsizing opportunities. Flag resources that cost more than 2x the service average.' },
  { icon: '📈', label: 'Anomaly Detection', desc: 'Detect unusual spending', prompt: 'Detect cost anomalies and unusual spending patterns in my Azure EA accounts. What is spiking above the average?' },
  { icon: '💡', label: 'RI Recommendations', desc: 'Reserved Instance savings', prompt: 'Show me all Azure Reserved Instance purchase recommendations and calculate the total potential net savings.' },
  { icon: '📋', label: 'Executive Report', desc: 'CFO-ready cost summary', prompt: 'Generate a professional monthly cloud cost optimization report with executive summary, top findings, and a prioritized action plan.' },
];

export default function AnalysisPanel({ messages, isLoading, activeToolCalls, onSendMessage, sessionId }) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleTextareaInput = (e) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
  };

  const showWelcome = messages.length === 0 && !isLoading;

  return (
    <div className="analysis-page">
      {/* Header */}
      <div className="analysis-topbar">
        <span style={{ fontSize: '1.2rem' }}>🔍</span>
        <h2>AI Cost Analysis</h2>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginLeft: '4px' }}>
          Real Azure data · analyzed by AI
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isLoading && (
            <span style={{ fontSize: '0.75rem', color: 'var(--accent-blue)', background: 'var(--accent-blue-pale)', padding: '3px 10px', borderRadius: '20px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ animation: 'pulse 1.4s ease-in-out infinite', display: 'inline-block' }}>⏳</span> Thinking…
            </span>
          )}
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', background: 'var(--bg-surface)', border: '1px solid var(--border)', padding: '3px 8px', borderRadius: '6px' }}>
            🤖 OpenRouter
          </span>
          {sessionId && (
            <span className="session-chip">Session: {sessionId.slice(0, 8)}…</span>
          )}
        </div>
      </div>


      {/* Messages / Welcome */}
      <div className="analysis-messages">
        {showWelcome ? (
          <div className="welcome-screen">
            <div className="welcome-badge">⚡ Powered by LLM + MCP Tools</div>
            <div className="welcome-icon">🤖</div>
            <h2>Cloud Cost Intelligence</h2>
            <p>
              Ask me anything about your cloud spend. I can analyze waste, detect anomalies,
              recommend rightsizing, and generate executive reports — all in real time.
            </p>
            <div className="welcome-prompts">
              {STARTER_PROMPTS.map((p, i) => (
                <button key={i} className="welcome-prompt" onClick={() => onSendMessage(p.prompt)}>
                  <span className="icon">{p.icon}</span>
                  <div className="label">{p.label}</div>
                  <div className="desc">{p.desc}</div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'user' ? '👤' : '🤖'}
                </div>
                <div className="message-content">
                  {msg.role === 'assistant' ? (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  ) : (
                    <p>{msg.content}</p>
                  )}
                  {msg.toolCalls && msg.toolCalls.length > 0 && (
                    <div style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {msg.toolCalls.map((tc, j) => (
                        <ToolBadge key={j} toolName={tc.tool} isComplete={true} />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="message assistant">
                <div className="message-avatar">🤖</div>
                <div>
                  {activeToolCalls.length > 0 ? (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {activeToolCalls.map((tool, i) => (
                        <ToolBadge key={i} toolName={tool} isComplete={false} />
                      ))}
                    </div>
                  ) : (
                    <div className="typing-indicator">
                      <div className="dot" /><div className="dot" /><div className="dot" />
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="input-bar">
        <div className="input-wrapper">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleTextareaInput}
            onKeyDown={handleKeyDown}
            placeholder="Ask about cloud waste, cost anomalies, rightsizing opportunities..."
            rows={1}
            disabled={isLoading}
          />
          <button className="send-btn" onClick={handleSend} disabled={!input.trim() || isLoading}>
            ↑
          </button>
        </div>
        <div className="input-hint">Press Enter to send · Shift+Enter for new line</div>
      </div>
    </div>
  );
}
