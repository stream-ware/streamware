/**
 * Voice Shell Client JavaScript
 * 
 * Handles:
 * - WebSocket communication
 * - Voice recognition (Web Speech API)
 * - Text-to-speech
 * - Session management
 * - Multi-language support
 */

// Configuration (set by server)
const CONFIG = {
    wsUrl: "ws://localhost:8765",
    language: "en",
};

// State
let ws;
let recognition;
let synthesis = window.speechSynthesis;
let isListening = false;
let isSpeaking = false;
let pendingCommand = null;
let currentSessionId = null;
let sessions = {};
let continuousMode = true;
let bargeInMode = true;
let currentUser = null;  // Logged in user

// View mode: 'conversation' shows user dialog, 'process' shows command output
let viewMode = 'conversation';

// Separate storage for conversation vs process output per session
let sessionConversations = {};  // sessionId -> [conversation lines]
let sessionProcessOutput = {};  // sessionId -> [process output lines]

// =============================================================================
// Authentication Functions
// =============================================================================

function showLoginModal() {
    document.getElementById('login-modal').style.display = 'flex';
    document.getElementById('login-email').focus();
    document.getElementById('login-status').textContent = '';
}

function hideLoginModal() {
    document.getElementById('login-modal').style.display = 'none';
}

async function requestMagicLink() {
    const email = document.getElementById('login-email').value.trim();
    const statusEl = document.getElementById('login-status');
    
    if (!email || !email.includes('@')) {
        statusEl.textContent = '❌ Please enter a valid email';
        statusEl.className = 'login-status error';
        return;
    }
    
    statusEl.textContent = '⏳ Sending...';
    statusEl.className = 'login-status';
    
    try {
        const resp = await fetch('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        
        const data = await resp.json();
        
        if (data.success) {
            statusEl.textContent = '✅ Magic link sent! Check your email or terminal.';
            statusEl.className = 'login-status success';
            // Keep modal open so user can see the message
        } else {
            statusEl.textContent = `❌ ${data.error || 'Failed to send email'}`;
            statusEl.className = 'login-status error';
        }
    } catch (e) {
        statusEl.textContent = `❌ Error: ${e.message}`;
        statusEl.className = 'login-status error';
    }
}

async function checkAuthStatus() {
    try {
        const resp = await fetch('/auth/me');
        const data = await resp.json();
        
        if (data.authenticated && data.user) {
            currentUser = data.user;
            updateAuthUI(true);
            console.log(`👤 Logged in as: ${data.user.email}`);
        } else {
            currentUser = null;
            updateAuthUI(false);
        }
    } catch (e) {
        currentUser = null;
        updateAuthUI(false);
    }
}

function updateAuthUI(isLoggedIn) {
    const loginBtn = document.getElementById('btn-login');
    const logoutBtn = document.getElementById('btn-logout');
    const userEmail = document.getElementById('user-email');
    
    if (isLoggedIn && currentUser) {
        loginBtn.style.display = 'none';
        logoutBtn.style.display = 'inline-block';
        userEmail.style.display = 'inline-block';
        userEmail.textContent = `👤 ${currentUser.email}`;
    } else {
        loginBtn.style.display = 'inline-block';
        logoutBtn.style.display = 'none';
        userEmail.style.display = 'none';
    }
}

function logout() {
    window.location.href = '/auth/logout';
}

// =============================================================================
// Centralized Multi-language Translations
// =============================================================================
const TRANSLATIONS = {
    en: {
        name: 'English',
        voiceCode: 'en-US',
        // UI Labels
        ui: {
            title: 'Streamware Voice Shell',
            sessions: 'Sessions',
            shellOutput: 'Shell Output',
            voiceControl: 'Voice Control',
            newConversation: 'New Conversation',
            stop: 'Stop',
            continuous: 'Continuous',
            bargeIn: 'Barge-in',
            copy: 'Copy',
            clear: 'Clear',
            send: 'Send',
            yes: 'Yes',
            no: 'No',
            new: 'New',
            trackPerson: 'Track Person',
            trackEmail: 'Track + Email',
            status: 'Status',
            typeCommand: 'Type a command...',
            clickToTalk: 'Click or press Space to talk',
            url: 'URL',
            email: 'Email',
            notSet: '(not set)',
            on: 'ON',
            off: 'OFF',
        },
        // Status Messages
        status: {
            connected: 'Connected to Streamware Voice Shell',
            disconnected: 'Disconnected. Reconnecting...',
            newConversation: 'New conversation started. Say hello or a command.',
            noOutput: '(No output yet)',
            switchedTo: 'Switched to',
            creatingSession: 'Creating new session (current is busy)',
            previousRunning: 'previous session still running',
            listening: 'Listening...',
            listeningWhileSpeaking: 'Listening (while speaking)...',
            speaking: 'Speaking...',
            voiceReady: 'Ready',
            executingCommand: 'EXECUTING COMMAND',
            commandCompleted: 'Command completed',
            commandStarted: 'Command started',
            cancelled: 'Cancelled',
            error: 'Error',
            sessionNotFound: 'Session not found',
            bargeIn: 'Barge-in: TTS interrupted',
            sent: 'Sent',
            newSession: 'New session',
        },
        // Conversation flow
        conversation: {
            hello: 'Hello! What would you like to monitor?',
            howWouldYouLike: 'How would you like to {action}?',
            withVoice: 'with voice (TTS)',
            silently: 'silently',
            andEmailMe: 'and email me',
            emailSaved: "I have your email saved as {email}. Say 'yes' to use it, or 'new' to enter different.",
            usingEmail: 'Using email {email}. Executing...',
            enterNewEmail: 'Please say your new email address.',
            sayYesConfirm: 'Say yes to confirm.',
            executing: 'Executing command.',
            notUnderstood: "Sorry, I didn't understand. Say 'hello' for options.",
        },
    },
    pl: {
        name: 'Polski',
        voiceCode: 'pl-PL',
        ui: {
            title: 'Streamware Voice Shell',
            sessions: 'Sesje',
            shellOutput: 'Wyjście Shell',
            voiceControl: 'Sterowanie Głosowe',
            newConversation: 'Nowa Rozmowa',
            stop: 'Stop',
            continuous: 'Ciągły',
            bargeIn: 'Przerywanie',
            copy: 'Kopiuj',
            clear: 'Wyczyść',
            send: 'Wyślij',
            yes: 'Tak',
            no: 'Nie',
            new: 'Nowy',
            trackPerson: 'Śledź Osobę',
            trackEmail: 'Śledź + Email',
            status: 'Status',
            typeCommand: 'Wpisz polecenie...',
            clickToTalk: 'Kliknij lub naciśnij Spację aby mówić',
            url: 'URL',
            email: 'Email',
            notSet: '(nie ustawiono)',
            on: 'WŁ',
            off: 'WYŁ',
        },
        status: {
            connected: 'Połączono ze Streamware Voice Shell',
            disconnected: 'Rozłączono. Ponowne łączenie...',
            newConversation: 'Nowa rozmowa. Powiedz cześć lub wydaj polecenie.',
            noOutput: '(Brak wyjścia)',
            switchedTo: 'Przełączono na',
            creatingSession: 'Tworzenie nowej sesji (obecna zajęta)',
            previousRunning: 'poprzednia sesja nadal działa',
            listening: 'Słucham...',
            listeningWhileSpeaking: 'Słucham (podczas mówienia)...',
            speaking: 'Mówię...',
            voiceReady: 'Gotowy',
            executingCommand: 'WYKONUJĘ POLECENIE',
            commandCompleted: 'Polecenie zakończone',
            commandStarted: 'Polecenie rozpoczęte',
            cancelled: 'Anulowano',
            error: 'Błąd',
            sessionNotFound: 'Sesja nie znaleziona',
            bargeIn: 'Przerwanie: TTS przerwany',
            sent: 'Wysłano',
            newSession: 'Nowa sesja',
        },
        conversation: {
            hello: 'Cześć! Co chciałbyś monitorować?',
            howWouldYouLike: 'Jak chcesz {action}?',
            withVoice: 'z głosem (TTS)',
            silently: 'cicho',
            andEmailMe: 'i wyślij mi email',
            emailSaved: "Mam zapisany email {email}. Powiedz 'tak' aby użyć, lub 'nowy' aby podać inny.",
            usingEmail: 'Używam email {email}. Wykonuję...',
            enterNewEmail: 'Podaj nowy adres email.',
            sayYesConfirm: 'Powiedz tak aby potwierdzić.',
            executing: 'Wykonuję polecenie.',
            notUnderstood: "Nie zrozumiałem. Powiedz 'cześć' aby zobaczyć opcje.",
        },
    },
    de: {
        name: 'Deutsch',
        voiceCode: 'de-DE',
        ui: {
            title: 'Streamware Voice Shell',
            sessions: 'Sitzungen',
            shellOutput: 'Shell Ausgabe',
            voiceControl: 'Sprachsteuerung',
            newConversation: 'Neue Unterhaltung',
            stop: 'Stopp',
            continuous: 'Kontinuierlich',
            bargeIn: 'Unterbrechen',
            copy: 'Kopieren',
            clear: 'Löschen',
            send: 'Senden',
            yes: 'Ja',
            no: 'Nein',
            new: 'Neu',
            trackPerson: 'Person verfolgen',
            trackEmail: 'Verfolgen + Email',
            status: 'Status',
            typeCommand: 'Befehl eingeben...',
            clickToTalk: 'Klicken oder Leertaste drücken zum Sprechen',
            url: 'URL',
            email: 'E-Mail',
            notSet: '(nicht gesetzt)',
            on: 'AN',
            off: 'AUS',
        },
        status: {
            connected: 'Mit Streamware Voice Shell verbunden',
            disconnected: 'Getrennt. Verbinde erneut...',
            newConversation: 'Neue Unterhaltung. Sag hallo oder einen Befehl.',
            noOutput: '(Keine Ausgabe)',
            switchedTo: 'Gewechselt zu',
            creatingSession: 'Erstelle neue Sitzung (aktuelle beschäftigt)',
            previousRunning: 'vorherige Sitzung läuft noch',
            listening: 'Höre zu...',
            listeningWhileSpeaking: 'Höre zu (während Sprechen)...',
            speaking: 'Spreche...',
            voiceReady: 'Bereit',
            executingCommand: 'FÜHRE BEFEHL AUS',
            commandCompleted: 'Befehl abgeschlossen',
            commandStarted: 'Befehl gestartet',
            cancelled: 'Abgebrochen',
            error: 'Fehler',
            sessionNotFound: 'Sitzung nicht gefunden',
            bargeIn: 'Unterbrechen: TTS unterbrochen',
            sent: 'Gesendet',
            newSession: 'Neue Sitzung',
        },
        conversation: {
            hello: 'Hallo! Was möchtest du überwachen?',
            howWouldYouLike: 'Wie möchtest du {action}?',
            withVoice: 'mit Stimme (TTS)',
            silently: 'leise',
            andEmailMe: 'und mir eine E-Mail senden',
            emailSaved: "E-Mail gespeichert: {email}. Sag 'ja' zum Verwenden, oder 'neu' für andere.",
            usingEmail: 'Verwende E-Mail {email}. Führe aus...',
            enterNewEmail: 'Bitte sage deine neue E-Mail-Adresse.',
            sayYesConfirm: 'Sag ja zum Bestätigen.',
            executing: 'Führe Befehl aus.',
            notUnderstood: "Entschuldigung, nicht verstanden. Sag 'hallo' für Optionen.",
        },
    },
};

// Helper functions for translations
function t(category, key, replacements = {}) {
    const lang = TRANSLATIONS[CONFIG.language] || TRANSLATIONS.en;
    let text = lang[category]?.[key] || TRANSLATIONS.en[category]?.[key] || key;
    
    // Replace placeholders like {email} with values
    for (const [k, v] of Object.entries(replacements)) {
        text = text.replace(`{${k}}`, v);
    }
    return text;
}

function ui(key) { return t('ui', key); }
function status(key) { return t('status', key); }
function conv(key, replacements) { return t('conversation', key, replacements); }

// Legacy function for backward compatibility
function msg(key) {
    // Map old keys to new structure
    const keyMap = {
        'connected': ['status', 'connected'],
        'newConversation': ['status', 'newConversation'],
        'noOutput': ['status', 'noOutput'],
        'listening': ['status', 'listening'],
        'listeningWhileSpeaking': ['status', 'listeningWhileSpeaking'],
        'speaking': ['status', 'speaking'],
        'voiceReady': ['status', 'voiceReady'],
        'bargeIn': ['status', 'bargeIn'],
    };
    const mapped = keyMap[key];
    if (mapped) {
        return t(mapped[0], mapped[1]);
    }
    return key;
}

// Get current voice recognition language code
function getVoiceCode() {
    return TRANSLATIONS[CONFIG.language]?.voiceCode || 'en-US';
}

// Update all UI text when language changes
function updateUILanguage() {
    // Update headers and labels
    const updates = {
        // These would need data-i18n attributes in HTML
        // For now, update via ID
    };
    
    // Update voice recognition language
    if (recognition) {
        recognition.lang = getVoiceCode();
        console.log('Voice recognition language set to:', getVoiceCode());
    }
    
    // Broadcast language change to server
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'set_language', content: CONFIG.language }));
    }
    
    showToast(`Language: ${TRANSLATIONS[CONFIG.language]?.name || CONFIG.language}`, 'info');
}

// ============================================================================
// Session Management
// ============================================================================

function newSession() {
    ws.send(JSON.stringify({ type: 'new_session' }));
    document.getElementById('output').innerHTML = '';
    hideProgressBar();  // New session has no running command
    hideAllOptionButtons();  // Clear any pending options
    addOutput(msg('newConversation'), 'system');
}

function switchSession(sessionId, mode = 'conversation') {
    console.log('Switching to session:', sessionId, 'mode:', mode);
    viewMode = mode;
    isProcessOutput = false;  // Reset process output tracking
    ws.send(JSON.stringify({ type: 'switch_session', content: sessionId }));
}

function closeSession(sessionId) {
    ws.send(JSON.stringify({ type: 'close_session', content: sessionId }));
}

function updateSessionsList(sessionsList) {
    const convContainer = document.getElementById('conversations-list');
    const procContainer = document.getElementById('processes-list');
    
    console.log(`📋 updateSessionsList: ${sessionsList.length} sessions received`);
    
    // Store sessions
    sessions = {};
    sessionsList.forEach(s => { sessions[s.id] = s; });
    
    // Show ALL sessions in conversations panel (sorted by name/id)
    const conversations = sessionsList.slice().sort((a, b) => {
        // Sort by id number descending (newest first)
        const numA = parseInt(a.id.replace(/\D/g, '')) || 0;
        const numB = parseInt(b.id.replace(/\D/g, '')) || 0;
        return numB - numA;
    });
    
    // Processes panel shows only running/recent completed
    const processes = sessionsList.filter(s => s.status === 'running' || s.status === 'completed' || s.status === 'error');
    
    // Update conversations panel
    if (convContainer) {
        convContainer.innerHTML = '';
        conversations.forEach(s => {
            const div = document.createElement('div');
            // Add status class for styling
            let statusClass = s.status === 'running' ? ' running' : (s.status === 'completed' ? ' completed' : '');
            div.className = 'conv-item' + (s.id === currentSessionId ? ' active' : '') + statusClass;
            div.setAttribute('data-session-id', s.id);
            
            // Status indicator
            const statusIcon = s.status === 'running' ? '🔄' : (s.status === 'completed' ? '✓' : '');
            
            div.innerHTML = `
                <div class="session-info" onclick="switchSession('${s.id}', 'conversation')">
                    <div class="session-name">${statusIcon} ${s.name || 'Conversation'}</div>
                    <div class="session-status">${s.output_lines} lines</div>
                </div>
                <button class="btn-delete-conv" onclick="event.stopPropagation(); deleteConversation('${s.id}')" title="Delete">×</button>
            `;
            convContainer.appendChild(div);
        });
        
        if (conversations.length === 0) {
            convContainer.innerHTML = '<div class="empty-state">No conversations</div>';
        }
        
        // Update conversation count badge
        const convBadge = document.getElementById('conv-count');
        if (convBadge) {
            convBadge.textContent = conversations.length;
        }
    }
    
    // Update processes panel
    if (procContainer) {
        procContainer.innerHTML = '';
        let runningCount = 0;
        
        processes.forEach(s => {
            if (s.status === 'running') runningCount++;
            
            const div = document.createElement('div');
            div.className = 'process-item ' + s.status;
            div.setAttribute('data-session-id', s.id);
            
            const statusIcon = s.status === 'running' ? '🔄' : s.status === 'completed' ? '✅' : '❌';
            const cmdShort = (s.command || s.name || '').substring(0, 40);
            
            div.innerHTML = `
                <div class="process-name">${statusIcon} ${s.name || 'Process'}</div>
                <div class="process-cmd" title="${s.command || ''}">${cmdShort}${cmdShort.length >= 40 ? '...' : ''}</div>
                <div class="process-status">
                    <span class="process-time">${s.output_lines} lines</span>
                    <span class="process-actions">
                        ${s.status === 'running' ? '<button onclick="event.stopPropagation(); stopProcess(\'' + s.id + '\')" title="Stop">⏹</button>' : ''}
                        <button onclick="event.stopPropagation(); viewProcess('${s.id}')" title="View">👁</button>
                        <button class="btn-delete-process" onclick="event.stopPropagation(); deleteProcess('${s.id}')" title="Delete">🗑️</button>
                    </span>
                </div>
            `;
            div.addEventListener('click', () => switchSession(s.id, 'process'));
            procContainer.appendChild(div);
        });
        
        if (processes.length === 0) {
            procContainer.innerHTML = '<div class="empty-state">No running processes</div>';
        }
        
        // Update process count badge
        const badge = document.getElementById('process-count');
        if (badge) {
            badge.textContent = runningCount;
            badge.className = 'badge' + (runningCount > 0 ? ' running' : '');
        }
    }
}

function stopProcess(sessionId) {
    ws.send(JSON.stringify({ type: 'stop_session', content: sessionId }));
    showToast('Stopping process...', 'info');
}

function viewProcess(sessionId) {
    switchSession(sessionId, 'process');
}

function deleteProcess(sessionId) {
    if (confirm(`Delete session ${sessionId}?`)) {
        ws.send(JSON.stringify({ type: 'close_session', content: sessionId }));
        showToast('Session deleted', 'info');
    }
}

function deleteConversation(sessionId) {
    // Don't allow deleting current session
    if (sessionId === currentSessionId) {
        showToast('Cannot delete current session', 'error');
        return;
    }
    
    ws.send(JSON.stringify({ type: 'close_session', content: sessionId }));
    showToast('Conversation deleted', 'info');
}

function clearAllConversations() {
    const deletableSessions = Object.values(sessions).filter(s => 
        s.id !== currentSessionId
    );
    
    if (deletableSessions.length === 0) {
        showToast('No conversations to clear', 'info');
        return;
    }
    
    if (confirm(`Delete ${deletableSessions.length} conversations (except current)?`)) {
        deletableSessions.forEach(s => {
            ws.send(JSON.stringify({ type: 'close_session', content: s.id }));
        });
        showToast(`Cleared ${deletableSessions.length} conversations`, 'success');
    }
}

function filterConversations(query) {
    const items = document.querySelectorAll('#conversations-list .conv-item');
    const lowerQuery = query.toLowerCase();
    
    let visibleCount = 0;
    items.forEach(item => {
        const name = item.querySelector('.session-name')?.textContent.toLowerCase() || '';
        
        if (!query || name.includes(lowerQuery)) {
            item.style.display = '';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });
    
    // Update count badge
    const badge = document.getElementById('conv-count');
    if (badge) {
        badge.textContent = visibleCount;
    }
}

function clearAllProcesses() {
    const completedSessions = Object.values(sessions).filter(s => 
        s.status === 'completed' || s.status === 'error'
    );
    
    if (completedSessions.length === 0) {
        showToast('No completed sessions to clear', 'info');
        return;
    }
    
    if (confirm(`Delete ${completedSessions.length} completed/error sessions?`)) {
        completedSessions.forEach(s => {
            ws.send(JSON.stringify({ type: 'close_session', content: s.id }));
        });
        showToast(`Cleared ${completedSessions.length} sessions`, 'success');
    }
}

function filterProcesses(query) {
    const statusFilter = document.getElementById('process-status-filter')?.value || 'all';
    const items = document.querySelectorAll('#processes-list .process-item');
    const lowerQuery = query.toLowerCase();
    
    let visibleCount = 0;
    items.forEach(item => {
        const name = item.querySelector('.process-name')?.textContent.toLowerCase() || '';
        const cmd = item.querySelector('.process-cmd')?.textContent.toLowerCase() || '';
        const status = item.classList.contains('running') ? 'running' : 
                       item.classList.contains('completed') ? 'completed' : 
                       item.classList.contains('error') ? 'error' : '';
        
        // Check text filter
        const matchesText = !query || name.includes(lowerQuery) || cmd.includes(lowerQuery);
        
        // Check status filter
        const matchesStatus = statusFilter === 'all' || status === statusFilter;
        
        if (matchesText && matchesStatus) {
            item.style.display = '';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });
    
    // Show empty state if no visible items
    const procList = document.getElementById('processes-list');
    const emptyState = procList.querySelector('.empty-state');
    if (visibleCount === 0 && !emptyState) {
        const msg = document.createElement('div');
        msg.className = 'empty-state filter-empty';
        msg.textContent = 'No matching processes';
        procList.appendChild(msg);
    } else if (visibleCount > 0 && emptyState?.classList.contains('filter-empty')) {
        emptyState.remove();
    }
}

// ============================================================================
// WebSocket
// ============================================================================

function connectWS() {
    ws = new WebSocket(CONFIG.wsUrl);
    
    ws.onopen = () => {
        document.getElementById('ws-status').classList.add('connected');
        document.getElementById('ws-status-text').textContent = 'Connected';
        addOutput(msg('connected'), 'system');
        // Request sessions - server will create first session if none exist
        ws.send(JSON.stringify({ type: 'get_sessions' }));
        // Don't send new_session here - let server handle it in get_sessions
    };
    
    ws.onclose = () => {
        document.getElementById('ws-status').classList.remove('connected');
        document.getElementById('ws-status-text').textContent = 'Disconnected';
        setTimeout(connectWS, 3000);
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleEvent(data);
    };
}

function handleEvent(event) {
    switch(event.type) {
        case 'voice_input':
        case 'text_input':
            addOutput('> ' + event.data.text, 'input');
            break;
            
        case 'command_parsed':
            if (event.data.understood) {
                if (event.data.options && event.data.options.length > 0) {
                    addOutput('❓ ' + event.data.explanation, 'system');
                    event.data.options.forEach(([key, desc]) => {
                        addOutput('   ' + key + '. ' + desc, 'system');
                    });
                } else {
                    addOutput('✅ ' + event.data.explanation, 'system');
                    if (event.data.command) {
                        addOutput('   Command: ' + event.data.command, 'command');
                        pendingCommand = event.data.command;
                        showConfirmButtons(true);
                    }
                }
            } else {
                addOutput('❌ ' + event.data.explanation, 'error');
            }
            break;
            
        case 'command_executed':
            addOutput('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'system');
            addOutput('🚀 EXECUTING COMMAND:', 'system');
            addOutput('$ ' + event.data.command, 'command');
            addOutput('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'system');
            showConfirmButtons(false);
            hideAllOptionButtons();
            showProgressBar();
            showToast('Command started', 'info');
            break;
            
        case 'command_output':
            addOutput(event.data.line, 'system');
            break;
        
        case 'session_output':
            if (event.data.session_id === currentSessionId) {
                addOutput(event.data.line, 'system');
            }
            break;
            
        case 'command_error':
            addOutput('❌ Error: ' + event.data.error, 'error');
            break;
            
        case 'session_created':
            updateSessionsList(event.data.sessions);
            if (event.data.session) {
                // Check if this was created by ensureIdleSession (we requested it)
                // In that case, switch to it
                const wasRequested = document.getElementById('output').innerHTML.includes('🆕');
                if (wasRequested) {
                    currentSessionId = event.data.session.id;
                    document.getElementById('current-session-name').textContent = 
                        '(' + event.data.session.name + ')';
                    console.log('Switched to new session:', event.data.session.name);
                } else {
                    console.log('New session created:', event.data.session.name);
                    showToast(`New session: ${event.data.session.name}`, 'info');
                }
            }
            break;
            
        case 'session_closed':
            updateSessionsList(event.data.sessions);
            break;
            
        case 'session_switched':
            console.log('Session switched event:', event.data, 'viewMode:', viewMode);
            currentSessionId = event.data.session.id;
            isProcessOutput = false;  // Reset tracking
            
            // Initialize storage for this session
            if (!sessionConversations[currentSessionId]) {
                sessionConversations[currentSessionId] = [];
            }
            if (!sessionProcessOutput[currentSessionId]) {
                sessionProcessOutput[currentSessionId] = [];
            }
            
            // Parse existing output into conversation vs process
            // Clear existing data for this session to avoid duplicates
            sessionConversations[currentSessionId] = [];
            sessionProcessOutput[currentSessionId] = [];
            
            if (event.data.output && event.data.output.length > 0) {
                let inProcess = false;
                event.data.output.forEach(line => {
                    if (!line) return;
                    
                    // Detect start of process output
                    if (line.includes('🚀 EXECUTING COMMAND:') || line.includes('EXECUTING COMMAND') ||
                        line.includes('━━━━━━━━━━━━━━━━━━━━')) {
                        inProcess = true;
                    }
                    
                    // Detect end of process output - user input starts new conversation
                    if (line.startsWith('> ')) {
                        inProcess = false;
                    }
                    
                    // Determine if this is a conversation line
                    const isConvLine = line.startsWith('> ') || 
                                       line.startsWith('✅ ') ||
                                       line.startsWith('❓ ') ||
                                       line.startsWith('❌ ') ||
                                       line.startsWith('🔊 ') ||
                                       line.includes('Say \'yes\'') || 
                                       line.includes('Powiedz tak') ||
                                       (line.includes('Command:') && !inProcess);
                    
                    const lineData = { text: line, type: 'system' };
                    if (inProcess && !isConvLine) {
                        sessionProcessOutput[currentSessionId].push(lineData);
                    } else {
                        sessionConversations[currentSessionId].push(lineData);
                    }
                });
            }
            
            // Update header based on view mode
            const modeLabel = viewMode === 'conversation' ? 'Conversation' : 'Process';
            document.getElementById('current-session-name').textContent = 
                `(${event.data.session.name} - ${modeLabel})`;
            
            // Hide progress bar when switching to non-running session
            if (event.data.session.status !== 'running') {
                hideProgressBar();
            } else {
                showProgressBar();
            }
            
            // Refresh display based on view mode
            refreshOutputDisplay();
            
            updateSessionsList(event.data.sessions || Object.values(sessions));
            showToast(`${modeLabel}: ${event.data.session.name}`, 'success');
            break;
            
        case 'sessions_list':
            updateSessionsList(event.data.sessions);
            if (event.data.current) {
                currentSessionId = event.data.current;
            }
            break;
            
        case 'command_completed':
            addOutput('✓ Command completed', 'system');
            hideProgressBar();
            showToast('Command completed', 'success');
            break;
            
        case 'command_cancel':
            addOutput('✗ Cancelled', 'system');
            showConfirmButtons(false);
            break;
            
        case 'tts_speak':
            speak(event.data.text);
            addOutput('🔊 ' + event.data.text, 'tts');
            // Parse message and show option buttons if applicable
            parseAndShowButtons(event.data.text);
            break;
            
        case 'context_updated':
            updateContext(event.data);
            break;
            
        case 'language_changed':
            // Update language without sending back to server (avoid recursion)
            applyLanguage(event.data.language);
            break;
            
        case 'config_loaded':
            // CQRS query response - apply config from server/SQLite
            console.log('Config loaded from server:', event.data);
            if (event.data.language) {
                applyLanguage(event.data.language);
            }
            updateVariablesFromConfig(event.data);
            break;
            
        case 'variable_changed':
            // Variable updated by server or another client
            console.log('Variable changed:', event.data);
            const { key, value, removed } = event.data;
            if (removed) {
                // Remove row if it's a custom variable
                const row = document.querySelector(`.var-row[data-key="${key}"]`);
                if (row && !['url', 'email', 'language', 'duration', 'focus'].includes(key)) {
                    row.remove();
                }
            } else {
                // Update input value
                const input = document.getElementById(`var-${key}`);
                if (input && document.activeElement !== input) {
                    input.value = value || '';
                    // Highlight change
                    const row = input.closest('.var-row');
                    if (row) {
                        row.classList.add('changed');
                        setTimeout(() => row.classList.remove('changed'), 500);
                    }
                }
            }
            setVarStatus('synced', 'Synced with server');
            break;
    }
}

// ============================================================================
// Output & UI
// ============================================================================

// Track if we're in process output mode (after EXECUTING COMMAND)
let isProcessOutput = false;

function addOutput(text, type = 'system') {
    if (!currentSessionId) return;
    
    // Initialize storage for session if needed
    if (!sessionConversations[currentSessionId]) {
        sessionConversations[currentSessionId] = [];
    }
    if (!sessionProcessOutput[currentSessionId]) {
        sessionProcessOutput[currentSessionId] = [];
    }
    
    // Detect start of process output (EXECUTING COMMAND or separator before it)
    if (text.includes('🚀 EXECUTING COMMAND:') || text.includes('EXECUTING COMMAND') ||
        text.includes('━━━━━━━━━━━━━━━━━━━━')) {
        isProcessOutput = true;
    }
    
    // Detect end of process output - when user input starts ("> " prefix) or new conversation
    // Process output ends when we see user input (type 'input') or explicit conversation markers
    if (type === 'input' || text.startsWith('> ')) {
        isProcessOutput = false;
    }
    
    // Store in appropriate array
    const lineData = { text, type };
    
    // Conversation types: input, tts (before execution), command_parsed, options
    // Process types: everything after EXECUTING COMMAND until next user input
    const isConversationType = type === 'input' || type === 'tts' || 
                               text.startsWith('> ') || 
                               text.startsWith('✅ ') ||  // Parsed command
                               text.startsWith('❓ ') ||  // Options question
                               text.startsWith('❌ ') ||  // Error in parsing
                               text.includes('Say \'yes\'') || text.includes('Powiedz tak') ||
                               text.includes('Command:') && !isProcessOutput;  // Command preview (not execution)
    
    if (isProcessOutput && !isConversationType) {
        // Process output (after EXECUTING COMMAND until next user input)
        sessionProcessOutput[currentSessionId].push(lineData);
    } else {
        // Conversation (user input, parsed commands, TTS responses, options)
        sessionConversations[currentSessionId].push(lineData);
    }
    
    // Always display (unified view by default)
    const output = document.getElementById('output');
    const line = document.createElement('div');
    line.className = 'output-line ' + type;
    line.textContent = text;
    output.appendChild(line);
    output.scrollTop = output.scrollHeight;
}

// Switch view mode and refresh display
function setViewMode(mode) {
    viewMode = mode;
    
    // Update button states
    const btnConv = document.getElementById('btn-view-conv');
    const btnProc = document.getElementById('btn-view-proc');
    if (btnConv) btnConv.classList.toggle('active', mode === 'conversation');
    if (btnProc) btnProc.classList.toggle('active', mode === 'process');
    
    refreshOutputDisplay();
}

// Refresh output display based on current view mode and session
function refreshOutputDisplay() {
    const output = document.getElementById('output');
    output.innerHTML = '';
    
    if (!currentSessionId) return;
    
    const convLines = sessionConversations[currentSessionId] || [];
    const procLines = sessionProcessOutput[currentSessionId] || [];
    
    if (viewMode === 'conversation') {
        // Show only conversation
        convLines.forEach(({ text, type }) => {
            const line = document.createElement('div');
            line.className = 'output-line ' + type;
            line.textContent = text;
            output.appendChild(line);
        });
        
        // Update header
        document.getElementById('current-session-name').textContent = '(Conversation)';
    } else {
        // Show only process output
        procLines.forEach(({ text, type }) => {
            const line = document.createElement('div');
            line.className = 'output-line ' + type;
            line.textContent = text;
            output.appendChild(line);
        });
        
        // Update header
        document.getElementById('current-session-name').textContent = '(Process Output)';
    }
    
    if (output.children.length === 0) {
        const emptyLine = document.createElement('div');
        emptyLine.className = 'output-line system';
        emptyLine.textContent = viewMode === 'conversation' ? 
            'No conversation yet. Say something!' : 
            'No process output yet. Execute a command!';
        output.appendChild(emptyLine);
    }
    
    output.scrollTop = output.scrollHeight;
}

function showConfirmButtons(show) {
    const btns = document.getElementById('confirm-buttons');
    if (btns) btns.style.display = show ? 'flex' : 'none';
}

function updateContext(data) {
    document.getElementById('ctx-url').textContent = data.url || '(not set)';
    document.getElementById('ctx-email').textContent = data.email || '(not set)';
}

function copyLogs() {
    const output = document.getElementById('output');
    const lines = Array.from(output.querySelectorAll('.output-line'))
        .map(el => el.textContent)
        .join('\n');
    
    // Try modern clipboard API first, fallback to execCommand
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(lines).then(() => {
            showCopyFeedback();
        }).catch(() => {
            fallbackCopy(lines);
        });
    } else {
        fallbackCopy(lines);
    }
}

function fallbackCopy(text) {
    // Fallback for non-HTTPS contexts
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    try {
        document.execCommand('copy');
        showCopyFeedback();
    } catch (err) {
        alert('Copy failed. Text:\n\n' + text.substring(0, 500) + '...');
    }
    document.body.removeChild(textarea);
}

function showCopyFeedback() {
    const btn = document.querySelector('[onclick="copyLogs()"]');
    if (btn) {
        const orig = btn.textContent;
        btn.textContent = '✅ Copied!';
        setTimeout(() => { btn.textContent = orig; }, 1500);
    }
}

function clearLogs() {
    document.getElementById('output').innerHTML = '';
    addOutput(msg('connected'), 'system');
}

// ============================================================================
// Quick Commands & Toast Notifications
// ============================================================================

function quickCommand(command) {
    // Send quick command directly
    document.getElementById('text-input').value = command;
    sendText();
    showToast(`Sent: ${command}`, 'info');
}

function showToast(message, type = 'info') {
    // Remove existing toast
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => toast.remove(), 3000);
}

function showCommandPreview(command) {
    const preview = document.getElementById('command-preview');
    const code = document.getElementById('preview-command');
    if (preview && code) {
        code.textContent = command;
        preview.style.display = 'block';
    }
}

function hideCommandPreview() {
    const preview = document.getElementById('command-preview');
    if (preview) preview.style.display = 'none';
}

function showProgressBar() {
    // Add progress bar to output panel
    const output = document.getElementById('output');
    if (!document.getElementById('progress-bar')) {
        const bar = document.createElement('div');
        bar.id = 'progress-bar';
        bar.className = 'progress-bar';
        output.parentElement.insertBefore(bar, output);
    }
}

function hideProgressBar() {
    const bar = document.getElementById('progress-bar');
    if (bar) bar.remove();
}

// ============================================================================
// Dynamic Option Buttons
// ============================================================================

function showNumberedOptions(options) {
    // options = [{key: "1", text: "Track person with voice"}, ...]
    const container = document.getElementById('option-buttons');
    if (!container) return;
    
    container.innerHTML = '<div class="options-label">🎯 Choose an option:</div>';
    
    options.forEach(opt => {
        const btn = document.createElement('button');
        btn.className = 'btn-option numbered';
        btn.innerHTML = `<span class="number">${opt.key}</span>${opt.text}`;
        btn.onclick = () => sendQuickResponse(opt.key);
        container.appendChild(btn);
    });
    
    container.style.display = 'flex';
    hideYesNoButtons();
}

function showYesNoButtons(showNew = true) {
    const container = document.getElementById('yesno-buttons');
    if (container) {
        container.style.display = 'flex';
        // Show/hide "New" button based on context
        const newBtn = container.querySelector('.btn-new');
        if (newBtn) newBtn.style.display = showNew ? 'block' : 'none';
    }
    hideNumberedOptions();
}

function hideNumberedOptions() {
    const container = document.getElementById('option-buttons');
    if (container) {
        container.style.display = 'none';
        container.innerHTML = '';
    }
}

function hideYesNoButtons() {
    const container = document.getElementById('yesno-buttons');
    if (container) container.style.display = 'none';
}

function hideAllOptionButtons() {
    hideNumberedOptions();
    hideYesNoButtons();
}

function sendQuickResponse(response) {
    // Send the response as text_input (same format as typing)
    // Note: Don't add output here - server will broadcast it back
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({type: 'text_input', content: response}));
        hideAllOptionButtons();
        showToast(`Sent: ${response}`, 'info');
    }
}

// Check if current session is running a command
function isCurrentSessionRunning() {
    if (!currentSessionId || !sessions[currentSessionId]) return false;
    return sessions[currentSessionId].status === 'running';
}

// Auto-create new session if current is busy
function ensureIdleSession() {
    if (isCurrentSessionRunning()) {
        showToast('Creating new session (current is busy)', 'info');
        ws.send(JSON.stringify({ type: 'new_session' }));
        document.getElementById('output').innerHTML = '';
        hideProgressBar();
        hideAllOptionButtons();
        addOutput('🆕 ' + msg('newConversation') + ' (previous session still running)', 'system');
        return true;  // New session created
    }
    return false;  // Current session is idle
}

// Parse TTS message and show appropriate buttons
function parseAndShowButtons(text) {
    const lower = text.toLowerCase();
    
    // Check for numbered options (1: xxx, 2: xxx)
    const numberedMatch = text.match(/(\d+)[:.]\s*([^.]+)/g);
    if (numberedMatch && numberedMatch.length >= 2) {
        const options = numberedMatch.map(m => {
            const match = m.match(/(\d+)[:.]\s*(.+)/);
            return match ? {key: match[1], text: match[2].trim()} : null;
        }).filter(x => x);
        
        if (options.length >= 2) {
            showNumberedOptions(options);
            return;
        }
    }
    
    // Check for yes/no questions
    if (lower.includes("say 'yes'") || lower.includes("say yes") || 
        lower.includes("confirm") || lower.includes("do you want")) {
        const showNew = lower.includes("new") || lower.includes("different");
        showYesNoButtons(showNew);
        return;
    }
    
    // Hide buttons if no options detected
    hideAllOptionButtons();
}

// ============================================================================
// Voice Recognition
// ============================================================================

function initVoice() {
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = CONFIG.language === 'pl' ? 'pl-PL' : 
                          CONFIG.language === 'de' ? 'de-DE' : 'en-US';
        
        recognition.onstart = () => {
            isListening = true;
            document.getElementById('voice-btn').classList.add('listening');
            document.getElementById('voice-status').classList.add('listening');
            document.getElementById('voice-status-text').textContent = 
                isSpeaking ? msg('listeningWhileSpeaking') : msg('listening');
        };
        
        recognition.onend = () => {
            isListening = false;
            document.getElementById('voice-btn').classList.remove('listening');
            document.getElementById('voice-status').classList.remove('listening');
            if (!isSpeaking) {
                document.getElementById('voice-status-text').textContent = msg('voiceReady');
            }
        };
        
        recognition.onspeechstart = () => {
            handleBargeIn();
        };
        
        recognition.onresult = (event) => {
            const result = event.results[event.results.length - 1];
            const text = result[0].transcript;
            
            if (result.isFinal) {
                sendVoiceInput(text);
            } else if (bargeInMode && isSpeaking) {
                handleBargeIn();
            }
        };
        
        recognition.onerror = (event) => {
            if (event.error !== 'no-speech') {
                console.error('Speech recognition error:', event.error);
            }
            isListening = false;
            document.getElementById('voice-btn').classList.remove('listening');
        };
    } else {
        document.getElementById('voice-btn').disabled = true;
        document.getElementById('voice-status-text').textContent = 'Voice not supported';
    }
}

function toggleVoice() {
    if (isListening) {
        recognition.stop();
    } else {
        recognition.start();
    }
}

function sendVoiceInput(text) {
    const lower = text.toLowerCase();
    if (pendingCommand && (lower === 'yes' || lower === 'yeah' || lower === 'okay' || 
        lower === 'tak' || lower === 'ja')) {
        confirm();
        return;
    }
    if (pendingCommand && (lower === 'no' || lower === 'cancel' || lower === 'nie' || 
        lower === 'nein')) {
        cancel();
        return;
    }
    
    // Auto-create new session if current is busy running a command
    if (isCurrentSessionRunning()) {
        ensureIdleSession();
        // Small delay to let new session be created, then send
        setTimeout(() => {
            ws.send(JSON.stringify({ type: 'voice_input', content: text }));
        }, 100);
    } else {
        ws.send(JSON.stringify({ type: 'voice_input', content: text }));
    }
}

// ============================================================================
// Text-to-Speech
// ============================================================================

function speak(text) {
    if (synthesis.speaking) {
        synthesis.cancel();
    }
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.1;
    utterance.pitch = 1.0;
    utterance.lang = CONFIG.language === 'pl' ? 'pl-PL' : 
                     CONFIG.language === 'de' ? 'de-DE' : 'en-US';
    
    utterance.onstart = () => {
        isSpeaking = true;
        document.getElementById('voice-btn').classList.add('speaking');
        document.getElementById('voice-status').classList.add('speaking');
        document.getElementById('voice-status-text').textContent = msg('speaking');
        
        if (bargeInMode && recognition && !isListening) {
            try { recognition.start(); } catch(e) {}
        }
    };
    
    utterance.onend = () => {
        isSpeaking = false;
        document.getElementById('voice-btn').classList.remove('speaking');
        document.getElementById('voice-status').classList.remove('speaking');
        document.getElementById('voice-status-text').textContent = msg('voiceReady');
        
        if (continuousMode && recognition && !isListening) {
            setTimeout(() => {
                if (!isListening) {
                    try { recognition.start(); } catch(e) {}
                }
            }, 300);
        }
    };
    
    synthesis.speak(utterance);
}

function handleBargeIn() {
    if (bargeInMode && isSpeaking) {
        synthesis.cancel();
        isSpeaking = false;
        document.getElementById('voice-btn').classList.remove('speaking');
        document.getElementById('voice-status-text').textContent = 'Listening (interrupted)';
        addOutput('⚡ [' + msg('bargeIn') + ']', 'system');
    }
}

// ============================================================================
// Controls
// ============================================================================

function sendText() {
    const input = document.getElementById('text-input');
    const text = input.value.trim();
    if (text) {
        // Auto-create new session if current is busy running a command
        if (isCurrentSessionRunning()) {
            ensureIdleSession();
            // Small delay to let new session be created, then send
            setTimeout(() => {
                ws.send(JSON.stringify({ type: 'text_input', content: text }));
            }, 100);
        } else {
            ws.send(JSON.stringify({ type: 'text_input', content: text }));
        }
        input.value = '';
    }
}

function confirm() {
    ws.send(JSON.stringify({ type: 'confirm' }));
    pendingCommand = null;
    showConfirmButtons(false);
}

function cancel() {
    ws.send(JSON.stringify({ type: 'cancel' }));
    pendingCommand = null;
    showConfirmButtons(false);
}

function stop() {
    ws.send(JSON.stringify({ type: 'stop' }));
}

function toggleContinuous() {
    continuousMode = !continuousMode;
    const btn = document.getElementById('continuous-btn');
    if (continuousMode) {
        btn.classList.add('active');
        btn.textContent = '🔄 Continuous: ON';
    } else {
        btn.classList.remove('active');
        btn.textContent = '🔄 Continuous: OFF';
    }
}

function toggleBargeIn() {
    bargeInMode = !bargeInMode;
    const btn = document.getElementById('bargein-btn');
    if (bargeInMode) {
        btn.classList.add('active');
        btn.textContent = '⚡ Barge-in: ON';
    } else {
        btn.classList.remove('active');
        btn.textContent = '⚡ Barge-in: OFF';
    }
}

// ============================================================================
// Language
// ============================================================================

// Apply language locally (used when receiving from server via WebSocket)
function applyLanguage(lang) {
    if (!TRANSLATIONS[lang]) {
        console.warn('Language not supported:', lang);
        lang = 'en';
    }
    
    CONFIG.language = lang;
    const langPack = TRANSLATIONS[lang];
    
    // Update voice recognition language
    if (recognition) {
        recognition.lang = langPack.voiceCode;
        console.log('Voice recognition set to:', langPack.voiceCode);
    }
    
    // Update UI elements with translations
    updateAllUIText();
    
    // Update language selector buttons
    document.querySelectorAll('.lang-selector button').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.lang === lang);
    });
    
    // No localStorage - state is managed by server via SQLite
}

// Set language command - sends to server for persistence (CQRS command)
function setLanguage(lang) {
    if (!TRANSLATIONS[lang]) {
        console.warn('Language not supported:', lang);
        return;
    }
    
    // Apply locally first for immediate UI feedback
    applyLanguage(lang);
    
    // Update URL state
    AppState.setLanguage(lang);
    trackAction('language-change', { lang });
    
    // Send command to server (event sourcing - server persists to SQLite)
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'set_language', content: lang }));
    }
    
    showToast(`${TRANSLATIONS[lang]?.name || lang}`, 'info');
}

// Reset grid to defaults
function resetGrid() {
    GridManager.reset();
    trackAction('grid-reset');
}

function updateAllUIText() {
    const lang = TRANSLATIONS[CONFIG.language] || TRANSLATIONS.en;
    
    // Update elements with data-i18n attribute (preserving icons)
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        const [category, field] = key.split('.');
        if (lang[category] && lang[category][field]) {
            // Preserve leading emoji if present
            const currentText = el.textContent;
            const emojiMatch = currentText.match(/^([\u{1F300}-\u{1F9FF}]|[\u2600-\u26FF]|[\u2700-\u27BF]|⏹|📋|🗑️|➕|✓|✗|🔄)/u);
            const emoji = emojiMatch ? emojiMatch[0] + ' ' : '';
            el.textContent = emoji + lang[category][field];
        }
    });
    
    // Update placeholders with data-i18n-placeholder
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.dataset.i18nPlaceholder;
        const [category, field] = key.split('.');
        if (lang[category] && lang[category][field]) {
            el.placeholder = lang[category][field];
        }
    });
    
    // Update text input placeholder
    const textInput = document.getElementById('text-input');
    if (textInput) textInput.placeholder = ui('type_command');
    
    // Update quick action buttons
    const quickActions = document.getElementById('quick-actions');
    if (quickActions) {
        const buttons = quickActions.querySelectorAll('.quick-action');
        buttons.forEach(btn => {
            const i18nKey = btn.dataset.i18n;
            if (i18nKey) {
                const [cat, field] = i18nKey.split('.');
                if (lang[cat] && lang[cat][field]) {
                    const emojiMatch = btn.textContent.match(/^([\u{1F300}-\u{1F9FF}]|[\u2600-\u26FF]|[\u2700-\u27BF]|⏹|📧|👤|📊)/u);
                    const emoji = emojiMatch ? emojiMatch[0] + ' ' : '';
                    btn.textContent = emoji + lang[cat][field];
                }
            }
        });
    }
    
    // Update audio settings buttons
    const continuousBtn = document.getElementById('continuous-btn');
    if (continuousBtn) {
        const state = continuousMode ? (lang.ui?.on || 'ON') : (lang.ui?.off || 'OFF');
        continuousBtn.textContent = `🔄 ${lang.ui?.continuous || 'Continuous'}: ${state}`;
    }
    
    const bargeinBtn = document.getElementById('bargein-btn');
    if (bargeinBtn) {
        const state = bargeInMode ? (lang.ui?.on || 'ON') : (lang.ui?.off || 'OFF');
        bargeinBtn.textContent = `⚡ ${lang.ui?.barge_in || 'Barge-in'}: ${state}`;
    }
    
    // Update Yes/No/New buttons
    const yesnoButtons = document.getElementById('yesno-buttons');
    if (yesnoButtons) {
        const yesBtn = yesnoButtons.querySelector('.btn-yes');
        const noBtn = yesnoButtons.querySelector('.btn-no');
        const newBtn = yesnoButtons.querySelector('.btn-new');
        if (yesBtn) yesBtn.textContent = `✓ ${lang.ui?.yes || 'Yes'}`;
        if (noBtn) noBtn.textContent = `✗ ${lang.ui?.no || 'No'}`;
        if (newBtn) newBtn.textContent = `🔄 ${lang.ui?.new || 'New'}`;
    }
    
    // Update voice hint
    const voiceHint = document.querySelector('.voice-hint');
    if (voiceHint) voiceHint.textContent = lang.ui?.click_to_talk || 'Click or press Space';
}

// ============================================================================
// Keyboard Shortcuts
// ============================================================================

document.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        toggleVoice();
    }
});

// ============================================================================
// Initialize
// ============================================================================

async function init() {
    // Load state from URL first
    AppState.loadFromURL();
    if (AppState.language) {
        CONFIG.language = AppState.language;
    }
    
    // Check auth status and update UI
    await checkAuthStatus();
    
    // Initialize grid manager (async - loads positions from server if logged in)
    await GridManager.init();
    
    // Connect to WebSocket
    connectWS();
    initVoice();
    
    // Apply language (from URL or default)
    setTimeout(() => {
        applyLanguage(CONFIG.language);
    }, 100);
    
    // Track initial page load
    trackAction('page-load');
    
    console.log('🎛️ Dashboard initialized. URL state:', AppState);
}

// Request full config from server (CQRS query)
function requestConfig() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'get_config' }));
    }
}

// =============================================================================
// Variables Panel (Excel-like editor)
// =============================================================================

// Update variable and send to server (CQRS command)
function updateVariable(key, value) {
    console.log('Updating variable:', key, '=', value);
    
    // Show syncing status
    setVarStatus('syncing', 'Syncing...');
    
    // Special handling for language
    if (key === 'language') {
        setLanguage(value);
        setVarStatus('synced', 'Synced with server');
        return;
    }
    
    // Send to server via WebSocket (CQRS command)
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ 
            type: 'set_variable', 
            content: { key, value } 
        }));
    }
    
    // Highlight the changed row
    const row = document.querySelector(`.var-row[data-key="${key}"]`);
    if (row) {
        row.classList.add('changed');
        setTimeout(() => row.classList.remove('changed'), 500);
    }
}

// Clear variable value
function clearVariable(key) {
    const input = document.getElementById(`var-${key}`);
    if (input) {
        input.value = '';
        updateVariable(key, '');
    }
}

// Add new custom variable
function addVariable() {
    const name = prompt('Variable name:');
    if (!name || !name.trim()) return;
    
    const key = name.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');
    
    // Check if already exists
    if (document.querySelector(`.var-row[data-key="${key}"]`)) {
        showToast(`Variable "${key}" already exists`, 'error');
        return;
    }
    
    // Create new row
    const table = document.getElementById('variables-table');
    const row = document.createElement('div');
    row.className = 'var-row';
    row.dataset.key = key;
    row.innerHTML = `
        <span class="var-name">📝 ${key}</span>
        <input type="text" class="var-input" id="var-${key}" 
               placeholder="Enter value..."
               onchange="updateVariable('${key}', this.value)"
               onkeypress="if(event.key==='Enter')this.blur()">
        <span class="var-actions">
            <button onclick="removeVariable('${key}')" title="Remove">🗑️</button>
        </span>
    `;
    table.appendChild(row);
    
    // Focus the new input
    const input = document.getElementById(`var-${key}`);
    if (input) input.focus();
    
    showToast(`Variable "${key}" added`, 'success');
}

// Remove custom variable
function removeVariable(key) {
    const row = document.querySelector(`.var-row[data-key="${key}"]`);
    if (row) {
        row.remove();
        // Notify server to remove variable
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ 
                type: 'remove_variable', 
                content: { key } 
            }));
        }
        showToast(`Variable "${key}" removed`, 'info');
    }
}

// Set variables panel status
function setVarStatus(status, text) {
    const statusEl = document.getElementById('var-status');
    const textEl = document.getElementById('var-status-text');
    if (statusEl) {
        statusEl.className = 'var-status ' + status;
    }
    if (textEl) {
        textEl.textContent = text;
    }
}

// Update all variable inputs from server data
function updateVariablesFromConfig(config) {
    for (const [key, value] of Object.entries(config)) {
        const input = document.getElementById(`var-${key}`);
        if (input) {
            if (input.tagName === 'SELECT') {
                input.value = value || input.options[0]?.value || '';
            } else {
                input.value = value || '';
            }
        }
    }
    setVarStatus('synced', 'Synced with server');
}

// Update context display (legacy - now uses variables panel)
function updateContext(ctx) {
    // Update variables panel inputs
    updateVariablesFromConfig(ctx);
}

// =============================================================================
// URL State Management (for debugging & state tracking)
// =============================================================================

const AppState = {
    language: CONFIG.language,
    panel: null,        // Currently focused panel
    action: null,       // Current action (typing, speaking, etc.)
    session: null,      // Current session ID
    view: 'dashboard',  // Current view
    
    // Update URL with current state
    updateURL() {
        const params = new URLSearchParams();
        if (this.language !== 'en') params.set('lang', this.language);
        if (this.panel) params.set('panel', this.panel);
        if (this.action) params.set('action', this.action);
        if (this.session) params.set('session', this.session);
        if (this.view !== 'dashboard') params.set('view', this.view);
        
        const hash = params.toString();
        const newURL = window.location.pathname + (hash ? '#' + hash : '');
        window.history.replaceState(null, '', newURL);
    },
    
    // Load state from URL
    loadFromURL() {
        const hash = window.location.hash.slice(1);
        if (!hash) return;
        
        const params = new URLSearchParams(hash);
        if (params.has('lang')) this.language = params.get('lang');
        if (params.has('panel')) this.panel = params.get('panel');
        if (params.has('action')) this.action = params.get('action');
        if (params.has('session')) this.session = params.get('session');
        if (params.has('view')) this.view = params.get('view');
    },
    
    // Set action and update URL
    setAction(action) {
        this.action = action;
        this.updateURL();
        console.log(`[Action] ${action}`);
    },
    
    // Set focused panel
    setPanel(panelId) {
        this.panel = panelId;
        this.updateURL();
    },
    
    // Set session
    setSession(sessionId) {
        this.session = sessionId;
        this.updateURL();
    },
    
    // Set language
    setLanguage(lang) {
        this.language = lang;
        this.updateURL();
    }
};

// Track user actions
function trackAction(action, details = {}) {
    AppState.setAction(action);
    const timestamp = new Date().toISOString().slice(11, 19);
    console.log(`[${timestamp}] Action: ${action}`, details);
}

// Track panel focus
document.addEventListener('click', (e) => {
    const panel = e.target.closest('.panel');
    if (panel && panel.id) {
        AppState.setPanel(panel.id);
    }
});

// Track typing
document.addEventListener('input', (e) => {
    if (e.target.id === 'text-input') {
        trackAction('typing', { length: e.target.value.length });
    }
});

// =============================================================================
// Grid Layout Management (Drag & Drop + Resize)
// =============================================================================

const GridManager = {
    // Grid configuration (10 columns x 8 rows for more flexibility)
    cols: 10,
    rows: 8,
    
    // Panel positions (stored in localStorage)
    positions: {},
    
    // Default positions (8 rows total: 1 header + 7 content)
    defaults: {
        'header-panel': { col: 1, row: 1, colSpan: 10, rowSpan: 1 },
        'conversations-panel': { col: 1, row: 2, colSpan: 2, rowSpan: 3 },
        'processes-panel': { col: 1, row: 5, colSpan: 2, rowSpan: 4 },  // Extend to row 8
        'output-panel': { col: 3, row: 2, colSpan: 5, rowSpan: 7 },     // Extend to row 8
        'audio-panel': { col: 8, row: 2, colSpan: 3, rowSpan: 2 },
        'text-panel': { col: 8, row: 4, colSpan: 3, rowSpan: 2 },
        'variables-panel': { col: 8, row: 6, colSpan: 3, rowSpan: 3 },  // Extend to row 8
    },
    
    // Initialize grid
    async init() {
        await this.loadPositions();
        this.applyPositions();
        this.setupDragDrop();
        this.setupResize();
    },
    
    // Current user (null if not logged in)
    currentUser: null,
    
    // Load positions from server (if logged in) or localStorage
    async loadPositions() {
        // Try to get user from server
        try {
            const resp = await fetch('/auth/me');
            const data = await resp.json();
            if (data.authenticated && data.user) {
                this.currentUser = data.user;
                console.log(`👤 Logged in as: ${data.user.email}`);
                
                // Load user settings from server
                const settingsResp = await fetch('/auth/settings');
                if (settingsResp.ok) {
                    const settings = await settingsResp.json();
                    if (settings.panel_positions) {
                        this.positions = settings.panel_positions;
                        console.log('📐 Loaded grid positions from server');
                        return;
                    }
                }
            }
        } catch (e) {
            console.log('Not logged in, using local storage');
        }
        
        // Try localStorage fallback
        try {
            const stored = localStorage.getItem('streamware_grid_positions');
            if (stored) {
                this.positions = JSON.parse(stored);
                console.log('📐 Loaded grid positions from localStorage');
                return;
            }
        } catch (e) {}
        
        // Use defaults
        this.positions = { ...this.defaults };
        console.log('📐 Using default grid positions');
    },
    
    // Save positions to server (if logged in) and localStorage
    async savePositions() {
        // Save to localStorage (always)
        try {
            localStorage.setItem('streamware_grid_positions', JSON.stringify(this.positions));
        } catch (e) {}
        
        // Save to server (if logged in)
        if (this.currentUser) {
            try {
                await fetch('/auth/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ panel_positions: this.positions })
                });
                console.log('📐 Saved grid positions to server');
            } catch (e) {
                console.log('Failed to save to server:', e);
            }
        }
    },
    
    // Apply positions to panels
    applyPositions() {
        Object.entries(this.positions).forEach(([panelId, pos]) => {
            const panel = document.getElementById(panelId);
            if (panel) {
                panel.style.gridColumn = `${pos.col} / span ${pos.colSpan}`;
                panel.style.gridRow = `${pos.row} / span ${pos.rowSpan}`;
            }
        });
    },
    
    // Set panel position
    setPosition(panelId, col, row, colSpan, rowSpan) {
        this.positions[panelId] = { col, row, colSpan, rowSpan };
        this.applyPositions();
        this.savePositions();
        trackAction('grid-move', { panelId, col, row, colSpan, rowSpan });
    },
    
    // Reset to defaults
    reset() {
        this.positions = { ...this.defaults };
        this.applyPositions();
        this.savePositions();
        showToast('Grid reset to defaults', 'info');
    },
    
    // Setup drag & drop
    setupDragDrop() {
        document.querySelectorAll('.btn-drag').forEach(btn => {
            btn.addEventListener('mousedown', (e) => {
                e.preventDefault();
                const panel = btn.closest('.panel');
                if (!panel) return;
                
                this.startDrag(panel, e);
            });
        });
    },
    
    // Start dragging
    startDrag(panel, startEvent) {
        panel.classList.add('dragging');
        trackAction('drag-start', { panel: panel.id });
        
        const dashboard = document.querySelector('.dashboard');
        const rect = dashboard.getBoundingClientRect();
        const cellWidth = rect.width / this.cols;
        const cellHeight = (rect.height - 50) / this.rows; // Subtract header
        
        const onMove = (e) => {
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            // Calculate grid position
            const col = Math.max(1, Math.min(this.cols, Math.ceil(x / cellWidth)));
            const row = Math.max(1, Math.min(this.rows, Math.ceil(y / cellHeight)));
            
            // Preview position
            const pos = this.positions[panel.id] || this.defaults[panel.id];
            panel.style.gridColumn = `${col} / span ${pos.colSpan}`;
            panel.style.gridRow = `${row} / span ${pos.rowSpan}`;
        };
        
        const onUp = (e) => {
            panel.classList.remove('dragging');
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
            
            // Calculate final position
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const col = Math.max(1, Math.min(this.cols, Math.ceil(x / cellWidth)));
            const row = Math.max(1, Math.min(this.rows, Math.ceil(y / cellHeight)));
            
            const pos = this.positions[panel.id] || this.defaults[panel.id];
            this.setPosition(panel.id, col, row, pos.colSpan, pos.rowSpan);
            
            trackAction('drag-end', { panel: panel.id, col, row });
        };
        
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
    },
    
    // Setup resize handles
    setupResize() {
        document.querySelectorAll('.resize-handle').forEach(handle => {
            handle.addEventListener('mousedown', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const panel = handle.closest('.panel');
                if (!panel) return;
                
                this.startResize(panel, e);
            });
        });
    },
    
    // Start resizing
    startResize(panel, startEvent) {
        panel.classList.add('resizing');
        trackAction('resize-start', { panel: panel.id });
        
        const dashboard = document.querySelector('.dashboard');
        const rect = dashboard.getBoundingClientRect();
        
        // Get header height for offset
        const headerPanel = document.getElementById('header-panel');
        const headerHeight = headerPanel ? headerPanel.offsetHeight + 10 : 60; // +gap
        
        // Use viewport height for better resize range (dashboard may not fill 100%)
        const availableHeight = Math.max(rect.height, window.innerHeight - rect.top);
        const contentRows = this.rows - 1; // -1 for header row
        
        const cellWidth = rect.width / this.cols;
        const cellHeight = (availableHeight - headerHeight) / contentRows;
        
        const pos = this.positions[panel.id] || this.defaults[panel.id];
        const startCol = pos.col;
        const startRow = pos.row;
        
        const onMove = (e) => {
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            // Calculate grid cell based on mouse position (relative to content area)
            const gridCol = Math.floor(x / cellWidth) + 1;
            const contentY = y - headerHeight;
            const gridRow = Math.floor(contentY / cellHeight) + 2; // +2 because content starts at row 2
            
            // Calculate span from start position to current grid cell
            // Allow resizing up to max grid size
            const maxColSpan = this.cols - startCol + 1;
            const maxRowSpan = this.rows - startRow + 1;
            
            const colSpan = Math.max(1, Math.min(maxColSpan, gridCol - startCol + 1));
            const rowSpan = Math.max(1, Math.min(maxRowSpan, gridRow - startRow + 1));
            
            // Preview size
            panel.style.gridColumn = `${startCol} / span ${colSpan}`;
            panel.style.gridRow = `${startRow} / span ${rowSpan}`;
        };
        
        const onUp = (e) => {
            panel.classList.remove('resizing');
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
            
            // Calculate final size (same logic as onMove)
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const gridCol = Math.floor(x / cellWidth) + 1;
            const contentY = y - headerHeight;
            const gridRow = Math.floor(contentY / cellHeight) + 2;
            
            const maxColSpan = this.cols - startCol + 1;
            const maxRowSpan = this.rows - startRow + 1;
            
            const colSpan = Math.max(1, Math.min(maxColSpan, gridCol - startCol + 1));
            const rowSpan = Math.max(1, Math.min(maxRowSpan, gridRow - startRow + 1));
            
            this.setPosition(panel.id, startCol, startRow, colSpan, rowSpan);
            trackAction('resize-end', { panel: panel.id, colSpan, rowSpan });
        };
        
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
    }
};

// =============================================================================
// Panel Grid Management
// =============================================================================

// Toggle panel expand/collapse
function toggleExpand(panelId) {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    
    const isExpanded = panel.classList.contains('expanded');
    
    // Remove expanded from all panels first
    document.querySelectorAll('.panel.expanded').forEach(p => {
        p.classList.remove('expanded');
        const btn = p.querySelector('.btn-expand');
        if (btn) btn.textContent = '⛶';
    });
    
    // Toggle current panel
    if (!isExpanded) {
        panel.classList.add('expanded');
        const btn = panel.querySelector('.btn-expand');
        if (btn) btn.textContent = '⛶'; // Could use different icon for collapse
        showToast('Panel expanded - click ⛶ to restore', 'info');
    }
}

// Close expanded panel on Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.panel.expanded').forEach(p => {
            p.classList.remove('expanded');
            const btn = p.querySelector('.btn-expand');
            if (btn) btn.textContent = '⛶';
        });
    }
});

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
