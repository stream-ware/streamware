# Fixing X11 Display Issues for Automation

## Problem
```
Error: Can't connect to display ":0": Authorization required, but no authorization protocol specified
```

## Solutions

### 1. **Allow X11 Access (Quick Fix)**
```bash
# Allow local connections
xhost +local:

# Test automation
sq auto click --x 100 --y 200
```

### 2. **SSH with X11 Forwarding**
```bash
# Connect with X11 forwarding
ssh -X user@server

# Or with trusted forwarding
ssh -Y user@server

# Test
sq auto screenshot --text test.png
```

### 3. **Running as Different User**
```bash
# From the graphical session user, allow your user
xhost +SI:localuser:yourusername

# Or allow all local users (less secure)
xhost +local:
```

### 4. **Set DISPLAY Variable**
```bash
# Check current display
echo $DISPLAY

# Set if needed
export DISPLAY=:0

# Or specific display
export DISPLAY=:1
```

### 5. **Using Xvfb (Headless)**
```bash
# Install Xvfb
sudo apt-get install xvfb

# Run with virtual display
xvfb-run sq auto click --x 100 --y 200

# Or start Xvfb
Xvfb :99 -screen 0 1024x768x24 &
export DISPLAY=:99
sq auto click --x 100 --y 200
```

### 6. **Docker Environment**
```dockerfile
# In Dockerfile
RUN apt-get update && apt-get install -y \
    xvfb \
    x11-utils \
    python3-tk

# Set display
ENV DISPLAY=:99

# Start Xvfb in entrypoint
CMD Xvfb :99 -screen 0 1024x768x24 & python app.py
```

### 7. **Fix Permissions**
```bash
# Check X authority
ls -la ~/.Xauthority

# Fix ownership if needed
sudo chown $USER:$USER ~/.Xauthority

# Regenerate if corrupted
rm ~/.Xauthority
startx
```

## Testing

### Test 1: Screenshot
```bash
sq auto screenshot --text test.png
ls -la test.png
```

### Test 2: Click
```bash
# Get mouse position first
python3 -c "import pyautogui; print(pyautogui.position())"

# Click there
sq auto click --x 100 --y 200
```

### Test 3: Type
```bash
# Open text editor first
gedit &

# Type text
sleep 2
sq auto type --text "Hello from Streamware!"
```

## Common Scenarios

### Scenario 1: Running in Terminal with GUI
```bash
# This should work directly
sq auto click --x 100 --y 200
```

### Scenario 2: Running via SSH
```bash
# On server (one time)
xhost +local:

# Connect with X11
ssh -X user@server

# Test
sq auto screenshot --text remote.png
```

### Scenario 3: Running as Root/Sudo
```bash
# From your user session
xhost +SI:localuser:root

# Then as root
sudo sq auto click --x 100 --y 200
```

### Scenario 4: Cron Job
```bash
# In crontab
DISPLAY=:0
XAUTHORITY=/home/user/.Xauthority

0 * * * * sq auto screenshot --text /tmp/hourly.png
```

### Scenario 5: Systemd Service
```ini
[Service]
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/user/.Xauthority"
User=your-username

ExecStart=/path/to/sq auto screenshot
```

## Alternative: Use Without Display

### For Automation Testing
```python
# Use pynput or keyboard libraries
# These work without X11 in some cases

# Or mock for testing
import unittest.mock as mock
with mock.patch('pyautogui.click'):
    # Your automation code
    pass
```

### For Screenshots
```bash
# Use scrot or ImageMagick
scrot screenshot.png

# Or import from X
import -window root screenshot.png
```

## Troubleshooting

### Check Display
```bash
# See what displays are available
w

# Check DISPLAY variable
echo $DISPLAY

# List X clients
xwininfo -root -children
```

### Check Permissions
```bash
# Check xhost settings
xhost

# Check who can access
xauth list
```

### Debug Mode
```bash
# Run with debug
DISPLAY=:0 sq auto click --x 100 --y 200 --debug

# Check pyautogui
python3 -c "import pyautogui; pyautogui.click(100, 200)"
```

## Security Note

**Using `xhost +` opens X server to all local users!**

Better alternatives:
```bash
# Allow specific user only
xhost +SI:localuser:username

# Use xauth instead
xauth extract - $DISPLAY | ssh user@host xauth merge -

# Reset after testing
xhost -
```

## Quick Reference

| Issue | Solution |
|-------|----------|
| "Authorization required" | `xhost +local:` |
| "Cannot connect to display" | `export DISPLAY=:0` |
| SSH automation | `ssh -X user@host` |
| Headless server | `xvfb-run sq auto ...` |
| Permission denied | `sudo chown $USER ~/.Xauthority` |
| Different user | `xhost +SI:localuser:username` |

---

**Now you can automate desktop with Streamware!** 🖱️✨
