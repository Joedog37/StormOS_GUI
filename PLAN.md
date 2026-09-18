# StormOS Development Plan

## What we are building

StormOS is a Python desktop environment: a fullscreen application that looks
and behaves like its own operating system while running on top of Windows.

It is not a bootable operating system yet. A real bootable OS is a separate,
much later project involving a kernel, drivers, and low-level languages.

## Rules for this new version

- Build one small feature at a time.
- Run a test after every feature.
- Keep code organized and easy to understand.
- Keep the old project only in `backups/` as a reference.
- Use Python 3.13 and PySide6 only; do not use Tkinter.
- Aim for a polished, modern desktop design with consistent colors, spacing,
  icons, typography, and window controls.
- Treat security as a foundation feature, not a later add-on.

## Security baseline

- [x] Keep StormOS data separate from its program files.
- [x] Never store passwords as plain text.
- [x] Use a unique random salt and a slow password hash for every account.
- [x] Use safe comparisons for password checks.
- [x] Validate all filenames, usernames, and app-package contents.
- [x] Do not run downloaded or installed app code automatically.
- [ ] Keep security-sensitive actions behind clear account permissions.
- [x] Add tests for login, data handling, and app-install security.
- [ ] Review security again before creating a public `.exe` release.

## Phase 0 - Visual design

- [x] Follow the Thunderhead Pictures design brief in `DESIGN.md`.
- [x] Choose the final wallpaper and logo treatment.
- [x] Design the boot, login, desktop, taskbar, and Start menu before coding.
- [x] Keep the interface original; do not copy Windows, Linux, or macOS.

## Phase 1 - Clean foundation

- [x] Create the new project folders.
- [x] Add `requirements.txt`.
- [x] Create one program entry file.
- [x] Open a simple fullscreen StormOS window.
- [x] Verify the program starts from PyCharm.

## Phase 2 - First user experience

- [x] Create a boot screen using the StormOS logo.
- [x] Create a login screen.
- [x] Create user registration / sign-up account creation dialog.
- [x] Create a temporary local test account.
- [x] Move from login to the desktop.

## Phase 3 - Desktop

- [x] Show the wallpaper.
- [x] Add a taskbar and clock.
- [x] Add a Start button.
- [x] Add a basic Start menu.
- [x] Add a safe Exit StormOS option.

## Phase 4 - Apps

- [x] Create an app system with app names and icons.
- [x] Build one simple built-in app, such as Notes.
- [x] Add an app window with minimize, maximize, and close buttons.
- [x] Add a file or settings app later.
- [x] Add versatile Storm Power Calculator (natural math expression engine, live tape, unit & base converters).
- [x] Add secure App Store & Package Manager with `.stormapp` package installation.

## Phase 5 - Accounts and settings

- [x] Save accounts safely on the computer.
- [x] Use hashed passwords with unique salts (PBKDF2-HMAC-SHA256).
- [x] Add wallpaper presets, procedural backgrounds, and custom image file picker.
- [x] Add multi-monitor display detection and custom resolution settings.
- [x] Add system-wide interactive mouse cursors and crisp icons.
- [x] Upgrade Notes into a multi-tab Notepad++ style Code Studio (syntax highlighting, line numbers, auto-indent, find/replace, code execution).
- [x] Add logout, lock, and restart-the-app actions.

## Phase 6 - Packaging

- [x] Test the completed project.
- [x] Package it as a standalone Windows `.exe` (`dist/StormOS/StormOS.exe`) with PyInstaller.
- [x] Add automated build script (`scripts/build_exe.py`) and PyInstaller spec (`StormOS.spec`).
- [x] Generate official multi-resolution Windows icon (`assets/stormos.ico`).
- [x] Ensure persistent user data and sandboxes are preserved across runs.

## Phase 7 - User Management & Account Administration

- [ ] Edit existing user accounts (change password, update display name, delete account).
- [ ] User profile avatars and custom profile pictures.
- [ ] Role-based permissions (Administrator vs. Standard User).
- [ ] User data export, backup, and restore tools.

## Phase 8 - Audio System & Atmospheric Immersion

- [ ] Startup sound playback toggle and audio settings.
- [ ] Ambient background audio (rain, thunderstorm, low hum).
- [ ] UI sound effects (button clicks, window maximize/minimize, error chime).
- [ ] Audio volume mixer app.

## Phase 9 - Advanced Windowing & Multitasking

- [ ] Window snap grid (left/right split, 4-corner snap).
- [ ] Virtual workspaces / multiple desktop surfaces.
- [ ] Alt+Tab task switcher overlay.
- [ ] Minimap / overview mode of all running applications.

## Phase 10 - Distribution & Cross-Platform

- [ ] Standalone installer wizard (Inno Setup / NSIS) for one-click setup.
- [ ] Portable zip package distribution.
- [ ] Linux and macOS compatibility layers.
- [ ] Research a separate real bootable-OS project.
