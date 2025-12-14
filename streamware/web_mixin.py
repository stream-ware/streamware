"""
Web Mixin Module

Web request and WebSocket handlers for AccountingWebService.
"""

import json
import base64
from typing import Dict, Any, Optional

try:
    from aiohttp import web
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    web = None

from .web_templates import get_scanner_html_template


class WebMixin:
    """Mixin class providing web handlers for AccountingWebService."""
    
    async def broadcast(self, message: Dict):
        """Send message to all connected clients."""
        data = json.dumps(message, default=str)
        for ws in self.clients[:]:
            try:
                await ws.send_str(data)
            except Exception:
                self.clients.remove(ws)

    async def handle_websocket(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.clients.append(ws)

        # Send initial config
        await ws.send_str(json.dumps({
            "type": "config",
            "project": self.project_name
        }))

        # Send current summary
        summary = self.manager.get_summary(self.project_name)
        await ws.send_str(json.dumps({
            "type": "summary",
            "summary": summary
        }))

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self.handle_command(data, ws)
                elif msg.type == web.WSMsgType.ERROR:
                    break
        finally:
            self.clients.remove(ws)

        return ws

    async def handle_command(self, data: Dict, ws):
        """Handle commands from client."""
        action = data.get("action")

        if action == "toggle":
            self.scanning = data.get("scanning", True)

        elif action == "capture":
            # Force immediate capture
            image_bytes = self.capture()
            if image_bytes:
                is_dup, dup_meta = self._is_duplicate(image_bytes, "manual_capture")
                if is_dup:
                    sim = float((dup_meta or {}).get("similarity", 0.0))
                    matched = (dup_meta or {}).get("matched")
                    matched_id = None
                    if isinstance(matched, dict):
                        matched_id = matched.get("archived_id")
                    await self.broadcast({
                        "type": "duplicate",
                        "message": f"🔄 Duplikat ({sim:.0%}) - pominięto skan",
                        "similarity": sim,
                        "reason": (dup_meta or {}).get("reason"),
                        "matched_id": matched_id,
                    })
                    return
                analysis = self.analyze_frame(image_bytes)
                if analysis["detected"]:
                    await self.archive_document(image_bytes, analysis)
                else:
                    await ws.send_str(json.dumps({
                        "type": "log",
                        "message": "Nie wykryto dokumentu na ekranie",
                        "level": "warning"
                    }))
        
        elif action == "analyze_deep":
            # Deep analysis with OCR + LLM
            await self._deep_analyze(ws)

        elif action == "set_interval":
            self.interval = max(0.5, min(10, data.get("interval", 1.0)))

        elif action == "set_confidence":
            self.min_confidence = max(0.1, min(0.95, data.get("confidence", 0.5)))

        elif action == "set_auto_archive":
            self.auto_archive = data.get("enabled", True)
        
        elif action == "get_pending":
            # Send list of pending documents for confirmation
            pending_list = []
            for i, doc in enumerate(self.pending_documents[-10:]):  # Last 10
                pending_list.append({
                    "id": i,
                    "doc_type": doc["doc_type"],
                    "confidence": doc["detection"]["confidence"],
                    "timestamp": doc["timestamp"],
                    "image": base64.b64encode(doc["frame"]).decode(),
                })
            await ws.send_str(json.dumps({
                "type": "pending_documents",
                "documents": pending_list,
                "count": len(self.pending_documents)
            }))
        
        elif action == "confirm_document":
            # Confirm and save a pending document
            doc_id = data.get("id", 0)
            pending_by_id = getattr(self, '_pending_by_id', {})
            if doc_id in pending_by_id:
                doc = pending_by_id.pop(doc_id)
                analysis = doc["detection"]
                analysis["detected"] = True
                analysis["doc_type"] = doc["doc_type"]
                await self.archive_document(doc["frame"], analysis)
                await ws.send_str(json.dumps({
                    "type": "log",
                    "message": f"✅ Zapisano: {doc['doc_type']}",
                    "level": "success"
                }))
        
        elif action == "reject_document":
            # Reject a pending document
            doc_id = data.get("id", 0)
            pending_by_id = getattr(self, '_pending_by_id', {})
            if doc_id in pending_by_id:
                doc = pending_by_id.pop(doc_id)
                await ws.send_str(json.dumps({
                    "type": "log",
                    "message": f"❌ Odrzucono: {doc['doc_type']}",
                    "level": "warning"
                }))
        
        elif action == "confirm_all":
            # Confirm all pending documents
            count = len(self.pending_documents)
            for doc in self.pending_documents:
                analysis = doc["detection"]
                analysis["detected"] = True
                await self.archive_document(doc["frame"], analysis)
            self.pending_documents.clear()
            await ws.send_str(json.dumps({
                "type": "log",
                "message": f"✅ Potwierdzono {count} dokumentów",
                "level": "success"
            }))
        
        elif action == "reject_all":
            # Reject all pending documents
            count = len(self.pending_documents)
            self.pending_documents.clear()
            await ws.send_str(json.dumps({
                "type": "log",
                "message": f"❌ Odrzucono {count} dokumentów",
                "level": "warning"
            }))
        
        elif action == "get_documents":
            # Get list of archived documents with OCR data
            docs = self.manager.get_documents(self.project_name)
            await ws.send_str(json.dumps({
                "type": "documents_list",
                "documents": docs[:50]  # Last 50
            }))
        
        elif action == "get_ocr_data":
            # Get OCR data for specific document
            doc_id = data.get("doc_id")
            doc = self.manager.get_document(self.project_name, doc_id)
            if doc:
                await ws.send_str(json.dumps({
                    "type": "document_detail",
                    "document": doc
                }))
        
        elif action == "get_settings":
            # Send current scanner settings
            await ws.send_str(json.dumps({
                "type": "settings",
                "fps": 1.0 / self.interval if self.interval > 0 else 2,
                "min_confidence": self.min_confidence,
                "confirm_threshold": self.confirm_threshold,
                "auto_save_threshold": self.auto_save_threshold,
                "cooldown_sec": self.cooldown_sec,
                "use_llm_confirm": self.use_llm_confirm,
                "auto_archive": self.auto_archive,
            }))

    async def handle_index(self, request):
        """Serve main HTML page."""
        return web.Response(text=get_scanner_html_template(), content_type='text/html')

    async def handle_export_csv(self, request):
        """Export documents to CSV."""
        csv_path = self.manager.export_to_csv(self.project_name)

        with open(csv_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return web.Response(
            text=content,
            content_type='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{self.project_name}.csv"'
            }
        )
