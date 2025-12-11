/**
 * Motion Player JS - DSL-based motion analysis viewer
 * 
 * Parses DSL text and renders SVG animations on-the-fly.
 * No pre-rendered SVGs needed - 95% smaller file size.
 * 
 * Usage:
 *   MotionPlayer.init({
 *     dsl: "FRAME 1 @ ...",
 *     backgrounds: { 1: "base64...", 2: "base64..." },
 *     container: document.getElementById('player'),
 *     width: 800,
 *     height: 600
 *   });
 */

const MotionPlayer = (function() {
    // Blob colors palette
    const COLORS = [
        '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4',
        '#ffeaa7', '#dfe6e9', '#fd79a8', '#a29bfe',
        '#74b9ff', '#55efc4', '#ffeaa7', '#fab1a0'
    ];
    
    // State
    let frames = [];
    let backgrounds = {};
    let currentFrame = 0;
    let playing = false;
    let playInterval = null;
    let config = { width: 800, height: 600, fps: 2 };
    
    // DOM elements
    let canvas, slider, frameInfo, dslPre, eventList, statsPanel;
    
    /**
     * Parse DSL text into frame objects
     */
    function parseDSL(dslText) {
        const lines = dslText.split('\n');
        const parsedFrames = [];
        let currentFrameData = null;
        
        for (const line of lines) {
            const trimmed = line.trim();
            
            // New frame
            if (trimmed.startsWith('FRAME ')) {
                if (currentFrameData) {
                    parsedFrames.push(currentFrameData);
                }
                const match = trimmed.match(/FRAME (\d+) @ ([\d:\.]+)/);
                currentFrameData = {
                    num: match ? parseInt(match[1]) : parsedFrames.length + 1,
                    time: match ? match[2] : '',
                    motion: 0,
                    blobs: [],
                    events: [],
                    tracks: []
                };
            }
            // Delta info
            else if (trimmed.startsWith('DELTA ')) {
                const match = trimmed.match(/motion_pct=([\d.]+)%/);
                if (match && currentFrameData) {
                    currentFrameData.motion = parseFloat(match[1]);
                }
            }
            // Blob
            else if (trimmed.startsWith('BLOB ')) {
                const match = trimmed.match(/id=(\d+) pos=\(([\d.]+),([\d.]+)\) size=\(([\d.]+),([\d.]+)\) vel=\(([-\d.]+),([-\d.]+)\)/);
                if (match && currentFrameData) {
                    currentFrameData.blobs.push({
                        id: parseInt(match[1]),
                        x: parseFloat(match[2]),
                        y: parseFloat(match[3]),
                        w: parseFloat(match[4]),
                        h: parseFloat(match[5]),
                        vx: parseFloat(match[6]),
                        vy: parseFloat(match[7])
                    });
                }
            }
            // Event
            else if (trimmed.startsWith('EVENT ')) {
                const match = trimmed.match(/type=(\w+) blob=(\d+)(?: dir=(\w+))?(?: speed=([\d.]+))?/);
                if (match && currentFrameData) {
                    currentFrameData.events.push({
                        type: match[1],
                        blobId: parseInt(match[2]),
                        dir: match[3] || '',
                        speed: match[4] ? parseFloat(match[4]) : 0
                    });
                }
            }
            // Track
            else if (trimmed.startsWith('TRACK ')) {
                const match = trimmed.match(/blob=(\d+) frames=(\d+) dist=([\d.]+) speed=([\d.]+)/);
                if (match && currentFrameData) {
                    currentFrameData.tracks.push({
                        blobId: parseInt(match[1]),
                        frames: parseInt(match[2]),
                        dist: parseFloat(match[3]),
                        speed: parseFloat(match[4])
                    });
                }
            }
            // Background image
            else if (trimmed.startsWith('BACKGROUND ')) {
                const match = trimmed.match(/BACKGROUND (.+)/);
                if (match && currentFrameData) {
                    currentFrameData.background = match[1];
                }
            }
        }
        
        // Don't forget last frame
        if (currentFrameData) {
            parsedFrames.push(currentFrameData);
        }
        
        return parsedFrames;
    }
    
    /**
     * Render frame to SVG
     */
    function renderFrame(frameData) {
        const w = config.width;
        const h = config.height;
        
        let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">`;
        
        // Defs for arrows
        svg += `<defs>
            <marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="#ffff00"/>
            </marker>
        </defs>`;
        
        // Background color
        svg += `<rect width="${w}" height="${h}" fill="#1a1a2e"/>`;
        
        // Background image (128px thumbnail)
        const bg = frameData.background || backgrounds[frameData.num];
        if (bg) {
            svg += `<image href="data:image/jpeg;base64,${bg}" width="${w}" height="${h}" preserveAspectRatio="xMidYMid slice" opacity="0.5"/>`;
        }
        
        // Draw blobs
        for (const blob of frameData.blobs) {
            const color = COLORS[blob.id % COLORS.length];
            const cx = blob.x * w;
            const cy = blob.y * h;
            const bw = blob.w * w;
            const bh = blob.h * h;
            
            // Blob rectangle
            svg += `<rect x="${cx - bw/2}" y="${cy - bh/2}" width="${bw}" height="${bh}" 
                    fill="${color}" fill-opacity="0.3" stroke="${color}" stroke-width="2" rx="3"/>`;
            
            // Blob ID label
            svg += `<text x="${cx}" y="${cy - bh/2 - 5}" fill="${color}" font-size="12" 
                    text-anchor="middle" font-family="monospace">#${blob.id}</text>`;
            
            // Velocity arrow
            if (Math.abs(blob.vx) > 0.001 || Math.abs(blob.vy) > 0.001) {
                const scale = 500;
                const ax = cx + blob.vx * scale;
                const ay = cy + blob.vy * scale;
                svg += `<line x1="${cx}" y1="${cy}" x2="${ax}" y2="${ay}" 
                        stroke="#ffff00" stroke-width="2" marker-end="url(#arrow)"/>`;
            }
            
            // Center dot
            svg += `<circle cx="${cx}" cy="${cy}" r="4" fill="${color}"/>`;
        }
        
        // Frame info overlay
        svg += `<text x="10" y="25" fill="#00d9ff" font-size="14" font-family="monospace">
            Frame ${frameData.num} | Motion: ${frameData.motion.toFixed(1)}% | Blobs: ${frameData.blobs.length}
        </text>`;
        
        svg += '</svg>';
        return svg;
    }
    
    /**
     * Show specific frame
     */
    function showFrame(idx) {
        if (idx < 0 || idx >= frames.length) return;
        
        currentFrame = idx;
        const frameData = frames[idx];
        
        // Render SVG
        if (canvas) {
            canvas.innerHTML = renderFrame(frameData);
        }
        
        // Update controls
        if (slider) {
            slider.value = idx;
            slider.max = frames.length - 1;
        }
        if (frameInfo) {
            frameInfo.textContent = `${idx + 1}/${frames.length}`;
        }
        
        // Highlight DSL
        highlightDSL(frameData.num);
        
        // Update events
        updateEvents(frameData);
    }
    
    /**
     * Highlight current frame in DSL output
     */
    function highlightDSL(frameNum) {
        if (!dslPre) return;
        
        const text = dslPre.dataset.original || dslPre.textContent;
        dslPre.dataset.original = text;
        
        const lines = text.split('\n');
        let html = '';
        let inFrame = false;
        
        for (const line of lines) {
            const escaped = escapeHtml(line);
            if (line.startsWith('FRAME ' + frameNum + ' ')) {
                inFrame = true;
                html += `<span class="dsl-highlight">${escaped}</span>\n`;
            } else if (line.startsWith('FRAME ') && inFrame) {
                inFrame = false;
                html += escaped + '\n';
            } else if (inFrame) {
                html += `<span class="dsl-highlight">${escaped}</span>\n`;
            } else {
                html += escaped + '\n';
            }
        }
        
        dslPre.innerHTML = html;
    }
    
    /**
     * Update events panel
     */
    function updateEvents(frameData) {
        if (!eventList) return;
        
        let html = '';
        for (const evt of frameData.events) {
            const dirStr = evt.dir ? ` ${evt.dir}` : '';
            html += `<div class="event-item event-${evt.type}">F${frameData.num}: ${evt.type} blob=${evt.blobId}${dirStr}</div>`;
        }
        eventList.innerHTML = html || '<div style="color:#666">No events</div>';
    }
    
    /**
     * Update stats panel
     */
    function updateStats() {
        if (!statsPanel) return;
        
        const totalFrames = frames.length;
        const avgMotion = frames.reduce((sum, f) => sum + f.motion, 0) / totalFrames;
        const maxBlobs = Math.max(...frames.map(f => f.blobs.length));
        const totalEvents = frames.reduce((sum, f) => sum + f.events.length, 0);
        
        statsPanel.innerHTML = `
            <div class="stat-row"><span>Total Frames</span><span class="stat-value">${totalFrames}</span></div>
            <div class="stat-row"><span>Avg Motion</span><span class="stat-value">${avgMotion.toFixed(1)}%</span></div>
            <div class="stat-row"><span>Max Blobs</span><span class="stat-value">${maxBlobs}</span></div>
            <div class="stat-row"><span>Total Events</span><span class="stat-value">${totalEvents}</span></div>
        `;
    }
    
    function escapeHtml(text) {
        return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
    
    // Navigation
    function nextFrame() {
        showFrame((currentFrame + 1) % frames.length);
    }
    
    function prevFrame() {
        showFrame((currentFrame - 1 + frames.length) % frames.length);
    }
    
    function togglePlay() {
        playing = !playing;
        const btn = document.getElementById('play-btn');
        if (btn) btn.textContent = playing ? '⏸' : '▶';
        
        if (playing) {
            playInterval = setInterval(nextFrame, 1000 / config.fps);
        } else {
            clearInterval(playInterval);
        }
    }
    
    /**
     * Initialize player
     */
    function init(options) {
        // Parse options
        const dslText = options.dsl || '';
        backgrounds = options.backgrounds || {};
        config.width = options.width || 800;
        config.height = options.height || 600;
        config.fps = options.fps || 2;
        
        // Parse DSL
        frames = parseDSL(dslText);
        
        // Get DOM elements
        const container = options.container || document.body;
        canvas = container.querySelector('.motion-canvas') || container.querySelector('#motion-canvas');
        slider = container.querySelector('#motion-slider') || container.querySelector('input[type="range"]');
        frameInfo = container.querySelector('.frame-info') || container.querySelector('#frame-info');
        dslPre = container.querySelector('.dsl-output pre') || container.querySelector('#dsl-text');
        eventList = container.querySelector('.event-list');
        statsPanel = container.querySelector('.stats-content') || container.querySelector('.motion-panel:first-child');
        
        // Setup controls
        if (slider) {
            slider.max = frames.length - 1;
            slider.oninput = (e) => showFrame(parseInt(e.target.value));
        }
        
        // Keyboard controls
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowRight') nextFrame();
            else if (e.key === 'ArrowLeft') prevFrame();
            else if (e.key === ' ') { togglePlay(); e.preventDefault(); }
        });
        
        // Update stats
        updateStats();
        
        // Show first frame
        if (frames.length > 0) {
            showFrame(0);
        }
        
        console.log(`MotionPlayer initialized: ${frames.length} frames`);
    }
    
    // Public API
    return {
        init,
        nextFrame,
        prevFrame,
        togglePlay,
        goToFrame: showFrame,
        getFrames: () => frames,
        getCurrentFrame: () => currentFrame
    };
})();

// Auto-init if data attribute present
document.addEventListener('DOMContentLoaded', () => {
    const container = document.querySelector('[data-motion-player]');
    if (container) {
        const dslEl = document.querySelector('#motion-dsl');
        const bgEl = document.querySelector('#motion-backgrounds');
        
        MotionPlayer.init({
            container,
            dsl: dslEl ? dslEl.textContent : '',
            backgrounds: bgEl ? JSON.parse(bgEl.textContent) : {},
            width: parseInt(container.dataset.width) || 800,
            height: parseInt(container.dataset.height) || 600,
            fps: parseFloat(container.dataset.fps) || 2
        });
    }
});
