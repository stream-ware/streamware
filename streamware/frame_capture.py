"""
Frame Capture Module

Methods for capturing frames from various sources (screen, camera, RTSP).
"""

import io
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    cv2 = None
    np = None

try:
    from PIL import ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import av
    HAS_PYAV = True
except ImportError:
    HAS_PYAV = False


class FrameCaptureMixin:
    """Mixin class providing frame capture methods for AccountingWebService."""
    
    def capture(self) -> Optional[bytes]:
        """Capture from configured source (screen, camera, or rtsp)."""
        if self.source == "rtsp" and self.rtsp_url:
            return self.capture_rtsp()
        elif self.source == "camera":
            return self.capture_camera(self.camera_device)
        else:
            return self.capture_screen()

    def _start_frame_thread(self):
        """Start background thread for continuous frame grabbing (low latency)."""
        if self.frame_thread_running:
            return
        
        if not self.rtsp_url:
            return
        
        self.frame_thread_running = True
        
        # Try PyAV first (fastest, ~100ms latency after connection)
        if HAS_PYAV:
            def grab_frames_pyav():
                """Grab frames using PyAV (FFmpeg bindings) - lowest latency with document detection."""
                try:
                    print(f"   📡 Łączenie z RTSP (PyAV)...")
                    container = av.open(self.rtsp_url, options={
                        'rtsp_transport': 'tcp',
                        'fflags': 'nobuffer',
                        'flags': 'low_delay',
                        'max_delay': '500000',  # 0.5s max delay
                    }, timeout=10.0)
                    
                    stream = container.streams.video[0]
                    stream.thread_type = 'AUTO'  # Enable multi-threaded decoding
                    # Get actual camera FPS from stream
                    try:
                        camera_fps = float(stream.average_rate)
                    except:
                        camera_fps = 6
                    scanner_fps = self.env_config.get("scanner_fps", 1)
                    detection_interval = max(1, int(camera_fps / scanner_fps))
                    
                    print(f"   ✅ Połączono: {stream.width}x{stream.height} @ {camera_fps:.0f} fps")
                    print(f"   ⚡ Detekcja co {detection_interval} klatek ({scanner_fps} FPS skanowania)")
                    
                    frame_count = 0
                    for frame in container.decode(video=0):
                        if not self.frame_thread_running:
                            break
                        try:
                            # Convert to numpy array
                            img = frame.to_ndarray(format='bgr24')
                            
                            # Document detection at configured FPS
                            frame_count += 1
                            if frame_count % detection_interval == 0:
                                detection = self.detect_document_fast(img)
                                self.document_detected = detection["detected"]
                                self.last_detection_result = detection
                                
                                # Log timing info
                                timing = detection.get("timing", {})
                                total_ms = timing.get("total", 0)
                                if total_ms > 100:
                                    print(f"   ⏱️ Detekcja: {total_ms:.0f}ms (opencv: {timing.get('opencv_edge', 0):.0f}ms, receipt: {timing.get('receipt_detect', 0):.0f}ms, yolo: {timing.get('yolo', 0):.0f}ms)")
                                
                                if detection["detected"] and detection["confidence"] >= self.min_confidence:
                                    if self.detection_cooldown <= 0:
                                        _, jpeg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
                                        doc_type = detection.get('document_type') or detection.get('class_name') or 'dokument'
                                        
                                        # Hierarchical decision based on confidence
                                        image_data = jpeg.tobytes()
                                        
                                        if detection["confidence"] >= self.auto_save_threshold:
                                            # High confidence - check for duplicates first
                                            is_dup, dup_meta = self._is_duplicate(image_data, doc_type)
                                            
                                            if is_dup:
                                                sim = float((dup_meta or {}).get('similarity', 0.0))
                                                replace = bool((dup_meta or {}).get('replace'))
                                                matched = (dup_meta or {}).get('matched')
                                                matched_archived_id = None
                                                if isinstance(matched, dict):
                                                    matched_archived_id = matched.get('archived_id')

                                                if replace and isinstance(matched, dict):
                                                    idx = None
                                                    for i, d in enumerate(self.recent_documents):
                                                        if d is matched:
                                                            idx = i
                                                            break
                                                    if idx is not None:
                                                        self.recent_documents[idx]["image_bytes"] = image_data
                                                        self.recent_documents[idx]["quality"] = self._compute_image_quality(image_data)
                                                        self.recent_documents[idx]["hash"] = self._compute_image_hash(image_data)
                                                    self.last_document_frame = image_data
                                                    self._enqueue_duplicate_notification({
                                                        "type": "duplicate",
                                                        "message": f"🔄 Duplikat ({sim:.0%}) - zamieniono na lepszą jakość",
                                                        "similarity": sim,
                                                        "reason": (dup_meta or {}).get('reason'),
                                                        "doc_type": doc_type,
                                                        "matched_id": matched_archived_id,
                                                    })
                                                    print(f"   📸 Zamieniono na lepszą jakość: {doc_type} (pewność: {detection['confidence']:.0%})")
                                                else:
                                                    self._enqueue_duplicate_notification({
                                                        "type": "duplicate",
                                                        "message": f"🔄 Duplikat ({sim:.0%}) - pominięto skan",
                                                        "similarity": sim,
                                                        "reason": (dup_meta or {}).get('reason'),
                                                        "doc_type": doc_type,
                                                        "matched_id": matched_archived_id,
                                                    })
                                                    print(f"   🔄 Duplikat pominięty: {doc_type}")
                                            else:
                                                # New document - auto save
                                                self.last_document_frame = image_data
                                                print(f"   📸 Auto-zapis: {doc_type} (pewność: {detection['confidence']:.0%}, metoda: {detection.get('method')}, {total_ms:.0f}ms)")
                                        elif detection["confidence"] >= self.confirm_threshold:
                                            # Medium confidence - check duplicates
                                            is_dup, dup_meta = self._is_duplicate(image_data, doc_type)
                                            if not is_dup:
                                                self.pending_documents.append({
                                                    "frame": image_data,
                                                    "detection": detection,
                                                    "timestamp": time.time(),
                                                    "doc_type": doc_type,
                                                })
                                                print(f"   🔍 Do potwierdzenia: {doc_type} (pewność: {detection['confidence']:.0%}, {total_ms:.0f}ms)")
                                            else:
                                                sim = float((dup_meta or {}).get('similarity', 0.0))
                                                matched = (dup_meta or {}).get('matched')
                                                matched_archived_id = None
                                                if isinstance(matched, dict):
                                                    matched_archived_id = matched.get('archived_id')
                                                self._enqueue_duplicate_notification({
                                                    "type": "duplicate",
                                                    "message": f"🔄 Duplikat ({sim:.0%}) - pominięto skan",
                                                    "similarity": sim,
                                                    "reason": (dup_meta or {}).get('reason'),
                                                    "doc_type": doc_type,
                                                    "matched_id": matched_archived_id,
                                                })
                                                print(f"   🔄 Duplikat pominięty: {doc_type}")
                                        else:
                                            # Low confidence - just notify
                                            print(f"   👁️ Możliwy dokument: {doc_type} (pewność: {detection['confidence']:.0%}, {total_ms:.0f}ms)")
                                        
                                        # Cooldown: cooldown_sec seconds worth of frames
                                        self.detection_cooldown = max(2, int(self.cooldown_sec * camera_fps))
                                
                                if self.detection_cooldown > 0:
                                    self.detection_cooldown -= 1
                            
                            # Encode to JPEG for live preview
                            _, jpeg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
                            self.latest_frame = jpeg.tobytes()
                        except Exception:
                            pass
                    
                    container.close()
                except Exception as e:
                    print(f"   ⚠️ PyAV error: {e}")
                    self.frame_thread_running = False
            
            self.frame_thread = threading.Thread(target=grab_frames_pyav, daemon=True)
            self.frame_thread.start()
            print(f"   🎥 Uruchomiono PyAV low-latency z detekcją dokumentów")
            return
        
        # Fallback to OpenCV with FFMPEG
        if not HAS_CV2:
            print(f"   ❌ Brak PyAV ani OpenCV")
            self.frame_thread_running = False
            return
        
        # Set FFMPEG options for low latency BEFORE creating capture
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|buffer_size;65536|max_delay;0|fflags;nobuffer+discardcorrupt|flags;low_delay|analyzeduration;0|probesize;32"
        
        self.camera_cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        
        if not self.camera_cap.isOpened():
            print(f"   ❌ Nie można otworzyć strumienia RTSP")
            self.frame_thread_running = False
            return
        
        # Set minimal buffer
        self.camera_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        frame_count = [0]  # Use list to allow modification in nested function
        
        def grab_frames_opencv():
            """Continuously grab frames using OpenCV with document detection."""
            while self.frame_thread_running and self.camera_cap and self.camera_cap.isOpened():
                try:
                    ret, frame = self.camera_cap.read()
                    if ret and frame is not None:
                        # Document detection based on FPS from .env
                        frame_count[0] += 1
                        detection_interval = max(1, int(10 / self.env_config.get("scanner_fps", 2)))
                        if frame_count[0] % detection_interval == 0:
                            detection = self.detect_document_fast(frame)
                            self.document_detected = detection["detected"]
                            self.last_detection_result = detection
                            
                            # Log timing info
                            timing = detection.get("timing", {})
                            total_ms = timing.get("total", 0)
                            if total_ms > 100:
                                print(f"   ⏱️ Detekcja: {total_ms:.0f}ms")
                            
                            if detection["detected"] and detection["confidence"] >= self.min_confidence:
                                if self.detection_cooldown <= 0:
                                    _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
                                    doc_type = detection.get('document_type') or detection.get('class_name') or 'dokument'
                                    
                                    if detection["confidence"] >= self.auto_save_threshold:
                                        image_data = jpeg.tobytes()
                                        is_dup, dup_meta = self._is_duplicate(image_data, doc_type)
                                        if is_dup:
                                            sim = float((dup_meta or {}).get('similarity', 0.0))
                                            replace = bool((dup_meta or {}).get('replace'))
                                            matched = (dup_meta or {}).get('matched')
                                            matched_archived_id = None
                                            if isinstance(matched, dict):
                                                matched_archived_id = matched.get('archived_id')
                                            if replace and isinstance(matched, dict):
                                                idx = None
                                                for i, d in enumerate(self.recent_documents):
                                                    if d is matched:
                                                        idx = i
                                                        break
                                                if idx is not None:
                                                    self.recent_documents[idx]["image_bytes"] = image_data
                                                    self.recent_documents[idx]["quality"] = self._compute_image_quality(image_data)
                                                    self.recent_documents[idx]["hash"] = self._compute_image_hash(image_data)
                                                self.last_document_frame = image_data
                                                self._enqueue_duplicate_notification({
                                                    "type": "duplicate",
                                                    "message": f"🔄 Duplikat ({sim:.0%}) - zamieniono na lepszą jakość",
                                                    "similarity": sim,
                                                    "reason": (dup_meta or {}).get('reason'),
                                                    "doc_type": doc_type,
                                                    "matched_id": matched_archived_id,
                                                })
                                                print(f"   📸 Zamieniono na lepszą jakość: {doc_type} (pewność: {detection['confidence']:.0%}, {total_ms:.0f}ms)")
                                            else:
                                                self._enqueue_duplicate_notification({
                                                    "type": "duplicate",
                                                    "message": f"🔄 Duplikat ({sim:.0%}) - pominięto skan",
                                                    "similarity": sim,
                                                    "reason": (dup_meta or {}).get('reason'),
                                                    "doc_type": doc_type,
                                                    "matched_id": matched_archived_id,
                                                })
                                                print(f"   🔄 Duplikat pominięty: {doc_type}")
                                        else:
                                            self.last_document_frame = image_data
                                            print(f"   📸 Auto-zapis: {doc_type} (pewność: {detection['confidence']:.0%}, {total_ms:.0f}ms)")
                                    elif detection["confidence"] >= self.confirm_threshold:
                                        image_data = jpeg.tobytes()
                                        is_dup, dup_meta = self._is_duplicate(image_data, doc_type)
                                        if not is_dup:
                                            self.pending_documents.append({
                                                "frame": image_data,
                                                "detection": detection,
                                                "timestamp": time.time(),
                                                "doc_type": doc_type,
                                            })
                                            print(f"   🔍 Do potwierdzenia: {doc_type} (pewność: {detection['confidence']:.0%}, {total_ms:.0f}ms)")
                                        else:
                                            sim = float((dup_meta or {}).get('similarity', 0.0))
                                            matched = (dup_meta or {}).get('matched')
                                            matched_archived_id = None
                                            if isinstance(matched, dict):
                                                matched_archived_id = matched.get('archived_id')
                                            self._enqueue_duplicate_notification({
                                                "type": "duplicate",
                                                "message": f"🔄 Duplikat ({sim:.0%}) - pominięto skan",
                                                "similarity": sim,
                                                "reason": (dup_meta or {}).get('reason'),
                                                "doc_type": doc_type,
                                                "matched_id": matched_archived_id,
                                            })
                                            print(f"   🔄 Duplikat pominięty: {doc_type}")
                                    else:
                                        print(f"   👁️ Możliwy dokument: {doc_type} (pewność: {detection['confidence']:.0%}, {total_ms:.0f}ms)")
                                    
                                    self.detection_cooldown = int(self.cooldown_sec * 10)
                            
                            if self.detection_cooldown > 0:
                                self.detection_cooldown -= 1
                        
                        _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                        self.latest_frame = jpeg.tobytes()
                except Exception:
                    pass
                time.sleep(0.01)
        
        self.frame_thread = threading.Thread(target=grab_frames_opencv, daemon=True)
        self.frame_thread.start()
        print(f"   🎥 Uruchomiono OpenCV low-latency z detekcją dokumentów")

    def _stop_frame_thread(self):
        """Stop the frame grabbing thread."""
        self.frame_thread_running = False
        if self.frame_thread:
            self.frame_thread.join(timeout=1.0)
            self.frame_thread = None
        if self.camera_cap:
            self.camera_cap.release()
            self.camera_cap = None
        self.latest_frame = None

    def capture_rtsp(self) -> Optional[bytes]:
        """Capture from RTSP camera stream with low latency."""
        if not HAS_CV2 or not self.rtsp_url:
            return None

        # Start frame thread if not running
        if not self.frame_thread_running:
            self._start_frame_thread()
            # Wait a bit for first frame
            time.sleep(0.1)
        
        # Return the latest frame (grabbed by background thread)
        return self.latest_frame

    def capture_screen(self) -> Optional[bytes]:
        """Capture screen and return as JPEG bytes."""
        # Method 1: Try grim (Wayland native - best for Wayland)
        try:
            output_path = self.temp_dir / f"screen_{int(time.time() * 1000)}.png"
            subprocess.run(
                ["grim", str(output_path)],
                capture_output=True, timeout=5
            )
            if output_path.exists() and output_path.stat().st_size > 0:
                return self._convert_to_jpeg(output_path)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Method 2: Try gnome-screenshot with dbus (works better on Wayland)
        try:
            output_path = self.temp_dir / f"screen_{int(time.time() * 1000)}.png"
            subprocess.run(
                ["gnome-screenshot", "-f", str(output_path), "--display=:0"],
                capture_output=True, timeout=5,
                env={**os.environ, "XDG_SESSION_TYPE": "x11"}
            )
            if output_path.exists() and output_path.stat().st_size > 0:
                return self._convert_to_jpeg(output_path)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Method 3: Try spectacle (KDE)
        try:
            output_path = self.temp_dir / f"screen_{int(time.time() * 1000)}.png"
            subprocess.run(
                ["spectacle", "-b", "-n", "-o", str(output_path)],
                capture_output=True, timeout=5
            )
            if output_path.exists() and output_path.stat().st_size > 0:
                return self._convert_to_jpeg(output_path)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Method 4: Try scrot (X11)
        try:
            output_path = self.temp_dir / f"screen_{int(time.time() * 1000)}.png"
            subprocess.run(
                ["scrot", str(output_path)],
                capture_output=True, timeout=5
            )
            if output_path.exists() and output_path.stat().st_size > 0:
                return self._convert_to_jpeg(output_path)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Method 5: Try PIL ImageGrab (may work on some systems)
        if HAS_PIL:
            try:
                screenshot = ImageGrab.grab()
                if screenshot:
                    buffer = io.BytesIO()
                    screenshot.save(buffer, format='JPEG', quality=70)
                    return buffer.getvalue()
            except Exception:
                pass

        # Method 6: Try ffmpeg with x11grab
        try:
            output_path = self.temp_dir / f"screen_{int(time.time() * 1000)}.jpg"
            display = os.environ.get("DISPLAY", ":0")
            subprocess.run(
                ["ffmpeg", "-y", "-f", "x11grab", "-video_size", "1920x1080",
                 "-i", display, "-vframes", "1", "-q:v", "2", str(output_path)],
                capture_output=True, timeout=5
            )
            if output_path.exists() and output_path.stat().st_size > 0:
                with open(output_path, 'rb') as f:
                    data = f.read()
                output_path.unlink()
                return data
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return None

    def _convert_to_jpeg(self, image_path: Path) -> Optional[bytes]:
        """Convert image file to JPEG bytes."""
        try:
            with open(image_path, 'rb') as f:
                data = f.read()
            image_path.unlink()

            if HAS_CV2:
                nparr = np.frombuffer(data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is not None:
                    _, jpeg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    return jpeg.tobytes()
            return data
        except Exception:
            return None

    def capture_camera(self, device: int = 0) -> Optional[bytes]:
        """Capture from camera and return as JPEG bytes."""
        if not HAS_CV2:
            return None

        try:
            cap = cv2.VideoCapture(device)
            if not cap.isOpened():
                return None

            ret, frame = cap.read()
            cap.release()

            if ret and frame is not None:
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                return jpeg.tobytes()
        except Exception:
            pass

        return None
