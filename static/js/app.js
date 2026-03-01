// ==========================================
// Wolfclaw SPA (Single Page Application) Logic
// ==========================================

const API_BASE = '/api';

// --- State Management ---
let currentUser = null;
let activeBots = {};
let chatMessages = [];
let chatBotId = null;
let sshPemContent = '';
let eli5Mode = localStorage.getItem('wolfclaw-eli5') === 'true';

function toggleELI5(enabled) {
    eli5Mode = enabled;
    localStorage.setItem('wolfclaw-eli5', enabled);
}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    // Check Theme Preference
    const savedTheme = localStorage.getItem('wolfclaw-theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('theme-dark');
        document.body.classList.remove('theme-light');
    }

    // Theme Toggle Handler
    document.getElementById('theme-toggle').addEventListener('click', () => {
        if (document.body.classList.contains('theme-light')) {
            document.body.classList.replace('theme-light', 'theme-dark');
            localStorage.setItem('wolfclaw-theme', 'dark');
        } else {
            document.body.classList.replace('theme-dark', 'theme-light');
            localStorage.setItem('wolfclaw-theme', 'light');
        }
    });

    // Logout Handler
    document.getElementById('logout-btn').addEventListener('click', () => {
        localStorage.removeItem('wolfclaw-auth');
        currentUser = null;
        showAuth();
    });

    // Navigation Handlers
    document.querySelectorAll('.nav-item').forEach(el => {
        el.addEventListener('click', (e) => {
            e.preventDefault();
            const viewId = el.getAttribute('data-view');
            switchView(viewId);

            // Highlight active side-nav
            document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
            el.classList.add('active');
        });
    });

    // Bind Forms
    document.getElementById('login-form').addEventListener('submit', handleLogin);
    document.getElementById('register-form').addEventListener('submit', handleRegister);
    document.getElementById('forgot-form').addEventListener('submit', handleRecovery);
    document.getElementById('new-bot-form').addEventListener('submit', handleCreateBot);

    document.querySelectorAll('.api-key-form').forEach(form => {
        form.addEventListener('submit', handleSaveApiKey);
    });

    // PEM File Upload Handler
    const pemInput = document.getElementById('ssh-pem-file');
    if (pemInput) {
        pemInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (ev) => {
                    sshPemContent = ev.target.result;
                    document.getElementById('ssh-pem-status').innerHTML = '<i class="fa-solid fa-check" style="color:var(--success-color);"></i> PEM loaded';
                };
                reader.readAsText(file);
            }
        });
    }

    // Check Auto-Login
    checkAuth();
});

// --- View Rendering ---
function switchAuthView(viewName) {
    document.getElementById('login-view').classList.add('hidden');
    document.getElementById('register-view').classList.add('hidden');
    document.getElementById('forgot-view').classList.add('hidden');
    document.getElementById(`${viewName}-view`).classList.remove('hidden');
}

function showAuth() {
    document.getElementById('auth-container').classList.remove('hidden');
    document.getElementById('app-container').classList.add('hidden');
    switchAuthView('login');
}

function showApp() {
    document.getElementById('auth-container').classList.add('hidden');
    document.getElementById('app-container').classList.remove('hidden');
    document.getElementById('current-user-email').innerText = currentUser.email;
    loadDashboard();
    checkLocalAI();
}

function switchView(viewName) {
    document.querySelectorAll('.view-panel').forEach(panel => {
        panel.classList.add('hidden');
        panel.classList.remove('active');
    });
    const activePanel = document.getElementById(`view-${viewName}`);
    if (activePanel) {
        activePanel.classList.remove('hidden');
        activePanel.classList.add('active');
    }

    // Trigger data loads
    if (viewName === 'manage-bots') loadBots();
    if (viewName === 'settings') loadSettings();
    if (viewName === 'chat') loadChatBots();
    if (viewName === 'remote-servers') loadSSHServers();
    if (viewName === 'bot-profiles') loadProfileBots();
    if (viewName === 'channels') loadChannelBots();
    if (viewName === 'ai-roles') loadTemplateGallery();
    if (viewName === 'saved') loadSavedResponses();
    if (viewName === 'war-room') loadWarRoom();
    if (viewName === 'wallet') loadWalletBotsDropdown();
}

function toggleNewBotForm() {
    const form = document.getElementById('new-bot-form-container');
    form.classList.toggle('hidden');
}

// --- Password Visibility Toggle ---
function togglePasswordVisibility(inputId, icon) {
    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
    } else {
        input.type = 'password';
        icon.classList.replace('fa-eye', 'fa-eye-slash');
    }
}

// ==========================================
// AUTH UTILS
// ==========================================

function getAuthHeader() {
    if (currentUser && currentUser.session_id) {
        return { 'Authorization': `Bearer ${currentUser.session_id}` };
    }
    return {};
}

// ==========================================
// AUTH API
// ==========================================

function checkAuth() {
    const saved = localStorage.getItem('wolfclaw-auth');
    if (saved) {
        currentUser = JSON.parse(saved);
        showApp();
    } else {
        showAuth();
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    try {
        const resp = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await resp.json();
        if (resp.ok && data.status === 'success') {
            currentUser = { id: data.user_id, email: data.email, session_id: data.session_id };
            localStorage.setItem('wolfclaw-auth', JSON.stringify(currentUser));
            showApp();
        } else {
            if (resp.status === 401) {
                alert('Invalid email or password.');
            } else if (resp.status === 500) {
                alert('Internal Server Error. Please check logs at ~/.wolfclaw/wolfclaw.log');
            } else {
                alert(data.detail || 'Login failed.');
            }
        }
    } catch (err) {
        console.error("Login Fetch Error:", err);
        alert('Connection error: Is the backend running?');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const email = document.getElementById('reg-email').value;
    const pwd1 = document.getElementById('reg-password').value;
    const pwd2 = document.getElementById('reg-confirm').value;
    if (pwd1 !== pwd2) return alert("Passwords don't match!");

    try {
        const resp = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, password: pwd1 })
        });

        const data = await resp.json();

        if (resp.ok && data.status === 'success') {
            alert(`Account created successfully!\n\nYOUR MASTER RECOVERY KEY:\n${data.recovery_key}\n\nSAVE THIS NOW. You will need it if you ever forget your password. We cannot email you a reset link.`);
            switchAuthView('login');
            document.getElementById('login-email').value = email;
            document.getElementById('login-password').value = '';
        } else {
            alert(data.detail || "Registration failed. Email might already exist.");
        }
    } catch (err) {
        console.error("Register Fetch Error:", err);
        alert('Connection error: Is the backend running?');
    }
}

async function handleRecovery(e) {
    e.preventDefault();
    const email = document.getElementById('forgot-email').value;
    const recovery_key = document.getElementById('forgot-key').value;
    const new_password = document.getElementById('forgot-new-password').value;

    try {
        const resp = await fetch(`${API_BASE}/auth/reset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, recovery_key, new_password })
        });
        const data = await resp.json();

        if (resp.ok && data.status === 'success') {
            alert(data.message);
            switchAuthView('login');
        } else {
            alert(data.detail || 'Recovery failed. Invalid key.');
        }
    } catch (err) {
        alert('System Error.');
    }
}

// ==========================================
// BOT MANAGEMENT
// ==========================================

async function loadBots() {
    const resp = await fetch(`${API_BASE}/bots/`, {
        headers: getAuthHeader()
    });
    const data = await resp.json();
    if (resp.ok) {
        activeBots = data.bots;
        document.getElementById('dash-bot-count').innerText = Object.keys(activeBots).length;
        renderBotTable();
    }
}

async function renderBotTable() {
    const tbody = document.getElementById('bot-table-body');
    tbody.innerHTML = '';

    // Fetch live Telegram worker status
    let workerStatus = {};
    try {
        const statusResp = await fetch(`${API_BASE}/channels/telegram/status`, {
            headers: getAuthHeader()
        });
        const statusData = await statusResp.json();
        if (statusResp.ok) workerStatus = statusData.workers || {};
    } catch (e) { }

    for (const [id, bot] of Object.entries(activeBots)) {
        const isRunning = workerStatus[id] && workerStatus[id].alive;
        const hasTelegram = bot.telegram_token && bot.telegram_token.length > 5;

        let statusBadge = '';
        if (hasTelegram) {
            statusBadge = isRunning
                ? '<span style="background:var(--success-color); color:#fff; padding:2px 10px; border-radius:12px; font-size:0.8em;">LIVE (TG)</span>'
                : `<div style="display:flex; align-items:center; gap:5px;">
                    <span style="background:var(--danger-color); color:#fff; padding:2px 10px; border-radius:12px; font-size:0.8em;" title="Telegram worker is not running. Go to Deploy Channels to start it.">WORKER STOPPED</span>
                    <a href="#" onclick="switchView('deploy-channels')" style="font-size:0.75em; color:var(--primary-color);">Manage</a>
                   </div>`;
        } else {
            statusBadge = '<span style="background:rgba(88,166,255,0.15); color:var(--primary-color); padding:2px 10px; border-radius:12px; font-size:0.8em; border:1px solid rgba(88,166,255,0.3);">LOCAL AI</span>';
        }

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${bot.name}</strong></td>
            <td><span style="font-size:0.85em; color:var(--text-muted);">${bot.model}</span></td>
            <td>${statusBadge}</td>
            <td>
                <button class="btn btn-sm btn-danger" onclick="deleteBot('${id}')">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    }
}

async function handleCreateBot(e) {
    e.preventDefault();
    const name = document.getElementById('new-bot-name').value;
    const model = document.getElementById('new-bot-model').value;
    const prompt = document.getElementById('new-bot-prompt').value;

    const resp = await fetch(`${API_BASE}/bots/`, {
        method: 'POST',
        headers: {
            ...getAuthHeader(),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name, model, prompt })
    });

    if (resp.ok) {
        toggleNewBotForm();
        loadBots();
        alert(`Bot "${name}" created!`);
    } else {
        const data = await resp.json();
        alert(data.detail || "Failed to create bot.");
    }
}

// Consolidated deleteBot into the enhanced version at line 1109


// ==========================================
// CHAT
let currentChatId = null; // Phase 11 tracking

async function loadChatBots() {
    try {
        const resp = await fetch(`${API_BASE}/chat/bots`, {
            headers: getAuthHeader()
        });
        const data = await resp.json();
        if (resp.ok) {
            const select = document.getElementById('chat-bot-select');
            select.innerHTML = '<option value="">-- Select a Bot --</option>';
            data.bots.forEach(b => {
                const opt = document.createElement('option');
                opt.value = b.id;
                opt.text = b.name;
                select.appendChild(opt);
            });

            // Set first bot as default and click start to bypass selection
            if (data.bots.length > 0) {
                select.value = data.bots[0].id;
                setTimeout(startNewChat, 100);
            }
        }
    } catch (err) {
        console.error("Error loading chat bots:", err);
    }
}

function startNewChat() {
    const select = document.getElementById('chat-bot-select');
    chatBotId = select.value;
    if (!chatBotId) return alert("Please select a bot first!");

    const botName = select.options[select.selectedIndex].text;
    document.getElementById('chat-bot-name').innerText = botName;
    document.getElementById('chat-no-bot').classList.add('hidden');
    document.getElementById('chat-active').classList.remove('hidden');

    // Reset state for new chat
    chatMessages = [];
    currentChatId = null;
    document.getElementById('chat-messages').innerHTML = '';

    // Reset doc context
    const docSelect = document.getElementById('chat-document-context');
    if (docSelect) docSelect.value = "";

    // Reload sidebar
    loadChatHistorySidebar();
}

function endChat() {
    chatBotId = null;
    chatMessages = [];
    currentChatId = null;
    document.getElementById('chat-no-bot').classList.remove('hidden');
    document.getElementById('chat-active').classList.add('hidden');
    document.getElementById('chat-messages').innerHTML = '';
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const userMsg = input.value.trim();
    if (!userMsg || !chatBotId) return;

    input.value = '';

    // If ELI5 mode is on, prepend simplification instruction
    let msgToSend = userMsg;
    if (eli5Mode) {
        msgToSend = userMsg + '\n\n[SYSTEM NOTE: Respond using simple words a 10-year-old would understand. Use emojis. Keep answers under 3-4 sentences. No jargon.]';
    }

    chatMessages.push({ role: 'user', content: msgToSend });
    appendChatBubble('user', userMsg);

    // Show thinking indicator
    const thinkingId = appendChatBubble('assistant', '<i>Thinking...</i>');

    try {
        const resp = await fetch(`${API_BASE}/chat/send`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ bot_id: chatBotId, messages: chatMessages })
        });

        const data = await resp.json();

        // Remove thinking indicator
        const thinkingEl = document.getElementById(thinkingId);
        if (thinkingEl) thinkingEl.remove();

        if (resp.ok) {
            // Render any tools that ran during the thought process
            if (data.tool_messages && data.tool_messages.length > 0) {
                data.tool_messages.forEach(tm => {
                    const tName = tm.name || "Tool";
                    const content = tm.content || "";

                    if (content.includes("SCREENSHOT_CAPTURED:")) {
                        const pathMatch = content.split("SCREENSHOT_CAPTURED:")[1];
                        if (pathMatch) {
                            const imgPath = encodeURIComponent(pathMatch.trim());
                            appendToolBubble(tName, `<img src="${API_BASE}/chat/media?path=${imgPath}" style="max-width:100%; border-radius:8px; margin-top:5px; border:1px solid var(--border-color);" />`);
                        }
                    } else {
                        // Safe rendering for code
                        const safeContent = content.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                        let trunc = safeContent.length > 2000 ? safeContent.substring(0, 2000) + '\n... [TRUNCATED]' : safeContent;

                        const html = `
                            <details style="background:var(--body-bg, #f4f6f8); padding:8px 12px; border-radius:6px; font-family:var(--font-family, Inter); font-size:0.85em; cursor:pointer; border:1px solid var(--border-color);">
                                <summary style="font-weight:600; color:var(--primary-color);"><i class="fa-solid fa-wrench"></i> ${tName} output</summary>
                                <pre style="margin-top:8px; white-space:pre-wrap; max-height:250px; overflow-y:auto; font-family:monospace; background:transparent;">${trunc}</pre>
                            </details>
                        `;
                        appendToolBubble(tName, html);
                    }
                });
            }

            chatMessages.push({ role: 'assistant', content: data.reply });
            appendChatBubble('assistant', data.reply);

            // Update current chat ID if newly created
            if (data.chat_id && data.chat_id !== currentChatId) {
                currentChatId = data.chat_id;
                loadChatHistorySidebar(); // Refresh sidebar to show new chat
            }

        } else {
            appendChatBubble('assistant', `Error: ${data.detail || 'Unknown error'}`);
        }
    } catch (err) {
        const thinkingEl = document.getElementById(thinkingId);
        if (thinkingEl) thinkingEl.remove();
        appendChatBubble('assistant', 'Connection error. Is the backend running?');
    }
}

function appendChatBubble(role, content) {
    const container = document.getElementById('chat-messages');
    const id = 'msg-' + Date.now() + Math.random();
    const div = document.createElement('div');
    div.id = id;
    div.style.marginBottom = '12px';
    div.style.padding = '10px 14px';
    div.style.borderRadius = '12px';
    div.style.maxWidth = '80%';
    div.style.wordWrap = 'break-word';
    div.style.whiteSpace = 'pre-wrap';

    if (role === 'user') {
        div.style.marginLeft = 'auto';
        div.style.background = 'var(--primary-color)';
        div.style.color = '#fff';
    } else {
        div.style.marginRight = 'auto';
        div.style.background = 'var(--border-color)';
        div.style.color = 'var(--text-color)';
    }

    div.innerHTML = content;

    // Add action buttons for AI responses (not for "Thinking..." indicators)
    if (role === 'assistant' && !content.includes('Thinking...') && !content.includes('⚠️')) {
        const actionsDiv = document.createElement('div');
        actionsDiv.style.cssText = 'display:flex; gap:6px; margin-top:8px; flex-wrap:wrap; border-top:1px solid rgba(128,128,128,0.2); padding-top:6px;';
        actionsDiv.innerHTML = `
            <button onclick="copyResponse(this)" class="chat-action-btn" title="Copy to clipboard">📋 Copy</button>
            <button onclick="refineResponse('Make this shorter — 2-3 sentences max')" class="chat-action-btn" title="Make shorter">✂️ Shorter</button>
            <button onclick="refineResponse('Rewrite this in a formal, professional tone')" class="chat-action-btn" title="Make formal">📝 Formal</button>
            <button onclick="refineResponse('Translate this to Hindi')" class="chat-action-btn" title="Translate">🌍 Hindi</button>
            <button onclick="refineResponse('Explain this like I am 5 years old, using simple words and emojis')" class="chat-action-btn" title="Simplify">🧒 ELI5</button>
            <button onclick="saveToFavorites(this)" class="chat-action-btn" title="Save this response">⭐ Save</button>
        `;
        div.appendChild(actionsDiv);
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

function appendToolBubble(toolName, contentHtml) {
    const container = document.getElementById('chat-messages');
    const id = 'msg-' + Date.now() + Math.random();
    const div = document.createElement('div');
    div.id = id;
    div.style.marginBottom = '12px';
    div.style.padding = '4px 14px';
    div.style.maxWidth = '85%';
    div.style.wordWrap = 'break-word';

    div.style.marginRight = 'auto';
    div.style.background = 'transparent';
    div.style.borderLeft = '3px solid var(--primary-color)';

    div.innerHTML = contentHtml;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

// --- Chat Action Helpers ---

function copyResponse(btn) {
    // Walk up to the message bubble and get text content (excluding buttons)
    const bubble = btn.closest('[id^="msg-"]');
    if (!bubble) return;

    // Clone, remove action buttons, get text
    const clone = bubble.cloneNode(true);
    const actions = clone.querySelector('[style*="border-top"]');
    if (actions) actions.remove();
    const text = clone.textContent.trim();

    navigator.clipboard.writeText(text).then(() => {
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = '📋 Copy'; }, 1500);
    });
}

async function refineResponse(instruction) {
    if (!chatBotId) return;

    // Get the last assistant message
    const lastAssistant = [...chatMessages].reverse().find(m => m.role === 'assistant');
    if (!lastAssistant) return;

    // Add the refinement request as a user message
    const refinementMsg = `${instruction}: "${lastAssistant.content}"`;
    chatMessages.push({ role: 'user', content: refinementMsg });
    appendChatBubble('user', instruction);

    const thinkingId = appendChatBubble('assistant', '<i>Refining...</i>');

    try {
        const resp = await fetch(`${API_BASE}/chat/send`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ bot_id: chatBotId, messages: chatMessages })
        });
        const data = await resp.json();

        const thinkingEl = document.getElementById(thinkingId);
        if (thinkingEl) thinkingEl.remove();

        if (resp.ok) {
            chatMessages.push({ role: 'assistant', content: data.reply });
            appendChatBubble('assistant', data.reply);
        } else {
            appendChatBubble('assistant', '⚠️ Refinement failed.');
        }
    } catch (err) {
        const thinkingEl = document.getElementById(thinkingId);
        if (thinkingEl) thinkingEl.remove();
        appendChatBubble('assistant', '⚠️ Connection error.');
    }
}

function exportChatToPDF() {
    window.print();
}

// ==========================================
// V3: SAVED RESPONSES (FAVORITES)
// ==========================================

async function saveToFavorites(btn) {
    const bubbleContent = btn.parentElement.previousSibling.textContent || btn.parentElement.previousSibling.innerText;
    const botName = document.getElementById('chat-bot-name').innerText;

    btn.innerHTML = 'Saving...';
    btn.disabled = true;

    try {
        const resp = await fetch(`${API_BASE}/favorites/`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ bot_name: botName, content: bubbleContent })
        });

        if (resp.ok) {
            btn.innerHTML = 'Saved';
            btn.style.color = 'var(--success-color)';
            btn.style.borderColor = 'var(--success-color)';
            btn.style.background = 'rgba(63, 185, 80, 0.1)';
            loadSavedResponses(); // Refresh background
        } else {
            btn.innerHTML = 'Failed';
            btn.disabled = false;
        }
    } catch (err) {
        btn.innerHTML = '❌ Error';
        btn.disabled = false;
    }
}

async function loadSavedResponses() {
    const gallery = document.getElementById('saved-responses-gallery');
    if (!gallery) return;

    gallery.innerHTML = '<p style="color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Loading saved responses...</p>';

    try {
        const resp = await fetch(`${API_BASE}/favorites`, {
            headers: getAuthHeader()
        });
        const data = await resp.json();
        if (resp.ok) {
            renderSavedGallery(data.favorites);
        } else {
            gallery.innerHTML = '<p style="color:var(--danger-color);">Failed to load favorites.</p>';
        }
    } catch (err) {
        gallery.innerHTML = '<p style="color:var(--danger-color);">Connection error.</p>';
    }
}

function renderSavedGallery(favorites) {
    const gallery = document.getElementById('saved-responses-gallery');
    gallery.innerHTML = '';

    if (favorites.length === 0) {
        gallery.innerHTML = '<p style="color:var(--text-muted);">No saved responses yet. Click the ⭐ Save button under an AI response in Chat.</p>';
        return;
    }

    favorites.forEach(fav => {
        const card = document.createElement('div');
        card.className = 'card template-card';
        card.style.cssText = 'position:relative; display:flex; flex-direction:column;';

        const dateStr = new Date(fav.created_at).toLocaleString();

        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px; border-bottom:1px solid rgba(128,128,128,0.2); padding-bottom:8px;">
                <div>
                    <h3 style="margin:0; font-size:1rem; color:var(--primary-color);"><i class="fa-solid fa-robot"></i> ${fav.bot_name}</h3>
                    <span style="font-size:0.75rem; color:var(--text-muted);">${dateStr}</span>
                </div>
                <button class="icon-btn" onclick="deleteSavedResponse('${fav.id}')" title="Delete this saved response" style="color:var(--danger-color);">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
            <div style="font-size:0.9em; line-height:1.5; color:var(--text-color); white-space:pre-wrap; flex:1; overflow-y:auto; max-height:200px;">${fav.content}</div>
            <button class="btn btn-sm btn-secondary" onclick="navigator.clipboard.writeText(this.previousElementSibling.innerText); this.innerHTML='<i class=\\\'fa-solid fa-check\\\'></i> Copied!';" style="margin-top:10px;">
                <i class="fa-regular fa-copy"></i> Copy Text
            </button>
        `;
        gallery.appendChild(card);
    });
}

async function deleteSavedResponse(favId) {
    if (!confirm('Are you sure you want to delete this saved response?')) return;

    try {
        const resp = await fetch(`${API_BASE}/favorites/${favId}`, {
            method: 'DELETE',
            headers: getAuthHeader()
        });
        if (resp.ok) {
            loadSavedResponses();
        } else {
            alert('Failed to delete.');
        }
    } catch (err) {
        alert('Connection error.');
    }
}

// ==========================================
// REMOTE SERVERS (SSH)
// ==========================================

let sshServers = [];
let activeSshServerId = null;

async function loadSSHServers() {
    try {
        const resp = await fetch(`${API_BASE}/remote/servers`, {
            headers: getAuthHeader()
        });
        const data = await resp.json();
        if (resp.ok && data.servers) {
            sshServers = data.servers;
            renderSSHServerList();
        }
    } catch (err) {
        console.error("Error loading SSH servers:", err);
    }
}

function renderSSHServerList() {
    const listDiv = document.getElementById('ssh-server-list');
    listDiv.innerHTML = '';

    if (sshServers.length === 0) {
        listDiv.innerHTML = '<p style="color:var(--text-muted); font-size:0.9em; text-align:center; margin-top:20px;">No servers added.</p>';
        if (activeSshServerId !== 'new') {
            document.getElementById('ssh-server-details-panel').classList.add('hidden');
        }
        return;
    }

    sshServers.forEach(server => {
        const btn = document.createElement('div');
        const isActive = server.id === activeSshServerId;
        btn.className = 'card';
        btn.style.cursor = 'pointer';
        btn.style.padding = '10px 15px';
        btn.style.marginBottom = '8px';
        btn.style.transition = 'all 0.2s ease';
        if (isActive) {
            btn.style.borderLeft = '4px solid var(--primary-color)';
            btn.style.background = 'var(--card-bg)';
            btn.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
        } else {
            btn.style.borderLeft = '4px solid transparent';
            btn.style.background = 'transparent';
            btn.style.border = '1px solid var(--border-color)';
        }

        btn.innerHTML = `
            <div style="font-weight:600; font-size:0.95em; color:var(--text-color);">${server.name || 'Unnamed Server'}</div>
            <div style="font-size:0.8em; color:var(--text-muted); margin-top:4px;">
                <i class="fa-solid fa-server"></i> ${server.host || 'No IP'}
            </div>
        `;
        btn.onclick = () => selectSSHServer(server.id);
        listDiv.appendChild(btn);
    });

    // Auto-select first if none selected and not creating new
    if (!activeSshServerId && sshServers.length > 0) {
        selectSSHServer(sshServers[0].id);
    }
}

function createNewSSHServer() {
    activeSshServerId = 'new';

    document.getElementById('ssh-id').value = '';
    document.getElementById('ssh-name').value = 'New Server';
    document.getElementById('ssh-host').value = '';
    document.getElementById('ssh-port').value = '22';
    document.getElementById('ssh-user').value = 'ubuntu';
    document.getElementById('ssh-password').value = '';
    document.getElementById('ssh-password').placeholder = 'SSH password';
    document.getElementById('ssh-pem-status').innerHTML = '';
    sshPemContent = null;

    document.getElementById('ssh-test-result').innerHTML = '';
    document.getElementById('ssh-chat-messages').innerHTML = '';

    // Hide delete button for unsaved server
    const delBtn = document.getElementById('ssh-delete-btn');
    if (delBtn) delBtn.style.display = 'none';

    renderSSHServerList();
    document.getElementById('ssh-server-details-panel').classList.remove('hidden');
}

function selectSSHServer(id) {
    const server = sshServers.find(s => s.id === id);
    if (!server) return;

    activeSshServerId = id;

    // Show delete button
    const delBtn = document.getElementById('ssh-delete-btn');
    if (delBtn) delBtn.style.display = 'block';

    document.getElementById('ssh-id').value = server.id || '';
    document.getElementById('ssh-name').value = server.name || 'Unnamed Server';
    document.getElementById('ssh-host').value = server.host || '';
    document.getElementById('ssh-port').value = server.port || '22';
    document.getElementById('ssh-user').value = server.user || 'ubuntu';

    document.getElementById('ssh-password').value = '';
    if (server.has_password) {
        document.getElementById('ssh-password').placeholder = '••••••• (saved)';
    } else {
        document.getElementById('ssh-password').placeholder = 'SSH password';
    }

    if (server.has_key) {
        document.getElementById('ssh-pem-status').innerHTML = '<i class="fa-solid fa-check" style="color:var(--success-color);"></i> PEM key saved';
    } else {
        document.getElementById('ssh-pem-status').innerHTML = '';
    }

    sshPemContent = null;
    document.getElementById('ssh-test-result').innerHTML = '';
    document.getElementById('ssh-chat-messages').innerHTML = '';

    document.getElementById('ssh-server-details-panel').classList.remove('hidden');

    renderSSHServerList();
}

async function saveSSHConfig() {
    const id = document.getElementById('ssh-id').value;
    const name = document.getElementById('ssh-name').value;
    const host = document.getElementById('ssh-host').value;
    const port = document.getElementById('ssh-port').value;
    const user = document.getElementById('ssh-user').value;
    const password = document.getElementById('ssh-password').value;

    if (!host) return alert("Please enter an IP or hostname!");
    if (!name) return alert("Please enter a sequence name for the server!");

    try {
        const resp = await fetch(`${API_BASE}/remote/servers`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ id: id || null, name, host, port, user, password, key_content: sshPemContent })
        });
        const data = await resp.json();
        if (resp.ok) {
            alert('Server configuration saved!');
            await loadSSHServers();
            selectSSHServer(data.id);
        } else {
            alert(data.detail || 'Failed to save.');
        }
    } catch (err) {
        alert('Connection error.');
    }
}

async function deleteSSHServer() {
    if (!activeSshServerId || activeSshServerId === 'new') return;
    if (!confirm("Are you sure you want to permanently delete this SSH server? This cannot be undone.")) return;

    try {
        const resp = await fetch(`${API_BASE}/remote/servers/${activeSshServerId}`, {
            method: 'DELETE',
            headers: getAuthHeader()
        });
        if (resp.ok) {
            activeSshServerId = null;
            await loadSSHServers();
        } else {
            alert("Failed to delete server.");
        }
    } catch (err) {
        alert("Connection error.");
    }
}

async function testSSHConnection() {
    const host = document.getElementById('ssh-host').value;
    const port = document.getElementById('ssh-port').value;
    const user = document.getElementById('ssh-user').value;
    const password = document.getElementById('ssh-password').value;
    const resultDiv = document.getElementById('ssh-test-result');

    if (!host) return alert("Enter a hostname first!");

    resultDiv.innerHTML = '<p style="color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Testing connection...</p>';

    try {
        const resp = await fetch(`${API_BASE}/remote/test`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ host, port, user, password, key_content: sshPemContent })
        });
        const data = await resp.json();
        if (resp.ok) {
            resultDiv.innerHTML = `
                <div class="card" style="border-left: 4px solid var(--success-color);">
                    <h3 style="color:var(--success-color);"><i class="fa-solid fa-check-circle"></i> Connected!</h3>
                    <p><strong>Hostname:</strong> ${data.hostname}</p>
                    <p><strong>System:</strong> ${data.system_info || 'N/A'}</p>
                    <p><strong>Disk:</strong> ${data.disk_info || 'N/A'}</p>
                </div>`;
        } else {
            resultDiv.innerHTML = `<div class="card" style="border-left: 4px solid var(--danger-color);"><p style="color:var(--danger-color);">❌ ${data.detail}</p></div>`;
        }
    } catch (err) {
        resultDiv.innerHTML = `<p style="color:var(--danger-color);">❌ Connection error.</p>`;
    }
}

async function spawnDedicatedSshBot() {
    const token = document.getElementById('dedicated-ssh-token').value.trim();
    if (!token) return alert("Please enter a Telegram Bot Token first!");

    if (!activeSshServerId || activeSshServerId === 'new') {
        return alert("Please save the server configuration first before deploying a bot.");
    }

    const serverName = document.getElementById('ssh-name').value;
    const serverHost = document.getElementById('ssh-host').value;

    const payload = {
        name: `SSH Commander: ${serverName}`,
        model: "openai/gpt-4o",
        prompt: `You are my dedicated DevOps Server Manager. Your ONLY job is to manage the remote SSH server "${serverName}" at ${serverHost}. You have access to the \`run_remote_ssh_command\` tool. When asked to do something on the server, you MUST use that tool. Do not try to manage the local desktop. Ensure all actions are safe and verify paths dynamically using 'ls' before executing potentially dangerous commands.`,
        fallback_models: ["anthropic/claude-3-5-sonnet-20241022", "google/gemini-2.5-pro"]
    };

    try {
        const botResp = await fetch(`${API_BASE}/bots`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        const botData = await botResp.json();

        if (!botResp.ok) throw new Error(botData.detail || "Failed to create bot.");
        const botId = botData.bot_id;

        const tgResp = await fetch(`${API_BASE}/channels/telegram/token`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ bot_id: botId, token: token })
        });

        if (!tgResp.ok) throw new Error("Bot created, but failed to save Telegram token.");

        document.getElementById('dedicated-ssh-token').value = "";
        alert("✅ Dedicated SSH Commander Bot successfully spawned!\n\nIt is specifically instructed to exclusively manage the " + serverName + " (" + serverHost + ") server.\n\nYou can now go to Telegram and message your bot directly.");

        loadProfileBots();
        loadArmyBots();
        loadChatBots();
    } catch (err) {
        alert("Error: " + err.message);
    }
}

// Embedded SSH Chat functionality
let embeddedChatMessages = [];

async function sendSSHChatMessage() {
    const input = document.getElementById('ssh-chat-input');
    const userMsg = input.value.trim();
    if (!userMsg || !activeSshServerId || activeSshServerId === 'new') {
        if (activeSshServerId === 'new') alert("Please save your server configuration before chatting!");
        return;
    }

    input.value = '';
    embeddedChatMessages.push({ role: 'user', content: userMsg });
    appendEmbeddedBubble('user', userMsg);

    const serverHost = document.getElementById('ssh-host').value;

    if (Object.keys(activeBots).length === 0) {
        appendEmbeddedBubble('assistant', '⚠️ You must have at least one AI bot created in "Manage Bots" to chat.');
        return;
    }

    const fallbackBotId = Object.keys(activeBots)[0];
    const thinkingId = appendEmbeddedBubble('assistant', '<i>Executing on server...</i>');

    const directiveMsg = `[SYSTEM OVERRIDE DIRECTIVE: Use the run_remote_ssh_command tool to execute commands on the remote server exactly as I request below. Focus ONLY on the remote server at IP: ${serverHost}]\n\nUSER REQUEST: ${userMsg}`;

    const tempMessages = [
        ...embeddedChatMessages.slice(0, -1),
        { role: 'user', content: directiveMsg }
    ];

    try {
        const resp = await fetch(`${API_BASE}/chat/send`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ bot_id: fallbackBotId, messages: tempMessages })
        });

        const data = await resp.json();
        const thinkingEl = document.getElementById(thinkingId);
        if (thinkingEl) thinkingEl.remove();

        if (resp.ok) {
            if (data.tool_messages && data.tool_messages.length > 0) {
                data.tool_messages.forEach(tm => {
                    if (tm.name === "run_remote_ssh_command") {
                        const safeContent = (tm.content || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                        const html = `
                            <div style="background:#1e1e1e; color:#cfcfcf; padding:8px 12px; border-radius:6px; font-size:0.85em; margin-bottom:8px; border:1px solid #333;">
                                <div style="font-weight:600; color:#58a6ff; margin-bottom:5px;"><i class="fa-solid fa-terminal"></i> root@${serverHost}</div>
                                <pre style="white-space:pre-wrap; max-height:200px; overflow-y:auto; font-family:monospace; margin:0;">${safeContent}</pre>
                            </div>
                        `;
                        appendEmbeddedBubble('assistant', html, false);
                    }
                });
            }

            embeddedChatMessages.push({ role: 'assistant', content: data.reply });
            appendEmbeddedBubble('assistant', data.reply);
        } else {
            appendEmbeddedBubble('assistant', `⚠️ Error: ${data.detail || 'Unknown error'}`);
        }
    } catch (err) {
        const thinkingEl = document.getElementById(thinkingId);
        if (thinkingEl) thinkingEl.remove();
        appendEmbeddedBubble('assistant', '⚠️ Connection error.');
    }
}

function appendEmbeddedBubble(role, content, isStandard = true) {
    const container = document.getElementById('ssh-chat-messages');
    const id = 'emb-' + Date.now() + Math.random();
    const div = document.createElement('div');
    div.id = id;
    div.style.marginBottom = '8px';
    div.style.padding = isStandard ? '8px 12px' : '0';
    div.style.borderRadius = '8px';
    div.style.fontSize = '0.9em';
    div.style.maxWidth = '90%';
    div.style.wordWrap = 'break-word';

    if (role === 'user') {
        div.style.marginLeft = 'auto';
        div.style.background = 'var(--primary-color)';
        div.style.color = '#fff';
    } else {
        div.style.marginRight = 'auto';
        if (isStandard) {
            div.style.background = 'var(--card-bg)';
            div.style.border = '1px solid var(--border-color)';
        }
    }

    div.innerHTML = content;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

// ==========================================
// BOT PROFILES
// ==========================================

async function loadProfileBots() {
    try {
        const resp = await fetch(`${API_BASE}/chat/bots`);
        const data = await resp.json();
        if (resp.ok) {
            const select = document.getElementById('profile-bot-select');
            select.innerHTML = '<option value="">-- Select a Bot --</option>';
            data.bots.forEach(bot => {
                select.innerHTML += `<option value="${bot.id}">${bot.name}</option>`;
            });
        }
    } catch (err) {
        console.error("Error loading profile bots:", err);
    }
}

async function loadBotProfile() {
    const botId = document.getElementById('profile-bot-select').value;
    if (!botId) {
        document.getElementById('profile-editor-area').classList.add('hidden');
        const delBtn = document.getElementById('btn-delete-bot');
        if (delBtn) delBtn.style.display = 'none';
        return;
    }

    try {
        const resp = await fetch(`${API_BASE}/bots/${botId}/profile`, {
            headers: getAuthHeader()
        });
        const data = await resp.json();
        if (resp.ok) {
            document.getElementById('profile-soul').value = data.soul || '';
            document.getElementById('profile-user').value = data.user || '';
            document.getElementById('profile-memory').value = data.memory || '';
            document.getElementById('profile-editor-area').classList.remove('hidden');

            const delBtn = document.getElementById('btn-delete-bot');
            if (delBtn) delBtn.style.display = 'block';
        }
    } catch (err) {
        alert('Error loading bot profile.');
    }
}

async function deleteBot(targetId = null) {
    let botId = targetId;
    if (!botId) {
        botId = document.getElementById('profile-bot-select').value;
    }

    if (!botId) return;

    if (!confirm("WARNING: This will permanently delete this bot and ALL of its chat history, knowledge base documents, and scheduled tasks. This cannot be undone.\n\nAre you sure?")) {
        return;
    }

    try {
        const resp = await fetch(`${API_BASE}/bots/${botId}`, {
            method: 'DELETE',
            headers: getAuthHeader()
        });

        if (resp.ok) {
            // Clear editor if the deleted bot was open
            const select = document.getElementById('profile-bot-select');
            if (select.value === botId) {
                document.getElementById('profile-editor-area').classList.add('hidden');
                select.value = '';
                document.getElementById('btn-delete-bot').style.display = 'none';
            }

            // Reload all dropdowns and tables
            await loadBots();
            loadProfileBots();
            try { if (typeof renderArmyTable === 'function') renderArmyTable(); } catch (e) { }
            try { if (typeof loadKnowledgeBots === 'function') loadKnowledgeBots(); } catch (e) { }

            // If this was the active chat bot, clear the chat
            if (chatBotId === botId) {
                endChat();
            }

            alert('Bot deleted successfully.');
        } else {
            const err = await resp.json();
            alert('Error deleting bot: ' + JSON.stringify(err));
        }
    } catch (e) {
        alert("Failed to delete bot: " + e.message);
    }
}

async function saveBotProfile(filename) {
    const botId = document.getElementById('profile-bot-select').value;
    if (!botId) return;

    const content = filename === 'SOUL.md'
        ? document.getElementById('profile-soul').value
        : document.getElementById('profile-user').value;

    try {
        const resp = await fetch(`${API_BASE}/bots/${botId}/profile`, {
            method: 'PUT',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filename, content })
        });
        const data = await resp.json();
        if (resp.ok) alert(`✅ ${filename} saved!`);
        else alert(data.detail || 'Failed to save.');
    } catch (err) {
        alert('Connection error.');
    }
}

async function clearBotMemory() {
    const botId = document.getElementById('profile-bot-select').value;
    if (!botId) return;
    if (!confirm("Clear all memory? This cannot be undone.")) return;

    try {
        const resp = await fetch(`${API_BASE}/bots/${botId}/memory`, {
            method: 'DELETE',
            headers: getAuthHeader()
        });
        const data = await resp.json();
        if (resp.ok) {
            alert('Memory cleared!');
            loadBotProfile();
        }
    } catch (err) {
        alert('Error clearing memory.');
    }
}

// ==========================================
// TEMPLATE GALLERY (AI ROLES)
// ==========================================

let _templateCache = null;

async function loadTemplateGallery() {
    const gallery = document.getElementById('template-gallery');
    const filtersDiv = document.getElementById('template-category-filters');
    if (!gallery) return;

    // Use cached data if available
    if (_templateCache) {
        renderTemplateGallery(_templateCache);
        return;
    }

    gallery.innerHTML = '<p style="color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Loading templates...</p>';

    try {
        const resp = await fetch(`${API_BASE}/templates/`, {
            headers: getAuthHeader()
        });
        const data = await resp.json();
        if (resp.ok) {
            _templateCache = data;
            renderTemplateGallery(data);
        } else {
            gallery.innerHTML = '<p style="color:var(--danger-color);">Failed to load templates.</p>';
        }
    } catch (err) {
        gallery.innerHTML = '<p style="color:var(--danger-color);">Connection error.</p>';
    }
}

function renderTemplateGallery(data) {
    const gallery = document.getElementById('template-gallery');
    const filtersDiv = document.getElementById('template-category-filters');

    // Render category filter buttons
    filtersDiv.innerHTML = '<button class="btn btn-sm template-filter active" onclick="filterTemplates(\'all\')" data-cat="all" style="background:var(--accent-color); color:#fff;">🌟 All</button>';
    data.categories.forEach(cat => {
        filtersDiv.innerHTML += `<button class="btn btn-sm template-filter" onclick="filterTemplates('${cat.id}')" data-cat="${cat.id}" style="background:${cat.color}20; color:${cat.color}; border:1px solid ${cat.color}40;">${cat.icon} ${cat.id}</button>`;
    });

    // Render template cards
    gallery.innerHTML = '';
    data.templates.forEach(tpl => {
        const catInfo = data.categories.find(c => c.id === tpl.category) || { color: '#888' };
        const card = document.createElement('div');
        card.className = 'card template-card';
        card.setAttribute('data-category', tpl.category);
        card.style.cssText = 'cursor:pointer; transition:all 0.2s ease; border-left:4px solid ' + catInfo.color + '; position:relative;';
        card.innerHTML = `
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                <span style="font-size:1.8rem;">${tpl.icon}</span>
                <div>
                    <h3 style="margin:0; font-size:1rem;">${tpl.name}</h3>
                    <span style="font-size:0.75rem; color:${catInfo.color}; font-weight:600;">${tpl.category}</span>
                </div>
            </div>
            <p style="font-size:0.85em; color:var(--text-muted); margin:0 0 12px 0; line-height:1.4;">${tpl.description}</p>
            <div style="display:flex; flex-direction:column; gap:6px;">
                <select class="form-control" id="deploy-model-${tpl.id}" onclick="event.stopPropagation()">
                    <option value="${tpl.model}">Default (${tpl.model})</option>
                    <option value="openai/gpt-4o">OpenAI GPT-4o</option>
                    <option value="openai/gpt-4o-mini">OpenAI GPT-4o Mini</option>
                    <option value="nvidia/llama-3.1-70b-instruct">Nvidia Llama 3.1 70B</option>
                    <option value="nvidia/llama-3.1-8b-instruct">Nvidia Llama 3.1 8B</option>
                    <option value="anthropic/claude-3-5-sonnet-20240620">Claude 3.5 Sonnet</option>
                </select>
                <button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); deployTemplate('${tpl.id}')" style="width:100%;">
                    <i class="fa-solid fa-rocket"></i> Deploy This Bot
                </button>
            </div>
        `;

        // Hover effects
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-3px)';
            card.style.boxShadow = '0 8px 25px rgba(0,0,0,0.15)';
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
            card.style.boxShadow = '';
        });

        gallery.appendChild(card);
    });
}

function filterTemplates(category) {
    // Update active filter button
    document.querySelectorAll('.template-filter').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-cat') === category) {
            btn.classList.add('active');
            btn.style.opacity = '1';
        }
    });

    // Filter cards
    document.querySelectorAll('.template-card').forEach(card => {
        if (category === 'all' || card.getAttribute('data-category') === category) {
            card.style.display = '';
            card.style.animation = 'fadeIn 0.3s ease';
        } else {
            card.style.display = 'none';
        }
    });
}

async function deployTemplate(templateId) {
    if (!confirm("Deploy this bot? It will be created and ready to chat instantly.")) return;

    // Grab the selected model override
    const selectEl = document.getElementById(`deploy-model-${templateId}`);
    const selectedModel = selectEl ? selectEl.value : null;

    try {
        const resp = await fetch(`${API_BASE}/templates/deploy`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                template_id: templateId,
                override_model: selectedModel
            })
        });
        const data = await resp.json();

        if (resp.ok) {
            alert(data.message || '✅ Bot deployed!');
            // Reload bots and switch to Chat
            await loadBots();
            await loadChatBots();
            switchView('chat');

            // Highlight the new bot in the sidebar
            document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
            document.querySelector('[data-view="chat"]').classList.add('active');
        } else {
            alert('Failed: ' + (data.detail || 'Unknown error'));
        }
    } catch (err) {
        alert('Connection error.');
    }
}

// ==========================================
// TELEGRAM CHANNELS
// ==========================================

async function loadChannelBots() {
    try {
        const resp = await fetch(`${API_BASE}/chat/bots`);
        const data = await resp.json();
        if (resp.ok) {
            const select = document.getElementById('tg-bot-select');
            select.innerHTML = '<option value="">-- Select a Bot --</option>';
            data.bots.forEach(bot => {
                select.innerHTML += `<option value="${bot.id}">${bot.name}</option>`;
            });
        }
        // Render the army table & update dashboard worker count
        await renderArmyTable();
    } catch (err) {
        console.error("Error loading channel bots:", err);
    }
}

async function checkTelegramTokenStatus() {
    const select = document.getElementById('tg-bot-select');
    const input = document.getElementById('tg-token');
    const btnUnlink = document.getElementById('btn-unlink-tg');
    const botId = select?.value;

    if (!botId) {
        if (input) input.value = '';
        if (input) input.placeholder = '123456:ABC-DEF...';
        if (btnUnlink) btnUnlink.style.display = 'none';
        return;
    }

    const bot = activeBots[botId];
    if (bot && bot.telegram_token) {
        if (input) input.value = '';
        if (input) input.placeholder = '✅ Token Saved (Hidden for security)';
        if (btnUnlink) btnUnlink.style.display = 'block';
    } else {
        if (input) input.value = '';
        if (input) input.placeholder = '123456:ABC-DEF...';
        if (btnUnlink) btnUnlink.style.display = 'none';
    }
}

async function unlinkTelegramToken() {
    const botId = document.getElementById('tg-bot-select').value;
    if (!botId) return;
    if (!confirm("Are you sure you want to unlink the Telegram token for this bot? Workers using it will be killed.")) return;

    try {
        const resp = await fetch(`${API_BASE}/channels/telegram/unlink`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ bot_id: botId })
        });

        if (resp.ok) {
            alert('Telegram token unlinked!');
            if (activeBots[botId]) activeBots[botId].telegram_token = null;
            checkTelegramTokenStatus();
            await renderArmyTable();
        } else {
            const data = await resp.json();
            alert('Failed to unlink: ' + (data.detail || 'Unknown error'));
        }
    } catch (err) {
        alert('Connection error.');
    }
}

async function saveTelegramToken() {
    const botId = document.getElementById('tg-bot-select').value;
    const token = document.getElementById('tg-token').value;
    if (!botId) return alert("Select a bot first!");
    if (!token) return alert("Enter a Telegram token!");

    try {
        const resp = await fetch(`${API_BASE}/channels/telegram/save`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ bot_id: botId, token })
        });
        const data = await resp.json();
        if (resp.ok) {
            alert('Telegram token saved!');
            if (activeBots[botId]) activeBots[botId].telegram_token = "*";
            checkTelegramTokenStatus();
            await renderArmyTable();
        }
        else alert(data.detail || 'Failed to save.');
    } catch (err) {
        alert('Connection error.');
    }
}

async function startTelegramWorker(botId) {
    if (!botId) {
        botId = document.getElementById('tg-bot-select').value;
    }
    if (!botId) return alert("Select a bot first!");

    try {
        const resp = await fetch(`${API_BASE}/channels/telegram/start`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ bot_id: botId })
        });
        const data = await resp.json();
        if (resp.ok) {
            document.getElementById('tg-worker-status').innerHTML =
                `<p style="color:var(--success-color);"><i class="fa-solid fa-circle"></i> Worker started for bot.</p>`;
            await renderArmyTable();
        } else {
            alert(data.detail || 'Failed to start worker.');
        }
    } catch (err) {
        alert('Connection error.');
    }
}

async function stopTelegramWorker(botId) {
    if (!botId) {
        botId = document.getElementById('tg-bot-select').value;
    }
    if (!botId) return alert("Select a bot first!");

    try {
        const resp = await fetch(`${API_BASE}/channels/telegram/stop`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ bot_id: botId })
        });
        if (resp.ok) {
            document.getElementById('tg-worker-status').innerHTML =
                '<p style="color:var(--text-muted);">Worker stopped.</p>';
            await renderArmyTable();
        }
    } catch (err) {
        alert('Connection error.');
    }
}

async function renderArmyTable() {
    const tbody = document.getElementById('army-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    // Fetch live worker status
    let workerStatus = {};
    try {
        const statusResp = await fetch(`${API_BASE}/channels/telegram/status`, {
            headers: getAuthHeader()
        });
        const statusData = await statusResp.json();
        if (statusResp.ok) workerStatus = statusData.workers || {};
    } catch (e) { }

    // Update dashboard worker count
    const liveCount = Object.values(workerStatus).filter(w => w.alive).length;
    document.getElementById('dash-worker-count').innerText = liveCount;

    for (const [id, bot] of Object.entries(activeBots)) {
        const hasToken = !!bot.telegram_token;
        const isRunning = workerStatus[id] && workerStatus[id].alive;
        const tokenDisplay = hasToken ? '••••••' : '<span style="color:var(--danger-color);">Not Set</span>';
        const statusBadge = isRunning
            ? '<span style="background:var(--success-color); color:#fff; padding:2px 10px; border-radius:12px; font-size:0.8em;">LIVE</span>'
            : '<span style="background:var(--border-color); padding:2px 10px; border-radius:12px; font-size:0.8em;">OFF</span>';

        const actionBtn = isRunning
            ? `<button class="btn btn-sm btn-danger" onclick="stopTelegramWorker('${id}')"><i class="fa-solid fa-stop"></i> Stop</button>`
            : hasToken
                ? `<button class="btn btn-sm btn-success" onclick="startTelegramWorker('${id}')"><i class="fa-solid fa-play"></i> Start</button>`
                : `<span style="font-size:0.8em; color:var(--text-muted);">Set token first</span>`;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${bot.name}</strong></td>
            <td><span style="font-size:0.85em; color:var(--text-muted);">${bot.model}</span></td>
            <td>${tokenDisplay}</td>
            <td>${statusBadge}</td>
            <td>
                <div style="display:flex; gap:5px;">
                    ${actionBtn}
                    <button class="btn btn-sm btn-danger" onclick="deleteBot('${id}')" title="Delete Bot">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    }
}

async function loadTelegramStatus() {
    await renderArmyTable();
}

// ==========================================
// DASHBOARD & SETTINGS
// ==========================================

async function loadDashboard() {
    loadBots();
    loadDashboardExtras();
}

async function loadDashboardExtras() {
    // Load API key count
    try {
        const resp = await fetch(`${API_BASE}/settings/`, {
            headers: getAuthHeader()
        });
        const data = await resp.json();
        if (resp.ok) {
            const count = Object.values(data.keys_set).filter(v => v).length;
            const total = Object.keys(data.keys_set).length;
            document.getElementById('dash-keys-count').innerText = `${count} / ${total}`;
        }
    } catch (err) { }

    // Load SSH status
    try {
        const resp = await fetch(`${API_BASE}/remote/servers`, {
            headers: getAuthHeader()
        });
        const data = await resp.json();
        if (resp.ok && data.servers && data.servers.length > 0) {
            document.getElementById('dash-server-status').innerText = data.servers.length + ' server(s)';
        }
    } catch (err) { }

    // Load Telegram worker count
    try {
        await loadTelegramStatus();
    } catch (err) { }
}

async function loadSettings() {
    try {
        const resp = await fetch(`${API_BASE}/settings/`, {
            headers: getAuthHeader()
        });
        const data = await resp.json();
        if (resp.ok) {
            const standardProviders = ['openai', 'anthropic', 'nvidia', 'google', 'deepseek'];
            const customProviders = [];

            Object.keys(data.keys_set).forEach(provider => {
                const statusEl = document.getElementById(`status-${provider}`);
                if (statusEl && data.keys_set[provider]) {
                    statusEl.innerHTML = '<i class="fa-solid fa-check-double" style="color:var(--success-color);"></i> Ready';
                    statusEl.title = "API Key is set and ready to use.";
                } else if (statusEl) {
                    statusEl.innerHTML = '<i class="fa-solid fa-circle-exclamation" style="color:var(--text-muted);"></i> Not Set';
                }
                if (!standardProviders.includes(provider) && data.keys_set[provider]) {
                    customProviders.push(provider);
                }
            });

            // Render custom providers list
            const listEl = document.getElementById('custom-providers-list');
            if (listEl && customProviders.length > 0) {
                listEl.innerHTML = '<p style="font-size:0.8em; color:var(--text-muted); margin-bottom:8px;"><strong>Your Custom Providers:</strong></p>' +
                    customProviders.map(p => `
                        <span style="display:inline-flex; align-items:center; gap:6px; background:var(--accent-color)15; border:1px solid var(--accent-color)40; padding:4px 10px; border-radius:20px; margin:3px; font-size:0.85em;">
                            <i class="fa-solid fa-key" style="color:var(--accent-color);"></i> ${p}
                            <button onclick="clearApiKey('${p}')" style="background:none; border:none; color:var(--danger-color); cursor:pointer; font-size:0.9em;" title="Remove">×</button>
                        </span>
                    `).join('');
            } else if (listEl) {
                listEl.innerHTML = '';
            }
        }
    } catch (err) {
        console.error('Failed to load settings', err);
    }
}

function showModelGuidance(provider) {
    const guidance = {
        'nvidia': 'Nvidia NIM: Use "meta/llama-3.1-405b" for logic, or "nvidia/nemotron-4-340b" for roleplay. Keys start with "nvapi-".',
        'openai': 'OpenAI: Use "gpt-4o" for best tool use and vision. Requires paid credits.',
        'anthropic': 'Anthropic: Use "claude-3-5-sonnet" for superior coding and long docs.',
        'deepseek': 'DeepSeek: Exceptional reasoning at low cost. Use "deepseek-reasoner" or "deepseek-chat".',
        'google': 'Google AI: Use "gemini-1.5-pro" for massive context windows.'
    };
    alert(guidance[provider] || "Standard API provider.");
}

async function saveCustomProvider() {
    const nameEl = document.getElementById('custom-provider-name');
    const keyEl = document.getElementById('custom-provider-key');
    const name = nameEl?.value?.trim().toLowerCase();
    const key = keyEl?.value?.trim();

    if (!name || !key) return alert('Please enter both a provider name and API key.');

    try {
        const resp = await fetch(`${API_BASE}/settings/`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ provider: name, key })
        });

        if (resp.ok) {
            alert(`✅ ${name} key saved!`);
            nameEl.value = '';
            keyEl.value = '';
            loadSettings();
        } else {
            alert('Failed to save key.');
        }
    } catch (err) {
        alert('Connection error.');
    }
}

async function handleSaveApiKey(e) {
    e.preventDefault();
    const form = e.target;
    const provider = form.getAttribute('data-provider');
    const key = form.querySelector('input').value;

    if (!key) return;

    const resp = await fetch(`${API_BASE}/settings`, {
        method: 'POST',
        headers: {
            ...getAuthHeader(),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ provider, key })
    });

    if (resp.ok) {
        const statusEl = document.getElementById(`status-${provider}`);
        if (statusEl) {
            statusEl.innerHTML = '<i class="fa-solid fa-check" style="color:var(--success-color);"></i> Saved';
            setTimeout(() => statusEl.innerHTML = '', 3000); // Clear after 3 seconds
        }
        form.querySelector('input').value = '';
        alert(`✅ ${provider.charAt(0).toUpperCase() + provider.slice(1)} key saved!`);
    } else {
        alert('Failed to save key.');
    }
}

async function deleteLocalAccount() {
    if (!confirm("🚨 WARNING: This will permanently delete your local account, all bots, and API keys. Are you absolutely sure?")) {
        return;
    }

    // Double confirmation for safety
    if (!confirm("Final Confirmation: Delete your Wolfclaw Account?")) {
        return;
    }

    try {
        const resp = await fetch(`${API_BASE}/account/delete`, {
            method: 'DELETE',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_id: currentUser.id })
        });

        if (resp.ok) {
            alert("Account securely deleted. Redirecting to login.");
            localStorage.removeItem('wolfclaw-auth');
            currentUser = null;
            showAuth();
        } else {
            const data = await resp.json();
            alert("Failed to delete account: " + (data.detail || "Unknown error"));
        }
    } catch (err) {
        alert("Connection error while attempting to delete account.");
    }
}

// ==========================================
// CHANGE PASSWORD
// ==========================================

async function changePassword(e) {
    e.preventDefault();
    const currentPassword = document.getElementById('cp-current').value;
    const newPassword = document.getElementById('cp-new').value;
    const statusEl = document.getElementById('status-change-password');

    if (!currentUser || !currentUser.id) return;

    statusEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    statusEl.style.color = 'var(--text-muted)';

    try {
        const resp = await fetch(`${API_BASE}/auth/change-password`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: currentUser.id,
                current_password: currentPassword,
                new_password: newPassword
            })
        });

        const data = await resp.json();
        if (resp.ok) {
            statusEl.innerHTML = '<i class="fa-solid fa-check"></i> Updated';
            statusEl.style.color = 'var(--success-color)';
            document.getElementById('change-password-form').reset();
            setTimeout(() => statusEl.innerHTML = '', 3000);
        } else {
            statusEl.innerHTML = '<i class="fa-solid fa-xmark"></i> ' + (data.detail || 'Failed');
            statusEl.style.color = 'var(--danger-color)';
        }
    } catch (err) {
        statusEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Error';
        statusEl.style.color = 'var(--danger-color)';
    }
}

// ==========================================
// CLEAR API KEY
// ==========================================

async function clearApiKey(provider) {
    if (!confirm(`Clear your ${provider} API key?`)) return;

    try {
        const resp = await fetch(`${API_BASE}/settings/`, {
            method: 'DELETE',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ provider })
        });

        if (resp.ok) {
            const statusEl = document.getElementById(`status-${provider}`);
            if (statusEl) statusEl.innerHTML = '';
            alert(`🗑️ ${provider.charAt(0).toUpperCase() + provider.slice(1)} key cleared.`);
        } else {
            alert('Failed to clear key.');
        }
    } catch (err) {
        alert('Connection error.');
    }
}

// ==========================================
// TOOL CONSOLE — Direct Tool Execution
// ==========================================

const TOOL_RESULT_MAP = {
    'run_terminal_command': 'tool-terminal-result',
    'web_search': 'tool-search-result',
    'capture_screenshot': 'tool-screenshot-result',
    'read_document': 'tool-doc-result',
    'run_remote_ssh_command': 'tool-ssh-result',
    'simulate_gui': 'tool-gui-result',
    'web_browser': 'tool-browser-result'
};

async function runToolDirect(toolName, args) {
    const resultId = TOOL_RESULT_MAP[toolName];
    const resultEl = document.getElementById(resultId);
    if (resultEl) {
        resultEl.classList.remove('hidden');
        resultEl.textContent = '⏳ Running...';
        resultEl.style.color = 'var(--text-muted)';
    }

    try {
        const resp = await fetch(`${API_BASE}/tools/execute`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ tool_name: toolName, arguments: args })
        });
        const data = await resp.json();

        if (resultEl) {
            if (data.status === 'success') {
                resultEl.style.color = 'var(--success-color)';
                resultEl.textContent = data.result || 'Done.';
                addActivityEntry('success', `${toolName}`, data.result ? data.result.substring(0, 100) : 'OK');
            } else {
                resultEl.style.color = 'var(--danger-color)';
                resultEl.textContent = '❌ ' + (data.result || 'Unknown error');
                addActivityEntry('error', `${toolName}`, data.result || 'Failed');
            }
        }
    } catch (err) {
        if (resultEl) {
            resultEl.style.color = 'var(--danger-color)';
            resultEl.textContent = '❌ Connection error: ' + err.message;
        }
        addActivityEntry('error', `${toolName}`, err.message);
    }
}

function runGuiTool() {
    const action = document.getElementById('tool-gui-action').value;
    const keys = document.getElementById('tool-gui-keys').value;
    const args = { action };

    if (action === 'click') {
        const parts = keys.split(',');
        args.x = parseInt(parts[0]) || 0;
        args.y = parseInt(parts[1]) || 0;
    } else {
        args.keys = keys;
    }

    runToolDirect('simulate_gui', args);
}

// ==========================================
// ACTIVITY LOG
// ==========================================

const activityLog = [];

function addActivityEntry(type, toolName, detail) {
    const now = new Date();
    const timeStr = now.toLocaleTimeString();
    const entry = { type, toolName, detail, time: timeStr };
    activityLog.unshift(entry);

    // Keep max 200 entries
    if (activityLog.length > 200) activityLog.pop();

    renderActivityLog();
}

function renderActivityLog(filter = 'all') {
    const list = document.getElementById('activity-log-list');
    if (!list) return;

    const filtered = filter === 'all' ? activityLog : activityLog.filter(e => e.type === filter);

    if (filtered.length === 0) {
        list.innerHTML = `<div class="activity-entry info">
            <span class="activity-icon"><i class="fa-solid fa-circle-info"></i></span>
            <span style="flex:1;">No activity yet.</span>
            <span class="activity-time">—</span>
        </div>`;
        return;
    }

    list.innerHTML = filtered.map(e => {
        const iconMap = {
            success: '<i class="fa-solid fa-circle-check"></i>',
            error: '<i class="fa-solid fa-circle-xmark"></i>',
            warning: '<i class="fa-solid fa-triangle-exclamation"></i>',
            info: '<i class="fa-solid fa-circle-info"></i>'
        };
        return `<div class="activity-entry ${e.type}">
            <span class="activity-icon">${iconMap[e.type] || iconMap.info}</span>
            <span style="flex:1;"><strong>${e.toolName}</strong> — ${e.detail}</span>
            <span class="activity-time">${e.time}</span>
        </div>`;
    }).join('');
}

function filterActivity(type) {
    renderActivityLog(type);
}

function clearActivityLog() {
    activityLog.length = 0;
    renderActivityLog();
}

// ==========================================
// DASHBOARD UPTIME COUNTER
// ==========================================

const _appStartTime = Date.now();

function updateUptime() {
    const el = document.getElementById('dash-uptime');
    if (!el) return;
    const diff = Date.now() - _appStartTime;
    const mins = Math.floor(diff / 60000);
    if (mins < 60) {
        el.textContent = `${mins}m`;
    } else {
        const hrs = Math.floor(mins / 60);
        const rm = mins % 60;
        el.textContent = `${hrs}h ${rm}m`;
    }
}

setInterval(updateUptime, 30000);
setTimeout(updateUptime, 1000);

// ==========================================
// V3: CHAT WITH DOCUMENTS
// ==========================================

async function uploadDocument(inputElement) {
    const file = inputElement.files[0];
    if (!file) return;

    inputElement.value = ''; // reset so they can upload same file again if needed

    // Size check
    if (file.size > 10 * 1024 * 1024) {
        alert("File is too large. Max size is 10MB.");
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const docSelect = document.getElementById('chat-document-context');
    const origStatus = docSelect.options[0].text;
    docSelect.options[0].text = `⏳ Uploading ${file.name}...`;

    try {
        const resp = await fetch(`${API_BASE}/documents/upload`, {
            method: 'POST',
            body: formData
        });

        const data = await resp.json();
        if (resp.ok) {
            // Append and select the new document
            const opt = document.createElement('option');
            opt.value = data.doc_id;
            opt.text = `📄 ${data.filename}`;
            docSelect.appendChild(opt);
            docSelect.value = data.doc_id;

            // Add a temporary success bubble in chat
            appendChatBubble('assistant', `<i>✅ Document successfully ingested: ${data.filename}. It is now selected as context for our conversation.</i>`);
        } else {
            alert(`Upload failed: ${data.detail}`);
        }
    } catch (err) {
        alert(`Connection error during upload: ${err}`);
    } finally {
        docSelect.options[0].text = "No Context (Standard Chat)";
        loadWorkspaceDocuments(); // update the list
    }
}

async function loadWorkspaceDocuments() {
    const docSelect = document.getElementById('chat-document-context');
    if (!docSelect) return;

    try {
        const resp = await fetch(`${API_BASE}/documents/`);
        const data = await resp.json();

        if (resp.ok) {
            // Keep the first option ("No Context") and currently selected value
            const currentValue = docSelect.value;
            docSelect.innerHTML = '<option value="">No Context (Standard Chat)</option>';

            data.documents.forEach(doc => {
                const opt = document.createElement('option');
                opt.value = doc.id;
                opt.text = `📄 ${doc.filename}`;
                docSelect.appendChild(opt);
            });

            // Restore selection if it still exists
            if ([...docSelect.options].some(o => o.value === currentValue)) {
                docSelect.value = currentValue;
            }
        }
    } catch (err) {
        console.error("Failed to load documents", err);
    }
}

// Ensure docs are loaded on app start
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(loadWorkspaceDocuments, 500);
});

// ==========================================
// V3: PERSISTENT CHAT HISTORY
// ==========================================

async function loadChatHistorySidebar() {
    const listEl = document.getElementById('chat-history-list');
    if (!listEl) return;

    try {
        const resp = await fetch(`${API_BASE}/history/`);
        const data = await resp.json();

        if (resp.ok) {
            listEl.innerHTML = '';

            if (data.histories.length === 0) {
                listEl.innerHTML = '<div style="padding:10px; text-align:center; color:gray; font-size:0.9em;">No past chats</div>';
                return;
            }

            data.histories.forEach(hist => {
                const isSelected = hist.id === currentChatId;

                const div = document.createElement('div');
                div.className = `history-item ${isSelected ? 'selected' : ''}`;
                div.style.cssText = `
                    padding: 8px 10px;
                    border-radius: 6px;
                    cursor: pointer;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    background: ${isSelected ? 'var(--border-color)' : 'transparent'};
                    transition: background 0.2s;
                `;

                // Truncate title
                let displayTitle = hist.title || "New Chat";
                if (displayTitle.length > 20) displayTitle = displayTitle.substring(0, 20) + '...';

                div.innerHTML = `
                    <div style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1;" onclick="resumeChat('${hist.id}')" title="${hist.title}">
                        <i class="fa-regular fa-message" style="margin-right:6px; opacity:0.7;"></i> ${displayTitle}
                    </div>
                    <button class="btn btn-sm btn-danger" style="padding:2px 6px; font-size:0.8em; margin-left:5px;" onclick="deleteChatHistory('${hist.id}')" title="Delete chat">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                `;

                // Add hover effect programmatically to avoid adding CSS rules right now
                div.onmouseover = () => { if (!isSelected) div.style.background = 'rgba(0,0,0,0.05)'; };
                div.onmouseout = () => { if (!isSelected) div.style.background = 'transparent'; };

                listEl.appendChild(div);
            });
        }
    } catch (err) {
        console.error("Failed to load history sidebar", err);
    }
}

async function resumeChat(historyId) {
    try {
        const resp = await fetch(`${API_BASE}/history/${historyId}`);
        if (!resp.ok) throw new Error("Could not load chat");

        const historyData = await resp.json();

        // Setup Chat UI
        currentChatId = historyData.id;
        chatBotId = historyData.bot_id; // Set target bot

        // Grab bot name for UI from our loaded bots array if possible.
        const select = document.getElementById('chat-bot-select');
        let botName = "Restored Bot";
        if (select && select.options) {
            for (let i = 0; i < select.options.length; i++) {
                if (select.options[i].value === chatBotId) {
                    botName = select.options[i].text;
                    select.value = chatBotId; // Sync dropdown
                    break;
                }
            }
        }

        document.getElementById('chat-bot-name').innerText = botName;
        document.getElementById('chat-no-bot').classList.add('hidden');
        document.getElementById('chat-active').classList.remove('hidden');

        // Parse messages and render
        document.getElementById('chat-messages').innerHTML = '';
        chatMessages = JSON.parse(historyData.messages);

        chatMessages.forEach(msg => {
            appendChatBubble(msg.role, msg.content, true); // true = raw mode, no action buttons for old messages
        });

        // Reload sidebar to highlight active
        loadChatHistorySidebar();

    } catch (err) {
        alert("Failed to restore conversation.");
        console.error(err);
    }
}

async function deleteChatHistory(historyId) {
    if (!confirm("Are you sure you want to delete this conversation?")) return;

    try {
        const resp = await fetch(`${API_BASE}/history/${historyId}`, {
            method: 'DELETE'
        });

        if (resp.ok) {
            if (currentChatId === historyId) {
                // We just deleted the active chat, reset it
                startNewChat();
            } else {
                loadChatHistorySidebar();
            }
        }
    } catch (err) {
        alert("Failed to delete chat.");
    }
}

// Modify global init to load the sidebar too if we are on the page
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(loadChatHistorySidebar, 600);
});

// ==========================================
// PHASE 13: KNOWLEDGE BASE
// ==========================================

async function loadKBBots() {
    try {
        const resp = await fetch(`${API_BASE}/chat/bots`, {
            headers: getAuthHeader()
        });
        const data = await resp.json();
        if (resp.ok) {
            const select = document.getElementById('kb-bot-select');
            if (!select) return;
            select.innerHTML = '<option value="">-- Select a Bot --</option>';
            data.bots.forEach(bot => {
                select.innerHTML += `<option value="${bot.id}">${bot.name}</option>`;
            });
        }
    } catch (err) { }
}

async function loadBotKnowledge() {
    const botId = document.getElementById('kb-bot-select').value;
    const contentDiv = document.getElementById('kb-content');
    if (!botId) {
        contentDiv.classList.add('hidden');
        return;
    }
    contentDiv.classList.remove('hidden');

    try {
        const resp = await fetch(`${API_BASE}/knowledge/${botId}`);
        const data = await resp.json();
        const listEl = document.getElementById('kb-doc-list');

        if (resp.ok && data.documents && data.documents.length > 0) {
            listEl.innerHTML = data.documents.map(doc => `
                <div style="display:flex; justify-content:space-between; align-items:center; padding:10px; border:1px solid var(--border-color); border-radius:8px; margin-bottom:8px;">
                    <div>
                        <strong><i class="fa-solid fa-file-lines"></i> ${doc.filename}</strong>
                        <span style="font-size:0.8em; color:var(--text-muted); margin-left:10px;">${doc.chunk_count} chunks</span>
                    </div>
                    <button class="btn btn-sm btn-danger" onclick="deleteKnowledgeDoc('${doc.id}')"><i class="fa-solid fa-trash"></i></button>
                </div>
            `).join('');
        } else {
            listEl.innerHTML = '<p style="color:var(--text-muted);">No documents uploaded yet.</p>';
        }
    } catch (err) {
        console.error('Failed to load KB docs', err);
    }
}

async function uploadKnowledgeDoc() {
    const botId = document.getElementById('kb-bot-select').value;
    const fileInput = document.getElementById('kb-file-input');
    const statusEl = document.getElementById('kb-upload-status');

    if (!botId) return alert('Select a bot first.');
    if (!fileInput.files[0]) return alert('Select a file to upload.');

    statusEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Uploading and indexing...';

    const formData = new FormData();
    formData.append('bot_id', botId);
    formData.append('file', fileInput.files[0]);

    try {
        const resp = await fetch(`${API_BASE}/knowledge/upload`, {
            method: 'POST',
            body: formData
        });
        const data = await resp.json();

        if (resp.ok) {
            statusEl.innerHTML = `<span style="color:var(--success-color);">${data.message}</span>`;
            fileInput.value = '';
            loadBotKnowledge();
        } else {
            statusEl.innerHTML = `<span style="color:var(--danger-color);">❌ ${data.detail}</span>`;
        }
    } catch (err) {
        statusEl.innerHTML = '<span style="color:var(--danger-color);">Connection error.</span>';
    }
}

async function deleteKnowledgeDoc(docId) {
    if (!confirm('Delete this document and all its chunks from the knowledge base?')) return;
    try {
        await fetch(`${API_BASE}/knowledge/${docId}`, { method: 'DELETE' });
        loadBotKnowledge();
    } catch (err) {
        alert('Failed to delete.');
    }
}

// ==========================================
// PHASE 14: AUTOMATIONS (SCHEDULED TASKS)
// ==========================================

async function loadSchedBots() {
    try {
        const resp = await fetch(`${API_BASE}/chat/bots`, {
            headers: getAuthHeader()
        });
        const data = await resp.json();
        if (resp.ok) {
            const select = document.getElementById('sched-bot-select');
            if (!select) return;
            select.innerHTML = '<option value="">-- Select Bot --</option>';
            data.bots.forEach(bot => {
                select.innerHTML += `<option value="${bot.id}">${bot.name}</option>`;
            });
        }
    } catch (err) { }
}

async function createScheduledTask() {
    const name = document.getElementById('sched-name').value;
    const botId = document.getElementById('sched-bot-select').value;
    const prompt = document.getElementById('sched-prompt').value;
    const type = document.getElementById('sched-type').value;
    const value = document.getElementById('sched-value').value;

    if (!name || !botId || !prompt || !value) return alert('All fields are required.');

    try {
        const resp = await fetch(`${API_BASE}/scheduler/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                bot_id: botId, name, prompt,
                schedule_type: type, schedule_value: value
            })
        });
        const data = await resp.json();
        if (resp.ok) {
            alert(data.message || '✅ Task created!');
            document.getElementById('sched-name').value = '';
            document.getElementById('sched-prompt').value = '';
            document.getElementById('sched-value').value = '';
            loadScheduledTasks();
        } else {
            alert('Failed: ' + (data.detail || 'Unknown error'));
        }
    } catch (err) {
        alert('Connection error.');
    }
}

async function loadScheduledTasks() {
    const listEl = document.getElementById('sched-task-list');
    if (!listEl) return;

    try {
        const resp = await fetch(`${API_BASE}/scheduler/tasks`);
        const data = await resp.json();

        if (resp.ok && data.tasks && data.tasks.length > 0) {
            listEl.innerHTML = data.tasks.map(task => {
                const statusBadge = task.is_active
                    ? '<span style="background:var(--success-color); color:#fff; padding:2px 8px; border-radius:10px; font-size:0.75em;">ACTIVE</span>'
                    : '<span style="background:var(--border-color); padding:2px 8px; border-radius:10px; font-size:0.75em;">PAUSED</span>';
                const schedLabel = task.schedule_type === 'interval' ? `Every ${task.schedule_value} min` : `Cron: ${task.schedule_value}`;
                const lastRun = task.last_run ? new Date(task.last_run).toLocaleString() : 'Never';

                return `
                    <div style="padding:12px; border:1px solid var(--border-color); border-radius:8px; margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <strong>${task.name}</strong> ${statusBadge}
                                <div style="font-size:0.8em; color:var(--text-muted); margin-top:4px;">
                                    <i class="fa-solid fa-clock"></i> ${schedLabel} &nbsp;|&nbsp;
                                    <i class="fa-solid fa-history"></i> Last run: ${lastRun}
                                </div>
                            </div>
                            <div style="display:flex; gap:6px;">
                                <button class="btn btn-sm btn-primary" onclick="runTaskNow('${task.id}')" title="Run now"><i class="fa-solid fa-play"></i></button>
                                <button class="btn btn-sm btn-secondary" onclick="viewTaskResults('${task.id}')" title="View results"><i class="fa-solid fa-eye"></i></button>
                                <button class="btn btn-sm btn-danger" onclick="deleteScheduledTask('${task.id}')" title="Delete"><i class="fa-solid fa-trash"></i></button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            listEl.innerHTML = '<p style="color:var(--text-muted);">No tasks yet.</p>';
        }
    } catch (err) {
        console.error('Failed to load tasks', err);
    }
}

async function runTaskNow(taskId) {
    try {
        const resp = await fetch(`${API_BASE}/scheduler/tasks/${taskId}/run`, { method: 'POST' });
        const data = await resp.json();
        alert(data.message || 'Task triggered!');
        setTimeout(loadScheduledTasks, 2000);
    } catch (err) {
        alert('Connection error.');
    }
}

async function viewTaskResults(taskId) {
    try {
        const resp = await fetch(`${API_BASE}/scheduler/tasks/${taskId}/results`);
        const data = await resp.json();

        if (resp.ok && data.results && data.results.length > 0) {
            const html = data.results.map(r => `
                <div style="padding:10px; border:1px solid var(--border-color); border-radius:6px; margin-bottom:8px;">
                    <div style="font-size:0.75em; color:var(--text-muted); margin-bottom:4px;">${new Date(r.created_at).toLocaleString()}</div>
                    <pre style="white-space:pre-wrap; font-size:0.85em; max-height:150px; overflow-y:auto;">${r.result}</pre>
                </div>
            `).join('');

            // Replace the task list temporarily with results
            const listEl = document.getElementById('sched-task-list');
            listEl.innerHTML = `
                <button class="btn btn-sm btn-secondary" onclick="loadScheduledTasks()" style="margin-bottom:10px;"><i class="fa-solid fa-arrow-left"></i> Back to Tasks</button>
                <h4>Execution History (${data.results.length} runs)</h4>
                ${html}
            `;
        } else {
            alert('No results yet. Task may not have run.');
        }
    } catch (err) {
        alert('Connection error.');
    }
}

async function deleteScheduledTask(taskId) {
    if (!confirm('Delete this scheduled task?')) return;
    try {
        await fetch(`${API_BASE}/scheduler/tasks/${taskId}`, { method: 'DELETE' });
        loadScheduledTasks();
    } catch (err) {
        alert('Failed to delete.');
    }
}

// ==========================================
// PHASE 15: EXPORT & REPORTS
// ==========================================

async function exportChatToPDFServer() {
    if (!chatMessages || chatMessages.length === 0) return alert('No messages to export.');
    const botName = document.getElementById('chat-bot-name')?.innerText || 'AI Bot';

    try {
        const resp = await fetch(`${API_BASE}/reports/pdf`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                bot_name: botName,
                messages: chatMessages,
                title: `Chat with ${botName}`
            })
        });

        if (resp.ok) {
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `wolfclaw_chat_${Date.now()}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
        } else {
            alert('PDF generation failed.');
        }
    } catch (err) {
        alert('Connection error.');
    }
}

async function exportChatToDOCX() {
    if (!chatMessages || chatMessages.length === 0) return alert('No messages to export.');
    const botName = document.getElementById('chat-bot-name')?.innerText || 'AI Bot';

    try {
        const resp = await fetch(`${API_BASE}/reports/docx`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                bot_name: botName,
                messages: chatMessages,
                title: `Chat with ${botName}`
            })
        });

        if (resp.ok) {
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `wolfclaw_chat_${Date.now()}.docx`;
            a.click();
            URL.revokeObjectURL(url);
        } else {
            alert('DOCX generation failed.');
        }
    } catch (err) {
        alert('Connection error.');
    }
}

// ==========================================
// PHASE 17: USAGE ANALYTICS
// ==========================================

async function loadAnalytics() {
    // Summary
    try {
        const resp = await fetch(`${API_BASE}/analytics/summary`);
        const data = await resp.json();
        if (resp.ok) {
            document.getElementById('analytics-total-tokens').innerText = (data.total_tokens || 0).toLocaleString();
            document.getElementById('analytics-total-cost').innerText = `$${(data.total_cost || 0).toFixed(4)}`;
            document.getElementById('analytics-total-calls').innerText = (data.total_calls || 0).toLocaleString();
            document.getElementById('analytics-avg-response').innerText = `${Math.round(data.avg_response_ms || 0)}ms`;
        }
    } catch (err) { }

    // By Model
    try {
        const resp = await fetch(`${API_BASE}/analytics/by-model`);
        const data = await resp.json();
        const el = document.getElementById('analytics-by-model');
        if (resp.ok && data.models && data.models.length > 0) {
            el.innerHTML = `<table style="width:100%; font-size:0.85em;">
                <tr style="color:var(--text-muted);"><th>Model</th><th>Calls</th><th>Tokens</th><th>Cost</th></tr>
                ${data.models.map(m => `<tr><td>${m.model}</td><td>${m.calls}</td><td>${(m.tokens || 0).toLocaleString()}</td><td>$${(m.cost || 0).toFixed(4)}</td></tr>`).join('')}
            </table>`;
        }
    } catch (err) { }

    // By Bot
    try {
        const resp = await fetch(`${API_BASE}/analytics/by-bot`);
        const data = await resp.json();
        const el = document.getElementById('analytics-by-bot');
        if (resp.ok && data.bots && data.bots.length > 0) {
            el.innerHTML = `<table style="width:100%; font-size:0.85em;">
                <tr style="color:var(--text-muted);"><th>Bot</th><th>Calls</th><th>Tokens</th><th>Cost</th></tr>
                ${data.bots.map(b => `<tr><td>${b.bot_name || b.bot_id}</td><td>${b.calls}</td><td>${(b.tokens || 0).toLocaleString()}</td><td>$${(b.cost || 0).toFixed(4)}</td></tr>`).join('')}
            </table>`;
        }
    } catch (err) { }

    // Daily Chart
    try {
        const resp = await fetch(`${API_BASE}/analytics/daily`);
        const data = await resp.json();
        if (resp.ok && data.daily && data.daily.length > 0) {
            drawDailyChart(data.daily);
        }
    } catch (err) { }
}

function drawDailyChart(dailyData) {
    const canvas = document.getElementById('daily-usage-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    canvas.width = canvas.offsetWidth * 2;
    canvas.height = 400;
    ctx.scale(2, 2);

    const w = canvas.offsetWidth;
    const h = 200;
    const padding = 40;
    const chartW = w - padding * 2;
    const chartH = h - padding * 2;

    ctx.clearRect(0, 0, w, h);

    const reversed = [...dailyData].reverse();
    const maxTokens = Math.max(...reversed.map(d => d.tokens || 0), 1);
    const barWidth = Math.max(chartW / reversed.length - 4, 8);

    // Draw bars
    reversed.forEach((d, i) => {
        const barH = ((d.tokens || 0) / maxTokens) * chartH;
        const x = padding + (i * (chartW / reversed.length)) + 2;
        const y = padding + chartH - barH;

        const gradient = ctx.createLinearGradient(x, y, x, y + barH);
        gradient.addColorStop(0, '#10b981');
        gradient.addColorStop(1, '#059669');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barH, 3);
        ctx.fill();
    });

    // Labels
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-muted') || '#888';
    ctx.font = '9px Inter, sans-serif';
    reversed.forEach((d, i) => {
        const x = padding + (i * (chartW / reversed.length)) + 2;
        const label = d.day ? d.day.substring(5) : '';
        if (i % Math.ceil(reversed.length / 10) === 0) {
            ctx.fillText(label, x, h - 5);
        }
    });
}

// ==========================================
// VIEW SWITCH HOOKS
// ==========================================

// Extend switchView to load data for new panels
const _originalSwitchView = typeof switchView === 'function' ? switchView : null;

function switchViewExtended(viewName) {
    // Call original if exists
    if (_originalSwitchView) _originalSwitchView(viewName);

    // Load data for new views
    if (viewName === 'knowledge-base') {
        loadKBBots();
    } else if (viewName === 'automations') {
        loadSchedBots();
        loadScheduledTasks();
    } else if (viewName === 'analytics') {
        loadAnalytics();
    }
}

// Override global switchView
if (typeof switchView === 'function') {
    const _origSwitch = switchView;
    switchView = function (viewName) {
        _origSwitch(viewName);
        if (viewName === 'knowledge-base') loadKBBots();
        else if (viewName === 'automations') { loadSchedBots(); loadScheduledTasks(); }
        else if (viewName === 'analytics') loadAnalytics();
        else if (viewName === 'deploy-channels') loadTelegramStatus();
        else if (viewName === 'flows') loadFlowsView();
        else if (viewName === 'war-room') loadWarRoomBots();
        else if (viewName === 'integrations') loadIntegrationsStatus();
        else if (viewName === 'marketplace') loadMarketplace();
    };
}

// ==========================================
// PHASE 18: WAR ROOM (MULTI-AGENT)
// ==========================================

let warRoomManagerId = null;
let warRoomSubBotIds = [];

async function loadWarRoomBots() {
    try {
        const resp = await fetch(`${API_BASE}/chat/bots`);
        const data = await resp.json();
        if (resp.ok) {
            const managerSelect = document.getElementById('warroom-manager-select');
            const subBotList = document.getElementById('warroom-subbot-list');

            managerSelect.innerHTML = '<option value="">-- Select Manager Bot --</option>';
            subBotList.innerHTML = '';

            data.bots.forEach(bot => {
                // Populate Manager Dropdown
                managerSelect.innerHTML += `<option value="${bot.id}">${bot.name} (${bot.model})</option>`;

                // Populate SubBot Checkboxes
                subBotList.innerHTML += `
                    <div style="margin-bottom: 5px;">
                        <label style="cursor: pointer; display: flex; align-items: center; gap: 8px;">
                            <input type="checkbox" value="${bot.id}" class="warroom-subbot-cb">
                            <span><strong>${bot.name}</strong> <small style="color:var(--text-muted)">${bot.model}</small></span>
                        </label>
                    </div>
                `;
            });
        }
    } catch (err) {
        console.error("Error loading War Room bots:", err);
    }
}

function startWarRoom() {
    warRoomManagerId = document.getElementById('warroom-manager-select').value;

    warRoomSubBotIds = [];
    document.querySelectorAll('.warroom-subbot-cb:checked').forEach(cb => {
        if (cb.value !== warRoomManagerId) { // Prevent manager from being its own sub-bot
            warRoomSubBotIds.push(cb.value);
        }
    });

    if (!warRoomManagerId) return alert("Please select a Manager Bot.");
    if (warRoomSubBotIds.length === 0) return alert("Please select at least one different Sub-Bot.");

    document.getElementById('war-room-setup').classList.add('hidden');
    document.getElementById('war-room-active').classList.remove('hidden');
    document.getElementById('warroom-messages').innerHTML = '';

    // Announce start
    const managerName = document.getElementById('warroom-manager-select').options[document.getElementById('warroom-manager-select').selectedIndex].text.split('(')[0].trim();
    appendWarRoomBubble('system', 'System', `War Room activated. Lead Manager: ${managerName}. Sub-agents standing by.`);
}

function endWarRoom() {
    if (!confirm("End this War Room mission?")) return;

    warRoomManagerId = null;
    warRoomSubBotIds = [];

    document.getElementById('war-room-setup').classList.remove('hidden');
    document.getElementById('war-room-active').classList.add('hidden');
    document.getElementById('warroom-messages').innerHTML = '';
}

async function sendWarRoomMessage() {
    const input = document.getElementById('warroom-input');
    const userMsg = input.value.trim();
    if (!userMsg || !warRoomManagerId) return;

    input.value = '';
    appendWarRoomBubble('user', 'You', userMsg);

    const sendBtn = input.nextElementSibling;
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running...';

    // We send a single prompt for now; keeping history stateless in UI for MVP
    const messages = [{ role: 'user', content: userMsg }];

    try {
        const resp = await fetch(`${API_BASE}/chat/warroom/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                manager_bot_id: warRoomManagerId,
                sub_bot_ids: warRoomSubBotIds,
                messages: messages
            })
        });

        const data = await resp.json();

        if (resp.ok) {
            data.events.forEach(event => {
                if (event.type === 'status') {
                    appendWarRoomBubble('status', event.bot_name, event.content);
                } else if (event.type === 'message') {
                    appendWarRoomBubble('assistant', event.bot_name, event.content);
                } else if (event.type === 'error') {
                    appendWarRoomBubble('error', event.bot_name, event.content);
                }
            });
        } else {
            appendWarRoomBubble('error', 'System', `Error: ${data.detail || 'Unknown error'}`);
        }
    } catch (err) {
        appendWarRoomBubble('error', 'System', 'Connection error. Is the backend running?');
    } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Dispatch';
    }
}

function appendWarRoomBubble(type, name, content) {
    const container = document.getElementById('warroom-messages');
    const div = document.createElement('div');
    div.style.marginBottom = '15px';
    div.style.padding = '12px 16px';
    div.style.borderRadius = '12px';
    div.style.maxWidth = '90%';
    div.style.wordWrap = 'break-word';
    div.style.whiteSpace = 'pre-wrap';

    let headerHtml = `<div style="font-weight:bold; font-size:0.85em; margin-bottom:4px; opacity:0.8;">${name}</div>`;

    if (type === 'user') {
        div.style.marginLeft = 'auto';
        div.style.background = 'var(--primary-color)';
        div.style.color = '#fff';
        headerHtml = ''; // No name for user
    } else if (type === 'status') {
        div.style.marginRight = 'auto';
        div.style.borderLeft = '3px solid var(--warning-color)';
        div.style.background = 'transparent';
        div.style.padding = '4px 12px';
        div.style.color = 'var(--text-muted)';
        div.style.fontStyle = 'italic';
        headerHtml = `<strong><i class="fa-solid fa-bolt"></i> ${name}:</strong> `;
    } else if (type === 'error') {
        div.style.marginRight = 'auto';
        div.style.background = 'rgba(239, 68, 68, 0.1)';
        div.style.color = 'var(--danger-color)';
        div.style.border = '1px solid var(--danger-color)';
        headerHtml = `<strong><i class="fa-solid fa-triangle-exclamation"></i> ${name} Error:</strong> `;
    } else if (type === 'system') {
        div.style.marginRight = 'auto';
        div.style.width = '100%';
        div.style.textAlign = 'center';
        div.style.color = 'var(--text-muted)';
        headerHtml = '';
    } else {
        div.style.marginRight = 'auto';
        div.style.background = 'var(--border-color)';
        div.style.color = 'var(--text-color)';
    }

    if (type === 'status' || type === 'error') {
        div.innerHTML = headerHtml + content;
    } else {
        div.innerHTML = headerHtml + content;
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}


// ==========================================
// PHASE 27: WOLFCLAW FLOWS (Visual Workflow Builder)
// ==========================================

let flowEditor = null;       // Drawflow instance
let currentFlowId = null;    // Active flow being edited
let flowBlockCatalog = [];   // Block types from API

async function loadFlowsView() {
    // Load the list of flows
    try {
        const res = await fetch(`${API_BASE}/flows`);
        const data = await res.json();
        renderFlowList(data.flows || []);
    } catch (e) {
        console.error('Failed to load flows:', e);
    }

    // Load block catalog (once)
    if (flowBlockCatalog.length === 0) {
        try {
            const res = await fetch(`${API_BASE}/flows/blocks`);
            const data = await res.json();
            flowBlockCatalog = data.blocks || [];
        } catch (e) {
            console.error('Failed to load block catalog:', e);
        }
    }
}

function renderFlowList(flows) {
    const container = document.getElementById('flows-list');
    if (!flows.length) {
        container.innerHTML = '<p style="color:var(--text-muted);">No flows yet. Click "New Flow" to get started.</p>';
        return;
    }

    container.innerHTML = flows.map(f => `
        <div class="flow-list-item" data-id="${f.id}">
            <div class="flow-list-info">
                <strong>${f.name}</strong>
                <span class="flow-list-desc">${f.description || 'No description'}</span>
                <span class="flow-list-date">${new Date(f.updated_at).toLocaleDateString()}</span>
            </div>
            <div class="flow-list-actions">
                <button class="btn btn-sm btn-primary" onclick="openFlowEditor('${f.id}')">
                    <i class="fa-solid fa-pen"></i> Edit
                </button>
                <button class="btn btn-sm btn-warning" onclick="quickRunFlow('${f.id}')">
                    <i class="fa-solid fa-play"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteFlow('${f.id}')">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

async function createNewFlow() {
    const name = prompt('Flow name:', 'My New Flow');
    if (!name) return;

    try {
        const res = await fetch(`${API_BASE}/flows`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                description: '',
                flow_data: JSON.stringify({ nodes: {}, edges: [] })
            })
        });
        const data = await res.json();
        await loadFlowsView();
        openFlowEditor(data.id);
    } catch (e) {
        alert('Failed to create flow: ' + e.message);
    }
}

async function openFlowEditor(flowId) {
    currentFlowId = flowId;

    // Hide list, show editor
    document.getElementById('flows-list-container').classList.add('hidden');
    document.getElementById('flow-editor-container').classList.remove('hidden');
    document.getElementById('flow-results-container').classList.add('hidden');

    // Load flow data
    try {
        const res = await fetch(`${API_BASE}/flows/${flowId}`);
        const flow = await res.json();

        document.getElementById('flow-name-input').value = flow.name || '';
        document.getElementById('flow-desc-input').value = flow.description || '';

        // Initialize Drawflow canvas
        initDrawflow(flow.flow_data ? JSON.parse(flow.flow_data) : { nodes: {}, edges: [] });
        renderBlockPalette();
    } catch (e) {
        alert('Failed to load flow: ' + e.message);
    }
}

function closeFlowEditor() {
    currentFlowId = null;
    document.getElementById('flows-list-container').classList.remove('hidden');
    document.getElementById('flow-editor-container').classList.add('hidden');

    // Destroy Drawflow instance
    if (flowEditor) {
        flowEditor.clear();
    }
    loadFlowsView();
}

function initDrawflow(flowData) {
    const container = document.getElementById('drawflow-canvas');
    container.innerHTML = '';

    flowEditor = new Drawflow(container);
    flowEditor.reroute = true;
    flowEditor.start();

    // Import saved flow data into Drawflow format
    if (flowData && flowData.nodes && Object.keys(flowData.nodes).length > 0) {
        importFlowToDrawflow(flowData);
    }
}

function renderBlockPalette() {
    const palette = document.getElementById('flow-palette');
    if (!flowBlockCatalog.length) {
        palette.innerHTML = '<p style="color:var(--text-muted)">Loading blocks...</p>';
        return;
    }

    palette.innerHTML = flowBlockCatalog.map(block => `
        <div class="flow-palette-block" 
             draggable="true" 
             ondragstart="dragBlock(event, '${block.type}')"
             style="border-left: 3px solid ${block.color};">
            <i class="fa-solid ${block.icon}" style="color:${block.color}"></i>
            <span>${block.label}</span>
        </div>
    `).join('');

    // Also allow click-to-add
    palette.querySelectorAll('.flow-palette-block').forEach(el => {
        el.addEventListener('dblclick', () => {
            const type = el.getAttribute('ondragstart').match(/'(.+?)'/)[1];
            addBlockToCanvas(type);
        });
    });
}

let _blockCounter = 1;

function dragBlock(event, blockType) {
    event.dataTransfer.setData('blockType', blockType);
}

function addBlockToCanvas(blockType, posX, posY) {
    const block = flowBlockCatalog.find(b => b.type === blockType);
    if (!block || !flowEditor) return;

    const nodeId = `node_${_blockCounter++}`;

    // Build HTML for the Drawflow node
    const html = `
        <div class="flow-node-content" style="border-top: 3px solid ${block.color}">
            <div class="flow-node-header">
                <i class="fa-solid ${block.icon}" style="color:${block.color}"></i>
                <strong>${block.label}</strong>
            </div>
            <div class="flow-node-body">
                ${getBlockConfigHTML(blockType)}
            </div>
        </div>
    `;

    const x = posX || 50 + Math.random() * 300;
    const y = posY || 50 + Math.random() * 200;

    flowEditor.addNode(
        nodeId,
        block.inputs,  // number of input connections
        block.outputs, // number of output connections
        x, y,
        blockType,     // CSS class
        { type: blockType },  // data
        html
    );
}

function getBlockConfigHTML(blockType) {
    switch (blockType) {
        case 'ai_prompt':
            return `
                <select class="df-input" df-model style="margin-bottom:4px;">
                    <option value="gpt-4o">GPT-4o (OpenAI)</option>
                    <option value="gpt-4o-mini">GPT-4o Mini</option>
                    <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
                    <option value="nvidia/llama-3.1-405b-instruct">Llama 3.1 405B (Nvidia)</option>
                    <option value="nvidia/llama-3.1-70b-instruct">Llama 3.1 70B (Nvidia)</option>
                    <option value="google/gemini-2.0-flash-001">Gemini 2.0 Flash</option>
                    <option value="deepseek/deepseek-chat">DeepSeek Chat</option>
                </select>
                <textarea class="df-input" df-prompt placeholder="Enter prompt..." rows="2"></textarea>
            `;
        case 'terminal_command':
            return `<input type="text" class="df-input" df-command placeholder="ls -la or dir">`;
        case 'web_search':
            return `<input type="text" class="df-input" df-query placeholder="Search query...">`;
        case 'http_request':
            return `
                <select class="df-input" df-method><option>GET</option><option>POST</option><option>PUT</option><option>DELETE</option></select>
                <input type="text" class="df-input" df-url placeholder="https://api.example.com" style="margin-top:4px;">
            `;
        case 'condition':
            return `
                <input type="text" class="df-input" df-field placeholder="Field name" style="margin-bottom:4px;">
                <select class="df-input" df-operator><option>==</option><option>!=</option><option>contains</option><option>></option><option><</option></select>
                <input type="text" class="df-input" df-value placeholder="Value" style="margin-top:4px;">
            `;
        case 'output':
            return `<input type="text" class="df-input" df-message placeholder="Output message template">`;
        case 'send_email':
            return `
                <input type="text" class="df-input" df-to placeholder="To (e.g., user@email.com)" style="margin-bottom:4px;">
                <input type="text" class="df-input" df-subject placeholder="Subject">
            `;
        case 'send_telegram':
            return `
                <input type="text" class="df-input" df-chat_id placeholder="Target Chat ID" style="margin-bottom:4px;">
                <input type="text" class="df-input" df-message placeholder="Message text">
            `;
        case 'delay':
            return `<input type="number" class="df-input" df-seconds placeholder="Seconds" value="5">`;
        case 'schedule_trigger':
            return `<input type="text" class="df-input" df-cron placeholder="*/5 * * * * (cron)">`;
        case 'manual_trigger':
            return `
                <select class="df-input" df-timezone>
                    <option value="UTC">UTC</option>
                    <option value="IST">IST (India)</option>
                    <option value="EST">EST (Eastern)</option>
                    <option value="PST">PST (Pacific)</option>
                </select>
                <small style="color:var(--text-muted); display:block; margin-top:5px;">Injects Timezone ctx</small>
            `;
        default:
            return '<small style="color:var(--text-muted)">No config needed</small>';
    }
}

// Handle drop onto canvas
document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('drawflow-canvas');
    if (canvas) {
        canvas.addEventListener('drop', (e) => {
            e.preventDefault();
            const blockType = e.dataTransfer.getData('blockType');
            if (blockType && flowEditor) {
                const rect = canvas.getBoundingClientRect();
                const x = (e.clientX - rect.left) / flowEditor.zoom;
                const y = (e.clientY - rect.top) / flowEditor.zoom;
                addBlockToCanvas(blockType, x, y);
            }
        });
        canvas.addEventListener('dragover', (e) => e.preventDefault());
    }
});

// --- Export Drawflow → Flow JSON ---
function exportDrawflowToFlowJSON() {
    if (!flowEditor) return { nodes: {}, edges: [] };

    const dfData = flowEditor.export();
    const nodes = {};
    const edges = [];

    // Drawflow stores data in: dfData.drawflow.Home.data
    const homeData = dfData?.drawflow?.Home?.data || {};

    for (const [id, node] of Object.entries(homeData)) {
        const nodeId = node.name || `node_${id}`;
        const blockType = node.class || node.data?.type || 'unknown';

        // Extract config from node data
        const config = {};
        if (node.data) {
            Object.assign(config, node.data);
        }

        nodes[nodeId] = {
            type: blockType,
            config: config,
            position: { x: node.pos_x, y: node.pos_y }
        };

        // Build edges from outputs
        if (node.outputs) {
            for (const [outputKey, output] of Object.entries(node.outputs)) {
                for (const conn of output.connections) {
                    const targetNode = homeData[conn.node];
                    const targetId = targetNode?.name || `node_${conn.node}`;
                    edges.push({ from: nodeId, to: targetId });
                }
            }
        }
    }

    return { nodes, edges };
}

// --- Import Flow JSON → Drawflow ---
function importFlowToDrawflow(flowData) {
    if (!flowEditor || !flowData.nodes) return;

    _blockCounter = 1;
    const nodeMap = {}; // flowNodeId → drawflowId

    // Add nodes
    for (const [nodeId, node] of Object.entries(flowData.nodes)) {
        const block = flowBlockCatalog.find(b => b.type === node.type);
        if (!block) continue;

        const html = `
            <div class="flow-node-content" style="border-top: 3px solid ${block.color}">
                <div class="flow-node-header">
                    <i class="fa-solid ${block.icon}" style="color:${block.color}"></i>
                    <strong>${block.label}</strong>
                </div>
                <div class="flow-node-body">
                    ${getBlockConfigHTML(node.type)}
                </div>
            </div>
        `;

        const x = node.position?.x || 100;
        const y = node.position?.y || 100;

        const dfId = flowEditor.addNode(
            nodeId, block.inputs, block.outputs,
            x, y, node.type, node.config || {}, html
        );
        nodeMap[nodeId] = dfId;
        _blockCounter++;
    }

    // Add edges
    for (const edge of (flowData.edges || [])) {
        const fromId = nodeMap[edge.from];
        const toId = nodeMap[edge.to];
        if (fromId && toId) {
            try {
                flowEditor.addConnection(fromId, toId, 'output_1', 'input_1');
            } catch (e) { /* connection might fail if ports don't match */ }
        }
    }
}

// --- Save ---
async function saveCurrentFlow() {
    if (!currentFlowId) return;

    const name = document.getElementById('flow-name-input').value || 'Untitled Flow';
    const description = document.getElementById('flow-desc-input').value || '';
    const flowData = exportDrawflowToFlowJSON();

    try {
        await fetch(`${API_BASE}/flows/${currentFlowId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                description: description,
                flow_data: JSON.stringify(flowData)
            })
        });
        alert('Flow saved!');
    } catch (e) {
        alert('Failed to save: ' + e.message);
    }
}

// --- Run ---
async function runCurrentFlow() {
    if (!currentFlowId) return;

    // Save first
    await saveCurrentFlow();

    document.getElementById('flow-results-container').classList.remove('hidden');
    document.getElementById('flow-results-output').textContent = '⏳ Running flow...';

    try {
        const res = await fetch(`${API_BASE}/flows/${currentFlowId}/run`, { method: 'POST' });
        const result = await res.json();
        document.getElementById('flow-results-output').textContent = JSON.stringify(result, null, 2);
    } catch (e) {
        document.getElementById('flow-results-output').textContent = '❌ Error: ' + e.message;
    }
}

async function quickRunFlow(flowId) {
    try {
        const res = await fetch(`${API_BASE}/flows/${flowId}/run`, { method: 'POST' });
        const result = await res.json();
        alert(`Flow completed in ${result.elapsed_seconds}s\n\n${JSON.stringify(result.results, null, 2).substring(0, 500)}`);
    } catch (e) {
        alert('Run failed: ' + e.message);
    }
}

async function deleteFlow(flowId) {
    if (!confirm('Delete this flow?')) return;
    try {
        await fetch(`${API_BASE}/flows/${flowId}`, { method: 'DELETE' });
        loadFlowsView();
    } catch (e) {
        alert('Delete failed: ' + e.message);
    }
}

// ==========================================
// MAGIC WAND (PROMPT-TO-FLOW)
// ==========================================

function openMagicWandModal() {
    document.getElementById('magic-wand-modal').classList.remove('hidden');
    document.getElementById('magic-wand-prompt').value = '';
    document.getElementById('magic-wand-prompt').focus();
}

function closeMagicWandModal() {
    document.getElementById('magic-wand-modal').classList.add('hidden');
}

async function generateMagicFlow() {
    const prompt = document.getElementById('magic-wand-prompt').value.trim();
    if (!prompt) return alert('Please enter a description for your automation.');

    const btn = document.getElementById('btn-magic-generate');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating...';

    try {
        const res = await fetch(`${API_BASE}/flows/magic`, { // Use absolute path equivalent or mapped base depending on modern vs legacy config. Wait, for modern it's /magic, wait, in modern we registered it as router.post("/magic") but the prefix in main.py is likely /api/flows? Let's check api/routes/flows.py. Yes, the prefix for this router is /api/flows. So /api/flows/magic
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ prompt: prompt })
        });
        const flowData = await res.json();

        if (res.ok) {
            closeMagicWandModal();
            // Create a new flow automatically
            const flowName = prompt.split(" ").slice(0, 4).join(" ") + " Flow";
            const createRes = await fetch(`${API_BASE}/flows`, {
                method: 'POST',
                headers: {
                    ...getAuthHeader(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: flowName.charAt(0).toUpperCase() + flowName.slice(1),
                    description: prompt,
                    flow_data: JSON.stringify(flowData)
                })
            });

            if (createRes.ok) {
                const newFlow = await createRes.json();
                alert('✨ Magic Flow Created! Opening Editor...');
                loadFlowsView();
                openFlowEditor(newFlow.id, newFlow.name, newFlow.description, newFlow.flow_data);
            } else {
                alert('Failed to save generated flow.');
            }
        } else {
            alert('Generation Failed: ' + (flowData.detail || 'Unknown error'));
        }
    } catch (e) {
        alert('Error: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate';
    }
}

// ==========================================
// PHASE 19: UNIVERSAL APP INTEGRATIONS
// ==========================================

async function loadIntegrationsStatus() {
    try {
        // Slack
        const sRes = await fetch(`${API_BASE}/integrations/slack`);
        if (sRes.ok) {
            const sData = await sRes.json();
            const el = document.getElementById('slack-status');
            if (sData.configured) {
                el.innerHTML = '<i class="fa-solid fa-circle-check" style="color:var(--success-color);"></i> Configured & Ready';
            } else {
                el.innerHTML = '<i class="fa-solid fa-circle-xmark" style="color:var(--danger-color);"></i> Not Configured';
            }
        }

        // Google
        const gRes = await fetch(`${API_BASE}/integrations/google/status`);
        if (gRes.ok) {
            const gData = await gRes.json();
            const el = document.getElementById('google-status');
            if (gData.is_authenticated) {
                el.innerHTML = '<i class="fa-solid fa-circle-check" style="color:var(--success-color);"></i> Authenticated & Ready';
            } else if (gData.has_credentials) {
                el.innerHTML = '<i class="fa-solid fa-circle-exclamation" style="color:var(--warning-color);"></i> Credentials found, but Needs Auth (Try using a bot first)';
            } else {
                el.innerHTML = '<i class="fa-solid fa-circle-xmark" style="color:var(--danger-color);"></i> Not Configured';
            }
        }
    } catch (e) {
        console.error("Error loading integrations status:", e);
    }
}

async function saveSlackToken() {
    const token = document.getElementById('slack-token-input').value.trim();
    if (!token) return alert("Please enter a valid Slack Bot Token.");

    try {
        const res = await fetch(`${API_BASE}/integrations/slack`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: token })
        });
        const data = await res.json();
        alert(data.message || 'Saved successfully');
        document.getElementById('slack-token-input').value = '';
        loadIntegrationsStatus();
    } catch (e) {
        alert("Failed to save Slack token: " + e.message);
    }
}

async function uploadGoogleCreds() {
    const fileInput = document.getElementById('google-creds-file');
    if (!fileInput.files.length) return alert("Please select a credentials.json file.");

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const res = await fetch(`${API_BASE}/integrations/google/upload_credentials`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (res.ok) {
            alert(data.message || 'Uploaded successfully');
            loadIntegrationsStatus();
        } else {
            alert('Upload failed: ' + data.detail);
        }
    } catch (e) {
        alert("Failed to upload credentials: " + e.message);
    }
}

// ==========================================
// PHASE 20: WATCH AND LEARN MACROS
// ==========================================

let isRecordingMacro = false;

async function toggleMacroRecording() {
    const btn = document.getElementById('btn-record-macro');
    if (!isRecordingMacro) {
        try {
            const res = await fetch(`${API_BASE}/macros/start`, { method: 'POST' });
            const data = await res.json();
            if (res.ok) {
                isRecordingMacro = true;
                btn.classList.remove('btn-warning');
                btn.classList.add('btn-danger');
                btn.innerHTML = '<i class="fa-solid fa-stop"></i> Stop Recording';
                alert('Recording started. Do your actions now, then click Stop Recording.');
            } else {
                alert('Failed to start: ' + data.detail);
            }
        } catch (e) {
            alert('Error: ' + e);
        }
    } else {
        try {
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...';
            btn.disabled = true;

            const res = await fetch(`${API_BASE}/macros/stop`, { method: 'POST' });
            const data = await res.json();
            if (res.ok) {
                isRecordingMacro = false;
                const sessionId = data.session_id;

                // Analyze
                const anRes = await fetch(`${API_BASE}/macros/${sessionId}/analyze`, { method: 'POST' });
                const anData = await anRes.json();

                if (anRes.ok && anData.flow_data) {
                    alert('Macro analyzed! Creating Flow...');

                    // Create a flow with this data
                    const flowDatObj = typeof anData.flow_data.flow_data === 'string' ? JSON.parse(anData.flow_data.flow_data) : anData.flow_data.flow_data;
                    const createRes = await fetch(`${API_BASE}/flows/`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            name: anData.flow_data.name || 'Recorded Macro',
                            description: anData.flow_data.description || '',
                            flow_data: JSON.stringify(flowDatObj)
                        })
                    });

                    if (createRes.ok) {
                        const newFlow = await createRes.json();
                        loadFlowsView();
                        openFlowEditor(newFlow.id, newFlow.name, newFlow.description, newFlow.flow_data);
                    }
                } else {
                    alert('Analysis failed: ' + (anData.detail || 'Unknown error'));
                }
            }
        } catch (e) {
            alert('Error: ' + e);
        } finally {
            btn.disabled = false;
            btn.classList.remove('btn-danger');
            btn.classList.add('btn-warning');
            btn.innerHTML = '<i class="fa-solid fa-video"></i> Record Macro';
        }
    }
}

// ==========================================
// PHASE 21: PLUGIN MARKETPLACE
// ==========================================

async function loadMarketplace() {
    const listEl = document.getElementById('marketplace-list');
    listEl.innerHTML = '<p style="color:var(--text-muted);">Loading plugins...</p>';

    try {
        const [storeRes, installedRes] = await Promise.all([
            fetch(`${API_BASE}/marketplace/`),
            fetch(`${API_BASE}/marketplace/installed`)
        ]);

        const storeData = await storeRes.json();
        const instData = await installedRes.json();
        const installedIds = instData.installed || [];

        if (storeData.plugins.length === 0) {
            listEl.innerHTML = '<p style="color:var(--text-muted);">No plugins available in the store yet.</p>';
            return;
        }

        listEl.innerHTML = storeData.plugins.map(p => {
            const isInstalled = installedIds.includes(p.id);
            const actionBtn = isInstalled
                ? `<button class="btn btn-danger btn-sm" onclick="uninstallPlugin('${p.id}')"><i class="fa-solid fa-trash"></i> Uninstall</button>`
                : `<button class="btn btn-primary btn-sm" onclick="installPlugin('${p.id}')"><i class="fa-solid fa-download"></i> Install</button>`;

            return `
            <div class="card" style="border-left: 4px solid #8b5cf6;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <h4 style="margin:0;">${p.name}</h4>
                        <p style="font-size:0.8em; color:var(--text-muted); margin:4px 0;">by ${p.author} &bull; <i class="fa-solid fa-download"></i> ${p.downloads}</p>
                    </div>
                    ${isInstalled ? '<span class="badge" style="background:var(--success-color);">Installed</span>' : ''}
                </div>
                <p style="font-size:0.85em; margin:10px 0;">${p.description}</p>
                <div style="text-align:right; margin-top:10px;">
                    ${actionBtn}
                </div>
            </div>`;
        }).join('');

    } catch (e) {
        listEl.innerHTML = `<p style="color:var(--danger-color);">Error loading marketplace: ${e.message}</p>`;
    }
}

async function installPlugin(pluginId) {
    try {
        const res = await fetch(`${API_BASE}/marketplace/install/${pluginId}`, {
            method: 'POST',
            headers: getAuthHeader()
        });
        const data = await res.json();
        if (res.ok) {
            alert(data.message);
            loadMarketplace();
        } else {
            alert('Install failed: ' + data.detail);
        }
    } catch (e) {
        alert('Error: ' + e);
    }
}

async function uninstallPlugin(pluginId) {
    if (!confirm('Uninstall this plugin?')) return;
    try {
        const res = await fetch(`${API_BASE}/marketplace/uninstall/${pluginId}`, {
            method: 'POST',
            headers: getAuthHeader()
        });
        const data = await res.json();
        if (res.ok) {
            alert(data.message);
            loadMarketplace();
        } else {
            alert('Uninstall failed: ' + data.detail);
        }
    } catch (e) {
        alert('Error: ' + e);
    }
}

// ==========================================
// FLOW TEMPLATES GALLERY
// ==========================================

async function showFlowTemplates() {
    try {
        const resp = await fetch(`${API_BASE}/flow-templates`, {
            headers: getAuthHeader()
        });
        const data = await resp.json();

        if (!resp.ok || !data.templates || data.templates.length === 0) {
            alert('No flow templates available.');
            return;
        }

        const modal = document.createElement('div');
        modal.id = 'flow-templates-modal';
        modal.style.cssText = 'position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.6); z-index:10000; display:flex; align-items:center; justify-content:center;';

        const inner = document.createElement('div');
        inner.style.cssText = 'background:var(--card-bg, #fff); border-radius:16px; padding:30px; max-width:700px; width:90%; max-height:80vh; overflow-y:auto; box-shadow:0 20px 60px rgba(0,0,0,0.3);';

        inner.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h2 style="margin:0;"><i class="fa-solid fa-book-open"></i> Flow Templates</h2>
                <button onclick="document.getElementById('flow-templates-modal').remove()" class="btn btn-sm" style="font-size:1.2em;">✕</button>
            </div>
            <p style="color:var(--text-muted); margin-bottom:20px;">Click "Import" to create a new flow from a pre-built template.</p>
            <div id="flow-tpl-list"></div>
        `;

        const listEl = inner.querySelector('#flow-tpl-list');
        data.templates.forEach(tpl => {
            const card = document.createElement('div');
            card.style.cssText = 'padding:16px; border:1px solid var(--border-color); border-radius:12px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; transition:all 0.2s;';
            card.innerHTML = `
                <div>
                    <h4 style="margin:0;">${tpl.name}</h4>
                    <p style="font-size:0.85em; color:var(--text-muted); margin:4px 0 0 0;">${tpl.description}</p>
                    <span style="font-size:0.75em; color:var(--accent-color); font-weight:600;">${tpl.category}</span>
                </div>
                <button class="btn btn-primary btn-sm" onclick="importFlowTemplate('${tpl.id}')">
                    <i class="fa-solid fa-download"></i> Import
                </button>
            `;
            card.addEventListener('mouseenter', () => { card.style.background = 'var(--accent-color)08'; card.style.borderColor = 'var(--accent-color)'; });
            card.addEventListener('mouseleave', () => { card.style.background = ''; card.style.borderColor = 'var(--border-color)'; });
            listEl.appendChild(card);
        });

        modal.appendChild(inner);
        modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
        document.body.appendChild(modal);
    } catch (err) {
        alert('Failed to load templates: ' + err.message);
    }
}

async function importFlowTemplate(templateId) {
    try {
        const resp = await fetch(`${API_BASE}/flow-templates/${templateId}`, {
            headers: getAuthHeader()
        });
        const tpl = await resp.json();

        if (!resp.ok || !tpl.flow_data) {
            alert('Failed to load template data.');
            return;
        }

        // Create a new flow with this template data
        const createResp = await fetch(`${API_BASE}/flows`, {
            method: 'POST',
            headers: {
                ...getAuthHeader(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: tpl.name.replace(/^[^\w]*/, '').trim() || 'Template Flow',
                description: tpl.description || '',
                flow_data: JSON.stringify(tpl.flow_data)
            })
        });

        if (createResp.ok) {
            const newFlow = await createResp.json();
            // Close the modal
            const modal = document.getElementById('flow-templates-modal');
            if (modal) modal.remove();

            alert('✅ Flow created from template! Opening editor...');
            loadFlowsView();
            openFlowEditor(newFlow.id, newFlow.name, newFlow.description, newFlow.flow_data);
        }
    } catch (err) {
        alert('Error importing template: ' + err.message);
    }
}

// ==========================================
// PLUGIN MARKETPLACE
// ==========================================
async function loadMarketplacePlugins(tab = 'store') {
    // Update button styling
    document.getElementById('btn-market-store').className = tab === 'store' ? 'btn btn-primary' : 'btn btn-secondary';
    document.getElementById('btn-market-installed').className = tab === 'installed' ? 'btn btn-primary' : 'btn btn-secondary';

    const container = document.getElementById('marketplace-list');
    container.innerHTML = '<p style="color:var(--text-muted);">Loading plugins...</p>';

    try {
        if (tab === 'store') {
            const resp = await fetch(`${API_BASE}/marketplace`, { headers: getAuthHeader() });
            const data = await resp.json();

            // Also fetch installed plugins to show correct button state
            const installedResp = await fetch(`${API_BASE}/marketplace/installed`, { headers: getAuthHeader() });
            const installedData = await installedResp.json();

            renderMarketplaceStore(data.plugins, installedData.installed);
        } else {
            const resp = await fetch(`${API_BASE}/marketplace/installed`, { headers: getAuthHeader() });
            const data = await resp.json();
            renderMarketplaceInstalled(data.installed);
        }
    } catch (err) {
        container.innerHTML = `<p style="color:var(--danger-color);">Error loading marketplace: ${err.message}</p>`;
    }
}

function renderMarketplaceStore(plugins, installedList) {
    const container = document.getElementById('marketplace-list');
    container.innerHTML = '';

    if (!plugins || plugins.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);">No plugins available in the store right now.</p>';
        return;
    }

    plugins.forEach(p => {
        const isInstalled = installedList.includes(p.id);
        const card = document.createElement('div');
        card.className = 'card';
        card.style.cssText = 'display:flex; flex-direction:column; justify-content:space-between; height:100%;';
        card.innerHTML = `
            <div>
                <h3 style="margin-top:0; margin-bottom:5px;">${p.name}</h3>
                <span style="font-size:0.8em; color:var(--text-muted);">by ${p.author} | ${p.downloads} Dls</span>
                <p style="font-size:0.9em; margin-top:10px; color:var(--text-color);">${p.description}</p>
            </div>
            <div style="margin-top:15px;">
                ${isInstalled ?
                `<button class="btn btn-secondary btn-sm" disabled style="width:100%;">Installed <i class="fa-solid fa-check"></i></button>` :
                `<button class="btn btn-primary btn-sm" onclick="installPlugin('${p.id}')" style="width:100%;">Install <i class="fa-solid fa-download"></i></button>`
            }
            </div>
        `;
        container.appendChild(card);
    });
}

function renderMarketplaceInstalled(installedIds) {
    const container = document.getElementById('marketplace-list');
    container.innerHTML = '';

    if (!installedIds || installedIds.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);">No plugins installed yet.</p>';
        return;
    }

    installedIds.forEach(id => {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.cssText = 'display:flex; justify-content:space-between; align-items:center; border-left:4px solid var(--success-color);';
        card.innerHTML = `
            <div>
                <h3 style="margin:0;">${id}</h3>
                <p style="font-size:0.8em; color:var(--text-muted); margin:4px 0 0 0;">Local Plugin Script</p>
            </div>
            <button class="btn btn-danger btn-sm" onclick="uninstallPlugin('${id}')">
                <i class="fa-solid fa-trash"></i> Uninstall
            </button>
        `;
        container.appendChild(card);
    });
}

async function installPlugin(pluginId) {
    try {
        const resp = await fetch(`${API_BASE}/marketplace/install/${pluginId}`, {
            method: 'POST',
            headers: getAuthHeader()
        });
        const data = await resp.json();
        if (resp.ok) {
            alert("✅ " + data.message);
            loadMarketplacePlugins('store'); // refresh
        } else {
            alert('Failed: ' + (data.detail || 'Unknown error'));
        }
    } catch (err) {
        alert('Error installing plugin: ' + err.message);
    }
}

async function uninstallPlugin(pluginId) {
    if (!confirm("Are you sure you want to uninstall " + pluginId + "?")) return;
    try {
        const resp = await fetch(`${API_BASE}/marketplace/uninstall/${pluginId}`, {
            method: 'POST',
            headers: getAuthHeader()
        });
        const data = await resp.json();
        if (resp.ok) {
            alert("✅ " + data.message);
            loadMarketplacePlugins('installed'); // refresh
        } else {
            alert('Failed: ' + (data.detail || 'Unknown error'));
        }
    } catch (err) {
        alert('Error uninstalling plugin: ' + err.message);
    }
}

async function checkLocalAI() {
    try {
        const resp = await fetch(`${API_BASE}/health`);
        const data = await resp.json();
        // The backend already checks for Ollama during init, we can just ask if it's there
        // Or we try to ping it directly from the browser since it's local
        const ollamaResp = await fetch('http://localhost:11434/api/tags');
        if (ollamaResp.ok) {
            document.getElementById('local-ai-notice').style.display = 'block';
        }
    } catch (e) {
        // Ollama not running or blocked
    }
}

// ==========================================
// WAR ROOM / SWARM LOGIC
// ==========================================
async function loadWarRoom() {
    try {
        const resp = await fetch(`${API_BASE}/bots`, { headers: getAuthHeader() });
        const data = await resp.json();

        const managerSelect = document.getElementById('warroom-manager-select');
        const subBotList = document.getElementById('warroom-subbot-list');

        if (!managerSelect || !subBotList) return;

        managerSelect.innerHTML = '<option value="">-- Select Manager Bot --</option>';
        subBotList.innerHTML = '';

        data.bots.forEach(bot => {
            // Add to manager select
            const opt = document.createElement('option');
            opt.value = bot.id;
            opt.textContent = `${bot.name} (${bot.model})`;
            managerSelect.appendChild(opt);

            // Add to sub-bot checklist
            const div = document.createElement('div');
            div.style.cssText = 'padding: 8px; border-bottom: 1px solid var(--border-color); display:flex; align-items:center; gap:10px;';
            div.innerHTML = `
                <input type="checkbox" id="warbot-${bot.id}" value="${bot.id}" class="warbot-checkbox" style="width:16px; height:16px;">
                <label for="warbot-${bot.id}" style="margin:0; cursor:pointer;"><strong>${bot.name}</strong> <span style="font-size:0.8em; color:var(--text-muted);">(${bot.model})</span></label>
            `;
            subBotList.appendChild(div);
        });
    } catch (e) {
        console.error("Failed to load bots for War Room:", e);
    }
}

async function startWarRoom() {
    const managerSelect = document.getElementById('warroom-manager-select');
    const checkboxes = document.querySelectorAll('.warbot-checkbox:checked');

    if (!managerSelect.value) {
        alert("Please select a Manager Bot.");
        return;
    }
    if (checkboxes.length === 0) {
        alert("Please select at least one Sub-Bot.");
        return;
    }

    const taskPrompt = prompt("Enter the complex task for the Manager to orchestrate:");
    if (!taskPrompt) return;

    // Switch UI to active war room
    document.getElementById('war-room-setup').classList.add('hidden');
    const activeView = document.getElementById('war-room-active');
    if (activeView) activeView.classList.remove('hidden');

    const logsEl = document.getElementById('war-room-logs');
    if (logsEl) {
        logsEl.innerHTML = `<p style="color:var(--accent-color);">[SYSTEM] Swarm Orchestration Started</p>
                            <p>> Task: ${taskPrompt}</p>
                            <p>> Manager processing and dispatching workers...</p>`;
    }

    const workerIds = Array.from(checkboxes).map(cb => cb.value);

    try {
        const resp = await fetch(`${API_BASE}/swarm/execute`, {
            method: 'POST',
            headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task: taskPrompt,
                manager_bot_id: managerSelect.value,
                worker_bot_ids: workerIds
            })
        });

        const result = await resp.json();

        if (resp.ok) {
            if (logsEl) {
                logsEl.innerHTML += `<p style="color:var(--success-color);">[SYSTEM] Swarm Task Complete!</p>`;

                result.worker_results.forEach(r => {
                    logsEl.innerHTML += `<p style="color:var(--text-muted);">> Worker ${r.bot_id} finished execution.</p>`;
                });

                logsEl.innerHTML += `<div style="margin-top:20px; padding:15px; border-top:1px solid var(--border-color); background:var(--bg-secondary); border-radius:8px;">
                    <h4 style="margin-top:0;">Manager Final Synthesis:</h4>
                    <p style="white-space:pre-wrap;">${result.final_answer.replace(/\\n/g, '<br>')}</p>
                </div>`;
            }
        } else {
            if (logsEl) logsEl.innerHTML += `<p style="color:var(--danger-color);">[ERROR] ${result.detail}</p>`;
        }
    } catch (e) {
        if (logsEl) logsEl.innerHTML += `<p style="color:var(--danger-color);">[FATAL ERROR] ${e.message}</p>`;
    }
}

// ==========================================
// PHASE 13: ACTIVITY FEED
// ==========================================
async function loadActivityFeed() {
    const container = document.getElementById('activity-feed-list');
    if (!container) return;
    try {
        const resp = await fetch(`${API_BASE}/activity?limit=30`, { headers: getAuthHeader() });
        const data = await resp.json();
        container.innerHTML = '';
        if (!data.events || data.events.length === 0) {
            container.innerHTML = '<p style="color:var(--text-muted);">No recent activity.</p>';
            return;
        }
        data.events.forEach(ev => {
            const div = document.createElement('div');
            div.style.cssText = 'padding:8px 12px; border-bottom:1px solid var(--border-color); font-size:0.9em;';
            const ts = new Date(ev.ts).toLocaleTimeString();
            const icon = { bot_ping: '🤖', flow: '⚙️', macro: '🎬', swarm: '🐝', plugin: '🧩', webhook: '🔗', clipboard: '📋', scheduler: '🗓️' }[ev.type] || '📌';
            div.innerHTML = `<span style="color:var(--text-muted);">${ts}</span> ${icon} <strong>${ev.type}</strong> — ${ev.detail}`;
            container.appendChild(div);
        });
    } catch (e) {
        if (container) container.innerHTML = '<p style="color:var(--danger-color);">Failed to load activity.</p>';
    }
}

// ==========================================
// PHASE 13: VOICE INPUT / OUTPUT
// ==========================================
function startVoiceInput() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert("Voice input is not supported in this browser. Try Chrome.");
        return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            chatInput.value = transcript;
        }
    };
    recognition.onerror = (event) => {
        console.error("Voice recognition error:", event.error);
        alert("Voice error: " + event.error);
    };
    recognition.start();
}

function speakResponse(text) {
    if (!window.speechSynthesis) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
}

// ==========================================
// PHASE 13: MEMORY SEARCH
// ==========================================
async function searchMemory() {
    const queryInput = document.getElementById('memory-search-input');
    const resultsDiv = document.getElementById('memory-search-results');
    if (!queryInput || !resultsDiv) return;

    const q = queryInput.value.trim();
    if (!q) { alert("Enter a search term."); return; }

    resultsDiv.innerHTML = '<p style="color:var(--text-muted);">Searching...</p>';
    try {
        const resp = await fetch(`${API_BASE}/memory/search?q=${encodeURIComponent(q)}`, { headers: getAuthHeader() });
        const data = await resp.json();
        resultsDiv.innerHTML = '';
        if (data.result_count === 0) {
            resultsDiv.innerHTML = '<p style="color:var(--text-muted);">No matches found.</p>';
            return;
        }
        data.results.forEach(r => {
            const card = document.createElement('div');
            card.className = 'card';
            card.style.marginBottom = '10px';
            let snippetsHtml = r.matches.map(m =>
                `<p style="font-size:0.85em; color:var(--text-color); margin:4px 0;"><strong>${m.role}:</strong> ${m.snippet}</p>`
            ).join('');
            card.innerHTML = `<h4 style="margin:0 0 5px 0;">${r.title || 'Chat'}</h4>${snippetsHtml}`;
            resultsDiv.appendChild(card);
        });
    } catch (e) {
        resultsDiv.innerHTML = '<p style="color:var(--danger-color);">Search failed.</p>';
    }
}

// ==========================================
// PHASE 13: BOT EXPORT / IMPORT
// ==========================================
async function exportBot(botId) {
    try {
        const resp = await fetch(`${API_BASE}/bots/${botId}/export`, { headers: getAuthHeader() });
        const data = await resp.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = (data.name || 'wolfbot') + '.wolfbot';
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        alert("Export failed: " + e.message);
    }
}

async function importBot() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.wolfbot,.json';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = async (ev) => {
            try {
                const wolfbot = JSON.parse(ev.target.result);
                const resp = await fetch(`${API_BASE}/bots/import`, {
                    method: 'POST',
                    headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
                    body: JSON.stringify(wolfbot)
                });
                const data = await resp.json();
                if (resp.ok) {
                    alert("✅ Bot imported: " + data.name);
                    loadBots();
                } else {
                    alert("Import failed: " + (data.detail || "Unknown error"));
                }
            } catch (err) {
                alert("Invalid .wolfbot file: " + err.message);
            }
        };
        reader.readAsText(file);
    };
    input.click();
}

// ==========================================
// PHASE 13: SCREENSHOT PASTE TO CHAT
// ==========================================
function initScreenshotPaste() {
    const chatInput = document.getElementById('chat-input');
    if (!chatInput) return;

    chatInput.addEventListener('paste', async (e) => {
        const items = e.clipboardData && e.clipboardData.items;
        if (!items) return;

        for (let item of items) {
            if (item.type.indexOf('image') !== -1) {
                e.preventDefault();
                const blob = item.getAsFile();
                const reader = new FileReader();
                reader.onload = async (ev) => {
                    const base64 = ev.target.result.split(',')[1];
                    const prompt = chatInput.value || "Analyze this screenshot.";

                    // Show loading state
                    const chatBox = document.getElementById('chat-messages');
                    if (chatBox) {
                        chatBox.innerHTML += '<div class="chat-message user"><p>📸 [Screenshot pasted for analysis]</p></div>';
                        chatBox.innerHTML += '<div class="chat-message bot"><p style="color:var(--text-muted);">Analyzing image...</p></div>';
                        chatBox.scrollTop = chatBox.scrollHeight;
                    }

                    try {
                        const resp = await fetch(`${API_BASE}/chat/vision`, {
                            method: 'POST',
                            headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
                            body: JSON.stringify({ image_base64: base64, prompt: prompt })
                        });
                        const data = await resp.json();
                        if (resp.ok && chatBox) {
                            chatBox.lastElementChild.innerHTML = '<p>' + data.analysis + '</p>';
                        } else if (chatBox) {
                            chatBox.lastElementChild.innerHTML = '<p style="color:var(--danger-color);">' + (data.detail || 'VLM analysis failed.') + '</p>';
                        }
                    } catch (err) {
                        if (chatBox) chatBox.lastElementChild.innerHTML = '<p style="color:var(--danger-color);">Error: ' + err.message + '</p>';
                    }
                };
                reader.readAsDataURL(blob);
                break;
            }
        }
    });
}

// Initialize screenshot paste when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initScreenshotPaste, 1000);
    setTimeout(initNotificationBell, 1500);
    setTimeout(loadTheme, 200);
    setTimeout(checkOnboarding, 2000);
});

// ==========================================
// PHASE 14: DASHBOARD HOME
// ==========================================
async function loadDashboardHome() {
    const container = document.getElementById('dashboard-home');
    if (!container) return;
    try {
        const resp = await fetch(`${API_BASE}/dashboard/home`, { headers: getAuthHeader() });
        const d = await resp.json();
        container.innerHTML = `
            <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:20px;">
                <div class="card" style="text-align:center;"><h2>${d.chats_today}</h2><small>Chats Today</small></div>
                <div class="card" style="text-align:center;"><h2>${d.total_bots}</h2><small>Total Bots</small></div>
                <div class="card" style="text-align:center;"><h2>${d.total_flows}</h2><small>Total Flows</small></div>
                <div class="card" style="text-align:center;"><h2>${d.tokens_today.toLocaleString()}</h2><small>Tokens Today</small></div>
            </div>
            ${d.top_bot ? `<p><strong>🏆 Top Bot:</strong> ${d.top_bot.name} (${d.top_bot.chats} chats)</p>` : ''}
            <div style="display:flex;gap:10px;margin-top:16px;">
                <button class="btn btn-primary" onclick="navigateTo('chat')">💬 New Chat</button>
                <button class="btn" onclick="navigateTo('bots')">🤖 Create Bot</button>
                <button class="btn" onclick="navigateTo('flows')">⚙️ Run Flow</button>
            </div>
        `;
    } catch (e) { console.error('Dashboard home error:', e); }
}

// ==========================================
// PHASE 14: NOTIFICATION BELL
// ==========================================
function initNotificationBell() {
    const header = document.querySelector('.header-right, .top-bar, nav');
    if (!header) return;
    const bell = document.createElement('div');
    bell.id = 'notif-bell';
    bell.style.cssText = 'position:relative;cursor:pointer;display:inline-block;margin-right:16px;font-size:1.3em;';
    bell.innerHTML = '🔔<span id="notif-badge" style="position:absolute;top:-5px;right:-8px;background:var(--danger-color);color:#fff;border-radius:50%;font-size:0.6em;padding:2px 5px;display:none;">0</span>';
    bell.onclick = toggleNotifDrawer;
    header.prepend(bell);
    setInterval(pollNotifications, 15000);
    pollNotifications();
}

async function pollNotifications() {
    try {
        const resp = await fetch(`${API_BASE}/notifications/count`, { headers: getAuthHeader() });
        const data = await resp.json();
        const badge = document.getElementById('notif-badge');
        if (badge) {
            if (data.unread_count > 0) {
                badge.textContent = data.unread_count;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }
        }
    } catch (e) { }
}

async function toggleNotifDrawer() {
    let drawer = document.getElementById('notif-drawer');
    if (drawer) { drawer.remove(); return; }
    drawer = document.createElement('div');
    drawer.id = 'notif-drawer';
    drawer.style.cssText = 'position:fixed;top:50px;right:20px;width:360px;max-height:400px;overflow-y:auto;background:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,0.3);z-index:9999;padding:16px;';
    try {
        const resp = await fetch(`${API_BASE}/notifications?limit=20`, { headers: getAuthHeader() });
        const data = await resp.json();
        let html = '<div style="display:flex;justify-content:space-between;margin-bottom:12px;"><h3 style="margin:0;">Notifications</h3><button onclick="markAllNotifRead()" style="font-size:0.8em;cursor:pointer;background:none;border:none;color:var(--accent-color);">Mark All Read</button></div>';
        if (!data.notifications || data.notifications.length === 0) {
            html += '<p style="color:var(--text-muted);">No notifications.</p>';
        } else {
            data.notifications.forEach(n => {
                const opacity = n.read ? '0.5' : '1';
                html += `<div style="padding:8px 0;border-bottom:1px solid var(--border-color);opacity:${opacity};"><strong>${n.title}</strong><br><small style="color:var(--text-muted);">${n.ts}</small><br><span style="font-size:0.85em;">${n.body.substring(0, 120)}</span></div>`;
            });
        }
        drawer.innerHTML = html;
    } catch (e) { drawer.innerHTML = '<p>Error loading notifications.</p>'; }
    document.body.appendChild(drawer);
}

async function markAllNotifRead() {
    await fetch(`${API_BASE}/notifications/read-all`, { method: 'POST', headers: getAuthHeader() });
    pollNotifications();
    const drawer = document.getElementById('notif-drawer');
    if (drawer) drawer.remove();
}

// ==========================================
// PHASE 14: THEME ENGINE
// ==========================================
async function loadTheme() {
    try {
        const resp = await fetch(`${API_BASE}/theme`, { headers: getAuthHeader() });
        const data = await resp.json();
        applyTheme(data.mode, data.accent);
    } catch (e) { }
}

function applyTheme(mode, accent) {
    document.documentElement.setAttribute('data-theme', mode);
    if (accent) document.documentElement.style.setProperty('--accent-color', accent);
}

async function setTheme(mode, accent) {
    await fetch(`${API_BASE}/theme`, {
        method: 'POST',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode, accent })
    });
    applyTheme(mode, accent);
}

// ==========================================
// PHASE 14: PINNED PROMPTS
// ==========================================
async function loadPinnedPrompts() {
    const container = document.getElementById('pinned-prompts-bar');
    if (!container) return;
    try {
        const resp = await fetch(`${API_BASE}/pinned-prompts`, { headers: getAuthHeader() });
        const data = await resp.json();
        container.innerHTML = '';
        if (data.prompts && data.prompts.length > 0) {
            data.prompts.forEach(p => {
                const btn = document.createElement('button');
                btn.className = 'btn btn-sm';
                btn.style.cssText = 'margin:2px 4px;font-size:0.85em;';
                btn.textContent = `${p.icon} ${p.label}`;
                btn.onclick = () => { document.getElementById('chat-input').value = p.prompt; };
                container.appendChild(btn);
            });
        }
    } catch (e) { }
}

async function pinCurrentPrompt() {
    const input = document.getElementById('chat-input');
    if (!input || !input.value.trim()) return;
    const label = prompt("Give this prompt a short label:");
    if (!label) return;
    await fetch(`${API_BASE}/pinned-prompts`, {
        method: 'POST',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ label, prompt: input.value.trim() })
    });
    loadPinnedPrompts();
}

// ==========================================
// PHASE 14: CHAT EXPORT
// ==========================================
async function exportCurrentChat(format = 'markdown') {
    const chatId = window._currentChatId;
    if (!chatId) { alert('No chat selected.'); return; }
    try {
        const resp = await fetch(`${API_BASE}/chat/${chatId}/export?format=${format}`, { headers: getAuthHeader() });
        const text = await resp.text();
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chat_export.${format === 'markdown' ? 'md' : 'txt'}`;
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) { alert('Export failed: ' + e.message); }
}

// ==========================================
// PHASE 14: DOCUMENT UPLOAD (RAG CHAT)
// ==========================================
async function uploadDocForRAG() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.docx,.doc,.txt,.csv,.md';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        try {
            const resp = await fetch(`${API_BASE}/chat/upload-doc`, {
                method: 'POST',
                headers: getAuthHeader(),
                body: formData
            });
            const data = await resp.json();
            if (resp.ok) {
                alert(`✅ ${data.message}\n\nDoc ID: ${data.doc_id}`);
                window._activeDocId = data.doc_id;
            } else {
                alert('Upload failed: ' + (data.detail || 'Error'));
            }
        } catch (err) { alert('Upload error: ' + err.message); }
    };
    input.click();
}

// ==========================================
// PHASE 14: ONBOARDING WIZARD
// ==========================================
async function checkOnboarding() {
    try {
        const resp = await fetch(`${API_BASE}/onboarding/status`, { headers: getAuthHeader() });
        const data = await resp.json();
        if (data.dismissed || data.all_complete) return;
        showOnboardingWizard(data);
    } catch (e) { }
}

function showOnboardingWizard(data) {
    const overlay = document.createElement('div');
    overlay.id = 'onboarding-overlay';
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:10000;display:flex;align-items:center;justify-content:center;';
    let stepsHtml = data.steps.map(s => `
        <div style="display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid var(--border-color);">
            <span style="font-size:1.5em;">${s.complete ? '✅' : '⬜'}</span>
            <div>
                <strong>${s.label}</strong>
                ${!s.complete ? `<br><button class="btn btn-sm" onclick="navigateTo('${s.route.toLowerCase()}');document.getElementById('onboarding-overlay').remove();">Go →</button>` : ''}
            </div>
        </div>
    `).join('');
    overlay.innerHTML = `
        <div style="background:var(--card-bg);border-radius:16px;padding:32px;max-width:460px;width:90%;">
            <h2>🐺 Welcome to Wolfclaw!</h2>
            <p style="color:var(--text-muted);">Complete these steps to get started (${data.progress}/${data.total})</p>
            <div style="background:var(--accent-color);height:6px;border-radius:3px;margin:12px 0;">
                <div style="background:#fff;height:100%;border-radius:3px;width:${(data.progress / data.total) * 100}%;"></div>
            </div>
            ${stepsHtml}
            <button class="btn" style="margin-top:16px;width:100%;" onclick="dismissOnboarding()">Skip for Now</button>
        </div>
    `;
    document.body.appendChild(overlay);
}

async function dismissOnboarding() {
    await fetch(`${API_BASE}/onboarding/dismiss`, { method: 'POST', headers: getAuthHeader() });
    document.getElementById('onboarding-overlay')?.remove();
}

// ==========================================
// PHASE 16: WALLET & USAGE DASHBOARD
// ==========================================

async function loadWalletBotsDropdown() {
    const select = document.getElementById('wallet-bot-select');
    if (!select) return;

    // Check if bots are loaded
    if (Object.keys(activeBots).length === 0) {
        // Fetch them if not
        try {
            const resp = await fetch(`${API_BASE}/bots/`);
            const data = await resp.json();
            if (resp.ok && data.bots) {
                activeBots = data.bots;
            }
        } catch (e) {
            console.error(e);
        }
    }

    select.innerHTML = '<option value="">Select a Bot to View</option>';
    for (const [id, bot] of Object.entries(activeBots)) {
        const opt = document.createElement('option');
        opt.value = id;
        opt.textContent = `${bot.name} (${bot.model})`;
        select.appendChild(opt);
    }
}

async function loadWalletData() {
    const botId = document.getElementById('wallet-bot-select').value;
    const container = document.getElementById('wallet-metrics-container');

    if (!botId) {
        container.style.display = 'none';
        return;
    }

    try {
        const resp = await fetch(`${API_BASE}/wallet/summary/${botId}`);
        const data = await resp.json();

        if (resp.ok && data.wallet) {
            container.style.display = 'block';

            document.getElementById('wallet-today-spend').innerText = `$${data.wallet.today_spend.toFixed(4)}`;
            document.getElementById('wallet-remaining-budget').innerText = `$${data.wallet.remaining.toFixed(4)}`;
            document.getElementById('wallet-daily-budget').innerText = `$${data.wallet.daily_budget.toFixed(4)}`;

            const remainingColor = data.wallet.remaining > 0 ? "var(--success-color)" : "var(--danger-color)";
            document.getElementById('wallet-remaining-budget').style.color = remainingColor;
        } else {
            alert("Failed to load wallet data: " + (data.detail || "Unknown error"));
        }
    } catch (err) {
        console.error("Failed to load wallet data", err);
        alert("Connection error fetching wallet data.");
    }
}

async function updateWalletBudget() {
    const botId = document.getElementById('wallet-bot-select').value;
    const amount = document.getElementById('wallet-new-budget').value;
    const statusLabel = document.getElementById('status-wallet-update');

    if (!botId) {
        statusLabel.innerHTML = '<span style="color:var(--danger-color);">Select a bot first.</span>';
        return;
    }

    if (amount === '' || parseFloat(amount) < 0) {
        statusLabel.innerHTML = '<span style="color:var(--danger-color);">Enter a valid amount.</span>';
        return;
    }

    const parsedAmount = parseFloat(amount);
    statusLabel.innerText = "Updating...";

    try {
        const resp = await fetch(`${API_BASE}/wallet/setup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                bot_id: botId,
                daily_budget: parsedAmount
            })
        });

        const data = await resp.json();

        if (resp.ok) {
            statusLabel.innerHTML = '<i class="fa-solid fa-check" style="color:var(--success-color);"></i> Updated!';
            document.getElementById('wallet-new-budget').value = '';
            // Refresh to show changes immediately
            loadWalletData();
            setTimeout(() => { statusLabel.innerText = ''; }, 3000);
        } else {
            statusLabel.innerHTML = `<span style="color:var(--danger-color);">Error: ${data.detail || 'Unknown'}</span>`;
        }
    } catch (err) {
        statusLabel.innerHTML = '<span style="color:var(--danger-color);">Connection error.</span>';
    }
}

// ==========================================
// PHASE 8: AUTOMATION STUDIO (MACROS & MAGIC WAND)
// ==========================================
let currentMacroSession = null;

async function generateMagicFlow() {
    const prompt = document.getElementById('magic-flow-prompt').value.trim();
    if (!prompt) return alert("Please enter a goal.");

    document.getElementById('magic-flow-result').style.display = 'none';
    const btn = document.querySelector('#view-automation .btn-primary');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Channeling...';
    btn.disabled = true;

    try {
        const resp = await fetch(`${API_BASE}/flows/magic`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });

        const data = await resp.json();
        btn.innerHTML = originalText;
        btn.disabled = false;

        if (resp.ok && data.flow_data) {
            document.getElementById('magic-flow-result').style.display = 'block';
            document.getElementById('magic-flow-json').textContent = JSON.stringify(data.flow_data, null, 2);
            window._lastMagicFlow = data.flow_data;
        } else {
            alert("Error: " + (data.detail || "Unknown erroer"));
        }
    } catch (err) {
        btn.innerHTML = originalText;
        btn.disabled = false;
        alert("Connection Error.");
    }
}

function downloadMagicFlow() {
    if (!window._lastMagicFlow) return;
    const blob = new Blob([JSON.stringify(window._lastMagicFlow, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = "magic_flow.json";
    a.click();
    URL.revokeObjectURL(url);
}

async function loadMagicFlowToCanvas() {
    if (!window._lastMagicFlow) return alert("Generate a Magic Flow first!");

    try {
        const resp = await fetch(`${API_BASE}/flows/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
            body: JSON.stringify({
                name: "Magic Flow " + new Date().toLocaleTimeString(),
                description: "Auto-generated from Automation Studio"
            })
        });
        const data = await resp.json();

        if (resp.ok) {
            await loadFlows();
            await openFlowEditor(data.flow_id);
            importFlowToDrawflow(window._lastMagicFlow);
            await saveFlowData();
            switchView('flows');
        } else {
            alert("Failed to create new flow container: " + (data.detail || "Unknown error"));
        }
    } catch (err) {
        alert("Connection error creating flow canvas.");
    }
}

async function startMacroRecording() {
    try {
        const resp = await fetch(`${API_BASE}/macros/start`, { method: 'POST' });
        const data = await resp.json();

        if (resp.ok) {
            document.getElementById('btn-start-macro').disabled = true;
            document.getElementById('btn-stop-macro').disabled = false;

            const container = document.getElementById('macro-status-container');
            container.style.display = 'block';
            document.getElementById('macro-status-text').textContent = "Recording in progress... Perform your actions on screen.";

            // Pulsing red dot
            container.querySelector('.status-indicator').innerHTML = '<span class="live-dot" style="background: var(--danger-color);"></span>';
            document.getElementById('macro-analysis-section').style.display = 'none';
        } else {
            alert("Failed to start recording: " + data.detail);
        }
    } catch (err) {
        alert("Connection error fetching Macro API.");
    }
}

async function stopMacroRecording() {
    try {
        const resp = await fetch(`${API_BASE}/macros/stop`, { method: 'POST' });
        const data = await resp.json();

        if (resp.ok) {
            document.getElementById('btn-start-macro').disabled = false;
            document.getElementById('btn-stop-macro').disabled = true;

            document.getElementById('macro-status-text').textContent = "Recording stopped. Ready for analysis.";
            document.querySelector('#macro-status-container .status-indicator').innerHTML = '<i class="fa-solid fa-check" style="color:var(--success-color);"></i>';

            currentMacroSession = data.session_id;
            document.getElementById('macro-analysis-section').style.display = 'block';
        } else {
            alert("Failed to stop recording: " + data.detail);
        }
    } catch (err) {
        alert("Connection error fetching Macro API.");
    }
}

async function analyzeMacroSession() {
    if (!currentMacroSession) return alert("No session recorded yet.");

    const btn = document.querySelector('#macro-analysis-section .btn-primary');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing Vision Data...';
    btn.disabled = true;

    try {
        const resp = await fetch(`${API_BASE}/macros/${currentMacroSession}/analyze`, { method: 'POST' });
        const data = await resp.json();

        btn.innerHTML = originalText;
        btn.disabled = false;

        if (resp.ok && data.flow_data) {
            alert("Analysis Complete! Flow JSON successfully generated.");

            // Re-use the magic flow result container to show the macro JSON
            document.getElementById('magic-flow-result').style.display = 'block';
            document.getElementById('magic-flow-json').textContent = JSON.stringify(data.flow_data, null, 2);
            window._lastMagicFlow = data.flow_data;

        } else {
            alert("Analysis failed: " + (data.detail || "Unknown error"));
        }
    } catch (err) {
        btn.innerHTML = originalText;
        btn.disabled = false;
        alert("Connection error during analysis.");
    }
}
