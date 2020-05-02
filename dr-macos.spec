# -*- mode: python ; coding: utf-8 -*-
from kivy.tools.packaging.pyinstaller_hooks import get_deps_minimal, hookspath

block_cipher = None

args = {**get_deps_minimal(video=None, audio=None, camera=None, spelling=None)}
args["hiddenimports"].append('plyer.platforms.macosx.filechooser')
args["binaries"].append(('assets/ffmpeg', 'assets'))
a = Analysis(['dr.py'],
             pathex=['/Users/orion/devel/drpy'],
             datas=[],
             hookspath=[],
             runtime_hooks=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False,
             **args )
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='dr',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='dr')
app = BUNDLE(coll,
             name='dr.app',
             icon=None,
             bundle_identifier=None)
