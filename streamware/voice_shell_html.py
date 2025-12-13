"""
Voice Shell HTML Templates

HTML, CSS, and JavaScript templates for the voice shell web UI.
Extracted from voice_shell_server.py for modularity.
"""

from pathlib import Path

# WEB UI HTML
# =============================================================================

def get_voice_shell_html_from_template(ws_port: int, language: str = "en") -> str:
    """Load HTML from template files (new modular approach)."""
    import socket
    hostname = socket.gethostname()
    
    templates_dir = Path(__file__).parent / "templates"
    
    try:
        # Load template
        html_path = templates_dir / "voice_shell.html"
        css_path = templates_dir / "voice_shell.css"
        js_path = templates_dir / "voice_shell.js"
        
        if html_path.exists():
            html = html_path.read_text()
            
            # Replace placeholders
            html = html.replace("{{WS_HOST}}", "localhost")
            html = html.replace("{{WS_PORT}}", str(ws_port))
            html = html.replace("{{LANGUAGE}}", language)
            
            # Inline CSS and JS for simplicity
            if css_path.exists():
                css = css_path.read_text()
                html = html.replace(
                    '<link rel="stylesheet" href="/static/voice_shell.css">',
                    f'<style>{css}</style>'
                )
            
            if js_path.exists():
                js = js_path.read_text()
                # Remove CONFIG definition from JS (already defined in HTML template)
                import re
                js = re.sub(r'const CONFIG = \{[^}]+\};', '', js, flags=re.DOTALL)
                html = html.replace(
                    '<script src="/static/voice_shell.js"></script>',
                    f'<script>{js}</script>'
                )
            
            return html
    except Exception as e:
        print(f"Warning: Could not load template: {e}")
    
    # Fallback to inline HTML
    return get_voice_shell_html(ws_port)


def get_voice_shell_html(ws_port: int) -> str:
    """Generate the voice shell web UI HTML (inline fallback)."""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Streamware Voice Shell</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        header {{
            text-align: center;
            padding: 20px 0;
            border-bottom: 1px solid #333;
        }}
        h1 {{
            font-size: 2em;
            color: #4fc3f7;
        }}
        .status {{
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 10px;
            font-size: 0.9em;
        }}
        .status-item {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .status-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #666;
        }}
        .status-dot.connected {{ background: #4caf50; }}
        .status-dot.listening {{ background: #ff9800; animation: pulse 1s infinite; }}
        .status-dot.speaking {{ background: #2196f3; animation: pulse 0.5s infinite; }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        .main {{
            display: grid;
            grid-template-columns: 250px 1fr 350px;
            gap: 20px;
            margin-top: 20px;
        }}
        @media (max-width: 1000px) {{
            .main {{ grid-template-columns: 1fr 1fr; }}
            .sessions-panel {{ display: none; }}
        }}
        @media (max-width: 700px) {{
            .main {{ grid-template-columns: 1fr; }}
        }}
        .sessions-panel {{
            max-height: 600px;
            overflow-y: auto;
        }}
        .session-item {{
            padding: 10px;
            margin: 5px 0;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            cursor: pointer;
            border-left: 3px solid #333;
        }}
        .session-item:hover {{ background: rgba(255,255,255,0.1); }}
        .session-item.active {{ border-left-color: #4fc3f7; background: rgba(79,195,247,0.1); }}
        .session-item.running {{ border-left-color: #ff9800; }}
        .session-item.completed {{ border-left-color: #4caf50; }}
        .session-item.error {{ border-left-color: #f44336; }}
        .session-name {{ font-weight: bold; font-size: 0.9em; }}
        .session-status {{ font-size: 0.75em; color: #888; }}
        .session-actions {{ display: flex; gap: 5px; margin-top: 5px; }}
        .session-actions button {{ 
            padding: 2px 8px; 
            font-size: 0.7em; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer;
        }}
        .btn-new-session {{
            width: 100%;
            padding: 10px;
            margin-bottom: 10px;
            background: #4fc3f7;
            color: black;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
        }}
        .btn-new-session:hover {{ background: #29b6f6; }}
        .panel {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
        }}
        .panel h2 {{
            font-size: 1.2em;
            color: #4fc3f7;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        #output {{
            height: 400px;
            overflow-y: auto;
            font-family: "Fira Code", monospace;
            font-size: 0.85em;
            background: #0d1117;
            padding: 15px;
            border-radius: 8px;
            white-space: pre-wrap;
            word-break: break-all;
        }}
        .output-line {{
            margin: 2px 0;
            line-height: 1.4;
        }}
        .output-line.input {{ color: #58a6ff; }}
        .output-line.command {{ color: #7ee787; }}
        .output-line.error {{ color: #f85149; }}
        .output-line.tts {{ color: #d2a8ff; }}
        .output-line.system {{ color: #8b949e; }}
        .controls {{
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}
        .voice-btn {{
            width: 120px;
            height: 120px;
            border-radius: 50%;
            border: 3px solid #4fc3f7;
            background: rgba(79, 195, 247, 0.1);
            color: #4fc3f7;
            font-size: 40px;
            cursor: pointer;
            transition: all 0.3s;
            margin: 0 auto;
        }}
        .voice-btn:hover {{
            background: rgba(79, 195, 247, 0.2);
            transform: scale(1.05);
        }}
        .voice-btn.listening {{
            background: rgba(255, 152, 0, 0.3);
            border-color: #ff9800;
            animation: pulse 1s infinite;
        }}
        .voice-btn.speaking {{
            background: rgba(33, 150, 243, 0.3);
            border-color: #2196f3;
        }}
        .text-input {{
            display: flex;
            gap: 10px;
        }}
        .text-input input {{
            flex: 1;
            padding: 12px 15px;
            border: 1px solid #333;
            border-radius: 8px;
            background: #0d1117;
            color: #e0e0e0;
            font-size: 1em;
        }}
        .text-input button {{
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            background: #4fc3f7;
            color: #000;
            font-weight: bold;
            cursor: pointer;
        }}
        .confirm-buttons {{
            display: flex;
            gap: 10px;
            justify-content: center;
        }}
        .confirm-buttons button {{
            padding: 10px 30px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
        }}
        .btn-yes {{ background: #4caf50; color: white; }}
        .btn-no {{ background: #f44336; color: white; }}
        .btn-stop {{ background: #ff9800; color: white; }}
        .btn-continuous {{ background: #333; color: #888; border: 1px solid #555; }}
        .btn-continuous.active {{ background: #2e7d32; color: white; border-color: #4caf50; }}
        .context {{
            background: #0d1117;
            padding: 10px 15px;
            border-radius: 8px;
            font-size: 0.85em;
            margin-top: 15px;
        }}
        .context-item {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #333;
        }}
        .context-item:last-child {{ border-bottom: none; }}
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎤 Streamware Voice Shell</h1>
            <div class="status">
                <div class="status-item">
                    <span class="status-dot" id="ws-status"></span>
                    <span id="ws-status-text">Connecting...</span>
                </div>
                <div class="status-item">
                    <span class="status-dot" id="voice-status"></span>
                    <span id="voice-status-text">Voice Ready</span>
                </div>
            </div>
        </header>
        
        <div class="main">
            <!-- Sessions Panel (left) -->
            <div class="panel sessions-panel">
                <h2>📋 Sessions</h2>
                <button class="btn-new-session" onclick="newSession()">➕ New Conversation</button>
                <div id="sessions-list"></div>
            </div>
            
            <!-- Shell Output (center) -->
            <div class="panel">
                <h2>
                    🖥️ Shell Output 
                    <span id="current-session-name" style="font-size: 0.7em; color: #888;"></span>
                    <button onclick="copyLogs()" style="float: right; font-size: 0.7em; padding: 4px 8px; cursor: pointer;" title="Copy logs">📋 Copy</button>
                    <button onclick="clearLogs()" style="float: right; font-size: 0.7em; padding: 4px 8px; cursor: pointer; margin-right: 5px;" title="Clear">🗑️ Clear</button>
                </h2>
                <div id="output"></div>
            </div>
            
            <!-- Voice Control (right) -->
            <div class="panel">
                <h2>🎤 Voice Control</h2>
                <div class="controls">
                    <button class="voice-btn" id="voice-btn" onclick="toggleVoice()">🎤</button>
                    <p style="text-align: center; color: #888;">Click or press Space to talk</p>
                    
                    <div class="text-input">
                        <input type="text" id="text-input" placeholder="Type a command..." 
                               onkeypress="if(event.key==='Enter')sendText()">
                        <button onclick="sendText()">Send</button>
                    </div>
                    
                    <div class="confirm-buttons" id="confirm-buttons" style="display:none;">
                        <button class="btn-yes" onclick="confirm()">✓ Yes</button>
                        <button class="btn-no" onclick="cancel()">✗ No</button>
                    </div>
                    
                    <div style="text-align: center; display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
                        <button class="btn-stop" onclick="stop()">⏹ Stop</button>
                        <button id="continuous-btn" class="btn-continuous active" onclick="toggleContinuous()">🔄 Continuous: ON</button>
                        <button id="bargein-btn" class="btn-continuous active" onclick="toggleBargeIn()">⚡ Barge-in: ON</button>
                    </div>
                    
                    <div class="context" id="context">
                        <div class="context-item">
                            <span>📹 URL:</span>
                            <span id="ctx-url">(not set)</span>
                        </div>
                        <div class="context-item">
                            <span>📧 Email:</span>
                            <span id="ctx-email">(not set)</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const WS_URL = "ws://" + window.location.hostname + ":{ws_port}";
        let ws;
        let recognition;
        let synthesis = window.speechSynthesis;
        let isListening = false;
        let pendingCommand = null;
        let currentSessionId = null;
        let sessions = {{}};
        
        // Session management
        function newSession() {{
            ws.send(JSON.stringify({{ type: 'new_session' }}));
            document.getElementById('output').innerHTML = '';
            addOutput('New conversation started. Say hello or a command.', 'system');
        }}
        
        function switchSession(sessionId) {{
            ws.send(JSON.stringify({{ type: 'switch_session', content: sessionId }}));
        }}
        
        function closeSession(sessionId) {{
            ws.send(JSON.stringify({{ type: 'close_session', content: sessionId }}));
        }}
        
        function updateSessionsList(sessionsList) {{
            const container = document.getElementById('sessions-list');
            container.innerHTML = '';
            sessions = {{}};
            
            sessionsList.forEach(s => {{
                sessions[s.id] = s;
                const div = document.createElement('div');
                div.className = 'session-item ' + s.status + (s.id === currentSessionId ? ' active' : '');
                div.setAttribute('data-session-id', s.id);
                div.innerHTML = `
                    <div class="session-name">${{s.name || 'Unnamed'}}</div>
                    <div class="session-status">${{s.status}} · ${{s.output_lines}} lines</div>
                    <div class="session-actions">
                        ${{s.status === 'running' ? '<button onclick="event.stopPropagation(); closeSession(\\'' + s.id + '\\')">⏹ Stop</button>' : ''}}
                        <button onclick="event.stopPropagation(); closeSession('` + s.id + `')">✕</button>
                    </div>
                `;
                div.addEventListener('click', function(e) {{
                    if (e.target.tagName !== 'BUTTON') {{
                        switchSession(s.id);
                    }}
                }});
                container.appendChild(div);
            }});
        }}
        
        function updateSessionInList(sessionId) {{
            // Update session status in UI
            const items = document.querySelectorAll('.session-item');
            items.forEach(item => {{
                if (item.dataset.sessionId === sessionId) {{
                    // Refresh from sessions object
                }}
            }});
        }}
        
        // Initialize WebSocket
        function connectWS() {{
            ws = new WebSocket(WS_URL);
            
            ws.onopen = () => {{
                document.getElementById('ws-status').classList.add('connected');
                document.getElementById('ws-status-text').textContent = 'Connected';
                addOutput('Connected to Streamware Voice Shell', 'system');
                // Request sessions list (new session will be created if none exist)
                ws.send(JSON.stringify({{ type: 'get_sessions' }}));
            }};
            
            ws.onclose = () => {{
                document.getElementById('ws-status').classList.remove('connected');
                document.getElementById('ws-status-text').textContent = 'Disconnected';
                setTimeout(connectWS, 3000);
            }};
            
            ws.onmessage = (event) => {{
                const data = JSON.parse(event.data);
                handleEvent(data);
            }};
        }}
        
        // Handle events from server
        function handleEvent(event) {{
            switch(event.type) {{
                case 'voice_input':
                case 'text_input':
                    addOutput('> ' + event.data.text, 'input');
                    break;
                    
                case 'command_parsed':
                    if (event.data.understood) {{
                        // Check if there are options to display
                        if (event.data.options && event.data.options.length > 0) {{
                            addOutput('❓ ' + event.data.explanation, 'system');
                            event.data.options.forEach(([key, desc]) => {{
                                addOutput('   ' + key + '. ' + desc, 'system');
                            }});
                        }} else {{
                            addOutput('✅ ' + event.data.explanation, 'system');
                            if (event.data.command) {{
                                addOutput('   Command: ' + event.data.command, 'command');
                                pendingCommand = event.data.command;
                                showConfirmButtons(true);
                            }}
                        }}
                    }} else {{
                        addOutput('❌ ' + event.data.explanation, 'error');
                    }}
                    break;
                    
                case 'command_executed':
                    addOutput('$ ' + event.data.command, 'command');
                    showConfirmButtons(false);
                    break;
                    
                case 'command_output':
                    addOutput(event.data.line, 'system');
                    break;
                
                case 'session_output':
                    // Output from a specific session
                    if (event.data.session_id === currentSessionId) {{
                        addOutput(event.data.line, 'system');
                    }}
                    updateSessionInList(event.data.session_id);
                    break;
                    
                case 'command_error':
                    addOutput('❌ Error: ' + event.data.error, 'error');
                    break;
                    
                case 'session_created':
                case 'session_closed':
                    updateSessionsList(event.data.sessions);
                    if (event.data.session) {{
                        currentSessionId = event.data.session.id;
                        document.getElementById('current-session-name').textContent = '(' + event.data.session.name + ')';
                    }}
                    break;
                    
                case 'session_switched':
                    currentSessionId = event.data.session.id;
                    document.getElementById('current-session-name').textContent = '(' + event.data.session.name + ')';
                    // Clear and show session output
                    document.getElementById('output').innerHTML = '';
                    if (event.data.output && event.data.output.length > 0) {{
                        event.data.output.forEach(line => {{
                            if (line) addOutput(line, 'system');
                        }});
                    }} else {{
                        addOutput('(No output yet)', 'system');
                    }}
                    // Update sessions list to show active
                    updateSessionsList(event.data.sessions || Object.values(sessions));
                    break;
                    
                case 'sessions_list':
                    updateSessionsList(event.data.sessions);
                    if (event.data.current) {{
                        currentSessionId = event.data.current;
                        // Update session name display
                        const currentSession = event.data.sessions.find(s => s.id === event.data.current);
                        if (currentSession) {{
                            document.getElementById('current-session-name').textContent = '(' + currentSession.name + ')';
                        }}
                    }}
                    // Show output from restored session
                    if (event.data.output && event.data.output.length > 0) {{
                        document.getElementById('output').innerHTML = '';
                        addOutput('📂 Restored conversation history:', 'system');
                        event.data.output.forEach(line => {{
                            if (line) addOutput(line, 'system');
                        }});
                    }}
                    break;
                    
                case 'command_completed':
                    addOutput('✓ Command completed', 'system');
                    break;
                    
                case 'command_cancel':
                    addOutput('✗ Cancelled', 'system');
                    showConfirmButtons(false);
                    break;
                    
                case 'tts_speak':
                    speak(event.data.text);
                    addOutput('🔊 ' + event.data.text, 'tts');
                    break;
                    
                case 'context_updated':
                    updateContext(event.data);
                    break;
            }}
        }}
        
        // Add output line
        function addOutput(text, type = 'system') {{
            const output = document.getElementById('output');
            const line = document.createElement('div');
            line.className = 'output-line ' + type;
            line.textContent = text;
            output.appendChild(line);
            output.scrollTop = output.scrollHeight;
        }}
        
        // Update context display
        function updateContext(ctx) {{
            document.getElementById('ctx-url').textContent = ctx.url || '(not set)';
            document.getElementById('ctx-email').textContent = ctx.email || '(not set)';
        }}
        
        // Copy logs to clipboard
        function copyLogs() {{
            const output = document.getElementById('output');
            const lines = Array.from(output.querySelectorAll('.output-line'))
                .map(el => el.textContent)
                .join('\\n');
            
            // Try clipboard API, fallback to execCommand
            if (navigator.clipboard && window.isSecureContext) {{
                navigator.clipboard.writeText(lines).then(() => {{
                    showCopyFeedback();
                }}).catch(() => {{ fallbackCopy(lines); }});
            }} else {{
                fallbackCopy(lines);
            }}
        }}
        
        function fallbackCopy(text) {{
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.left = '-9999px';
            document.body.appendChild(ta);
            ta.select();
            try {{ document.execCommand('copy'); showCopyFeedback(); }}
            catch(e) {{ alert('Copy failed'); }}
            document.body.removeChild(ta);
        }}
        
        function showCopyFeedback() {{
            const btn = document.querySelector('[onclick="copyLogs()"]');
            if (btn) {{
                const orig = btn.textContent;
                btn.textContent = '✅ Copied!';
                setTimeout(() => {{ btn.textContent = orig; }}, 1500);
            }}
        }}
        
        // Clear logs
        function clearLogs() {{
            document.getElementById('output').innerHTML = '';
            addOutput('Output cleared', 'system');
        }}
        
        // Show/hide confirm buttons
        function showConfirmButtons(show) {{
            document.getElementById('confirm-buttons').style.display = show ? 'flex' : 'none';
        }}
        
        // Voice recognition
        function initVoice() {{
            if ('webkitSpeechRecognition' in window) {{
                recognition = new webkitSpeechRecognition();
                recognition.continuous = false;
                recognition.interimResults = true;  // Enable interim for faster barge-in
                recognition.lang = 'en-US';
                
                recognition.onstart = () => {{
                    isListening = true;
                    document.getElementById('voice-btn').classList.add('listening');
                    document.getElementById('voice-status').classList.add('listening');
                    document.getElementById('voice-status-text').textContent = isSpeaking ? 'Listening (while speaking)...' : 'Listening...';
                }};
                
                recognition.onend = () => {{
                    isListening = false;
                    document.getElementById('voice-btn').classList.remove('listening');
                    document.getElementById('voice-status').classList.remove('listening');
                    if (!isSpeaking) {{
                        document.getElementById('voice-status-text').textContent = 'Voice Ready';
                    }}
                }};
                
                recognition.onspeechstart = () => {{
                    // User started speaking - trigger barge-in
                    handleBargeIn();
                }};
                
                recognition.onresult = (event) => {{
                    const result = event.results[event.results.length - 1];
                    const text = result[0].transcript;
                    
                    // Only process final results
                    if (result.isFinal) {{
                        sendVoiceInput(text);
                    }} else if (bargeInMode && isSpeaking) {{
                        // Interim result while speaking - barge-in!
                        handleBargeIn();
                    }}
                }};
                
                recognition.onerror = (event) => {{
                    if (event.error !== 'no-speech') {{
                        console.error('Speech recognition error:', event.error);
                    }}
                    isListening = false;
                    document.getElementById('voice-btn').classList.remove('listening');
                }};
            }} else {{
                document.getElementById('voice-btn').disabled = true;
                document.getElementById('voice-status-text').textContent = 'Voice not supported';
            }}
        }}
        
        // Toggle voice listening
        function toggleVoice() {{
            if (isListening) {{
                recognition.stop();
            }} else {{
                recognition.start();
            }}
        }}
        
        // Send voice input
        function sendVoiceInput(text) {{
            // Check for yes/no confirmation
            const lower = text.toLowerCase();
            if (pendingCommand && (lower === 'yes' || lower === 'yeah' || lower === 'okay' || lower === 'execute')) {{
                confirm();
                return;
            }}
            if (pendingCommand && (lower === 'no' || lower === 'cancel' || lower === 'stop')) {{
                cancel();
                return;
            }}
            
            ws.send(JSON.stringify({{ type: 'voice_input', content: text }}));
        }}
        
        // Send text input
        function sendText() {{
            const input = document.getElementById('text-input');
            const text = input.value.trim();
            if (text) {{
                ws.send(JSON.stringify({{ type: 'text_input', content: text }}));
                input.value = '';
            }}
        }}
        
        // Confirm command
        function confirm() {{
            ws.send(JSON.stringify({{ type: 'confirm' }}));
            pendingCommand = null;
        }}
        
        // Cancel command
        function cancel() {{
            ws.send(JSON.stringify({{ type: 'cancel' }}));
            pendingCommand = null;
        }}
        
        // Stop running process
        function stop() {{
            ws.send(JSON.stringify({{ type: 'stop' }}));
        }}
        
        // Continuous mode - auto-listen after TTS
        let continuousMode = true;
        let bargeInMode = true;  // Allow interrupting TTS
        let isSpeaking = false;
        
        function toggleContinuous() {{
            continuousMode = !continuousMode;
            const btn = document.getElementById('continuous-btn');
            if (continuousMode) {{
                btn.classList.add('active');
                btn.textContent = '🔄 Continuous: ON';
            }} else {{
                btn.classList.remove('active');
                btn.textContent = '🔄 Continuous: OFF';
            }}
        }}
        
        function toggleBargeIn() {{
            bargeInMode = !bargeInMode;
            const btn = document.getElementById('bargein-btn');
            if (bargeInMode) {{
                btn.classList.add('active');
                btn.textContent = '⚡ Barge-in: ON';
            }} else {{
                btn.classList.remove('active');
                btn.textContent = '⚡ Barge-in: OFF';
            }}
        }}
        
        // Text-to-speech with barge-in support
        function speak(text) {{
            if (synthesis.speaking) {{
                synthesis.cancel();
            }}
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.1;  // Slightly faster
            utterance.pitch = 1.0;
            
            utterance.onstart = () => {{
                isSpeaking = true;
                document.getElementById('voice-btn').classList.add('speaking');
                document.getElementById('voice-status').classList.add('speaking');
                document.getElementById('voice-status-text').textContent = 'Speaking...';
                
                // In barge-in mode, start listening while speaking
                if (bargeInMode && recognition && !isListening) {{
                    try {{
                        recognition.start();
                    }} catch(e) {{}}
                }}
            }};
            
            utterance.onend = () => {{
                isSpeaking = false;
                document.getElementById('voice-btn').classList.remove('speaking');
                document.getElementById('voice-status').classList.remove('speaking');
                document.getElementById('voice-status-text').textContent = 'Voice Ready';
                
                // Auto-listen in continuous mode (if not already listening from barge-in)
                if (continuousMode && recognition && !isListening) {{
                    setTimeout(() => {{
                        if (!isListening) {{
                            try {{
                                recognition.start();
                            }} catch(e) {{}}
                        }}
                    }}, 300);
                }}
            }};
            
            synthesis.speak(utterance);
        }}
        
        // Cancel TTS when user speaks (barge-in)
        function handleBargeIn() {{
            if (bargeInMode && isSpeaking) {{
                synthesis.cancel();
                isSpeaking = false;
                document.getElementById('voice-btn').classList.remove('speaking');
                document.getElementById('voice-status-text').textContent = 'Listening (interrupted)';
                addOutput('⚡ [Barge-in: TTS interrupted]', 'system');
            }}
        }}
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {{
            if (e.code === 'Space' && document.activeElement.tagName !== 'INPUT') {{
                e.preventDefault();
                toggleVoice();
            }}
        }});
        
        // Initialize
        connectWS();
        initVoice();
    </script>
</body>
</html>'''


# =============================================================================