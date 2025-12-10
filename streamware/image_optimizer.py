"""
Image Optimizer - Reduce image size for faster LLM processing

Optimizations:
- Resize to optimal dimensions for vision LLMs
- JPEG compression with quality tuning
- Posterization for simpler images (optional)
- Grayscale conversion for non-color tasks (optional)

Usage:
    from streamware.image_optimizer import optimize_for_llm
    
    optimized_path = optimize_for_llm(frame_path, max_size=512)
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

from .config import config

logger = logging.getLogger(__name__)


def optimize_for_llm(
    image_path: Path,
    max_size: int = 512,
    quality: int = 75,
    output_path: Path = None,
    keep_aspect: bool = True,
) -> Path:
    """Optimize image for LLM vision processing.
    
    Args:
        image_path: Source image path
        max_size: Maximum dimension (width or height)
        quality: JPEG quality (1-100)
        output_path: Output path (default: same as input with _opt suffix)
        keep_aspect: Maintain aspect ratio
        
    Returns:
        Path to optimized image
    """
    try:
        from PIL import Image
        
        img = Image.open(image_path)
        original_size = img.size
        
        # Calculate new size
        width, height = img.size
        if width > max_size or height > max_size:
            if keep_aspect:
                ratio = min(max_size / width, max_size / height)
                new_size = (int(width * ratio), int(height * ratio))
            else:
                new_size = (max_size, max_size)
            
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Output path
        if output_path is None:
            # Use RAM disk for optimized images
            ramdisk = Path(config.get("SQ_RAMDISK_PATH", "/dev/shm/streamware"))
            ramdisk.mkdir(parents=True, exist_ok=True)
            output_path = ramdisk / f"{image_path.stem}_opt.jpg"
        
        # Save with compression
        img.convert("RGB").save(output_path, "JPEG", quality=quality, optimize=True)
        
        # Log compression stats
        original_kb = image_path.stat().st_size / 1024
        optimized_kb = output_path.stat().st_size / 1024
        reduction = (1 - optimized_kb / original_kb) * 100
        
        logger.debug(f"Image optimized: {original_size} → {img.size}, {original_kb:.0f}KB → {optimized_kb:.0f}KB ({reduction:.0f}% reduction)")
        
        return output_path
        
    except ImportError:
        logger.warning("PIL not available, returning original image")
        return image_path
    except Exception as e:
        logger.debug(f"Image optimization failed: {e}")
        return image_path


def get_optimal_size_for_model(model_name: str) -> int:
    """Get optimal image size for a specific vision model."""
    # Model-specific optimal sizes
    optimal_sizes = {
        "llava:7b": 512,
        "llava:13b": 768,
        "llava:34b": 1024,
        "moondream": 384,
        "bakllava": 512,
        "gpt-4o": 1024,
        "gpt-4-vision": 1024,
        "claude-3": 1024,
    }
    
    # Check for partial matches
    model_lower = model_name.lower()
    for name, size in optimal_sizes.items():
        if name in model_lower:
            return size
    
    # Default
    return 512


class DescriptionCache:
    """Cache for similar frame descriptions to avoid redundant LLM calls.
    
    NOTE: In track mode, cache should be disabled or very short-lived
    because we need to detect movement changes, not just static scenes.
    """
    
    def __init__(self, max_size: int = 100, similarity_threshold: float = 0.95, ttl_seconds: float = 5.0):
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds  # Cache entries expire after this time
        self._cache: dict = {}  # hash -> (description, timestamp)
        self._image_hashes: list = []  # LRU order
        self._enabled = True  # Can be disabled for track mode
    
    def _compute_hash(self, image_path: Path) -> str:
        """Compute perceptual hash of image."""
        try:
            from PIL import Image
            import hashlib
            
            # Simple hash based on downscaled grayscale
            img = Image.open(image_path).convert("L").resize((16, 16))
            pixels = list(img.getdata())
            
            # Average hash
            avg = sum(pixels) / len(pixels)
            bits = "".join("1" if p > avg else "0" for p in pixels)
            
            return hashlib.md5(bits.encode()).hexdigest()[:16]
            
        except Exception:
            return None
    
    def get(self, image_path: Path) -> Optional[str]:
        """Get cached description if similar image exists and not expired."""
        if not self._enabled:
            return None
        
        img_hash = self._compute_hash(image_path)
        if img_hash and img_hash in self._cache:
            desc, timestamp = self._cache[img_hash]
            
            # Check TTL
            import time
            if time.time() - timestamp > self.ttl_seconds:
                # Expired, remove from cache
                del self._cache[img_hash]
                if img_hash in self._image_hashes:
                    self._image_hashes.remove(img_hash)
                logger.debug(f"Cache expired for {image_path.name}")
                return None
            
            logger.debug(f"Cache hit for {image_path.name}")
            return desc
        return None
    
    def disable(self):
        """Disable cache (for track mode)."""
        self._enabled = False
        self.clear()
    
    def enable(self):
        """Enable cache."""
        self._enabled = True
    
    def put(self, image_path: Path, description: str):
        """Cache description for image."""
        img_hash = self._compute_hash(image_path)
        if not img_hash:
            return
        
        # Evict old entries if cache full
        while len(self._image_hashes) >= self.max_size:
            old_hash = self._image_hashes.pop(0)
            self._cache.pop(old_hash, None)
        
        self._cache[img_hash] = (description, __import__("time").time())
        self._image_hashes.append(img_hash)
    
    def clear(self):
        """Clear cache."""
        self._cache.clear()
        self._image_hashes.clear()
    
    @property
    def size(self) -> int:
        return len(self._cache)
    
    @property
    def hit_rate(self) -> float:
        """Placeholder for hit rate tracking."""
        return 0.0


# Global cache instance
_description_cache: Optional[DescriptionCache] = None


def get_description_cache() -> DescriptionCache:
    """Get or create description cache."""
    global _description_cache
    if _description_cache is None:
        _description_cache = DescriptionCache()
    return _description_cache
