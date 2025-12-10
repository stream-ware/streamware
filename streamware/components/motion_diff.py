"""
Motion Diff Component - Pixel-level motion detection with region analysis

Efficient change detection workflow:
1. Pixel-level diff to detect changed regions (fast, no AI)
2. Extract only changed regions
3. Send only changed regions to LLM for detailed analysis (smart, focused)

This approach is:
- Faster (smaller images to analyze)
- More accurate (focused on actual changes)
- Cheaper (fewer tokens for LLM)
- Works with small LLM models

URI Examples:
    motion://diff?source=rtsp://camera/live&threshold=30
    motion://analyze?source=rtsp://camera/live&regions=true
    motion://regions?source=rtsp://camera/live

Related:
    - streamware/components/stream.py
    - streamware/components/tracking.py
"""

import subprocess
import tempfile
import logging
import time
import os
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple
from dataclasses import dataclass
import base64
from ..core import Component, StreamwareURI, register
from ..exceptions import ComponentError
from ..config import config

logger = logging.getLogger(__name__)


@dataclass
class Region:
    """Changed region in image"""
    x: int
    y: int
    width: int
    height: int
    change_percent: float
    
    @property
    def area(self) -> int:
        return self.width * self.height
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


@register("motion")
@register("diff")
class MotionDiffComponent(Component):
    """
    Pixel-level motion detection with smart region analysis.
    
    Two-phase approach:
    1. Fast pixel diff to find changed regions
    2. AI analysis only on changed regions
    
    Operations:
        - diff: Detect pixel-level changes between frames
        - analyze: Full analysis with region extraction + AI
        - regions: Get changed regions only (no AI)
        - heatmap: Generate motion heatmap over time
    
    URI Examples:
        motion://diff?source=rtsp://camera/live&threshold=30
        motion://analyze?source=rtsp://camera/live&min_region=500
        motion://regions?source=rtsp://camera/live
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "analyze"
        
        self.source = uri.get_param("source", uri.get_param("url", ""))
        
        # Use config defaults if not specified in URI
        threshold_default = config.get("SQ_MOTION_THRESHOLD", "25")
        min_region_default = config.get("SQ_MIN_REGION", "500")
        scale_default = config.get("SQ_FRAME_SCALE", "0.3")
        
        # Diff sensitivity (0-100, lower = more sensitive)
        self.threshold = int(uri.get_param("threshold", threshold_default))
        
        # Minimum region size to report (pixels)
        self.min_region = int(uri.get_param("min_region", min_region_default))
        
        # Grid size for region detection
        self.grid_size = int(uri.get_param("grid", "8"))  # 8x8 grid
        
        # Optional downscaling factor for diff analysis (0 < scale <= 1)
        try:
            self.scale = float(uri.get_param("scale", scale_default))
        except ValueError:
            self.scale = 0.3
        if self.scale <= 0 or self.scale > 1:
            self.scale = 1.0
        
        # Analysis settings
        self.interval = int(uri.get_param("interval", "5"))
        self.duration = int(uri.get_param("duration", "30"))
        self.model = uri.get_param("model", "llava:7b")
        self.focus = uri.get_param("focus", "person")
        
        # Save frames for report
        save_param = uri.get_param("save_frames", "false")
        self.save_frames = str(save_param).lower() in ("true", "1", "yes")
        
        self._temp_dir = None
        self._prev_frame = None
    
    def process(self, data: Any) -> Dict:
        """Process motion detection"""
        self._temp_dir = Path(tempfile.mkdtemp())
        
        try:
            if self.operation == "diff":
                return self._detect_diff()
            elif self.operation == "analyze":
                return self._analyze_with_regions()
            elif self.operation == "regions":
                return self._get_regions_only()
            elif self.operation == "heatmap":
                return self._generate_heatmap()
            else:
                raise ComponentError(f"Unknown operation: {self.operation}")
        finally:
            if self._temp_dir and self._temp_dir.exists():
                import shutil
                shutil.rmtree(self._temp_dir, ignore_errors=True)
    
    def _detect_diff(self) -> Dict:
        """Detect pixel-level differences between frames"""
        results = []
        num_frames = max(1, self.duration // self.interval)
        
        for i in range(num_frames):
            frame_path = self._capture_frame(i)
            if frame_path and frame_path.exists():
                diff_result = self._compute_diff(frame_path, i)
                results.append(diff_result)
                self._prev_frame = frame_path
            
            if i < num_frames - 1:
                time.sleep(self.interval)
        
        changes = [r for r in results if r.get("has_change")]
        
        return {
            "success": True,
            "operation": "diff",
            "source": self.source,
            "threshold": self.threshold,
            "timeline": results,
            "total_changes": len(changes),
            "frames_analyzed": len(results)
        }
    
    def _analyze_with_regions(self) -> Dict:
        """Full analysis: pixel diff + AI on changed regions"""
        results = []
        num_frames = max(1, self.duration // self.interval)
        
        for i in range(num_frames):
            frame_path = self._capture_frame(i)
            if not frame_path or not frame_path.exists():
                continue
            
            timestamp = time.strftime("%H:%M:%S")
            
            # Phase 1: Pixel-level diff
            diff_result = self._compute_diff(frame_path, i)
            regions = diff_result.get("regions", [])
            
            frame_result = {
                "frame": i + 1,
                "timestamp": timestamp,
                "has_change": diff_result.get("has_change", False),
                "change_percent": diff_result.get("change_percent", 0),
                "regions_detected": len(regions),
                "type": "no_change"
            }
            
            # Phase 2: If changes detected, analyze regions with AI
            if regions and diff_result.get("has_change"):
                frame_result["type"] = "change"
                
                # Analyze each changed region
                region_analyses = []
                for region in regions[:3]:  # Limit to 3 largest regions
                    analysis = self._analyze_region(frame_path, region)
                    region_analyses.append({
                        "region": {
                            "x": region.x,
                            "y": region.y,
                            "width": region.width,
                            "height": region.height,
                            "change_percent": region.change_percent
                        },
                        "analysis": analysis
                    })
                
                frame_result["region_analyses"] = region_analyses
                
                # Generate summary
                frame_result["changes"] = self._summarize_changes(region_analyses)
            
            # Save frame image for report
            if self.save_frames:
                try:
                    with open(frame_path, "rb") as f:
                        frame_result["image_base64"] = base64.b64encode(f.read()).decode()
                except Exception:
                    pass
            
            results.append(frame_result)
            self._prev_frame = frame_path
            
            if i < num_frames - 1:
                time.sleep(self.interval)
        
        changes = [r for r in results if r.get("type") == "change"]
        
        return {
            "success": True,
            "operation": "analyze",
            "source": self.source,
            "mode": "region_diff",
            "timeline": results,
            "significant_changes": len(changes),
            "frames_analyzed": len(results)
        }
    
    def _get_regions_only(self) -> Dict:
        """Get changed regions without AI analysis"""
        results = []
        num_frames = max(1, self.duration // self.interval)
        
        for i in range(num_frames):
            frame_path = self._capture_frame(i)
            if frame_path and frame_path.exists():
                diff_result = self._compute_diff(frame_path, i)
                diff_result["frame"] = i + 1
                diff_result["timestamp"] = time.strftime("%H:%M:%S")
                results.append(diff_result)
                self._prev_frame = frame_path
            
            if i < num_frames - 1:
                time.sleep(self.interval)
        
        return {
            "success": True,
            "operation": "regions",
            "source": self.source,
            "timeline": results,
            "frames_analyzed": len(results)
        }
    
    def _generate_heatmap(self) -> Dict:
        """Generate motion heatmap data"""
        # Aggregate all change positions
        all_regions = []
        num_frames = max(1, self.duration // self.interval)
        
        for i in range(num_frames):
            frame_path = self._capture_frame(i)
            if frame_path and frame_path.exists():
                diff_result = self._compute_diff(frame_path, i)
                for region in diff_result.get("regions", []):
                    all_regions.append({
                        "frame": i,
                        "x": region.x,
                        "y": region.y,
                        "width": region.width,
                        "height": region.height,
                        "intensity": region.change_percent
                    })
                self._prev_frame = frame_path
            
            if i < num_frames - 1:
                time.sleep(self.interval)
        
        return {
            "success": True,
            "operation": "heatmap",
            "source": self.source,
            "regions": all_regions,
            "total_regions": len(all_regions),
            "frames_analyzed": num_frames
        }
    
    def _capture_frame(self, frame_num: int) -> Optional[Path]:
        """Capture frame from source"""
        output_path = self._temp_dir / f"frame_{frame_num:05d}.jpg"
        
        try:
            if self.source.startswith("rtsp://"):
                cmd = [
                    "ffmpeg", "-y", "-rtsp_transport", "tcp",
                    "-i", self.source,
                    "-frames:v", "1",
                    "-q:v", "2",
                    str(output_path)
                ]
            else:
                cmd = [
                    "ffmpeg", "-y",
                    "-i", self.source,
                    "-frames:v", "1",
                    str(output_path)
                ]
            
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            return output_path
        except Exception as e:
            logger.warning(f"Frame capture failed: {e}")
            return None
    
    def _compute_diff(self, current_frame: Path, frame_num: int) -> Dict:
        """Compute pixel-level diff and find changed regions"""
        if self._prev_frame is None or not self._prev_frame.exists():
            return {
                "has_change": frame_num == 0,  # First frame is always "change"
                "change_percent": 100 if frame_num == 0 else 0,
                "regions": []
            }
        
        try:
            from PIL import Image, ImageChops, ImageFilter
            import numpy as np
        except ImportError:
            # Fallback without numpy/PIL
            return self._simple_diff(current_frame, frame_num)
        
        try:
            # Load images (grayscale)
            img1_full = Image.open(self._prev_frame).convert('L')
            img2_full = Image.open(current_frame).convert('L')

            # Resize second image to match first if needed
            if img1_full.size != img2_full.size:
                img2_full = img2_full.resize(img1_full.size)

            # Downscale for faster diff computation
            if self.scale < 1.0:
                small_size = (
                    max(1, int(img1_full.width * self.scale)),
                    max(1, int(img1_full.height * self.scale)),
                )
                img1 = img1_full.resize(small_size, Image.BILINEAR)
                img2 = img2_full.resize(small_size, Image.BILINEAR)
            else:
                img1 = img1_full
                img2 = img2_full
            
            # Compute absolute difference on downscaled frames
            diff = ImageChops.difference(img1, img2)
            
            # Apply threshold
            diff_array = np.array(diff)
            diff_binary = (diff_array > self.threshold).astype(np.uint8) * 255
            
            # Calculate overall change percentage
            total_pixels = diff_binary.size
            changed_pixels = np.sum(diff_binary > 0)
            change_percent = (changed_pixels / total_pixels) * 100
            
            # Find changed regions using grid (in downscaled coordinate space)
            regions = self._find_regions(diff_binary, img1.size)
            
            # Filter small regions
            regions = [r for r in regions if r.area >= self.min_region]
            
            # Sort by change intensity
            regions.sort(key=lambda r: r.change_percent, reverse=True)
            
            # Rescale regions back to original image coordinates if downscaled
            if self.scale < 1.0 and regions:
                scale_x = img1_full.width / float(img1.width)
                scale_y = img1_full.height / float(img1.height)
                scaled_regions = []
                for r in regions:
                    scaled_regions.append(
                        Region(
                            x=int(r.x * scale_x),
                            y=int(r.y * scale_y),
                            width=int(r.width * scale_x),
                            height=int(r.height * scale_y),
                            change_percent=r.change_percent,
                        )
                    )
                regions = scaled_regions

            # More sensitive detection - any visible change counts
            has_change = change_percent > 0.1 or len(regions) > 0
            
            return {
                "has_change": has_change,
                "change_percent": round(change_percent, 2),
                "regions": regions
            }
            
        except Exception as e:
            logger.warning(f"Diff computation failed: {e}")
            return {"has_change": False, "change_percent": 0, "regions": []}
    
    def _find_regions(self, diff_binary, img_size: Tuple[int, int]) -> List[Region]:
        """Find changed regions using grid-based analysis"""
        import numpy as np
        
        width, height = img_size
        grid_w = width // self.grid_size
        grid_h = height // self.grid_size
        
        regions = []
        
        for gy in range(self.grid_size):
            for gx in range(self.grid_size):
                x1 = gx * grid_w
                y1 = gy * grid_h
                x2 = min((gx + 1) * grid_w, width)
                y2 = min((gy + 1) * grid_h, height)
                
                # Get grid cell
                cell = diff_binary[y1:y2, x1:x2]
                
                # Calculate change in cell
                cell_change = np.mean(cell) / 255 * 100
                
                if cell_change > 1:  # At least 1% change in cell
                    regions.append(Region(
                        x=x1,
                        y=y1,
                        width=x2 - x1,
                        height=y2 - y1,
                        change_percent=round(cell_change, 2)
                    ))
        
        # Merge adjacent regions
        regions = self._merge_adjacent_regions(regions)
        
        return regions
    
    def _merge_adjacent_regions(self, regions: List[Region]) -> List[Region]:
        """Merge adjacent changed regions"""
        if not regions:
            return []
        
        # Simple merge: group regions that overlap or are adjacent
        merged = []
        used = set()
        
        for i, r1 in enumerate(regions):
            if i in used:
                continue
            
            # Find all adjacent regions
            group = [r1]
            used.add(i)
            
            for j, r2 in enumerate(regions):
                if j in used:
                    continue
                
                # Check if adjacent (within 1 grid cell)
                margin = max(r1.width, r1.height)
                if (abs(r1.x - r2.x) < margin * 2 and 
                    abs(r1.y - r2.y) < margin * 2):
                    group.append(r2)
                    used.add(j)
            
            # Merge group into single region
            if group:
                min_x = min(r.x for r in group)
                min_y = min(r.y for r in group)
                max_x = max(r.x + r.width for r in group)
                max_y = max(r.y + r.height for r in group)
                avg_change = sum(r.change_percent for r in group) / len(group)
                
                merged.append(Region(
                    x=min_x,
                    y=min_y,
                    width=max_x - min_x,
                    height=max_y - min_y,
                    change_percent=round(avg_change, 2)
                ))
        
        return merged
    
    def _simple_diff(self, current_frame: Path, frame_num: int) -> Dict:
        """Simple diff without numpy (fallback)"""
        # Just check file size difference as rough approximation
        try:
            prev_size = self._prev_frame.stat().st_size
            curr_size = current_frame.stat().st_size
            diff_ratio = abs(prev_size - curr_size) / max(prev_size, curr_size)
            return {
                "has_change": diff_ratio > 0.05,
                "change_percent": round(diff_ratio * 100, 2),
                "regions": []
            }
        except Exception:
            return {"has_change": False, "change_percent": 0, "regions": []}
    
    def _analyze_region(self, frame_path: Path, region: Region) -> str:
        """Analyze specific region with AI"""
        try:
            from PIL import Image
            
            # Crop region from image
            img = Image.open(frame_path)
            
            # Add margin around region
            margin = 20
            x1 = max(0, region.x - margin)
            y1 = max(0, region.y - margin)
            x2 = min(img.width, region.x + region.width + margin)
            y2 = min(img.height, region.y + region.height + margin)
            
            cropped = img.crop((x1, y1, x2, y2))
            
            # Save cropped region
            region_path = self._temp_dir / f"region_{region.x}_{region.y}.jpg"
            cropped.save(region_path, quality=90)
            
            # Analyze with LLM using external prompt
            from ..prompts import render_prompt
            prompt = render_prompt("motion_region", focus=self.focus)
            
            return self._call_vision_model(region_path, prompt)
            
        except Exception as e:
            return f"Could not analyze region: {e}"
    
    def _summarize_changes(self, region_analyses: List[Dict]) -> str:
        """Summarize all region analyses"""
        if not region_analyses:
            return "No changes detected"
        
        summaries = []
        for ra in region_analyses:
            region = ra["region"]
            analysis = ra["analysis"]
            
            # Extract key info
            summary = f"Region ({region['x']},{region['y']}): {analysis[:200]}"
            summaries.append(summary)
        
        return " | ".join(summaries)
    
    def _call_vision_model(self, image_path: Path, prompt: str) -> str:
        """Call vision model for analysis with optimized image"""
        try:
            import requests
            
            # Optimize image before sending to LLM
            from ..image_optimize import prepare_image_for_llm_base64
            
            # Use fast preset for motion analysis (already cropped to region)
            image_data = prepare_image_for_llm_base64(image_path, preset="fast")
            
            ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
            timeout = int(config.get("SQ_LLM_TIMEOUT", "60"))
            
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False
                },
                timeout=timeout
            )
            
            if response.ok:
                return response.json().get("response", "")
            return f"Analysis failed: {response.status_code}"
            
        except Exception as e:
            return f"Could not analyze: {e}"


# ============================================================================
# Helper Functions
# ============================================================================

def detect_motion(source: str, duration: int = 30, threshold: int = 25) -> Dict:
    """
    Quick motion detection using pixel diff.
    
    Args:
        source: RTSP URL or file path
        duration: Analysis duration in seconds
        threshold: Sensitivity (0-100, lower = more sensitive)
    
    Example:
        result = detect_motion("rtsp://camera/live", 60, 20)
        if result['total_changes'] > 0:
            print("Motion detected!")
    """
    from ..core import flow
    return flow(f"motion://diff?source={source}&duration={duration}&threshold={threshold}").run()


def analyze_motion(source: str, duration: int = 30, focus: str = "person") -> Dict:
    """
    Full motion analysis with AI on changed regions.
    
    Args:
        source: RTSP URL or file path
        duration: Analysis duration
        focus: What to focus on (person, vehicle, etc.)
    
    Example:
        result = analyze_motion("rtsp://camera/live", 60, "person")
        for frame in result['timeline']:
            if frame['type'] == 'change':
                print(f"Change at {frame['timestamp']}: {frame['changes']}")
    """
    from ..core import flow
    return flow(f"motion://analyze?source={source}&duration={duration}&focus={focus}&save_frames=true").run()


def get_motion_regions(source: str, threshold: int = 25) -> Dict:
    """
    Get changed regions without AI (fast).
    
    Example:
        result = get_motion_regions("rtsp://camera/live", 20)
        for frame in result['timeline']:
            for region in frame.get('regions', []):
                print(f"Change at ({region.x}, {region.y})")
    """
    from ..core import flow
    return flow(f"motion://regions?source={source}&threshold={threshold}&duration=10").run()
