"""
Motion Tracker & Object Extraction for Streamware

Advanced algorithms for tracking objects between frames:
- Kalman Filter: Predict object position
- Hungarian Algorithm: Optimal assignment between detections
- Optical Flow: Dense motion estimation
- Background Subtraction: Isolate moving objects

Features:
- Track objects across frames with unique IDs
- Extract motion regions and focus on them
- Mathematical representation of movement vectors
- SVG vector output for visualization
"""

import logging
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class Point:
    """2D point with optional velocity."""
    x: float
    y: float
    vx: float = 0.0  # velocity x
    vy: float = 0.0  # velocity y
    
    def distance_to(self, other: 'Point') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)
    
    def __add__(self, other: 'Point') -> 'Point':
        return Point(self.x + other.x, self.y + other.y, self.vx, self.vy)
    
    def __sub__(self, other: 'Point') -> 'Point':
        return Point(self.x - other.x, self.y - other.y, self.vx, self.vy)


@dataclass
class BoundingBox:
    """Bounding box with center, size, and motion."""
    x: float  # center x (normalized 0-1)
    y: float  # center y (normalized 0-1)
    w: float  # width (normalized)
    h: float  # height (normalized)
    confidence: float = 1.0
    class_name: str = "object"
    
    @property
    def center(self) -> Point:
        return Point(self.x, self.y)
    
    @property
    def area(self) -> float:
        return self.w * self.h
    
    @property
    def top_left(self) -> Tuple[float, float]:
        return (self.x - self.w/2, self.y - self.h/2)
    
    @property
    def bottom_right(self) -> Tuple[float, float]:
        return (self.x + self.w/2, self.y + self.h/2)
    
    def iou(self, other: 'BoundingBox') -> float:
        """Intersection over Union."""
        x1 = max(self.x - self.w/2, other.x - other.w/2)
        y1 = max(self.y - self.h/2, other.y - other.h/2)
        x2 = min(self.x + self.w/2, other.x + other.w/2)
        y2 = min(self.y + self.h/2, other.y + other.h/2)
        
        if x2 < x1 or y2 < y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        union = self.area + other.area - intersection
        
        return intersection / union if union > 0 else 0.0


@dataclass
class TrackedObject:
    """Object being tracked across frames."""
    id: int
    bbox: BoundingBox
    velocity: Point = field(default_factory=lambda: Point(0, 0))
    age: int = 0  # frames since first detection
    hits: int = 1  # successful detections
    misses: int = 0  # frames without detection
    class_name: str = "object"
    
    # Kalman filter state
    state: Optional[np.ndarray] = None
    covariance: Optional[np.ndarray] = None
    
    # History for trajectory
    history: List[Point] = field(default_factory=list)
    
    def predict_position(self) -> Point:
        """Predict next position using velocity."""
        return Point(
            self.bbox.x + self.velocity.x,
            self.bbox.y + self.velocity.y,
            self.velocity.vx,
            self.velocity.vy
        )
    
    def update_velocity(self, new_bbox: BoundingBox):
        """Update velocity based on new position."""
        self.velocity = Point(
            new_bbox.x - self.bbox.x,
            new_bbox.y - self.bbox.y
        )
    
    def get_trajectory_svg(self, width: int, height: int) -> str:
        """Generate SVG path for trajectory."""
        if len(self.history) < 2:
            return ""
        
        points = [(int(p.x * width), int(p.y * height)) for p in self.history]
        path_data = f"M {points[0][0]} {points[0][1]}"
        for x, y in points[1:]:
            path_data += f" L {x} {y}"
        
        return f'<path d="{path_data}" stroke="#{self.id * 12345 % 0xFFFFFF:06x}" stroke-width="2" fill="none" opacity="0.7"/>'


# ============================================================================
# Kalman Filter for Motion Prediction
# ============================================================================

class KalmanFilter2D:
    """
    2D Kalman Filter for object tracking.
    
    State: [x, y, vx, vy] - position and velocity
    Measurement: [x, y] - observed position
    """
    
    def __init__(self, initial_pos: Point, dt: float = 1.0):
        self.dt = dt
        
        # State: [x, y, vx, vy]
        self.state = np.array([initial_pos.x, initial_pos.y, 0, 0], dtype=float)
        
        # State transition matrix (constant velocity model)
        self.F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=float)
        
        # Measurement matrix (we only measure position)
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ], dtype=float)
        
        # Process noise covariance
        q = 0.1  # process noise
        self.Q = np.array([
            [q, 0, 0, 0],
            [0, q, 0, 0],
            [0, 0, q, 0],
            [0, 0, 0, q]
        ], dtype=float)
        
        # Measurement noise covariance
        r = 0.5  # measurement noise
        self.R = np.array([
            [r, 0],
            [0, r]
        ], dtype=float)
        
        # Initial covariance
        self.P = np.eye(4) * 1.0
    
    def predict(self) -> Point:
        """Predict next state."""
        self.state = self.F @ self.state
        self.P = self.F @ self.P @ self.F.T + self.Q
        return Point(self.state[0], self.state[1], self.state[2], self.state[3])
    
    def update(self, measurement: Point) -> Point:
        """Update state with measurement."""
        z = np.array([measurement.x, measurement.y])
        
        # Innovation
        y = z - self.H @ self.state
        
        # Innovation covariance
        S = self.H @ self.P @ self.H.T + self.R
        
        # Kalman gain
        K = self.P @ self.H.T @ np.linalg.inv(S)
        
        # Update state
        self.state = self.state + K @ y
        
        # Update covariance
        I = np.eye(4)
        self.P = (I - K @ self.H) @ self.P
        
        return Point(self.state[0], self.state[1], self.state[2], self.state[3])
    
    def get_velocity(self) -> Point:
        """Get current velocity estimate."""
        return Point(0, 0, self.state[2], self.state[3])


# ============================================================================
# Hungarian Algorithm for Detection Assignment
# ============================================================================

def hungarian_assignment(cost_matrix: np.ndarray) -> List[Tuple[int, int]]:
    """
    Hungarian algorithm for optimal assignment.
    
    Args:
        cost_matrix: NxM matrix where N=tracks, M=detections
                    cost_matrix[i,j] = cost of assigning track i to detection j
    
    Returns:
        List of (track_idx, detection_idx) pairs
    """
    try:
        from scipy.optimize import linear_sum_assignment
        row_indices, col_indices = linear_sum_assignment(cost_matrix)
        return list(zip(row_indices, col_indices))
    except ImportError:
        # Fallback: greedy assignment
        return _greedy_assignment(cost_matrix)


def _greedy_assignment(cost_matrix: np.ndarray) -> List[Tuple[int, int]]:
    """Greedy assignment fallback when scipy not available."""
    assignments = []
    used_cols = set()
    
    for i in range(cost_matrix.shape[0]):
        best_j = -1
        best_cost = float('inf')
        
        for j in range(cost_matrix.shape[1]):
            if j not in used_cols and cost_matrix[i, j] < best_cost:
                best_cost = cost_matrix[i, j]
                best_j = j
        
        if best_j >= 0 and best_cost < 1.0:  # threshold
            assignments.append((i, best_j))
            used_cols.add(best_j)
    
    return assignments


# ============================================================================
# Multi-Object Tracker
# ============================================================================

class MultiObjectTracker:
    """
    Multi-object tracker using Kalman filter and Hungarian algorithm.
    
    Tracks multiple objects across frames, handling:
    - New objects appearing
    - Objects disappearing
    - Occlusion and re-identification
    """
    
    def __init__(
        self,
        max_age: int = 30,  # frames before track deletion
        min_hits: int = 3,  # hits before track confirmed
        iou_threshold: float = 0.3,
        distance_threshold: float = 0.2,
    ):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.distance_threshold = distance_threshold
        
        self.tracks: Dict[int, TrackedObject] = {}
        self.kalman_filters: Dict[int, KalmanFilter2D] = {}
        self.next_id = 1
        self.frame_count = 0
    
    def update(self, detections: List[BoundingBox]) -> List[TrackedObject]:
        """
        Update tracker with new detections.
        
        Args:
            detections: List of detected bounding boxes
            
        Returns:
            List of confirmed tracked objects
        """
        self.frame_count += 1
        
        # Predict new positions for existing tracks
        predictions = {}
        for track_id, track in self.tracks.items():
            if track_id in self.kalman_filters:
                pred = self.kalman_filters[track_id].predict()
                predictions[track_id] = pred
        
        # Build cost matrix
        track_ids = list(self.tracks.keys())
        if track_ids and detections:
            cost_matrix = np.zeros((len(track_ids), len(detections)))
            
            for i, track_id in enumerate(track_ids):
                track = self.tracks[track_id]
                pred = predictions.get(track_id, track.bbox.center)
                
                for j, det in enumerate(detections):
                    # Cost = 1 - IoU + distance penalty
                    iou = track.bbox.iou(det)
                    dist = pred.distance_to(det.center)
                    cost_matrix[i, j] = (1 - iou) + dist
            
            # Hungarian assignment
            assignments = hungarian_assignment(cost_matrix)
        else:
            assignments = []
        
        # Process assignments
        assigned_tracks = set()
        assigned_detections = set()
        
        for track_idx, det_idx in assignments:
            track_id = track_ids[track_idx]
            det = detections[det_idx]
            
            # Check if assignment is valid
            if cost_matrix[track_idx, det_idx] < 1.5:
                # Update track
                track = self.tracks[track_id]
                track.update_velocity(det)
                track.bbox = det
                track.hits += 1
                track.misses = 0
                track.age += 1
                track.history.append(det.center)
                
                # Update Kalman filter
                if track_id in self.kalman_filters:
                    self.kalman_filters[track_id].update(det.center)
                
                assigned_tracks.add(track_id)
                assigned_detections.add(det_idx)
        
        # Handle unassigned tracks (missed detections)
        for track_id in track_ids:
            if track_id not in assigned_tracks:
                self.tracks[track_id].misses += 1
                self.tracks[track_id].age += 1
        
        # Handle unassigned detections (new objects)
        for det_idx, det in enumerate(detections):
            if det_idx not in assigned_detections:
                self._create_track(det)
        
        # Remove old tracks
        tracks_to_remove = [
            track_id for track_id, track in self.tracks.items()
            if track.misses > self.max_age
        ]
        for track_id in tracks_to_remove:
            del self.tracks[track_id]
            if track_id in self.kalman_filters:
                del self.kalman_filters[track_id]
        
        # Return confirmed tracks
        return [
            track for track in self.tracks.values()
            if track.hits >= self.min_hits
        ]
    
    def _create_track(self, detection: BoundingBox):
        """Create new track for detection."""
        track = TrackedObject(
            id=self.next_id,
            bbox=detection,
            class_name=detection.class_name,
            history=[detection.center]
        )
        self.tracks[self.next_id] = track
        self.kalman_filters[self.next_id] = KalmanFilter2D(detection.center)
        self.next_id += 1
    
    def get_active_tracks(self) -> List[TrackedObject]:
        """Get all active tracks."""
        return list(self.tracks.values())
    
    def reset(self):
        """Reset tracker state."""
        self.tracks.clear()
        self.kalman_filters.clear()
        self.next_id = 1
        self.frame_count = 0


# ============================================================================
# Motion Region Extractor
# ============================================================================

class MotionRegionExtractor:
    """
    Extract and focus on moving regions in frames.
    
    Uses background subtraction and contour analysis.
    """
    
    def __init__(
        self,
        history: int = 50,
        var_threshold: float = 16,
        detect_shadows: bool = False,
        min_area: int = 500,
        padding: float = 0.1,  # padding around motion region
    ):
        self.history = history
        self.var_threshold = var_threshold
        self.detect_shadows = detect_shadows
        self.min_area = min_area
        self.padding = padding
        
        self._bg_subtractor = None
        self._frame_size = None
    
    def _init_bg_subtractor(self):
        """Initialize background subtractor."""
        try:
            import cv2
            self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=self.history,
                varThreshold=self.var_threshold,
                detectShadows=self.detect_shadows
            )
        except ImportError:
            logger.warning("OpenCV not available for background subtraction")
    
    def extract_motion_regions(
        self,
        frame_path: Path,
    ) -> List[BoundingBox]:
        """
        Extract motion regions from frame.
        
        Args:
            frame_path: Path to frame image
            
        Returns:
            List of bounding boxes for motion regions
        """
        try:
            import cv2
        except ImportError:
            return []
        
        if self._bg_subtractor is None:
            self._init_bg_subtractor()
        
        frame = cv2.imread(str(frame_path))
        if frame is None:
            return []
        
        self._frame_size = (frame.shape[1], frame.shape[0])
        
        # Apply background subtraction
        fg_mask = self._bg_subtractor.apply(frame)
        
        # Clean up mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(
            fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Convert to bounding boxes
        boxes = []
        w, h = self._frame_size
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area:
                continue
            
            x, y, bw, bh = cv2.boundingRect(contour)
            
            # Normalize to 0-1
            boxes.append(BoundingBox(
                x=(x + bw/2) / w,
                y=(y + bh/2) / h,
                w=bw / w,
                h=bh / h,
                confidence=min(1.0, area / 10000),
                class_name="motion"
            ))
        
        return boxes
    
    def crop_to_motion(
        self,
        frame_path: Path,
        regions: List[BoundingBox],
        output_path: Path = None,
    ) -> Optional[Path]:
        """
        Crop frame to focus on motion regions.
        
        Args:
            frame_path: Path to frame
            regions: Motion regions
            output_path: Output path (optional)
            
        Returns:
            Path to cropped image
        """
        try:
            import cv2
        except ImportError:
            return frame_path
        
        if not regions:
            return frame_path
        
        frame = cv2.imread(str(frame_path))
        if frame is None:
            return frame_path
        
        h, w = frame.shape[:2]
        
        # Find bounding box of all regions
        min_x = min(max(0, r.x - r.w/2 - self.padding) for r in regions)
        min_y = min(max(0, r.y - r.h/2 - self.padding) for r in regions)
        max_x = max(min(1, r.x + r.w/2 + self.padding) for r in regions)
        max_y = max(min(1, r.y + r.h/2 + self.padding) for r in regions)
        
        # Convert to pixels
        x1, y1 = int(min_x * w), int(min_y * h)
        x2, y2 = int(max_x * w), int(max_y * h)
        
        # Crop
        cropped = frame[y1:y2, x1:x2]
        
        # Save
        if output_path is None:
            output_path = frame_path.with_stem(frame_path.stem + "_cropped")
        
        cv2.imwrite(str(output_path), cropped)
        return output_path
    
    def reset(self):
        """Reset background model."""
        self._bg_subtractor = None


# ============================================================================
# Optical Flow for Dense Motion
# ============================================================================

class OpticalFlowAnalyzer:
    """
    Optical flow analysis for dense motion estimation.
    """
    
    def __init__(self, grid_size: int = 20):
        self.grid_size = grid_size
        self._prev_gray = None
    
    def compute_flow(self, frame_path: Path) -> Optional[np.ndarray]:
        """
        Compute optical flow from previous frame.
        
        Returns NxMx2 array of flow vectors.
        """
        try:
            import cv2
        except ImportError:
            return None
        
        frame = cv2.imread(str(frame_path))
        if frame is None:
            return None
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self._prev_gray is None:
            self._prev_gray = gray
            return None
        
        # Compute dense optical flow
        flow = cv2.calcOpticalFlowFarneback(
            self._prev_gray, gray,
            None, 0.5, 3, 15, 3, 5, 1.2, 0
        )
        
        self._prev_gray = gray
        return flow
    
    def flow_to_vectors(
        self,
        flow: np.ndarray,
        threshold: float = 1.0,
    ) -> List[Tuple[Point, Point]]:
        """
        Convert flow to motion vectors.
        
        Returns list of (start_point, end_point) pairs.
        """
        if flow is None:
            return []
        
        h, w = flow.shape[:2]
        vectors = []
        
        step = max(1, min(h, w) // self.grid_size)
        
        for y in range(0, h, step):
            for x in range(0, w, step):
                fx, fy = flow[y, x]
                magnitude = math.sqrt(fx**2 + fy**2)
                
                if magnitude > threshold:
                    start = Point(x / w, y / h)
                    end = Point((x + fx) / w, (y + fy) / h)
                    vectors.append((start, end))
        
        return vectors
    
    def get_dominant_direction(self, flow: np.ndarray) -> Tuple[float, float]:
        """Get dominant motion direction."""
        if flow is None:
            return (0, 0)
        
        avg_fx = np.mean(flow[:, :, 0])
        avg_fy = np.mean(flow[:, :, 1])
        
        return (avg_fx, avg_fy)
    
    def reset(self):
        """Reset flow state."""
        self._prev_gray = None


# ============================================================================
# Convenience Functions
# ============================================================================

_tracker: Optional[MultiObjectTracker] = None
_motion_extractor: Optional[MotionRegionExtractor] = None
_flow_analyzer: Optional[OpticalFlowAnalyzer] = None


def get_tracker(**kwargs) -> MultiObjectTracker:
    """Get or create tracker."""
    global _tracker
    if _tracker is None:
        _tracker = MultiObjectTracker(**kwargs)
    return _tracker


def get_motion_extractor(**kwargs) -> MotionRegionExtractor:
    """Get or create motion extractor."""
    global _motion_extractor
    if _motion_extractor is None:
        _motion_extractor = MotionRegionExtractor(**kwargs)
    return _motion_extractor


def get_flow_analyzer(**kwargs) -> OpticalFlowAnalyzer:
    """Get or create optical flow analyzer."""
    global _flow_analyzer
    if _flow_analyzer is None:
        _flow_analyzer = OpticalFlowAnalyzer(**kwargs)
    return _flow_analyzer
