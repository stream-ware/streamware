"""
Keyframe Extractor for Streamware

Extracts important frames from video stream based on:
- Visual changes (histogram comparison)
- Motion detection
- Object detection changes

This reduces LLM calls by only analyzing frames that matter.
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class KeyframeInfo:
    """Information about a keyframe."""
    path: Path
    timestamp: float
    reason: str  # 'scene_change', 'motion', 'detection', 'periodic'
    similarity: float  # 0-1, lower = more different
    frame_num: int


class KeyframeExtractor:
    """
    Extracts keyframes from video stream.
    
    Only keyframes are sent to LLM for analysis, significantly reducing
    processing time for static scenes.
    """
    
    def __init__(
        self,
        scene_threshold: float = 0.15,  # Histogram difference threshold
        motion_threshold: float = 2.0,   # Minimum motion percent
        min_interval: float = 1.0,       # Minimum seconds between keyframes
        max_interval: float = 10.0,      # Maximum seconds without keyframe
    ):
        self.scene_threshold = scene_threshold
        self.motion_threshold = motion_threshold
        self.min_interval = min_interval
        self.max_interval = max_interval
        
        self._last_histogram = None
        self._last_keyframe_time = 0
        self._last_keyframe_path = None
        self._frame_count = 0
        self._keyframe_count = 0
    
    def is_keyframe(
        self,
        frame_path: Path,
        motion_percent: float = 0,
        has_detection: bool = False,
    ) -> Tuple[bool, str]:
        """
        Determine if frame is a keyframe.
        
        Args:
            frame_path: Path to frame image
            motion_percent: Percentage of frame with motion
            has_detection: Whether YOLO detected something
            
        Returns:
            (is_keyframe, reason) tuple
        """
        self._frame_count += 1
        now = time.time()
        time_since_last = now - self._last_keyframe_time
        
        # Always keyframe if max interval exceeded
        if time_since_last > self.max_interval:
            return self._mark_keyframe(frame_path, now, "periodic")
        
        # Skip if too soon
        if time_since_last < self.min_interval:
            return False, "too_soon"
        
        # Keyframe if significant motion
        if motion_percent > self.motion_threshold:
            return self._mark_keyframe(frame_path, now, "motion")
        
        # Keyframe if new detection
        if has_detection:
            return self._mark_keyframe(frame_path, now, "detection")
        
        # Check visual similarity
        try:
            similarity = self._compute_similarity(frame_path)
            if similarity < (1 - self.scene_threshold):
                return self._mark_keyframe(frame_path, now, f"scene_change_{similarity:.2f}")
        except Exception as e:
            logger.debug(f"Similarity check failed: {e}")
        
        return False, "similar"
    
    def _mark_keyframe(self, frame_path: Path, timestamp: float, reason: str) -> Tuple[bool, str]:
        """Mark frame as keyframe and update state."""
        self._last_keyframe_time = timestamp
        self._last_keyframe_path = frame_path
        self._keyframe_count += 1
        return True, reason
    
    def _compute_similarity(self, frame_path: Path) -> float:
        """
        Compute visual similarity to last keyframe.
        
        Uses histogram comparison for speed.
        Returns 0-1 where 1 is identical.
        """
        try:
            import cv2
        except ImportError:
            return 0.5  # Assume different if cv2 not available
        
        frame = cv2.imread(str(frame_path))
        if frame is None:
            return 0.5
        
        # Compute histogram
        hist = cv2.calcHist(
            [frame], [0, 1, 2], None,
            [8, 8, 8], [0, 256, 0, 256, 0, 256]
        )
        hist = cv2.normalize(hist, hist).flatten()
        
        if self._last_histogram is None:
            self._last_histogram = hist
            return 0  # First frame is always different
        
        # Compare using Bhattacharyya distance
        similarity = 1 - cv2.compareHist(self._last_histogram, hist, cv2.HISTCMP_BHATTACHARYYA)
        
        # Update histogram for next comparison
        self._last_histogram = hist
        
        return max(0, min(1, similarity))
    
    def get_stats(self) -> dict:
        """Get extraction statistics."""
        return {
            "total_frames": self._frame_count,
            "keyframes": self._keyframe_count,
            "skip_rate": 1 - (self._keyframe_count / max(1, self._frame_count)),
        }
    
    def reset(self):
        """Reset extractor state."""
        self._last_histogram = None
        self._last_keyframe_time = 0
        self._last_keyframe_path = None
        self._frame_count = 0
        self._keyframe_count = 0


class BatchFrameBuffer:
    """
    Buffer for batch processing multiple frames.
    
    Collects frames and creates a grid image for batch LLM analysis.
    """
    
    def __init__(self, batch_size: int = 3, grid_cols: int = 3):
        self.batch_size = batch_size
        self.grid_cols = grid_cols
        self.frames: List[Path] = []
        self.timestamps: List[float] = []
    
    def add(self, frame_path: Path) -> bool:
        """
        Add frame to buffer.
        
        Returns True if batch is ready for processing.
        """
        self.frames.append(frame_path)
        self.timestamps.append(time.time())
        return len(self.frames) >= self.batch_size
    
    def is_ready(self) -> bool:
        """Check if batch is ready."""
        return len(self.frames) >= self.batch_size
    
    def create_grid(self, target_size: int = 512) -> Optional[Path]:
        """
        Create grid image from buffered frames.
        
        Returns path to grid image.
        """
        if not self.frames:
            return None
        
        try:
            import cv2
            import tempfile
        except ImportError:
            return self.frames[-1]  # Return last frame if cv2 not available
        
        # Load frames
        images = []
        for fp in self.frames[:self.batch_size]:
            img = cv2.imread(str(fp))
            if img is not None:
                images.append(img)
        
        if not images:
            return None
        
        # Calculate grid dimensions
        n = len(images)
        cols = min(n, self.grid_cols)
        rows = (n + cols - 1) // cols
        
        # Resize images to fit grid
        cell_size = target_size // cols
        resized = [cv2.resize(img, (cell_size, cell_size)) for img in images]
        
        # Pad to fill grid
        while len(resized) < rows * cols:
            resized.append(np.zeros_like(resized[0]))
        
        # Create grid
        grid_rows = []
        for r in range(rows):
            row_images = resized[r * cols:(r + 1) * cols]
            grid_rows.append(np.hstack(row_images))
        grid = np.vstack(grid_rows)
        
        # Save grid
        grid_path = Path(tempfile.mktemp(suffix='.jpg'))
        cv2.imwrite(str(grid_path), grid, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        return grid_path
    
    def clear(self):
        """Clear buffer."""
        self.frames.clear()
        self.timestamps.clear()
    
    def get_time_span(self) -> float:
        """Get time span of buffered frames."""
        if len(self.timestamps) < 2:
            return 0
        return self.timestamps[-1] - self.timestamps[0]


class SceneClassifier:
    """
    Classifies scene activity level for adaptive processing.
    """
    
    PROFILES = {
        'static': {
            'interval': 10.0,
            'model': 'moondream',
            'skip_guarder': True,
        },
        'low_activity': {
            'interval': 5.0,
            'model': 'moondream',
            'skip_guarder': False,
        },
        'normal': {
            'interval': 3.0,
            'model': 'llava:7b',
            'skip_guarder': False,
        },
        'high_activity': {
            'interval': 1.0,
            'model': 'llava:7b',
            'skip_guarder': False,
        },
        'emergency': {
            'interval': 0.5,
            'model': 'llava:13b',
            'skip_guarder': False,
        },
    }
    
    def __init__(self):
        self._history: List[str] = []
        self._max_history = 10
    
    def classify(
        self,
        motion_percent: float,
        detection_count: int,
        detection_types: List[str] = None,
    ) -> str:
        """
        Classify current scene.
        
        Args:
            motion_percent: Percentage of frame with motion
            detection_count: Number of objects detected
            detection_types: Types of detected objects
            
        Returns:
            Scene classification string
        """
        detection_types = detection_types or []
        
        # Emergency: multiple people or high-priority detection
        emergency_types = ['fire', 'weapon', 'fall', 'accident']
        if any(t in detection_types for t in emergency_types):
            scene = 'emergency'
        elif detection_count > 3:
            scene = 'emergency'
        # High activity: lots of motion or multiple detections
        elif motion_percent > 30 or detection_count > 1:
            scene = 'high_activity'
        # Normal: some motion or single detection
        elif motion_percent > 5 or detection_count > 0:
            scene = 'normal'
        # Low activity: minimal changes
        elif motion_percent > 1:
            scene = 'low_activity'
        else:
            scene = 'static'
        
        # Smooth transitions using history
        self._history.append(scene)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        
        # Return most common recent classification
        return max(set(self._history), key=self._history.count)
    
    def get_profile(self, scene_type: str = None) -> dict:
        """Get processing profile for scene type."""
        if scene_type is None:
            scene_type = self._history[-1] if self._history else 'normal'
        return self.PROFILES.get(scene_type, self.PROFILES['normal'])
    
    def reset(self):
        """Reset classifier state."""
        self._history.clear()


# Convenience functions
_keyframe_extractor: Optional[KeyframeExtractor] = None
_scene_classifier: Optional[SceneClassifier] = None


def get_keyframe_extractor(**kwargs) -> KeyframeExtractor:
    """Get or create keyframe extractor."""
    global _keyframe_extractor
    if _keyframe_extractor is None:
        _keyframe_extractor = KeyframeExtractor(**kwargs)
    return _keyframe_extractor


def get_scene_classifier() -> SceneClassifier:
    """Get or create scene classifier."""
    global _scene_classifier
    if _scene_classifier is None:
        _scene_classifier = SceneClassifier()
    return _scene_classifier
