"""
LLM Motion Prompt Generator

Converts DSL motion analysis data into compact, LLM-friendly prompts.
Reduces ~2KB verbose DSL to ~300-500 bytes optimized for fast LLM comprehension.
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ObjectSummary:
    """Summary of a tracked object."""
    id: int
    first_frame: int
    last_frame: int
    path_directions: List[str]
    total_distance: float
    avg_speed: float
    classification: str = "unknown"
    
    def path_string(self) -> str:
        """Convert path to arrow notation: R→D→L"""
        if not self.path_directions:
            return "stationary"
        dir_map = {"RIGHT": "R", "LEFT": "L", "UP": "U", "DOWN": "D", "STATIC": "•"}
        return "→".join(dir_map.get(d, d[0]) for d in self.path_directions)


def analyze_objects(deltas: List['FrameDelta']) -> Dict[int, ObjectSummary]:
    """Analyze all tracked objects across frames."""
    from .frame_diff_dsl import FrameDelta, Direction
    
    objects: Dict[int, ObjectSummary] = {}
    
    for delta in deltas:
        for blob in delta.blobs:
            if blob.id not in objects:
                objects[blob.id] = ObjectSummary(
                    id=blob.id,
                    first_frame=delta.frame_num,
                    last_frame=delta.frame_num,
                    path_directions=[],
                    total_distance=0.0,
                    avg_speed=0.0,
                )
            
            obj = objects[blob.id]
            obj.last_frame = delta.frame_num
            
            # Track velocity/direction
            vel_mag = (blob.velocity.x**2 + blob.velocity.y**2)**0.5
            if vel_mag > 0.01:
                obj.total_distance += vel_mag
                # Determine dominant direction
                if abs(blob.velocity.x) > abs(blob.velocity.y):
                    direction = "RIGHT" if blob.velocity.x > 0 else "LEFT"
                else:
                    direction = "DOWN" if blob.velocity.y > 0 else "UP"
                
                if not obj.path_directions or obj.path_directions[-1] != direction:
                    obj.path_directions.append(direction)
        
        # Check events for classification hints
        for event in delta.events:
            if event.blob_id in objects:
                obj = objects[event.blob_id]
                if event.direction.value != "STATIC":
                    pass  # Could add direction from events
    
    # Calculate averages
    for obj in objects.values():
        frames_visible = obj.last_frame - obj.first_frame + 1
        obj.avg_speed = obj.total_distance / frames_visible if frames_visible > 0 else 0
        
        # Simple classification based on movement
        if obj.total_distance > 0.1:
            obj.classification = "moving"
        elif obj.total_distance > 0.02:
            obj.classification = "slight_movement"
        else:
            obj.classification = "stationary"
    
    return objects


def generate_timeline(deltas: List['FrameDelta']) -> List[str]:
    """Generate compact timeline."""
    timeline = []
    
    for delta in deltas:
        events = []
        
        # Motion level
        motion_level = "HIGH" if delta.motion_percent > 50 else "MED" if delta.motion_percent > 10 else "LOW"
        
        # Collect events
        appears = []
        moves = []
        disappears = []
        
        for evt in delta.events:
            if evt.type.value == "APPEAR":
                appears.append(str(evt.blob_id))
            elif evt.type.value == "MOVE":
                dir_short = evt.direction.value[0] if evt.direction.value != "STATIC" else "•"
                moves.append(f"#{evt.blob_id}{dir_short}")
            elif evt.type.value == "DISAPPEAR":
                disappears.append(str(evt.blob_id))
            elif evt.type.value in ("ENTER", "EXIT"):
                events.append(f"{evt.type.value}:#{evt.blob_id}")
        
        parts = [f"F{delta.frame_num}: {motion_level}"]
        if appears:
            parts.append(f"+#{','.join(appears)}")
        if moves:
            parts.append(f"[{' '.join(moves)}]")
        if disappears:
            parts.append(f"-#{','.join(disappears)}")
        if events:
            parts.extend(events)
        
        timeline.append(" ".join(parts))
    
    return timeline


def classify_scene(objects: Dict[int, ObjectSummary], deltas: List['FrameDelta']) -> str:
    """Classify overall scene activity."""
    if not objects:
        return "empty_scene"
    
    moving_objects = [o for o in objects.values() if o.classification == "moving"]
    avg_motion = sum(d.motion_percent for d in deltas) / len(deltas) if deltas else 0
    
    if len(moving_objects) == 0:
        return "static_scene"
    elif len(moving_objects) == 1 and moving_objects[0].total_distance > 0.15:
        return "single_traversal"  # One object moving across scene
    elif len(moving_objects) > 2:
        return "multi_activity"
    elif avg_motion > 50:
        return "high_activity"
    else:
        return "low_activity"


def generate_motion_prompt(
    deltas: List['FrameDelta'],
    question: str = "Describe what is happening in this scene.",
    include_timeline: bool = True,
    max_objects: int = 5,
) -> str:
    """
    Generate compact LLM-friendly prompt from motion analysis data.
    
    Args:
        deltas: List of FrameDelta objects from analysis
        question: Question for the LLM to answer
        include_timeline: Include frame-by-frame timeline
        max_objects: Max objects to include in summary
        
    Returns:
        Compact prompt string (~300-500 bytes)
    """
    if not deltas:
        return f"No motion data available.\n\nQuestion: {question}"
    
    # Analyze
    objects = analyze_objects(deltas)
    scene_type = classify_scene(objects, deltas)
    
    # Calculate stats
    duration = deltas[-1].timestamp - deltas[0].timestamp if len(deltas) > 1 else 0
    avg_motion = sum(d.motion_percent for d in deltas) / len(deltas)
    
    # Build prompt
    lines = [
        "MOTION_ANALYSIS",
        f"Duration: {duration:.0f}s | Frames: {len(deltas)} | Objects: {len(objects)} | Scene: {scene_type}",
        "",
        "OBJECTS:"
    ]
    
    # Sort objects by importance (distance traveled)
    sorted_objects = sorted(objects.values(), key=lambda o: o.total_distance, reverse=True)
    
    for obj in sorted_objects[:max_objects]:
        frames_str = f"{obj.first_frame}-{obj.last_frame}" if obj.first_frame != obj.last_frame else str(obj.first_frame)
        path = obj.path_string()
        lines.append(f"  #{obj.id}: F{frames_str}, {path}, dist={obj.total_distance:.2f}, {obj.classification}")
    
    if len(objects) > max_objects:
        lines.append(f"  ... +{len(objects) - max_objects} more objects")
    
    # Timeline (compact)
    if include_timeline:
        lines.append("")
        lines.append("TIMELINE:")
        timeline = generate_timeline(deltas)
        for t in timeline[-6:]:  # Last 6 frames max
            lines.append(f"  {t}")
    
    # Question
    lines.extend(["", f"Question: {question}"])
    
    return "\n".join(lines)


def generate_motion_context(
    deltas: List['FrameDelta'],
    focus: str = "person",
) -> str:
    """
    Generate even more compact context for guarder LLM.
    
    Returns ~100-150 bytes of essential info.
    """
    if not deltas:
        return "No motion data"
    
    objects = analyze_objects(deltas)
    moving = [o for o in objects.values() if o.classification == "moving"]
    
    if not moving:
        return f"Scene: static, {len(objects)} stationary objects"
    
    # Main object summary
    main_obj = max(moving, key=lambda o: o.total_distance)
    path = main_obj.path_string()
    
    avg_motion = sum(d.motion_percent for d in deltas) / len(deltas)
    
    return f"Motion: {avg_motion:.0f}% | Main object #{main_obj.id}: {path}, dist={main_obj.total_distance:.2f} | Total: {len(objects)} objects"


# Export functions
__all__ = [
    "generate_motion_prompt",
    "generate_motion_context", 
    "analyze_objects",
    "ObjectSummary",
]
