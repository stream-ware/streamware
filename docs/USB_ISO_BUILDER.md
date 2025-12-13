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
├── Partition 1 (8GB, FAT32, EFI)
│   └── Bootable Linux Live system
│   └── LLM Station scripts
└── Partition 2 (22GB, ext4)
    ├── environments/     # LLM configurations
    ├── models/ollama/    # Ollama models
    ├── models/gguf/      # GGUF models
    └── images/           # Container images
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

## After Booting

```bash
# Mount data partition (usually auto-mounted)
# Run setup script
/run/media/$USER/LLM-DATA/setup.sh

# Or manually
sudo /cdrom/llm-data/first-boot.sh
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
