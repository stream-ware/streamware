"""
Video Processing Component for Streamware

Real-time video processing with RTSP, YOLO, OpenCV, and frame analysis.
"""

from __future__ import annotations
import os
import time
import json
import base64
from typing import Any, Optional, Dict, List, Generator
from ..core import Component, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)

# Check for dependencies
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.debug("OpenCV not installed. Video features limited.")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# YOLO detection (optional)
YOLO_AVAILABLE = False
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    logger.debug("ultralytics not installed. YOLO detection unavailable.")


@register("video")
class VideoComponent(Component):
    """
    Video processing component
    
    Operations:
    - rtsp: Read from RTSP stream
    - capture: Capture from camera/file
    - detect: Object detection (YOLO)
    - analyze: Frame analysis
    - caption: Generate captions with LLM
    - stream: Stream processed frames
    
    URI Examples:
        video://rtsp?url=rtsp://camera.com/stream&fps=1
        video://detect?model=yolov8n.pt&confidence=0.5
        video://caption?interval=5
        video://stream?output=http://localhost:8080
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "rtsp"
        
        # Video source
        self.source = uri.get_param("url") or uri.get_param("source", "0")
        self.fps = int(uri.get_param("fps", 1))  # Process N frames per second
        self.skip_frames = int(uri.get_param("skip", 30))  # Skip N frames between processing
        
        # Detection
        self.model_path = uri.get_param("model", "yolov8n.pt")
        self.confidence = float(uri.get_param("confidence", 0.5))
        self.classes = uri.get_param("classes")  # Filter specific classes
        
        # Captioning
        self.caption_interval = int(uri.get_param("interval", 5))  # Caption every N seconds
        self.llm_provider = uri.get_param("llm_provider", "ollama")
        
        # Output
        self.output_url = uri.get_param("output")
        self.save_path = uri.get_param("save")
        
        if not OPENCV_AVAILABLE:
            raise ComponentError("OpenCV (cv2) is required for video processing")
    
    def process(self, data: Any) -> Any:
        """Process video operation"""
        logger.info(f"Video operation: {self.operation}")
        
        operations = {
            "rtsp": self._process_rtsp,
            "capture": self._capture_video,
            "detect": self._detect_objects,
            "analyze": self._analyze_frame,
            "caption": self._generate_captions,
            "stream": self._stream_video,
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown video operation: {self.operation}")
        
        return operation_func(data)
    
    def _process_rtsp(self, data: Any) -> Generator[Dict, None, None]:
        """Process RTSP stream"""
        logger.info(f"Connecting to RTSP: {self.source}")
        
        cap = cv2.VideoCapture(self.source)
        
        if not cap.isOpened():
            raise ComponentError(f"Failed to open video source: {self.source}")
        
        frame_count = 0
        last_process_time = 0
        process_interval = 1.0 / self.fps
        
        try:
            while True:
                ret, frame = cap.read()
                
                if not ret:
                    logger.warning("Failed to read frame, reconnecting...")
                    cap.release()
                    time.sleep(1)
                    cap = cv2.VideoCapture(self.source)
                    continue
                
                frame_count += 1
                current_time = time.time()
                
                # Process at specified FPS
                if current_time - last_process_time >= process_interval:
                    last_process_time = current_time
                    
                    # Encode frame
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_b64 = base64.b64encode(buffer).decode('utf-8')
                    
                    yield {
                        "frame_number": frame_count,
                        "timestamp": current_time,
                        "frame": frame_b64,
                        "width": frame.shape[1],
                        "height": frame.shape[0]
                    }
        
        finally:
            cap.release()
    
    def _capture_video(self, data: Any) -> Generator[Dict, None, None]:
        """Capture from camera or file"""
        source = self.source
        
        # Try to convert to int for camera index
        try:
            source = int(source)
        except ValueError:
            pass
        
        cap = cv2.VideoCapture(source)
        
        if not cap.isOpened():
            raise ComponentError(f"Failed to open: {source}")
        
        frame_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                frame_count += 1
                
                if frame_count % self.skip_frames == 0:
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_b64 = base64.b64encode(buffer).decode('utf-8')
                    
                    yield {
                        "frame_number": frame_count,
                        "frame": frame_b64,
                        "width": frame.shape[1],
                        "height": frame.shape[0]
                    }
        
        finally:
            cap.release()
    
    def _detect_objects(self, data: Any) -> Dict:
        """Detect objects using YOLO"""
        if not YOLO_AVAILABLE:
            raise ComponentError("YOLO (ultralytics) not installed")
        
        # Load model
        model = YOLO(self.model_path)
        
        # Decode frame
        if isinstance(data, dict) and "frame" in data:
            frame_b64 = data["frame"]
            frame_data = base64.b64decode(frame_b64)
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif isinstance(data, str):
            # Assume it's a path
            frame = cv2.imread(data)
        else:
            raise ComponentError("Invalid input for object detection")
        
        # Run detection
        results = model(frame, conf=self.confidence)
        
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                detection = {
                    "class": model.names[int(box.cls)],
                    "confidence": float(box.conf),
                    "bbox": box.xyxy[0].tolist()
                }
                
                # Filter by class if specified
                if self.classes:
                    allowed_classes = self.classes.split(',')
                    if detection["class"] in allowed_classes:
                        detections.append(detection)
                else:
                    detections.append(detection)
        
        return {
            "detections": detections,
            "count": len(detections),
            "timestamp": time.time()
        }
    
    def _analyze_frame(self, data: Any) -> Dict:
        """Analyze frame (without YOLO)"""
        # Basic OpenCV analysis
        if isinstance(data, dict) and "frame" in data:
            frame_b64 = data["frame"]
            frame_data = base64.b64decode(frame_b64)
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            raise ComponentError("Invalid input for frame analysis")
        
        # Calculate basic metrics
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Brightness
        brightness = np.mean(gray)
        
        # Motion detection (simple frame difference)
        # For real motion detection, need previous frame
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.count_nonzero(edges) / edges.size
        
        return {
            "brightness": float(brightness),
            "edge_density": float(edge_density),
            "timestamp": time.time(),
            "analysis": "frame_analyzed"
        }
    
    def _generate_captions(self, data: Any) -> str:
        """Generate captions using LLM"""
        # This would use the LLM component
        from .llm import LLMComponent
        from ..uri import StreamwareURI
        
        # Prepare prompt based on detections
        if isinstance(data, dict) and "detections" in data:
            detections = data["detections"]
            objects = [d["class"] for d in detections]
            object_counts = {}
            for obj in objects:
                object_counts[obj] = object_counts.get(obj, 0) + 1
            
            prompt = f"Generate a natural language caption for this scene. Detected objects: {object_counts}"
        else:
            prompt = "Generate a caption for this video frame"
        
        # Use LLM to generate caption
        uri = StreamwareURI(f"llm://generate?prompt={prompt}&provider={self.llm_provider}")
        llm = LLMComponent(uri)
        
        caption = llm.process(prompt)
        
        return caption
    
    def _stream_video(self, data: Any) -> Generator[bytes, None, None]:
        """Stream video to HTTP endpoint"""
        # This would implement MJPEG streaming or similar
        # For now, return generator of frames
        
        for frame_data in self._process_rtsp(data):
            # Convert to MJPEG format
            frame_bytes = base64.b64decode(frame_data["frame"])
            
            # MJPEG boundary
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


# Helper functions
def video_from_rtsp(rtsp_url: str, fps: int = 1) -> Generator:
    """Quick RTSP video capture"""
    from ..core import flow
    uri = f"video://rtsp?url={rtsp_url}&fps={fps}"
    return flow(uri).run()


def detect_objects(source: str, model: str = "yolov8n.pt") -> Dict:
    """Quick object detection"""
    from ..core import flow
    uri = f"video://detect?source={source}&model={model}"
    return flow(uri).run()


def generate_caption(detections: Dict, provider: str = "ollama") -> str:
    """Quick caption generation"""
    from ..core import flow
    uri = f"video://caption?llm_provider={provider}"
    return flow(uri).run(detections)
