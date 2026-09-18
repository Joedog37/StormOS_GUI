# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['E:/StormOS_GUI/main.py'],
    pathex=['E:/StormOS_GUI/src'],
    binaries=[],
    datas=[('E:/StormOS_GUI/assets', 'assets')],
    hiddenimports=['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'stormos', 'stormos.core', 'stormos.core.constants', 'stormos.core.paths', 'stormos.core.security', 'stormos.ui', 'stormos.ui.main_window', 'stormos.ui.theme', 'stormos.ui.wallpaper_manager', 'stormos.screens', 'stormos.screens.boot_screen', 'stormos.screens.login_screen', 'stormos.screens.signup_dialog', 'stormos.desktop', 'stormos.desktop.desktop_view', 'stormos.desktop.storm_dock', 'stormos.desktop.command_center', 'stormos.desktop.window', 'stormos.desktop.safe_exit_dialog', 'stormos.apps', 'stormos.apps.registry', 'stormos.apps.calculator', 'stormos.apps.notes', 'stormos.apps.files', 'stormos.apps.terminal', 'stormos.apps.activity_monitor', 'stormos.apps.settings', 'stormos.apps.app_manager', 'stormos.services', 'stormos.services.user_manager', 'stormos.services.app_installer'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='StormOS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['E:/StormOS_GUI/assets/stormos.ico'],
)
