# =============================================================================
# LLM Station USB/ISO Builder Makefile
# =============================================================================
#
# Usage:
#   make install      - Install all dependencies
#   make prepare      - Download and cache all resources
#   make iso          - Build bootable ISO
#   make test         - Test ISO in QEMU
#   make clean        - Clean build artifacts
#
# =============================================================================

SHELL := /bin/bash
.PHONY: all install prepare iso usb test test-gui verify diagnose clean cache-clean help

# Directories
SCRIPT_DIR := $(shell pwd)
ENV_DIR := $(shell dirname $(SCRIPT_DIR))
CACHE_DIR := $(SCRIPT_DIR)/cache
OUTPUT_DIR := $(SCRIPT_DIR)/output

# Configuration (can be overridden)
DISTRO ?= fedora
ISO_NAME ?= llm-station-um790pro.iso
RAM ?= 8G
CPUS ?= 4

# Default target
all: help

# =============================================================================
# Installation
# =============================================================================

install: install-deps install-uefi
	@echo "✓ All dependencies installed"

install-deps:
	@echo "Installing build dependencies..."
	@if [ -f /etc/fedora-release ]; then \
		sudo dnf install -y xorriso squashfs-tools p7zip p7zip-plugins file syslinux curl; \
	elif [ -f /etc/debian_version ]; then \
		sudo apt-get update && \
		sudo apt-get install -y xorriso squashfs-tools p7zip-full file syslinux-utils curl; \
	elif [ -f /etc/arch-release ]; then \
		sudo pacman -S --noconfirm xorriso squashfs-tools p7zip file syslinux curl; \
	else \
		echo "Unknown distro. Please install: xorriso squashfs-tools p7zip file syslinux-utils curl"; \
		exit 1; \
	fi

install-uefi:
	@echo "Installing UEFI firmware for VM testing..."
	@if [ -f /etc/fedora-release ]; then \
		sudo dnf install -y edk2-ovmf; \
	elif [ -f /etc/debian_version ]; then \
		sudo apt-get install -y ovmf; \
	elif [ -f /etc/arch-release ]; then \
		sudo pacman -S --noconfirm edk2-ovmf; \
	fi

install-qemu:
	@echo "Installing QEMU for VM testing..."
	@if [ -f /etc/fedora-release ]; then \
		sudo dnf install -y qemu-kvm qemu-system-x86; \
	elif [ -f /etc/debian_version ]; then \
		sudo apt-get install -y qemu-kvm qemu-system-x86; \
	elif [ -f /etc/arch-release ]; then \
		sudo pacman -S --noconfirm qemu-full; \
	fi

install-virt-manager:
	@echo "Installing virt-manager..."
	@if [ -f /etc/fedora-release ]; then \
		sudo dnf install -y virt-manager; \
	elif [ -f /etc/debian_version ]; then \
		sudo apt-get install -y virt-manager; \
	elif [ -f /etc/arch-release ]; then \
		sudo pacman -S --noconfirm virt-manager; \
	fi

# =============================================================================
# Build
# =============================================================================

prepare:
	@echo "Preparing offline resources..."
	@./prepare-offline.sh

iso: $(OUTPUT_DIR)/$(ISO_NAME)
	@echo "✓ ISO ready: $(OUTPUT_DIR)/$(ISO_NAME)"

$(OUTPUT_DIR)/$(ISO_NAME): prepare-dirs
	@echo "Building ISO..."
	@sudo DISTRO=$(DISTRO) ISO_NAME=$(ISO_NAME) ./build-iso.sh

usb:
	@echo "Building bootable USB..."
	@if [ -z "$(USB)" ]; then \
		echo "Usage: make usb USB=/dev/sdX"; \
		echo ""; \
		echo "Available devices:"; \
		lsblk -d -o NAME,SIZE,MODEL | grep -v loop; \
		exit 1; \
	fi
	@sudo ./build-usb.sh $(USB)

prepare-dirs:
	@mkdir -p $(CACHE_DIR)/iso $(CACHE_DIR)/images $(OUTPUT_DIR)

# =============================================================================
# Testing
# =============================================================================

test:
	@echo "Testing ISO in QEMU..."
	@RAM=$(RAM) CPUS=$(CPUS) ./test-iso.sh

test-gui:
	@echo "Opening virt-manager..."
	@./test-iso.sh --gui

verify:
	@echo "Verifying ISO..."
	@./verify-iso.sh $(OUTPUT_DIR)/$(ISO_NAME)

# =============================================================================
# Diagnostics
# =============================================================================

diagnose:
	@./diagnose.sh

diagnose-full:
	@./diagnose.sh --full

status:
	@echo "=== Cache Status ==="
	@echo "ISO cache:"
	@ls -lh $(CACHE_DIR)/iso/*.iso 2>/dev/null || echo "  (empty)"
	@echo ""
	@echo "Container images:"
	@ls -lh $(CACHE_DIR)/images/*.tar 2>/dev/null || echo "  (empty)"
	@echo ""
	@echo "=== Output ==="
	@ls -lh $(OUTPUT_DIR)/*.iso 2>/dev/null || echo "  (no ISO built)"

# =============================================================================
# Cleanup
# =============================================================================

clean:
	@echo "Cleaning build artifacts..."
	@sudo rm -rf $(OUTPUT_DIR)/*.iso $(OUTPUT_DIR)/*.sha256 $(OUTPUT_DIR)/*.md5
	@echo "✓ Build artifacts cleaned"

cache-clean:
	@echo "Cleaning cache..."
	@sudo rm -rf $(CACHE_DIR)/iso/* $(CACHE_DIR)/images/*
	@echo "✓ Cache cleaned"

clean-all: clean cache-clean
	@echo "✓ All cleaned"

# =============================================================================
# Development
# =============================================================================

lint:
	@echo "Checking shell scripts..."
	@command -v shellcheck >/dev/null && shellcheck *.sh lib/*.sh 2>/dev/null || echo "Install shellcheck for linting"

test-lib:
	@echo "Running library tests..."
	@if [ -d tests ]; then ./tests/run_tests.sh; else echo "No tests yet"; fi

# =============================================================================
# Help
# =============================================================================

help:
	@echo "LLM Station USB/ISO Builder"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Installation:"
	@echo "  install          Install all dependencies"
	@echo "  install-deps     Install build tools only"
	@echo "  install-uefi     Install UEFI firmware"
	@echo "  install-qemu     Install QEMU for testing"
	@echo ""
	@echo "Build:"
	@echo "  prepare          Download and cache resources"
	@echo "  iso              Build bootable ISO"
	@echo "  usb USB=/dev/sdX Build bootable USB"
	@echo ""
	@echo "Testing:"
	@echo "  test             Test ISO in QEMU"
	@echo "  test-gui         Open virt-manager"
	@echo "  verify           Verify ISO integrity"
	@echo ""
	@echo "Diagnostics:"
	@echo "  diagnose         Quick diagnostics"
	@echo "  diagnose-full    Full diagnostics"
	@echo "  status           Show cache/output status"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean            Remove built ISO"
	@echo "  cache-clean      Clear download cache"
	@echo "  clean-all        Remove everything"
	@echo ""
	@echo "Configuration (environment variables):"
	@echo "  DISTRO=$(DISTRO)    Base distribution"
	@echo "  ISO_NAME=$(ISO_NAME)"
	@echo "  RAM=$(RAM)          QEMU RAM"
	@echo "  CPUS=$(CPUS)         QEMU CPUs"
