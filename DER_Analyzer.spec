# -*- mode: python ; coding: utf-8 -*-
import os
import docx
from PyInstaller.utils.hooks import collect_data_files

# Bundle python-docx package data and explicitly include its default Word template.
# docx.Document() needs this file when creating a new document without a template.
datas = collect_data_files('docx')
template_src = os.path.join(os.path.dirname(docx.__file__), 'templates', 'default.docx')
if os.path.isfile(template_src):
    normalized_src = os.path.normcase(os.path.abspath(template_src))
    already_included = any(
        os.path.normcase(os.path.abspath(src)) == normalized_src
        and os.path.normpath(dest).replace('\\', '/') == 'docx/templates'
        for src, dest in datas
    )
    if not already_included:
        datas.append((template_src, 'docx/templates'))
else:
    raise FileNotFoundError(f"python-docx default template not found: {template_src}")

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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
)
