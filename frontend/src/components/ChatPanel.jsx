import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import ToolBadge from './ToolBadge';

const WELCOME_PROMPTS = [
    {
        icon: '🔍',
        label: 'Find Unused AWS Resources',
        desc: 'Scan for unattached volumes, idle instances & waste',
        prompt: 'Find all unused resources in my AWS environment and estimate potential monthly savings.',
    },
    {
        icon: '📊',
        label: 'Azure Cost Breakdown',
        desc: 'Analyze historical Azure billing by account',
        prompt: 'Show me the cost breakdown for Azure account ACC-001 for the most recent billing period.',
    },
    {
        icon: '⚙️',
        label: 'Rightsizing Analysis',
        desc: 'Identify oversized EC2 and RDS instances',
        prompt: 'Analyze my EC2 and RDS instances for rightsizing opportunities over the last 30 days.',
    },
    {
        icon: '📈',
        label: 'Cost Anomaly Detection',
        desc: 'Detect unusual spending patterns in AWS',
        prompt: 'Detect any cost anomalies and unusual spending patterns in my AWS account over the last 30 days.',
    },
    {
        icon: '🏆',
        label: 'FinOps Best Practices',
        desc: 'Expert guidance on cost optimization strategies',
        prompt: 'What are the top AWS cost optimization best practices? Cover compute, storage, network, and database strategies.',
    },
    {
        icon: '📋',
        label: 'Monthly Report Template',
        desc: 'Generate a CFO-ready cost report template',
        prompt: 'Generate a professional monthly cost optimization report template with sections for executive summary, cost breakdown, and action items.',
    },
];

export default function ChatPanel({
    messages,
    isLoading,
    activeToolCalls,
    onSendMessage,
    sessionId,
}) {
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
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleTextareaInput = (e) => {
        setInput(e.target.value);
        e.target.style.height = 'auto';
        e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
    };

    const handlePromptClick = (prompt) => {
        onSendMessage(prompt);
    };

    const showWelcome = messages.length === 0 && !isLoading;

    return (
        <div className="chat-panel">
            {/* Header */}
            <div className="chat-header">
                <h2>
                    {sessionId ? '💬 Active Analysis' : '⚡ OmniCloud FinOps Agent'}
                </h2>
                {sessionId && (
                    <span className="session-id">Session: {sessionId.slice(0, 8)}...</span>
                )}
            </div>

            {/* Messages or Welcome */}
            <div className="chat-messages">
                {showWelcome ? (
                    <div className="welcome-screen">
                        <div className="welcome-icon">⚡</div>
                        <h2>OmniCloud FinOps Agent</h2>
                        <p>
                            Your AI-powered multi-cloud cost intelligence assistant.
                            Ask about AWS infrastructure waste or Azure billing history.
                        </p>
                        <div className="welcome-prompts">
                            {WELCOME_PROMPTS.map((wp, i) => (
                                <button
                                    key={i}
                                    className="welcome-prompt"
                                    onClick={() => handlePromptClick(wp.prompt)}
                                >
                                    <div className="icon">{wp.icon}</div>
                                    <div className="label">{wp.label}</div>
                                    <div className="desc">{wp.desc}</div>
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
                                    {/* Show tool badges for this message */}
                                    {msg.toolCalls && msg.toolCalls.length > 0 && (
                                        <div style={{ marginTop: '10px' }}>
                                            {msg.toolCalls.map((tc, j) => (
                                                <ToolBadge key={j} toolName={tc.tool} isComplete={true} />
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}

                        {/* Loading State */}
                        {isLoading && (
                            <div className="message assistant">
                                <div className="message-avatar">🤖</div>
                                <div>
                                    {activeToolCalls.length > 0 ? (
                                        activeToolCalls.map((tool, i) => (
                                            <ToolBadge key={i} toolName={tool} isComplete={false} />
                                        ))
                                    ) : (
                                        <div className="typing-indicator">
                                            <div className="dot"></div>
                                            <div className="dot"></div>
                                            <div className="dot"></div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="chat-input-area">
                <div className="chat-input-wrapper">
                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={handleTextareaInput}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask about AWS waste, Azure billing, or cost optimization..."
                        rows={1}
                        disabled={isLoading}
                    />
                    <button
                        className="send-btn"
                        onClick={handleSend}
                        disabled={!input.trim() || isLoading}
                    >
                        ↑
                    </button>
                </div>
                <div className="chat-disclaimer">
                    Powered by Llama 4 Scout via Groq API
                </div>
            </div>
        </div>
    );
}
