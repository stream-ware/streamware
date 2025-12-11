"""
Frame Diff DSL - Lightweight metadata language for frame-to-frame changes

This module provides:
1. Pure algorithmic motion/edge detection (no LLM)
2. DSL for describing detected changes
3. LLM only for final object classification (optional)
4. Real-time matrix operations via OpenCV

Key concepts:
- FrameDelta: Differences between consecutive frames
- MotionBlob: Detected moving region
- EdgeContour: Detected edges of moving object
- MetaEvent: High-level interpretation of changes

DSL Output Format:
------------------
FRAME 1 @ 00:00:01.234
  DELTA motion_pct=5.2% regions=2
  BLOB id=1 pos=(0.3,0.4) size=(0.1,0.15) velocity=(0.02,0.01) 
  BLOB id=2 pos=(0.7,0.2) size=(0.05,0.08) velocity=(-0.01,0.0)
  EDGE blob=1 points=24 area=1240px complexity=0.7
  EVENT type=ENTER direction=LEFT object=UNKNOWN
  
FRAME 2 @ 00:00:02.456
  DELTA motion_pct=3.1% regions=2
  BLOB id=1 pos=(0.32,0.41) size=(0.1,0.15) velocity=(0.02,0.01) 
  TRACK blob=1 frames=2 distance=0.03 speed=0.02
  CLASSIFY blob=1 -> person (LLM confidence=0.92)
"""

import logging
import time
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from enum import Enum
import numpy as np

try:  # Optional config integration
    from .config import config as _sq_config
except Exception:  # pragma: no cover - keep analyzer usable without full config
    _sq_config = None

logger = logging.getLogger(__name__)


# ============================================================================
# Core Data Structures
# ============================================================================

class EventType(Enum):
    """Types of motion events."""
    ENTER = "ENTER"      # Object entered frame
    EXIT = "EXIT"        # Object exited frame
    MOVE = "MOVE"        # Object is moving
    STOP = "STOP"        # Object stopped
    APPEAR = "APPEAR"    # Object appeared (not from edge)
    DISAPPEAR = "DISAPPEAR"  # Object disappeared
    SPLIT = "SPLIT"      # One blob split into multiple
    MERGE = "MERGE"      # Multiple blobs merged


class Direction(Enum):
    """Movement directions."""
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    UP = "UP"
    DOWN = "DOWN"
    TOWARD = "TOWARD"    # Toward camera (getting bigger)
    AWAY = "AWAY"        # Away from camera (getting smaller)
    STATIC = "STATIC"


@dataclass
class Point2D:
    """2D point in normalized coordinates (0-1)."""
    x: float
    y: float
    
    def distance_to(self, other: 'Point2D') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def __sub__(self, other: 'Point2D') -> 'Point2D':
        return Point2D(self.x - other.x, self.y - other.y)
    
    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class MotionBlob:
    """Detected motion region."""
    id: int
    center: Point2D
    size: Point2D  # width, height normalized
    area_px: int   # area in pixels
    velocity: Point2D = field(default_factory=lambda: Point2D(0, 0))
    
    # Contour data
    contour_points: int = 0
    complexity: float = 0.0  # 0-1, how complex the shape is
    aspect_ratio: float = 1.0
    # Appearance descriptors (for matching in low-light / grayscale)
    # Hu moments in log-scale (7 values typically), robust to rotation/scale
    shape_descriptor: Tuple[float, ...] = field(default_factory=tuple)
    # Grayscale intensity statistics inside blob region
    intensity_mean: float = -1.0
    intensity_std: float = -1.0
    
    # Tracking
    age: int = 1  # frames since first seen
    last_seen: int = 0  # frame number
    
    # Classification (filled by LLM if needed)
    classification: str = "UNKNOWN"
    confidence: float = 0.0


@dataclass
class FrameDelta:
    """Differences between consecutive frames."""
    frame_num: int
    timestamp: float
    
    # Motion metrics
    motion_percent: float = 0.0
    changed_pixels: int = 0
    total_pixels: int = 0
    
    # Detected blobs
    blobs: List[MotionBlob] = field(default_factory=list)
    
    # Events
    events: List['MetaEvent'] = field(default_factory=list)
    
    # Raw data for visualization
    motion_mask: Optional[np.ndarray] = None
    edge_map: Optional[np.ndarray] = None
    
    # Frame path and background for thumbnails
    frame_path: Optional[str] = None
    background_base64: Optional[str] = None  # 128px thumbnail captured during analysis


@dataclass
class MetaEvent:
    """High-level event interpretation."""
    type: EventType
    blob_id: int
    direction: Direction = Direction.STATIC
    details: str = ""
    confidence: float = 1.0


@dataclass
class TrackInfo:
    """Tracking information for a blob."""
    blob_id: int
    total_frames: int
    total_distance: float
    avg_speed: float
    trajectory: List[Point2D] = field(default_factory=list)
    direction_history: List[Direction] = field(default_factory=list)


# ============================================================================
# Frame Analyzer - Pure OpenCV Operations
# ============================================================================

class FrameDiffAnalyzer:
    """
    Analyzes frame differences using pure OpenCV operations.
    No LLM calls - only matrix operations.
    """
    
    def __init__(
        self,
        motion_threshold: int = 20,  # Lowered from 25 for better sensitivity
        min_blob_area: int = 500,    # Higher default to ignore tiny flicker/noise
        max_blobs: int = 20,
        blur_size: int = 5,
        dilate_iterations: int = 2,
        # Filtering for truly moving objects
        min_velocity: float = 0.008,  # Lowered from 0.01 for more sensitive detection
        max_blob_size_ratio: float = 0.8,  # Raised from 0.7 to allow larger objects
        min_moving_frames: int = 1,  # Lowered from 2 for faster detection
        filter_static: bool = True,  # Filter out static objects (monitors, pictures)
        # Heuristic for global camera motion
        camera_motion_threshold: float = 40.0,  # % of pixels changed to treat as camera move
    ):
        # Allow config to override blob area / count and camera motion threshold
        if _sq_config is not None:
            try:
                cfg_val = _sq_config.get("SQ_DSL_MIN_BLOB_AREA", None)
                if cfg_val is not None:
                    min_blob_area = int(cfg_val)
                cfg_val = _sq_config.get("SQ_DSL_MAX_BLOBS", None)
                if cfg_val is not None:
                    max_blobs = int(cfg_val)
                cfg_val = _sq_config.get("SQ_DSL_CAMERA_MOTION_THRESHOLD", None)
                if cfg_val is not None:
                    camera_motion_threshold = float(cfg_val)
            except Exception:
                pass

        self.motion_threshold = motion_threshold
        self.min_blob_area = min_blob_area
        self.max_blobs = max_blobs
        self.blur_size = blur_size
        self.dilate_iterations = dilate_iterations
        
        # Filtering parameters
        self.min_velocity = min_velocity
        self.max_blob_size_ratio = max_blob_size_ratio
        self.min_moving_frames = min_moving_frames
        self.filter_static = filter_static
        self.camera_motion_threshold = camera_motion_threshold
        
        self._prev_gray = None
        self._prev_blobs: Dict[int, MotionBlob] = {}
        self._next_blob_id = 1
        self._frame_count = 0
        
        # Track movement history per blob (for filtering static objects)
        self._blob_movement_history: Dict[int, List[float]] = {}  # blob_id -> [velocity magnitudes]
        
        # Background model for more stable detection
        self._bg_model = None
        self._use_bg_subtraction = True
    
    def analyze(self, frame_path: Path, timing_logger=None) -> FrameDelta:
        """
        Analyze frame and return delta from previous.
        
        Pure OpenCV operations - no LLM.
        
        Args:
            frame_path: Path to frame image
            timing_logger: Optional DSLTimingLogger for performance tracking
        """
        import time
        t0 = time.perf_counter()
        
        try:
            import cv2
        except ImportError:
            return self._empty_delta()
        
        self._frame_count += 1
        
        # Start timing
        if timing_logger:
            timing_logger.start_frame(self._frame_count)
        
        # Load frame
        t_step = time.perf_counter()
        frame = cv2.imread(str(frame_path))
        if frame is None:
            return self._empty_delta()
        if timing_logger:
            timing_logger.log_step("capture", (time.perf_counter() - t_step) * 1000)
        
        h, w = frame.shape[:2]
        total_pixels = h * w
        
        # Convert to grayscale
        t_step = time.perf_counter()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if timing_logger:
            timing_logger.log_step("grayscale", (time.perf_counter() - t_step) * 1000)
        
        t_step = time.perf_counter()
        gray = cv2.GaussianBlur(gray, (self.blur_size, self.blur_size), 0)
        if timing_logger:
            timing_logger.log_step("blur", (time.perf_counter() - t_step) * 1000)
        
        # Initialize background model
        if self._bg_model is None and self._use_bg_subtraction:
            self._bg_model = cv2.createBackgroundSubtractorMOG2(
                history=100, varThreshold=16, detectShadows=False
            )
        
        # Get motion mask
        t_step = time.perf_counter()
        if self._use_bg_subtraction and self._bg_model is not None:
            motion_mask = self._bg_model.apply(frame)
        elif self._prev_gray is not None:
            # Simple frame differencing
            diff = cv2.absdiff(self._prev_gray, gray)
            _, motion_mask = cv2.threshold(diff, self.motion_threshold, 255, cv2.THRESH_BINARY)
        else:
            self._prev_gray = gray
            return self._empty_delta()
        if timing_logger:
            timing_logger.log_step("diff", (time.perf_counter() - t_step) * 1000)
        
        # Clean up mask
        t_step = time.perf_counter()
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, kernel)
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_CLOSE, kernel)
        motion_mask = cv2.dilate(motion_mask, kernel, iterations=self.dilate_iterations)
        if timing_logger:
            timing_logger.log_step("threshold", (time.perf_counter() - t_step) * 1000)
        
        # Calculate motion percentage
        changed_pixels = cv2.countNonZero(motion_mask)
        motion_percent = (changed_pixels / total_pixels) * 100
        
        # Detect potential camera motion (global change across most of the frame)
        if motion_percent >= self.camera_motion_threshold:
            # Treat as camera movement: no blobs/events, only report motion level
            # Edge map restricted to motion mask for consistency
            edges = cv2.Canny(gray, 50, 150)
            edges = cv2.bitwise_and(edges, edges, mask=motion_mask)
            
            background_b64 = self._capture_thumbnail(frame_path, frame)
            
            delta = FrameDelta(
                frame_num=self._frame_count,
                timestamp=time.time(),
                motion_percent=motion_percent,
                changed_pixels=changed_pixels,
                total_pixels=total_pixels,
                blobs=[],
                events=[],
                motion_mask=motion_mask,
                edge_map=edges,
                frame_path=str(frame_path),
                background_base64=background_b64,
            )
            
            if timing_logger:
                timing_logger.set_metrics(
                    blobs=0,
                    motion_pct=motion_percent,
                    events=0,
                )
                timing_logger.end_frame()
            
            self._prev_gray = gray
            return delta
        
        # Find contours (blobs)
        t_step = time.perf_counter()
        contours, _ = cv2.findContours(
            motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if timing_logger:
            timing_logger.log_step("contours", (time.perf_counter() - t_step) * 1000)
        
        # Extract candidate rectangles for motion regions
        rects: List[Tuple[int, int, int, int, int, int]] = []  # (x1, y1, x2, y2, area, contour_points)
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_blob_area:
                continue
            
            x, y, bw, bh = cv2.boundingRect(contour)
            x1, y1, x2, y2 = x, y, x + bw, y + bh
            rects.append((x1, y1, x2, y2, int(area), len(contour)))
        
        # Group nearby / overlapping rectangles into larger motion fragments
        gap_px = max(20, int(0.01 * min(w, h)))
        if _sq_config is not None:
            try:
                cfg_gap = _sq_config.get("SQ_DSL_GAP_PX", None)
                if cfg_gap is not None:
                    gap_px = int(cfg_gap)
            except Exception:
                pass
        merged_rects = self._merge_motion_rects(rects, gap_px=gap_px)
        
        blobs: List[MotionBlob] = []
        for x1, y1, x2, y2, area_px, contour_pts in merged_rects:
            bw = max(1, x2 - x1)
            bh = max(1, y2 - y1)
            cx = x1 + bw / 2.0
            cy = y1 + bh / 2.0
            
            # Filter out very large blobs (likely background/full frame)
            blob_size_ratio = (bw * bh) / (w * h)
            if self.filter_static and blob_size_ratio > self.max_blob_size_ratio:
                continue
            
            # Approximate complexity for merged region
            perimeter = 2 * (bw + bh)
            complexity = min(1.0, (perimeter ** 2) / (4 * math.pi * max(area_px, 1)) / 10)
            
            # Compute simple appearance descriptors in grayscale (shape + intensity)
            shape_desc: Tuple[float, ...] = tuple()
            intensity_mean: float = -1.0
            intensity_std: float = -1.0
            try:
                import cv2
                # Clip to frame bounds (defensive)
                rx1 = max(0, min(x1, w - 1))
                ry1 = max(0, min(y1, h - 1))
                rx2 = max(1, min(x2, w))
                ry2 = max(1, min(y2, h))
                roi_mask = motion_mask[ry1:ry2, rx1:rx2]
                roi_gray = gray[ry1:ry2, rx1:rx2]
                if roi_mask.size > 0 and roi_gray.size > 0:
                    # Hu moments on binary mask (shape, robust to illumination)
                    m = cv2.moments(roi_mask)
                    if m["m00"] > 0:
                        hu = cv2.HuMoments(m).flatten()
                        # Log-scale for stability, limit extremes
                        shape_desc = tuple(
                            float(-math.copysign(1.0, v) * math.log10(abs(v) + 1e-6))
                            for v in hu
                        )
                    # Intensity stats on moving pixels only
                    moving_pixels = roi_gray[roi_mask > 0]
                    if moving_pixels.size > 0:
                        intensity_mean = float(np.mean(moving_pixels))
                        intensity_std = float(np.std(moving_pixels))
            except Exception:
                # Descriptors are optional; tracking falls back to geometric cost
                pass
            
            blob = MotionBlob(
                id=0,  # Will be assigned during tracking
                center=Point2D(cx / w, cy / h),
                size=Point2D(bw / w, bh / h),
                area_px=int(area_px),
                contour_points=int(contour_pts),
                complexity=complexity,
                aspect_ratio=bw / bh if bh > 0 else 1.0,
                shape_descriptor=shape_desc,
                intensity_mean=intensity_mean,
                intensity_std=intensity_std,
                last_seen=self._frame_count,
            )
            blobs.append(blob)
        
        # Sort by area (largest first) and limit
        blobs.sort(key=lambda b: b.area_px, reverse=True)
        blobs = blobs[:self.max_blobs]
        
        # Track blobs (assign IDs, calculate velocity)
        t_step = time.perf_counter()
        tracked_blobs, events = self._track_blobs(blobs)
        if timing_logger:
            timing_logger.log_step("tracking", (time.perf_counter() - t_step) * 1000)
        
        # Edge detection on motion regions
        edges = cv2.Canny(gray, 50, 150)
        edges = cv2.bitwise_and(edges, edges, mask=motion_mask)
        
        # Capture 128px thumbnail while frame file still exists
        t_step = time.perf_counter()
        background_b64 = self._capture_thumbnail(frame_path, frame)
        if timing_logger:
            timing_logger.log_step("thumbnail", (time.perf_counter() - t_step) * 1000)
        
        # Create delta
        delta = FrameDelta(
            frame_num=self._frame_count,
            timestamp=time.time(),
            motion_percent=motion_percent,
            changed_pixels=changed_pixels,
            total_pixels=total_pixels,
            blobs=tracked_blobs,
            events=events,
            motion_mask=motion_mask,
            edge_map=edges,
            frame_path=str(frame_path),
            background_base64=background_b64,
        )
        
        # Set metrics and end frame timing
        if timing_logger:
            timing_logger.set_metrics(
                blobs=len(tracked_blobs),
                motion_pct=motion_percent,
                events=len(events)
            )
            timing_logger.end_frame()
        
        self._prev_gray = gray
        return delta
    
    def _merge_motion_rects(
        self,
        rects: List[Tuple[int, int, int, int, int, int]],
        gap_px: int = 10,
    ) -> List[Tuple[int, int, int, int, int, int]]:
        """Merge overlapping / nearby motion rectangles into larger fragments.
        
        Args:
            rects: list of (x1, y1, x2, y2, area_px, contour_points)
            gap_px: distance in pixels to still treat rectangles as connected
        """
        merged: List[Tuple[int, int, int, int, int, int]] = []
        
        for rect in rects:
            x1, y1, x2, y2, area, pts = rect
            merged_into = False
            for idx, (mx1, my1, mx2, my2, marea, mpts) in enumerate(merged):
                # Expand existing merged rect by gap_px and check overlap
                ex1 = mx1 - gap_px
                ey1 = my1 - gap_px
                ex2 = mx2 + gap_px
                ey2 = my2 + gap_px
                
                if not (x2 < ex1 or x1 > ex2 or y2 < ey1 or y1 > ey2):
                    # Overlaps or is close enough - merge
                    nx1 = min(mx1, x1)
                    ny1 = min(my1, y1)
                    nx2 = max(mx2, x2)
                    ny2 = max(my2, y2)
                    narea = marea + area
                    npts = mpts + pts
                    merged[idx] = (nx1, ny1, nx2, ny2, narea, npts)
                    merged_into = True
                    break
            
            if not merged_into:
                merged.append(rect)
        
        return merged
    
    def _capture_thumbnail(self, frame_path: Path, frame: np.ndarray, max_size: int = 128) -> str:
        """Capture 128px thumbnail from frame while it still exists."""
        try:
            import cv2
            import base64
            
            h, w = frame.shape[:2]
            if w > h:
                new_w = max_size
                new_h = int(h * max_size / w)
            else:
                new_h = max_size
                new_w = int(w * max_size / h)
            
            resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            _, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 70])
            return base64.b64encode(buffer).decode()
        except Exception:
            return ""
    
    def _track_blobs(
        self,
        new_blobs: List[MotionBlob]
    ) -> Tuple[List[MotionBlob], List[MetaEvent]]:
        """
        Track blobs between frames using distance-based matching.
        """
        events = []
        tracked = []
        
        # Match new blobs to existing
        used_old = set()
        used_new = set()
        
        # Build cost matrix
        if self._prev_blobs and new_blobs:
            matches = []
            for new_idx, new_blob in enumerate(new_blobs):
                for old_id, old_blob in self._prev_blobs.items():
                    # Geometric distance (normalized center distance)
                    dist = new_blob.center.distance_to(old_blob.center)
                    # Relative size difference
                    size_diff = abs(new_blob.area_px - old_blob.area_px) / max(new_blob.area_px, old_blob.area_px, 1)
                    
                    # Appearance distance based on shape descriptor (Hu moments)
                    shape_dist = 0.0
                    if new_blob.shape_descriptor and old_blob.shape_descriptor and \
                       len(new_blob.shape_descriptor) == len(old_blob.shape_descriptor):
                        shape_dist = sum(
                            abs(a - b) for a, b in zip(new_blob.shape_descriptor, old_blob.shape_descriptor)
                        ) / len(new_blob.shape_descriptor)
                        # Clamp to reasonable range
                        shape_dist = min(shape_dist, 5.0)
                    
                    # Intensity distance (mean brightness)
                    intensity_diff = 0.0
                    if new_blob.intensity_mean >= 0 and old_blob.intensity_mean >= 0:
                        intensity_diff = abs(new_blob.intensity_mean - old_blob.intensity_mean) / 255.0
                    
                    # Combined cost: geometric + weighted appearance
                    cost = dist + size_diff * 0.3 + shape_dist * 0.2 + intensity_diff * 0.2
                    matches.append((cost, new_idx, old_id))
            
            # Greedy matching (could use Hungarian for optimal)
            matches.sort(key=lambda x: x[0])
            
            for cost, new_idx, old_id in matches:
                if new_idx in used_new or old_id in used_old:
                    continue
                if cost > 0.8:  # Too different (position/shape/brightness)
                    continue
                
                new_blob = new_blobs[new_idx]
                old_blob = self._prev_blobs[old_id]
                
                # Update blob with tracking info
                new_blob.id = old_id
                new_blob.velocity = new_blob.center - old_blob.center
                new_blob.age = old_blob.age + 1
                new_blob.classification = old_blob.classification
                new_blob.confidence = old_blob.confidence
                
                # Track movement history for this blob
                vel_mag = new_blob.velocity.magnitude()
                if old_id not in self._blob_movement_history:
                    self._blob_movement_history[old_id] = []
                self._blob_movement_history[old_id].append(vel_mag)
                # Keep only last 5 frames
                self._blob_movement_history[old_id] = self._blob_movement_history[old_id][-5:]
                
                # Check if this object is truly moving (not just noise/flicker)
                is_truly_moving = vel_mag >= self.min_velocity
                if self.filter_static and self.min_moving_frames > 1:
                    # Check if it has moved consistently across multiple frames
                    history = self._blob_movement_history[old_id]
                    moving_frames = sum(1 for v in history if v >= self.min_velocity)
                    is_truly_moving = moving_frames >= min(self.min_moving_frames, len(history))
                
                # Detect direction
                direction = self._get_direction(new_blob.velocity) if is_truly_moving else Direction.STATIC
                
                # Create MOVE event only if truly moving
                if is_truly_moving:
                    events.append(MetaEvent(
                        type=EventType.MOVE,
                        blob_id=old_id,
                        direction=direction,
                        details=f"speed={vel_mag:.4f}"
                    ))
                
                tracked.append(new_blob)
                used_new.add(new_idx)
                used_old.add(old_id)
        
        # Handle new blobs (ENTER/APPEAR)
        for new_idx, new_blob in enumerate(new_blobs):
            if new_idx in used_new:
                continue
            
            new_blob.id = self._next_blob_id
            self._next_blob_id += 1
            
            # Determine if entering from edge
            event_type = EventType.APPEAR
            direction = Direction.STATIC
            
            if new_blob.center.x < 0.1:
                event_type = EventType.ENTER
                direction = Direction.LEFT
            elif new_blob.center.x > 0.9:
                event_type = EventType.ENTER
                direction = Direction.RIGHT
            elif new_blob.center.y < 0.1:
                event_type = EventType.ENTER
                direction = Direction.UP
            elif new_blob.center.y > 0.9:
                event_type = EventType.ENTER
                direction = Direction.DOWN
            
            events.append(MetaEvent(
                type=event_type,
                blob_id=new_blob.id,
                direction=direction,
            ))
            
            tracked.append(new_blob)
        
        # Handle disappeared blobs (EXIT/DISAPPEAR)
        for old_id, old_blob in self._prev_blobs.items():
            if old_id in used_old:
                continue
            
            # Determine if exiting at edge
            event_type = EventType.DISAPPEAR
            direction = Direction.STATIC
            
            if old_blob.center.x < 0.1:
                event_type = EventType.EXIT
                direction = Direction.LEFT
            elif old_blob.center.x > 0.9:
                event_type = EventType.EXIT
                direction = Direction.RIGHT
            elif old_blob.center.y < 0.1:
                event_type = EventType.EXIT
                direction = Direction.UP
            elif old_blob.center.y > 0.9:
                event_type = EventType.EXIT
                direction = Direction.DOWN
            
            events.append(MetaEvent(
                type=event_type,
                blob_id=old_id,
                direction=direction,
            ))
        
        # Update tracked blobs
        self._prev_blobs = {b.id: b for b in tracked}
        
        return tracked, events
    
    def _get_direction(self, velocity: Point2D) -> Direction:
        """Determine direction from velocity vector."""
        if velocity.magnitude() < 0.005:
            return Direction.STATIC
        
        # Primary direction
        if abs(velocity.x) > abs(velocity.y):
            return Direction.RIGHT if velocity.x > 0 else Direction.LEFT
        else:
            return Direction.DOWN if velocity.y > 0 else Direction.UP
    
    def _empty_delta(self) -> FrameDelta:
        """Return empty delta."""
        return FrameDelta(
            frame_num=self._frame_count,
            timestamp=time.time(),
        )
    
    def reset(self):
        """Reset analyzer state."""
        self._prev_gray = None
        self._prev_blobs.clear()
        self._next_blob_id = 1
        self._frame_count = 0
        self._bg_model = None


# ============================================================================
# DSL Generator - Converts analysis to DSL text
# ============================================================================

class DSLGenerator:
    """
    Generates DSL metadata text from frame analysis.
    """
    
    def __init__(self):
        self.lines: List[str] = []
        self.tracks: Dict[int, TrackInfo] = {}
    
    def add_delta(self, delta: FrameDelta) -> str:
        """
        Convert FrameDelta to DSL text.
        
        Returns DSL string for this frame.
        """
        lines = []
        
        # Frame header
        ts = time.strftime("%H:%M:%S", time.localtime(delta.timestamp))
        ms = int((delta.timestamp % 1) * 1000)
        lines.append(f"FRAME {delta.frame_num} @ {ts}.{ms:03d}")
        
        # Delta info
        lines.append(f"  DELTA motion_pct={delta.motion_percent:.1f}% regions={len(delta.blobs)}")
        
        # Blobs
        for blob in delta.blobs:
            pos = f"({blob.center.x:.3f},{blob.center.y:.3f})"
            size = f"({blob.size.x:.3f},{blob.size.y:.3f})"
            vel = f"({blob.velocity.x:.4f},{blob.velocity.y:.4f})"
            
            lines.append(f"  BLOB id={blob.id} pos={pos} size={size} vel={vel}")
            
            # Edge/contour info
            if blob.contour_points > 0:
                lines.append(f"  EDGE blob={blob.id} points={blob.contour_points} area={blob.area_px}px complexity={blob.complexity:.2f}")
            
            # Update tracking
            self._update_track(blob)
        
        # Events
        for event in delta.events:
            dir_str = f" dir={event.direction.value}" if event.direction != Direction.STATIC else ""
            details = f" {event.details}" if event.details else ""
            lines.append(f"  EVENT type={event.type.value} blob={event.blob_id}{dir_str}{details}")
        
        # Track summaries for blobs with history
        for blob in delta.blobs:
            if blob.id in self.tracks:
                track = self.tracks[blob.id]
                if track.total_frames >= 3:
                    lines.append(f"  TRACK blob={blob.id} frames={track.total_frames} dist={track.total_distance:.4f} speed={track.avg_speed:.4f}")
        
        # Classification (if known)
        for blob in delta.blobs:
            if blob.classification != "UNKNOWN":
                lines.append(f"  CLASS blob={blob.id} -> {blob.classification} (conf={blob.confidence:.2f})")
        
        dsl_text = "\n".join(lines)
        self.lines.append(dsl_text)
        return dsl_text
    
    def _update_track(self, blob: MotionBlob):
        """Update tracking information."""
        if blob.id not in self.tracks:
            self.tracks[blob.id] = TrackInfo(
                blob_id=blob.id,
                total_frames=1,
                total_distance=0,
                avg_speed=0,
                trajectory=[blob.center],
            )
        else:
            track = self.tracks[blob.id]
            
            # Update distance
            if track.trajectory:
                dist = blob.center.distance_to(track.trajectory[-1])
                track.total_distance += dist
            
            track.trajectory.append(blob.center)
            track.total_frames += 1
            track.avg_speed = track.total_distance / track.total_frames
            
            # Track direction history
            direction = self._get_direction(blob.velocity)
            track.direction_history.append(direction)
    
    def _get_direction(self, velocity: Point2D) -> Direction:
        """Get direction from velocity."""
        if velocity.magnitude() < 0.005:
            return Direction.STATIC
        if abs(velocity.x) > abs(velocity.y):
            return Direction.RIGHT if velocity.x > 0 else Direction.LEFT
        return Direction.DOWN if velocity.y > 0 else Direction.UP
    
    def get_full_dsl(self) -> str:
        """Get complete DSL output."""
        header = [
            "# Motion Analysis DSL Output",
            f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Total frames: {len(self.lines)}",
            f"# Tracked objects: {len(self.tracks)}",
            "",
        ]
        return "\n".join(header) + "\n" + "\n\n".join(self.lines)
    
    def get_summary(self) -> Dict:
        """Get analysis summary."""
        return {
            "total_frames": len(self.lines),
            "tracked_objects": len(self.tracks),
            "tracks": {
                tid: {
                    "frames": t.total_frames,
                    "distance": t.total_distance,
                    "avg_speed": t.avg_speed,
                }
                for tid, t in self.tracks.items()
            }
        }
    
    def reset(self):
        """Reset generator."""
        self.lines.clear()
        self.tracks.clear()


# ============================================================================
# LLM Classifier - Minimal LLM usage for object classification only
# ============================================================================

class BlobClassifier:
    """
    Classifies blob type using LLM (minimal usage).
    
    Only called when:
    1. New object detected
    2. Object has been tracked for N frames (stable)
    3. Explicitly requested
    """
    
    def __init__(
        self,
        model: str = "moondream",  # Fast model for classification
        min_frames_before_classify: int = 3,
        ollama_url: str = "http://localhost:11434",
    ):
        self.model = model
        self.min_frames = min_frames_before_classify
        self.ollama_url = ollama_url
        
        self._classified: Dict[int, str] = {}  # blob_id -> classification
        self._pending: Dict[int, int] = {}  # blob_id -> frame_count
    
    def should_classify(self, blob: MotionBlob) -> bool:
        """Check if blob should be classified."""
        if blob.id in self._classified:
            return False
        
        # Track frames
        self._pending[blob.id] = self._pending.get(blob.id, 0) + 1
        
        return self._pending[blob.id] >= self.min_frames
    
    def classify(
        self,
        blob: MotionBlob,
        frame_path: Path,
        crop_to_blob: bool = True,
    ) -> Tuple[str, float]:
        """
        Classify blob using LLM.
        
        Returns (classification, confidence).
        """
        if blob.id in self._classified:
            return self._classified[blob.id], 1.0
        
        try:
            import requests
            import base64
            import cv2
        except ImportError:
            return "UNKNOWN", 0.0
        
        # Load and crop image
        frame = cv2.imread(str(frame_path))
        if frame is None:
            return "UNKNOWN", 0.0
        
        h, w = frame.shape[:2]
        
        if crop_to_blob:
            # Crop to blob with padding
            padding = 0.1
            x1 = max(0, int((blob.center.x - blob.size.x/2 - padding) * w))
            y1 = max(0, int((blob.center.y - blob.size.y/2 - padding) * h))
            x2 = min(w, int((blob.center.x + blob.size.x/2 + padding) * w))
            y2 = min(h, int((blob.center.y + blob.size.y/2 + padding) * h))
            
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                crop = frame
        else:
            crop = frame
        
        # Resize for faster processing
        crop = cv2.resize(crop, (256, 256))
        
        # Encode to base64
        _, buffer = cv2.imencode('.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 70])
        img_b64 = base64.b64encode(buffer).decode()
        
        # Simple classification prompt
        prompt = """What is this object? Reply with ONLY ONE word:
- person
- bird
- cat
- dog
- car
- vehicle
- animal
- unknown

Answer:"""
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [img_b64],
                    "stream": False,
                    "options": {"num_predict": 10}
                },
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json().get("response", "").strip().lower()
                
                # Parse result
                valid_classes = ["person", "bird", "cat", "dog", "car", "vehicle", "animal"]
                for cls in valid_classes:
                    if cls in result:
                        self._classified[blob.id] = cls.upper()
                        return cls.upper(), 0.9
                
                return "UNKNOWN", 0.3
            
        except Exception as e:
            logger.debug(f"Classification failed: {e}")
        
        return "UNKNOWN", 0.0
    
    def get_cached(self, blob_id: int) -> Optional[str]:
        """Get cached classification."""
        return self._classified.get(blob_id)
    
    def reset(self):
        """Reset classifier."""
        self._classified.clear()
        self._pending.clear()


# ============================================================================
# Complete Pipeline
# ============================================================================

class FrameDiffPipeline:
    """
    Complete pipeline: Frame -> Analysis -> DSL -> Optional Classification.
    """
    
    def __init__(
        self,
        enable_classification: bool = True,
        classifier_model: str = "moondream",
    ):
        self.analyzer = FrameDiffAnalyzer()
        self.generator = DSLGenerator()
        self.classifier = BlobClassifier(model=classifier_model) if enable_classification else None
        
        self.deltas: List[FrameDelta] = []
    
    def process_frame(
        self,
        frame_path: Path,
        classify_new: bool = True,
    ) -> Tuple[FrameDelta, str]:
        """
        Process single frame.
        
        Returns (delta, dsl_text).
        """
        # Analyze frame (pure OpenCV)
        delta = self.analyzer.analyze(frame_path)
        
        # Classify blobs if needed
        if self.classifier and classify_new:
            for blob in delta.blobs:
                if self.classifier.should_classify(blob):
                    cls, conf = self.classifier.classify(blob, frame_path)
                    blob.classification = cls
                    blob.confidence = conf
                else:
                    # Use cached
                    cached = self.classifier.get_cached(blob.id)
                    if cached:
                        blob.classification = cached
                        blob.confidence = 1.0
        
        # Generate DSL
        dsl_text = self.generator.add_delta(delta)
        
        self.deltas.append(delta)
        return delta, dsl_text
    
    def get_full_dsl(self) -> str:
        """Get complete DSL output."""
        return self.generator.get_full_dsl()
    
    def get_summary(self) -> Dict:
        """Get analysis summary."""
        return self.generator.get_summary()
    
    def export_dsl(self, output_path: Path):
        """Export DSL to file."""
        Path(output_path).write_text(self.get_full_dsl())
    
    def reset(self):
        """Reset pipeline."""
        self.analyzer.reset()
        self.generator.reset()
        if self.classifier:
            self.classifier.reset()
        self.deltas.clear()


# ============================================================================
# Convenience Functions
# ============================================================================

_pipeline: Optional[FrameDiffPipeline] = None


def get_pipeline(**kwargs) -> FrameDiffPipeline:
    """Get or create global pipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = FrameDiffPipeline(**kwargs)
    return _pipeline


def analyze_frame(frame_path: Path) -> Tuple[FrameDelta, str]:
    """Quick function to analyze single frame."""
    pipeline = get_pipeline()
    return pipeline.process_frame(frame_path)
