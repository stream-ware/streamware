# USB/ISO Builder Documentation

Create bootable USB drives and ISO images for offline LLM environments on AMD GPU hardware.

> **Full documentation**: [environments/usb-builder/README.md](../environments/usb-builder/README.md)

## Quick Start

```bash
cd environments/usb-builder

# Install dependencies
make install

# Build bootable ISO (Fedora)
make iso-build

# Create hybrid USB (interactive device selection)
make usb-hybrid

# Or with specific device
make usb-hybrid USB=/dev/sdX

# Verify USB
make usb-verify USB=/dev/sdX

# Test USB boot in QEMU
make usb-test USB=/dev/sdX
```

## Supported Distributions

| Distro | Command | Description |
|--------|---------|-------------|
| Fedora LXQt | `make usb-hybrid` | Default, lightweight (~1.8GB) |
| openSUSE Tumbleweed | `make usb-suse` | Rolling release, KDE (~2.5GB) |
| openSUSE Leap | `make usb-suse-leap` | Stable release (~2.3GB) |
| Ubuntu | `make usb-ubuntu` | Desktop (~5GB) |

## Available Outputs

| Output | Command | Description |
|--------|---------|-------------|
| Live ISO | `make iso-build` | Bootable Fedora + LLM Station (~1.8GB) |
| Models ISO | `make models-iso` | Compressed LLM models (size varies) |
| USB (single) | `make usb USB=/dev/sdX` | Single partition bootable USB |
| USB (hybrid) | `make usb-hybrid` | Dual partition: Linux + Data |

## Hybrid USB Layout (30GB example)

```
/dev/sdX
├── Partition 1 (8GB, FAT32, EFI) - INTELI-LIVE
│   ├── EFI/BOOT/           # UEFI bootloader
│   ├── LiveOS/             # Squashfs root filesystem
│   ├── images/pxeboot/     # Kernel + initrd
│   ├── etc/skel/.config/autostart/  # Desktop autostart
│   └── usr/local/bin/      # Autorun scripts
│
└── Partition 2 (22GB, ext4) - LLM-DATA
    ├── streamware/         # Full project (dev mode, with .git)
    ├── environments/       # LLM configurations
    ├── models/ollama/      # Ollama models
    ├── models/gguf/        # GGUF models
    ├── images/             # Container images (.tar)
    ├── config/             # Configuration files
    │   └── accounting.conf # Streamware accounting config
    ├── setup.sh            # Manual setup script
    ├── install-service.sh  # Systemd service installer
    ├── autostart.sh        # Main autostart script
    └── llm-station.service # Systemd service file
```

```
Boot → Login → Terminal otwiera się automatycznie
                    ↓
         "LLM Station First Boot Setup"
                    ↓
         Montuje LLM-DATA partition
                    ↓
         Uruchamia install-service.sh
                    ↓
         Instaluje systemd service
                    ↓
         Uruchamia autostart.sh:
           - Python + pip
           - Streamware (dev mode)
           - Ollama + llava:7b
           - Open-WebUI container
           - sq accounting web
                    ↓
         "LLM Station installed successfully!"
         
         Services:
           Open-WebUI:  http://localhost:3000
           Ollama API:  http://localhost:11434
           Accounting:  http://localhost:8080
```

## USB Verification

After creating USB, verify it:

```bash
make usb-verify USB=/dev/sdX
```

This checks:
- Partition table (GPT)
- Filesystems (FAT32, ext4)
- EFI bootloader
- GRUB configuration
- Kernel, initrd, squashfs
- LLM Station content
- Models and container images

## Testing

```bash
# Test USB boot in QEMU
make usb-test USB=/dev/sdX

# Test ISO in QEMU
make iso-test

# GUI test with virt-manager
make iso-test-gui

# Deep ISO validation
make test-deep
```

## Target Hardware

- **CPU**: AMD Ryzen 9 7940HS (UM790 Pro)
- **GPU**: AMD Radeon 780M (RDNA3)
- **RAM**: 16GB+
- **Storage**: 16GB+ USB drive (32GB+ recommended)

## After Booting (Fully Automatic!)

**Everything starts automatically on first boot:**

1. Terminal opens with setup wizard
2. Installs systemd service
3. Starts all services:
   - **Ollama** (port 11434) + downloads llava:7b model
   - **Open-WebUI** (port 3000)
   - **Streamware accounting** (port 8080)

### Available Services

| Service | URL | Description |
|---------|-----|-------------|
| Open-WebUI | http://localhost:3000 | Chat interface for LLMs |
| Ollama API | http://localhost:11434 | LLM inference API |
| Accounting | http://localhost:8080 | `sq accounting web` (see [docs/ACCOUNTING.md](ACCOUNTING.md)) |

### Service Management

```bash
# Check status
sudo systemctl status llm-station

# View logs
sudo journalctl -u llm-station -f

# Restart services
sudo systemctl restart llm-station
```

### Configuration

Edit `/run/media/$USER/LLM-DATA/config/accounting.conf`:

```bash
PROJECT="faktury"        # Project name
SOURCE="camera"          # camera, screen, or rtsp://...
PORT="8080"              # Web interface port
TTS_ENABLED="false"      # Voice announcements
MODEL="llava:7b"         # Ollama model
```

### Development Mode

The entire streamware project is copied to USB:

```bash
cd /run/media/$USER/LLM-DATA/streamware

# Activate dev environment
./activate-dev.sh

# Now you can edit code and test
sq --help
pytest tests/
```

## Related Documentation

- [Main README](../README.md)
- [Architecture](ARCHITECTURE.md)
- [LLM Integration](LLM_INTEGRATION.md)
- [USB Builder Details](../environments/usb-builder/README.md)
- [Refactoring Plan](../environments/usb-builder/REFACTORING_PLAN.md)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DISTRO` | `fedora` | Base distro (fedora/ubuntu/suse/suse-leap) |
| `ISO_NAME` | `llm-station-um790pro.iso` | Output filename |
| `RAM` | `8G` | QEMU RAM for testing |
| `CPUS` | `4` | QEMU CPUs for testing |
| `LIVE_PARTITION_SIZE` | `8G` | Size of boot partition |
