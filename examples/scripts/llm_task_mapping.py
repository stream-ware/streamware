#!/usr/bin/env python3
"""
LLM Task Mapping Demo

Shows how different LLMs are mapped to different tasks based on:
- Speed requirements
- Quality requirements
- Vision capability
- Cost constraints

Usage:
    python llm_task_mapping.py
    python llm_task_mapping.py --task detect --vision
    python llm_task_mapping.py --list-models
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from streamware.detection_pipeline import (
    LLM_REGISTRY,
    LLMCapability,
    get_best_llm_for_task,
)


# =============================================================================
# TASK DEFINITIONS
# =============================================================================

TASKS = {
    "detect": {
        "description": "Quick YES/NO detection",
        "example_prompt": "Is there a person in this image? Answer YES or NO.",
        "requires_vision": True,
        "prefer_speed": True,
        "prefer_quality": False,
    },
    "summarize": {
        "description": "Short summary (1 sentence)",
        "example_prompt": "Describe what you see in ONE short sentence.",
        "requires_vision": True,
        "prefer_speed": True,
        "prefer_quality": False,
    },
    "describe": {
        "description": "Full detailed description",
        "example_prompt": "Describe in detail what is happening in this image.",
        "requires_vision": True,
        "prefer_speed": False,
        "prefer_quality": True,
    },
    "compare": {
        "description": "Compare two states",
        "example_prompt": "Compare BEFORE and NOW. Is there a meaningful change?",
        "requires_vision": False,
        "prefer_speed": True,
        "prefer_quality": False,
    },
    "classify": {
        "description": "Classify scene or action",
        "example_prompt": "Classify this scene: indoor/outdoor, day/night, activity type.",
        "requires_vision": True,
        "prefer_speed": True,
        "prefer_quality": False,
    },
    "converse": {
        "description": "Conversational response",
        "example_prompt": "The user asks: 'What's happening?' Respond naturally.",
        "requires_vision": True,
        "prefer_speed": False,
        "prefer_quality": True,
    },
}


def show_model_capabilities():
    """Display all models and their capabilities."""
    print("\n" + "="*80)
    print("LLM REGISTRY - Available Models")
    print("="*80)
    
    print(f"\n{'Model':<20} {'Provider':<10} {'Size':<8} {'Vision':<8} {'Speed':<8} {'Quality':<8} {'Cost':<8}")
    print("-"*80)
    
    for name, cap in LLM_REGISTRY.items():
        vision = "✅" if cap.vision else "❌"
        print(f"{name:<20} {cap.provider:<10} {cap.size:<8} {vision:<8} {cap.speed:<8} {cap.quality:<8} {cap.cost:<8}")
    
    print("\n📊 Capability Matrix:")
    print(f"\n{'Model':<20} {'Detect':<8} {'Summary':<8} {'Describe':<8} {'Compare':<8} {'Classify':<8} {'Converse':<8}")
    print("-"*80)
    
    for name, cap in LLM_REGISTRY.items():
        detect = "✅" if cap.can_detect else "❌"
        summary = "✅" if cap.can_summarize else "❌"
        describe = "✅" if cap.can_describe else "❌"
        compare = "✅" if cap.can_compare else "❌"
        classify = "✅" if cap.can_classify else "❌"
        converse = "✅" if cap.can_converse else "❌"
        print(f"{name:<20} {detect:<8} {summary:<8} {describe:<8} {compare:<8} {classify:<8} {converse:<8}")


def show_task_mapping():
    """Show which LLM is best for each task."""
    print("\n" + "="*80)
    print("TASK → LLM MAPPING")
    print("="*80)
    
    for task_name, task_info in TASKS.items():
        print(f"\n📋 Task: {task_name.upper()}")
        print(f"   Description: {task_info['description']}")
        print(f"   Example: {task_info['example_prompt'][:60]}...")
        
        # Find best model
        best = get_best_llm_for_task(
            task_name,
            require_vision=task_info['requires_vision'],
            prefer_speed=task_info['prefer_speed'],
            prefer_quality=task_info['prefer_quality'],
        )
        
        if best:
            cap = LLM_REGISTRY[best]
            print(f"   → Best LLM: {best}")
            print(f"     Speed: {cap.speed}, Quality: {cap.quality}, Cost: {cap.cost}")
        else:
            print(f"   → No suitable LLM found")


def show_pipeline_example():
    """Show how tasks are chained in a pipeline."""
    print("\n" + "="*80)
    print("PIPELINE EXAMPLE - Person Tracking")
    print("="*80)
    
    print("""
    ┌─────────────────────────────────────────────────────────────┐
    │                    TASK PIPELINE                             │
    ├─────────────────────────────────────────────────────────────┤
    │                                                              │
    │  1. DETECT (fast)                                           │
    │     └─ Model: gemma2:2b                                     │
    │     └─ Prompt: "Is there a person? YES/NO"                  │
    │     └─ Time: ~1s                                            │
    │     └─ If NO → STOP                                         │
    │                                                              │
    │  2. SUMMARIZE (fast)                                        │
    │     └─ Model: gemma2:2b                                     │
    │     └─ Prompt: "Describe in ONE sentence"                   │
    │     └─ Time: ~2s                                            │
    │     └─ Output: "Person: at desk, using computer"            │
    │                                                              │
    │  3. COMPARE (fast)                                          │
    │     └─ Model: gemma2:2b                                     │
    │     └─ Prompt: "Is this different from before?"             │
    │     └─ Time: ~1s                                            │
    │     └─ If NO → STOP (no change)                             │
    │                                                              │
    │  4. DESCRIBE (slow, optional)                               │
    │     └─ Model: llava:13b                                     │
    │     └─ Prompt: "Describe in detail"                         │
    │     └─ Time: ~5s                                            │
    │     └─ Only for security/behavior modes                     │
    │                                                              │
    └─────────────────────────────────────────────────────────────┘
    
    Total time (best case): ~1s (no person detected)
    Total time (typical): ~4s (person detected, no change)
    Total time (worst case): ~9s (full description needed)
    """)


def find_best_for_task(task: str, vision: bool = False, speed: bool = True, quality: bool = False):
    """Find best LLM for a specific task."""
    print(f"\n🔍 Finding best LLM for: {task}")
    print(f"   Vision required: {vision}")
    print(f"   Prefer speed: {speed}")
    print(f"   Prefer quality: {quality}")
    
    best = get_best_llm_for_task(
        task,
        require_vision=vision,
        prefer_speed=speed,
        prefer_quality=quality,
    )
    
    if best:
        cap = LLM_REGISTRY[best]
        print(f"\n   ✅ Best match: {best}")
        print(f"      Provider: {cap.provider}")
        print(f"      Size: {cap.size}")
        print(f"      Speed: {cap.speed}")
        print(f"      Quality: {cap.quality}")
        print(f"      Cost: {cap.cost}")
    else:
        print(f"\n   ❌ No suitable LLM found")


def main():
    parser = argparse.ArgumentParser(description="LLM Task Mapping Demo")
    parser.add_argument("--list-models", action="store_true", help="List all models")
    parser.add_argument("--task", help="Find best LLM for task (detect, summarize, describe, compare, classify, converse)")
    parser.add_argument("--vision", action="store_true", help="Require vision capability")
    parser.add_argument("--speed", action="store_true", default=True, help="Prefer speed")
    parser.add_argument("--quality", action="store_true", help="Prefer quality")
    args = parser.parse_args()
    
    if args.list_models:
        show_model_capabilities()
    elif args.task:
        find_best_for_task(args.task, args.vision, args.speed, args.quality)
    else:
        show_model_capabilities()
        show_task_mapping()
        show_pipeline_example()
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    main()
