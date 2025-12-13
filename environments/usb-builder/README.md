# LLM Station USB/ISO Builder

Create bootable USB drives and ISO images for offline LLM environments on AMD GPU hardware (UM790 Pro, etc.).

## Quick Start

```bash
# 1. Prepare offline resources (downloads ~5GB)
make usb-prepare

# 2. Build bootable ISO
make iso-build

# 3. Test in virtual machine
make iso-test
```

## Features

- **Offline LLM environments**: Ollama + Open-WebUI, llama.cpp + ROCm
- **AMD GPU support**: ROCm drivers, GPU passthrough for containers
- **Caching**: Downloads cached for fast rebuilds
- **Multiple output formats**: USB drive or ISO for Balena Etcher

## Requirements

### Host System
- Linux (Fedora, Ubuntu, Arch)
- 10GB+ free disk space
- Internet connection (for initial download)

### Target Hardware
- AMD Ryzen with integrated GPU (Radeon 780M recommended)
- 16GB+ RAM
- 64GB+ USB drive (for USB build)

## Makefile Targets

### Build Commands
| Target | Description |
|--------|-------------|
| `make install` | Install all build dependencies |
| `make prepare` | Download and cache all offline resources |
| `make iso-build` | Build bootable Live ISO (Fedora) |
| `make models-iso` | Build separate Models ISO (compressed) |
| `make iso-all` | Build both Live ISO and Models ISO |

### USB Commands (Hybrid - 2 partitions)
| Target | Description |
|--------|-------------|
| `make usb-hybrid` | Build USB with Fedora (interactive) |
| `make usb-hybrid USB=/dev/sdX` | Build USB with Fedora |
| `make usb-suse` | Build USB with openSUSE Tumbleweed |
| `make usb-suse-leap` | Build USB with openSUSE Leap (stable) |
| `make usb-ubuntu` | Build USB with Ubuntu |
| `make usb USB=/dev/sdX` | Build single-partition USB |

### USB Verification & Testing
| Target | Description |
|--------|-------------|
| `make usb-verify` | Verify USB structure (interactive) |
| `make usb-verify USB=/dev/sdX` | Verify specific USB device |
| `make usb-test USB=/dev/sdX` | Boot USB in QEMU virtual machine |

### ISO Testing Commands
| Target | Description |
|--------|-------------|
| `make iso-test` | Test ISO in QEMU/KVM |
| `make iso-test-gui` | Open virt-manager for GUI testing |
| `make test-deep` | Deep validation of ISO structure |
| `make verify` | Verify ISO checksums |

### Maintenance Commands
| Target | Description |
|--------|-------------|
| `make clean` | Remove built ISO files |
| `make cache-clean` | Clear download cache |
| `make diagnose` | Quick environment diagnostics |
| `make diagnose-full` | Full diagnostics report |

## Scripts

| Script | Description |
|--------|-------------|
| `prepare-offline.sh` | Download and cache all resources |
| `build-iso.sh` | Build bootable Live ISO image |
| `build-models-iso.sh` | Build Models ISO with compressed LLM models |
| `build-usb.sh` | Build single-partition bootable USB |
| `build-usb-hybrid.sh` | Build dual-partition USB (Linux + Data) |
| `test-iso.sh` | Test ISO in QEMU or virt-manager |
| `test-iso-deep.sh` | Deep validation of ISO structure |
| `verify-usb.sh` | Verify USB drive structure and bootability |
| `diagnose.sh` | Run environment diagnostics |
| `config.sh` | Centralized configuration (distros, URLs) |

## Directory Structure

```
usb-builder/
├── lib/                    # Shared libraries (Phase 1 refactoring)
│   ├── common.sh           # Logging, error handling, utilities
│   ├── cache.sh            # Cache management
│   ├── container.sh        # Container operations
│   └── boot.sh             # Boot configuration generation
├── tests/                  # Automated tests
│   └── run_tests.sh        # Test runner
├── cache/
│   ├── iso/                # Cached base ISO downloads
│   └── images/             # Cached container images (.tar)
├── output/
│   └── llm-station-um790pro.iso
├── systemd/                # Systemd service files
├── config.sh               # Centralized configuration
├── Makefile                # Local build commands
├── build-iso.sh
├── build-usb.sh
├── prepare-offline.sh
├── test-iso.sh
├── verify-iso.sh
├── diagnose.sh
├── REFACTORING_PLAN.md     # Future improvements roadmap
└── README.md
```

## Workflow

### Building an ISO

```bash
# Step 1: Prepare (optional, for faster boot)
./prepare-offline.sh

# Step 2: Build ISO
sudo ./build-iso.sh

# Step 3: Test
./test-iso.sh
```

### Testing in QEMU

```bash
# CLI mode (default)
./test-iso.sh

# With custom settings
RAM=16G CPUS=8 ./test-iso.sh

# GUI mode (virt-manager)
./test-iso.sh --gui
```

### After Booting the ISO

```bash
# Run first-boot setup
sudo /cdrom/llm-data/first-boot.sh

# Start LLM environment
cd /opt/llm-station/ollama-webui
./start.sh

# Access Open-WebUI
firefox http://localhost:3000
```

## Caching

All downloads are cached to avoid repeated downloads:

| Cache | Location | Size |
|-------|----------|------|
| Base ISO | `cache/iso/` | ~1.5GB |
| Container images | `cache/images/` | ~3GB |
| Models | `../ollama-webui/models/` | ~4GB |

To clear cache:
```bash
make iso-cache-clean  # Clear ISO cache only
rm -rf cache/         # Clear all cache
```

## Troubleshooting

### ISO build fails with "corrupted download"
```bash
make iso-cache-clean
make iso-build
```

### QEMU shows black screen
Ensure UEFI firmware is installed:
```bash
# Fedora
sudo dnf install edk2-ovmf

# Ubuntu
sudo apt install ovmf
```

### No GPU acceleration in VM
GPU passthrough requires additional setup. For testing, software rendering is used.

### Container images not loading
Run `prepare-offline.sh` before building ISO for offline container support.

## Library Usage

The `lib/` directory contains reusable shell libraries:

```bash
# Source libraries in your scripts
source "$(dirname "$0")/lib/common.sh"
source "$(dirname "$0")/lib/cache.sh"
source "$(dirname "$0")/lib/container.sh"

# Use functions
log_info "Starting build..."
cache_init
if cache_has_iso "Fedora.iso"; then
    log_success "Using cached ISO"
fi
```

### Available Libraries

| Library | Functions |
|---------|-----------|
| `lib/common.sh` | `log_info`, `log_success`, `log_warn`, `log_error`, `check_root`, `command_exists`, `ensure_dir`, `extract_iso`, `make_iso_hybrid` |
| `lib/cache.sh` | `cache_init`, `cache_has_iso`, `cache_get_iso`, `cache_download_iso`, `cache_status`, `cache_clean_all` |
| `lib/container.sh` | `container_init`, `container_pull`, `container_save`, `container_load`, `container_pull_and_cache` |
| `lib/boot.sh` | `generate_first_boot_script`, `generate_autostart_desktop`, `generate_autorun_script` |

## Running Tests

```bash
# Run all library tests
make test-lib

# Or directly
./tests/run_tests.sh
```

## Related Documentation

- [Main README](../../README.md)
- [Architecture](../../ARCHITECTURE.md)
- [Refactoring Plan](REFACTORING_PLAN.md)
- [Ollama-WebUI Environment](../ollama-webui/README.md)
- [llama.cpp ROCm Environment](../llama-cpp-rocm/README.md)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DISTRO` | `fedora` | Base distro (`fedora` or `ubuntu`) |
| `ISO_NAME` | `llm-station-um790pro.iso` | Output ISO filename |
| `CACHE_DIR` | `./cache` | Cache directory path |
| `OUTPUT_DIR` | `./output` | Output directory path |
| `RAM` | `8G` | QEMU RAM allocation |
| `CPUS` | `4` | QEMU CPU count |
