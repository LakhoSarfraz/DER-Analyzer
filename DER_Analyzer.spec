# -*- mode: python ; coding: utf-8 -*-
import os
import docx

# Copy the entire docx package folder to ensure all XML and docx templates are included
docx_path = os.path.dirname(docx.__file__)
datas = [(docx_path, 'docx')]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DER_Analyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # CRITICAL FIX: Disable UPX to prevent corruption of the .docx template
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
)
