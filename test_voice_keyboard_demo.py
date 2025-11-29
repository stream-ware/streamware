#!/usr/bin/env python3
"""
Demo Voice Keyboard Component
Uses TTS to explain what to say, then STT to test it
"""

import time
import subprocess
from streamware import flow

def speak(text):
    """Speak using espeak (fast and reliable)"""
    try:
        subprocess.run(['espeak', '-v', 'pl', '-s', '150', text], timeout=10)
    except:
        print(f"[TTS] {text}")

def demo_typing():
    """Demo voice typing"""
    print("\n" + "="*60)
    print("🎤 DEMO 1: Voice Typing (Wpisywanie głosem)")
    print("="*60)
    
    speak("Demo pierwszy. Wpisywanie głosem.")
    time.sleep(1)
    
    # Example 1: Direct text
    print("\n📝 Test 1: Wpisz 'hello world'")
    speak("Przykład pierwszy. Powiedz: wpisz hello world")
    time.sleep(2)
    
    result = flow("voice_keyboard://type?command=wpisz hello world").run()
    print(f"✓ Result: {result}")
    time.sleep(2)
    
    # Example 2: Polish text
    print("\n📝 Test 2: Wpisz polski tekst")
    speak("Przykład drugi. Powiedz: wpisz witaj świecie")
    time.sleep(2)
    
    result = flow("voice_keyboard://type?command=wpisz witaj świecie").run()
    print(f"✓ Result: {result}")
    time.sleep(2)

def demo_keys():
    """Demo key presses"""
    print("\n" + "="*60)
    print("⌨️  DEMO 2: Key Presses (Naciskanie klawiszy)")
    print("="*60)
    
    speak("Demo drugi. Naciskanie klawiszy.")
    time.sleep(1)
    
    # Example 1: Enter
    print("\n⌨️  Test 1: Naciśnij enter")
    speak("Przykład pierwszy. Powiedz: naciśnij enter")
    time.sleep(2)
    
    result = flow("voice_keyboard://press?command=naciśnij enter").run()
    print(f"✓ Result: {result}")
    time.sleep(2)
    
    # Example 2: Tab
    print("\n⌨️  Test 2: Naciśnij tab")
    speak("Przykład drugi. Powiedz: naciśnij tab")
    time.sleep(2)
    
    result = flow("voice_keyboard://press?command=naciśnij tab").run()
    print(f"✓ Result: {result}")
    time.sleep(2)

def demo_interactive():
    """Demo interactive mode"""
    print("\n" + "="*60)
    print("🎙️  DEMO 3: Interactive Mode (Tryb interaktywny)")
    print("="*60)
    
    speak("Demo trzeci. Tryb interaktywny.")
    time.sleep(1)
    
    speak("Otwieram notatnik. Możesz dyktować.")
    time.sleep(1)
    
    # Open text editor
    try:
        subprocess.Popen(['gedit'])
        time.sleep(3)
    except:
        print("⚠️  Could not open gedit. Open any text editor manually.")
        speak("Otwórz edytor tekstu ręcznie")
        time.sleep(5)
    
    print("\n🎙️  Now you can dictate!")
    print("Say things like:")
    print("  - 'wpisz hello' (types 'hello')")
    print("  - 'naciśnij enter' (presses enter)")
    print("  - 'stop' (exits)")
    print()
    
    speak("Teraz możesz dyktować. Powiedz stop aby zakończyć.")
    
    # Run interactive mode
    result = flow("voice_keyboard://listen_and_type?iterations=5&confirm=true").run()
    print(f"\n✓ Completed {result.get('iterations_completed')} iterations")

def demo_commands():
    """Show example commands"""
    print("\n" + "="*60)
    print("📚 Example Voice Commands")
    print("="*60)
    
    examples = {
        "Typing": [
            "wpisz hello world",
            "wpisz test 123",
            "napisz moje imię",
            "wprowadź tekst",
        ],
        "Keys": [
            "naciśnij enter",
            "naciśnij tab",
            "naciśnij spacja",
            "naciśnij escape",
            "naciśnij backspace",
        ],
        "English": [
            "type hello",
            "press enter",
            "write test",
        ]
    }
    
    for category, commands in examples.items():
        print(f"\n{category}:")
        for cmd in commands:
            print(f"  • {cmd}")
            speak(cmd)
            time.sleep(0.5)

def main():
    """Run all demos"""
    print("\n" + "="*60)
    print("🎤 VOICE KEYBOARD DEMO")
    print("="*60)
    
    speak("Witaj w demo voice keyboard")
    time.sleep(1)
    
    # Check dependencies
    print("\n✓ Checking dependencies...")
    
    # Check xdotool
    try:
        subprocess.run(['which', 'xdotool'], capture_output=True, check=True)
        print("✓ xdotool available")
    except:
        print("⚠️  xdotool not found (install: sudo apt-get install xdotool)")
    
    # Check espeak
    try:
        subprocess.run(['which', 'espeak'], capture_output=True, check=True)
        print("✓ espeak available")
    except:
        print("⚠️  espeak not found (install: sudo apt-get install espeak)")
    
    print("\n" + "="*60)
    print("Choose demo:")
    print("1. Voice Typing Demo")
    print("2. Key Presses Demo")
    print("3. Interactive Mode (with text editor)")
    print("4. Show Example Commands")
    print("5. All Demos")
    print("="*60)
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == '1':
        demo_typing()
    elif choice == '2':
        demo_keys()
    elif choice == '3':
        demo_interactive()
    elif choice == '4':
        demo_commands()
    elif choice == '5':
        demo_commands()
        time.sleep(2)
        demo_typing()
        time.sleep(2)
        demo_keys()
        time.sleep(2)
        print("\n💡 Ready for interactive mode?")
        if input("Open text editor? (y/n): ").lower() == 'y':
            demo_interactive()
    else:
        print("Invalid choice")
        return
    
    print("\n" + "="*60)
    print("✅ Demo Complete!")
    print("="*60)
    
    speak("Demo zakończone")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
