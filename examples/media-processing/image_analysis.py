#!/usr/bin/env python3
"""
Image Analysis - Describe images with AI (LLaVA)

Requirements:
    ollama pull llava

Related:
    - docs/v2/guides/MEDIA_GUIDE.md
    - streamware/components/media.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow


def describe_image(image_path: str, model: str = "llava"):
    """Describe image using AI vision"""
    result = flow(f"media://describe_image?file={image_path}&model={model}").run()
    return result


def demo():
    print("=" * 60)
    print("IMAGE ANALYSIS WITH AI")
    print("=" * 60)
    
    print("\n📋 Usage:")
    print("   python image_analysis.py photo.jpg")
    print("   sq media describe_image --file photo.jpg --model llava")
    
    print("\n🔧 Setup:")
    print("   ollama pull llava")
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        print(f"\n🖼️ Analyzing: {image_path}")
        
        try:
            result = describe_image(image_path)
            print(f"\n📝 Description:")
            print(result.get("description", result))
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("\n💡 Provide an image path to analyze")


if __name__ == "__main__":
    demo()
