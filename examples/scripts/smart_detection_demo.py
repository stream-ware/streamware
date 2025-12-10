#!/usr/bin/env python3
"""
Smart Detection Pipeline Demo

Demonstrates the prioritized detection system that uses:
1. OpenCV (fast) - motion detection, HOG person detection
2. Small LLM (medium) - quick checks, summaries
3. Large LLM (slow) - full descriptions when needed

Usage:
    python smart_detection_demo.py --intent "track person"
    python smart_detection_demo.py --intent "notify when someone enters"
    python smart_detection_demo.py --intent "security monitoring"
"""

import argparse
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from streamware.detection_pipeline import (
    DetectionPipeline, 
    UserIntent, 
    parse_user_intent,
    LLM_REGISTRY,
    get_best_llm_for_task,
)


def demo_intent_parsing():
    """Demonstrate intent parsing from natural language."""
    print("\n" + "="*60)
    print("INTENT PARSING DEMO")
    print("="*60)
    
    examples = [
        "track person in the room",
        "notify me when someone enters",
        "alert when person leaves",
        "security monitoring",
        "log all activity",
        "watch what they're doing",
        "śledź osobę",  # Polish
        "powiadom gdy ktoś wejdzie",  # Polish
    ]
    
    for text in examples:
        intent, params = parse_user_intent(text)
        print(f"\n📝 '{text}'")
        print(f"   → Intent: {intent.name}")
        print(f"   → Focus: {params.get('focus', 'person')}")
        print(f"   → Sensitivity: {params.get('sensitivity', 'medium')}")


def demo_llm_selection():
    """Demonstrate LLM selection for different tasks."""
    print("\n" + "="*60)
    print("LLM SELECTION DEMO")
    print("="*60)
    
    tasks = [
        ("detect", False, True, False),   # Quick detection, no vision, prefer speed
        ("summarize", True, True, False), # Summary with vision, prefer speed
        ("describe", True, False, True),  # Full description, prefer quality
        ("compare", False, True, False),  # Compare states, no vision
        ("converse", True, False, True),  # Conversation, prefer quality
    ]
    
    print("\nAvailable LLMs:")
    for name, cap in LLM_REGISTRY.items():
        vision = "👁️" if cap.vision else "  "
        print(f"  {vision} {name:20} | {cap.size:6} | {cap.speed:6} | {cap.quality:6} | {cap.cost}")
    
    print("\nBest LLM for each task:")
    for task, vision, speed, quality in tasks:
        best = get_best_llm_for_task(task, require_vision=vision, prefer_speed=speed, prefer_quality=quality)
        print(f"  {task:12} (vision={vision}, speed={speed}, quality={quality}) → {best}")


def demo_pipeline_config():
    """Demonstrate pipeline configuration for different intents."""
    print("\n" + "="*60)
    print("PIPELINE CONFIGURATION DEMO")
    print("="*60)
    
    intents = [
        UserIntent.TRACK_PERSON,
        UserIntent.ALERT_ON_ENTRY,
        UserIntent.SECURITY_WATCH,
        UserIntent.ACTIVITY_LOG,
    ]
    
    for intent in intents:
        pipeline = DetectionPipeline(intent=intent)
        print(f"\n🎯 {intent.name}")
        print(f"   Stages ({len(pipeline._stages)}):")
        for stage in pipeline._stages:
            print(f"     {stage.priority:2}. {stage.method.name:20} | model={stage.model or 'opencv'}")


def demo_from_natural_language():
    """Demonstrate creating pipeline from natural language."""
    print("\n" + "="*60)
    print("NATURAL LANGUAGE PIPELINE DEMO")
    print("="*60)
    
    queries = [
        "notify me when someone enters the room",
        "track the person and tell me what they're doing",
        "security watch with high sensitivity",
        "log all activity in the area",
    ]
    
    for query in queries:
        print(f"\n📝 '{query}'")
        pipeline = DetectionPipeline.from_intent(query)
        print(f"   → Intent: {pipeline.intent.name}")
        print(f"   → Focus: {pipeline.focus}")
        print(f"   → Sensitivity: {pipeline.sensitivity}")
        print(f"   → Stages: {[s.method.name for s in pipeline._stages]}")


def demo_processing_flow():
    """Demonstrate the processing flow (without actual images)."""
    print("\n" + "="*60)
    print("PROCESSING FLOW DEMO")
    print("="*60)
    
    print("""
    ┌─────────────────────────────────────────────────────────────┐
    │                    DETECTION PIPELINE                        │
    ├─────────────────────────────────────────────────────────────┤
    │                                                              │
    │  Frame Input                                                 │
    │       │                                                      │
    │       ▼                                                      │
    │  ┌─────────────────────────────────────────────────────┐    │
    │  │ Stage 1: MOTION_OPENCV (~50ms)                      │    │
    │  │   • Compare with previous frame                     │    │
    │  │   • motion < 0.5% → SKIP                           │    │
    │  └─────────────────────────────────────────────────────┘    │
    │       │                                                      │
    │       ▼                                                      │
    │  ┌─────────────────────────────────────────────────────┐    │
    │  │ Stage 2: HOG_PERSON (~100ms)                        │    │
    │  │   • OpenCV HOG descriptor                           │    │
    │  │   • No person shape → SKIP (verify every 5th)      │    │
    │  └─────────────────────────────────────────────────────┘    │
    │       │                                                      │
    │       ▼                                                      │
    │  ┌─────────────────────────────────────────────────────┐    │
    │  │ Stage 3: LLM_QUICK_CHECK (~1-2s) - gemma2:2b       │    │
    │  │   • "Is there a person?" → YES/NO                  │    │
    │  │   • NO → SKIP                                       │    │
    │  └─────────────────────────────────────────────────────┘    │
    │       │                                                      │
    │       ▼                                                      │
    │  ┌─────────────────────────────────────────────────────┐    │
    │  │ Stage 4: LLM_QUICK_SUMMARY (~2s) - gemma2:2b       │    │
    │  │   • "Person: at desk, using computer"              │    │
    │  │   • Short-circuit if tracking mode                 │    │
    │  └─────────────────────────────────────────────────────┘    │
    │       │                                                      │
    │       ▼                                                      │
    │  ┌─────────────────────────────────────────────────────┐    │
    │  │ Stage 5: LLM_CHANGE_CHECK (~1s) - gemma2:2b        │    │
    │  │   • Compare with previous summary                  │    │
    │  │   • No change → SKIP                               │    │
    │  └─────────────────────────────────────────────────────┘    │
    │       │                                                      │
    │       ▼                                                      │
    │  ┌─────────────────────────────────────────────────────┐    │
    │  │ Stage 6: LLM_FULL_DESCRIBE (~5s) - llava:13b       │    │
    │  │   • Full description (only for security/behavior)  │    │
    │  └─────────────────────────────────────────────────────┘    │
    │       │                                                      │
    │       ▼                                                      │
    │  Result: should_notify, should_speak, should_log            │
    │                                                              │
    └─────────────────────────────────────────────────────────────┘
    """)


def main():
    parser = argparse.ArgumentParser(description="Smart Detection Pipeline Demo")
    parser.add_argument("--intent", help="Natural language intent to parse")
    parser.add_argument("--all", action="store_true", help="Run all demos")
    args = parser.parse_args()
    
    if args.intent:
        print(f"\n🎯 Parsing intent: '{args.intent}'")
        pipeline = DetectionPipeline.from_intent(args.intent)
        print(f"   Intent: {pipeline.intent.name}")
        print(f"   Focus: {pipeline.focus}")
        print(f"   Sensitivity: {pipeline.sensitivity}")
        print(f"   Stages:")
        for stage in pipeline._stages:
            print(f"     {stage.priority:2}. {stage.method.name}")
    else:
        demo_intent_parsing()
        demo_llm_selection()
        demo_pipeline_config()
        demo_from_natural_language()
        demo_processing_flow()
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    main()
