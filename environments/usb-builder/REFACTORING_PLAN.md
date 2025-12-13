# USB/ISO Builder Refactoring Plan

## Current State

The USB/ISO builder consists of several shell scripts that create bootable media for offline LLM environments. While functional, there are opportunities for improvement.

## Identified Issues

### 1. Code Duplication
- `build-iso.sh` and `build-usb.sh` share similar logic for:
  - Dependency checking
  - Environment detection
  - Container image handling
  - First-boot script generation

### 2. Error Handling
- Some scripts use `set -e` but lack proper cleanup on failure
- Temp directories may not be cleaned up on errors
- No rollback mechanism for partial builds

### 3. Configuration Management
- Hardcoded values scattered across scripts
- No central configuration file
- Environment variables not documented consistently

### 4. Testing
- No automated tests for build scripts
- Manual testing required for each change
- No CI/CD integration

### 5. Modularity
- Scripts are monolithic
- Difficult to reuse components
- No plugin system for different distros

---

## Refactoring Phases

### Phase 1: Extract Common Functions (Priority: High)

**Goal**: Create shared library of functions

**Tasks**:
1. Create `lib/common.sh` with shared functions:
   - `check_deps()` - dependency checking
   - `verify_iso()` - ISO validation
   - `cleanup()` - temp directory cleanup
   - `log_info()`, `log_warn()`, `log_error()` - logging
   - `check_root()` - root permission check

2. Create `lib/cache.sh` for caching logic:
   - `cache_get()` - retrieve from cache
   - `cache_put()` - store in cache
   - `cache_verify()` - verify cache integrity
   - `cache_clean()` - clean cache

3. Create `lib/container.sh` for container operations:
   - `container_pull()` - pull image
   - `container_save()` - save to tar
   - `container_load()` - load from tar

**Estimated effort**: 4-6 hours

### Phase 2: Configuration File (Priority: High)

**Goal**: Centralize configuration

**Tasks**:
1. Create `config.sh` with all configurable values:
   ```bash
   # config.sh
   ISO_NAME="llm-station-um790pro.iso"
   DISTRO="fedora"
   BASE_ISO_URL_FEDORA="..."
   BASE_ISO_URL_UBUNTU="..."
   CONTAINER_IMAGES=("ollama/ollama:rocm" "ghcr.io/open-webui/open-webui:main")
   RAM_DEFAULT="8G"
   CPUS_DEFAULT="4"
   ```

2. Support `.env` file for user overrides

3. Document all configuration options

**Estimated effort**: 2-3 hours

### Phase 3: Error Handling & Cleanup (Priority: High)

**Goal**: Robust error handling with proper cleanup

**Tasks**:
1. Implement trap-based cleanup:
   ```bash
   cleanup() {
       [ -d "$WORK_DIR" ] && rm -rf "$WORK_DIR"
       [ -n "$MOUNT_POINT" ] && umount "$MOUNT_POINT" 2>/dev/null
   }
   trap cleanup EXIT
   ```

2. Add error codes for different failure types

3. Implement `--dry-run` mode for testing

4. Add `--verbose` and `--quiet` modes

**Estimated effort**: 3-4 hours

### Phase 4: Modular Distro Support (Priority: Medium)

**Goal**: Plugin system for different base distros

**Tasks**:
1. Create `distros/` directory with per-distro configs:
   ```
   distros/
   ├── fedora.sh
   ├── ubuntu.sh
   └── arch.sh
   ```

2. Each distro file defines:
   - `DISTRO_ISO_URL`
   - `DISTRO_PACKAGES`
   - `distro_post_install()`
   - `distro_boot_config()`

3. Auto-detect distro from ISO or allow override

**Estimated effort**: 4-5 hours

### Phase 5: Testing Framework (Priority: Medium)

**Goal**: Automated testing for build scripts

**Tasks**:
1. Create `tests/` directory with test scripts:
   ```
   tests/
   ├── test_common.sh
   ├── test_cache.sh
   ├── test_iso_build.sh
   └── run_tests.sh
   ```

2. Use `bats` (Bash Automated Testing System) or simple assertions

3. Add mock mode for testing without actual downloads

4. Integrate with CI (GitHub Actions)

**Estimated effort**: 6-8 hours

### Phase 6: Python Wrapper (Priority: Low)

**Goal**: Python CLI for better integration with streamware

**Tasks**:
1. Create `streamware/cli/iso_builder.py`:
   ```python
   @click.command()
   @click.option('--distro', default='fedora')
   @click.option('--output', default='output/')
   def build_iso(distro, output):
       ...
   ```

2. Add to main CLI: `sq iso-build`, `sq iso-test`

3. Better progress reporting with rich/tqdm

4. Cross-platform support (Windows WSL, macOS)

**Estimated effort**: 8-10 hours

---

## Proposed Directory Structure

```
environments/usb-builder/
├── lib/
│   ├── common.sh       # Shared functions
│   ├── cache.sh        # Caching logic
│   ├── container.sh    # Container operations
│   └── boot.sh         # Boot configuration
├── distros/
│   ├── fedora.sh       # Fedora-specific
│   ├── ubuntu.sh       # Ubuntu-specific
│   └── arch.sh         # Arch-specific
├── templates/
│   ├── first-boot.sh   # First boot template
│   ├── autostart.desktop
│   └── grub.cfg        # GRUB config template
├── tests/
│   ├── test_common.sh
│   ├── test_cache.sh
│   └── run_tests.sh
├── cache/              # Downloaded files
├── output/             # Built ISOs
├── config.sh           # Configuration
├── build-iso.sh        # Main ISO builder
├── build-usb.sh        # Main USB builder
├── test-iso.sh         # ISO tester
├── diagnose.sh         # Diagnostics
└── README.md
```

---

## Priority Matrix

| Phase | Priority | Effort | Impact |
|-------|----------|--------|--------|
| 1. Common Functions | High | 4-6h | High |
| 2. Configuration | High | 2-3h | Medium |
| 3. Error Handling | High | 3-4h | High |
| 4. Distro Plugins | Medium | 4-5h | Medium |
| 5. Testing | Medium | 6-8h | High |
| 6. Python Wrapper | Low | 8-10h | Medium |

**Total estimated effort**: 27-36 hours

---

## Quick Wins (Do First)

1. **Add trap cleanup** - 30 min, prevents orphaned temp dirs
2. **Create config.sh** - 1 hour, centralizes settings
3. **Add --dry-run** - 1 hour, safer testing
4. **Extract verify_iso()** - 30 min, reusable validation

---

## Migration Path

1. Start with Phase 1 (common functions) - no breaking changes
2. Add config.sh alongside existing scripts
3. Gradually migrate scripts to use common functions
4. Add tests for each migrated component
5. Python wrapper last (optional enhancement)

---

## Success Metrics

- [ ] All scripts use common functions
- [ ] Single config file for all settings
- [ ] No orphaned temp directories on failure
- [ ] 80%+ test coverage for shell functions
- [ ] CI passes on all PRs
- [ ] Documentation up to date
