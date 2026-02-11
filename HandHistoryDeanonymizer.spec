# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Hand History De-anonymizer."""

import sys
from pathlib import Path

block_cipher = None

# Get the project root
project_root = Path(SPECPATH)

# Data files to include
datas = [
    (str(project_root / 'hand_history' / 'seat_mapping.toml'), 'hand_history'),
    (str(project_root / 'image_analyzer' / 'corrections.toml'), 'image_analyzer'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'anthropic',
    'httpx',
    'PIL',
    'cv2',
    'numpy',
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'tomllib',
    'tomli_w',
    'dotenv',
]

a = Analysis(
    ['app.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'IPython',
        'jupyter',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Hand History De-anonymizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Hand History De-anonymizer',
)

# macOS app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='Hand History De-anonymizer.app',
        icon=None,  # Add icon path here if you have one: 'assets/icon.icns'
        bundle_identifier='com.oitnow.handhistory',
        info_plist={
            'CFBundleName': 'Hand History De-anonymizer',
            'CFBundleDisplayName': 'Hand History De-anonymizer',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.15',
        },
    )
