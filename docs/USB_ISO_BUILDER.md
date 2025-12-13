# USB/ISO Builder Documentation

Create bootable USB drives and ISO images for offline LLM environments on AMD GPU hardware.

> **Full documentation**: [environments/usb-builder/README.md](../environments/usb-builder/README.md)

## Quick Start

```bash
cd environments/usb-builder

# Install dependencies
make install

# Build bootable ISO
make iso-build

# Test in VM
make iso-test

# Deep validation
make test-deep
```

## Available Outputs

| Output | Command | Description |
|--------|---------|-------------|
| Live ISO | `make iso-build` | Bootable Fedora + LLM Station (~1.8GB) |
| Models ISO | `make models-iso` | Compressed LLM models (size varies) |
| USB (single) | `make usb USB=/dev/sdX` | Single partition bootable USB |
| USB (hybrid) | `make usb-hybrid USB=/dev/sdX` | Dual partition: Linux + Data |

## Hybrid USB Layout (30GB example)

```
/dev/sdX
├── Partition 1 (8GB, FAT32, EFI)
│   └── Bootable Fedora Live system
└── Partition 2 (22GB, ext4)
    ├── environments/     # LLM configurations
    ├── models/ollama/    # Ollama models
    ├── models/gguf/      # GGUF models
    └── images/           # Container images
```

## Testing

```bash
# Quick test in QEMU
make iso-test

# GUI test with virt-manager
make iso-test-gui

# Deep validation (checks boot config, labels, structure)
make test-deep

# Verify checksums
make verify
```

## Target Hardware

- **CPU**: AMD Ryzen 9 7940HS (UM790 Pro)
- **GPU**: AMD Radeon 780M (RDNA3)
- **RAM**: 16GB+
- **Storage**: 64GB+ USB drive

## Related Documentation

- [Main README](../README.md)
- [Architecture](ARCHITECTURE.md)
- [LLM Integration](LLM_INTEGRATION.md)
- [USB Builder Details](../environments/usb-builder/README.md)
- [Refactoring Plan](../environments/usb-builder/REFACTORING_PLAN.md)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DISTRO` | `fedora` | Base distro (fedora/ubuntu) |
| `ISO_NAME` | `llm-station-um790pro.iso` | Output filename |
| `RAM` | `8G` | QEMU RAM for testing |
| `CPUS` | `4` | QEMU CPUs for testing |
