function getAuthHeaders() {
    const saved = localStorage.getItem('omni_user_email');
    return saved ? { 'X-User-Email': saved } : {};
}

const API = {
    async getSetup() {
        const res = await fetch('/api/setup', { headers: getAuthHeaders() });
        return await res.json();
    },

    async saveSetup(data) {
        const res = await fetch('/api/setup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
            body: JSON.stringify(data)
        });
        return await res.json();
    },

    async getAgentsStatus() {
        const res = await fetch('/api/agents/status', { headers: getAuthHeaders() });
        return await res.json();
    },

    async triggerAgentCycle() {
        const res = await fetch('/api/agents/trigger', { method: 'POST', headers: getAuthHeaders() });
        return await res.json();
    },

    async getPosts(status = 'ALL') {
        const res = await fetch(`/api/posts?status=${status}`, { headers: getAuthHeaders() });
        return await res.json();
    },

    async getAnalyticsOverview() {
        const res = await fetch('/api/analytics/overview', { headers: getAuthHeaders() });
        return await res.json();
    },

    async getAgentMemory() {
        const res = await fetch('/api/agents/memory', { headers: getAuthHeaders() });
        return await res.json();
    },

    async getSystemLogs() {
        const res = await fetch('/api/logs/system', { headers: getAuthHeaders() });
        return await res.json();
    }
};

