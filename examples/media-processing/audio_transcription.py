#!/usr/bin/env python3
"""
Audio Transcription - Convert speech to text

Usage:
    python audio_transcription.py audio.mp3
    python audio_transcription.py meeting.wav --output transcript.txt

CLI equivalent:
    sq media transcribe --file audio.mp3
    sq media transcribe --file audio.mp3 --output transcript.txt

Related:
    - docs/v2/guides/MEDIA_GUIDE.md - Media processing guide
    - examples/voice-control/ - Voice input/output examples
    - streamware/components/media.py - Source code
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware import flow


def transcribe(file: str, output: str = None):
    """
    Transcribe audio file to text.
    
    Args:
        file: Path to audio file (mp3, wav, etc.)
        output: Optional output file for transcript
    
    Returns:
        dict: Transcription result
    """
    uri = f"media://transcribe?file={file}"
    if output:
        uri += f"&output={output}"
    
    result = flow(uri).run()
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio to text",
        epilog="""
Examples:
  python audio_transcription.py recording.mp3
  python audio_transcription.py meeting.wav --output notes.txt

CLI equivalent:
  sq media transcribe --file audio.mp3

Documentation:
  - examples/media-processing/README.md
  - docs/v2/guides/MEDIA_GUIDE.md
        """
    )
    parser.add_argument("file", nargs="?", help="Audio file to transcribe")
    parser.add_argument("--output", "-o", help="Save transcript to file")
    
    args = parser.parse_args()
    
    if not args.file:
        print("=" * 60)
        print("AUDIO TRANSCRIPTION")
        print("=" * 60)
        print("\nUsage: python audio_transcription.py <audio_file>")
        print("\nSupported formats: mp3, wav, m4a, flac, ogg")
        print("\nExamples:")
        print("  python audio_transcription.py recording.mp3")
        print("  python audio_transcription.py meeting.wav --output transcript.txt")
        print("\nCLI equivalent:")
        print("  sq media transcribe --file audio.mp3")
        return 1
    
    try:
        print(f"🎤 Transcribing: {args.file}")
        result = transcribe(args.file, args.output)
        
        print(f"\n📝 Transcript:\n{result.get('text', 'No transcript generated')}")
        
        if args.output:
            print(f"\n💾 Saved to: {args.output}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
