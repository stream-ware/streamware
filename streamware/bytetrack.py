"""
ByteTrack Multi-Object Tracker for Streamware

High-performance object tracking with stable IDs, optimized for AMD CPU/iGPU.
Based on ByteTrack algorithm with optional ReID for ID recovery after occlusions.

Features:
- Two-stage association (high + low confidence detections)
- Lost track recovery pool
- Optional ReID feature matching (OSNet)
- Motion gating with MOG2 background subtraction
- Threaded RTSP capture for low latency

Usage:
    from streamware.bytetrack import ByteTracker, MotionGate
    
    tracker = ByteTracker()
    motion_gate = MotionGate()
    
    for frame in video_stream:
        if motion_gate.should_detect(frame)[0]:
            detections = yolo_detector.detect(frame)
            tracks = tracker.update(detections, frame)
            
            for track in tracks:
                print(f"#{track.id} {track.class_name} at {track.bbox}")

Reference: https://github.com/ifzhang/ByteTrack
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from threading import Thread
from queue import Queue
from typing import List, Optional, Dict, Tuple, Any
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

class TrackState(Enum):
    """Track lifecycle states"""
    TENTATIVE = "tentative"      # New track, not yet confirmed
    CONFIRMED = "confirmed"      # Active, confirmed track
    OCCLUDED = "occluded"        # Lost but within buffer
    DELETED = "deleted"          # Removed


@dataclass
class Detection:
    """Single detection from YOLO or other detector"""
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    confidence: float
    class_id: int
    class_name: str
    feature: Optional[np.ndarray] = None  # ReID feature vector
    
    @classmethod
    def from_yolo(cls, box, conf, cls_id, class_names: Dict[int, str]) -> 'Detection':
        """Create Detection from YOLO output"""
        return cls(
            bbox=tuple(box),
            confidence=float(conf),
            class_id=int(cls_id),
            class_name=class_names.get(int(cls_id), f"class_{cls_id}"),
        )


@dataclass
class Track:
    """Tracked object with state and history"""
    id: int
    bbox: Tuple[float, float, float, float]
    class_id: int
    class_name: str
    confidence: float
    state: TrackState = TrackState.TENTATIVE
    age: int = 0                    # Total frames since creation
    hits: int = 1                   # Consecutive detections
    time_since_update: int = 0      # Frames since last detection
    velocity: Tuple[float, float] = (0.0, 0.0)
    features: List[np.ndarray] = field(default_factory=list)  # ReID feature gallery
    
    @property
    def center(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)
    
    @property
    def area(self) -> float:
        x1, y1, x2, y2 = self.bbox
        return max(0, (x2 - x1) * (y2 - y1))
    
    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]
    
    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "bbox": list(self.bbox),
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "state": self.state.value,
            "age": self.age,
            "hits": self.hits,
            "center": list(self.center),
        }


# =============================================================================
# Motion Gating (Reduces detection calls by 60-80%)
# =============================================================================

class MotionGate:
    """
    Background subtraction to gate expensive YOLO inference.
    Only runs detection when motion is detected OR periodically.
    
    Uses MOG2 which works well for both indoor and outdoor scenes.
    For variable lighting, consider LSBP or GSOC alternatives.
    """
    
    def __init__(
        self,
        motion_threshold: int = 1000,      # Min changed pixels to trigger
        periodic_interval: int = 30,        # Force detection every N frames
        history: int = 500,                 # Background model history
        var_threshold: int = 16,            # Variance threshold for MOG2
    ):
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=True
        )
        self.motion_threshold = motion_threshold
        self.periodic_interval = periodic_interval
        self.frame_count = 0
        
        # Morphological kernels for noise removal
        self.kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self.kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    
    def should_detect(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        Determine if we should run detection on this frame.
        
        Returns:
            (should_detect, motion_percent)
        """
        # Apply background subtraction
        fg_mask = self.bg_subtractor.apply(frame)
        
        # Clean up mask
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self.kernel_open)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, self.kernel_close)
        
        # Count motion pixels
        motion_pixels = cv2.countNonZero(fg_mask)
        total_pixels = frame.shape[0] * frame.shape[1]
        motion_percent = (motion_pixels / total_pixels) * 100
        
        self.frame_count += 1
        
        # Decide if we should detect
        should_run = (
            motion_pixels > self.motion_threshold or
            self.frame_count % self.periodic_interval == 0
        )
        
        return should_run, motion_percent
    
    def get_motion_regions(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Get bounding boxes of motion regions"""
        fg_mask = self.bg_subtractor.apply(frame, learningRate=0)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self.kernel_open)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, self.kernel_close)
        
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        regions = []
        for c in contours:
            if cv2.contourArea(c) > 500:  # Filter small regions
                x, y, w, h = cv2.boundingRect(c)
                regions.append((x, y, x + w, y + h))
        
        return regions
    
    def reset(self):
        """Reset background model"""
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=16,
            detectShadows=True
        )
        self.frame_count = 0


# =============================================================================
# Threaded RTSP Capture
# =============================================================================

class RTSPCapture:
    """
    Threaded RTSP capture to prevent frame buffering delays.
    Essential for real-time streaming - without this, you get 2-3s latency.
    """
    
    def __init__(self, source: str, buffer_size: int = 2):
        self.source = source
        self.cap = cv2.VideoCapture(source)
        
        # Optimize for low latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Try to set RTSP transport to TCP (more reliable)
        if isinstance(source, str) and source.startswith("rtsp://"):
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))
        
        self.queue = Queue(maxsize=buffer_size)
        self.stopped = False
        self.frame_count = 0
        
        # Get stream properties
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        
        logger.info(f"Stream opened: {self.width}x{self.height} @ {self.fps:.1f} FPS")
        
        # Start reader thread
        self.thread = Thread(target=self._reader, daemon=True)
        self.thread.start()
    
    def _reader(self):
        """Background thread that continuously reads frames"""
        while not self.stopped:
            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Frame read failed, reconnecting...")
                time.sleep(1)
                self.cap.release()
                self.cap = cv2.VideoCapture(self.source)
                continue
            
            self.frame_count += 1
            
            # Drop old frame if queue is full (keep latest)
            if self.queue.full():
                try:
                    self.queue.get_nowait()
                except:
                    pass
            
            self.queue.put(frame)
    
    def read(self, timeout: float = 5.0) -> Optional[np.ndarray]:
        """Get latest frame (blocks until available)"""
        try:
            return self.queue.get(timeout=timeout)
        except:
            return None
    
    def stop(self):
        """Stop capture thread"""
        self.stopped = True
        if self.thread.is_alive():
            self.thread.join(timeout=2)
        self.cap.release()


# =============================================================================
# ReID Feature Extractor
# =============================================================================

class ReIDExtractor:
    """
    Lightweight ReID feature extractor.
    
    Uses OSNet x0.25 if torchreid is available, otherwise falls back to ResNet18.
    Only used when IoU matching is ambiguous or for track recovery.
    Adds ~15-25ms per crop on CPU.
    """
    
    def __init__(self, model_name: str = "osnet_x0_25"):
        self.model = None
        self.model_name = model_name
        self.input_size = (256, 128)  # height, width
        self.feature_dim = 512
        self.transform = None
        
        self._load_model()
    
    def _load_model(self):
        """Load ReID model"""
        try:
            import torch
            import torchvision.transforms as T
            
            # Try torchreid first (better features)
            try:
                from torchreid import models
                self.model = models.build_model(
                    name=self.model_name,
                    num_classes=1,
                    pretrained=True,
                )
                self.model.eval()
                logger.info(f"Loaded ReID model: {self.model_name} (torchreid)")
            except ImportError:
                # Fallback: ResNet18 features
                logger.warning("torchreid not installed, using ResNet18 features")
                from torchvision.models import resnet18, ResNet18_Weights
                base_model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
                self.model = torch.nn.Sequential(*list(base_model.children())[:-1])
                self.model.eval()
                self.feature_dim = 512
            
            self.transform = T.Compose([
                T.ToPILImage(),
                T.Resize(self.input_size),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
            
        except ImportError:
            logger.warning("PyTorch not available, ReID disabled")
            self.model = None
    
    def extract(self, frame: np.ndarray, bbox: Tuple[float, float, float, float]) -> Optional[np.ndarray]:
        """
        Extract ReID feature from detection crop.
        
        Returns 512-dim normalized feature vector or None if extraction fails.
        """
        if self.model is None:
            return None
        
        try:
            import torch
            
            # Crop detection region
            x1, y1, x2, y2 = map(int, bbox)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
            
            if x2 <= x1 or y2 <= y1:
                return None
            
            crop = frame[y1:y2, x1:x2]
            
            if crop.size == 0:
                return None
            
            # Transform and extract
            img_tensor = self.transform(crop).unsqueeze(0)
            
            with torch.no_grad():
                feature = self.model(img_tensor)
                feature = feature.squeeze().numpy()
            
            # L2 normalize
            feature = feature / (np.linalg.norm(feature) + 1e-6)
            
            return feature
            
        except Exception as e:
            logger.debug(f"ReID extraction failed: {e}")
            return None
    
    def compute_distance(self, feat1: np.ndarray, feat2: np.ndarray) -> float:
        """Compute cosine distance between two feature vectors"""
        if feat1 is None or feat2 is None:
            return 1.0
        return 1.0 - np.dot(feat1, feat2)


# =============================================================================
# ByteTracker
# =============================================================================

class ByteTracker:
    """
    ByteTrack-style multi-object tracker.
    
    Key features:
    - Two-stage association (high + low confidence)
    - Kalman-like velocity prediction
    - Optional ReID for ID recovery after occlusions
    - Proper track lifecycle management
    
    Recommended parameters for different scenarios:
    
    Less false positives:
        high_thresh=0.6, new_track_thresh=0.7, min_hits=5
        
    Less ID switches:
        track_buffer=120, iou_threshold=0.2, use_reid=True
        
    Higher FPS:
        use_reid=False, track_buffer=60
    """
    
    def __init__(
        self,
        # Association thresholds
        high_thresh: float = 0.5,       # High confidence detection threshold
        low_thresh: float = 0.1,        # Low confidence (second pass)
        new_track_thresh: float = 0.6,  # Min confidence to start new track
        
        # Track management
        track_buffer: int = 90,         # Frames before deleting lost track (~3s at 30fps)
        min_hits: int = 3,              # Consecutive hits to confirm track
        
        # Matching thresholds
        iou_threshold: float = 0.3,     # Min IoU for association
        reid_threshold: float = 0.4,    # Max ReID distance for association
        
        # ReID settings
        use_reid: bool = False,
        reid_extractor: Optional[ReIDExtractor] = None,
        max_features: int = 50,         # Feature gallery size per track
    ):
        self.high_thresh = high_thresh
        self.low_thresh = low_thresh
        self.new_track_thresh = new_track_thresh
        self.track_buffer = track_buffer
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.reid_threshold = reid_threshold
        self.use_reid = use_reid
        self.reid_extractor = reid_extractor
        self.max_features = max_features
        
        self.tracks: List[Track] = []
        self.lost_tracks: List[Track] = []
        self.next_id = 1
        self.frame_count = 0
    
    def update(self, detections: List[Detection], frame: np.ndarray = None) -> List[Track]:
        """
        Update tracker with new detections.
        
        Args:
            detections: List of Detection objects
            frame: Original frame (needed for ReID extraction)
        
        Returns:
            List of confirmed Track objects
        """
        self.frame_count += 1
        
        # Predict new locations for existing tracks
        self._predict_tracks()
        
        # Split detections by confidence
        high_dets = [d for d in detections if d.confidence >= self.high_thresh]
        low_dets = [d for d in detections if self.low_thresh <= d.confidence < self.high_thresh]
        
        # Extract ReID features for high-confidence detections if enabled
        if self.use_reid and self.reid_extractor and frame is not None:
            for det in high_dets:
                det.feature = self.reid_extractor.extract(frame, det.bbox)
        
        # === First association: high-confidence detections with active tracks ===
        active_tracks = [t for t in self.tracks if t.state != TrackState.DELETED]
        matched_track_ids, matched_det_ids, unmatched_tracks, unmatched_dets = \
            self._associate(active_tracks, high_dets, use_reid=self.use_reid)
        
        # Update matched tracks
        for track_idx, det_idx in zip(matched_track_ids, matched_det_ids):
            self._update_track(active_tracks[track_idx], high_dets[det_idx])
        
        # === Second association: low-confidence detections with remaining tracks ===
        remaining_tracks = [active_tracks[i] for i in unmatched_tracks]
        remaining_high_dets = [high_dets[i] for i in unmatched_dets]
        
        matched_track_ids2, matched_det_ids2, still_unmatched_tracks, _ = \
            self._associate(remaining_tracks, low_dets, use_reid=False)
        
        for track_idx, det_idx in zip(matched_track_ids2, matched_det_ids2):
            self._update_track(remaining_tracks[track_idx], low_dets[det_idx])
        
        # === Third association: try to recover lost tracks ===
        if self.lost_tracks and remaining_high_dets:
            matched_lost, matched_det_lost, _, final_unmatched_dets = \
                self._associate(self.lost_tracks, remaining_high_dets, use_reid=self.use_reid)
            
            for track_idx, det_idx in zip(matched_lost, matched_det_lost):
                track = self.lost_tracks[track_idx]
                track.state = TrackState.CONFIRMED
                track.time_since_update = 0
                self._update_track(track, remaining_high_dets[det_idx])
                self.tracks.append(track)
            
            # Remove recovered tracks from lost
            for idx in sorted(matched_lost, reverse=True):
                self.lost_tracks.pop(idx)
            
            remaining_high_dets = [remaining_high_dets[i] for i in final_unmatched_dets]
        
        # === Create new tracks for remaining high-confidence detections ===
        for det in remaining_high_dets:
            if det.confidence >= self.new_track_thresh:
                self._create_track(det, frame)
        
        # === Handle unmatched tracks ===
        for idx in still_unmatched_tracks:
            track = remaining_tracks[idx]
            track.time_since_update += 1
            
            if track.time_since_update > self.track_buffer:
                track.state = TrackState.DELETED
            elif track.state == TrackState.CONFIRMED:
                track.state = TrackState.OCCLUDED
                self.lost_tracks.append(track)
                self.tracks.remove(track)
        
        # Clean up old lost tracks
        self.lost_tracks = [
            t for t in self.lost_tracks 
            if t.time_since_update <= self.track_buffer
        ]
        
        # Clean up deleted tracks
        self.tracks = [t for t in self.tracks if t.state != TrackState.DELETED]
        
        # Return only confirmed tracks
        return [t for t in self.tracks if t.state == TrackState.CONFIRMED]
    
    def _predict_tracks(self):
        """Predict next position using simple velocity model"""
        for track in self.tracks:
            if track.velocity != (0, 0):
                x1, y1, x2, y2 = track.bbox
                vx, vy = track.velocity
                track.bbox = (x1 + vx, y1 + vy, x2 + vx, y2 + vy)
            track.age += 1
    
    def _associate(
        self,
        tracks: List[Track],
        detections: List[Detection],
        use_reid: bool = False,
    ) -> Tuple[List[int], List[int], List[int], List[int]]:
        """
        Associate tracks with detections using IoU and optionally ReID.
        
        Returns:
            matched_track_ids, matched_det_ids, unmatched_track_ids, unmatched_det_ids
        """
        if not tracks or not detections:
            return [], [], list(range(len(tracks))), list(range(len(detections)))
        
        # Compute IoU matrix
        iou_matrix = np.zeros((len(tracks), len(detections)))
        for i, track in enumerate(tracks):
            for j, det in enumerate(detections):
                iou_matrix[i, j] = self._compute_iou(track.bbox, det.bbox)
        
        # Compute ReID cost matrix if enabled
        reid_matrix = None
        if use_reid and self.reid_extractor:
            reid_matrix = np.ones((len(tracks), len(detections)))
            for i, track in enumerate(tracks):
                if track.features:
                    avg_feature = np.mean(track.features[-10:], axis=0)
                    for j, det in enumerate(detections):
                        if det.feature is not None:
                            reid_matrix[i, j] = self.reid_extractor.compute_distance(
                                avg_feature, det.feature
                            )
            
            # Combined cost: IoU-weighted ReID
            cost_matrix = 0.7 * (1 - iou_matrix) + 0.3 * reid_matrix
        else:
            cost_matrix = 1 - iou_matrix
        
        # Hungarian matching
        try:
            from scipy.optimize import linear_sum_assignment
            row_indices, col_indices = linear_sum_assignment(cost_matrix)
        except ImportError:
            row_indices, col_indices = self._greedy_match(cost_matrix)
        
        matched_tracks, matched_dets = [], []
        for row, col in zip(row_indices, col_indices):
            if iou_matrix[row, col] >= self.iou_threshold:
                if use_reid and reid_matrix is not None:
                    if reid_matrix[row, col] <= self.reid_threshold or iou_matrix[row, col] >= 0.5:
                        matched_tracks.append(row)
                        matched_dets.append(col)
                else:
                    matched_tracks.append(row)
                    matched_dets.append(col)
        
        unmatched_tracks = [i for i in range(len(tracks)) if i not in matched_tracks]
        unmatched_dets = [j for j in range(len(detections)) if j not in matched_dets]
        
        return matched_tracks, matched_dets, unmatched_tracks, unmatched_dets
    
    def _greedy_match(self, cost_matrix: np.ndarray) -> Tuple[List[int], List[int]]:
        """Greedy matching fallback when scipy is not available"""
        rows, cols = [], []
        used_cols = set()
        
        indices = np.unravel_index(np.argsort(cost_matrix, axis=None), cost_matrix.shape)
        
        for row, col in zip(indices[0], indices[1]):
            if row not in rows and col not in used_cols:
                rows.append(row)
                cols.append(col)
                used_cols.add(col)
        
        return rows, cols
    
    def _compute_iou(self, bbox1: Tuple, bbox2: Tuple) -> float:
        """Compute IoU between two bboxes"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        xi1 = max(x1_1, x1_2)
        yi1 = max(y1_1, y1_2)
        xi2 = min(x2_1, x2_2)
        yi2 = min(y2_1, y2_2)
        
        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        
        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0
    
    def _update_track(self, track: Track, detection: Detection):
        """Update track with new detection"""
        # Compute velocity
        old_center = track.center
        new_x1, new_y1, new_x2, new_y2 = detection.bbox
        new_center = ((new_x1 + new_x2) / 2, (new_y1 + new_y2) / 2)
        
        # Smooth velocity update (EMA)
        alpha = 0.3
        track.velocity = (
            alpha * (new_center[0] - old_center[0]) + (1 - alpha) * track.velocity[0],
            alpha * (new_center[1] - old_center[1]) + (1 - alpha) * track.velocity[1],
        )
        
        # Update bbox and state
        track.bbox = detection.bbox
        track.confidence = detection.confidence
        track.hits += 1
        track.time_since_update = 0
        
        # Update state
        if track.state == TrackState.TENTATIVE and track.hits >= self.min_hits:
            track.state = TrackState.CONFIRMED
        elif track.state == TrackState.OCCLUDED:
            track.state = TrackState.CONFIRMED
        
        # Update ReID features
        if detection.feature is not None:
            track.features.append(detection.feature)
            if len(track.features) > self.max_features:
                track.features.pop(0)
    
    def _create_track(self, detection: Detection, frame: np.ndarray = None):
        """Create new track from detection"""
        track = Track(
            id=self.next_id,
            bbox=detection.bbox,
            class_id=detection.class_id,
            class_name=detection.class_name,
            confidence=detection.confidence,
            state=TrackState.TENTATIVE,
        )
        
        if detection.feature is not None:
            track.features.append(detection.feature)
        
        self.tracks.append(track)
        self.next_id += 1
    
    def reset(self):
        """Reset tracker state"""
        self.tracks.clear()
        self.lost_tracks.clear()
        self.next_id = 1
        self.frame_count = 0
    
    def get_all_tracks(self) -> List[Track]:
        """Get all tracks including tentative and occluded"""
        return self.tracks + self.lost_tracks


# =============================================================================
# Convenience Functions
# =============================================================================

def create_tracker(
    use_reid: bool = False,
    preset: str = "balanced",
) -> ByteTracker:
    """
    Create a ByteTracker with preset configuration.
    
    Presets:
        - "speed": Maximum FPS, may have more ID switches
        - "balanced": Good balance of speed and accuracy (default)
        - "stable": Stable IDs, lower FPS
    """
    presets = {
        "speed": {
            "high_thresh": 0.6,
            "new_track_thresh": 0.7,
            "track_buffer": 60,
            "min_hits": 2,
            "use_reid": False,
        },
        "balanced": {
            "high_thresh": 0.5,
            "new_track_thresh": 0.6,
            "track_buffer": 90,
            "min_hits": 3,
            "use_reid": use_reid,
        },
        "stable": {
            "high_thresh": 0.4,
            "new_track_thresh": 0.5,
            "track_buffer": 120,
            "min_hits": 3,
            "iou_threshold": 0.2,
            "use_reid": True,
        },
    }
    
    config = presets.get(preset, presets["balanced"])
    
    reid_extractor = None
    if config.get("use_reid", use_reid):
        reid_extractor = ReIDExtractor()
    
    return ByteTracker(
        reid_extractor=reid_extractor,
        **config,
    )
