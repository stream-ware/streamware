#!/usr/bin/env python3
"""
Standalone tracking benchmark: YOLO11n + ByteTrack/OC-SORT + Motion Gating

Tests the recommended stack for AMD CPU/iGPU:
- YOLO11n with OpenVINO backend (or PyTorch fallback)
- ByteTrack via Supervision (or OC-SORT via BoxMOT)
- MOG2 motion gating to reduce detection frequency
- Optional OSNet ReID for ambiguous associations

Usage:
    python tracker_demo.py --source rtsp://... --display
    python tracker_demo.py --source video.mp4 --output result.mp4
    python tracker_demo.py --source 0  # webcam
"""

import argparse
import time
import sys
from pathlib import Path
from threading import Thread
from queue import Queue
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import logging

import cv2
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logging.getLogger().handlers[0].flush = sys.stdout.flush
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Threaded RTSP/Video Capture
# -----------------------------------------------------------------------------
class ThreadedCapture:
    """Non-blocking video capture with frame dropping for live streams."""

    def __init__(self, source, queue_size: int = 2):
        self.source = source
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {source}")

        # Minimize buffer for live streams
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.queue = Queue(maxsize=queue_size)
        self.stopped = False
        self.thread = Thread(target=self._reader, daemon=True)
        self.thread.start()

        # Get video properties
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0

    def _reader(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            if not ret:
                self.stopped = True
                break
            if self.queue.full():
                try:
                    self.queue.get_nowait()  # Drop old frame
                except Exception:
                    pass
            self.queue.put(frame)

    def read(self) -> Optional[np.ndarray]:
        if self.stopped and self.queue.empty():
            return None
        try:
            return self.queue.get(timeout=1.0)
        except Exception:
            return None

    def release(self):
        self.stopped = True
        self.cap.release()


# -----------------------------------------------------------------------------
# Motion Gating (MOG2)
# -----------------------------------------------------------------------------
class MotionGate:
    """
    Background subtraction-based motion detection.
    Returns True when significant motion is detected OR periodic keyframe.
    """

    def __init__(
        self,
        motion_threshold: int = 1000,
        periodic_interval: int = 30,
        history: int = 500,
        var_threshold: int = 16,
    ):
        self.bg_sub = cv2.createBackgroundSubtractorMOG2(
            history=history, varThreshold=var_threshold, detectShadows=True
        )
        self.motion_threshold = motion_threshold
        self.periodic_interval = periodic_interval
        self.frame_count = 0
        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

        # Stats
        self.total_frames = 0
        self.detection_frames = 0

    def check(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        Check if detection should run.
        Returns (should_detect, motion_percent).
        """
        fg_mask = self.bg_sub.apply(frame)

        # Clean up mask
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self.kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, self.kernel)

        motion_pixels = cv2.countNonZero(fg_mask)
        total_pixels = frame.shape[0] * frame.shape[1]
        motion_percent = (motion_pixels / total_pixels) * 100

        self.frame_count += 1
        self.total_frames += 1

        # Run detection if motion OR periodic keyframe
        should_detect = (
            motion_pixels > self.motion_threshold
            or self.frame_count % self.periodic_interval == 0
        )

        if should_detect:
            self.detection_frames += 1

        return should_detect, motion_percent

    @property
    def detection_rate(self) -> float:
        if self.total_frames == 0:
            return 0.0
        return self.detection_frames / self.total_frames


# -----------------------------------------------------------------------------
# YOLO Detector (OpenVINO or PyTorch)
# -----------------------------------------------------------------------------
class YOLODetector:
    """
    YOLO11n detector with OpenVINO acceleration (falls back to PyTorch).
    """

    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        conf_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        classes: Optional[List[int]] = None,
        use_openvino: bool = True,
        input_size: int = 640,
    ):
        from ultralytics import YOLO

        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.classes = classes or [0, 2, 5, 7, 15, 16, 17]  # person, car, bus, truck, cat, dog, horse
        self.input_size = input_size

        # Try OpenVINO export if requested
        model_file = Path(model_path)
        openvino_dir = model_file.parent / (model_file.stem + "_openvino_model")

        if use_openvino and openvino_dir.exists():
            logger.info(f"Loading OpenVINO model from {openvino_dir}")
            self.model = YOLO(openvino_dir)
            self.backend = "openvino"
        elif use_openvino and model_file.exists():
            logger.info(f"Exporting {model_path} to OpenVINO...")
            base_model = YOLO(model_path)
            try:
                base_model.export(format="openvino", imgsz=input_size)
                self.model = YOLO(openvino_dir)
                self.backend = "openvino"
                logger.info("OpenVINO export successful")
            except Exception as e:
                logger.warning(f"OpenVINO export failed: {e}, using PyTorch")
                self.model = base_model
                self.backend = "pytorch"
        else:
            logger.info(f"Loading PyTorch model: {model_path}")
            self.model = YOLO(model_path)
            self.backend = "pytorch"

        # Inference timing
        self.last_inference_ms = 0.0

    def detect(self, frame: np.ndarray):
        """
        Run detection, return ultralytics Results object.
        """
        t0 = time.perf_counter()
        results = self.model(
            frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            classes=self.classes,
            imgsz=self.input_size,
            verbose=False,
        )[0]
        self.last_inference_ms = (time.perf_counter() - t0) * 1000
        return results


# -----------------------------------------------------------------------------
# Tracker (Supervision ByteTrack)
# -----------------------------------------------------------------------------
class Tracker:
    """
    ByteTrack tracker via Supervision library.
    Tracks object states: new, stable, lost.
    """

    def __init__(
        self,
        track_activation_threshold: float = 0.25,
        lost_track_buffer: int = 90,  # ~3 sec at 30fps
        minimum_matching_threshold: float = 0.8,
        frame_rate: int = 30,
        min_stable_frames: int = 3,
    ):
        import supervision as sv

        self.tracker = sv.ByteTrack(
            track_activation_threshold=track_activation_threshold,
            lost_track_buffer=lost_track_buffer,
            minimum_matching_threshold=minimum_matching_threshold,
            frame_rate=frame_rate,
        )
        self.sv = sv
        self.min_stable_frames = min_stable_frames

        # Track state management
        self._last_detections = None
        self._track_frames: dict = {}  # track_id -> frames_seen
        self._prev_track_ids: set = set()

    def update(self, results) -> "sv.Detections":
        """
        Update tracker with new detections.
        Returns detections and updates track state counters.
        """
        detections = self.sv.Detections.from_ultralytics(results)
        detections = self.tracker.update_with_detections(detections)
        self._last_detections = detections

        # Update track frame counts
        current_ids = set()
        if detections.tracker_id is not None:
            for tid in detections.tracker_id:
                current_ids.add(tid)
                self._track_frames[tid] = self._track_frames.get(tid, 0) + 1

        # Detect state changes
        new_tracks = current_ids - self._prev_track_ids
        lost_tracks = self._prev_track_ids - current_ids
        self._prev_track_ids = current_ids

        return detections, new_tracks, lost_tracks

    def predict(self):
        """
        Return last known detections (for frames without detection).
        In a full implementation, this would apply Kalman prediction.
        """
        return self._last_detections, set(), set()

    def get_stable_tracks(self) -> List[int]:
        """Return track IDs that have been seen for min_stable_frames."""
        return [tid for tid, frames in self._track_frames.items()
                if frames >= self.min_stable_frames and tid in self._prev_track_ids]


# -----------------------------------------------------------------------------
# Annotator
# -----------------------------------------------------------------------------
class Annotator:
    """
    Draws bounding boxes, labels, and traces on frames.
    """

    def __init__(self, class_names: dict):
        import supervision as sv

        self.class_names = class_names
        self.box_annotator = sv.BoxCornerAnnotator(thickness=2)
        self.label_annotator = sv.LabelAnnotator(text_scale=0.5, text_padding=5)
        self.trace_annotator = sv.TraceAnnotator(thickness=2, trace_length=50)

    def annotate(self, frame: np.ndarray, detections, show_trace: bool = True) -> np.ndarray:
        if detections is None or len(detections) == 0:
            return frame

        # Build labels
        labels = []
        for i in range(len(detections)):
            tid = detections.tracker_id[i] if detections.tracker_id is not None else "?"
            cid = detections.class_id[i] if detections.class_id is not None else 0
            conf = detections.confidence[i] if detections.confidence is not None else 0
            class_name = self.class_names.get(cid, f"cls{cid}")
            labels.append(f"#{tid} {class_name} {conf:.2f}")

        frame = self.box_annotator.annotate(frame.copy(), detections)
        frame = self.label_annotator.annotate(frame, detections, labels=labels)

        if show_trace:
            frame = self.trace_annotator.annotate(frame, detections)

        return frame


# -----------------------------------------------------------------------------
# Stats Display
# -----------------------------------------------------------------------------
@dataclass
class PipelineStats:
    frame_count: int = 0
    detection_count: int = 0
    total_time_ms: float = 0.0
    detection_time_ms: float = 0.0
    tracking_time_ms: float = 0.0
    motion_percent: float = 0.0
    active_tracks: int = 0
    stable_tracks: int = 0
    total_new_tracks: int = 0
    total_lost_tracks: int = 0

    fps_history: List[float] = field(default_factory=list)

    def add_frame_time(self, ms: float):
        self.total_time_ms += ms
        self.frame_count += 1
        if ms > 0:
            self.fps_history.append(1000.0 / ms)
            if len(self.fps_history) > 30:
                self.fps_history.pop(0)

    @property
    def avg_fps(self) -> float:
        if not self.fps_history:
            return 0.0
        return sum(self.fps_history) / len(self.fps_history)

    @property
    def detection_rate(self) -> float:
        if self.frame_count == 0:
            return 0.0
        return self.detection_count / self.frame_count


def draw_stats(frame: np.ndarray, stats: PipelineStats, motion_gate: MotionGate) -> np.ndarray:
    """Draw performance stats overlay."""
    lines = [
        f"FPS: {stats.avg_fps:.1f}",
        f"Det: {stats.detection_time_ms:.1f}ms | Trk: {stats.tracking_time_ms:.1f}ms",
        f"Motion: {stats.motion_percent:.1f}% | Gate: {motion_gate.detection_rate*100:.0f}%",
        f"Tracks: {stats.active_tracks} (stable: {stats.stable_tracks})",
    ]

    y = 30
    for line in lines:
        cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        y += 25

    return frame


# -----------------------------------------------------------------------------
# Main Pipeline
# -----------------------------------------------------------------------------
def run_pipeline(args):
    """Main tracking pipeline."""

    # Initialize components
    logger.info(f"Opening source: {args.source}")

    # Parse source (int for webcam, string for file/rtsp)
    try:
        source = int(args.source)
    except ValueError:
        source = args.source

    capture = ThreadedCapture(source)
    logger.info(f"Video: {capture.width}x{capture.height} @ {capture.fps:.1f} FPS")

    motion_gate = MotionGate(
        motion_threshold=args.motion_threshold,
        periodic_interval=args.periodic_interval,
    )

    detector = YOLODetector(
        model_path=args.model,
        conf_threshold=args.conf,
        use_openvino=not args.no_openvino,
        input_size=args.imgsz,
    )
    logger.info(f"Detector backend: {detector.backend}")

    tracker = Tracker(
        lost_track_buffer=args.track_buffer,
        frame_rate=int(capture.fps),
    )

    annotator = Annotator(detector.model.names)

    # Output video writer
    writer = None
    if args.output:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            args.output, fourcc, capture.fps, (capture.width, capture.height)
        )
        logger.info(f"Writing output to: {args.output}")

    stats = PipelineStats()

    logger.info("Starting pipeline... Press 'q' to quit.")
    start_time = time.time()

    try:
        while True:
            # Check duration/frame limits
            if args.duration > 0 and (time.time() - start_time) >= args.duration:
                logger.info(f"Duration limit ({args.duration}s) reached")
                break
            if args.max_frames > 0 and stats.frame_count >= args.max_frames:
                logger.info(f"Frame limit ({args.max_frames}) reached")
                break

            t_start = time.perf_counter()

            frame = capture.read()
            if frame is None:
                logger.info("End of stream")
                break

            # Motion gating
            should_detect, motion_pct = motion_gate.check(frame)
            stats.motion_percent = motion_pct

            # Detection or prediction
            t_det = time.perf_counter()
            if should_detect:
                results = detector.detect(frame)
                detections, new_tracks, lost_tracks = tracker.update(results)
                stats.detection_count += 1
                stats.detection_time_ms = detector.last_inference_ms
                stats.total_new_tracks += len(new_tracks)
                stats.total_lost_tracks += len(lost_tracks)
            else:
                detections, new_tracks, lost_tracks = tracker.predict()
                stats.detection_time_ms = 0.0

            t_trk = time.perf_counter()
            stats.tracking_time_ms = (t_trk - t_det) * 1000 - stats.detection_time_ms

            # Count active and stable tracks
            if detections is not None and detections.tracker_id is not None:
                stats.active_tracks = len(set(detections.tracker_id))
                stats.stable_tracks = len(tracker.get_stable_tracks())
            else:
                stats.active_tracks = 0
                stats.stable_tracks = 0

            # Annotate
            annotated = annotator.annotate(frame, detections, show_trace=args.trace)

            # Stats overlay
            if args.stats:
                annotated = draw_stats(annotated, stats, motion_gate)

            # Frame timing
            frame_ms = (time.perf_counter() - t_start) * 1000
            stats.add_frame_time(frame_ms)

            # Output
            if writer:
                writer.write(annotated)

            if args.display:
                cv2.imshow("Tracking Demo", annotated)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    logger.info("Quit requested")
                    break
                elif key == ord("s"):
                    # Save screenshot
                    cv2.imwrite(f"screenshot_{stats.frame_count}.jpg", annotated)
                    logger.info(f"Screenshot saved: screenshot_{stats.frame_count}.jpg")

            # Progress logging
            if stats.frame_count % 100 == 0:
                logger.info(
                    f"Frame {stats.frame_count}: "
                    f"FPS={stats.avg_fps:.1f}, "
                    f"Det={stats.detection_time_ms:.1f}ms, "
                    f"DetRate={stats.detection_rate*100:.0f}%, "
                    f"Tracks={stats.active_tracks}"
                )

    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        capture.release()
        if writer:
            writer.release()
        cv2.destroyAllWindows()

    # Final stats
    logger.info("=" * 50)
    logger.info("Pipeline Statistics:")
    logger.info(f"  Total frames: {stats.frame_count}")
    logger.info(f"  Detection frames: {stats.detection_count} ({stats.detection_rate*100:.1f}%)")
    logger.info(f"  Motion gate savings: {(1 - motion_gate.detection_rate)*100:.1f}%")
    logger.info(f"  Average FPS: {stats.avg_fps:.1f}")
    logger.info(f"  Track events: {stats.total_new_tracks} entered, {stats.total_lost_tracks} left")
    logger.info("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="YOLO11n + ByteTrack tracking benchmark",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Input/Output
    parser.add_argument(
        "--source", "-s", required=True,
        help="Video source: file path, RTSP URL, or webcam index (0, 1, ...)"
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output video file path"
    )
    parser.add_argument(
        "--display", "-d", action="store_true",
        help="Show live display window"
    )

    # Model
    parser.add_argument(
        "--model", "-m", default="yolo11n.pt",
        help="YOLO model path"
    )
    parser.add_argument(
        "--no-openvino", action="store_true",
        help="Disable OpenVINO acceleration"
    )
    parser.add_argument(
        "--imgsz", type=int, default=640,
        help="Input image size for detection"
    )
    parser.add_argument(
        "--conf", type=float, default=0.5,
        help="Detection confidence threshold"
    )

    # Motion gating
    parser.add_argument(
        "--motion-threshold", type=int, default=1000,
        help="Motion pixels threshold for detection trigger"
    )
    parser.add_argument(
        "--periodic-interval", type=int, default=30,
        help="Force detection every N frames regardless of motion"
    )

    # Tracking
    parser.add_argument(
        "--track-buffer", type=int, default=90,
        help="Frames to keep lost tracks before deletion"
    )

    # Display options
    parser.add_argument(
        "--trace", action="store_true",
        help="Show movement traces"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Show stats overlay"
    )

    # Benchmark options
    parser.add_argument(
        "--duration", type=int, default=0,
        help="Limit run to N seconds (0 = unlimited)"
    )
    parser.add_argument(
        "--max-frames", type=int, default=0,
        help="Limit run to N frames (0 = unlimited)"
    )

    args = parser.parse_args()

    if not args.display and not args.output:
        logger.warning("Neither --display nor --output specified. Running in headless mode.")

    run_pipeline(args)


if __name__ == "__main__":
    main()
