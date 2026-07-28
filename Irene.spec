# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [
    ('web', 'web'),
    ('avatar', 'avatar'),
    ('cogs', 'cogs'),
    ('.env', '.'),
    ('manifest.json', '.'),
]
binaries = []
hiddenimports = [
    'cogs.commands',
    'cogs.messages',
    'aiohttp',
    'edge_tts',
    'speech_recognition',
    'gtts',
]

# Collect edge_tts data files
try:
    tmp_ret = collect_all('edge_tts')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except Exception:
    pass

a = Analysis(
    ['desktop_entry.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='IreneApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='IreneApp',
)
