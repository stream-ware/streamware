"""
SVG Visualizer for Motion Tracking

Converts frame analysis to SVG vector graphics:
- Object bounding boxes as rectangles
- Motion trajectories as paths
- Velocity vectors as arrows
- Heat maps for motion density

Generates HTML with animated SVG for visualization.
"""

import json
import logging
import math
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============================================================================
# SVG Elements
# ============================================================================

@dataclass
class SVGStyle:
    """SVG styling options."""
    stroke: str = "#00ff00"
    stroke_width: float = 2
    fill: str = "none"
    opacity: float = 1.0
    
    def to_attr(self) -> str:
        return f'stroke="{self.stroke}" stroke-width="{self.stroke_width}" fill="{self.fill}" opacity="{self.opacity}"'


@dataclass
class SVGRect:
    """SVG rectangle element."""
    x: float
    y: float
    width: float
    height: float
    style: SVGStyle = field(default_factory=SVGStyle)
    label: str = ""
    id: str = ""
    
    def to_svg(self, canvas_width: int, canvas_height: int) -> str:
        px = int(self.x * canvas_width)
        py = int(self.y * canvas_height)
        pw = int(self.width * canvas_width)
        ph = int(self.height * canvas_height)
        
        id_attr = f'id="{self.id}"' if self.id else ""
        svg = f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" {self.style.to_attr()} {id_attr}/>'
        
        if self.label:
            svg += f'<text x="{px}" y="{py - 5}" fill="{self.style.stroke}" font-size="12">{self.label}</text>'
        
        return svg


@dataclass
class SVGPath:
    """SVG path element for trajectories."""
    points: List[Tuple[float, float]]
    style: SVGStyle = field(default_factory=SVGStyle)
    id: str = ""
    
    def to_svg(self, canvas_width: int, canvas_height: int) -> str:
        if len(self.points) < 2:
            return ""
        
        px_points = [(int(x * canvas_width), int(y * canvas_height)) for x, y in self.points]
        
        d = f"M {px_points[0][0]} {px_points[0][1]}"
        for x, y in px_points[1:]:
            d += f" L {x} {y}"
        
        id_attr = f'id="{self.id}"' if self.id else ""
        return f'<path d="{d}" {self.style.to_attr()} {id_attr}/>'


@dataclass
class SVGArrow:
    """SVG arrow for velocity vectors."""
    start: Tuple[float, float]
    end: Tuple[float, float]
    style: SVGStyle = field(default_factory=SVGStyle)
    
    def to_svg(self, canvas_width: int, canvas_height: int) -> str:
        x1, y1 = int(self.start[0] * canvas_width), int(self.start[1] * canvas_height)
        x2, y2 = int(self.end[0] * canvas_width), int(self.end[1] * canvas_height)
        
        # Arrow head
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx**2 + dy**2)
        if length < 5:
            return ""
        
        # Normalize
        dx, dy = dx / length, dy / length
        
        # Arrow head points
        head_size = min(10, length * 0.3)
        hx1 = x2 - head_size * (dx + dy * 0.5)
        hy1 = y2 - head_size * (dy - dx * 0.5)
        hx2 = x2 - head_size * (dx - dy * 0.5)
        hy2 = y2 - head_size * (dy + dx * 0.5)
        
        return f'''
        <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {self.style.to_attr()}/>
        <polygon points="{x2},{y2} {hx1:.0f},{hy1:.0f} {hx2:.0f},{hy2:.0f}" fill="{self.style.stroke}"/>
        '''


@dataclass
class SVGCircle:
    """SVG circle for points."""
    cx: float
    cy: float
    r: float = 5
    style: SVGStyle = field(default_factory=SVGStyle)
    
    def to_svg(self, canvas_width: int, canvas_height: int) -> str:
        px = int(self.cx * canvas_width)
        py = int(self.cy * canvas_height)
        return f'<circle cx="{px}" cy="{py}" r="{self.r}" {self.style.to_attr()}/>'


# ============================================================================
# Frame SVG Generator
# ============================================================================

@dataclass
class FrameSVG:
    """SVG representation of a single frame."""
    frame_num: int
    timestamp: float
    width: int
    height: int
    elements: List[Any] = field(default_factory=list)
    background_image: str = ""  # base64 encoded
    
    def to_svg(self) -> str:
        """Generate SVG string."""
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}" width="{self.width}" height="{self.height}">
        <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="#00ff00"/>
            </marker>
        </defs>
        '''
        
        # Background image if provided
        if self.background_image:
            svg += f'<image href="data:image/jpeg;base64,{self.background_image}" width="{self.width}" height="{self.height}"/>'
        else:
            svg += f'<rect width="{self.width}" height="{self.height}" fill="#1a1a2e"/>'
        
        # Render elements
        for elem in self.elements:
            svg += elem.to_svg(self.width, self.height)
        
        # Frame info
        svg += f'<text x="10" y="20" fill="white" font-size="14">Frame {self.frame_num}</text>'
        
        svg += '</svg>'
        return svg


# ============================================================================
# Video to SVG Converter
# ============================================================================

class VideoToSVGConverter:
    """
    Converts video analysis to SVG animation.
    
    Creates vector representation of:
    - Object positions and movements
    - Trajectories over time
    - Velocity fields
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
        
        self.frames: List[FrameSVG] = []
        self.trajectories: Dict[int, List[Tuple[float, float]]] = defaultdict(list)
        self.colors = self._generate_colors(20)
    
    def _generate_colors(self, n: int) -> List[str]:
        """Generate distinct colors for objects."""
        colors = []
        for i in range(n):
            hue = i / n
            # HSV to RGB (simplified)
            r = int(255 * abs(math.sin(hue * 6.28)))
            g = int(255 * abs(math.sin((hue + 0.33) * 6.28)))
            b = int(255 * abs(math.sin((hue + 0.66) * 6.28)))
            colors.append(f"#{r:02x}{g:02x}{b:02x}")
        return colors
    
    def add_frame(
        self,
        frame_num: int,
        timestamp: float,
        detections: List[Dict],
        motion_vectors: List[Tuple[Tuple[float, float], Tuple[float, float]]] = None,
        background_base64: str = "",
    ):
        """
        Add frame to SVG sequence.
        
        Args:
            frame_num: Frame number
            timestamp: Frame timestamp
            detections: List of detection dicts with x, y, w, h, id, class_name
            motion_vectors: Optional list of (start, end) motion vectors
            background_base64: Optional base64 encoded background image
        """
        frame = FrameSVG(
            frame_num=frame_num,
            timestamp=timestamp,
            width=self.width,
            height=self.height,
            background_image=background_base64 if self.include_background else "",
        )
        
        # Add detection boxes
        for det in detections:
            obj_id = det.get('id', 0)
            color = self.colors[obj_id % len(self.colors)]
            
            # Bounding box
            style = SVGStyle(stroke=color, stroke_width=2, fill="none", opacity=0.8)
            box = SVGRect(
                x=det['x'] - det['w']/2,
                y=det['y'] - det['h']/2,
                width=det['w'],
                height=det['h'],
                style=style,
                label=f"{det.get('class_name', 'obj')} #{obj_id}",
                id=f"obj_{obj_id}_{frame_num}"
            )
            frame.elements.append(box)
            
            # Center point
            center_style = SVGStyle(stroke=color, fill=color, opacity=0.9)
            center = SVGCircle(cx=det['x'], cy=det['y'], r=4, style=center_style)
            frame.elements.append(center)
            
            # Update trajectory
            self.trajectories[obj_id].append((det['x'], det['y']))
        
        # Add trajectories
        for obj_id, points in self.trajectories.items():
            if len(points) >= 2:
                color = self.colors[obj_id % len(self.colors)]
                path_style = SVGStyle(stroke=color, stroke_width=1, opacity=0.5)
                path = SVGPath(points=points[-50:], style=path_style)  # Last 50 points
                frame.elements.append(path)
        
        # Add motion vectors
        if motion_vectors:
            arrow_style = SVGStyle(stroke="#ffff00", stroke_width=1, opacity=0.6)
            for start, end in motion_vectors:
                arrow = SVGArrow(start=start, end=end, style=arrow_style)
                frame.elements.append(arrow)
        
        self.frames.append(frame)
    
    def generate_html_animation(
        self,
        output_path: Path,
        fps: float = 2.0,
        title: str = "Motion Analysis",
    ) -> Path:
        """
        Generate HTML file with animated SVG.
        
        Args:
            output_path: Output HTML path
            fps: Animation frames per second
            title: Page title
            
        Returns:
            Path to generated HTML
        """
        frame_duration = int(1000 / fps)  # ms per frame
        
        # Generate SVG frames
        svg_frames = [f.to_svg() for f in self.frames]
        
        # Build trajectory summary
        trajectory_summary = []
        for obj_id, points in self.trajectories.items():
            if len(points) >= 2:
                # Calculate total distance
                distance = sum(
                    math.sqrt((points[i+1][0] - points[i][0])**2 + 
                             (points[i+1][1] - points[i][1])**2)
                    for i in range(len(points) - 1)
                )
                trajectory_summary.append({
                    "id": obj_id,
                    "points": len(points),
                    "distance": round(distance, 4),
                    "color": self.colors[obj_id % len(self.colors)],
                })
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 20px;
            color: #00d9ff;
            text-shadow: 0 0 10px rgba(0, 217, 255, 0.5);
        }}
        .main-content {{
            display: grid;
            grid-template-columns: 1fr 350px;
            gap: 20px;
        }}
        .viewer {{
            background: #0f0f23;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        }}
        #svg-container {{
            border: 2px solid #333;
            border-radius: 8px;
            overflow: hidden;
            background: #1a1a2e;
        }}
        #svg-container svg {{
            display: block;
            width: 100%;
            height: auto;
        }}
        .controls {{
            display: flex;
            gap: 10px;
            margin-top: 15px;
            justify-content: center;
            flex-wrap: wrap;
        }}
        button {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }}
        button:active {{
            transform: translateY(0);
        }}
        .slider-container {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 10px;
            justify-content: center;
        }}
        input[type="range"] {{
            width: 300px;
            accent-color: #667eea;
        }}
        .sidebar {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        .panel {{
            background: #0f0f23;
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.2);
        }}
        .panel h3 {{
            color: #00d9ff;
            margin-bottom: 10px;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .stat {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #333;
        }}
        .stat:last-child {{
            border-bottom: none;
        }}
        .stat-value {{
            color: #00ff88;
            font-weight: bold;
        }}
        .trajectory-list {{
            max-height: 200px;
            overflow-y: auto;
        }}
        .trajectory-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px;
            border-radius: 4px;
            margin-bottom: 5px;
            background: rgba(255, 255, 255, 0.05);
        }}
        .color-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}
        #frame-info {{
            text-align: center;
            color: #888;
            margin-top: 10px;
        }}
        .matrix-view {{
            font-family: monospace;
            font-size: 10px;
            background: #000;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            white-space: pre;
            color: #0f0;
        }}
        @media (max-width: 1000px) {{
            .main-content {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 {title}</h1>
        
        <div class="main-content">
            <div class="viewer">
                <div id="svg-container"></div>
                
                <div class="controls">
                    <button onclick="prevFrame()">⏮ Prev</button>
                    <button onclick="togglePlay()" id="play-btn">▶ Play</button>
                    <button onclick="nextFrame()">Next ⏭</button>
                    <button onclick="resetView()">🔄 Reset</button>
                    <button onclick="exportSVG()">💾 Export SVG</button>
                </div>
                
                <div class="slider-container">
                    <span>Frame:</span>
                    <input type="range" id="frame-slider" min="0" max="{len(self.frames) - 1}" value="0" onchange="goToFrame(this.value)">
                    <span id="frame-info">1 / {len(self.frames)}</span>
                </div>
                
                <div class="slider-container">
                    <span>Speed:</span>
                    <input type="range" id="speed-slider" min="100" max="2000" value="{frame_duration}" onchange="setSpeed(this.value)">
                    <span id="speed-info">{fps:.1f} FPS</span>
                </div>
            </div>
            
            <div class="sidebar">
                <div class="panel">
                    <h3>📊 Statistics</h3>
                    <div class="stat">
                        <span>Total Frames</span>
                        <span class="stat-value">{len(self.frames)}</span>
                    </div>
                    <div class="stat">
                        <span>Objects Tracked</span>
                        <span class="stat-value">{len(self.trajectories)}</span>
                    </div>
                    <div class="stat">
                        <span>Canvas Size</span>
                        <span class="stat-value">{self.width}x{self.height}</span>
                    </div>
                </div>
                
                <div class="panel">
                    <h3>🎯 Trajectories</h3>
                    <div class="trajectory-list">
                        {"".join(f'''
                        <div class="trajectory-item">
                            <div class="color-dot" style="background: {t['color']}"></div>
                            <span>Object #{t['id']}</span>
                            <span style="margin-left: auto; color: #888;">{t['points']} pts, d={t['distance']:.2f}</span>
                        </div>
                        ''' for t in trajectory_summary)}
                    </div>
                </div>
                
                <div class="panel">
                    <h3>📐 Motion Matrix</h3>
                    <div class="matrix-view" id="motion-matrix">
Loading...
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const frames = {json.dumps(svg_frames)};
        let currentFrame = 0;
        let isPlaying = false;
        let playInterval = null;
        let frameDelay = {frame_duration};
        
        const container = document.getElementById('svg-container');
        const slider = document.getElementById('frame-slider');
        const frameInfo = document.getElementById('frame-info');
        const playBtn = document.getElementById('play-btn');
        const matrixView = document.getElementById('motion-matrix');
        
        function showFrame(index) {{
            if (index >= 0 && index < frames.length) {{
                currentFrame = index;
                container.innerHTML = frames[index];
                slider.value = index;
                frameInfo.textContent = `${{index + 1}} / ${{frames.length}}`;
                updateMatrix();
            }}
        }}
        
        function nextFrame() {{
            showFrame((currentFrame + 1) % frames.length);
        }}
        
        function prevFrame() {{
            showFrame((currentFrame - 1 + frames.length) % frames.length);
        }}
        
        function goToFrame(index) {{
            showFrame(parseInt(index));
        }}
        
        function togglePlay() {{
            isPlaying = !isPlaying;
            playBtn.textContent = isPlaying ? '⏸ Pause' : '▶ Play';
            
            if (isPlaying) {{
                playInterval = setInterval(nextFrame, frameDelay);
            }} else {{
                clearInterval(playInterval);
            }}
        }}
        
        function setSpeed(ms) {{
            frameDelay = parseInt(ms);
            document.getElementById('speed-info').textContent = `${{(1000/frameDelay).toFixed(1)}} FPS`;
            
            if (isPlaying) {{
                clearInterval(playInterval);
                playInterval = setInterval(nextFrame, frameDelay);
            }}
        }}
        
        function resetView() {{
            showFrame(0);
            if (isPlaying) {{
                togglePlay();
            }}
        }}
        
        function exportSVG() {{
            const svgContent = frames[currentFrame];
            const blob = new Blob([svgContent], {{type: 'image/svg+xml'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `frame_${{currentFrame}}.svg`;
            a.click();
            URL.revokeObjectURL(url);
        }}
        
        function updateMatrix() {{
            // Simple visualization of motion
            const svg = container.querySelector('svg');
            if (!svg) return;
            
            const rects = svg.querySelectorAll('rect[id^="obj_"]');
            let matrix = 'Objects in frame ' + (currentFrame + 1) + ':\\n\\n';
            
            rects.forEach(rect => {{
                const id = rect.getAttribute('id');
                const x = parseInt(rect.getAttribute('x'));
                const y = parseInt(rect.getAttribute('y'));
                const w = parseInt(rect.getAttribute('width'));
                const h = parseInt(rect.getAttribute('height'));
                matrix += `${{id}}:\\n  pos: (${{x}}, ${{y}})\\n  size: ${{w}}x${{h}}\\n\\n`;
            }});
            
            if (matrix === 'Objects in frame ' + (currentFrame + 1) + ':\\n\\n') {{
                matrix += 'No objects detected';
            }}
            
            matrixView.textContent = matrix;
        }}
        
        // Initialize
        showFrame(0);
        
        // Keyboard controls
        document.addEventListener('keydown', (e) => {{
            switch(e.key) {{
                case 'ArrowLeft': prevFrame(); break;
                case 'ArrowRight': nextFrame(); break;
                case ' ': togglePlay(); e.preventDefault(); break;
            }}
        }});
    </script>
</body>
</html>'''
        
        output_path = Path(output_path)
        output_path.write_text(html)
        
        logger.info(f"Generated HTML animation: {output_path}")
        return output_path
    
    def reset(self):
        """Reset converter state."""
        self.frames.clear()
        self.trajectories.clear()


# ============================================================================
# DSL for Motion Analysis Orchestration
# ============================================================================

class MotionAnalysisDSL:
    """
    Domain-Specific Language for motion analysis orchestration.
    
    Example DSL:
        ANALYZE stream://camera
        DETECT objects WITH yolo
        TRACK objects WITH kalman
        EXTRACT motion_regions
        CONVERT TO svg
        ANIMATE AT 2fps
        OUTPUT TO analysis.html
    """
    
    def __init__(self):
        self.source = None
        self.detector = None
        self.tracker = None
        self.extractor = None
        self.converter = None
        self.output_path = None
        self.fps = 2.0
        
        self._commands = []
    
    def parse(self, dsl_script: str) -> 'MotionAnalysisDSL':
        """Parse DSL script."""
        lines = dsl_script.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.upper().split()
            if not parts:
                continue
            
            cmd = parts[0]
            args = line[len(cmd):].strip()
            
            self._commands.append((cmd, args))
        
        return self
    
    def execute(self) -> Path:
        """Execute parsed DSL commands."""
        from .motion_tracker import (
            MultiObjectTracker, MotionRegionExtractor, OpticalFlowAnalyzer
        )
        
        for cmd, args in self._commands:
            if cmd == 'ANALYZE':
                self.source = args
            elif cmd == 'DETECT':
                self.detector = 'yolo' if 'YOLO' in args.upper() else 'hog'
            elif cmd == 'TRACK':
                self.tracker = MultiObjectTracker()
            elif cmd == 'EXTRACT':
                self.extractor = MotionRegionExtractor()
            elif cmd == 'CONVERT':
                self.converter = VideoToSVGConverter()
            elif cmd == 'ANIMATE':
                # Parse FPS
                if 'FPS' in args.upper():
                    try:
                        self.fps = float(args.upper().replace('FPS', '').replace('AT', '').strip())
                    except ValueError:
                        pass
            elif cmd == 'OUTPUT':
                self.output_path = args.replace('TO', '').strip()
        
        # Execute pipeline
        if self.converter and self.output_path:
            return self.converter.generate_html_animation(
                Path(self.output_path),
                fps=self.fps
            )
        
        return None
    
    @classmethod
    def from_string(cls, script: str) -> 'MotionAnalysisDSL':
        """Create and parse DSL from string."""
        dsl = cls()
        return dsl.parse(script)


# ============================================================================
# Convenience function to create analysis
# ============================================================================

def create_motion_analysis_html(
    frames_data: List[Dict],
    output_path: str = "motion_analysis.html",
    title: str = "Motion Analysis",
    width: int = 800,
    height: int = 600,
    fps: float = 2.0,
) -> Path:
    """
    Create HTML motion analysis from frame data.
    
    Args:
        frames_data: List of dicts with frame_num, timestamp, detections
        output_path: Output HTML path
        title: Page title
        width: Canvas width
        height: Canvas height
        fps: Animation FPS
        
    Returns:
        Path to generated HTML
    """
    converter = VideoToSVGConverter(width=width, height=height)
    
    for frame in frames_data:
        converter.add_frame(
            frame_num=frame.get('frame_num', 0),
            timestamp=frame.get('timestamp', time.time()),
            detections=frame.get('detections', []),
            motion_vectors=frame.get('motion_vectors', []),
        )
    
    return converter.generate_html_animation(Path(output_path), fps=fps, title=title)
