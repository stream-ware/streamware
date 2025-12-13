"""
Duplicate Mixin Module

Duplicate detection and quality selection methods for AccountingWebService.
"""

import time
from typing import Tuple, Optional, List, Dict

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
    
    def _is_duplicate(self, image_bytes: bytes, doc_type: str) -> Tuple[bool, Optional[int]]:
        """Check if document is duplicate. Returns (is_dup, better_idx)."""
        now = time.time()
        
        # Clean old entries
        self.recent_documents = [
            d for d in self.recent_documents 
            if now - d["timestamp"] < self.duplicate_window_sec
        ]
        
        # Compute hash and quality
        new_hash = self._compute_image_hash(image_bytes)
        new_quality = self._compute_image_quality(image_bytes)
        
        # Check for similar documents
        for i, doc in enumerate(self.recent_documents):
            if doc["doc_type"] != doc_type:
                continue
            
            # Compare hashes (allow 10% difference for perceptual hash)
            if len(new_hash) == 64:  # Perceptual hash
                diff = sum(a != b for a, b in zip(new_hash, doc["hash"]))
                if diff <= 6:  # Similar images
                    if new_quality > doc["quality"]:
                        return True, i  # Duplicate, but new is better
                    else:
                        return True, None  # Duplicate, keep old
        
        # Not a duplicate - add to recent
        self.recent_documents.append({
            "hash": new_hash,
            "quality": new_quality,
            "doc_type": doc_type,
            "timestamp": now,
            "image_bytes": image_bytes,
        })
        
        return False, None
