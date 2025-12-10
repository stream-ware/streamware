#!/usr/bin/env python3
"""
Intent-Based Monitoring Examples

Shows how to create monitoring pipelines from natural language intents.

Examples:
    # Track person
    python intent_based_monitoring.py "track person in the room"
    
    # Security alert
    python intent_based_monitoring.py "notify when someone enters"
    
    # Activity logging
    python intent_based_monitoring.py "log all activity"
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from streamware.detection_pipeline import DetectionPipeline, UserIntent


# =============================================================================
# EXAMPLE CONFIGURATIONS
# =============================================================================

EXAMPLE_CONFIGS = {
    "home_security": {
        "intent": "notify when someone enters or leaves",
        "description": "Home security - alerts on entry/exit",
        "expected_behavior": [
            "Motion detection triggers first",
            "HOG person detection validates",
            "Small LLM confirms person",
            "Alert sent on entry/exit",
            "TTS announces: 'Person detected at door'",
        ]
    },
    
    "office_tracking": {
        "intent": "track people in the office and log activity",
        "description": "Office monitoring - tracks and logs",
        "expected_behavior": [
            "Continuous person tracking",
            "Quick summaries: 'Person: at desk, working'",
            "Logs all significant movements",
            "No TTS (silent logging)",
        ]
    },
    
    "pet_monitoring": {
        "intent": "watch for my dog and notify if it leaves the room",
        "description": "Pet monitoring - tracks specific animal",
        "expected_behavior": [
            "Focus: dog (not person)",
            "Motion triggers detection",
            "LLM checks for dog presence",
            "Alert when dog leaves",
        ]
    },
    
    "package_detection": {
        "intent": "alert when a package is delivered",
        "description": "Delivery monitoring",
        "expected_behavior": [
            "Focus: package",
            "Motion at door triggers",
            "LLM identifies package",
            "Notification sent",
        ]
    },
    
    "behavior_analysis": {
        "intent": "watch what the person is doing and describe their actions",
        "description": "Detailed behavior analysis",
        "expected_behavior": [
            "Full LLM descriptions enabled",
            "Detailed action analysis",
            "TTS describes actions",
            "Higher resource usage",
        ]
    },
}


def show_example(name: str, config: dict):
    """Show example configuration."""
    print(f"\n{'='*60}")
    print(f"📋 {name.upper()}")
    print(f"{'='*60}")
    print(f"\n📝 Intent: \"{config['intent']}\"")
    print(f"📖 Description: {config['description']}")
    
    # Create pipeline
    pipeline = DetectionPipeline.from_intent(config['intent'])
    
    print(f"\n🎯 Parsed Configuration:")
    print(f"   Intent: {pipeline.intent.name}")
    print(f"   Focus: {pipeline.focus}")
    print(f"   Sensitivity: {pipeline.sensitivity}")
    
    print(f"\n⚙️ Detection Stages:")
    for stage in pipeline._stages:
        model_info = f" ({stage.model})" if stage.model else ""
        print(f"   {stage.priority:2}. {stage.method.name}{model_info}")
    
    print(f"\n📌 Expected Behavior:")
    for behavior in config['expected_behavior']:
        print(f"   • {behavior}")


def interactive_mode():
    """Interactive intent parsing."""
    print("\n" + "="*60)
    print("INTERACTIVE INTENT PARSER")
    print("="*60)
    print("\nEnter natural language intents to see how they're parsed.")
    print("Type 'quit' to exit.\n")
    
    while True:
        try:
            intent = input("🎤 Your intent: ").strip()
            if intent.lower() in ['quit', 'exit', 'q']:
                break
            
            if not intent:
                continue
            
            pipeline = DetectionPipeline.from_intent(intent)
            
            print(f"\n   🎯 Intent: {pipeline.intent.name}")
            print(f"   👁️ Focus: {pipeline.focus}")
            print(f"   📊 Sensitivity: {pipeline.sensitivity}")
            print(f"   ⚙️ Stages: {len(pipeline._stages)}")
            
            for stage in pipeline._stages:
                model = f" → {stage.model}" if stage.model else ""
                print(f"      {stage.priority:2}. {stage.method.name}{model}")
            
            print()
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
    
    print("\n👋 Goodbye!")


def main():
    parser = argparse.ArgumentParser(description="Intent-Based Monitoring Examples")
    parser.add_argument("intent", nargs="?", help="Natural language intent")
    parser.add_argument("--examples", action="store_true", help="Show all examples")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    elif args.examples:
        for name, config in EXAMPLE_CONFIGS.items():
            show_example(name, config)
    elif args.intent:
        pipeline = DetectionPipeline.from_intent(args.intent)
        print(f"\n🎯 Intent: {pipeline.intent.name}")
        print(f"👁️ Focus: {pipeline.focus}")
        print(f"📊 Sensitivity: {pipeline.sensitivity}")
        print(f"\n⚙️ Stages:")
        for stage in pipeline._stages:
            model = f" → {stage.model}" if stage.model else ""
            print(f"   {stage.priority:2}. {stage.method.name}{model}")
    else:
        print("Usage:")
        print("  python intent_based_monitoring.py 'track person'")
        print("  python intent_based_monitoring.py --examples")
        print("  python intent_based_monitoring.py --interactive")


if __name__ == "__main__":
    main()
