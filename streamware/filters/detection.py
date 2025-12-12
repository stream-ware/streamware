"""
Detection Helpers

Quick detection checks and summarization.
Extracted from response_filter.py.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def quick_person_check(
    yolo_detections: List[Dict],
    motion_percent: float = 0.0,
    confidence_threshold: float = 0.5,
) -> Tuple[bool, str]:
    """
    Quick check if person is detected by YOLO.
    
    Args:
        yolo_detections: List of YOLO detection dicts
        motion_percent: Motion percentage from frame diff
        confidence_threshold: Minimum confidence for detection
    
    Returns:
        Tuple of (person_detected, summary)
    """
    if not yolo_detections:
        return False, "No detections"
    
    # Filter for person class
    persons = [
        d for d in yolo_detections
        if d.get("class", "").lower() == "person"
        and d.get("confidence", 0) >= confidence_threshold
    ]
    
    if not persons:
        return False, "No person detected"
    
    # Build summary
    count = len(persons)
    avg_conf = sum(p.get("confidence", 0) for p in persons) / count
    
    # Get positions
    positions = []
    for p in persons:
        box = p.get("box", {})
        x_center = (box.get("x1", 0) + box.get("x2", 0)) / 2
        if x_center < 0.33:
            positions.append("left")
        elif x_center > 0.66:
            positions.append("right")
        else:
            positions.append("center")
    
    pos_text = ", ".join(set(positions)) if positions else ""
    
    if count == 1:
        summary = f"Person detected on {pos_text}" if pos_text else "Person detected"
    else:
        summary = f"{count} people detected"
        if pos_text:
            summary += f" ({pos_text})"
    
    return True, summary


def quick_change_check(
    current_detections: List[Dict],
    previous_detections: List[Dict],
    focus: str = "person",
) -> Tuple[bool, str]:
    """
    Quick check if scene changed significantly.
    
    Args:
        current_detections: Current frame detections
        previous_detections: Previous frame detections
        focus: Object class to focus on
    
    Returns:
        Tuple of (changed, summary)
    """
    def count_class(detections, cls):
        return sum(1 for d in detections if d.get("class", "").lower() == cls.lower())
    
    current_count = count_class(current_detections, focus)
    previous_count = count_class(previous_detections, focus)
    
    if current_count == previous_count:
        return False, f"No change ({current_count} {focus})"
    
    diff = current_count - previous_count
    if diff > 0:
        return True, f"{focus.title()} entered (+{diff})"
    else:
        return True, f"{focus.title()} left ({diff})"


def summarize_detection(
    yolo_detections: List[Dict],
    motion_data: Optional[Dict] = None,
    focus: str = "person",
    include_counts: bool = True,
) -> str:
    """
    Create human-readable summary of detections.
    
    Args:
        yolo_detections: List of YOLO detections
        motion_data: Optional motion analysis data
        focus: Primary focus class
        include_counts: Include object counts
    
    Returns:
        Summary string
    """
    if not yolo_detections:
        if motion_data and motion_data.get("has_motion"):
            return f"Motion detected ({motion_data.get('motion_percent', 0):.1f}%)"
        return "No objects detected"
    
    # Group by class
    class_counts: Dict[str, int] = {}
    for d in yolo_detections:
        cls = d.get("class", "unknown")
        class_counts[cls] = class_counts.get(cls, 0) + 1
    
    # Build summary
    parts = []
    
    # Focus class first
    if focus in class_counts:
        count = class_counts.pop(focus)
        if count == 1:
            parts.append(f"{focus.title()} detected")
        else:
            parts.append(f"{count} {focus}s detected")
    
    # Other classes
    if include_counts and class_counts:
        for cls, count in sorted(class_counts.items(), key=lambda x: -x[1]):
            if count == 1:
                parts.append(f"1 {cls}")
            else:
                parts.append(f"{count} {cls}s")
    
    # Add motion info
    if motion_data and motion_data.get("has_motion"):
        parts.append(f"motion {motion_data.get('motion_percent', 0):.0f}%")
    
    return ", ".join(parts) if parts else "Scene analyzed"


def extract_alert_info(response: str) -> Tuple[bool, str]:
    """
    Extract alert information from structured response.
    
    Args:
        response: LLM response text
    
    Returns:
        Tuple of (is_alert, alert_message)
    """
    # Check for ALERT: YES pattern
    match = re.search(r"ALERT:\s*(YES|NO)", response, re.IGNORECASE)
    if match:
        is_alert = match.group(1).upper() == "YES"
        
        # Extract alert message
        msg_match = re.search(r"MESSAGE:\s*(.+?)(?:\n|$)", response, re.IGNORECASE)
        if msg_match:
            return is_alert, msg_match.group(1).strip()
        
        return is_alert, "Alert triggered" if is_alert else ""
    
    # Check for keywords
    alert_keywords = ["alert", "warning", "danger", "intruder", "unauthorized"]
    text_lower = response.lower()
    
    for kw in alert_keywords:
        if kw in text_lower:
            return True, f"{kw.title()} detected"
    
    return False, ""


def extract_structured_fields(response: str) -> Dict:
    """
    Extract structured fields from LLM response.
    
    Looks for patterns like:
    - VISIBLE: YES/NO
    - COUNT: N
    - SUMMARY: text
    
    Returns:
        Dict of extracted fields
    """
    fields = {}
    
    patterns = {
        "visible": r"VISIBLE:\s*(YES|NO)",
        "present": r"PRESENT:\s*(YES|NO)",
        "changed": r"CHANGED:\s*(YES|NO)",
        "alert": r"ALERT:\s*(YES|NO)",
        "count": r"COUNT:\s*(\d+)",
        "confidence": r"CONFIDENCE:\s*([\d.]+)",
        "summary": r"SUMMARY:\s*(.+?)(?:\n|$)",
        "description": r"DESCRIPTION:\s*(.+?)(?:\n|$)",
        "object": r"OBJECT:\s*(.+?)(?:\n|$)",
        "position": r"POSITION:\s*(.+?)(?:\n|$)",
    }
    
    for field, pattern in patterns.items():
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Convert boolean strings
            if value.upper() in ("YES", "NO"):
                value = value.upper() == "YES"
            # Convert numbers
            elif field in ("count",):
                value = int(value)
            elif field in ("confidence",):
                value = float(value)
            fields[field] = value
    
    return fields
