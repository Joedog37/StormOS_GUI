# StormOS Bootable OS Research

## Overview

This document researches the feasibility and approach for creating a real, bootable operating system based on the StormOS desktop environment. Currently, StormOS runs as a Python application on top of Windows. This research explores paths to make it a standalone Debian-based Linux distribution with StormOS as the default desktop.

## Current State

StormOS is a Python/PySide6 desktop environment running on top of Windows. It provides:
- Custom desktop shell with wallpaper, dock, and command center
- Window management with snapping, workspaces, and task switching
- Built-in applications (Notes, Calculator, Terminal, File Manager, etc.)
- User account management with secure authentication
- Audio system with ambient sounds and UI effects
- App store and package management

## Why Not a Traditional Kernel?

Building a kernel from scratch in C/C/Rust is a massive undertaking:
- **Linux kernel**: ~30 million lines of code, decades of development
- **Microkernels**: Still require significant driver and HAL development
- **Time estimate**: 5-10 years of full-time work by a team of engineers
- **Hardware support**: Each device needs a driver; thousands of devices exist

## Recommended Approach: Debian-Based Custom Distribution

The most practical path is to create a custom Debian-based Linux distribution using `live-build`, with StormOS as the sole desktop environment. This provides full package management (apt), hardware support, and the ability to install Linux software while maintaining StormOS as the primary UI.

### Why Debian Trixie (Testing)?

**Debian trixie** (testing branch) is required instead of bookworm (stable) because:
- **Python 3.13** is available in trixie, while bookworm only has Python 3.11
- StormOS requires Python 3.13+ for compatibility
- The testing branch is stable enough for custom distributions
- Critical packages can be pinned to stable versions if needed

### Build Environment Requirements

**Important**: The ISO must be built on a Linux system. Windows cannot run `live-build` directly.

**Recommended build environments:**
- **WSL2** (Windows Subsystem for Linux 2) — run Ubuntu/Debian inside Windows
- **Ubuntu VM** — full Linux VM via VirtualBox or VMware
- **Native Linux machine** — direct build on Linux hardware

Do not attempt to build the ISO on Windows natively; the live-build toolchain requires Linux kernel features.

### Option 1: Debian Live-Build (Recommended)

**live-build** is Debian's official tool for creating custom live images and installable distributions.

**Advantages:**
- Creates bootable ISO images with Calamares graphical installer
- Full apt package management for installing Linux software after installation
- Based on Debian trixie with Python 3.13 support
- Can create both Live USB (try before install) and installable ISO
- StormOS replaces the entire desktop environment — no traditional DE needed
- Well-documented and used by Linux Mint, Debian Live, etc.

**Disadvantages:**
- Requires Linux build environment (WSL2 or VM)
- Larger ISO size (~1.5-2GB) due to full package management
- Dependency on Debian repositories

**Implementation Steps:**
1. Set up live-build on WSL2 or Ubuntu VM
2. Configure Debian trixie as the base system
3. Add Python 3.13, PySide6, and dependencies via apt
4. Install StormOS to `/opt/stormos`
5. Configure systemd service for StormOS startup
6. Configure Calamares installer for disk installation
7. Build the ISO image

**Estimated Timeline:** 1-3 months for a working prototype

### Option 2: Buildroot (Embedded Systems)

**Buildroot** is a toolchain that generates complete Linux systems from source.

**Advantages:**
- Simple configuration interface (menuconfig)
- Generates a complete bootable image (SD card, USB, disk image)
- Full control over every package included
- No package management overhead (static system)
- Small footprint (can be under 100MB)
- Excellent for embedded and kiosk-style systems

**Disadvantages:**
- No package management after build (must rebuild to add/remove packages)
- Manual Python/PySide6 integration required
- No automatic updates

**Best for:** Embedded devices, Raspberry Pi, kiosk systems where package management is not needed

**Estimated Timeline:** 3-6 months for a working prototype

### Option 3: Yocto Project (Enterprise)

**Yocto Project** is a more complex framework for building Linux distributions.

**Advantages:**
- Full package management (OPK/IPK)
- Layer-based customization
- Industry-standard for embedded Linux
- Support for updates and overlays
- Large community and documentation

**Disadvantages:**
- Steeper learning curve than live-build
- Slower build times
- More complex configuration

**Best for:** Enterprise embedded Linux, layer-based customization

**Estimated Timeline:** 6-12 months for a stable distribution

### Option 4: Raspberry Pi Focus

Targeting Raspberry Pi specifically opens additional options:

**Raspberry Pi OS Lite:**
- Start with Raspberry Pi OS Lite (no desktop)
- Install Python and PySide6
- Configure StormOS as the default application
- Benefits from existing hardware support

**Advantages:**
- Excellent hardware documentation
- Large community
- Affordable development hardware
- Well-supported Python ecosystem

**Estimated Timeline:** 1-2 months for Raspberry Pi prototype

## Technical Challenges

### 1. Python on Embedded Linux

**Challenge:** PySide6 requires Qt6, which has many system dependencies.

**Solution:**
- Use system packages for Qt6 where available
- For Buildroot/Yocto, create custom packages for Qt6 and PySide6
- Consider PyOgre or other lighter alternatives for very constrained systems

### 2. Hardware Acceleration and Auto-Driver Detection

**Challenge:** GUI performance requires GPU acceleration. Different GPUs need different drivers — NVIDIA requires proprietary drivers for good gaming performance, while AMD and Intel work well with open-source drivers.

**Solution: Auto-Driver Detection Script**

Create `dist/scripts/setup_drivers.sh` that automatically detects and installs the appropriate GPU drivers:

1. **GPU Detection**: Run `lspci | grep -i vga` to identify the GPU hardware
2. **NVIDIA GPUs**: Install proprietary `nvidia-driver` package with user confirmation
   - Requires `non-free` repository in sources.list
   - May need `linux-headers` for kernel module compilation
   - Provides full hardware acceleration for gaming
3. **AMD GPUs**: Use `amdgpu` open-source driver (excellent performance, no extra installation needed)
4. **Intel GPUs**: Use `i915` open-source driver (excellent performance, no extra installation needed)
5. **Fallback**: If no driver matches, use `llvmpipe` software rendering (slow but functional)

**Important Notes:**
- NVIDIA RTX 3050 and similar GPUs will run slowly with open-source `nouveau` drivers
- Proprietary NVIDIA drivers are required for good gaming performance
- Open-source drivers (amdgpu, i915) provide excellent performance for AMD and Intel GPUs
- The script runs during first boot or installation, prompting the user for confirmation

### 3. Input Devices

**Challenge:** Keyboard, mouse, and touch input must work out of the box.

**Solution:**
- Linux kernel includes drivers for most USB input devices
- Configure udev rules for automatic device detection
- Qt handles input abstraction

### 4. Display Output

**Challenge:** Multiple display resolutions and configurations.

**Solution:**
- Use kernel modesetting (KMS) drivers
- Configure display output in bootloader (GRUB, U-Boot)
- StormOS can detect and adapt to available displays

### 5. Storage and Filesystem

**Challenge:** Persistent user data across reboots.

**Solution:**
- Standard Linux filesystem (ext4, btrfs, f2fs)
- StormOS user data directory mapped to /home/stormos
- Optional: read-only root filesystem with overlay for updates

### 6. Secure Boot Requirement

**Important**: Secure Boot must be disabled in the BIOS/UEFI settings to boot the StormOS ISO.

- The StormOS ISO does not support Secure Boot signing
- Users must enter BIOS/UEFI setup before booting and disable Secure Boot
- This is documented in the installation guide and shown on the boot screen
- Secure Boot can be re-enabled after installation if the system supports third-party key enrollment

## Boot Configuration

**Single Boot Method: systemd Service Only**

StormOS uses one consistent boot method — a systemd user service. No mixing of approaches (no .xinitrc, no getty autologin override).

### systemd Service for StormOS

Create `/etc/systemd/system/stormos.service`:

```ini
[Unit]
Description=StormOS Desktop Environment
After=graphical.target
Wants=graphical.target

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

### Auto-Login Configuration

Use `systemd-logind.conf` for auto-login instead of pam_nologin (which blocks logins):

`/etc/systemd/logind.conf`:
```ini
[Login]
AutoVCLogin=stormos
```

This auto-logs in the `stormos` user on the virtual console, then the systemd service starts StormOS.

### Why Not Other Methods?

- **pam_nologin**: Blocks all logins when `/etc/nologin` exists — not suitable for auto-login
- **.xinitrc**: Requires startx/X11 to be started separately — adds complexity
- **getty autologin override**: Works but mixes with other boot methods — keeps things simple with one approach

## Recommended Roadmap

### Phase 1: Research and Planning (1-2 months)
- [x] Research bootable OS approaches (this document)
- [x] Select target platform (x86_64 VM first, then real hardware)
- [x] Choose build system (Debian live-build recommended)
- [ ] Define minimum hardware requirements
- [ ] Create proof-of-concept on virtual machine

### Phase 2: Base System (2-3 months)
- [ ] Set up live-build development environment on WSL2 or Ubuntu VM
- [ ] Configure Debian trixie as the base system
- [ ] Add Python 3.13 package
- [ ] Add Qt6 and PySide6 packages
- [ ] Create minimal bootable ISO

### Phase 3: StormOS Integration (2-3 months)
- [ ] Port StormOS to run on Linux
- [ ] Replace Windows-specific code with cross-platform alternatives
- [ ] Configure systemd service for StormOS startup
- [ ] Test window management and applications
- [ ] Optimize boot time

### Phase 4: Hardware Support (2-3 months)
- [ ] Test on target hardware (PC or VM)
- [ ] Configure display output
- [ ] Test input devices (keyboard, mouse, touch)
- [ ] Configure audio output
- [ ] Test network connectivity
- [ ] Implement auto-driver detection for NVIDIA/AMD/Intel GPUs

### Phase 5: Polish and Distribution (1-2 months)
- [ ] Create installation media (ISO with Calamares installer)
- [ ] Write installation documentation with Secure Boot warning
- [ ] Test on multiple hardware configurations
- [ ] Create update mechanism
- [ ] Prepare for beta testing

**Total Estimated Timeline:** 8-13 months

## Hardware Requirements

### Minimum (Raspberry Pi 4)
- CPU: Quad-core ARM Cortex-A72
- RAM: 2GB
- Storage: 16GB SD card
- Display: HDMI output

### Recommended (x86_64 PC)
- CPU: Dual-core x86_64 (Intel/AMD)
- RAM: 4GB
- Storage: 32GB SSD
- Display: Any HDMI/DisplayPort/VGA

### Ideal
- CPU: Quad-core x86_64
- RAM: 8GB
- Storage: 64GB SSD
- GPU: Integrated or discrete GPU
- Display: Multiple display support

## Alternative: Hybrid Approach

If a full bootable OS is too ambitious, consider a hybrid approach:

1. **StormOS as a Linux Desktop Environment**
   - Install StormOS alongside GNOME/KDE on any Linux distribution
   - Users select "StormOS" at the login screen
   - StormOS replaces the desktop shell but uses system services

2. **StormOS Container**
   - Package StormOS in a Docker container
   - Run on any Linux system with a display server
   - Isolated from host system dependencies

3. **StormOS WSL2 Integration**
   - Run StormOS inside WSL2 on Windows
   - Use WSLg for GUI support
   - Access Windows files from within StormOS

## App Store Linux Program Loading

The StormOS App Store needs to load and display native Linux programs installed via apt.

### LinuxProgramLoader Service

Create `src/stormos/services/linux_program_loader.py` that:

1. **Scans** `/usr/share/applications/*.desktop` files for installed Linux programs
2. **Parses** desktop entries: name, icon, exec command, categories
3. **Creates** StormOS AppMetadata wrappers for each Linux program
4. **Registers** them in AppRegistry so they appear in the App Store and Start menu
5. **Handles** launching via subprocess with proper environment

### App Store Integration

Update `src/stormos/apps/app_manager.py` to add a "Linux Programs" section:

- Shows apps detected from the system (Firefox, LibreOffice, Steam, etc.)
- Launch button runs the native Linux executable
- Install button runs `apt install` for the package (via `pkexec` for root access)

### Benefits

- Users can install and run any Linux software (browsers, games, development tools)
- StormOS manages windows for all installed Linux programs
- The App Store becomes a unified interface for both StormOS apps and Linux programs

## Conclusion

The most practical path to a bootable StormOS is using **Debian live-build** to create a custom Debian-based distribution, targeting x86_64 PCs and VMs. This approach provides:

- Full apt package management for installing Linux software
- Python 3.13 support via Debian trixie (testing)
- Auto-driver detection for NVIDIA/AMD/Intel GPUs with proprietary driver support
- Single boot method via systemd service for reliable startup
- Calamares graphical installer for easy installation
- StormOS as the sole desktop environment — no traditional DE needed

**Key Requirements:**
- Build the ISO on Linux (WSL2 or VM), not Windows
- Disable Secure Boot in BIOS/UEFI to boot the ISO
- Use Debian trixie for Python 3.13 compatibility

The estimated timeline is 8-13 months for a working prototype, depending on available resources and target hardware complexity.

## References

- Buildroot: https://buildroot.org/
- Yocto Project: https://yoctoproject.org/
- Raspberry Pi OS: https://www.raspberrypi.com/software/
- Alpine Linux: https://www.alpinelinux.org/
- Qt for Python (PySide6): https://doc.qt.io/qtforpython-6/
- Linux Kernel Documentation: https://www.kernel.org/doc/
