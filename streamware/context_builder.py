"""
Context Builder - Builds rich LLM context from preprocessed metadata

Instead of asking LLM "what do you see?", we tell it:
"We detected an object that:
- Entered from the left 3 seconds ago
- Has been moving right at 0.02 units/frame
- Size increased 20% (approaching camera)
- Trajectory shows walking pattern
- Shape complexity suggests human form

Confirm: Is this a person? What are they doing?"

This approach:
1. Reduces LLM guesswork
2. Provides temporal context (history)
3. Uses algorithmic analysis to guide LLM
4. Results in more accurate, faster responses
"""

import logging
import time
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Context Data Structures
# ============================================================================

@dataclass
class ObjectHistory:
    """History of tracked object."""
    object_id: int
    first_seen_frame: int
    last_seen_frame: int
    total_frames: int = 0
    
    # Position history
    positions: List[Tuple[float, float]] = field(default_factory=list)
    sizes: List[Tuple[float, float]] = field(default_factory=list)
    
    # Computed metrics
    total_distance: float = 0.0
    avg_speed: float = 0.0
    direction: str = "unknown"
    movement_pattern: str = "unknown"
    
    # Entry/exit info
    entry_direction: str = ""
    entry_time: float = 0.0
    
    # Size changes
    size_change_percent: float = 0.0  # positive = getting bigger (approaching)
    
    # Shape info
    avg_complexity: float = 0.0
    avg_aspect_ratio: float = 1.0
    
    # Classification guess based on shape
    shape_suggests: str = "unknown"


@dataclass  
class SceneContext:
    """Overall scene context."""
    total_frames_analyzed: int = 0
    duration_seconds: float = 0.0
    
    # Motion summary
    avg_motion_percent: float = 0.0
    max_motion_percent: float = 0.0
    motion_events: int = 0
    
    # Objects summary
    objects_detected: int = 0
    objects_currently_visible: int = 0
    
    # Events summary
    enter_events: int = 0
    exit_events: int = 0
    
    # Scene type guess
    scene_activity: str = "unknown"  # static, low_activity, active, busy


@dataclass
class FrameContext:
    """Context for current frame."""
    frame_num: int
    timestamp: float
    
    # Current state
    motion_percent: float = 0.0
    visible_objects: int = 0
    
    # Recent events
    recent_events: List[str] = field(default_factory=list)
    
    # Objects in frame
    objects: List[ObjectHistory] = field(default_factory=list)


# ============================================================================
# Context Builder
# ============================================================================

class ContextBuilder:
    """
    Builds rich context from frame metadata for LLM queries.
    
    Aggregates:
    - Object tracking history
    - Motion patterns
    - Entry/exit events
    - Size changes (depth estimation)
    - Shape analysis
    
    Outputs structured context for LLM prompts.
    """
    
    def __init__(self):
        self.object_histories: Dict[int, ObjectHistory] = {}
        self.scene_context = SceneContext()
        self.recent_events: List[Tuple[int, str]] = []  # (frame, event_desc)
        
        self._start_time = time.time()
        self._frame_count = 0
        self._motion_sum = 0.0
        self._max_motion = 0.0
    
    def update(self, delta: 'FrameDelta') -> FrameContext:
        """
        Update context with new frame delta.
        
        Args:
            delta: FrameDelta from frame_diff_dsl
            
        Returns:
            FrameContext for current frame
        """
        from .frame_diff_dsl import FrameDelta, EventType, Direction
        
        self._frame_count += 1
        self._motion_sum += delta.motion_percent
        self._max_motion = max(self._max_motion, delta.motion_percent)
        
        # Update object histories
        for blob in delta.blobs:
            self._update_object_history(blob, delta.frame_num)
        
        # Process events
        for event in delta.events:
            event_desc = f"{event.type.value}"
            if event.direction.value != "STATIC":
                event_desc += f" from {event.direction.value}"
            
            self.recent_events.append((delta.frame_num, f"Object #{event.blob_id} {event_desc}"))
            
            # Update scene counters
            if event.type == EventType.ENTER:
                self.scene_context.enter_events += 1
                if event.blob_id in self.object_histories:
                    self.object_histories[event.blob_id].entry_direction = event.direction.value
                    self.object_histories[event.blob_id].entry_time = delta.timestamp
            elif event.type == EventType.EXIT:
                self.scene_context.exit_events += 1
        
        # Keep only recent events
        self.recent_events = self.recent_events[-20:]
        
        # Update scene context
        self._update_scene_context(delta)
        
        # Build frame context
        frame_ctx = FrameContext(
            frame_num=delta.frame_num,
            timestamp=delta.timestamp,
            motion_percent=delta.motion_percent,
            visible_objects=len(delta.blobs),
            recent_events=[e[1] for e in self.recent_events[-5:]],
            objects=[self.object_histories[b.id] for b in delta.blobs if b.id in self.object_histories],
        )
        
        return frame_ctx
    
    def _update_object_history(self, blob: 'MotionBlob', frame_num: int):
        """Update history for single object."""
        from .frame_diff_dsl import MotionBlob
        
        if blob.id not in self.object_histories:
            self.object_histories[blob.id] = ObjectHistory(
                object_id=blob.id,
                first_seen_frame=frame_num,
                last_seen_frame=frame_num,
            )
        
        hist = self.object_histories[blob.id]
        hist.last_seen_frame = frame_num
        hist.total_frames += 1
        
        # Add position
        hist.positions.append((blob.center.x, blob.center.y))
        hist.sizes.append((blob.size.x, blob.size.y))
        
        # Calculate metrics if enough history
        if len(hist.positions) >= 2:
            # Total distance
            dist = math.sqrt(
                (hist.positions[-1][0] - hist.positions[-2][0])**2 +
                (hist.positions[-1][1] - hist.positions[-2][1])**2
            )
            hist.total_distance += dist
            hist.avg_speed = hist.total_distance / hist.total_frames
            
            # Direction (overall)
            if len(hist.positions) >= 3:
                start = hist.positions[0]
                end = hist.positions[-1]
                dx = end[0] - start[0]
                dy = end[1] - start[1]
                
                if abs(dx) > abs(dy):
                    hist.direction = "right" if dx > 0 else "left"
                elif abs(dy) > abs(dx):
                    hist.direction = "down" if dy > 0 else "up"
                else:
                    hist.direction = "stationary"
            
            # Size change (depth)
            if len(hist.sizes) >= 3:
                start_size = hist.sizes[0][0] * hist.sizes[0][1]
                end_size = hist.sizes[-1][0] * hist.sizes[-1][1]
                if start_size > 0:
                    hist.size_change_percent = ((end_size - start_size) / start_size) * 100
        
        # Shape analysis
        hist.avg_complexity = (hist.avg_complexity * (hist.total_frames - 1) + blob.complexity) / hist.total_frames
        hist.avg_aspect_ratio = (hist.avg_aspect_ratio * (hist.total_frames - 1) + blob.aspect_ratio) / hist.total_frames
        
        # Guess object type from shape
        hist.shape_suggests = self._guess_object_type(hist)
        
        # Movement pattern analysis
        hist.movement_pattern = self._analyze_movement_pattern(hist)
    
    def _guess_object_type(self, hist: ObjectHistory) -> str:
        """Guess object type from shape characteristics."""
        ar = hist.avg_aspect_ratio
        complexity = hist.avg_complexity
        
        # Aspect ratio hints
        # Person: typically taller than wide (ar < 1), moderate complexity
        # Vehicle: wider than tall (ar > 1.5), low complexity
        # Bird: small, variable aspect ratio, high complexity
        # Animal: variable
        
        if 0.3 < ar < 0.8 and 0.3 < complexity < 0.8:
            return "likely_person"
        elif ar > 1.5 and complexity < 0.4:
            return "likely_vehicle"
        elif hist.avg_speed > 0.05 and complexity > 0.6:
            return "likely_bird"
        elif 0.8 < ar < 1.5 and complexity > 0.5:
            return "likely_animal"
        else:
            return "unknown_object"
    
    def _analyze_movement_pattern(self, hist: ObjectHistory) -> str:
        """Analyze movement pattern from trajectory."""
        if len(hist.positions) < 5:
            return "insufficient_data"
        
        # Calculate speed variance
        speeds = []
        for i in range(1, len(hist.positions)):
            dist = math.sqrt(
                (hist.positions[i][0] - hist.positions[i-1][0])**2 +
                (hist.positions[i][1] - hist.positions[i-1][1])**2
            )
            speeds.append(dist)
        
        if not speeds:
            return "stationary"
        
        avg_speed = sum(speeds) / len(speeds)
        speed_variance = sum((s - avg_speed)**2 for s in speeds) / len(speeds)
        
        # Classify pattern
        if avg_speed < 0.005:
            return "stationary"
        elif speed_variance < 0.0001:
            return "constant_motion"  # Walking, driving
        elif speed_variance > 0.001:
            return "erratic_motion"  # Running, bird flying
        else:
            return "variable_motion"
    
    def _update_scene_context(self, delta: 'FrameDelta'):
        """Update overall scene context."""
        self.scene_context.total_frames_analyzed = self._frame_count
        self.scene_context.duration_seconds = time.time() - self._start_time
        self.scene_context.avg_motion_percent = self._motion_sum / max(1, self._frame_count)
        self.scene_context.max_motion_percent = self._max_motion
        self.scene_context.objects_detected = len(self.object_histories)
        self.scene_context.objects_currently_visible = len(delta.blobs)
        
        # Classify scene activity
        if self.scene_context.avg_motion_percent < 1:
            self.scene_context.scene_activity = "static"
        elif self.scene_context.avg_motion_percent < 5:
            self.scene_context.scene_activity = "low_activity"
        elif self.scene_context.avg_motion_percent < 15:
            self.scene_context.scene_activity = "active"
        else:
            self.scene_context.scene_activity = "busy"
    
    def build_llm_prompt(
        self,
        frame_context: FrameContext,
        focus_object_id: int = None,
        question_type: str = "describe",  # describe, classify, activity
    ) -> str:
        """
        Build rich LLM prompt with all context.
        
        Args:
            frame_context: Current frame context
            focus_object_id: Specific object to ask about (or None for all)
            question_type: Type of question to ask
            
        Returns:
            Formatted prompt string
        """
        parts = []
        
        # Scene overview
        parts.append("=== SCENE ANALYSIS ===")
        parts.append(f"Analyzed {self.scene_context.total_frames_analyzed} frames over {self.scene_context.duration_seconds:.1f}s")
        parts.append(f"Scene type: {self.scene_context.scene_activity}")
        parts.append(f"Current motion: {frame_context.motion_percent:.1f}%")
        parts.append("")
        
        # Focus on specific object or all
        objects_to_describe = frame_context.objects
        if focus_object_id is not None:
            objects_to_describe = [o for o in objects_to_describe if o.object_id == focus_object_id]
        
        if objects_to_describe:
            parts.append("=== DETECTED OBJECTS ===")
            
            for obj in objects_to_describe:
                parts.append(f"\nObject #{obj.object_id}:")
                parts.append(f"  - Tracked for {obj.total_frames} frames ({obj.last_seen_frame - obj.first_seen_frame + 1} frame span)")
                
                if obj.entry_direction:
                    parts.append(f"  - Entered from: {obj.entry_direction}")
                
                parts.append(f"  - Current position: ({obj.positions[-1][0]:.2f}, {obj.positions[-1][1]:.2f})")
                parts.append(f"  - Moving: {obj.direction} at speed {obj.avg_speed:.4f}")
                parts.append(f"  - Movement pattern: {obj.movement_pattern}")
                
                if obj.size_change_percent != 0:
                    direction = "approaching" if obj.size_change_percent > 0 else "moving away"
                    parts.append(f"  - Size change: {obj.size_change_percent:+.1f}% ({direction})")
                
                parts.append(f"  - Shape analysis: aspect_ratio={obj.avg_aspect_ratio:.2f}, complexity={obj.avg_complexity:.2f}")
                parts.append(f"  - Shape suggests: {obj.shape_suggests}")
        
        # Recent events
        if frame_context.recent_events:
            parts.append("\n=== RECENT EVENTS ===")
            for event in frame_context.recent_events[-3:]:
                parts.append(f"  - {event}")
        
        parts.append("")
        
        # Question based on type
        if question_type == "classify":
            if focus_object_id and objects_to_describe:
                obj = objects_to_describe[0]
                parts.append("=== QUESTION ===")
                parts.append(f"Based on the analysis above (shape suggests {obj.shape_suggests}),")
                parts.append("what type of object is this? Answer with ONE word:")
                parts.append("(person/bird/cat/dog/car/vehicle/animal/unknown)")
            else:
                parts.append("=== QUESTION ===")
                parts.append("What objects do you see? List each with one word classification.")
        
        elif question_type == "activity":
            parts.append("=== QUESTION ===")
            parts.append("Based on the movement patterns and positions described above,")
            parts.append("describe in ONE sentence what is happening in this scene.")
        
        else:  # describe
            parts.append("=== QUESTION ===")
            parts.append("Looking at this frame with the analysis context above,")
            parts.append("confirm what you see and describe any activity in 1-2 sentences.")
        
        return "\n".join(parts)
    
    def build_compact_context(self, frame_context: FrameContext) -> str:
        """
        Build compact context string for fast LLM queries.
        
        Returns single-line context summary.
        """
        parts = []
        
        # Scene
        parts.append(f"Scene:{self.scene_context.scene_activity}")
        parts.append(f"motion:{frame_context.motion_percent:.0f}%")
        
        # Objects
        for obj in frame_context.objects[:3]:  # Max 3 objects
            obj_desc = f"Obj{obj.object_id}:{obj.shape_suggests}"
            if obj.direction != "unknown":
                obj_desc += f",{obj.direction}"
            if obj.entry_direction:
                obj_desc += f",from_{obj.entry_direction}"
            parts.append(obj_desc)
        
        return " | ".join(parts)
    
    def get_summary(self) -> Dict:
        """Get analysis summary."""
        return {
            "frames_analyzed": self.scene_context.total_frames_analyzed,
            "duration_seconds": self.scene_context.duration_seconds,
            "objects_tracked": len(self.object_histories),
            "scene_activity": self.scene_context.scene_activity,
            "enter_events": self.scene_context.enter_events,
            "exit_events": self.scene_context.exit_events,
            "avg_motion": self.scene_context.avg_motion_percent,
        }
    
    def reset(self):
        """Reset context builder."""
        self.object_histories.clear()
        self.scene_context = SceneContext()
        self.recent_events.clear()
        self._start_time = time.time()
        self._frame_count = 0
        self._motion_sum = 0.0
        self._max_motion = 0.0


# ============================================================================
# Enhanced Pipeline with Context
# ============================================================================

class EnhancedAnalysisPipeline:
    """
    Complete pipeline with context-aware LLM queries.
    
    1. Preprocess frames (OpenCV) → metadata
    2. Build rich context from metadata
    3. Query LLM with context (much better results)
    """
    
    def __init__(
        self,
        classifier_model: str = "moondream",
        narrator_model: str = "llava:7b",
        ollama_url: str = "http://localhost:11434",
    ):
        from .frame_diff_dsl import FrameDiffPipeline
        
        self.diff_pipeline = FrameDiffPipeline(enable_classification=False)
        self.context_builder = ContextBuilder()
        
        self.classifier_model = classifier_model
        self.narrator_model = narrator_model
        self.ollama_url = ollama_url
        
        self._classified_objects: Dict[int, str] = {}
    
    def process_frame(
        self,
        frame_path: Path,
        classify_objects: bool = True,
        describe_scene: bool = False,
    ) -> Dict:
        """
        Process frame with full context.
        
        Args:
            frame_path: Path to frame image
            classify_objects: Whether to classify new objects
            describe_scene: Whether to get scene description
            
        Returns:
            Dict with analysis results
        """
        # 1. Preprocess (OpenCV only, ~10ms)
        delta, dsl_text = self.diff_pipeline.process_frame(frame_path, classify_new=False)
        
        # 2. Build context
        frame_ctx = self.context_builder.update(delta)
        
        result = {
            "frame_num": delta.frame_num,
            "motion_percent": delta.motion_percent,
            "objects_visible": len(delta.blobs),
            "dsl": dsl_text,
            "compact_context": self.context_builder.build_compact_context(frame_ctx),
            "classifications": {},
            "description": "",
        }
        
        # 3. Classify new objects (LLM, only when needed)
        if classify_objects:
            for obj in frame_ctx.objects:
                if obj.object_id not in self._classified_objects and obj.total_frames >= 3:
                    # Build context-aware prompt
                    prompt = self.context_builder.build_llm_prompt(
                        frame_ctx, 
                        focus_object_id=obj.object_id,
                        question_type="classify"
                    )
                    
                    classification = self._query_llm(
                        prompt, frame_path, 
                        model=self.classifier_model,
                        max_tokens=10
                    )
                    
                    # Parse classification
                    cls = self._parse_classification(classification)
                    self._classified_objects[obj.object_id] = cls
                    result["classifications"][obj.object_id] = cls
        
        # 4. Describe scene if requested (LLM)
        if describe_scene and frame_ctx.objects:
            prompt = self.context_builder.build_llm_prompt(
                frame_ctx,
                question_type="activity"
            )
            
            description = self._query_llm(
                prompt, frame_path,
                model=self.narrator_model,
                max_tokens=50
            )
            result["description"] = description
        
        return result
    
    def _query_llm(
        self,
        prompt: str,
        frame_path: Path,
        model: str,
        max_tokens: int = 50,
    ) -> str:
        """Query LLM with image and context."""
        try:
            import requests
            import base64
            import cv2
            
            # Load and encode image
            frame = cv2.imread(str(frame_path))
            if frame is None:
                return ""
            
            # Resize for speed
            frame = cv2.resize(frame, (384, 384))
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            img_b64 = base64.b64encode(buffer).decode()
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "images": [img_b64],
                    "stream": False,
                    "options": {"num_predict": max_tokens}
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            
        except Exception as e:
            logger.debug(f"LLM query failed: {e}")
        
        return ""
    
    def _parse_classification(self, response: str) -> str:
        """Parse classification response."""
        response = response.lower().strip()
        
        valid = ["person", "bird", "cat", "dog", "car", "vehicle", "animal"]
        for cls in valid:
            if cls in response:
                return cls.upper()
        
        return "UNKNOWN"
    
    def get_full_context(self) -> str:
        """Get full analysis context."""
        return self.diff_pipeline.get_full_dsl()
    
    def reset(self):
        """Reset pipeline."""
        self.diff_pipeline.reset()
        self.context_builder.reset()
        self._classified_objects.clear()


# ============================================================================
# Quick Integration Functions
# ============================================================================

def analyze_with_context(
    frame_path: Path,
    pipeline: EnhancedAnalysisPipeline = None,
) -> Dict:
    """
    Quick function to analyze frame with full context.
    """
    if pipeline is None:
        pipeline = EnhancedAnalysisPipeline()
    
    return pipeline.process_frame(frame_path, classify_objects=True, describe_scene=True)
