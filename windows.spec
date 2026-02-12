# -*- mode: python ; coding: utf-8 -*-

datas = [
    ('./res/excel_tool.ico', 'res'),
    ('./config/service', 'config'),
    ('./config/master_account', 'config'),
    ('./config/from_account', 'config'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PyQt5.sip',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'xlsxwriter',
        'pandas',
        'numpy',
        'openpyxl',
        'pkg_resources.py2_warn',
        'pkg_resources',
        'setuptools',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5.QtBluetooth',
        'PyQt5.QtDesigner',
        'PyQt5.QtHelp',
        'PyQt5.QtMultimedia',
        'PyQt5.QtNetwork',
        'PyQt5.QtQml',
        'PyQt5.QtQuick',
        'PyQt5.QtWebEngine',
        'PyQt5.QtWebEngineCore',
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtWebSockets',
        'PyQt5.QtXml',
        'PyQt5.QtXmlPatterns',
        'matplotlib',
        'scipy',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='excel_tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='res/excel_tool.ico',
)