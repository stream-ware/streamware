#!/usr/bin/env python3
"""Test different screenshot methods"""

import os
import subprocess
import sys

print("Testing screenshot methods...\n")

# Method 1: scrot
print("1. Testing scrot...")
try:
    result = subprocess.run(['scrot', '/tmp/test_scrot.png'], 
                          capture_output=True, timeout=5)
    if result.returncode == 0 and os.path.exists('/tmp/test_scrot.png'):
        print("   ✓ scrot works!")
        os.remove('/tmp/test_scrot.png')
    else:
        print(f"   ✗ scrot failed: {result.stderr.decode()}")
except Exception as e:
    print(f"   ✗ scrot error: {e}")

# Method 2: ImageMagick import
print("\n2. Testing ImageMagick import...")
try:
    result = subprocess.run(['import', '-window', 'root', '/tmp/test_import.png'],
                          capture_output=True, timeout=5)
    if result.returncode == 0 and os.path.exists('/tmp/test_import.png'):
        print("   ✓ ImageMagick import works!")
        os.remove('/tmp/test_import.png')
    else:
        print(f"   ✗ import failed: {result.stderr.decode()}")
except Exception as e:
    print(f"   ✗ import error: {e}")

# Method 3: pyscreeze directly
print("\n3. Testing pyscreeze...")
try:
    import pyscreeze
    # Configure pyscreeze to use scrot
    pyscreeze.screenshot('/tmp/test_pyscreeze.png')
    if os.path.exists('/tmp/test_pyscreeze.png'):
        print("   ✓ pyscreeze works!")
        os.remove('/tmp/test_pyscreeze.png')
    else:
        print("   ✗ pyscreeze failed")
except Exception as e:
    print(f"   ✗ pyscreeze error: {e}")

# Method 4: pyautogui
print("\n4. Testing pyautogui...")
try:
    import pyautogui
    pyautogui.screenshot('/tmp/test_pyautogui.png')
    if os.path.exists('/tmp/test_pyautogui.png'):
        print("   ✓ pyautogui works!")
        os.remove('/tmp/test_pyautogui.png')
    else:
        print("   ✗ pyautogui failed")
except Exception as e:
    print(f"   ✗ pyautogui error: {e}")

print("\n" + "="*50)
print("Recommended: Use scrot or ImageMagick import")
print("="*50)
