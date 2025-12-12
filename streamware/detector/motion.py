"""
Motion Detection Module

OpenCV-based motion detection and analysis.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import MotionLevel

logger = logging.getLogger(__name__)


# =============================================================================
# MOTION DETECTOR
# =============================================================================

class MotionDetector:
    """Motion detection using frame differencing."""
    
    def __init__(
        self,
        threshold: int = 25,
        min_area: int = 500,
        blur_size: int = 21,
    ):
        """
        Initialize motion detector.
        
        Args:
            threshold: Pixel difference threshold
            min_area: Minimum contour area to consider
            blur_size: Gaussian blur kernel size
        """
        self.threshold = threshold
        self.min_area = min_area
        self.blur_size = blur_size
        self._prev_frame = None
    
    def detect(
        self,
        frame_path: str,
        prev_frame_path: Optional[str] = None,
    ) -> Dict:
        """
        Detect motion between frames.
        
        Args:
            frame_path: Current frame path
            prev_frame_path: Previous frame path (optional, uses internal state)
        
        Returns:
            Dict with motion analysis results
        """
        try:
            import cv2
            import numpy as np
        except ImportError:
            return {"has_motion": False, "motion_percent": 0.0, "regions": []}
        
        # Load current frame
        frame = cv2.imread(str(frame_path))
        if frame is None:
            return {"has_motion": False, "motion_percent": 0.0, "regions": []}
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (self.blur_size, self.blur_size), 0)
        
        # Load or use previous frame
        if prev_frame_path:
            prev = cv2.imread(str(prev_frame_path))
            if prev is not None:
                prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
                prev_gray = cv2.GaussianBlur(prev_gray, (self.blur_size, self.blur_size), 0)
            else:
                prev_gray = self._prev_frame
        else:
            prev_gray = self._prev_frame
        
        # Store for next iteration
        self._prev_frame = gray
        
        if prev_gray is None:
            return {"has_motion": False, "motion_percent": 0.0, "regions": [], "first_frame": True}
        
        # Compute frame difference
        diff = cv2.absdiff(prev_gray, gray)
        _, thresh = cv2.threshold(diff, self.threshold, 255, cv2.THRESH_BINARY)
        
        # Calculate motion percentage
        total_pixels = thresh.shape[0] * thresh.shape[1]
        motion_pixels = np.count_nonzero(thresh)
        motion_percent = (motion_pixels / total_pixels) * 100
        
        # Find motion regions
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        regions = []
        height, width = frame.shape[:2]
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
            # Normalize coordinates
            regions.append({
                "x": x / width,
                "y": y / height,
                "w": w / width,
                "h": h / height,
                "area": area,
                "position": self._get_position(x + w/2, y + h/2, width, height),
            })
        
        has_motion = motion_percent > 0.5 and len(regions) > 0
        
        return {
            "has_motion": has_motion,
            "motion_percent": round(motion_percent, 2),
            "motion_level": MotionLevel.from_percent(motion_percent),
            "regions": regions,
            "region_count": len(regions),
        }
    
    def _get_position(self, x: float, y: float, width: int, height: int) -> str:
        """Get human-readable position from coordinates."""
        x_norm = x / width
        y_norm = y / height
        
        h_pos = "left" if x_norm < 0.33 else ("right" if x_norm > 0.66 else "center")
        v_pos = "top" if y_norm < 0.33 else ("bottom" if y_norm > 0.66 else "middle")
        
        return f"{v_pos}-{h_pos}"
    
    def reset(self):
        """Reset detector state."""
        self._prev_frame = None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def detect_motion(
    frame_path: str,
    prev_frame_path: Optional[str] = None,
    threshold: int = 25,
) -> Tuple[bool, float, List[Dict]]:
    """
    Quick motion detection between frames.
    
    Args:
        frame_path: Current frame path
        prev_frame_path: Previous frame path
        threshold: Pixel difference threshold
    
    Returns:
        Tuple of (has_motion, motion_percent, regions)
    """
    detector = MotionDetector(threshold=threshold)
    
    if prev_frame_path:
        # Prime with previous frame
        detector.detect(prev_frame_path)
    
    result = detector.detect(frame_path)
    
    return (
        result.get("has_motion", False),
        result.get("motion_percent", 0.0),
        result.get("regions", []),
    )


def motion_score(frame_path: str, prev_frame_path: str) -> float:
    """
    Calculate motion score between frames.
    
    Returns:
        Motion score 0-100
    """
    has_motion, percent, _ = detect_motion(frame_path, prev_frame_path)
    return percent if has_motion else 0.0
