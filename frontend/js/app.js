document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

let currentAutoMode = false;
let currentUser = null;

function initApp() {
    setupEventListeners();
    setupAuthModal();
    checkCurrentUser();
    loadSetupConfig();

    const path = window.location.pathname;
    if (path === '/dashboard' || path === '/overview') {
        refreshAllData();
        setInterval(refreshAllData, 10000);
    } else if (path === '/posts') {
        loadPosts();
        setInterval(loadPosts, 10000);
    } else if (path === '/analytics') {
        loadAnalytics();
        setInterval(loadAnalytics, 10000);
    } else if (path === '/pages') {
        loadSettingsConnectedPages();
        setInterval(loadSettingsConnectedPages, 10000);
    } else if (path === '/settings') {
        loadSetupConfig();
    }
}

function openAuthModal(mode = 'login') {
    const modal = document.getElementById('auth-modal');
    if (!modal) return;

    const tabLogin = document.getElementById('tab-btn-login');
    const tabSignup = document.getElementById('tab-btn-signup');
    const formLogin = document.getElementById('form-login');
    const formSignup = document.getElementById('form-signup');

    modal.classList.add('active');
    if (mode === 'signup') {
        if (tabSignup) tabSignup.classList.add('active');
        if (tabLogin) tabLogin.classList.remove('active');
        if (formSignup) formSignup.style.display = 'flex';
        if (formLogin) formLogin.style.display = 'none';
    } else {
        if (tabLogin) tabLogin.classList.add('active');
        if (tabSignup) tabSignup.classList.remove('active');
        if (formLogin) formLogin.style.display = 'flex';
        if (formSignup) formSignup.style.display = 'none';
    }
}

function setupAuthModal() {
    const modal = document.getElementById('auth-modal');
    const btnShow = document.getElementById('btn-show-auth');
    const btnClose = document.getElementById('btn-close-auth');
    const tabLogin = document.getElementById('tab-btn-login');
    const tabSignup = document.getElementById('tab-btn-signup');
    const formLogin = document.getElementById('form-login');
    const formSignup = document.getElementById('form-signup');

    if (btnShow) {
        btnShow.addEventListener('click', () => {
            if (currentUser) {
                if (confirm(`Logged in as ${currentUser.email}. Do you want to log out?`)) {
                    logoutUser();
                }
            } else {
                openAuthModal('login');
            }
        });
    }

    if (btnClose && modal) {
        btnClose.addEventListener('click', () => modal.classList.remove('active'));
    }

    if (tabLogin) tabLogin.addEventListener('click', () => openAuthModal('login'));
    if (tabSignup) tabSignup.addEventListener('click', () => openAuthModal('signup'));

    // Login submit
    if (formLogin) {
        formLogin.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;
            try {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                const data = await res.json();
                if (res.ok) {
                    currentUser = data;
                    localStorage.setItem('omni_user_email', data.email);
                    updateUserUI(currentUser);
                    if (modal) modal.classList.remove('active');
                    if (window.location.pathname === '/' || window.location.pathname === '/landing') {
                        window.location.href = '/dashboard';
                    } else {
                        await checkCurrentUser();
                    }
                } else {
                    alert(data.detail || 'Login failed.');
                }
            } catch (err) {
                console.error("Login error:", err);
            }
        });
    }

    // Signup submit
    if (formSignup) {
        formSignup.addEventListener('submit', async (e) => {
            e.preventDefault();
            const full_name = document.getElementById('signup-name').value;
            const email = document.getElementById('signup-email').value;
            const password = document.getElementById('signup-password').value;
            try {
                const res = await fetch('/api/auth/signup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ full_name, email, password })
                });
                const data = await res.json();
                if (res.ok) {
                    currentUser = data;
                    localStorage.setItem('omni_user_email', data.email);
                    updateUserUI(currentUser);
                    if (modal) modal.classList.remove('active');
                    if (window.location.pathname === '/' || window.location.pathname === '/landing') {
                        window.location.href = '/dashboard';
                    } else {
                        await checkCurrentUser();
                    }
                } else {
                    alert(data.detail || 'Signup failed.');
                }
            } catch (err) {
                console.error("Signup error:", err);
            }
        });
    }
}


async function checkCurrentUser() {
    try {
        const res = await fetch('/api/auth/me');
        if (res.ok) {
            const data = await res.json();
            if (data && data.email) {
                currentUser = data;
                updateUserUI(currentUser);
            } else {
                currentUser = null;
                updateUserUI(null);
            }
        } else {
            currentUser = null;
            updateUserUI(null);
        }
    } catch (err) {
        currentUser = null;
        updateUserUI(null);
    }
}

function updateUserUI(user) {
    const btnLabel = document.getElementById('user-display-name');
    if (btnLabel) {
        if (user) {
            btnLabel.textContent = `👤 ${user.full_name || user.email}`;
        } else {
            btnLabel.textContent = 'Sign In';
        }
    }
}

async function logoutUser() {
    await fetch('/api/auth/logout', { method: 'POST' });
    currentUser = null;
    localStorage.removeItem('omni_user_email');
    updateUserUI(null);
    window.location.href = '/';
}

// Wizard step controls
function showWizardStep(stepNum) {
    document.querySelectorAll('.wizard-step').forEach(s => s.style.display = 'none');
    const stepEl = document.getElementById(`wizard-step-${stepNum}`);
    if (stepEl) stepEl.style.display = 'block';
}

async function loadDiscoveredPagesStep() {
    showWizardStep(2);
    const container = document.getElementById('wizard-pages-container');
    if (!container) return;
    container.innerHTML = '<div style="color:#64748b">Fetching connected Facebook pages...</div>';

    try {
        const res = await fetch('/api/setup/pages');
        const pages = await res.json();
        
        if (!pages || pages.length === 0) {
            container.innerHTML = `
                <div class="page-item-card">
                    <div class="page-item-info">
                        <h4>No Facebook Pages Discovered Yet</h4>
                        <span>Click 'Back' and authorize Meta Facebook Login.</span>
                    </div>
                </div>
            `;
            return;
        }

        let html = '';
        pages.forEach((p) => {
            html += `
                <div class="page-item-card" data-page-id="${p.facebook_page_id}">
                    <div class="page-item-info">
                        <h4>${p.facebook_page_name || 'Facebook Page'}</h4>
                        <span>ID: ${p.facebook_page_id} ${p.instagram_account_id ? '• Linked Instagram' : ''}</span>
                    </div>
                    <div style="display:flex;gap:10px;align-items:center;">
                        <select class="form-select page-cat-select" style="width:180px;">
                            <option value="Technology & AI" ${p.page_category === 'Technology & AI' ? 'selected' : ''}>Technology & AI</option>
                            <option value="Digital Marketing & Growth" ${p.page_category === 'Digital Marketing & Growth' ? 'selected' : ''}>Digital Marketing & Growth</option>
                            <option value="Business & Entrepreneurship" ${p.page_category === 'Business & Entrepreneurship' ? 'selected' : ''}>Business & Entrepreneurship</option>
                            <option value="Fitness & Wellness" ${p.page_category === 'Fitness & Wellness' ? 'selected' : ''}>Fitness & Wellness</option>
                        </select>
                        <label class="checkbox-container">
                            <input type="checkbox" class="page-active-chk" ${p.is_active_growth ? 'checked' : ''}>
                            <span class="checkmark"></span>
                        </label>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;

    } catch (err) {
        console.error("Error loading pages:", err);
    }
}

async function loadSettingsConnectedPages() {
    const container = document.getElementById('settings-connected-pages-list');
    if (!container) return;
    container.innerHTML = '<div style="color:#64748b">Loading connected pages...</div>';

    try {
        const res = await fetch('/api/setup/pages');
        const pages = await res.json();

        if (!pages || pages.length === 0) {
            container.innerHTML = `
                <div class="page-item-card">
                    <div class="page-item-info">
                        <h4>No Facebook Pages Connected Yet</h4>
                        <span>Click "+ Connect New Facebook Account" to discover your pages.</span>
                    </div>
                </div>
            `;
            return;
        }

        let html = '';
        pages.forEach((p) => {
            const pageId = p.facebook_page_id;
            const pageName = (p.facebook_page_name || 'Facebook Page').replace(/'/g, "\\'");
            const pageAbout = (p.page_about || '').replace(/'/g, "\\'").replace(/\n/g, ' ');
            const targetAud = (p.target_audience || 'General Target Audience').replace(/'/g, "\\'");
            const growthGoal = (p.growth_goal || 'Brand Building & High Engagement').replace(/'/g, "\\'");
            const toneOfVoice = (p.tone_of_voice || 'Professional & Engaging').replace(/'/g, "\\'");
            const customInst = (p.custom_instructions || '').replace(/'/g, "\\'");

            const isActive = p.is_active_growth !== false;
            const statusBadgeHtml = isActive 
                ? `<span class="tag-badge" style="background:#dcfce7;color:#166534;font-size:12px;font-weight:700;display:inline-flex;align-items:center;gap:4px;"><span style="width:8px;height:8px;border-radius:50%;background:#22c55e;display:inline-block;"></span> 24/7 AI Growth Active (ON WORKING)</span>`
                : `<span class="tag-badge" style="background:#f1f5f9;color:#64748b;font-size:12px;">⏸️ Paused</span>`;

            html += `
                <div class="page-item-card" style="padding:20px;margin-bottom:16px;background:#ffffff;border:1px solid #e2e8f0;border-radius:14px;">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                        <div class="page-item-info">
                            <h4 style="font-size:17px;color:#0f172a;font-weight:700;margin-bottom:4px;">${p.facebook_page_name || 'Facebook Page'}</h4>
                            <span style="font-size:13px;color:#64748b;">ID: ${p.facebook_page_id} ${p.instagram_account_id ? '• Linked Instagram' : ''}</span>
                        </div>
                        <div>
                            ${statusBadgeHtml}
                        </div>
                    </div>
                    
                    <div style="background:#f8fafc;padding:12px 14px;border-radius:10px;border:1px solid #f1f5f9;margin-bottom:14px;font-size:13px;color:#334155;">
                        <div style="margin-bottom:4px;"><strong>📝 Page About / Business:</strong> ${p.page_about ? p.page_about : '<em style="color:#ef4444;">Not set - Click "Configure Target Goal" to add About details!</em>'}</div>
                        <div style="margin-top:4px;"><strong>🎯 Target Audience:</strong> ${p.target_audience || 'General Target Audience'}</div>
                        <div style="margin-top:4px;"><strong>🚀 Growth Goal:</strong> ${p.growth_goal || 'Brand Awareness & Organic Engagement'}</div>
                        <div style="margin-top:4px;"><strong>🗣️ Voice & Tone:</strong> ${p.tone_of_voice || 'Professional & Engaging'} ${p.custom_instructions ? `• <em>"${p.custom_instructions}"</em>` : ''}</div>
                    </div>

                    <div style="display:flex;gap:10px;align-items:center;justify-content:flex-end;">
                        <button type="button" class="btn btn-secondary" onclick="openTargetModal('${pageId}', '${pageName}', '${p.page_category || 'Technology & AI'}', '${pageAbout}', '${targetAud}', '${growthGoal}', '${toneOfVoice}', '${customInst}')" style="background:#e0e7ff;color:#4f46e5;border:1px solid #c7d2fe;padding:8px 14px;font-size:13px;font-weight:600;">
                            ⚙️ Edit Page About & Strategy
                        </button>
                        <button type="button" class="btn btn-primary" onclick="openTargetModal('${pageId}', '${pageName}', '${p.page_category || 'Technology & AI'}', '${pageAbout}', '${targetAud}', '${growthGoal}', '${toneOfVoice}', '${customInst}')" style="background:#4f46e5;color:#ffffff;padding:8px 18px;font-size:13px;font-weight:700;">
                            🚀 Launch AI Growth Pipeline
                        </button>
                        <button type="button" class="btn btn-secondary" onclick="deletePage('${pageId}', '${pageName}')" style="background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;padding:8px 14px;font-size:13px;">
                            🗑️ Remove Page
                        </button>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;

    } catch (err) {
        console.error("Failed loading settings pages:", err);
    }
}

function openTargetModal(pageId, pageName, category, pageAbout, targetAud, growthGoal, toneOfVoice, customInst) {
    const modal = document.getElementById('target-modal');
    if (!modal) return;
    document.getElementById('modal-page-id').value = pageId;
    document.getElementById('modal-page-name').textContent = pageName;
    document.getElementById('page-about').value = (pageAbout && pageAbout !== 'undefined') ? pageAbout : '';
    document.getElementById('target-audience').value = (targetAud && targetAud !== 'undefined') ? targetAud : 'General Target Audience';
    document.getElementById('growth-goal').value = (growthGoal && growthGoal !== 'undefined') ? growthGoal : 'Brand Awareness & Organic Engagement';
    document.getElementById('tone-of-voice').value = (toneOfVoice && toneOfVoice !== 'undefined') ? toneOfVoice : 'Professional & Authoritative';
    document.getElementById('page-category-modal').value = (category && category !== 'undefined') ? category : 'Technology & AI';
    document.getElementById('custom-instructions').value = (customInst && customInst !== 'undefined') ? customInst : '';
    modal.classList.add('active');
}


function closeTargetModal() {
    const modal = document.getElementById('target-modal');
    if (modal) modal.classList.remove('active');
}

async function triggerPagePipeline(facebookPageId, pageName, btnElement, pageAbout) {
    if (!pageAbout || pageAbout === 'undefined' || pageAbout.trim() === '') {
        alert(`📝 Before launching AI Growth for '${pageName}', please enter your Page About & Business Description so AI can understand your business!`);
        openTargetModal(facebookPageId, pageName, 'Technology & AI', '', '', '', '', '');
        return;
    }

    const btn = btnElement || (event ? event.currentTarget : null);
    const origHtml = btn ? btn.innerHTML : '🚀 Launch AI Growth Pipeline';
    
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span style="display:inline-flex;align-items:center;gap:6px;">⚡ Executing AI Pipeline...</span>`;
    }


    try {
        const res = await fetch(`/api/setup/pages/${facebookPageId}/trigger`, { method: 'POST' });
        const data = await res.json();
        
        if (res.ok) {
            // Live polling for agent statuses
            let checks = 0;
            const interval = setInterval(async () => {
                checks++;
                if (typeof loadAgentsStatus === 'function') await loadAgentsStatus();
                if (checks >= 6) {
                    clearInterval(interval);
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = origHtml;
                    }
                    if (window.location.pathname !== '/dashboard') {
                        window.location.href = '/dashboard';
                    } else {
                        refreshAllData();
                    }
                }
            }, 1000);
        } else {
            alert(data.detail || 'Failed triggering page pipeline.');
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = origHtml;
            }
        }
    } catch (err) {
        console.error("Error triggering page pipeline:", err);
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = origHtml;
        }
    }
}


async function deletePage(facebookPageId, pageName) {
    if (!confirm(`Are you sure you want to disconnect and remove page "${pageName}" (${facebookPageId})?`)) {
        return;
    }
    try {
        const res = await fetch(`/api/setup/pages/${facebookPageId}`, { method: 'DELETE' });
        const data = await res.json();
        if (res.ok) {
            alert(`Page "${pageName}" disconnected successfully!`);
            loadSettingsConnectedPages();
            checkCurrentUser();
        } else {
            alert(data.detail || 'Failed to remove page.');
        }
    } catch (err) {
        console.error("Error deleting page:", err);
    }
}

async function savePagesAndProceed() {
    showWizardStep(3);
}

function setupEventListeners() {
    const connectButtons = [
        document.getElementById('btn-wizard-connect-fb'),
        document.getElementById('btn-settings-connect-fb')
    ];

    connectButtons.forEach(btn => {
        if (btn) {
            btn.addEventListener('click', async () => {
                try {
                    const res = await fetch('/api/setup/facebook/login_url');
                    const data = await res.json();
                    if (data.login_url) {
                        window.location.href = data.login_url;
                    }
                } catch (err) {
                    console.error("FB Login error:", err);
                }
            });
        }
    });

    const wizKeysForm = document.getElementById('wizard-keys-form');
    if (wizKeysForm) {
        wizKeysForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const geminiKey = document.getElementById('wiz-gemini-key').value;
            const virtuxKey = document.getElementById('wiz-virtux-key').value;
            const autoMode = document.getElementById('wiz-auto-mode').checked;

            const currentSetup = await API.getSetup();
            currentSetup.gemini_api_key = geminiKey || currentSetup.gemini_api_key;
            currentSetup.virtux_api_key = virtuxKey || currentSetup.virtux_api_key;
            currentSetup.auto_mode_enabled = autoMode;

            await API.saveSetup(currentSetup);
            window.location.href = '/dashboard';
        });
    }

    const headerToggle = document.getElementById('header-auto-toggle');
    if (headerToggle) {
        headerToggle.addEventListener('change', async (e) => {
            const enabled = e.target.checked;
            await toggleAutoMode(enabled);
        });
    }

    const triggerBtn = document.getElementById('btn-trigger-cycle');
    if (triggerBtn) {
        triggerBtn.addEventListener('click', async () => {
            triggerBtn.disabled = true;
            triggerBtn.innerHTML = `<span>Running AI Pipeline...</span>`;
            await API.triggerAgentCycle();
            setTimeout(async () => {
                await refreshAllData();
                triggerBtn.disabled = false;
                triggerBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg><span>Run AI Cycle Now</span>`;
            }, 3000);
        });
    }

    const setupForm = document.getElementById('setup-form');
    if (setupForm) {
        setupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                page_category: document.getElementById('setup-category').value,
                language: document.getElementById('setup-language').value,
                gemini_api_key: document.getElementById('setup-gemini-key').value,
                virtux_api_key: document.getElementById('setup-virtux-key').value,
                auto_mode_enabled: document.getElementById('header-auto-toggle') ? document.getElementById('header-auto-toggle').checked : false
            };
            await API.saveSetup(payload);
            alert('Settings saved & synced with .env file successfully!');
            refreshAllData();
        });
    }
}

async function loadSetupConfig() {
    try {
        const config = await API.getSetup();
        if (document.getElementById('setup-category')) document.getElementById('setup-category').value = config.page_category || 'Technology & AI';
        if (document.getElementById('setup-language')) document.getElementById('setup-language').value = config.language || 'English';
        if (document.getElementById('setup-gemini-key')) document.getElementById('setup-gemini-key').value = config.gemini_api_key || '';
        if (document.getElementById('setup-virtux-key')) document.getElementById('setup-virtux-key').value = config.virtux_api_key || '';
        
        if (document.getElementById('header-auto-toggle')) document.getElementById('header-auto-toggle').checked = config.auto_mode_enabled;
        updateAutoModeUI(config.auto_mode_enabled);
    } catch (err) {
        console.error("Failed loading setup:", err);
    }
}

async function toggleAutoMode(enabled) {
    try {
        const currentSetup = await API.getSetup();
        currentSetup.auto_mode_enabled = enabled;
        await API.saveSetup(currentSetup);
        updateAutoModeUI(enabled);
    } catch (err) {
        console.error("Failed toggling auto mode:", err);
    }
}

function updateAutoModeUI(enabled) {
    currentAutoMode = enabled;
    const autoDot = document.getElementById('sidebar-auto-dot');
    const autoText = document.getElementById('sidebar-auto-text');
    const bannerText = document.getElementById('auto-banner-status');

    if (enabled) {
        if (autoDot) autoDot.classList.add('active');
        if (autoText) autoText.textContent = 'ONLINE (24/7)';
        if (bannerText) bannerText.textContent = 'Autonomous Mode Active • System Self-Operating';
    } else {
        if (autoDot) autoDot.classList.remove('active');
        if (autoText) autoText.textContent = 'OFFLINE';
        if (bannerText) bannerText.textContent = 'Autonomous Mode Inactive';
    }
}

async function refreshAllData() {
    loadAgentsStatus();
    loadAISuggestions();
    loadAnalytics();
    loadPosts();
}

async function loadAgentsStatus() {
    try {
        const data = await API.getAgentsStatus();
        const container = document.getElementById('pipeline-cards-container');
        if (!container) return;
        
        let html = '';
        data.agents.forEach(ag => {
            html += `
                <div class="agent-card">
                    <div class="agent-card-header">
                        <span class="agent-name">${ag.display_name}</span>
                        <span class="agent-status-badge ${ag.status}">${ag.status}</span>
                    </div>
                    <div class="agent-last-action" style="font-size:13px;color:#475569;margin-top:6px;">${ag.last_action}</div>
                    <div class="agent-card-footer" style="font-size:11px;color:#94a3b8;margin-top:12px;">
                        <span>Last Run: ${ag.last_run || 'Startup'}</span>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch (err) {
        console.error("Failed fetching agent statuses:", err);
    }
}

async function loadAISuggestions() {
    const container = document.getElementById('ai-suggestions-container');
    if (!container) return;

    try {
        const res = await fetch('/api/agents/suggestions');
        const data = await res.json();
        
        let html = '';
        if (data.suggestions && data.suggestions.length > 0) {
            data.suggestions.forEach(s => {
                html += `
                    <div class="agent-card" style="background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;padding:20px;">
                        <div class="agent-card-header">
                            <span class="agent-name" style="font-size:15px;color:#0f172a;">💡 ${s.title}</span>
                            <span class="agent-status-badge" style="background:#e0e7ff;color:#4f46e5;">${s.category}</span>
                        </div>
                        <p style="font-size:13px;color:#334155;margin-top:8px;line-height:1.5;">${s.suggestion}</p>
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:14px;font-size:12px;">
                            <span class="tag-badge" style="background:#dcfce7;color:#166534;">Impact: ${s.impact}</span>
                            <span style="color:#64748b;font-weight:600;">Status: ${s.action}</span>
                        </div>
                    </div>
                `;
            });
        }
        container.innerHTML = html;
    } catch (err) {
        console.error("Failed fetching AI suggestions:", err);
    }
}

let currentPostFilter = 'ALL';

async function filterPostsTab(status, btnElement) {
    currentPostFilter = status;
    document.querySelectorAll('.post-filter-btn').forEach(b => {
        b.style.background = '#f1f5f9';
        b.style.color = '#334155';
        b.classList.remove('active');
    });
    if (btnElement) {
        btnElement.style.background = status === 'PUBLISHED' ? '#22c55e' : '#4f46e5';
        btnElement.style.color = '#ffffff';
        btnElement.classList.add('active');
    }
    await loadPosts(status);
}

async function loadPosts(overrideStatus) {
    try {
        // Check URL param if not overridden
        const urlParams = new URLSearchParams(window.location.search);
        let filterStatus = overrideStatus || urlParams.get('filter') || currentPostFilter || 'ALL';

        const posts = await API.getPosts(filterStatus === 'ALL' ? 'ALL' : filterStatus);
        const overviewContainer = document.getElementById('overview-recent-posts');
        const gridContainer = document.getElementById('posts-grid-container');

        if (document.getElementById('overview-pub-count')) {
            const allPosts = await API.getPosts('ALL');
            document.getElementById('overview-pub-count').textContent = allPosts.filter(p => p.status === 'PUBLISHED').length;
        }

        let filteredPosts = posts;
        if (filterStatus !== 'ALL') {
            filteredPosts = posts.filter(p => p.status === filterStatus);
        }

        let cardsHtml = '';
        filteredPosts.forEach(p => {
            const mediaUrl = (p.media_urls && p.media_urls.length > 0) ? p.media_urls[0] : '';
            const isPublished = p.status === 'PUBLISHED';
            const statusBadgeStyle = isPublished
                ? 'background:#dcfce7;color:#166534;font-weight:700;'
                : (p.status === 'SCHEDULED' ? 'background:#e0e7ff;color:#4f46e5;' : 'background:#f1f5f9;color:#64748b;');
            
            const statusLabel = isPublished ? '🟢 PUBLISHED TO META' : p.status;

            cardsHtml += `
                <div class="post-card" style="background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden;margin-bottom:16px;">
                    ${mediaUrl ? `<img src="${mediaUrl}" class="post-media-preview" style="width:100%;height:260px;object-fit:cover;" alt="post visual">` : `<div class="post-media-preview" style="height:200px;display:flex;align-items:center;justify-content:center;background:#f8fafc;color:#64748b;">🎨 Visual Graphic Asset</div>`}
                    <div class="post-card-body" style="padding:18px;">
                        <div class="post-tag-row" style="display:flex;gap:8px;margin-bottom:10px;">
                            <span class="tag-badge" style="${statusBadgeStyle}">${statusLabel}</span>
                            <span class="tag-badge" style="background:#e0e7ff;color:#4f46e5;">FB & IG • ${p.media_type}</span>
                        </div>
                        <h4 class="post-title" style="font-size:16px;font-weight:700;color:#0f172a;margin-bottom:8px;">${p.title}</h4>
                        <p class="post-hook" style="font-size:13px;font-weight:600;color:#4f46e5;margin-bottom:8px;">"${p.hook}"</p>
                        <p style="font-size:13px;color:#334155;line-height:1.5;margin-bottom:10px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;">${p.caption}</p>
                        <p class="post-hashtags" style="font-size:12px;color:#0284c7;font-weight:600;">${p.hashtags}</p>
                    </div>
                </div>
            `;
        });

        if (gridContainer) {
            gridContainer.innerHTML = cardsHtml || `<div style="color:#64748b;grid-column:1/-1;padding:40px;text-align:center;background:#fff;border-radius:16px;border:1px solid #e2e8f0;">No ${filterStatus.toLowerCase()} posts found. Click "Run AI Cycle Now" to publish new content!</div>`;
        }
        if (overviewContainer) {
            overviewContainer.innerHTML = cardsHtml ? cardsHtml.slice(0, 3) : '<div style="color:#64748b;padding:20px;background:#fff;border-radius:12px;border:1px solid #e2e8f0;width:100%;">No posts published yet. Connect Facebook and run AI cycle!</div>';
        }
    } catch (err) {
        console.error("Failed loading posts:", err);
    }
}


async function loadAnalytics() {
    try {
        const ana = await API.getAnalyticsOverview();
        if (document.getElementById('kpi-reach')) document.getElementById('kpi-reach').textContent = (ana.total_reach || 0).toLocaleString();
        if (document.getElementById('kpi-engagement')) document.getElementById('kpi-engagement').textContent = `${(ana.avg_engagement_rate || 0).toFixed(1)}%`;
        if (document.getElementById('kpi-shares-saves')) document.getElementById('kpi-shares-saves').textContent = ((ana.total_shares || 0) + (ana.total_saves || 0)).toLocaleString();
        if (document.getElementById('kpi-followers')) document.getElementById('kpi-followers').textContent = `${ana.total_followers || 0}`;
    } catch (err) {
        console.error("Failed loading analytics:", err);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const targetForm = document.getElementById('form-page-target');
    if (targetForm) {
        targetForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const pageId = document.getElementById('modal-page-id').value;
            const pageAbout = document.getElementById('page-about').value;
            const targetAudience = document.getElementById('target-audience').value;
            const growthGoal = document.getElementById('growth-goal').value;
            const toneOfVoice = document.getElementById('tone-of-voice').value;
            const pageCategory = document.getElementById('page-category-modal').value;
            const customInstructions = document.getElementById('custom-instructions').value;

            try {
                const res = await fetch(`/api/setup/pages/${pageId}/target`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        page_about: pageAbout,
                        target_audience: targetAudience,
                        growth_goal: growthGoal,
                        tone_of_voice: toneOfVoice,
                        page_category: pageCategory,
                        custom_instructions: customInstructions
                    })
                });


                if (res.ok) {
                    closeTargetModal();
                    triggerPagePipeline(pageId, document.getElementById('modal-page-name').textContent, null, pageAbout);
                } else {
                    const data = await res.json();
                    alert(data.detail || 'Failed saving growth strategy.');
                }
            } catch (err) {
                console.error("Failed saving page target:", err);
            }
        });
    }
});

