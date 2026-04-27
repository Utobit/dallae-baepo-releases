# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

block_cipher = None

webview_datas, webview_bins, webview_hidden = collect_all('webview')
clr_datas,     clr_bins,     clr_hidden     = collect_all('clr_loader')
pn_datas,      pn_bins,      pn_hidden      = collect_all('pythonnet')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=webview_bins + clr_bins + pn_bins,
    datas=[('dallae_icon.png', '.'), ('dallae_icon.ico', '.')] + webview_datas + clr_datas + pn_datas,
    hiddenimports=[
        'pycaw',
        'pycaw.pycaw',
        'comtypes',
        'comtypes.client',
        'anthropic',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'pystray',
        'PIL',
        'win32gui',
        'win32con',
        'pythoncom',
        'pywintypes',
        'google.generativeai',
        'google.auth',
        'google.api_core',
        'webview',
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        'clr',
        'clr_loader',
        'pythonnet',
    ] + webview_hidden + clr_hidden + pn_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DallaePC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='dallae_icon.ico',
)
