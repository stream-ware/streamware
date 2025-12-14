"""
Web Templates Module

Contains HTML templates for the accounting web interface.
Separated for maintainability and reusability.
"""


def get_scanner_html_template() -> str:
    """Get the main scanner HTML template."""
    return '''<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Streamware Accounting - Live Scanner</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
        }
        .container { max-width: 1600px; margin: 0 auto; padding: 15px; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 15px;
        }
        h1 { font-size: 1.3rem; }
        .status { display: flex; gap: 20px; font-size: 0.9rem; }
        .status-item { display: flex; align-items: center; gap: 8px; }
        .status-dot {
            width: 10px;
            height: 10px;
            background: #4ade80;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        .status-dot.paused { background: #fbbf24; animation: none; }
        .status-dot.error { background: #f87171; animation: none; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .main-grid {
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 15px;
            height: calc(100vh - 100px);
        }
        @media (max-width: 1200px) {
            .main-grid { grid-template-columns: 1fr; height: auto; }
        }
        .docs-table-container {
            flex: 1;
            overflow: auto;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
        }
        .docs-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }
        .docs-table th {
            background: #334155;
            padding: 10px 8px;
            text-align: left;
            position: sticky;
            top: 0;
            cursor: pointer;
        }
        .docs-table th:hover { background: #475569; }
        .docs-table td {
            padding: 8px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .docs-table tr:hover { background: rgba(255,255,255,0.05); }
        .docs-table tr.pending { background: rgba(234,179,8,0.15); }
        .docs-table .thumb { width: 50px; height: 35px; object-fit: cover; border-radius: 4px; }
        .badge { padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
        .badge-invoice { background: #3b82f6; }
        .badge-receipt { background: #22c55e; }
        .badge-letter { background: #8b5cf6; }
        .badge-other { background: #6b7280; }
        .filter-bar {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 10px;
        }
        .filter-bar select {
            padding: 6px 10px;
            border-radius: 4px;
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.2);
            color: white;
            font-size: 0.8rem;
        }
        .stats-row {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }
        .stat-card {
            background: rgba(255,255,255,0.08);
            padding: 8px 15px;
            border-radius: 6px;
            text-align: center;
        }
        .stat-value { font-size: 1.3rem; font-weight: 700; color: #60a5fa; }
        .stat-label { font-size: 0.7rem; color: #888; }
        .panel {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
        }
        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .panel-title { font-size: 1.1rem; font-weight: 600; }
        .preview-container {
            position: relative;
            background: #000;
            border-radius: 8px;
            overflow: hidden;
            aspect-ratio: 16/9;
        }
        #preview-img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        .preview-overlay {
            position: absolute;
            bottom: 10px;
            left: 10px;
            right: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .preview-info {
            background: rgba(0,0,0,0.7);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.85rem;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .btn-primary { background: #3b82f6; color: white; }
        .btn-primary:hover { background: #2563eb; }
        .btn-success { background: #22c55e; color: white; }
        .btn-success:hover { background: #16a34a; }
        .btn-warning { background: #f59e0b; color: white; }
        .btn-warning:hover { background: #d97706; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-danger:hover { background: #dc2626; }
        .log-content {
            background: #0d1117;
            border-radius: 8px;
            padding: 15px;
            font-family: 'Fira Code', monospace;
            font-size: 0.8rem;
            max-height: 200px;
            overflow-y: auto;
        }
        .log-entry { margin-bottom: 5px; opacity: 0.8; }
        .log-entry.info { color: #58a6ff; }
        .log-entry.success { color: #3fb950; }
        .log-entry.warning { color: #d29922; }
        .log-entry.error { color: #f85149; }
        .docs-table .thumb { cursor: pointer; transition: transform 0.2s; }
        .docs-table .thumb:hover { transform: scale(1.1); }
        .doc-modal {
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.9);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .doc-modal.active { display: flex; }
        .doc-modal-content {
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            max-width: 90%;
            max-height: 90%;
            display: flex;
            gap: 20px;
        }
        .doc-modal-img {
            max-width: 600px;
            max-height: 80vh;
            object-fit: contain;
            border-radius: 8px;
        }
        .doc-modal-details {
            min-width: 300px;
            max-width: 400px;
        }
        .doc-modal-details h3 { margin-bottom: 15px; }
        .doc-modal-details .detail-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .doc-modal-details .detail-label { color: #888; }
        .doc-modal-details .detail-value { font-weight: 600; }
        .doc-modal-ocr {
            margin-top: 15px;
            background: #0d1117;
            padding: 10px;
            border-radius: 8px;
            max-height: 200px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.8rem;
            white-space: pre-wrap;
        }
        .doc-modal-close {
            position: absolute;
            top: 20px;
            right: 30px;
            font-size: 2rem;
            cursor: pointer;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📄 Streamware Accounting - Live Scanner</h1>
            <div class="status">
                <div class="status-item">
                    <div class="status-dot" id="status-dot"></div>
                    <span id="status-text">Skanowanie aktywne</span>
                </div>
                <div class="status-item">
                    <span>Projekt:</span>
                    <strong id="project-name">-</strong>
                </div>
            </div>
        </header>

        <div class="main-grid">
            <!-- Left Sidebar: Preview + Controls -->
            <div class="left-column" style="display:flex;flex-direction:column;gap:10px;">
                <div class="panel" style="padding:10px;">
                    <div class="preview-container" style="aspect-ratio:4/3;">
                        <img id="preview-img" src="" alt="Preview">
                        <div class="preview-overlay">
                            <div class="preview-info" id="detection-info">Oczekiwanie...</div>
                        </div>
                    </div>
                    <div class="controls" style="margin-top:8px;justify-content:center;">
                        <button class="btn-primary" onclick="toggleScanning()" style="padding:6px 12px;" title="Pauza/Wznów">
                            <span id="scan-btn-icon">⏸️</span>
                        </button>
                        <button class="btn-success" onclick="captureNow()" style="padding:6px 12px;" title="Zeskanuj">📷</button>
                        <button class="btn-primary" onclick="analyzeDeep()" style="padding:6px 12px;background:#8b5cf6;" title="Głęboka analiza OCR+LLM">🔬</button>
                        <button class="btn-warning" onclick="exportCSV()" style="padding:6px 12px;" title="Eksport CSV">📊</button>
                    </div>
                </div>
                
                <div class="panel" style="padding:10px;flex:1;overflow:hidden;display:flex;flex-direction:column;">
                    <div style="font-weight:600;margin-bottom:8px;">📋 Log</div>
                    <div class="log-content" id="log-content" style="flex:1;max-height:none;"></div>
                </div>
            </div>

            <!-- Main Content: Stats + Filters + Documents Table -->
            <div class="right-column" style="display:flex;flex-direction:column;gap:10px;overflow:hidden;">
                <!-- Stats Row -->
                <div class="stats-row">
                    <div class="stat-card"><div class="stat-value" id="total-docs">0</div><div class="stat-label">Dokumenty</div></div>
                    <div class="stat-card"><div class="stat-value" id="total-invoices">0</div><div class="stat-label">Faktury</div></div>
                    <div class="stat-card"><div class="stat-value" id="total-receipts">0</div><div class="stat-label">Paragony</div></div>
                    <div class="stat-card"><div class="stat-value" id="total-amount">0 zł</div><div class="stat-label">Suma</div></div>
                    <div class="stat-card"><div class="stat-value" id="pending-count-stat">0</div><div class="stat-label">Oczekuje</div></div>
                </div>
                
                <!-- Filters -->
                <div class="filter-bar">
                    <select id="filter-type" onchange="filterDocs()">
                        <option value="">Wszystkie typy</option>
                        <option value="invoice">Faktury</option>
                        <option value="receipt">Paragony</option>
                        <option value="letter">Pisma</option>
                        <option value="other">Inne</option>
                    </select>
                    <select id="filter-lang" onchange="filterDocs()">
                        <option value="">Wszystkie języki</option>
                        <option value="pl">Polski</option>
                        <option value="en">English</option>
                        <option value="de">Deutsch</option>
                    </select>
                    <select id="filter-status" onchange="filterDocs()">
                        <option value="">Wszystkie statusy</option>
                        <option value="pending">Oczekujące</option>
                        <option value="saved">Zapisane</option>
                    </select>
                    <input type="text" id="filter-search" placeholder="Szukaj..." onkeyup="filterDocs()" style="flex:1;min-width:150px;padding:6px 10px;border-radius:4px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);color:white;">
                </div>
                
                <!-- Documents Table -->
                <div class="docs-table-container">
                    <table class="docs-table">
                        <thead>
                            <tr>
                                <th style="width:60px;">Foto</th>
                                <th onclick="sortDocs('type')">Typ ▼</th>
                                <th onclick="sortDocs('date')">Data ▼</th>
                                <th onclick="sortDocs('amount')">Kwota ▼</th>
                                <th>NIP/ID</th>
                                <th>Język</th>
                                <th>OCR</th>
                                <th style="width:80px;">Akcje</th>
                            </tr>
                        </thead>
                        <tbody id="docs-table-body">
                            <tr><td colspan="8" style="text-align:center;color:#888;padding:40px;">Brak dokumentów</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- Document Modal -->
    <div id="doc-modal" class="doc-modal" onclick="if(event.target===this)closeDocModal()">
        <span class="doc-modal-close" onclick="closeDocModal()">&times;</span>
        <div class="doc-modal-content">
            <img id="doc-modal-img" class="doc-modal-img" src="" alt="Document">
            <div class="doc-modal-details">
                <h3>📄 Szczegóły dokumentu</h3>
                <div class="detail-row"><span class="detail-label">ID:</span><span class="detail-value" id="modal-id">-</span></div>
                <div class="detail-row"><span class="detail-label">Typ:</span><span class="detail-value" id="modal-type">-</span></div>
                <div class="detail-row"><span class="detail-label">Data:</span><span class="detail-value" id="modal-date">-</span></div>
                <div class="detail-row"><span class="detail-label">Kwota:</span><span class="detail-value" id="modal-amount">-</span></div>
                <div class="detail-row"><span class="detail-label">NIP:</span><span class="detail-value" id="modal-nip">-</span></div>
                <div class="detail-row"><span class="detail-label">Język:</span><span class="detail-value" id="modal-lang">-</span></div>
                <div class="detail-row"><span class="detail-label">Pewność:</span><span class="detail-value" id="modal-confidence">-</span></div>
                <div class="detail-row"><span class="detail-label">Status:</span><span class="detail-value" id="modal-status">-</span></div>
                <h4 style="margin-top:15px;">📝 OCR Text:</h4>
                <div class="doc-modal-ocr" id="modal-ocr">Brak danych OCR</div>
                <div style="margin-top:15px;display:flex;gap:10px;">
                    <button class="btn-success" id="modal-confirm-btn" onclick="confirmFromModal()" style="flex:1;">✓ Potwierdź</button>
                    <button class="btn-danger" onclick="removeFromModal()" style="flex:1;">✗ Usuń</button>
                </div>
            </div>
        </div>
    </div>

    <script>
''' + get_scanner_javascript() + '''
    </script>
</body>
</html>
'''


def get_scanner_javascript() -> str:
    """Get the JavaScript code for the scanner."""
    return '''
        // Documents data store
        let allDocs = [];
        let sortField = 'date';
        let sortDir = -1;
        let ws;
        let scanning = true;
        let frameCount = 0;
        let lastFpsUpdate = Date.now();

        function connect() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws`);

            ws.onopen = () => {
                log('Połączono z serwerem', 'success');
                updateStatus('active');
            };

            ws.onclose = () => {
                log('Rozłączono - ponawiam za 2s...', 'warning');
                updateStatus('error');
                setTimeout(connect, 2000);
            };

            ws.onerror = (e) => {
                log('Błąd WebSocket', 'error');
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleMessage(data);
                } catch (e) {
                    console.error('Parse error:', e);
                }
            };
        }

        function handleMessage(data) {
            switch(data.type) {
                case 'frame':
                    updatePreview(data);
                    break;
                case 'duplicate':
                    {
                        const sim = data.similarity != null ? Math.round(data.similarity * 100) : null;
                        const msg = data.message || (sim != null ? `🔄 Duplikat (${sim}%)` : '🔄 Duplikat');
                        log(msg, 'warning');

                        // Brief overlay hint
                        const info = document.getElementById('detection-info');
                        if (info) {
                            const prevText = info.textContent;
                            const prevBg = info.style.background;
                            info.textContent = msg;
                            info.style.background = 'rgba(239, 68, 68, 0.85)';
                            setTimeout(() => {
                                info.textContent = prevText;
                                info.style.background = prevBg;
                            }, 1200);
                        }
                    }
                    break;
                case 'document':
                    addDocument(data.document);
                    log(`Zarchiwizowano: ${data.document.type} - ${data.document.id}`, 'success');
                    break;
                case 'summary':
                    updateSummary(data.summary);
                    break;
                case 'config':
                    document.getElementById('project-name').textContent = data.project;
                    break;
                case 'log':
                    log(data.message, data.level || 'info');
                    break;
                case 'pending_document':
                    addPendingDocument(data.document);
                    break;
            }
        }

        function updatePreview(data) {
            const img = document.getElementById('preview-img');
            if (data.image) {
                img.src = 'data:image/jpeg;base64,' + data.image;
            }

            frameCount++;
            const now = Date.now();
            if (now - lastFpsUpdate > 1000) {
                lastFpsUpdate = now;
                frameCount = 0;
            }

            const info = document.getElementById('detection-info');
            if (data.document_in_view) {
                const conf = Math.round((data.confidence || 0) * 100);
                const docType = data.doc_type || 'dokument';
                const method = data.method || '';
                info.textContent = `🔍 ${docType} (${conf}%) [${method}]`;
                info.style.background = conf >= 85 ? 'rgba(34, 197, 94, 0.9)' : 
                                        conf >= 60 ? 'rgba(234, 179, 8, 0.9)' : 
                                        'rgba(59, 130, 246, 0.8)';
            } else {
                info.textContent = 'Oczekiwanie na dokument...';
                info.style.background = 'rgba(0,0,0,0.7)';
            }
        }

        function updateSummary(summary) {
            document.getElementById('total-docs').textContent = summary.total_documents || 0;
            document.getElementById('total-invoices').textContent = summary.by_type?.invoice || 0;
            document.getElementById('total-receipts').textContent = summary.by_type?.receipt || 0;
            const total = (summary.total_amounts?.invoices || 0) + (summary.total_amounts?.receipts || 0);
            document.getElementById('total-amount').textContent = Math.round(total) + ' zł';
        }

        function addDocument(doc) {
            const existingIdx = allDocs.findIndex(d => d.id === doc.id);
            if (existingIdx >= 0) {
                allDocs[existingIdx] = {...allDocs[existingIdx], ...doc};
            } else {
                allDocs.unshift(doc);
            }
            renderDocsTable();
            updateStats();
        }
        
        function addPendingDocument(doc) {
            addDocument({
                ...doc,
                pending: true,
                type: doc.doc_type || doc.type || 'dokument',
                date: new Date().toLocaleTimeString('pl-PL', {hour:'2-digit', minute:'2-digit'}),
            });
        }
        
        function renderDocsTable() {
            const tbody = document.getElementById('docs-table-body');
            const filtered = getFilteredDocs();
            
            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#888;padding:40px;">Brak dokumentów</td></tr>';
                return;
            }
            
            filtered.sort((a, b) => {
                let va = a[sortField] || '';
                let vb = b[sortField] || '';
                if (sortField === 'amount') {
                    va = parseFloat(va) || 0;
                    vb = parseFloat(vb) || 0;
                }
                return va > vb ? sortDir : va < vb ? -sortDir : 0;
            });
            
            tbody.innerHTML = filtered.map(doc => {
                const isPending = doc.pending === true;
                const typeClass = doc.type === 'invoice' ? 'badge-invoice' : doc.type === 'receipt' ? 'badge-receipt' : doc.type === 'letter' ? 'badge-letter' : 'badge-other';
                const typeName = doc.type === 'invoice' ? 'Faktura' : doc.type === 'receipt' ? 'Paragon' : doc.type === 'paragon' ? 'Paragon' : doc.type === 'faktura' ? 'Faktura' : doc.type || 'Dokument';
                const lang = doc.lang || detectLang(doc.ocr_text);
                const ocrPreview = doc.ocr_text ? doc.ocr_text.substring(0, 50) + '...' : '-';
                const docIdStr = typeof doc.id === 'string' ? `'${doc.id}'` : doc.id;
                
                return `<tr class="${isPending ? 'pending' : ''}" data-id="${doc.id}">
                    <td>${doc.thumbnail ? `<img src="data:image/jpeg;base64,${doc.thumbnail}" class="thumb" onclick="openDocModal(${docIdStr})">` : `<span style="cursor:pointer;font-size:1.5rem;" onclick="openDocModal(${docIdStr})">📄</span>`}</td>
                    <td><span class="badge ${typeClass}">${typeName}</span>${isPending ? ' ⏳' : ''}</td>
                    <td>${doc.date || '-'}</td>
                    <td>${doc.amount ? doc.amount + ' zł' : '-'}</td>
                    <td>${doc.nip || doc.id || '-'}</td>
                    <td>${lang ? `<span class="badge">${lang.toUpperCase()}</span>` : '-'}</td>
                    <td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer;" title="${doc.ocr_text || ''}" onclick="openDocModal(${docIdStr})">${ocrPreview}</td>
                    <td>
                        ${isPending ? `<button onclick="confirmDoc(${docIdStr})" style="background:#22c55e;color:white;border:none;padding:3px 8px;border-radius:4px;cursor:pointer;margin-right:4px;">✓</button>` : ''}
                        <button onclick="removeDoc(${docIdStr}, ${isPending})" style="background:#ef4444;color:white;border:none;padding:3px 8px;border-radius:4px;cursor:pointer;">✗</button>
                    </td>
                </tr>`;
            }).join('');
        }
        
        function getFilteredDocs() {
            const typeFilter = document.getElementById('filter-type').value;
            const langFilter = document.getElementById('filter-lang').value;
            const statusFilter = document.getElementById('filter-status').value;
            const search = document.getElementById('filter-search').value.toLowerCase();
            
            return allDocs.filter(doc => {
                if (typeFilter && doc.type !== typeFilter && doc.type !== (typeFilter === 'receipt' ? 'paragon' : typeFilter === 'invoice' ? 'faktura' : typeFilter)) return false;
                if (langFilter && (doc.lang || detectLang(doc.ocr_text)) !== langFilter) return false;
                if (statusFilter === 'pending' && !doc.pending) return false;
                if (statusFilter === 'saved' && doc.pending) return false;
                if (search && !JSON.stringify(doc).toLowerCase().includes(search)) return false;
                return true;
            });
        }
        
        function detectLang(text) {
            if (!text) return null;
            const t = text.toLowerCase();
            if (t.includes('faktura') || t.includes('paragon') || t.includes('nip') || t.includes('zł')) return 'pl';
            if (t.includes('invoice') || t.includes('receipt') || t.includes('total')) return 'en';
            if (t.includes('rechnung') || t.includes('quittung') || t.includes('€')) return 'de';
            return null;
        }
        
        function sortDocs(field) {
            if (sortField === field) sortDir *= -1;
            else { sortField = field; sortDir = -1; }
            renderDocsTable();
        }
        
        function filterDocs() {
            renderDocsTable();
        }
        
        function confirmDoc(docId) {
            ws.send(JSON.stringify({action: 'confirm_document', id: docId}));
            const doc = allDocs.find(d => d.id === docId);
            if (doc) { doc.pending = false; }
            renderDocsTable();
            updateStats();
            log('✅ Zapisano dokument', 'success');
        }
        
        function removeDoc(docId, isPending) {
            if (isPending) {
                ws.send(JSON.stringify({action: 'reject_document', id: docId}));
            }
            allDocs = allDocs.filter(d => d.id !== docId);
            renderDocsTable();
            updateStats();
        }
        
        function updateStats() {
            const pending = allDocs.filter(d => d.pending).length;
            const invoices = allDocs.filter(d => d.type === 'invoice' || d.type === 'faktura').length;
            const receipts = allDocs.filter(d => d.type === 'receipt' || d.type === 'paragon').length;
            const totalAmount = allDocs.reduce((sum, d) => sum + (parseFloat(d.amount) || 0), 0);
            
            document.getElementById('total-docs').textContent = allDocs.length;
            document.getElementById('total-invoices').textContent = invoices;
            document.getElementById('total-receipts').textContent = receipts;
            document.getElementById('total-amount').textContent = totalAmount.toFixed(0) + ' zł';
            document.getElementById('pending-count-stat').textContent = pending;
        }

        function updateStatus(status) {
            const dot = document.getElementById('status-dot');
            const text = document.getElementById('status-text');

            dot.className = 'status-dot';
            if (status === 'active') {
                text.textContent = 'Skanowanie aktywne';
            } else if (status === 'paused') {
                dot.classList.add('paused');
                text.textContent = 'Wstrzymane';
            } else if (status === 'error') {
                dot.classList.add('error');
                text.textContent = 'Błąd połączenia';
            }
        }

        function toggleScanning() {
            scanning = !scanning;
            ws.send(JSON.stringify({ action: 'toggle', scanning: scanning }));

            const icon = document.getElementById('scan-btn-icon');
            if (scanning) {
                icon.textContent = '⏸️';
                updateStatus('active');
            } else {
                icon.textContent = '▶️';
                updateStatus('paused');
            }
        }

        function captureNow() {
            ws.send(JSON.stringify({ action: 'capture' }));
            log('Wymuszono skan...', 'info');
        }

        function analyzeDeep() {
            log('🔬 Głęboka analiza OCR+LLM...', 'info');
            ws.send(JSON.stringify({ action: 'analyze_deep' }));
        }

        function exportCSV() {
            window.open('/export/csv', '_blank');
            log('Eksportowanie CSV...', 'info');
        }

        function log(message, level = 'info') {
            const content = document.getElementById('log-content');
            if (!content) return;
            const time = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = `log-entry ${level}`;
            entry.textContent = `[${time}] ${message}`;
            content.appendChild(entry);
            content.scrollTop = content.scrollHeight;
        }

        function clearLog() {
            const content = document.getElementById('log-content');
            if (content) content.innerHTML = '';
        }

        // Modal functions
        let currentModalDocId = null;
        
        function openDocModal(docId) {
            const doc = allDocs.find(d => d.id === docId || d.id === String(docId));
            if (!doc) {
                log('Nie znaleziono dokumentu: ' + docId, 'error');
                return;
            }
            
            currentModalDocId = docId;
            
            // Set image - prefer full image over thumbnail
            const imgEl = document.getElementById('doc-modal-img');
            if (doc.image) {
                imgEl.src = 'data:image/jpeg;base64,' + doc.image;
                imgEl.style.display = 'block';
            } else if (doc.thumbnail) {
                imgEl.src = 'data:image/jpeg;base64,' + doc.thumbnail;
                imgEl.style.display = 'block';
            } else {
                imgEl.style.display = 'none';
            }
            
            // Set details
            document.getElementById('modal-id').textContent = doc.id || '-';
            document.getElementById('modal-type').textContent = doc.type || '-';
            document.getElementById('modal-date').textContent = doc.date || '-';
            document.getElementById('modal-amount').textContent = doc.amount ? doc.amount + ' zł' : '-';
            document.getElementById('modal-nip').textContent = doc.nip || '-';
            document.getElementById('modal-lang').textContent = (doc.lang || detectLang(doc.ocr_text) || '-').toUpperCase();
            document.getElementById('modal-confidence').textContent = doc.confidence ? Math.round(doc.confidence * 100) + '%' : '-';
            document.getElementById('modal-status').textContent = doc.pending ? '⏳ Oczekuje' : '✅ Zapisany';
            document.getElementById('modal-ocr').textContent = doc.ocr_text || 'Brak danych OCR';
            
            // Show/hide confirm button
            document.getElementById('modal-confirm-btn').style.display = doc.pending ? 'block' : 'none';
            
            // Show modal
            document.getElementById('doc-modal').classList.add('active');
        }
        
        function closeDocModal() {
            document.getElementById('doc-modal').classList.remove('active');
            currentModalDocId = null;
        }
        
        function confirmFromModal() {
            if (currentModalDocId) {
                confirmDoc(currentModalDocId);
                document.getElementById('modal-status').textContent = '✅ Zapisany';
                document.getElementById('modal-confirm-btn').style.display = 'none';
            }
        }
        
        function removeFromModal() {
            if (currentModalDocId) {
                const doc = allDocs.find(d => d.id === currentModalDocId);
                removeDoc(currentModalDocId, doc?.pending || false);
                closeDocModal();
            }
        }
        
        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeDocModal();
        });

        // Start
        connect();
'''
