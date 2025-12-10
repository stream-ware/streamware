"""
Motion Analysis DSL - Domain Specific Language for Video Stream Analysis

A declarative language for orchestrating motion detection, object tracking,
and SVG visualization pipelines.

DSL Syntax:
-----------
# Comments start with #

# Define source
SOURCE rtsp://camera/stream
# or
SOURCE /path/to/video.mp4

# Detection configuration  
DETECT person, vehicle USING yolo WITH confidence=0.5

# Tracking configuration
TRACK WITH kalman, hungarian PARAMS max_age=30, min_hits=3

# Motion extraction
EXTRACT motion WITH background_subtraction PARAMS history=50

# Focus on motion regions
FOCUS ON motion_regions WITH padding=0.1

# SVG conversion
CONVERT TO svg SIZE 800x600

# Animation output
ANIMATE AT 2fps DURATION 60s
OUTPUT TO analysis.html

# Mathematical analysis
ANALYZE velocity, acceleration, trajectory
MATRIX representation=polar

Example Usage:
--------------
    from streamware.motion_dsl import MotionDSL
    
    dsl = MotionDSL()
    dsl.load('''
        SOURCE rtsp://camera/stream
        DETECT person USING yolo
        TRACK WITH kalman
        CONVERT TO svg
        OUTPUT TO analysis.html
    ''')
    result = dsl.execute()
"""

import logging
import re
import time
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
import json

logger = logging.getLogger(__name__)


# ============================================================================
# DSL Token Types
# ============================================================================

class TokenType(Enum):
    SOURCE = "SOURCE"
    DETECT = "DETECT"
    TRACK = "TRACK"
    EXTRACT = "EXTRACT"
    FOCUS = "FOCUS"
    CONVERT = "CONVERT"
    ANIMATE = "ANIMATE"
    OUTPUT = "OUTPUT"
    ANALYZE = "ANALYZE"
    MATRIX = "MATRIX"
    FILTER = "FILTER"
    TRANSFORM = "TRANSFORM"
    
    # Modifiers
    USING = "USING"
    WITH = "WITH"
    PARAMS = "PARAMS"
    TO = "TO"
    ON = "ON"
    AT = "AT"
    SIZE = "SIZE"
    DURATION = "DURATION"
    

@dataclass
class DSLCommand:
    """Parsed DSL command."""
    command: TokenType
    target: str = ""
    modifier: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    raw: str = ""


# ============================================================================
# DSL Parser
# ============================================================================

class DSLParser:
    """Parser for Motion Analysis DSL."""
    
    def __init__(self):
        self.commands: List[DSLCommand] = []
    
    def parse(self, script: str) -> List[DSLCommand]:
        """Parse DSL script into commands."""
        self.commands = []
        
        lines = script.strip().split('\n')
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            try:
                cmd = self._parse_line(line)
                if cmd:
                    self.commands.append(cmd)
            except Exception as e:
                logger.warning(f"DSL parse error at line {line_num}: {e}")
        
        return self.commands
    
    def _parse_line(self, line: str) -> Optional[DSLCommand]:
        """Parse single DSL line."""
        # Tokenize
        tokens = line.split()
        if not tokens:
            return None
        
        cmd_str = tokens[0].upper()
        
        # Try to match command type
        try:
            cmd_type = TokenType(cmd_str)
        except ValueError:
            logger.warning(f"Unknown DSL command: {cmd_str}")
            return None
        
        cmd = DSLCommand(command=cmd_type, raw=line)
        
        # Parse rest of line based on command type
        rest = ' '.join(tokens[1:])
        
        if cmd_type == TokenType.SOURCE:
            cmd.target = rest
            
        elif cmd_type == TokenType.DETECT:
            # DETECT person, vehicle USING yolo WITH confidence=0.5
            parts = re.split(r'\s+USING\s+|\s+WITH\s+', rest, flags=re.IGNORECASE)
            cmd.target = parts[0].strip()
            if len(parts) > 1:
                cmd.modifier = parts[1].strip()
            if len(parts) > 2:
                cmd.params = self._parse_params(parts[2])
                
        elif cmd_type == TokenType.TRACK:
            # TRACK WITH kalman, hungarian PARAMS max_age=30
            parts = re.split(r'\s+WITH\s+|\s+PARAMS\s+', rest, flags=re.IGNORECASE)
            if parts:
                cmd.modifier = parts[0].strip() if parts[0] else ""
            if len(parts) > 1:
                cmd.modifier = parts[1].strip()
            if len(parts) > 2:
                cmd.params = self._parse_params(parts[2])
                
        elif cmd_type == TokenType.EXTRACT:
            # EXTRACT motion WITH background_subtraction
            parts = re.split(r'\s+WITH\s+|\s+PARAMS\s+', rest, flags=re.IGNORECASE)
            cmd.target = parts[0].strip()
            if len(parts) > 1:
                cmd.modifier = parts[1].strip()
            if len(parts) > 2:
                cmd.params = self._parse_params(parts[2])
                
        elif cmd_type == TokenType.FOCUS:
            # FOCUS ON motion_regions WITH padding=0.1
            parts = re.split(r'\s+ON\s+|\s+WITH\s+', rest, flags=re.IGNORECASE)
            if len(parts) > 1:
                cmd.target = parts[1].strip()
            if len(parts) > 2:
                cmd.params = self._parse_params(parts[2])
                
        elif cmd_type == TokenType.CONVERT:
            # CONVERT TO svg SIZE 800x600
            parts = re.split(r'\s+TO\s+|\s+SIZE\s+', rest, flags=re.IGNORECASE)
            if len(parts) > 1:
                cmd.target = parts[1].strip()
            if len(parts) > 2:
                size_match = re.match(r'(\d+)x(\d+)', parts[2].strip())
                if size_match:
                    cmd.params['width'] = int(size_match.group(1))
                    cmd.params['height'] = int(size_match.group(2))
                    
        elif cmd_type == TokenType.ANIMATE:
            # ANIMATE AT 2fps DURATION 60s
            fps_match = re.search(r'(\d+(?:\.\d+)?)\s*fps', rest, re.IGNORECASE)
            if fps_match:
                cmd.params['fps'] = float(fps_match.group(1))
            dur_match = re.search(r'DURATION\s+(\d+)\s*s', rest, re.IGNORECASE)
            if dur_match:
                cmd.params['duration'] = int(dur_match.group(1))
                
        elif cmd_type == TokenType.OUTPUT:
            # OUTPUT TO analysis.html
            parts = re.split(r'\s+TO\s+', rest, flags=re.IGNORECASE)
            if len(parts) > 1:
                cmd.target = parts[1].strip()
            else:
                cmd.target = rest.strip()
                
        elif cmd_type == TokenType.ANALYZE:
            # ANALYZE velocity, acceleration, trajectory
            cmd.target = rest
            
        elif cmd_type == TokenType.MATRIX:
            # MATRIX representation=polar
            cmd.params = self._parse_params(rest)
            
        elif cmd_type == TokenType.FILTER:
            # FILTER confidence > 0.5
            cmd.target = rest
            
        elif cmd_type == TokenType.TRANSFORM:
            # TRANSFORM normalize, scale=2
            parts = rest.split(',')
            cmd.target = parts[0].strip()
            if len(parts) > 1:
                cmd.params = self._parse_params(','.join(parts[1:]))
        
        return cmd
    
    def _parse_params(self, param_str: str) -> Dict[str, Any]:
        """Parse parameter string like 'key1=val1, key2=val2'."""
        params = {}
        
        # Split by comma
        for part in param_str.split(','):
            part = part.strip()
            if '=' in part:
                key, val = part.split('=', 1)
                key = key.strip()
                val = val.strip()
                
                # Try to convert value
                try:
                    if '.' in val:
                        params[key] = float(val)
                    else:
                        params[key] = int(val)
                except ValueError:
                    if val.lower() in ('true', 'false'):
                        params[key] = val.lower() == 'true'
                    else:
                        params[key] = val
        
        return params


# ============================================================================
# DSL Executor
# ============================================================================

class MotionDSL:
    """
    Motion Analysis DSL Executor.
    
    Executes parsed DSL commands to build and run analysis pipeline.
    """
    
    def __init__(self):
        self.parser = DSLParser()
        self.commands: List[DSLCommand] = []
        
        # Pipeline state
        self.source = None
        self.detector = None
        self.tracker = None
        self.extractor = None
        self.converter = None
        self.output_path = "analysis.html"
        self.fps = 2.0
        self.duration = 60
        self.width = 800
        self.height = 600
        
        # Analysis state
        self.frames_data: List[Dict] = []
        self.analysis_results: Dict = {}
    
    def load(self, script: str) -> 'MotionDSL':
        """Load and parse DSL script."""
        self.commands = self.parser.parse(script)
        return self
    
    def load_file(self, path: Path) -> 'MotionDSL':
        """Load DSL from file."""
        script = Path(path).read_text()
        return self.load(script)
    
    def execute(self, frames: List[Path] = None) -> Dict:
        """
        Execute DSL pipeline.
        
        Args:
            frames: Optional list of frame paths to process
            
        Returns:
            Dict with results and output path
        """
        # Process commands to configure pipeline
        for cmd in self.commands:
            self._execute_command(cmd)
        
        # If frames provided, process them
        if frames:
            self._process_frames(frames)
        
        # Generate output
        output_path = self._generate_output()
        
        return {
            "success": True,
            "output_path": str(output_path) if output_path else None,
            "frames_processed": len(self.frames_data),
            "analysis": self.analysis_results,
        }
    
    def _execute_command(self, cmd: DSLCommand):
        """Execute single DSL command."""
        if cmd.command == TokenType.SOURCE:
            self.source = cmd.target
            
        elif cmd.command == TokenType.DETECT:
            self._setup_detector(cmd)
            
        elif cmd.command == TokenType.TRACK:
            self._setup_tracker(cmd)
            
        elif cmd.command == TokenType.EXTRACT:
            self._setup_extractor(cmd)
            
        elif cmd.command == TokenType.CONVERT:
            self._setup_converter(cmd)
            
        elif cmd.command == TokenType.ANIMATE:
            self.fps = cmd.params.get('fps', 2.0)
            self.duration = cmd.params.get('duration', 60)
            
        elif cmd.command == TokenType.OUTPUT:
            self.output_path = cmd.target or "analysis.html"
            
        elif cmd.command == TokenType.ANALYZE:
            self._setup_analysis(cmd)
    
    def _setup_detector(self, cmd: DSLCommand):
        """Setup object detector."""
        detector_type = cmd.modifier.lower() if cmd.modifier else 'yolo'
        
        if detector_type == 'yolo':
            try:
                from .yolo_detector import YOLODetector
                classes = [c.strip() for c in cmd.target.split(',')]
                self.detector = YOLODetector(
                    classes=classes if classes[0] else None,
                    confidence_threshold=cmd.params.get('confidence', 0.25)
                )
            except ImportError:
                logger.warning("YOLO not available, using motion detection")
                self.detector = None
        elif detector_type == 'hog':
            # HOG detector for person detection
            self.detector = 'hog'
    
    def _setup_tracker(self, cmd: DSLCommand):
        """Setup object tracker."""
        from .motion_tracker import MultiObjectTracker
        
        self.tracker = MultiObjectTracker(
            max_age=cmd.params.get('max_age', 30),
            min_hits=cmd.params.get('min_hits', 3),
            iou_threshold=cmd.params.get('iou_threshold', 0.3),
        )
    
    def _setup_extractor(self, cmd: DSLCommand):
        """Setup motion extractor."""
        from .motion_tracker import MotionRegionExtractor
        
        self.extractor = MotionRegionExtractor(
            history=cmd.params.get('history', 50),
            min_area=cmd.params.get('min_area', 500),
            padding=cmd.params.get('padding', 0.1),
        )
    
    def _setup_converter(self, cmd: DSLCommand):
        """Setup SVG converter."""
        from .svg_visualizer import VideoToSVGConverter
        
        self.width = cmd.params.get('width', 800)
        self.height = cmd.params.get('height', 600)
        
        self.converter = VideoToSVGConverter(
            width=self.width,
            height=self.height,
        )
    
    def _setup_analysis(self, cmd: DSLCommand):
        """Setup analysis types."""
        analyses = [a.strip().lower() for a in cmd.target.split(',')]
        self.analysis_results['types'] = analyses
    
    def _process_frames(self, frames: List[Path]):
        """Process frames through pipeline."""
        from .motion_tracker import BoundingBox
        
        for i, frame_path in enumerate(frames):
            frame_data = {
                'frame_num': i + 1,
                'timestamp': time.time(),
                'detections': [],
                'motion_vectors': [],
            }
            
            # Run detection
            detections = []
            if self.detector and hasattr(self.detector, 'detect'):
                try:
                    raw_detections = self.detector.detect(frame_path)
                    for det in raw_detections:
                        detections.append(BoundingBox(
                            x=det.x, y=det.y, w=det.w, h=det.h,
                            confidence=det.confidence,
                            class_name=det.class_name
                        ))
                except Exception as e:
                    logger.debug(f"Detection failed: {e}")
            
            # Run motion extraction
            if self.extractor:
                try:
                    motion_regions = self.extractor.extract_motion_regions(frame_path)
                    detections.extend(motion_regions)
                except Exception as e:
                    logger.debug(f"Motion extraction failed: {e}")
            
            # Run tracking
            if self.tracker and detections:
                tracked = self.tracker.update(detections)
                for track in tracked:
                    frame_data['detections'].append({
                        'id': track.id,
                        'x': track.bbox.x,
                        'y': track.bbox.y,
                        'w': track.bbox.w,
                        'h': track.bbox.h,
                        'class_name': track.class_name,
                        'velocity': (track.velocity.x, track.velocity.y),
                    })
            elif detections:
                # No tracker, just use raw detections
                for j, det in enumerate(detections):
                    frame_data['detections'].append({
                        'id': j,
                        'x': det.x,
                        'y': det.y,
                        'w': det.w,
                        'h': det.h,
                        'class_name': det.class_name,
                    })
            
            # Add to converter
            if self.converter:
                self.converter.add_frame(
                    frame_num=frame_data['frame_num'],
                    timestamp=frame_data['timestamp'],
                    detections=frame_data['detections'],
                )
            
            self.frames_data.append(frame_data)
    
    def _generate_output(self) -> Optional[Path]:
        """Generate final output."""
        if self.converter:
            return self.converter.generate_html_animation(
                Path(self.output_path),
                fps=self.fps,
                title="Motion Analysis"
            )
        return None
    
    def add_frame_data(self, frame_data: Dict):
        """Manually add frame data."""
        self.frames_data.append(frame_data)
        
        if self.converter:
            self.converter.add_frame(
                frame_num=frame_data.get('frame_num', len(self.frames_data)),
                timestamp=frame_data.get('timestamp', time.time()),
                detections=frame_data.get('detections', []),
                motion_vectors=frame_data.get('motion_vectors', []),
            )
    
    def generate(self) -> Path:
        """Generate output from added frame data."""
        if self.converter:
            return self.converter.generate_html_animation(
                Path(self.output_path),
                fps=self.fps,
                title="Motion Analysis"
            )
        return None


# ============================================================================
# Mathematical Analysis Functions
# ============================================================================

def compute_velocity(positions: List[Tuple[float, float]], dt: float = 1.0) -> List[Tuple[float, float]]:
    """Compute velocity from position sequence."""
    velocities = []
    for i in range(1, len(positions)):
        vx = (positions[i][0] - positions[i-1][0]) / dt
        vy = (positions[i][1] - positions[i-1][1]) / dt
        velocities.append((vx, vy))
    return velocities


def compute_acceleration(velocities: List[Tuple[float, float]], dt: float = 1.0) -> List[Tuple[float, float]]:
    """Compute acceleration from velocity sequence."""
    accelerations = []
    for i in range(1, len(velocities)):
        ax = (velocities[i][0] - velocities[i-1][0]) / dt
        ay = (velocities[i][1] - velocities[i-1][1]) / dt
        accelerations.append((ax, ay))
    return accelerations


def trajectory_to_polar(positions: List[Tuple[float, float]], origin: Tuple[float, float] = (0.5, 0.5)) -> List[Tuple[float, float]]:
    """Convert trajectory to polar coordinates relative to origin."""
    polar = []
    for x, y in positions:
        dx = x - origin[0]
        dy = y - origin[1]
        r = math.sqrt(dx**2 + dy**2)
        theta = math.atan2(dy, dx)
        polar.append((r, theta))
    return polar


def trajectory_smoothing(positions: List[Tuple[float, float]], window: int = 3) -> List[Tuple[float, float]]:
    """Smooth trajectory using moving average."""
    if len(positions) < window:
        return positions
    
    smoothed = []
    half = window // 2
    
    for i in range(len(positions)):
        start = max(0, i - half)
        end = min(len(positions), i + half + 1)
        
        avg_x = sum(p[0] for p in positions[start:end]) / (end - start)
        avg_y = sum(p[1] for p in positions[start:end]) / (end - start)
        smoothed.append((avg_x, avg_y))
    
    return smoothed


# ============================================================================
# Example DSL Scripts
# ============================================================================

EXAMPLE_PERSON_TRACKING = """
# Person Tracking Analysis
SOURCE rtsp://camera/stream
DETECT person USING yolo WITH confidence=0.5
TRACK WITH kalman PARAMS max_age=30, min_hits=3
EXTRACT motion WITH background_subtraction
CONVERT TO svg SIZE 800x600
ANIMATE AT 2fps
OUTPUT TO person_tracking.html
"""

EXAMPLE_VEHICLE_TRACKING = """
# Vehicle Tracking Analysis
SOURCE rtsp://traffic/cam1
DETECT car, truck, bus USING yolo WITH confidence=0.4
TRACK WITH kalman, hungarian
CONVERT TO svg SIZE 1280x720
ANIMATE AT 5fps
OUTPUT TO vehicle_tracking.html
"""

EXAMPLE_MOTION_ANALYSIS = """
# Motion Analysis Only
SOURCE /path/to/video.mp4
EXTRACT motion WITH background_subtraction PARAMS history=100
FOCUS ON motion_regions WITH padding=0.15
CONVERT TO svg SIZE 640x480
ANIMATE AT 3fps
ANALYZE velocity, trajectory
OUTPUT TO motion_analysis.html
"""
