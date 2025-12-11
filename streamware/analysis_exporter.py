"""
Analysis Exporter - Export live narrator results to SVG animation

Integrates motion tracking with live narrator to produce
interactive HTML visualizations of video stream analysis.
"""

import logging
import time
import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FrameAnalysisData:
    """Data for a single analyzed frame."""
    frame_num: int
    timestamp: float
    frame_path: Optional[Path] = None
    detections: List[Dict] = None
    motion_percent: float = 0.0
    description: str = ""
    has_person: bool = False
    
    def __post_init__(self):
        if self.detections is None:
            self.detections = []


class AnalysisExporter:
    """
    Exports live narrator analysis to various formats.
    
    Integrates with:
    - SVG Visualizer for animated HTML output
    - Motion Tracker for trajectory visualization
    - DSL for custom analysis pipelines
    """
    
    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        include_background: bool = False,
    ):
        self.width = width
        self.height = height
        self.include_background = include_background
        
        self.frames: List[FrameAnalysisData] = []
        self._converter = None
        self._tracker = None
    
    def _ensure_converter(self):
        """Lazy initialize converter."""
        if self._converter is None:
            from .svg_visualizer import VideoToSVGConverter
            self._converter = VideoToSVGConverter(
                width=self.width,
                height=self.height,
                include_background=self.include_background,
            )
    
    def _ensure_tracker(self):
        """Lazy initialize tracker."""
        if self._tracker is None:
            from .motion_tracker import MultiObjectTracker
            self._tracker = MultiObjectTracker()
    
    def _resize_and_encode_frame(self, frame_path: Path, max_size: int = 128) -> str:
        """Resize frame to max_size and encode as base64.
        
        Args:
            frame_path: Path to frame image
            max_size: Maximum dimension (width or height)
            
        Returns:
            Base64 encoded JPEG string
        """
        try:
            import cv2
            img = cv2.imread(str(frame_path))
            if img is None:
                return ""
            
            # Calculate new size maintaining aspect ratio
            h, w = img.shape[:2]
            if w > h:
                new_w = max_size
                new_h = int(h * max_size / w)
            else:
                new_h = max_size
                new_w = int(w * max_size / h)
            
            # Resize
            resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            # Encode to JPEG
            _, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 70])
            return base64.b64encode(buffer).decode()
            
        except ImportError:
            # Fallback: read original file
            with open(frame_path, 'rb') as f:
                return base64.b64encode(f.read()).decode()
    
    def add_frame(
        self,
        frame_num: int,
        frame_path: Path = None,
        detections: List[Dict] = None,
        motion_percent: float = 0.0,
        description: str = "",
        yolo_detections: List = None,
    ):
        """
        Add analyzed frame.
        
        Args:
            frame_num: Frame number
            frame_path: Path to frame image
            detections: List of detection dicts
            motion_percent: Motion percentage
            description: LLM description
            yolo_detections: Raw YOLO detections
        """
        self._ensure_converter()
        self._ensure_tracker()
        
        # Convert YOLO detections to tracking format
        if yolo_detections:
            from .motion_tracker import BoundingBox
            boxes = []
            for det in yolo_detections:
                if hasattr(det, 'x'):
                    boxes.append(BoundingBox(
                        x=det.x, y=det.y, w=det.w, h=det.h,
                        confidence=getattr(det, 'confidence', 0.5),
                        class_name=getattr(det, 'class_name', 'object')
                    ))
                elif isinstance(det, dict):
                    boxes.append(BoundingBox(
                        x=det.get('x', 0), y=det.get('y', 0),
                        w=det.get('w', 0.1), h=det.get('h', 0.1),
                        confidence=det.get('confidence', 0.5),
                        class_name=det.get('class_name', det.get('type', 'object'))
                    ))
            
            # Run tracking
            tracked = self._tracker.update(boxes)
            
            # Convert to dict format
            detections = [
                {
                    'id': t.id,
                    'x': t.bbox.x,
                    'y': t.bbox.y,
                    'w': t.bbox.w,
                    'h': t.bbox.h,
                    'class_name': t.class_name,
                    'velocity': (t.velocity.x, t.velocity.y),
                }
                for t in tracked
            ]
        
        detections = detections or []
        
        # Check for person
        has_person = any(
            d.get('class_name', '').lower() in ('person', 'human', 'man', 'woman')
            for d in detections
        ) or 'person' in description.lower()
        
        # Store frame data
        frame_data = FrameAnalysisData(
            frame_num=frame_num,
            timestamp=time.time(),
            frame_path=frame_path,
            detections=detections,
            motion_percent=motion_percent,
            description=description,
            has_person=has_person,
        )
        self.frames.append(frame_data)
        
        # Add to SVG converter (resize background to 128px for smaller file size)
        background_b64 = ""
        if self.include_background and frame_path and frame_path.exists():
            try:
                background_b64 = self._resize_and_encode_frame(frame_path, max_size=128)
            except (OSError, IOError):
                pass
        
        self._converter.add_frame(
            frame_num=frame_num,
            timestamp=frame_data.timestamp,
            detections=detections,
            background_base64=background_b64,
        )
    
    def export_html(
        self,
        output_path: str = "analysis.html",
        title: str = "Video Stream Analysis",
        fps: float = 2.0,
    ) -> Path:
        """
        Export analysis to interactive HTML.
        
        Args:
            output_path: Output file path
            title: Page title
            fps: Animation FPS
            
        Returns:
            Path to generated HTML
        """
        self._ensure_converter()
        
        output = Path(output_path)
        return self._converter.generate_html_animation(
            output, fps=fps, title=title
        )
    
    def export_json(self, output_path: str = "analysis.json") -> Path:
        """Export analysis to JSON."""
        import json
        
        data = {
            "metadata": {
                "total_frames": len(self.frames),
                "width": self.width,
                "height": self.height,
                "exported_at": datetime.now().isoformat(),
            },
            "frames": [
                {
                    "frame_num": f.frame_num,
                    "timestamp": f.timestamp,
                    "detections": f.detections,
                    "motion_percent": f.motion_percent,
                    "description": f.description,
                    "has_person": f.has_person,
                }
                for f in self.frames
            ],
            "trajectories": dict(self._converter.trajectories) if self._converter else {},
        }
        
        output = Path(output_path)
        output.write_text(json.dumps(data, indent=2, default=str))
        return output
    
    def export_summary(self) -> Dict:
        """Get analysis summary."""
        if not self.frames:
            return {"frames": 0}
        
        person_frames = sum(1 for f in self.frames if f.has_person)
        motion_frames = sum(1 for f in self.frames if f.motion_percent > 1.0)
        
        return {
            "total_frames": len(self.frames),
            "person_detected_frames": person_frames,
            "motion_frames": motion_frames,
            "person_detection_rate": person_frames / len(self.frames),
            "avg_motion_percent": sum(f.motion_percent for f in self.frames) / len(self.frames),
            "objects_tracked": len(self._converter.trajectories) if self._converter else 0,
        }
    
    def reset(self):
        """Reset exporter state."""
        self.frames.clear()
        if self._converter:
            self._converter.reset()
        if self._tracker:
            self._tracker.reset()


# Global exporter instance
_exporter: Optional[AnalysisExporter] = None


def get_exporter(**kwargs) -> AnalysisExporter:
    """Get or create global exporter."""
    global _exporter
    if _exporter is None:
        _exporter = AnalysisExporter(**kwargs)
    return _exporter


def export_to_html(
    frames_data: List[Dict],
    output_path: str = "analysis.html",
    title: str = "Video Analysis",
    fps: float = 2.0,
) -> Path:
    """
    Convenience function to export frame data to HTML.
    
    Args:
        frames_data: List of frame dictionaries
        output_path: Output file path
        title: Page title
        fps: Animation FPS
        
    Returns:
        Path to generated HTML
    """
    exporter = AnalysisExporter()
    
    for frame in frames_data:
        exporter.add_frame(
            frame_num=frame.get('frame_num', 0),
            detections=frame.get('detections', []),
            motion_percent=frame.get('motion_percent', 0),
            description=frame.get('description', ''),
        )
    
    return exporter.export_html(output_path, title, fps)
