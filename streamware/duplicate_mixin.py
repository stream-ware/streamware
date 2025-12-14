"""
Duplicate Mixin Module

Duplicate detection and quality selection methods for AccountingWebService.
"""

import time
from typing import Tuple, Optional, List, Dict, Any

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    cv2 = None
    np = None


class DuplicateMixin:
    """Mixin class providing duplicate detection methods for AccountingWebService."""
    
    def _compute_image_hash(self, image_bytes: bytes) -> str:
        """Compute perceptual hash for image similarity."""
        import hashlib
        if not HAS_CV2:
            return hashlib.md5(image_bytes).hexdigest()
        
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return hashlib.md5(image_bytes).hexdigest()
            
            # Resize to 8x8 and compute hash
            resized = cv2.resize(img, (8, 8), interpolation=cv2.INTER_AREA)
            mean = resized.mean()
            bits = (resized > mean).flatten()
            return ''.join(['1' if b else '0' for b in bits])
        except Exception:
            return hashlib.md5(image_bytes).hexdigest()

    def _hash_similarity(self, h1: str, h2: str) -> float:
        if not h1 or not h2:
            return 0.0
        if len(h1) == 64 and len(h2) == 64:
            diff = sum(a != b for a, b in zip(h1, h2))
            return max(0.0, 1.0 - (diff / 64.0))
        if len(h1) == 32 and len(h2) == 32:
            return 1.0 if h1 == h2 else 0.0
        return 0.0
    
    def _compute_image_quality(self, image_bytes: bytes) -> float:
        """Compute image quality score based on sharpness and contrast."""
        if not HAS_CV2:
            return len(image_bytes) / 1000000  # Fallback: file size
        
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return 0.0
            
            # Laplacian variance as sharpness metric
            laplacian = cv2.Laplacian(img, cv2.CV_64F)
            sharpness = laplacian.var()
            
            # Contrast (std of pixel values)
            contrast = img.std()
            
            # Combined score
            return sharpness * 0.01 + contrast * 0.1
        except Exception:
            return 0.0
    
    def _enqueue_duplicate_notification(self, payload: Dict[str, Any]) -> None:
        queue = getattr(self, "queued_broadcasts", None)
        if isinstance(queue, list):
            queue.append(payload)

    def _is_duplicate(self, image_bytes: bytes, doc_type: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        now = time.time()

        if not hasattr(self, "recent_documents") or self.recent_documents is None:
            self.recent_documents = []

        new_hash = self._compute_image_hash(image_bytes)
        new_quality = self._compute_image_quality(image_bytes)

        last_n = int(getattr(self, "duplicate_last_n", 3) or 3)
        immediate_threshold = float(getattr(self, "duplicate_immediate_similarity_threshold", 0.97) or 0.97)
        recent_threshold = float(getattr(self, "duplicate_similarity_threshold", 0.93) or 0.93)
        recent = self.recent_documents[-max(1, last_n):]

        if recent:
            last_doc = recent[-1]
            sim = self._hash_similarity(new_hash, last_doc.get("hash", ""))
            if sim >= immediate_threshold:
                replace = (not last_doc.get("archived_id")) and (new_quality > float(last_doc.get("quality", 0.0)))
                return True, {
                    "reason": "immediate",
                    "similarity": sim,
                    "matched": last_doc,
                    "new_quality": new_quality,
                    "matched_quality": float(last_doc.get("quality", 0.0)),
                    "replace": replace,
                    "doc_type": doc_type,
                    "timestamp": now,
                }

        best: Optional[Dict[str, Any]] = None
        for doc in reversed(recent[:-1] if len(recent) > 1 else []):
            sim = self._hash_similarity(new_hash, doc.get("hash", ""))
            if sim >= recent_threshold and (best is None or sim > float(best.get("similarity", 0.0))):
                replace = (not doc.get("archived_id")) and (new_quality > float(doc.get("quality", 0.0)))
                best = {
                    "reason": "recent",
                    "similarity": sim,
                    "matched": doc,
                    "new_quality": new_quality,
                    "matched_quality": float(doc.get("quality", 0.0)),
                    "replace": replace,
                    "doc_type": doc_type,
                    "timestamp": now,
                }
        if best is not None:
            return True, best

        self.recent_documents.append({
            "hash": new_hash,
            "quality": new_quality,
            "doc_type": doc_type,
            "timestamp": now,
            "image_bytes": image_bytes,
        })

        max_keep = int(getattr(self, "duplicate_history_max", max(10, last_n)) or max(10, last_n))
        if len(self.recent_documents) > max_keep:
            self.recent_documents = self.recent_documents[-max_keep:]

        return False, None
