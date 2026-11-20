---
sessionId: session-261120-111415-1vmp
---

# Requirements

### Overview & Goals

Transform StormOS from a Windows Python application into a bootable Debian-based Linux distribution with StormOS as the default desktop environment. The distribution will be installable via ISO image or Live USB, runnable in VirtualBox/VMware/QEMU virtual machines, and deployable on real x86_64 hardware.

### Goals
- Create a bootable Debian-based Linux distribution with StormOS as the sole desktop environment
- Support installation via ISO image and Live USB (try before install)
- Run in virtual machines (VirtualBox/VMware/QEMU) for testing
- Deploy on real x86_64 hardware
- Provide apt package management for installing Linux software
- Auto-login and launch StormOS at boot — no traditional desktop manager
- StormOS reads and runs Linux programs, manages windows, and looks like a standalone OS

### User Stories
- As a developer, I want to build a StormOS ISO so I can test it in a VM without affecting my main system
- As a user, I want to try StormOS from a Live USB before installing it permanently
- As a user, I want to install StormOS on my PC and have it boot directly into the StormOS desktop
- As a user, I want to install Linux software (browsers, games, etc.) via apt while using StormOS as my desktop
- As a developer, I want StormOS to manage windows, run apps, and handle all desktop functions without a traditional DE

### Scope

**In Scope:**
- Debian-based distribution build system using `live-build` or `debootstrap`
- Calamares graphical installer for ISO/Live USB
- GRUB bootloader configuration
- Linux kernel with hardware support (display, audio, network, USB)
- Display server (X11/Wayland) configuration
- Auto-login and StormOS startup via systemd
- StormOS porting for Linux (path resolution, platform-specific code)
- Python 3.13 + PySide6 installation on the base system
- apt package management and custom StormOS repository
- Virtual machine testing (VirtualBox/VMware/QEMU)
- Documentation for building and installing the distribution

**Out of Scope:**
- Raspberry Pi / ARM support (future phase)
- Custom kernel development (use mainline Linux kernel)
- Proprietary driver support (NVIDIA, etc.) — use open-source drivers
- Package signing infrastructure (initial phase)
- Multi-user login screen (auto-login only, initially)
- Firmware updates
- Secure boot support (initial phase)

### Non-Functional Requirements
- **Boot time**: Under 30 seconds to StormOS desktop on standard hardware
- **Minimum RAM**: 2GB (4GB recommended)
- **Minimum storage**: 16GB (32GB recommended)
- **ISO size**: Under 2GB for download
- **Live USB**: Runnable without installation for testing
- **Package management**: Full apt support for installing Linux software
- **Hardware acceleration**: GPU-accelerated rendering via Mesa drivers


# Technical Design

### Current Implementation

StormOS is a Python/PySide6 application with:
- **Entry point**: `main.py` → `stormos/app.py` → `StormMainWindow` (fullscreen)
- **Dependencies**: PySide6>=6.6.0, Pillow>=10.0.0
- **Cross-platform layer**: `src/stormos/core/platform_compat.py` (Phase 10) with `get_platform()`, `get_data_dir()`, etc.
- **Path resolution**: `src/stormos/core/paths.py` — uses `sys.frozen` for PyInstaller bundles, falls back to project root
- **Services**: User manager, audio manager, workspace manager, all in `src/stormos/services/`
- **Desktop**: Window management, task switcher, overview mode in `src/stormos/desktop/`
- **Apps**: Settings, file manager, terminal, etc. in `src/stormos/apps/`
- **Tests**: 269 tests passing, covering all phases 0–10

### Key Decisions

1. **Debian-based distribution** — uses `live-build` to create custom Debian with StormOS pre-installed, similar to how Linux Mint is based on Ubuntu
2. **Calamares installer** — modern, modular, graphical installer used by Manjaro, KDE Neon, etc.
3. **X11 display server** — more mature and widely supported than Wayland for Qt applications; can add Wayland later
4. **systemd init** — standard service management, auto-login via `pam_nologin` and systemd targets
5. **apt package management** — full Debian package support for installing Linux software
6. **Python system installation** — Python 3.13 and PySide6 installed via apt, not bundled
7. **VirtualBox first** — test in VM before real hardware deployment

### Architecture Overview

```
mermaid
graph LR
  ISO[StormOS ISO Image] --> GRUB[GRUB Bootloader]
  GRUB --> Kernel[Linux Kernel 6.x]
  Kernel --> Init[systemd]
  Init --> X11[X11 Display Server]
  Init --> StormOS[StormOS Desktop]
  X11 --> StormOS
  StormOS --> WM[Window Manager]
  StormOS --> Apps[Built-in Apps]
  StormOS --> Services[Services: Audio, Users, Workspaces]
  Init --> Apt[apt Package Manager]
  Apt --> Repos[Debian Repositories]
  Apt --> StormOS-Repo[StormOS Repository]
  StormOS --> Linux-Apps[Linux Applications]
```

### Distribution Build System

**Tool**: `live-build` (Debian's official live image builder)

**Structure**:
```
dist/
  config/                 # live-build configuration
    auto/                 # hooks and scripts
    hooks/                # pre/post install hooks
    includes/             # files to include in the image
      chroot/             # files in the chroot (installed system)
      binary/             # files in the ISO root (boot menu, etc.)
  scripts/
    build_iso.sh          # main build script
    install_stormos.sh    # StormOS installation hook
    configure_boot.sh     # boot configuration hook
    setup_auto_login.sh   # auto-login configuration
    setup_display.sh      # X11 configuration
  output/                 # built ISO images
  docs/
    build-guide.md        # build instructions
    install-guide.md      # installation guide
```

**Build process**:
1. `lb config` — configure base system (Debian bookworm, x86_64, Calamares installer)
2. `lb build` — build the ISO image with:
   - Debian base system
   - Linux kernel with hardware support
   - X11 display server with Mesa drivers
   - Python 3.13 + PySide6 + dependencies
   - StormOS source code installed to `/opt/stormos`
   - systemd services for auto-login and StormOS startup
   - Calamares installer for disk installation

### StormOS Linux Porting

**Changes needed in StormOS code**:

1. **`src/stormos/core/paths.py`** — add Linux-specific path resolution:
   - When running on Linux, use `/opt/stormos` as bundle root
   - Use `/home/stormos/.local/share/stormos` for user data
   - Use `/var/lib/stormos` for system-wide data

2. **`src/stormos/core/platform_compat.py`** — already has Linux support from Phase 10, but needs:
   - Integration with systemd for startup
   - Proper X11/Wayland display detection
   - Linux-specific file explorer integration

3. **`src/stormos/app.py`** — add Linux-specific initialization:
   - Check for display server availability
   - Set up logging to systemd journal
   - Handle graceful shutdown signals

4. **`src/stormos/desktop/window.py`** — ensure window management works with X11:
   - Use X11 window properties for window management
   - Handle X11-specific events

5. **`src/stormos/services/audio_manager.py`** — use PulseAudio/PipeWire on Linux:
   - Detect and use PulseAudio or PipeWire for audio output
   - Fallback to ALSA if neither is available

### Boot Configuration

**Auto-login and StormOS startup**:

1. **systemd service** (`/etc/systemd/system/stormos.service`):
   ```ini
   [Unit]
   Description=StormOS Desktop Environment
   After=display-manager.service
   Wants=display-manager.service

   [Service]
   Type=simple
   User=stormos
   Environment=DISPLAY=:0
   ExecStart=/usr/bin/python3 /opt/stormos/main.py
   Restart=on-failure
   RestartSec=5

   [Install]
   WantedBy=graphical.target
   ```

2. **Auto-login configuration** (`/etc/systemd/system/getty@tty1.service.d/override.conf`):
   ```ini
   [Service]
   ExecStart=
   ExecStart=-/sbin/agetty --autologin stormos --noclear %I $TERM
   ```

3. **X11 auto-start** (`/home/stormos/.xinitrc`):
   ```bash
   exec startx /opt/stormos/main.py
   ```

### Calamares Installer Configuration

**Modules**:
- `welcome` — welcome screen with StormOS branding
- `locale` — language selection
- `keyboard` — keyboard layout
- `partition` — disk partitioning (guided/manual)
- `users` — user account creation
- `bootloader` — GRUB installation
- `fstab` — filesystem configuration
- `finished` — completion screen

**Custom modules**:
- `stormos-setup` — post-install StormOS configuration
- `stormos-services` — enable StormOS systemd services

### Package Management

**Custom StormOS apt repository**:
- Hosted on GitHub Pages or a simple web server
- Contains StormOS-specific packages:
  - `stormos-core` — main StormOS application
  - `stormos-apps` — built-in applications
  - `stormos-services` — system services
  - `stormos-theme` — visual theme and assets

**Debian dependencies** (installed via apt):
- `python3` (3.13)
- `python3-pyside6` (Qt6 bindings)
- `python3-pil` (Pillow)
- `xserver-xorg` (X11 display server)
- `xserver-xorg-video-all` (video drivers)
- `mesa-utils` (3D acceleration)
- `pulseaudio` or `pipewire` (audio)
- `network-manager` (network connectivity)
- `bluez` (Bluetooth)
- `firmware-linux` (basic firmware)

### Virtual Machine Testing

**VirtualBox**:
- Create VM with 4GB RAM, 32GB disk, 2 CPU cores
- Install Guest Additions for better integration
- Test boot, installation, and basic functionality

**QEMU**:
- Test with different hardware configurations
- Test without GUI (headless) for CI/CD

**VMware**:
- Test on VMware Workstation/Player
- Install VMware Tools

### File Structure

```
StormOS_GUI/
  dist/                          # NEW: Distribution build system
    config/                      # live-build configuration
      auto/
      hooks/
      includes/
        chroot/
          etc/
            systemd/system/
              stormos.service    # systemd service
          opt/stormos/           # StormOS installation
          usr/bin/
            stormos              # launcher script
        binary/
          isolinux/              # boot menu
          calamares/             # installer config
    scripts/
      build_iso.sh               # main build script
      install_stormos.sh         # StormOS installation
      configure_boot.sh          # boot config
      setup_auto_login.sh        # auto-login
      setup_display.sh           # X11 config
    output/                      # built ISO images
    docs/
      build-guide.md             # build instructions
      install-guide.md           # installation guide
  src/stormos/
    core/
      paths.py                   # MODIFIED: Linux path resolution
      platform_compat.py         # MODIFIED: systemd integration
    app.py                       # MODIFIED: Linux initialization
    desktop/
      window.py                  # MODIFIED: X11 window properties
    services/
      audio_manager.py           # MODIFIED: PulseAudio/PipeWire
  tests/
    test_bootable.py             # NEW: Boot configuration tests
```

### Risks

1. **PySide6 availability** — PySide6 may not be available in Debian bookworm's repositories; may need to use pip or build from source
   - **Mitigation**: Use pip to install PySide6 in the chroot, or use a newer Debian release (trixie/testing)

2. **Hardware acceleration** — GPU drivers may not work in VMs or on all hardware
   - **Mitigation**: Include software rendering fallback (LLVMpipe)

3. **Audio compatibility** — PulseAudio vs PipeWire conflicts
   - **Mitigation**: Detect and use whichever is available, with ALSA fallback

4. **ISO size** — including all dependencies may exceed 2GB
   - **Mitigation**: Use minimal base system, exclude unnecessary packages

5. **Calamares customization** — may require significant configuration for StormOS-specific needs
   - **Mitigation**: Use Calamares defaults where possible, customize only StormOS-specific steps

6. **Boot time** — systemd services and X11 startup may be slow
   - **Mitigation**: Disable unnecessary services, use lightweight X11 configuration


# Testing

### Validation Approach

Test the bootable distribution at multiple levels:
1. **Unit tests** — test StormOS Linux-specific code changes
2. **Build tests** — verify ISO builds successfully
3. **VM tests** — boot and test in VirtualBox/QEMU
4. **Functional tests** — test installation, boot, and basic functionality

### Key Scenarios

1. **ISO Build**
   - Run `build_iso.sh` and verify ISO is created
   - Check ISO size is under 2GB
   - Verify ISO contains Calamares installer

2. **VM Boot**
   - Create VirtualBox VM with ISO
   - Verify GRUB menu appears
   - Verify "Try StormOS" option boots to Live environment
   - Verify "Install StormOS" option launches Calamares

3. **Live USB**
   - Boot from Live USB without installation
   - Verify StormOS desktop loads
   - Verify basic functionality (window management, apps, etc.)

4. **Installation**
   - Run Calamares installer
   - Complete installation to virtual disk
   - Reboot and verify auto-login to StormOS

5. **Post-Installation**
   - Verify StormOS desktop loads on boot
   - Verify apt package management works
   - Verify Linux software can be installed (e.g., `apt install firefox`)
   - Verify StormOS manages windows for installed software
   - Verify audio, network, and USB work

6. **StormOS Functionality**
   - Verify all built-in apps work
   - Verify window management (snap, workspaces, task switcher)
   - Verify user account management
   - Verify audio system
   - Verify settings app

### Edge Cases

1. **Low RAM** — test with 2GB RAM (minimum)
2. **No GPU** — test with software rendering only
3. **No network** — test offline installation and usage
4. **Multiple monitors** — test with dual monitor setup
5. **Different keyboard layouts** — test non-US keyboards
6. **Disk space** — test with minimal disk space (16GB)

### Test Changes

- **`tests/test_bootable.py`** — new test suite for boot configuration, systemd service files, and Linux-specific path resolution
- **`tests/test_linux_integration.py`** — tests for Linux-specific functionality (X11, audio, display detection)
- **Integration tests** — VM-based tests that boot the ISO and verify functionality (requires VirtualBox/QEMU)


# Delivery Steps

###   Step 1: Phase 11.1 — Distribution Build System Foundation
Create the live-build configuration and build scripts for the Debian-based StormOS distribution.

- Create `dist/` directory structure with `config/`, `scripts/`, `output/`, and `docs/`
- Write `dist/config/` live-build configuration (Debian bookworm, x86_64, Calamares installer)
- Create `dist/scripts/build_iso.sh` — main build script that configures and builds the ISO
- Create `dist/scripts/install_stormos.sh` — hook to install StormOS in the chroot
- Create `dist/scripts/configure_boot.sh` — GRUB and boot configuration
- Create `dist/scripts/setup_auto_login.sh` — auto-login configuration
- Create `dist/scripts/setup_display.sh` — X11 display server configuration
- Write `dist/docs/build-guide.md` — step-by-step build instructions
- Test build process (dry run) to verify configuration is correct

###   Step 2: Phase 11.2 — StormOS Linux Porting
Modify StormOS code to run on Linux with proper path resolution, display server integration, and audio.

- Update `src/stormos/core/paths.py` — add Linux-specific paths (`/opt/stormos`, `/home/stormos/.local/share/stormos`, `/var/lib/stormos`)
- Update `src/stormos/core/platform_compat.py` — add systemd integration, X11/Wayland display detection, Linux file explorer
- Update `src/stormos/app.py` — add Linux initialization (display server check, systemd logging, shutdown signals)
- Update `src/stormos/desktop/window.py` — add X11 window properties for window management
- Update `src/stormos/services/audio_manager.py` — add PulseAudio/PipeWire detection and usage with ALSA fallback
- Create `tests/test_linux_integration.py` — tests for Linux-specific functionality
- Run existing tests to verify no regressions on Windows

###   Step 3: Phase 11.3 — Boot Configuration and Systemd Services
Create systemd services, auto-login configuration, and X11 setup for booting directly into StormOS.

- Create `dist/config/includes/chroot/etc/systemd/system/stormos.service` — systemd service for StormOS
- Create auto-login override for getty@tty1.service
- Create `/home/stormos/.xinitrc` — X11 auto-start script
- Create X11 configuration (`/etc/X11/xorg.conf`) with basic video driver setup
- Create `/usr/bin/stormos` launcher script
- Configure systemd targets (graphical.target, disable multi-user.target)
- Create `tests/test_bootable.py` — tests for boot configuration files and systemd service syntax
- Verify service files parse correctly with `systemd-analyze verify`

###   Step 4: Phase 11.4 — Calamares Installer Configuration
Configure Calamares graphical installer with StormOS branding and custom post-install steps.

- Create `dist/config/includes/chroot/etc/calamares/` — Calamares configuration directory
- Configure installer modules: welcome, locale, keyboard, partition, users, bootloader, fstab, finished
- Create custom Calamares module `stormos-setup` — post-install StormOS configuration
- Create custom Calamares module `stormos-services` — enable StormOS systemd services
- Add StormOS branding (logo, colors, welcome text) to Calamares
- Configure GRUB installation via Calamares
- Create `dist/config/includes/binary/isolinux/` — boot menu configuration
- Test Calamares configuration syntax

###   Step 5: Phase 11.5 — ISO Build and Virtual Machine Testing
Build the final ISO image and test it in VirtualBox/QEMU virtual machines.

- Run full ISO build with `dist/scripts/build_iso.sh`
- Verify ISO size and contents
- Create VirtualBox VM (4GB RAM, 32GB disk, 2 CPU cores)
- Test Live USB boot (Try StormOS without installation)
- Test Calamares installation in VM
- Verify auto-login and StormOS desktop after installation
- Test basic functionality: window management, apps, audio, network
- Test apt package management (install a package like `firefox`)
- Test StormOS manages windows for installed Linux software
- Create `dist/docs/install-guide.md` — installation and usage guide
- Document any issues and create follow-up tasks for real hardware testing