// DOM Elements
const apiKeyModal = document.getElementById('apiKeyModal');
const apiKeyInput = document.getElementById('apiKeyInput');
const saveApiKeyBtn = document.getElementById('saveApiKeyBtn');
const apiError = document.getElementById('apiError');

const sessionInfo = document.getElementById('sessionInfo');
const sessionIdDisplay = document.getElementById('sessionIdDisplay');
const copySessionBtn = document.getElementById('copySessionBtn');

const searchPanel = document.getElementById('searchPanel');
const searchForm = document.getElementById('searchForm');
const resumeFile = document.getElementById('resumeFile');
const fileNameDisplay = document.getElementById('fileName');
const searchError = document.getElementById('searchError');

const loadingState = document.getElementById('loadingState');
const resultsView = document.getElementById('resultsView');
const jobsList = document.getElementById('jobsList');

const chatHistory = document.getElementById('chatHistory');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const globalLoading = document.getElementById('globalLoading');

const draftSection = document.getElementById('draftSection');
const draftTo = document.getElementById('draftTo');
const draftSubject = document.getElementById('draftSubject');
const draftBody = document.getElementById('draftBody');
const approveDraftBtn = document.getElementById('approveDraftBtn');
const discardDraftBtn = document.getElementById('discardDraftBtn');

const errorBanner = document.getElementById('errorBanner');
const errorText = document.getElementById('errorText');
const closeErrorBtn = document.getElementById('closeErrorBtn');

// State
let API_KEY = localStorage.getItem('JOB_HUNTER_API_KEY');
let SESSION_ID = localStorage.getItem('JOB_HUNTER_SESSION_ID');
let USER_ID = localStorage.getItem('JOB_HUNTER_USER_ID');
let currentDraft = null;

// ==========================================
// Note: Storing the API key in localStorage is acceptable for local/dev use, 
// but is NOT a secure pattern for a real deployed frontend where the key should be held by a server-side proxy.
// ==========================================

// Initialization
async function init() {
    if (!API_KEY) {
        apiKeyModal.classList.remove('hidden');
    } else {
        await verifyAndStart();
    }
}

saveApiKeyBtn.addEventListener('click', async () => {
    const key = apiKeyInput.value.trim();
    if (!key) return;
    
    API_KEY = key;
    localStorage.setItem('JOB_HUNTER_API_KEY', API_KEY);
    await verifyAndStart();
});

async function verifyAndStart() {
    saveApiKeyBtn.textContent = 'Verifying...';
    try {
        const res = await callApi('/health', { method: 'GET' });
        apiKeyModal.classList.add('hidden');
        
        // Initialize session if missing
        if (!SESSION_ID) {
            const sessionRes = await callApi('/session', { method: 'POST', body: JSON.stringify({}) });
            SESSION_ID = sessionRes.session_id;
            USER_ID = sessionRes.user_id;
            localStorage.setItem('JOB_HUNTER_SESSION_ID', SESSION_ID);
            localStorage.setItem('JOB_HUNTER_USER_ID', USER_ID);
        }
        
        sessionInfo.classList.remove('hidden');
        sessionIdDisplay.textContent = SESSION_ID;
        
    } catch (err) {
        apiError.textContent = err.message || 'Invalid API Key or server unreachable.';
        apiKeyModal.classList.remove('hidden');
        localStorage.removeItem('JOB_HUNTER_API_KEY');
        API_KEY = null;
    } finally {
        saveApiKeyBtn.textContent = 'Start Session';
    }
}

// API Wrapper
async function callApi(path, options = {}) {
    if (!API_KEY) throw new Error("API Key missing");
    
    const headers = {
        'X-API-Key': API_KEY,
        ...(options.headers || {})
    };
    
    // Default to JSON content type if body is a string (and not FormData)
    if (options.body && typeof options.body === 'string' && !headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
    }

    try {
        const response = await fetch(path, { ...options, headers });
        const data = await response.json().catch(() => null);
        
        if (!response.ok) {
            const errorMsg = data?.detail || response.statusText;
            showError(`Error ${response.status}: ${errorMsg}`);
            throw new Error(errorMsg);
        }
        return data;
    } catch (err) {
        if (err.name !== 'Error') {
            showError("Network error or server unreachable");
        }
        throw err;
    }
}

function showError(msg) {
    errorText.textContent = msg;
    errorBanner.classList.remove('hidden');
}

closeErrorBtn.addEventListener('click', () => {
    errorBanner.classList.add('hidden');
});

copySessionBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(SESSION_ID);
    copySessionBtn.textContent = '✅';
    setTimeout(() => { copySessionBtn.textContent = '📋'; }, 2000);
});

// File UI
resumeFile.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        fileNameDisplay.textContent = `📄 ${e.target.files[0].name}`;
        fileNameDisplay.classList.remove('hidden');
    }
});

// Search Submit
searchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    searchError.textContent = '';
    
    const file = resumeFile.files[0];
    if (!file) {
        searchError.textContent = "Please upload a resume.";
        return;
    }

    // 1. Upload & Parse File
    searchPanel.classList.add('hidden');
    loadingState.classList.remove('hidden');
    
    let resumeText = '';
    try {
        const formData = new FormData();
        formData.append('file', file);
        const uploadRes = await callApi('/upload', {
            method: 'POST',
            body: formData // Note: no Content-Type header, browser sets it for FormData
        });
        
        if (uploadRes.error) {
            throw new Error(uploadRes.error);
        }
        resumeText = uploadRes.text;
    } catch (err) {
        loadingState.classList.add('hidden');
        searchPanel.classList.remove('hidden');
        searchError.textContent = "Failed to parse resume: " + err.message;
        return;
    }

    // 2. Gather Preferences
    const job_type = document.querySelector('input[name="job_type"]:checked').value;
    const work_mode = document.querySelector('input[name="work_mode"]:checked').value;
    const locationsRaw = document.getElementById('locationsInput').value;
    const locations = locationsRaw.split(',').map(l => l.trim()).filter(l => l);
    const paid_only = document.getElementById('paidOnly').checked;

    const preferences = { job_type, work_mode, locations, paid_only };

    // 3. Initial Chat Request with State Updates
    try {
        const chatRes = await callApi('/chat', {
            method: 'POST',
            body: JSON.stringify({
                session_id: SESSION_ID,
                user: USER_ID,
                message: "Find me a job based on my resume and preferences.",
                state_updates: {
                    resume_raw: resumeText,
                    preferences: preferences
                }
            })
        });
        
        loadingState.classList.add('hidden');
        resultsView.classList.remove('hidden');
        
        renderState(chatRes);
        addChatMessage("assistant", chatRes.response);
        
    } catch (err) {
        loadingState.classList.add('hidden');
        searchPanel.classList.remove('hidden');
    }
});

// Chat UI
function addChatMessage(role, text) {
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerHTML = `<p>${text.replace(/\n/g, '<br>')}</p>`;
    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = chatInput.value.trim();
    if (!msg) return;
    
    chatInput.value = '';
    addChatMessage('user', msg);
    
    await sendChatMessage(msg);
});

async function sendChatMessage(message, extraPayload = {}) {
    globalLoading.classList.remove('hidden');
    try {
        const chatRes = await callApi('/chat', {
            method: 'POST',
            body: JSON.stringify({
                session_id: SESSION_ID,
                user: USER_ID,
                message: message,
                ...extraPayload
            })
        });
        
        renderState(chatRes);
        addChatMessage("assistant", chatRes.response);
    } catch (err) {
        // Error already surfaced by wrapper
    } finally {
        globalLoading.classList.add('hidden');
    }
}

// Render Results & Intel
function renderState(chatRes) {
    if (!chatRes.state_snapshot) return;
    
    const { ranked_jobs, company_intel, email_draft } = chatRes.state_snapshot;
    
    if (ranked_jobs && ranked_jobs.length > 0) {
        jobsList.innerHTML = '';
        ranked_jobs.forEach(rank => {
            const job = rank.job;
            const score = (rank.score * 100).toFixed(0);
            const intel = company_intel ? company_intel[job.company] : null;
            
            let intelHtml = '';
            if (intel && intel.length > 0) {
                intelHtml = `<div class="intel-section"><strong>Company Intel:</strong><br>`;
                intel.forEach(review => {
                    const badgeClass = review.sentiment === 'positive' ? 'intel-positive' : review.sentiment === 'negative' ? 'intel-negative' : 'intel-neutral';
                    intelHtml += `<span class="intel-badge ${badgeClass}">${review.source}: ${review.summary}</span>`;
                });
                intelHtml += `</div>`;
            }
            
            const card = document.createElement('div');
            card.className = 'job-card';
            card.innerHTML = `
                <div class="job-header">
                    <div>
                        <div class="job-title">${job.title}</div>
                        <div class="job-company">${job.company}</div>
                    </div>
                    <div class="job-score">${score}% Match</div>
                </div>
                <div class="job-meta">
                    <span>📍 ${job.location}</span>
                    <span>🏢 ${job.work_mode}</span>
                    <span>💼 ${job.job_type}</span>
                    <span>🏷️ ${job.source}</span>
                </div>
                <div class="job-desc" id="desc-${job.id}">${job.description}</div>
                <button class="expand-btn" onclick="document.getElementById('desc-${job.id}').classList.toggle('expanded')">Read more...</button>
                <div style="margin-top:0.5rem"><a href="${job.url}" target="_blank" style="font-size:0.875rem; color:var(--primary);">View Posting ↗</a></div>
                ${intelHtml}
            `;
            jobsList.appendChild(card);
        });
    }
    
    // Render Draft
    if (email_draft && email_draft.status === "pending_user_approval") {
        currentDraft = email_draft;
        draftTo.textContent = email_draft.to;
        draftSubject.textContent = email_draft.subject;
        draftBody.value = email_draft.body;
        draftSection.classList.remove('hidden');
    } else {
        draftSection.classList.add('hidden');
        currentDraft = null;
    }
}

// Draft Actions
discardDraftBtn.addEventListener('click', async () => {
    draftSection.classList.add('hidden');
    currentDraft = null;
    addChatMessage('user', "I have discarded the draft.");
    await sendChatMessage("I discarded the draft. Please create a new one or ask how I want to modify it.", {
        state_updates: { email_draft: null }
    });
});

approveDraftBtn.addEventListener('click', async () => {
    if (!currentDraft) return;
    
    draftSection.classList.add('hidden');
    addChatMessage('user', "I have approved the draft. Send it!");
    
    // Explicitly send user_confirmed = true and the updated body just in case the user edited it
    const updatedDraft = {
        ...currentDraft,
        body: draftBody.value
    };
    
    await sendChatMessage("Send the email now.", {
        state_updates: { email_draft: updatedDraft },
        user_confirmed: true // This would be intercepted by the backend if we built that, or handled via the message context
    });
});

init();
