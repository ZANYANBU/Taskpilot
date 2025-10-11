const navButtons = document.querySelectorAll('.nav-btn');
const views = document.querySelectorAll('[data-view]');
const viewTitle = document.getElementById('view-title');
const viewSubtitle = document.getElementById('view-subtitle');
const themeSelect = document.getElementById('theme-select');
const openDocsBtn = document.getElementById('open-docs');
const refreshStatsBtn = document.getElementById('refresh-stats');
const resultsList = document.getElementById('results-list');
const progressEl = document.getElementById('progress');
const generateForm = document.getElementById('generate-form');
const generateStatus = document.getElementById('generate-status');
const clearBtn = document.getElementById('clear-results');
const settingsForm = document.getElementById('settings-form');
const settingsStatus = document.getElementById('settings-status');
const historyList = document.getElementById('history-list');
const refreshHistoryBtn = document.getElementById('refresh-history');
const exportSummaryBtn = document.getElementById('export-summary');
const exportCsvBtn = document.getElementById('export-csv');
const statTotal = document.getElementById('stat-total');
const statToday = document.getElementById('stat-today');
const statAuto = document.getElementById('stat-auto');
const statMemory = document.getElementById('stat-memory');
const regionSelect = document.getElementById('region-select');
const modelSelect = document.getElementById('model-select');
const conversationsList = document.getElementById('conversations-list');
const conversationView = document.getElementById('conversation-view');

const REGION_CODES = {
  united_states: 'United States',
  united_kingdom: 'United Kingdom',
  japan: 'Japan',
  germany: 'Germany',
  australia: 'Australia'
};

const GROQ_MODELS = [
  'llama-3.1-8b-instant',
  'llama-3.1-70b-versatile',
  'llama-guard-3-8b',
  'gemma2-9b-it'
];

function applyTheme(mode) {
  document.documentElement.dataset.theme = mode;
  if (mode === 'light') {
    document.documentElement.style.setProperty('--bg', '#f4f7fc');
    document.documentElement.style.setProperty('--bg-soft', '#ffffff');
    document.documentElement.style.setProperty('--bg-card', '#ffffff');
    document.documentElement.style.setProperty('--bg-lighter', '#eceff5');
    document.documentElement.style.setProperty('--text', '#0f172a');
    document.documentElement.style.setProperty('--text-muted', '#475569');
  } else if (mode === 'dark') {
    document.documentElement.style.removeProperty('--bg');
    document.documentElement.style.removeProperty('--bg-soft');
    document.documentElement.style.removeProperty('--bg-card');
    document.documentElement.style.removeProperty('--bg-lighter');
    document.documentElement.style.removeProperty('--text');
    document.documentElement.style.removeProperty('--text-muted');
  }
}

themeSelect.addEventListener('change', (event) => {
  const value = event.target.value;
  applyTheme(value);
});

openDocsBtn.addEventListener('click', () => {
  window.open('https://github.com/ZANYANBU/Taskpilot', '_blank');
});

function switchView(target) {
  navButtons.forEach((btn) => btn.classList.toggle('active', btn.dataset.target === target));
  views.forEach((view) => view.classList.toggle('hidden', view.id !== `view-${target}`));

  if (target === 'generate') {
    viewTitle.textContent = 'Generate campaign';
    viewSubtitle.textContent = 'Choose your parameters, then deploy TaskPilot to craft Reddit-ready posts.';
  } else if (target === 'conversations') {
    viewTitle.textContent = 'AI Memory';
    viewSubtitle.textContent = 'View conversation history and how the AI learns from your interactions.';
    loadConversations();
  } else if (target === 'history') {
    viewTitle.textContent = 'Engagement history';
    viewSubtitle.textContent = 'Review every post with upvotes and comment counts synced from Reddit.';
    loadHistory();
  } else if (target === 'settings') {
    viewTitle.textContent = 'Integrations';
    viewSubtitle.textContent = 'Connect Groq and Reddit so TaskPilot can orchestrate automation end-to-end.';
    preloadConfig();
  }
}

navButtons.forEach((btn) => {
  btn.addEventListener('click', () => switchView(btn.dataset.target));
});

function populateSelect(select, options) {
  select.innerHTML = '';
  options.forEach((value) => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = REGION_CODES[value] || value;
    select.appendChild(option);
  });
}

populateSelect(regionSelect, Object.keys(REGION_CODES));

function populateModels(models) {
  modelSelect.innerHTML = '';
  models.forEach((model) => {
    const option = document.createElement('option');
    option.value = model;
    option.textContent = model;
    modelSelect.appendChild(option);
  });
}

populateModels(GROQ_MODELS);

async function fetchJSON(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail = data.detail || response.statusText;
    throw new Error(detail);
  }
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json();
  }
  return response.text();
}

async function loadStats() {
  try {
    const stats = await fetchJSON('/api/stats');
    const memoryStats = await fetchJSON('/api/memory/stats');
    statTotal.textContent = stats.total_posts;
    statToday.textContent = stats.today_posts;
    statAuto.textContent = stats.auto_posts;
    statMemory.textContent = memoryStats.conversations;
  } catch (error) {
    console.error('Failed to load stats', error);
  }
}

refreshStatsBtn.addEventListener('click', loadStats);

async function loadHistory() {
  try {
    const history = await fetchJSON('/api/history');
    historyList.innerHTML = '';
    if (!history.items.length) {
      historyList.innerHTML = '<p class="status">No history yet. Generate a post to get started.</p>';
      return;
    }
    history.items.forEach((item) => {
      const row = document.createElement('article');
      row.className = 'history-row';
      row.innerHTML = `
        <div class="meta">
          <strong>${item.topic}</strong>
          <span>${item.title}</span>
          <small>${item.subreddit || '(no subreddit)'} · ${new Date(item.timestamp).toLocaleString()}</small>
        </div>
        <div class="meta">
          <a href="${item.link}" target="_blank" rel="noopener" class="ghost">Open</a>
          <small>👍 ${item.upvotes} · 💬 ${item.comments}</small>
        </div>
      `;
      historyList.appendChild(row);
    });
  } catch (error) {
    historyList.innerHTML = `<p class="status error">${error.message}</p>`;
  }
}

async function loadConversations() {
  try {
    const response = await fetchJSON('/api/conversations');
    const memoryStats = await fetchJSON('/api/memory/stats');

    conversationsList.innerHTML = '';

    // Add memory insights header
    const insightsDiv = document.createElement('div');
    insightsDiv.className = 'memory-insights';
    insightsDiv.innerHTML = `
      <div class="insight-cards">
        <div class="insight-card">
          <strong>${memoryStats.conversations}</strong>
          <span>Conversations</span>
        </div>
        <div class="insight-card">
          <strong>${memoryStats.messages}</strong>
          <span>Messages</span>
        </div>
        <div class="insight-card">
          <strong>${memoryStats.memory_items}</strong>
          <span>Memory Items</span>
        </div>
      </div>
      <div class="insights-list">
        ${memoryStats.insights.map(insight => `<p>${insight}</p>`).join('')}
      </div>
    `;
    conversationsList.appendChild(insightsDiv);

    if (!response.conversations.length) {
      conversationsList.innerHTML += '<p class="status">No conversations yet. Generate content to start building AI memory.</p>';
      return;
    }

    response.conversations.forEach((conv) => {
      const item = document.createElement('div');
      item.className = 'conversation-item';
      item.onclick = () => loadConversationDetail(conv.id);
      item.innerHTML = `
        <h4>${conv.title}</h4>
        <small>${conv.persona} · ${conv.tone}</small>
        <small>Last updated: ${new Date(conv.updated_at).toLocaleString()}</small>
      `;
      conversationsList.appendChild(item);
    });
  } catch (error) {
    conversationsList.innerHTML = `<p class="status error">${error.message}</p>`;
  }
}

async function loadConversationDetail(conversationId) {
  try {
    const response = await fetchJSON(`/api/conversations/${conversationId}`);
    conversationView.innerHTML = `
      <div class="conversation-header">
        <h3>Conversation Thread</h3>
        <p>ID: ${response.conversation_id}</p>
      </div>
      <div class="messages">
        ${response.messages.map(msg => `
          <div class="message ${msg.role}">
            <div class="message-header">
              <strong>${msg.role === 'user' ? 'You' : 'AI Assistant'}</strong>
              <small>${new Date(msg.timestamp).toLocaleString()}</small>
            </div>
            <div class="message-content">${msg.content.replace(/\n/g, '<br />')}</div>
            ${msg.metadata ? `<small class="metadata">${msg.metadata}</small>` : ''}
          </div>
        `).join('')}
      </div>
    `;
  } catch (error) {
    conversationView.innerHTML = `<p class="status error">${error.message}</p>`;
  }
}

async function preloadConfig() {
  try {
    const config = await fetchJSON('/api/config');
    // For now, default to Groq
    settingsForm.provider.value = 'groq';
    if (!GROQ_MODELS.includes(config.GROQ.model)) {
      GROQ_MODELS.push(config.GROQ.model);
      populateModels(GROQ_MODELS);
    }
    settingsForm.api_key.value = config.GROQ.api_key;
    settingsForm.model.value = config.GROQ.model;
    settingsForm.reddit_client_id.value = config.REDDIT.client_id;
    settingsForm.reddit_client_secret.value = config.REDDIT.client_secret;
    settingsForm.reddit_username.value = config.REDDIT.username;
    settingsForm.reddit_password.value = config.REDDIT.password;
    settingsForm.reddit_refresh_token.value = config.REDDIT.refresh_token;
    settingsForm.reddit_user_agent.value = config.REDDIT.user_agent;
  } catch (error) {
    settingsStatus.textContent = error.message;
  }
}

settingsForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  settingsStatus.textContent = 'Saving…';
  const payload = {
    GROQ: {
      api_key: settingsForm.api_key.value,
      model: settingsForm.model.value
    },
    REDDIT: {
      client_id: settingsForm.reddit_client_id.value,
      client_secret: settingsForm.reddit_client_secret.value,
      username: settingsForm.reddit_username.value,
      password: settingsForm.reddit_password.value,
      refresh_token: settingsForm.reddit_refresh_token.value,
      user_agent: settingsForm.reddit_user_agent.value
    }
  };
  try {
    const response = await fetchJSON('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    settingsStatus.textContent = response.message;
  } catch (error) {
    settingsStatus.textContent = error.message;
  }
});

function renderResult(post) {
  const card = document.createElement('article');
  card.className = 'result-card';
  card.innerHTML = `
    <h4>${post.title}</h4>
    <p class="topic">Topic: <strong>${post.topic}</strong></p>
    <p class="body">${post.body.replace(/\n/g, '<br />')}</p>
    <p class="link">Link: <a href="${post.link}" target="_blank" rel="noopener">${post.link}</a></p>
    <small>${post.auto_posted ? '✅ Posted to Reddit' : '📝 Saved locally'}</small>
  `;
  return card;
}

generateForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  generateStatus.textContent = 'Generating…';
  progressEl.value = 0;
  resultsList.innerHTML = '';

  const payload = {
    keyword: generateForm.keyword.value || null,
    subreddit: generateForm.subreddit.value || null,
    tone: generateForm.tone.value,
    region: generateForm.region.value,
    persona: generateForm.persona.value,
    length: generateForm.length.value,
    auto_post: generateForm.auto_post.checked
  };

  try {
    const response = await fetchJSON('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    response.posts.forEach((post) => {
      resultsList.appendChild(renderResult(post));
    });
    progressEl.value = 1;
    generateStatus.textContent = response.message;
    loadStats();
  } catch (error) {
    generateStatus.textContent = error.message;
    progressEl.value = 0;
  }
});

clearBtn.addEventListener('click', () => {
  resultsList.innerHTML = '';
  progressEl.value = 0;
  generateStatus.textContent = 'Cleared.';
});

refreshHistoryBtn.addEventListener('click', async () => {
  refreshHistoryBtn.disabled = true;
  refreshHistoryBtn.textContent = 'Refreshing…';
  try {
    const response = await fetchJSON('/api/refresh', { method: 'POST' });
    refreshHistoryBtn.textContent = response.message;
    loadHistory();
    loadStats();
  } catch (error) {
    refreshHistoryBtn.textContent = error.message;
  } finally {
    setTimeout(() => {
      refreshHistoryBtn.textContent = 'Refresh engagement';
      refreshHistoryBtn.disabled = false;
    }, 2000);
  }
});

async function downloadFile(url, filename) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error('Download failed');
  }
  const blob = await response.blob();
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

exportSummaryBtn.addEventListener('click', async () => {
  try {
    await downloadFile('/api/summary?format=txt', `taskpilot-summary-${Date.now()}.txt`);
  } catch (error) {
    alert(error.message);
  }
});

exportCsvBtn.addEventListener('click', async () => {
  try {
    await downloadFile('/api/summary?format=csv', `taskpilot-history-${Date.now()}.csv`);
  } catch (error) {
    alert(error.message);
  }
});

// Initial data load
switchView('generate');
loadStats();
loadHistory();
