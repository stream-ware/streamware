"""
Archive Mixin Module

Document archiving and deep analysis methods for AccountingWebService.
"""

import time
import json
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    cv2 = None
    np = None

from .document_classifier import get_classifier


class ArchiveMixin:
    """Mixin class providing archiving and analysis methods for AccountingWebService."""
    
    def _create_thumbnail(self, image_bytes: bytes, max_size: int = 120) -> Optional[bytes]:
        """Create a thumbnail from image bytes."""
        if not HAS_CV2 or not image_bytes:
            return None
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return None
            
            h, w = img.shape[:2]
            scale = max_size / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            thumb = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            _, jpeg = cv2.imencode('.jpg', thumb, [cv2.IMWRITE_JPEG_QUALITY, 60])
            return jpeg.tobytes()
        except Exception:
            return None

    def analyze_frame(self, image_bytes: bytes) -> Dict[str, Any]:
        """Analyze frame for document detection."""
        result = {
            "detected": False,
            "doc_type": None,
            "confidence": 0.0,
        }

        try:
            # Save to temp file for OCR
            temp_path = self.temp_dir / "current_frame.jpg"
            with open(temp_path, 'wb') as f:
                f.write(image_bytes)

            # Quick OCR to detect document
            text, confidence, _ = self.ocr_engine.extract_text(temp_path, lang="pol")

            if text and len(text) > 50:  # Minimum text length
                from .components.accounting import DocumentAnalyzer

                doc_type = DocumentAnalyzer.classify_document(text)

                if doc_type != "other" and confidence >= self.min_confidence:
                    result["detected"] = True
                    result["doc_type"] = doc_type
                    result["confidence"] = confidence
                    result["text"] = text[:200]  # Preview

        except Exception as e:
            print(f"Analysis error: {e}")

        return result

    async def archive_document(self, image_bytes: bytes, analysis: Dict):
        """Archive detected document."""
        try:
            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            doc_type = analysis.get("doc_type", "other")
            filename = f"{timestamp}_{doc_type}.jpg"
            file_path = self.temp_dir / filename

            with open(file_path, 'wb') as f:
                f.write(image_bytes)

            # Process document
            doc_info = self.scanner.process_document(file_path, auto_crop=True)

            # Notify clients
            await self.broadcast({
                "type": "document",
                "document": {
                    "id": doc_info.id,
                    "type": doc_info.type,
                    "amount": doc_info.extracted_data.get("amounts", {}).get("gross") or
                             doc_info.extracted_data.get("total_amount"),
                    "date": doc_info.scan_date.strftime("%H:%M:%S"),
                }
            })

            # Send updated summary
            summary = self.manager.get_summary(self.project_name)
            await self.broadcast({
                "type": "summary",
                "summary": summary
            })

        except Exception as e:
            await self.broadcast({
                "type": "log",
                "message": f"Błąd archiwizacji: {e}",
                "level": "error"
            })

    async def _deep_analyze(self, ws):
        """Deep analysis with OCR + LLM (LLaVA-style vision analysis)."""
        t_start = time.time()
        
        await ws.send_str(json.dumps({
            "type": "log",
            "message": "🔬 Rozpoczynam głęboką analizę...",
            "level": "info"
        }))
        
        # Capture current frame
        image_bytes = self.capture()
        if not image_bytes:
            await ws.send_str(json.dumps({
                "type": "log",
                "message": "❌ Nie można pobrać klatki",
                "level": "error"
            }))
            return
        
        timing = {"capture": (time.time() - t_start) * 1000}
        
        # Step 1: OCR analysis
        t_ocr = time.time()
        temp_path = self.temp_dir / f"deep_analyze_{int(time.time() * 1000)}.jpg"
        with open(temp_path, 'wb') as f:
            f.write(image_bytes)
        
        ocr_text = ""
        ocr_confidence = 0.0
        try:
            ocr_text, ocr_confidence, _ = self.ocr_engine.extract_text(temp_path, lang="pol")
            timing["ocr"] = (time.time() - t_ocr) * 1000
            await ws.send_str(json.dumps({
                "type": "log",
                "message": f"📝 OCR: {len(ocr_text)} znaków ({timing['ocr']:.0f}ms)",
                "level": "info"
            }))
        except Exception as e:
            timing["ocr"] = (time.time() - t_ocr) * 1000
            await ws.send_str(json.dumps({
                "type": "log",
                "message": f"⚠️ OCR error: {e}",
                "level": "warning"
            }))
        
        # Step 2: LLM classification
        t_llm = time.time()
        classifier = get_classifier()
        llm_result = {}
        
        if len(ocr_text) > 50:
            # Use text-based classification
            llm_result = classifier.classify_document(ocr_text)
            timing["llm_text"] = (time.time() - t_llm) * 1000
            await ws.send_str(json.dumps({
                "type": "log",
                "message": f"🤖 LLM klasyfikacja: {llm_result.get('document_type', 'unknown')} ({timing['llm_text']:.0f}ms)",
                "level": "info"
            }))
        else:
            # Try vision LLM (LLaVA-style) if OCR failed
            await ws.send_str(json.dumps({
                "type": "log",
                "message": "👁️ OCR niewystarczający, próbuję analizy wizyjnej...",
                "level": "warning"
            }))
            llm_result = await self._vision_analyze(image_bytes, ws)
            timing["llm_vision"] = (time.time() - t_llm) * 1000
        
        timing["total"] = (time.time() - t_start) * 1000
        
        # Create document entry
        doc_type = llm_result.get("document_type", "other")
        confidence = llm_result.get("confidence", 0.5)
        
        thumbnail = self._create_thumbnail(image_bytes, max_size=120)
        doc_id = int(time.time() * 1000) % 100000
        
        # Log YAML summary
        yaml_log = self._format_yaml_log({
            "action": "deep_analyze",
            "timestamp": datetime.now().isoformat(),
            "timing_ms": timing,
            "ocr_length": len(ocr_text),
            "ocr_confidence": ocr_confidence,
            "llm_result": llm_result,
            "document_type": doc_type,
            "confidence": confidence,
        })
        print(yaml_log)
        
        # Create larger thumbnail for better visibility
        large_thumbnail = self._create_thumbnail(image_bytes, max_size=300)
        
        # Send result to browser - add as document (not pending) with full data
        await ws.send_str(json.dumps({
            "type": "document",
            "document": {
                "id": doc_id,
                "type": doc_type,
                "doc_type": doc_type,
                "confidence": confidence,
                "thumbnail": base64.b64encode(large_thumbnail).decode() if large_thumbnail else None,
                "image": base64.b64encode(image_bytes).decode() if image_bytes else None,
                "ocr_text": ocr_text[:2000] if ocr_text else "",
                "amount": llm_result.get("total_amount") or llm_result.get("gross_amount"),
                "nip": llm_result.get("nip") or llm_result.get("seller_nip"),
                "lang": llm_result.get("language"),
                "vendor": llm_result.get("vendor_name") or llm_result.get("vendor"),
                "summary": llm_result.get("summary") or llm_result.get("description"),
                "pending": False,
                "date": datetime.now().strftime("%H:%M:%S"),
                "timestamp": datetime.now().isoformat(),
            }
        }))
        
        # Store for confirmation
        self._pending_by_id = getattr(self, '_pending_by_id', {})
        self._pending_by_id[doc_id] = {
            "frame": image_bytes,
            "doc_type": doc_type,
            "detection": {"confidence": confidence},
            "ocr_text": ocr_text,
            "llm_result": llm_result,
            "timestamp": datetime.now().isoformat(),
        }
        
        await ws.send_str(json.dumps({
            "type": "log",
            "message": f"✅ Analiza zakończona: {doc_type} ({confidence:.0%}) w {timing['total']:.0f}ms",
            "level": "success"
        }))

    async def _vision_analyze(self, image_bytes: bytes, ws) -> dict:
        """Analyze image using vision LLM (LLaVA-style)."""
        try:
            import litellm
            
            # Encode image to base64
            img_b64 = base64.b64encode(image_bytes).decode()
            
            response = litellm.completion(
                model="gpt-4o-mini",  # or "ollama/llava" for local
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": """Analyze this image of a document. 
Respond in JSON:
{
    "document_type": "invoice|receipt|letter|form|id_document|other",
    "confidence": 0.0-1.0,
    "language": "pl|en|de|other",
    "description": "brief description",
    "visible_text": "key text visible",
    "total_amount": number or null,
    "currency": "PLN|EUR|USD|null"
}"""},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]
                }],
                temperature=0.1,
            )
            
            content = response.choices[0].message.content
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\{[^{}]+\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"document_type": "other", "confidence": 0.3, "description": content[:200]}
            
        except Exception as e:
            await ws.send_str(json.dumps({
                "type": "log",
                "message": f"⚠️ Vision LLM error: {e}",
                "level": "warning"
            }))
            return {"document_type": "other", "confidence": 0.2}

    def _format_yaml_log(self, data: dict) -> str:
        """Format data as YAML log output."""
        lines = ["---"]
        def _format(d, indent=0):
            result = []
            prefix = "  " * indent
            for k, v in d.items():
                if isinstance(v, dict):
                    result.append(f"{prefix}{k}:")
                    result.extend(_format(v, indent + 1))
                elif isinstance(v, list):
                    result.append(f"{prefix}{k}:")
                    for item in v:
                        if isinstance(item, dict):
                            result.append(f"{prefix}  -")
                            result.extend(_format(item, indent + 2))
                        else:
                            result.append(f"{prefix}  - {item}")
                else:
                    result.append(f"{prefix}{k}: {v}")
            return result
        lines.extend(_format(data))
        return "\n".join(lines)
