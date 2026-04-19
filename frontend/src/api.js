/**
 * API client for the OmniCloud FinOps Agent backend.
 */

const API_BASE = 'http://localhost:8000/api';

/**
 * Fetch real dashboard metrics from Azure billing data.
 */
export async function getDashboard() {
    const res = await fetch(`${API_BASE}/dashboard`);
    if (!res.ok) throw new Error(`Dashboard fetch failed: ${res.statusText}`);
    return res.json();
}

/**
 * Send a chat message to the agent.
 */
export async function sendMessage({ message, sessionId, userId = 'default-user' }) {
    const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message,
            session_id: sessionId || null,
            user_id: userId,
        }),
    });
    if (!res.ok) throw new Error(`Chat failed: ${res.statusText}`);
    return res.json();
}

/**
 * List chat sessions for a user.
 */
export async function listSessions(userId = 'default-user') {
    const res = await fetch(`${API_BASE}/sessions?user_id=${encodeURIComponent(userId)}`);
    if (!res.ok) throw new Error(`Failed to list sessions: ${res.statusText}`);
    return res.json();
}

/**
 * Get a full chat session by ID.
 */
export async function getSession(sessionId) {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
    if (!res.ok) throw new Error(`Failed to get session: ${res.statusText}`);
    return res.json();
}

/**
 * List available MCP tools.
 */
export async function listTools() {
    const res = await fetch(`${API_BASE}/tools`);
    if (!res.ok) throw new Error(`Failed to list tools: ${res.statusText}`);
    return res.json();
}

/**
 * Save a cost report.
 */
export async function saveReport({ userId = 'default-user', sessionId, title, content }) {
    const res = await fetch(`${API_BASE}/reports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            session_id: sessionId,
            title,
            content,
        }),
    });
    if (!res.ok) throw new Error(`Failed to save report: ${res.statusText}`);
    return res.json();
}

/**
 * List saved cost reports for a user.
 */
export async function listReports(userId = 'default-user') {
    const res = await fetch(`${API_BASE}/reports?user_id=${encodeURIComponent(userId)}`);
    if (!res.ok) throw new Error(`Failed to list reports: ${res.statusText}`);
    return res.json();
}

/**
 * List knowledge base topics.
 */
export async function listKnowledge() {
    const res = await fetch(`${API_BASE}/knowledge`);
    if (!res.ok) throw new Error(`Failed to list knowledge: ${res.statusText}`);
    return res.json();
}

/**
 * Get a report template by name.
 */
export async function getTemplate(name) {
    const res = await fetch(`${API_BASE}/templates/${encodeURIComponent(name)}`);
    if (!res.ok) throw new Error(`Failed to get template: ${res.statusText}`);
    return res.json();
}

/**
 * Health check.
 */
export async function healthCheck() {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error('Backend not available');
    return res.json();
}
