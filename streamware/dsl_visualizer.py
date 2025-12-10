"""
DSL Visualizer - Converts DSL metadata to SVG/HTML visualization

Takes frame_diff_dsl output and creates:
1. Real-time console visualization (ASCII)
2. SVG frames for each analyzed frame
3. Interactive HTML with animation
4. Motion heatmap
"""

import logging
import time
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

logger = logging.getLogger(__name__)


# ============================================================================
# ASCII Visualizer for Console
# ============================================================================

class ASCIIVisualizer:
    """
    Real-time ASCII visualization for console.
    
    Shows motion regions as characters in a grid.
    """
    
    CHARS = " ·░▒▓█"  # Intensity levels
    
    def __init__(self, width: int = 60, height: int = 20):
        self.width = width
        self.height = height
    
    def render(self, delta: 'FrameDelta') -> str:
        """Render frame delta as ASCII art."""
        from .frame_diff_dsl import FrameDelta
        
        # Create empty grid
        grid = [[' ' for _ in range(self.width)] for _ in range(self.height)]
        
        # Draw motion mask if available
        if delta.motion_mask is not None:
            h, w = delta.motion_mask.shape
            for y in range(self.height):
                for x in range(self.width):
                    # Sample from mask
                    my = int(y * h / self.height)
                    mx = int(x * w / self.width)
                    val = delta.motion_mask[my, mx]
                    
                    if val > 200:
                        grid[y][x] = '█'
                    elif val > 100:
                        grid[y][x] = '▓'
                    elif val > 50:
                        grid[y][x] = '░'
        
        # Draw blobs
        for blob in delta.blobs:
            cx = int(blob.center.x * self.width)
            cy = int(blob.center.y * self.height)
            
            # Draw bounding box
            x1 = max(0, int((blob.center.x - blob.size.x/2) * self.width))
            y1 = max(0, int((blob.center.y - blob.size.y/2) * self.height))
            x2 = min(self.width-1, int((blob.center.x + blob.size.x/2) * self.width))
            y2 = min(self.height-1, int((blob.center.y + blob.size.y/2) * self.height))
            
            # Top and bottom edges
            for x in range(x1, x2+1):
                if 0 <= y1 < self.height:
                    grid[y1][x] = '─'
                if 0 <= y2 < self.height:
                    grid[y2][x] = '─'
            
            # Left and right edges
            for y in range(y1, y2+1):
                if 0 <= x1 < self.width:
                    grid[y][x1] = '│'
                if 0 <= x2 < self.width:
                    grid[y][x2] = '│'
            
            # Corners
            if 0 <= y1 < self.height and 0 <= x1 < self.width:
                grid[y1][x1] = '┌'
            if 0 <= y1 < self.height and 0 <= x2 < self.width:
                grid[y1][x2] = '┐'
            if 0 <= y2 < self.height and 0 <= x1 < self.width:
                grid[y2][x1] = '└'
            if 0 <= y2 < self.height and 0 <= x2 < self.width:
                grid[y2][x2] = '┘'
            
            # Center marker with ID
            if 0 <= cy < self.height and 0 <= cx < self.width:
                grid[cy][cx] = str(blob.id % 10)
            
            # Velocity arrow
            if blob.velocity.magnitude() > 0.01:
                vx = int(blob.velocity.x * self.width * 3)
                vy = int(blob.velocity.y * self.height * 3)
                ax = cx + vx
                ay = cy + vy
                if 0 <= ay < self.height and 0 <= ax < self.width:
                    if abs(vx) > abs(vy):
                        grid[ay][ax] = '→' if vx > 0 else '←'
                    else:
                        grid[ay][ax] = '↓' if vy > 0 else '↑'
        
        # Build output
        lines = []
        lines.append(f"┌{'─' * self.width}┐ Frame {delta.frame_num}")
        for row in grid:
            lines.append(f"│{''.join(row)}│")
        lines.append(f"└{'─' * self.width}┘ Motion: {delta.motion_percent:.1f}%")
        
        # Add blob info
        for blob in delta.blobs:
            cls = blob.classification if blob.classification != "UNKNOWN" else "?"
            lines.append(f"  [{blob.id}] {cls} at ({blob.center.x:.2f},{blob.center.y:.2f}) vel=({blob.velocity.x:.3f},{blob.velocity.y:.3f})")
        
        return '\n'.join(lines)


# ============================================================================
# SVG Frame Generator
# ============================================================================

class SVGFrameGenerator:
    """
    Generates SVG frames from DSL analysis.
    """
    
    # Color palette for blobs
    COLORS = [
        "#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", 
        "#ffeaa7", "#dfe6e9", "#fd79a8", "#a29bfe"
    ]
    
    def __init__(self, width: int = 800, height: int = 600):
        self.width = width
        self.height = height
        self.trajectories: Dict[int, List[Tuple[float, float]]] = {}
    
    def generate_frame_svg(
        self,
        delta: 'FrameDelta',
        include_motion_mask: bool = True,
        include_edges: bool = True,
    ) -> str:
        """Generate SVG for single frame."""
        from .frame_diff_dsl import FrameDelta, EventType
        
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}" width="{self.width}" height="{self.height}">',
            '<defs>',
            '  <marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">',
            '    <polygon points="0 0, 10 3.5, 0 7" fill="#ffff00"/>',
            '  </marker>',
            '</defs>',
            # Background
            f'<rect width="{self.width}" height="{self.height}" fill="#1a1a2e"/>',
        ]
        
        # Motion mask as semi-transparent overlay
        if include_motion_mask and delta.motion_mask is not None:
            svg_parts.append(self._motion_mask_to_svg(delta.motion_mask))
        
        # Edge map
        if include_edges and delta.edge_map is not None:
            svg_parts.append(self._edge_map_to_svg(delta.edge_map))
        
        # Draw trajectories
        for blob in delta.blobs:
            if blob.id not in self.trajectories:
                self.trajectories[blob.id] = []
            self.trajectories[blob.id].append((blob.center.x, blob.center.y))
            
            # Draw trajectory path
            points = self.trajectories[blob.id][-50:]  # Last 50 points
            if len(points) >= 2:
                color = self.COLORS[blob.id % len(self.COLORS)]
                path_d = f"M {points[0][0] * self.width} {points[0][1] * self.height}"
                for px, py in points[1:]:
                    path_d += f" L {px * self.width} {py * self.height}"
                svg_parts.append(f'<path d="{path_d}" stroke="{color}" stroke-width="2" fill="none" opacity="0.5"/>')
        
        # Draw blobs
        for blob in delta.blobs:
            color = self.COLORS[blob.id % len(self.COLORS)]
            
            # Bounding box
            x = (blob.center.x - blob.size.x/2) * self.width
            y = (blob.center.y - blob.size.y/2) * self.height
            w = blob.size.x * self.width
            h = blob.size.y * self.height
            
            svg_parts.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" stroke="{color}" stroke-width="2" fill="none"/>')
            
            # Center point
            cx = blob.center.x * self.width
            cy = blob.center.y * self.height
            svg_parts.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="5" fill="{color}"/>')
            
            # Label
            label = f"#{blob.id}"
            if blob.classification != "UNKNOWN":
                label += f" {blob.classification}"
            svg_parts.append(f'<text x="{x:.0f}" y="{y - 5:.0f}" fill="{color}" font-size="12" font-family="monospace">{label}</text>')
            
            # Velocity arrow
            if blob.velocity.magnitude() > 0.01:
                vx = blob.velocity.x * self.width * 5
                vy = blob.velocity.y * self.height * 5
                svg_parts.append(f'<line x1="{cx:.0f}" y1="{cy:.0f}" x2="{cx + vx:.0f}" y2="{cy + vy:.0f}" stroke="#ffff00" stroke-width="2" marker-end="url(#arrow)"/>')
        
        # Events overlay
        event_y = 30
        for event in delta.events:
            event_text = f"{event.type.value}"
            if event.direction.value != "STATIC":
                event_text += f" {event.direction.value}"
            svg_parts.append(f'<text x="10" y="{event_y}" fill="#00ff88" font-size="11" font-family="monospace">● {event_text} blob={event.blob_id}</text>')
            event_y += 15
        
        # Frame info
        svg_parts.append(f'<text x="{self.width - 150}" y="20" fill="white" font-size="14" font-family="monospace">Frame {delta.frame_num}</text>')
        svg_parts.append(f'<text x="{self.width - 150}" y="40" fill="white" font-size="12" font-family="monospace">Motion: {delta.motion_percent:.1f}%</text>')
        svg_parts.append(f'<text x="{self.width - 150}" y="55" fill="white" font-size="12" font-family="monospace">Blobs: {len(delta.blobs)}</text>')
        
        svg_parts.append('</svg>')
        
        return '\n'.join(svg_parts)
    
    def _motion_mask_to_svg(self, mask) -> str:
        """Convert motion mask to SVG rectangles."""
        # Downsample mask for SVG
        try:
            import cv2
            small = cv2.resize(mask, (40, 30))
        except:
            return ""
        
        cell_w = self.width / 40
        cell_h = self.height / 30
        
        parts = []
        for y in range(30):
            for x in range(40):
                val = small[y, x]
                if val > 50:
                    opacity = min(0.4, val / 255 * 0.5)
                    parts.append(f'<rect x="{x * cell_w:.0f}" y="{y * cell_h:.0f}" width="{cell_w:.0f}" height="{cell_h:.0f}" fill="#00ff00" opacity="{opacity:.2f}"/>')
        
        return '\n'.join(parts)
    
    def _edge_map_to_svg(self, edges) -> str:
        """Convert edge map to SVG."""
        # Downsample and convert to points
        try:
            import cv2
            small = cv2.resize(edges, (80, 60))
        except:
            return ""
        
        points = []
        for y in range(60):
            for x in range(80):
                if small[y, x] > 100:
                    px = x * self.width / 80
                    py = y * self.height / 60
                    points.append(f"{px:.0f},{py:.0f}")
        
        if points:
            return f'<polyline points="{" ".join(points[:500])}" stroke="#ff00ff" stroke-width="1" fill="none" opacity="0.3"/>'
        return ""
    
    def reset(self):
        """Reset generator."""
        self.trajectories.clear()


# ============================================================================
# HTML Animation Generator
# ============================================================================

def generate_dsl_html(
    deltas: List['FrameDelta'],
    dsl_output: str,
    output_path: str = "dsl_analysis.html",
    title: str = "Frame Diff DSL Analysis",
    fps: float = 2.0,
) -> Path:
    """
    Generate interactive HTML from DSL analysis.
    """
    from .frame_diff_dsl import FrameDelta
    
    generator = SVGFrameGenerator()
    svg_frames = []
    
    for delta in deltas:
        svg = generator.generate_frame_svg(delta)
        svg_frames.append(svg)
    
    # Calculate statistics
    total_motion = sum(d.motion_percent for d in deltas) / len(deltas) if deltas else 0
    max_blobs = max(len(d.blobs) for d in deltas) if deltas else 0
    
    # Collect all events
    all_events = []
    for delta in deltas:
        for event in delta.events:
            all_events.append({
                "frame": delta.frame_num,
                "type": event.type.value,
                "blob_id": event.blob_id,
                "direction": event.direction.value,
            })
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Consolas', 'Monaco', monospace;
            background: #0a0a1a;
            color: #eee;
            min-height: 100vh;
        }}
        .container {{
            display: grid;
            grid-template-columns: 1fr 400px;
            height: 100vh;
        }}
        .viewer {{
            padding: 20px;
            display: flex;
            flex-direction: column;
        }}
        h1 {{
            color: #00d9ff;
            margin-bottom: 15px;
            font-size: 18px;
        }}
        #svg-container {{
            flex: 1;
            border: 1px solid #333;
            border-radius: 8px;
            overflow: hidden;
            background: #1a1a2e;
        }}
        #svg-container svg {{
            width: 100%;
            height: 100%;
        }}
        .controls {{
            display: flex;
            gap: 10px;
            margin-top: 15px;
            align-items: center;
        }}
        button {{
            background: #333;
            border: 1px solid #555;
            color: white;
            padding: 8px 15px;
            border-radius: 4px;
            cursor: pointer;
            font-family: inherit;
        }}
        button:hover {{ background: #444; }}
        input[type="range"] {{
            flex: 1;
            accent-color: #00d9ff;
        }}
        .sidebar {{
            background: #111;
            border-left: 1px solid #333;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }}
        .panel {{
            padding: 15px;
            border-bottom: 1px solid #333;
        }}
        .panel h3 {{
            color: #00d9ff;
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 10px;
        }}
        .stat {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            font-size: 12px;
        }}
        .stat-value {{ color: #00ff88; }}
        .dsl-output {{
            flex: 1;
            overflow-y: auto;
            padding: 15px;
        }}
        .dsl-output pre {{
            font-size: 10px;
            line-height: 1.4;
            color: #888;
            white-space: pre-wrap;
        }}
        .dsl-output .highlight {{
            background: #1a3a1a;
            display: block;
        }}
        .event-list {{
            max-height: 150px;
            overflow-y: auto;
            font-size: 11px;
        }}
        .event-item {{
            padding: 3px 5px;
            border-radius: 2px;
            margin: 2px 0;
        }}
        .event-ENTER {{ background: #1a3a1a; color: #00ff88; }}
        .event-EXIT {{ background: #3a1a1a; color: #ff6b6b; }}
        .event-MOVE {{ background: #1a1a3a; color: #4ecdc4; }}
        #frame-info {{
            color: #888;
            font-size: 12px;
            min-width: 80px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="viewer">
            <h1>🎯 {title}</h1>
            <div id="svg-container"></div>
            <div class="controls">
                <button onclick="prevFrame()">⏮</button>
                <button onclick="togglePlay()" id="play-btn">▶</button>
                <button onclick="nextFrame()">⏭</button>
                <input type="range" id="slider" min="0" max="{len(svg_frames)-1}" value="0" oninput="goToFrame(this.value)">
                <span id="frame-info">1/{len(svg_frames)}</span>
            </div>
        </div>
        
        <div class="sidebar">
            <div class="panel">
                <h3>📊 Statistics</h3>
                <div class="stat"><span>Total Frames</span><span class="stat-value">{len(deltas)}</span></div>
                <div class="stat"><span>Avg Motion</span><span class="stat-value">{total_motion:.1f}%</span></div>
                <div class="stat"><span>Max Blobs</span><span class="stat-value">{max_blobs}</span></div>
                <div class="stat"><span>Total Events</span><span class="stat-value">{len(all_events)}</span></div>
            </div>
            
            <div class="panel">
                <h3>⚡ Events</h3>
                <div class="event-list">
                    {"".join(f'<div class="event-item event-{e["type"]}">F{e["frame"]}: {e["type"]} blob={e["blob_id"]} {e["direction"]}</div>' for e in all_events[-20:])}
                </div>
            </div>
            
            <div class="dsl-output">
                <h3 style="color: #00d9ff; font-size: 12px; margin-bottom: 10px;">📝 DSL Output</h3>
                <pre id="dsl-text">{dsl_output}</pre>
            </div>
        </div>
    </div>
    
    <script>
        const frames = {json.dumps(svg_frames)};
        let current = 0;
        let playing = false;
        let interval = null;
        
        const container = document.getElementById('svg-container');
        const slider = document.getElementById('slider');
        const info = document.getElementById('frame-info');
        const dslText = document.getElementById('dsl-text');
        
        function show(idx) {{
            if (idx >= 0 && idx < frames.length) {{
                current = idx;
                container.innerHTML = frames[idx];
                slider.value = idx;
                info.textContent = `${{idx+1}}/${{frames.length}}`;
                highlightDSL(idx + 1);
            }}
        }}
        
        function highlightDSL(frameNum) {{
            const text = dslText.textContent;
            const lines = text.split('\\n');
            let html = '';
            let inFrame = false;
            
            for (const line of lines) {{
                if (line.startsWith('FRAME ' + frameNum + ' ')) {{
                    inFrame = true;
                    html += '<span class="highlight">' + escapeHtml(line) + '</span>\\n';
                }} else if (line.startsWith('FRAME ') && inFrame) {{
                    inFrame = false;
                    html += escapeHtml(line) + '\\n';
                }} else if (inFrame) {{
                    html += '<span class="highlight">' + escapeHtml(line) + '</span>\\n';
                }} else {{
                    html += escapeHtml(line) + '\\n';
                }}
            }}
            
            dslText.innerHTML = html;
        }}
        
        function escapeHtml(text) {{
            return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }}
        
        function nextFrame() {{ show((current + 1) % frames.length); }}
        function prevFrame() {{ show((current - 1 + frames.length) % frames.length); }}
        function goToFrame(idx) {{ show(parseInt(idx)); }}
        
        function togglePlay() {{
            playing = !playing;
            document.getElementById('play-btn').textContent = playing ? '⏸' : '▶';
            if (playing) {{
                interval = setInterval(nextFrame, {int(1000/fps)});
            }} else {{
                clearInterval(interval);
            }}
        }}
        
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowRight') nextFrame();
            else if (e.key === 'ArrowLeft') prevFrame();
            else if (e.key === ' ') {{ togglePlay(); e.preventDefault(); }}
        }});
        
        show(0);
    </script>
</body>
</html>'''
    
    output = Path(output_path)
    output.write_text(html)
    return output
