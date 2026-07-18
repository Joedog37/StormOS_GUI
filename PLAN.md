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

- [ ] Keep StormOS data separate from its program files.
- [ ] Never store passwords as plain text.
- [ ] Use a unique random salt and a slow password hash for every account.
- [ ] Use safe comparisons for password checks.
- [ ] Validate all filenames, usernames, and app-package contents.
- [ ] Do not run downloaded or installed app code automatically.
- [ ] Keep security-sensitive actions behind clear account permissions.
- [ ] Add tests for login, data handling, and app-install security.
- [ ] Review security again before creating a public `.exe` release.

## Phase 0 - Visual design

- [ ] Follow the Thunderhead Pictures design brief in `DESIGN.md`.
- [ ] Choose the final wallpaper and logo treatment.
- [ ] Design the boot, login, desktop, taskbar, and Start menu before coding.
- [ ] Keep the interface original; do not copy Windows, Linux, or macOS.

## Phase 1 - Clean foundation

- [ ] Create the new project folders.
- [ ] Add `requirements.txt`.
- [ ] Create one program entry file.
- [ ] Open a simple fullscreen StormOS window.
- [ ] Verify the program starts from PyCharm.

## Phase 2 - First user experience

- [ ] Create a boot screen using the StormOS logo.
- [ ] Create a login screen.
- [ ] Create a temporary local test account.
- [ ] Move from login to the desktop.

## Phase 3 - Desktop

- [ ] Show the wallpaper.
- [ ] Add a taskbar and clock.
- [ ] Add a Start button.
- [ ] Add a basic Start menu.
- [ ] Add a safe Exit StormOS option.

## Phase 4 - Apps

- [ ] Create an app system with app names and icons.
- [ ] Build one simple built-in app, such as Notes.
- [ ] Add an app window with minimize, maximize, and close buttons.
- [ ] Add a file or settings app later.

## Phase 5 - Accounts and settings

- [ ] Save accounts safely on the computer.
- [ ] Use hashed passwords.
- [ ] Add wallpaper and theme settings.
- [ ] Add logout and restart-the-app actions.

## Phase 6 - Packaging

- [ ] Test the completed project.
- [ ] Package it as a Windows `.exe`.
- [ ] Test the `.exe` on a computer without Python installed.

## Later ideas

- Linux and macOS versions.
- App store and installable apps.
- Multiple desktops and better window management.
- Research a separate real bootable-OS project.
