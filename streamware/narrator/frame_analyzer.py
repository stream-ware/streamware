"""
Frame Analyzer Module

Advanced frame analysis with motion detection, edge tracking, and preprocessing.
Extracted from live_narrator.py for modularity.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from ..config import config

logger = logging.getLogger(__name__)


class FrameAnalyzer:
    """
    Advanced frame analysis with motion detection, edge tracking, and preprocessing.
    Processes frames before sending to LLM for better accuracy.
    """
    
    def __init__(self, threshold: int = 25, min_area: int = 500):
        self.threshold = threshold
        self.min_area = min_area
        self._prev_frame = None
        self._prev_gray = None
        self._motion_history = []
    
    def analyze(self, frame_path: Path) -> Tuple[Dict, Optional[Path]]:
        """
        Analyze frame for motion and objects.

        Performance optimisation:
        - Motion / edge detection works on a downscaled (~30%) frame
        - Annotations are drawn on the original resolution image
        
        Returns:
            Tuple of (analysis dict, path to annotated frame)
        """
        if not PIL_AVAILABLE:
            return {"error": "PIL not installed"}, None
        
        img = Image.open(frame_path)

        # Downscale for faster numerical analysis
        scale_factor = float(config.get("SQ_FRAME_SCALE", "0.3"))
        gray_small = self._downscale_to_gray(img, scale_factor)
        
        analysis = {
            "has_motion": False,
            "motion_percent": 0.0,
            "motion_regions": [],
            "edge_objects": [],
            "likely_person": False,
            "person_confidence": 0.0,
        }
        
        # Motion detection (on downscaled frames)
        if self._prev_gray is not None:
            motion_data = self._detect_motion(gray_small, self._prev_gray)
            analysis.update(motion_data)
        
        # Edge detection for object boundaries
        edge_data = self._detect_edges(gray_small)
        analysis["edge_objects"] = edge_data.get("objects", [])
        
        # Analyze if motion pattern suggests person
        if analysis["has_motion"]:
            person_analysis = self._analyze_for_person(analysis, img.size)
            analysis.update(person_analysis)
        
        # Rescale motion regions back to original coordinates
        self._rescale_regions(analysis, img.size, gray_small.size)

        # Create annotated frame on original-resolution image
        annotated_path = self._create_annotated_frame(frame_path, img, analysis)
        
        # Store downscaled grayscale for next iteration
        self._prev_gray = gray_small
        self._prev_frame = frame_path
        
        return analysis, annotated_path
    
    def _downscale_to_gray(self, img: 'Image', scale_factor: float) -> 'Image':
        """Downscale image and convert to grayscale."""
        try:
            if img.width > 0 and img.height > 0:
                small_size = (
                    max(1, int(img.width * scale_factor)),
                    max(1, int(img.height * scale_factor)),
                )
                return img.resize(small_size, Image.BILINEAR).convert('L')
        except Exception:
            pass
        return img.convert('L')
    
    def _rescale_regions(self, analysis: Dict, orig_size: Tuple[int, int], 
                         small_size: Tuple[int, int]):
        """Rescale motion regions to original image coordinates."""
        try:
            if analysis.get("motion_regions"):
                scale_x = orig_size[0] / float(small_size[0])
                scale_y = orig_size[1] / float(small_size[1])
                for region in analysis["motion_regions"]:
                    region["x"] = int(region["x"] * scale_x)
                    region["y"] = int(region["y"] * scale_y)
                    region["w"] = int(region["w"] * scale_x)
                    region["h"] = int(region["h"] * scale_y)
        except Exception as e:
            logger.debug(f"Failed to rescale motion regions: {e}")
    
    def _detect_motion(self, current: 'Image', previous: 'Image') -> Dict:
        """Detect motion between frames."""
        try:
            # Resize if needed
            if current.size != previous.size:
                previous = previous.resize(current.size)
            
            # Compute difference
            diff = ImageChops.difference(current, previous)
            
            # Get histogram
            histogram = diff.histogram()
            
            # Count changed pixels above threshold
            changed_pixels = sum(histogram[self.threshold:])
            total_pixels = sum(histogram)
            motion_percent = (changed_pixels / total_pixels * 100) if total_pixels > 0 else 0
            
            has_motion = motion_percent > 0.5
            
            # Find motion regions
            regions = []
            if has_motion:
                regions = self._find_motion_regions(diff)
            
            return {
                "has_motion": has_motion,
                "motion_percent": round(motion_percent, 2),
                "motion_regions": regions,
            }
        except Exception as e:
            logger.debug(f"Motion detection error: {e}")
            return {"has_motion": False, "motion_percent": 0, "motion_regions": []}
    
    def _find_motion_regions(self, diff_img: 'Image') -> List[Dict]:
        """Find regions with significant motion."""
        regions = []
        width, height = diff_img.size
        grid_size = 8
        cell_w = width // grid_size
        cell_h = height // grid_size
        
        for gy in range(grid_size):
            for gx in range(grid_size):
                x1, y1 = gx * cell_w, gy * cell_h
                x2, y2 = x1 + cell_w, y1 + cell_h
                
                cell = diff_img.crop((x1, y1, x2, y2))
                hist = cell.histogram()
                changed = sum(hist[self.threshold:])
                total = sum(hist)
                
                if total > 0 and (changed / total) > 0.1:
                    regions.append({
                        "x": x1, "y": y1, "w": cell_w, "h": cell_h,
                        "intensity": round(changed / total, 2),
                        "position": self._get_position_name(gx, gy, grid_size)
                    })
        
        return regions
    
    def _detect_edges(self, gray: 'Image') -> Dict:
        """Detect edges to identify object boundaries."""
        try:
            # Apply edge detection filter
            edges = gray.filter(ImageFilter.FIND_EDGES)
            
            # Find vertical edges (often indicate standing people)
            objects = []
            width, height = edges.size
            
            # Scan for vertical edge patterns
            for x in range(0, width, width // 8):
                col_sum = 0
                for y in range(height):
                    pixel = edges.getpixel((min(x, width-1), y))
                    if pixel > 50:
                        col_sum += 1
                
                if col_sum > height * 0.3:  # Strong vertical edge
                    objects.append({
                        "type": "vertical_edge",
                        "x": x,
                        "strength": col_sum / height
                    })
            
            return {"objects": objects}
        except Exception as e:
            logger.debug(f"Edge detection error: {e}")
            return {"objects": []}
    
    def _analyze_for_person(self, analysis: Dict, img_size: Tuple[int, int]) -> Dict:
        """Analyze motion patterns to determine if person is present."""
        regions = analysis.get("motion_regions", [])
        motion_pct = analysis.get("motion_percent", 0)
        
        if not regions:
            return {"likely_person": False, "person_confidence": 0.0}
        
        # Heuristics for person detection:
        # 1. Motion in upper part (head/torso)
        # 2. Vertical motion pattern
        # 3. Medium-sized motion area
        
        confidence = 0.0
        width, height = img_size
        
        # Check for motion in person-likely areas
        upper_motion = [r for r in regions if r["y"] < height * 0.6]
        if upper_motion:
            confidence += 0.3
        
        # Check motion intensity (person moves moderately)
        if 0.5 < motion_pct < 15:
            confidence += 0.2
        
        # Check for multiple adjacent regions (body shape)
        if 2 <= len(regions) <= 8:
            confidence += 0.2
        
        # Check for consistent motion area
        if regions:
            xs = [r["x"] for r in regions]
            ys = [r["y"] for r in regions]
            spread_x = (max(xs) - min(xs)) / width
            spread_y = (max(ys) - min(ys)) / height
            
            if 0.1 < spread_x < 0.5 and 0.1 < spread_y < 0.6:
                confidence += 0.3
        
        return {
            "likely_person": confidence > 0.5,
            "person_confidence": round(confidence, 2)
        }
    
    def _get_position_name(self, gx: int, gy: int, grid: int) -> str:
        """Convert grid position to human-readable location."""
        h_pos = "left" if gx < grid // 3 else ("right" if gx >= grid * 2 // 3 else "center")
        v_pos = "top" if gy < grid // 3 else ("bottom" if gy >= grid * 2 // 3 else "middle")
        return f"{v_pos}-{h_pos}"
    
    def _create_annotated_frame(self, original_path: Path, img: 'Image', 
                                 analysis: Dict) -> Path:
        """Create annotated frame with motion regions highlighted."""
        try:
            annotated = img.copy()
            draw = ImageDraw.Draw(annotated)
            
            # Draw motion regions
            for region in analysis.get("motion_regions", []):
                x, y, w, h = region["x"], region["y"], region["w"], region["h"]
                draw.rectangle([x, y, x + w, y + h], outline=(255, 0, 0), width=2)
            
            # Add analysis info overlay
            info_text = []
            if analysis.get("has_motion"):
                info_text.append(f"Motion: {analysis['motion_percent']:.1f}%")
            if analysis.get("likely_person"):
                info_text.append(f"Person likely ({analysis['person_confidence']:.0%})")
            
            if info_text:
                text = " | ".join(info_text)
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
                except Exception:
                    font = ImageFont.load_default()
                
                bbox = draw.textbbox((10, 10), text, font=font)
                draw.rectangle([bbox[0]-5, bbox[1]-5, bbox[2]+5, bbox[3]+5], fill=(0, 0, 0, 180))
                draw.text((10, 10), text, fill=(255, 255, 0), font=font)
            
            # Save annotated frame
            annotated_path = original_path.parent / f"annotated_{original_path.name}"
            annotated.save(annotated_path, quality=90)
            
            return annotated_path
            
        except Exception as e:
            logger.debug(f"Annotation failed: {e}")
            return original_path
    
    def reset(self):
        """Reset analyzer state."""
        self._prev_frame = None
        self._prev_gray = None
        self._motion_history = []
