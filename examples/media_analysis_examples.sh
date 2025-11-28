#!/bin/bash
# Media Analysis Examples with LLM
# Video, Audio, Image analysis with AI models

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "======================================================================"
echo "MEDIA ANALYSIS WITH AI - Streamware Examples"
echo "======================================================================"
echo ""

# Example 1: Video Description
echo -e "${BLUE}=== Example 1: Video Description with LLaVA ===${NC}"
echo ""
echo "# Install LLaVA model"
echo "ollama pull llava"
echo ""
echo "# Describe video content"
echo 'sq media describe_video --file video.mp4 --model llava'
echo ""
echo "# Output: AI-generated description of video content"
echo '{
  "success": true,
  "file": "video.mp4",
  "model": "llava",
  "description": "The video shows a person walking through a park...",
  "num_frames": 5
}'
echo ""

# Example 2: Image Description
echo -e "${BLUE}=== Example 2: Image Description ===${NC}"
echo ""
echo 'sq media describe_image --file photo.jpg --model llava'
echo ""
echo "# Output:"
echo '{
  "success": true,
  "file": "photo.jpg",
  "description": "A sunset over the ocean with orange and pink colors..."
}'
echo ""

# Example 3: Audio Transcription (STT)
echo -e "${BLUE}=== Example 3: Speech-to-Text with Whisper ===${NC}"
echo ""
echo "# Install Whisper"
echo "pip install openai-whisper"
echo ""
echo "# Transcribe audio"
echo 'sq media transcribe --file audio.mp3'
echo ""
echo "# Save transcript"
echo 'sq media transcribe --file interview.mp3 --output transcript.txt'
echo ""

# Example 4: Text-to-Speech (TTS)
echo -e "${BLUE}=== Example 4: Text-to-Speech ===${NC}"
echo ""
echo "# Generate speech from text"
echo 'sq media speak --text "Hello, this is AI speaking" --output speech.wav'
echo ""
echo "# Or use system TTS"
echo 'sq media speak --text "Welcome to Streamware" --output welcome.wav'
echo ""

# Example 5: Music Analysis
echo -e "${BLUE}=== Example 5: Music Analysis ===${NC}"
echo ""
echo 'sq media analyze_music --file song.mp3'
echo ""
echo "# Output:"
echo '{
  "success": true,
  "file": "song.mp3",
  "tempo": 120.5,
  "duration": 180.0,
  "analysis": "Music analysis complete"
}'
echo ""

# Example 6: Auto Caption Any Media
echo -e "${CYAN}=== Example 6: Auto Caption (Video, Image, or Audio) ===${NC}"
echo ""
echo "# Auto-detect type and generate caption"
echo 'sq media caption --file video.mp4'
echo 'sq media caption --file photo.jpg'
echo 'sq media caption --file audio.mp3'
echo ""

# Example 7: Video Surveillance with AI
echo -e "${CYAN}=== Example 7: AI Video Surveillance ===${NC}"
echo ""
cat << 'EOF'
#!/bin/bash
# Monitor camera feed with AI descriptions

while true; do
    # Capture frame from camera
    ffmpeg -i rtsp://camera/stream -vframes 1 frame.jpg
    
    # Describe what's happening
    desc=$(sq media describe_image --file frame.jpg --model llava | jq -r '.description')
    
    # Check for suspicious activity
    if echo "$desc" | grep -i "person"; then
        # Alert
        sq slack security --message "Person detected: $desc"
    fi
    
    sleep 5
done
EOF
echo ""

# Example 8: Podcast Transcription Pipeline
echo -e "${CYAN}=== Example 8: Podcast Transcription Pipeline ===${NC}"
echo ""
cat << 'EOF'
#!/bin/bash
# Complete podcast processing

# 1. Download podcast
sq get https://podcast.com/episode.mp3 --save episode.mp3

# 2. Transcribe
sq media transcribe --file episode.mp3 --output transcript.txt

# 3. Analyze with LLM
cat transcript.txt | sq llm "summarize this podcast" --analyze

# 4. Generate blog post
sq llm "write a blog post about this podcast: $(cat transcript.txt)" \
    --output blog.md

# 5. Publish
sq post https://myblog.com/api/posts --data @blog.md
EOF
echo ""

# Example 9: Content Moderation
echo -e "${CYAN}=== Example 9: Content Moderation ===${NC}"
echo ""
cat << 'EOF'
#!/bin/bash
# Moderate user-uploaded content

for file in uploads/*; do
    # Analyze content
    desc=$(sq media caption --file "$file" | jq -r '.description')
    
    # Check for inappropriate content
    result=$(echo "$desc" | sq llm "is this appropriate for kids?" --analyze)
    
    if echo "$result" | grep -i "no"; then
        # Flag content
        echo "Flagged: $file"
        mv "$file" quarantine/
        
        # Notify moderators
        sq slack moderation --message "Content flagged: $file - $desc"
    fi
done
EOF
echo ""

# Example 10: Multilingual Transcription
echo -e "${CYAN}=== Example 10: Multilingual Transcription ===${NC}"
echo ""
cat << 'EOF'
# Transcribe in different languages
sq media transcribe --file spanish.mp3 --language es
sq media transcribe --file french.mp3 --language fr
sq media transcribe --file japanese.mp3 --language ja

# Translate transcription
sq media transcribe --file german.mp3 | \
  sq llm "translate this to English" --analyze
EOF
echo ""

# Example 11: Video Summary Generation
echo -e "${CYAN}=== Example 11: Video Summary Generation ===${NC}"
echo ""
cat << 'EOF'
#!/bin/bash
# Generate comprehensive video summary

VIDEO="lecture.mp4"

# 1. Visual description
visual=$(sq media describe_video --file "$VIDEO" --model llava | jq -r '.description')

# 2. Audio transcription
audio=$(sq media transcribe --file "$VIDEO" | jq -r '.text')

# 3. Combine and summarize
summary=$(cat << END | sq llm "create a comprehensive summary"
Visual: $visual

Spoken Content: $audio
END
)

echo "$summary" > summary.txt

# 4. Create presentation
sq llm "create presentation slides from: $summary" --output slides.md
EOF
echo ""

# Example 12: Music Description
echo -e "${CYAN}=== Example 12: Music Description with AI ===${NC}"
echo ""
cat << 'EOF'
# Describe music style and mood
sq media analyze_music --file song.mp3 | \
  sq llm "describe the music style and mood" --analyze

# Generate playlist based on mood
sq media analyze_music --file song1.mp3 | \
  sq llm "suggest similar songs" --analyze
EOF
echo ""

# Example 13: Deploy Media Service
echo -e "${CYAN}=== Example 13: Deploy Media Analysis Service ===${NC}"
echo ""
cat << 'EOF'
#!/bin/bash
# Deploy AI media analysis as a service

# 1. Create service script
cat > media_service.py << 'PYTHON'
from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.route('/analyze/video', methods=['POST'])
def analyze_video():
    file = request.files['video']
    file.save('temp.mp4')
    
    result = subprocess.run(
        ['sq', 'media', 'describe_video', '--file', 'temp.mp4'],
        capture_output=True, text=True
    )
    
    return jsonify(eval(result.stdout))

@app.route('/transcribe', methods=['POST'])
def transcribe():
    file = request.files['audio']
    file.save('temp.mp3')
    
    result = subprocess.run(
        ['sq', 'media', 'transcribe', '--file', 'temp.mp3'],
        capture_output=True, text=True
    )
    
    return jsonify(eval(result.stdout))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
PYTHON

# 2. Install as service
sq service install --name media-api --command "python media_service.py"

# 3. Start service
sq service start --name media-api

# 4. Check status
sq service status --name media-api

# 5. Use the API
curl -X POST -F "video=@video.mp4" http://localhost:8080/analyze/video
curl -X POST -F "audio=@audio.mp3" http://localhost:8080/transcribe
EOF
echo ""

echo "======================================================================"
echo "EXAMPLES COMPLETE!"
echo "======================================================================"
echo ""
echo -e "${GREEN}✓ Video description with LLaVA${NC}"
echo -e "${GREEN}✓ Image analysis${NC}"
echo -e "${GREEN}✓ Speech-to-text (STT)${NC}"
echo -e "${GREEN}✓ Text-to-speech (TTS)${NC}"
echo -e "${GREEN}✓ Music analysis${NC}"
echo -e "${GREEN}✓ Auto captioning${NC}"
echo -e "${GREEN}✓ Video surveillance${NC}"
echo -e "${GREEN}✓ Podcast transcription${NC}"
echo -e "${GREEN}✓ Content moderation${NC}"
echo -e "${GREEN}✓ Service deployment${NC}"
echo ""
echo "Try it yourself:"
echo "  # Install LLaVA"
echo "  ollama pull llava"
echo ""
echo "  # Describe video"
echo "  sq media describe_video --file video.mp4"
echo ""
echo "  # Transcribe audio"
echo "  sq media transcribe --file audio.mp3"
echo ""
echo "  # Generate speech"
echo "  sq media speak --text 'Hello World' --output hello.wav"
echo ""
