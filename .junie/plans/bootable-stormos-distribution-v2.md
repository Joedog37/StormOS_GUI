---
sessionId: session-261120-111415-1vmp
---

# Requirements

### Overview & Goals

Update the bootable StormOS distribution plan based on Muse AI feedback. The key fixes address Python 3.13 compatibility, boot startup consistency, security, hardware drivers, and build environment requirements.

### Goals
- Use **Debian trixie** (testing) instead of bookworm for Python 3.13 support
- Pick **one** boot method for StormOS (systemd service only) instead of mixing approaches
- Remove `pam_nologin` which blocks logins
- Add **auto-driver detection** for NVIDIA and other GPUs (including proprietary drivers)
- Note that Secure Boot must be disabled in BIOS
- Update the App Store to load Linux programs (native .deb/apt packages)
- Note that the ISO must be built on Linux (WSL or VM), not Windows

### User Stories
- As a developer, I want to build the StormOS ISO on WSL or a Linux VM because Windows can't run live-build
- As a user with an NVIDIA RTX 3050, I want auto-detected proprietary drivers so games run fast
- As a user, I want to install Linux programs (Firefox, Steam, etc.) from the App Store via apt
- As a user, I want StormOS to boot reliably with a single, consistent startup method

### Scope

**In Scope:**
- Update `docs/bootable-os-research.md` with corrected requirements
- Update distribution build system design (Debian trixie, live-build)
- Simplify boot configuration to single systemd service approach
- Add auto-driver detection and installation (NVIDIA proprietary + open-source)
- Update App Store design to support native Linux program loading
- Document build environment requirements (Linux/WSL only)
- Document Secure Boot requirement

**Out of Scope:**
- Actual ISO building (Phase 11 implementation)
- Raspberry Pi / ARM support
- Custom kernel development


# Technical Design

### Current Implementation

**Existing files:**
- `docs/bootable-os-research.md` — research document covering Buildroot, Yocto, and live USB approaches
- `src/stormos/core/platform_compat.py` — cross-platform layer with Linux support (XDG paths, display detection, desktop env detection)
- `src/stormos/apps/app_manager.py` — App Store UI with `.stormapp` package installation
- `src/stormos/services/app_installer.py` — package installer service with validation and security
- `src/stormos/core/paths.py` — path resolution with `sys.frozen` support for PyInstaller bundles

**Issues identified by Muse AI:**
1. **Debian bookworm** has Python 3.11, not 3.13 → need **trixie** (testing)
2. **Mixed boot methods**: systemd service + getty autologin + .xinitrc → pick one
3. **pam_nologin** blocks logins → remove it
4. **Open-source drivers only** → NVIDIA RTX 3050 will be slow; user wants auto-detect all drivers
5. **Secure Boot** not mentioned → must be disabled
6. **App Store** doesn't load Linux programs → needs apt integration
7. **ISO build** must be on Linux → document WSL/VM requirement

### Key Decisions

1. **Debian trixie (testing)** — Python 3.13 is available in trixie, not bookworm. Testing branch is stable enough for custom distros.
2. **Single boot method: systemd service** — StormOS starts as a systemd user service after graphical.target. No .xinitrc, no getty autologin mixing. Auto-login via `systemd-logind.conf` `AutoVCLogin=` or `pam_nologin` replacement with `pam_autologin`.
3. **Auto-driver detection** — script detects GPU hardware (lspci), checks for NVIDIA/AMD/Intel, installs proprietary NVIDIA drivers (`nvidia-driver`) or uses open-source (nouveau, amdgpu, i915) with user confirmation.
4. **App Store Linux integration** — add a `LinuxProgramLoader` that scans installed apt packages for desktop entries (`/usr/share/applications/`) and creates StormOS app wrappers.
5. **Secure Boot disabled** — document in build guide and install guide.
6. **Build on Linux** — document WSL2 or Ubuntu VM as build environment.

### Proposed Changes

**1. `docs/bootable-os-research.md` — Update requirements section**
- Change "Debian bookworm" → "Debian trixie (testing)" with Python 3.13 rationale
- Add Secure Boot requirement: "Must be disabled in BIOS/UEFI to boot the ISO"
- Add build environment: "ISO must be built on Linux (WSL2 or Ubuntu VM), not Windows"
- Update driver section: add auto-detection script for NVIDIA proprietary drivers

**2. `docs/bootable-os-research.md` — Simplify boot configuration**
- Remove .xinitrc approach entirely
- Remove getty autologin override
- Keep only: systemd service for StormOS + systemd auto-login via `systemd-logind.conf`
- Fix the .xinitrc line mentioned: it should run the app directly, not `startx`

**3. `docs/bootable-os-research.md` — Add auto-driver detection design**
- Create `dist/scripts/setup_drivers.sh` that:
  - Runs `lspci | grep -i vga` to detect GPU
  - Checks for NVIDIA: installs `nvidia-driver` (proprietary) with user prompt
  - Checks for AMD: uses `amdgpu` (open-source, good performance)
  - Checks for Intel: uses `i915` (open-source, good performance)
  - Falls back to `llvmpipe` (software rendering) if no driver matches

**4. App Store Linux program loading**
- Add `src/stormos/services/linux_program_loader.py` — scans `/usr/share/applications/*.desktop` files
- Parses desktop entries: name, icon, exec command, categories
- Creates StormOS AppMetadata wrappers for each Linux program
- Registers them in AppRegistry so they appear in the App Store and Start menu
- Handles launching via subprocess with proper environment

**5. `src/stormos/apps/app_manager.py` — Add Linux programs section**
- Add a "Linux Programs" tab/section alongside installed apps
- Shows apps detected from the system (Firefox, LibreOffice, etc.)
- Launch button runs the native Linux executable
- Install button runs `apt install` for the package

### File Structure

```
StormOS_GUI/
  docs/
    bootable-os-research.md       # UPDATED: all fixes from Muse AI feedback
  src/stormos/
    services/
      linux_program_loader.py     # NEW: scans and wraps Linux desktop entries
    apps/
      app_manager.py              # UPDATED: add Linux programs section
    core/
      platform_compat.py          # UPDATED: add GPU driver detection helpers
  dist/
    scripts/
      setup_drivers.sh            # NEW: auto-detect and install GPU drivers
      build_iso.sh                # UPDATED: note Linux build requirement
    docs/
      build-guide.md              # UPDATED: WSL/VM build instructions
      install-guide.md            # UPDATED: Secure Boot warning
```

### Architecture Diagram

```
mermaid
graph LR
  ISO[StormOS ISO<br/>Debian trixie] --> GRUB[GRUB Bootloader]
  GRUB --> Kernel[Linux Kernel 6.x]
  Kernel --> systemd[systemd]
  systemd --> StormOS[StormOS Desktop<br/>via systemd service]
  systemd --> Apt[apt Package Manager]
  Apt --> Debian-Repo[Debian Repositories]
  Apt --> NVIDIA[NVIDIA Drivers<br/>auto-detected]
  Apt --> Mesa[Mesa Drivers<br/>open-source]
  StormOS --> LinuxLoader[LinuxProgramLoader<br/>scan .desktop files]
  LinuxLoader --> AppStore[App Store<br/>Linux programs tab]
  AppStore --> Launch[Launch native apps]
  StormOS --> WM[Window Manager]
  StormOS --> Apps[Built-in Apps]
```

### Risks

1. **Debian trixie stability** — testing branch may have broken packages
   - **Mitigation**: Pin critical packages to stable versions where needed
2. **NVIDIA driver installation** — proprietary drivers require non-free repo and may need kernel headers
   - **Mitigation**: Include `non-free` in sources.list, install `linux-headers` automatically
3. **Secure Boot** — users may not know to disable it
   - **Mitigation**: Clear warning in install guide and boot screen
4. **App Store apt integration** — running apt from within StormOS requires root/sudo
   - **Mitigation**: Use `pkexec` for privileged apt operations, or pre-install common apps in the ISO
5. **WSL2 build environment** — live-build may have issues in WSL2
   - **Mitigation**: Provide a full Ubuntu VM alternative with VirtualBox


# Testing

### Validation Approach

Verify that the updated documentation and new code components are correct:
1. **Documentation review** — check that all Muse AI fixes are applied
2. **Unit tests** — test LinuxProgramLoader parsing and wrapper creation
3. **Driver detection** — test GPU detection logic with mock lspci output

### Key Scenarios

1. **Debian trixie reference**
   - Verify `docs/bootable-os-research.md` mentions trixie, not bookworm
   - Verify Python 3.13 rationale is documented

2. **Boot configuration**
   - Verify only one boot method is documented (systemd service)
   - Verify .xinitrc and getty autologin are removed
   - Verify pam_nologin is not mentioned

3. **Driver detection**
   - Verify auto-driver detection script handles NVIDIA, AMD, Intel
   - Verify fallback to software rendering

4. **App Store Linux programs**
   - Verify LinuxProgramLoader parses .desktop files correctly
   - Verify App Store shows Linux programs section

5. **Build environment**
   - Verify documentation states Linux/WSL build requirement
   - Verify Secure Boot warning is present

### Test Changes

- **`tests/test_linux_program_loader.py`** — new tests for desktop entry parsing, app wrapper creation, and AppRegistry integration
- **`tests/test_driver_detection.py`** — tests for GPU detection logic with mock hardware data
- Update existing tests to verify no regressions in App Store functionality

# Delivery Plan

### ✓ Step 1: Update bootable-os-research.md with all Muse AI fixes
### ✓ Step 2: Create setup_drivers.sh auto-driver detection script
### ✓ Step 3: Create LinuxProgramLoader service
### ✓ Step 4: Update App Store for Linux programs
### ✓ Step 5: Create tests and validate
